"""
API Endpoints module
-----------------
Defines RESTful API endpoints for the application using FastAPI with enhanced security and logging
"""

import os
import threading
import time
import hashlib
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import pathlib
import json
import pandas as pd
from src.controller.spreadsheet_controller import SpreadsheetController
from src.model.session_manager import SessionManager
from src.model.prompt_history import PromptHistory
from src.controller.script_fixer import ScriptExecutionFailureException
from src.controller.mapping_manager import MappingManager
from src.controller.security_manager import SecurityManager
from src.controller.session_manager import session_manager
from src.controller.security_logger import SecurityLevel

# Create FastAPI app with security settings
app = FastAPI(
    title="EditorLive Finance Application",
    description="Secure finance application for spreadsheet processing",
    version="1.0.0"
)

# Initialize security components
security_manager = SecurityManager()

# Rate limiting storage (simple in-memory for now)
rate_limit_storage = {}

# Session tracking middleware
@app.middleware("http")
async def session_middleware(request: Request, call_next):
    """Track user sessions and log activity"""
    # Get or create session
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Create session if needed (in real app, would use cookies/JWT)
    session_id = f"{client_ip}_{hashlib.md5(user_agent.encode()).hexdigest()[:8]}"
    
    # Log page access
    session_manager.log_page_view(
        session_id, 
        str(request.url.path), 
        request.method
    )
    
    # Process request
    response = await call_next(request)
    
    # Log response status
    if response.status_code >= 400:
        session_manager.log_security_event(
            session_id,
            SecurityLevel.MEDIUM if response.status_code < 500 else SecurityLevel.HIGH,
            "http_error",
            f"🚨 HTTP Error {response.status_code} on {request.url.path}",
            {
                'status_code': response.status_code,
                'method': request.method,
                'path': str(request.url.path),
                'user_agent': user_agent
            },
            "WebServer"
        )
    
    return response

# Rate limiting storage (simple in-memory for now)
rate_limit_storage = {}

def get_client_ip(request: Request) -> str:
    """Extract client IP address"""
    if "x-forwarded-for" in request.headers:
        return request.headers["x-forwarded-for"].split(",")[0].strip()
    if "x-real-ip" in request.headers:
        return request.headers["x-real-ip"]
    return request.client.host if request.client else "unknown"

def check_rate_limit(request: Request, max_requests: int = 100, window_seconds: int = 300) -> bool:
    """Check if request is within rate limits with logging"""
    client_ip = get_client_ip(request)
    current_time = time.time()
    
    # Initialize rate limiting for IP
    if client_ip not in rate_limit_storage:
        rate_limit_storage[client_ip] = []
    
    # Clean old entries
    rate_limit_storage[client_ip] = [
        timestamp for timestamp in rate_limit_storage[client_ip]
        if current_time - timestamp < window_seconds
    ]
    
    request_count = len(rate_limit_storage[client_ip])
    
    # Create session ID for logging
    user_agent = request.headers.get("user-agent", "unknown")
    session_id = f"{client_ip}_{hashlib.md5(user_agent.encode()).hexdigest()[:8]}"
    
    # Log rate limit check
    session_manager.log_security_event(
        session_id,
        SecurityLevel.MEDIUM if request_count >= max_requests else SecurityLevel.LOW,
        "rate_limiting",
        f"⏱️ Rate limit check: {request_count}/{max_requests} requests",
        {
            'client_ip': client_ip,
            'endpoint': str(request.url.path),
            'request_count': request_count,
            'rate_limit': max_requests,
            'window_seconds': window_seconds,
            'utilization_percent': round((request_count / max_requests) * 100, 1)
        },
        "RateLimiter"
    )
    
    # Check if limit exceeded
    if request_count >= max_requests:
        return False
    
    # Add current request
    rate_limit_storage[client_ip].append(current_time)
    return True

# Dependency for rate limiting
def rate_limit_dependency(request: Request):
    """FastAPI dependency for rate limiting with enhanced logging"""
    if not check_rate_limit(request):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )

# Dependency for basic request validation
def validate_request_dependency(request: Request):
    """FastAPI dependency for basic request validation"""
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    
    # Check for suspicious user agents
    blocked_agents = ["sqlmap", "nikto", "nmap", "masscan", "nessus"]
    for blocked_agent in blocked_agents:
        if blocked_agent.lower() in user_agent.lower():
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Basic path validation
    path = str(request.url.path)
    if "../" in path or "..\\" in path:
        raise HTTPException(status_code=400, detail="Invalid request path")

# Get the base directory (adjust if needed)
BASE_DIR = pathlib.Path(__file__).parent.parent.parent

# Mount static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Setup templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Define Pydantic models for request/response validation
class CommandRequest(BaseModel):
    sessionId: str
    command: str

class PromptRequest(BaseModel):
    prompt: str

class HealthResponse(BaseModel):
    status: str
    version: str

class UploadResponse(BaseModel):
    success: bool
    sessionId: str
    has_mapping: Optional[bool] = False
    mapped_commands: Optional[List[str]] = None
    command_count: Optional[int] = 0

class ErrorResponse(BaseModel):
    error: str

class PromptHistoryResponse(BaseModel):
    prompt: Optional[str] = None

# Add these new model classes after your existing models
class TableChangesRequest(BaseModel):
    sessionId: str
    changes: List[Dict[str, Any]]

class CreateMappingRequest(BaseModel):
    spreadsheet_filename: str
    command_filename: str
    commands: List[str]

class MappingResponse(BaseModel):
    mapping_id: str
    spreadsheet_filename: str
    command_filename: str
    command_count: int
    created_at: str
    use_count: int
    is_active: bool

# PLACEHOLDER: SchemaRequest model removed
# This model was used for schema-related endpoints that have been removed
# New implementation will use different request models

class Controllers:
    spreadsheet_controller = None
    session_manager = None
    prompt_history = None
    mapping_manager = None
    PROMPT_FILE = None

controllers = Controllers()

def init_controllers(controller, manager, history, prompt_file):
    """Initialize controllers used by the endpoints"""
    controllers.spreadsheet_controller = controller
    controllers.session_manager = manager
    controllers.prompt_history = history
    controllers.mapping_manager = MappingManager()
    controllers.PROMPT_FILE = prompt_file
    os.makedirs(os.path.dirname(prompt_file), exist_ok=True)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager to initialize controllers and managers at FastAPI startup.
    """
    # Set up session manager and prompt history
    session_manager = SessionManager()
    prompt_folder = os.path.join("static", "assets", "prompts")
    prompt_file = os.path.join(prompt_folder, "prompts.txt")
    prompt_history = PromptHistory(prompt_folder)
    # Set up spreadsheet controller
    spreadsheet_controller = SpreadsheetController(session_manager)
    # Initialize controllers for endpoints
    init_controllers(
        spreadsheet_controller,
        session_manager,
        prompt_history,
        prompt_file
    )
    yield

app.router.lifespan_context = lifespan

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the main application page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/health", response_model=HealthResponse)
def health_check():
    """
    Health check endpoint
    
    Returns:
        HealthResponse: JSON response with health status
    """
    return HealthResponse(
        status="ok",
        version="1.0.0"
    )

@app.get("/api/security/status")
async def security_status(request: Request):
    """
    Security status endpoint (restricted access)
    """
    client_ip = get_client_ip(request)
    
    # Basic security statistics
    security_stats = {
        "security_manager": "active",
        "rate_limiting": {
            "tracked_ips": len(rate_limit_storage),
            "current_limits": {ip: len(requests) for ip, requests in rate_limit_storage.items()}
        },
        "environment": "development",
        "security_level": "medium"
    }
    
    return security_stats

@app.get("/api/security/alerts")
async def get_security_alerts(request: Request):
    """
    Get pending security alerts (basic implementation)
    """
    client_ip = get_client_ip(request)
    
    alerts = []  # Basic implementation
    return {"alerts": alerts, "count": len(alerts)}

@app.post("/upload", response_model=UploadResponse, dependencies=[Depends(rate_limit_dependency), Depends(validate_request_dependency)])
async def upload_file(request: Request, file: UploadFile = File(...)):
    """Handle spreadsheet file uploads with basic security validation."""
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    
    # Log access
    start_time = time.time()
    
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No selected file")
        
        # Basic filename validation
        if ".." in file.filename or "/" in file.filename or "\\" in file.filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        # Check file extension
        allowed_extensions = {'.xlsx', '.xls', '.csv', '.txt'}
        file_ext = os.path.splitext(file.filename.lower())[1]
        if file_ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail="File type not allowed")
        
        # Read file content for basic validation
        content = await file.read()
        
        # Basic file size check (50MB limit)
        max_size = 50 * 1024 * 1024  # 50MB
        if len(content) > max_size:
            raise HTTPException(status_code=400, detail="File too large")
        
        # Reset file position for the controller
        file.file.seek(0)
        
        # Pass the file directly to the controller which now handles FastAPI UploadFile
        session_id = controllers.spreadsheet_controller.upload_spreadsheet(file)
        
        # Check for existing mapping
        mapped_commands = controllers.mapping_manager.get_commands_for_spreadsheet(
            file.filename, content
        )
        
        response_data = {
            "success": True,
            "sessionId": session_id
        }
        
        # If mapping exists, include it in the response
        if mapped_commands:
            response_data["has_mapping"] = True
            response_data["mapped_commands"] = mapped_commands
            response_data["command_count"] = len(mapped_commands)
        else:
            response_data["has_mapping"] = False
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
        
    except ValueError as e:
        # Convert ValueError to HTTPException
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Other exceptions
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.get("/view/{session_id}")
def view_spreadsheet(session_id: str):
    """Get the spreadsheet data for viewing."""
    try:
        spreadsheet_view = controllers.spreadsheet_controller.view_spreadsheet(session_id)
        return spreadsheet_view
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/prompt_history/{session_id}", response_model=PromptHistoryResponse)
def prompt_history_route(session_id: str, index: int = 0):
    """
    Returns the nth previous prompt for the session.
    Query param: index (int, 0=most recent)
    Response: { "prompt": "..." } or { "prompt": null }
    """
    prompt = controllers.prompt_history.get(session_id, index)
    return PromptHistoryResponse(prompt=prompt)

@app.post("/process")
def process_command(request: CommandRequest):
    """Process a user command through the LLM."""
    try:
        # Append prompt to history file
        controllers.prompt_history.append(request.sessionId, request.command)
        # Use simple processing for regular AI commands (no advanced processing)
        spreadsheet_view = controllers.spreadsheet_controller.process_command(
            request.sessionId, request.command, use_advanced_processing=False
        )
        return spreadsheet_view
    except ScriptExecutionFailureException as e:
        # Special handling for script execution failures after debugging pipeline
        raise HTTPException(status_code=422, detail={
            "error": "SCRIPT_EXECUTION_FAILED",
            "message": f"Failed to understand and execute the command: '{e.command}'. Please rephrase your request and try again.",
            "command": e.command,
            "details": e.error_details
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/undo/{session_id}")
def undo_modification(session_id: str):
    """Undo the last modification."""
    try:
        spreadsheet_view = controllers.spreadsheet_controller.undo_modification(session_id)
        return spreadsheet_view
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/redo/{session_id}")
def redo_modification(session_id: str):
    """Redo a previously undone modification."""
    try:
        spreadsheet_view = controllers.spreadsheet_controller.redo_modification(session_id)
        return spreadsheet_view
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/download/{session_id}")
def download_spreadsheet(session_id: str, background_tasks: BackgroundTasks):
    """Download the modified spreadsheet."""
    try:
        # Get both file_path and original_filename
        file_path, original_filename = controllers.spreadsheet_controller.download_spreadsheet(session_id)
        
        # Schedule cleanup after download
        background_tasks.add_task(controllers.spreadsheet_controller.cleanup_session, session_id)
        
        # Use original filename for download
        return FileResponse(
            path=file_path,
            filename=original_filename,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/prompts")
def get_prompts():
    """Get saved prompts"""
    prompts = []
    if os.path.exists(controllers.PROMPT_FILE):
        with open(controllers.PROMPT_FILE, 'r', encoding='utf-8') as f:
            prompts = [line.strip() for line in f if line.strip()]
    return prompts

@app.post("/prompts")
def save_prompt(request: PromptRequest):
    """Save a prompt"""
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is empty")

    lock = threading.Lock()
    with lock:
        # Avoid duplicates, append only if not present
        prompts = []
        if os.path.exists(controllers.PROMPT_FILE):
            with open(controllers.PROMPT_FILE, 'r', encoding='utf-8') as f:
                prompts = [line.strip() for line in f if line.strip()]
        if prompt not in prompts:
            with open(controllers.PROMPT_FILE, 'a', encoding='utf-8') as f:
                f.write(prompt.replace('\n', ' ') + '\n')
    return {"success": True}


from fastapi import Request as FastAPIRequest

@app.delete("/prompts")
async def delete_prompt(request: FastAPIRequest):
    """
    Delete a prompt from the prompts file.
    Expects JSON: { "prompt": "..." }
    """
    data = await request.json()
    prompt_to_delete = data.get("prompt", "").strip()
    if not prompt_to_delete:
        raise HTTPException(status_code=400, detail="Prompt is empty")
    # Do not allow deleting predefined prompts
    predefined = {"Remove row", "Remove column", "Add row", "Add column"}
    if prompt_to_delete in predefined:
        raise HTTPException(status_code=403, detail="Cannot delete predefined prompt")
    lock = threading.Lock()
    with lock:
        if not os.path.exists(controllers.PROMPT_FILE):
            return {"success": False, "error": "Prompt file not found"}
        with open(controllers.PROMPT_FILE, 'r', encoding='utf-8') as f:
            prompts = [line.strip() for line in f if line.strip()]
        # Remove only the first occurrence
        try:
            prompts.remove(prompt_to_delete)
        except ValueError:
            pass
        with open(controllers.PROMPT_FILE, 'w', encoding='utf-8') as f:
            for p in prompts:
                f.write(p + '\n')
    return {"success": True}


# Add this new endpoint after your existing endpoints
@app.post("/table_changes")
def process_table_changes(request: TableChangesRequest):
    """Process changes made directly in the table."""
    try:
        spreadsheet_view = controllers.spreadsheet_controller.process_table_changes(
            request.sessionId, request.changes
        )
        return spreadsheet_view
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/update_schema")
def update_schema(request: dict):
    """
    Manual schema transformation - applies right spreadsheet structure to left spreadsheet
    without LLM processing. Uses the right spreadsheet as a template.
    """
    try:
        session_id = request.get('sessionId')
        right_data = request.get('rightSpreadsheetData', [])
        transform_left = request.get('transformLeft', False)
        
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID is required")
        
        if transform_left:
            # Apply the right spreadsheet structure to the left spreadsheet
            result = controllers.spreadsheet_controller.apply_manual_schema_transformation(
                session_id, right_data
            )
            return result
        else:
            # Just capture/validate the schema from right spreadsheet
            schema_info = controllers.spreadsheet_controller.capture_schema_structure(right_data)
            return {"success": True, "schema": schema_info, "message": "Schema structure captured successfully"}
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/transform_to_schema/{session_id}")
def transform_to_schema(session_id: str, request: dict):
    """
    Alias endpoint for manual schema transformation
    """
    try:
        right_data = request.get('rightSpreadsheetData', [])
        
        result = controllers.spreadsheet_controller.apply_manual_schema_transformation(
            session_id, right_data
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/upload_commands")
async def upload_command_file(
    file: UploadFile = File(...), 
    sessionId: str = None,
    request: FastAPIRequest = None
):
    """
    Upload a text file containing commands to execute sequentially.
    Each line in the file will be treated as a separate command.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
        
    if not file.filename.lower().endswith('.txt'):
        raise HTTPException(status_code=400, detail="Only .txt files are supported")
    
    # Get sessionId from form data if not provided as a parameter
    if not sessionId:
        form = await request.form()
        sessionId = form.get("sessionId")
        
    if not sessionId:
        raise HTTPException(status_code=400, detail="No session ID provided")
    
    # Check if session exists
    if not controllers.session_manager.session_exists(sessionId):
        raise HTTPException(status_code=404, detail=f"Session {sessionId} not found or expired")
    
    try:
        # Read all lines from the file
        content = await file.read()
        text_content = content.decode('utf-8')
        
        # Split by newlines and filter out empty lines
        commands = [line.strip() for line in text_content.split('\n') if line.strip()]
        
        return {
            "success": True,
            "commands": commands,
            "count": len(commands),
            "filename": file.filename
        }
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File encoding not supported. Please use UTF-8 encoded text files.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.post("/generate_algorithm")
async def generate_algorithm(request: Request):
    """Generate and execute a universal algorithm from an action plan"""
    try:
        data = await request.json()
        session_id = data.get('sessionId')
        action_plan = data.get('actionPlan')
        left_spreadsheet_data = data.get('leftSpreadsheetData')
        right_spreadsheet_data = data.get('rightSpreadsheetData')
        
        if not all([session_id, action_plan, left_spreadsheet_data, right_spreadsheet_data]):
            raise HTTPException(status_code=400, detail="Missing required parameters")
        
        # Generate and execute the universal algorithm
        result = controllers.spreadsheet_controller.generate_and_execute_algorithm(
            session_id, action_plan, left_spreadsheet_data, right_spreadsheet_data
        )
        
        return result
        
    except ScriptExecutionFailureException as e:
        # Special handling for script execution failures after debugging pipeline
        raise HTTPException(status_code=422, detail={
            "error": "SCRIPT_EXECUTION_FAILED",
            "message": f"Failed to understand and execute the algorithm: '{e.command}'. Please rephrase your action plan and try again.",
            "command": e.command,
            "details": e.error_details
        })
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/generate_schema_json/{session_id}")
def generate_schema_json(session_id: str):
    """
    Generate JSON schema representation of current spreadsheet
    """
    try:
        schema_json = controllers.spreadsheet_controller.generate_schema_json(session_id)
        return {"success": True, "schema": schema_json}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/validate_schema_compatibility/{session_id}")
def validate_schema_compatibility(session_id: str, request: dict):
    """
    Validate if current spreadsheet can be transformed to match target schema
    """
    try:
        right_data = request.get('rightSpreadsheetData', [])
        
        if not right_data:
            raise HTTPException(status_code=400, detail="Right spreadsheet data is required")
        
        compatibility = controllers.spreadsheet_controller.validate_schema_compatibility(
            session_id, right_data
        )
        return {"success": True, "compatibility": compatibility}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Script Reuse API Endpoints
@app.get("/script_reuse_stats")
def get_script_reuse_stats():
    """
    Get statistics about script reuse performance
    """
    try:
        stats = controllers.spreadsheet_controller.get_script_reuse_stats()
        return JSONResponse(content=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cleanup_script_reuse_data")
def cleanup_script_reuse_data(max_age_days: int = 30):
    """
    Clean up old script reuse data
    """
    try:
        cleanup_results = controllers.spreadsheet_controller.cleanup_script_reuse_data(max_age_days)
        return JSONResponse(content=cleanup_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/script_reuse_config")
def get_script_reuse_config():
    """
    Get current script reuse configuration
    """
    try:
        config = {
            'enabled': controllers.spreadsheet_controller.script_reuser.model is not None,
            'similarity_threshold': controllers.spreadsheet_controller.script_reuser.similarity_threshold,
            'model_name': 'all-MiniLM-L6-v2',
            'mapping_file': controllers.spreadsheet_controller.script_reuser.mapping_file
        }
        return JSONResponse(content=config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/script_reuse_config")
def update_script_reuse_config(config: dict):
    """
    Update script reuse configuration
    """
    try:
        if 'similarity_threshold' in config:
            threshold = float(config['similarity_threshold'])
            if 0.0 <= threshold <= 1.0:
                controllers.spreadsheet_controller.script_reuser.similarity_threshold = threshold
            else:
                raise ValueError("Similarity threshold must be between 0.0 and 1.0")
        
        return JSONResponse(content={"success": True, "message": "Configuration updated"})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/create_mapping")
async def create_mapping(request: CreateMappingRequest):
    """
    Create a mapping between a spreadsheet and command file
    """
    try:
        mapping_id = controllers.mapping_manager.create_mapping(
            spreadsheet_filename=request.spreadsheet_filename,
            command_filename=request.command_filename,
            commands=request.commands
        )
        
        return {
            "success": True,
            "mapping_id": mapping_id,
            "message": f"Mapping created successfully for '{request.spreadsheet_filename}'"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating mapping: {str(e)}")

@app.get("/mappings")
async def get_all_mappings():
    """
    Get all active mappings
    """
    try:
        mappings = controllers.mapping_manager.get_active_mappings()
        stats = controllers.mapping_manager.get_mapping_stats()
        
        return {
            "success": True,
            "mappings": mappings,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving mappings: {str(e)}")

@app.get("/mapping/{mapping_id}")
async def get_mapping(mapping_id: str):
    """
    Get a specific mapping by ID
    """
    try:
        mapping = controllers.mapping_manager.get_mapping_by_id(mapping_id)
        if not mapping:
            raise HTTPException(status_code=404, detail="Mapping not found")
        
        return {
            "success": True,
            "mapping": mapping
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving mapping: {str(e)}")

@app.put("/mapping/{mapping_id}")
async def update_mapping(mapping_id: str, request: Request):
    """
    Update a mapping
    """
    try:
        data = await request.json()
        updated = controllers.mapping_manager.update_mapping(mapping_id, **data)
        
        if not updated:
            raise HTTPException(status_code=404, detail="Mapping not found")
        
        return {
            "success": True,
            "message": "Mapping updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating mapping: {str(e)}")

@app.delete("/mapping/{mapping_id}")
async def delete_mapping(mapping_id: str):
    """
    Delete (deactivate) a mapping
    """
    try:
        deleted = controllers.mapping_manager.delete_mapping(mapping_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Mapping not found")
        
        return {
            "success": True,
            "message": "Mapping deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting mapping: {str(e)}")

@app.get("/check_mapping/{spreadsheet_filename}")
async def check_mapping(spreadsheet_filename: str):
    """
    Check if a mapping exists for a spreadsheet
    """
    try:
        mapping = controllers.mapping_manager.find_mapping_by_spreadsheet(spreadsheet_filename)
        conflicts = controllers.mapping_manager.check_spreadsheet_conflicts(spreadsheet_filename)
        
        if mapping:
            return {
                "success": True,
                "has_mapping": True,
                "mapping": mapping,
                "conflicts": conflicts
            }
        else:
            return {
                "success": True,
                "has_mapping": False,
                "mapping": None,
                "conflicts": conflicts
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking mapping: {str(e)}")

@app.get("/token_usage_stats")
async def get_token_usage_stats():
    """
    Get comprehensive token usage statistics for the dashboard
    """
    try:
        from src.llm.token_manager import token_manager
        import random
        from datetime import datetime, timedelta
        
        # Get real dashboard statistics
        dashboard_stats = token_manager.get_dashboard_stats()
        batch_history = token_manager.get_batch_history()
        
        # Generate timeline data from batch history and current session
        timeline_data = []
        if batch_history:
            # Use real batch history for timeline
            for batch in batch_history[-7:]:  # Last 7 batches
                timeline_data.append({
                    "date": batch.get('timestamp', datetime.now().isoformat())[:10],
                    "tokens": batch.get('total_tokens', 0),
                    "cost": batch.get('estimated_cost', 0)
                })
        
        # Process model usage data - only real data
        model_usage_data = []
        for model, usage in dashboard_stats.get('model_usage', {}).items():
            # Shorten model names for display
            short_name = model.replace('gemini-', '').replace('-preview', '').replace('-06-17', '')
            model_usage_data.append({
                "name": short_name[:15],  # Limit length
                "usage": usage
            })
        
        # Process recent activities from batch history
        recent_activities = []
        recent_batches = dashboard_stats.get('recent_batches', [])
        
        if recent_batches:
            print(f"📊 Found {len(recent_batches)} batch sessions in history")
            # Use only real batch history data - no sample data
            for i, batch in enumerate(recent_batches[-50:]):  # Last 50 batches
                batch_number = len(recent_batches) - len(recent_batches[-50:]) + i + 1
                recent_activities.append({
                    "batchName": f"Batch Command #{batch_number}",
                    "timestamp": batch.get('timestamp', datetime.now().isoformat()),
                    "commandCount": batch.get('commands', 0),
                    "tokens": batch.get('total_tokens', 0),
                    "cost": batch.get('estimated_cost', 0),
                    "model": batch.get('models_used', ['Unknown'])[0] if batch.get('models_used') else 'Unknown'
                })
            print(f"📋 Returning {len(recent_activities)} recent activities from persistent storage")
        else:
            print("📭 No batch history found in persistent storage - returning empty recent activities")
        
        # No sample data - let frontend handle empty state
        
        # Calculate trends (simple calculation based on recent vs older data)
        tokens_trend = 0
        cost_trend = 0
        batch_trend = 0
        avg_trend = 0
        
        if len(batch_history) >= 2:
            recent_tokens = sum(batch.get('total_tokens', 0) for batch in batch_history[-3:])
            older_tokens = sum(batch.get('total_tokens', 0) for batch in batch_history[-6:-3])
            if older_tokens > 0:
                tokens_trend = int(((recent_tokens - older_tokens) / older_tokens) * 100)
            
            recent_cost = sum(batch.get('estimated_cost', 0) for batch in batch_history[-3:])
            older_cost = sum(batch.get('estimated_cost', 0) for batch in batch_history[-6:-3])
            if older_cost > 0:
                cost_trend = int(((recent_cost - older_cost) / older_cost) * 100)
        
        response_data = {
            "summary": {
                "totalTokens": int(dashboard_stats.get('total_tokens', 0)),
                "totalCost": dashboard_stats.get('total_cost', 0),
                "totalBatchCommands": dashboard_stats.get('total_batch_commands', 0),
                "avgTokensPerCommand": int(dashboard_stats.get('avg_tokens_per_command', 0)),
                "tokensTrend": tokens_trend,
                "costTrend": cost_trend,
                "batchTrend": batch_trend,
                "avgTrend": avg_trend
            },
            "tokenDistribution": {
                "inputTokens": dashboard_stats.get('total_input_tokens', 0),
                "outputTokens": dashboard_stats.get('total_output_tokens', 0)
            },
            "modelUsage": {
                "models": model_usage_data if model_usage_data else []
            },
            "costBreakdown": {
                "categories": [
                    {"name": "Input", "cost": dashboard_stats.get('total_cost', 0) * 0.3},
                    {"name": "Output", "cost": dashboard_stats.get('total_cost', 0) * 0.7}
                ]
            },
            "usageTimeline": {
                "timeline": timeline_data if dashboard_stats.get('total_tokens', 0) > 0 else []
            },
            "recentActivity": recent_activities
        }
        
        print(f"🔍 Final response data - Recent activities: {len(recent_activities)} items")
        if recent_activities:
            print(f"📝 Sample activity: {recent_activities[0]}")
        
        return response_data
        
    except Exception as e:
        print(f"Error getting token usage stats: {e}")
        import traceback
        traceback.print_exc()
        # Return empty data structure in case of error
        return {
            "summary": {
                "totalTokens": 0,
                "totalCost": 0,
                "totalBatchCommands": 0,
                "avgTokensPerCommand": 0,
                "tokensTrend": 0,
                "costTrend": 0,
                "batchTrend": 0,
                "avgTrend": 0
            },
            "tokenDistribution": {
                "inputTokens": 0,
                "outputTokens": 0
            },
            "modelUsage": {
                "models": []
            },
            "costBreakdown": {
                "categories": []
            },
            "usageTimeline": {
                "timeline": []
            },
            "recentActivity": []
        }

# ========== Cache Management Endpoints ==========

@app.delete("/cache/clear/uploads")
async def clear_uploads():
    """Clear all uploaded spreadsheet files"""
    try:
        uploads_dir = BASE_DIR / "static" / "uploads"
        if uploads_dir.exists():
            # Get all files except .gitkeep
            files_to_delete = [f for f in uploads_dir.iterdir() if f.is_file() and f.name != '.gitkeep']
            
            for file_path in files_to_delete:
                try:
                    file_path.unlink()
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")
            
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": f"Deleted {len(files_to_delete)} uploaded files",
                    "deleted_count": len(files_to_delete)
                }
            )
        else:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "Uploads directory does not exist",
                    "deleted_count": 0
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing uploads: {str(e)}")

@app.delete("/cache/clear/downloads")
async def clear_downloads():
    """Clear all downloaded files"""
    try:
        downloads_dir = BASE_DIR / "static" / "downloads"
        if downloads_dir.exists():
            # Get all files except .gitkeep
            files_to_delete = [f for f in downloads_dir.iterdir() if f.is_file() and f.name != '.gitkeep']
            
            for file_path in files_to_delete:
                try:
                    file_path.unlink()
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")
            
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": f"Deleted {len(files_to_delete)} downloaded files",
                    "deleted_count": len(files_to_delete)
                }
            )
        else:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "Downloads directory does not exist",
                    "deleted_count": 0
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing downloads: {str(e)}")

@app.delete("/cache/clear/json")
async def clear_json_data():
    """Clear all JSON configuration files"""
    try:
        json_dir = BASE_DIR / "static" / "json"
        deleted_count = 0
        
        if json_dir.exists():
            # Get all JSON files except .gitkeep
            files_to_delete = [f for f in json_dir.iterdir() if f.is_file() and f.suffix == '.json']
            
            for file_path in files_to_delete:
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Deleted {deleted_count} JSON files",
                "deleted_count": deleted_count
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing JSON data: {str(e)}")

@app.delete("/cache/clear/prompts")
async def clear_prompts():
    """Clear prompt history files and content of prompts.txt"""
    try:
        prompts_dir = BASE_DIR / "static" / "assets" / "prompts"
        deleted_count = 0
        
        if prompts_dir.exists():
            # Delete all .txt files except prompts.txt
            files_to_delete = [f for f in prompts_dir.iterdir() 
                             if f.is_file() and f.suffix == '.txt' and f.name != 'prompts.txt']
            
            for file_path in files_to_delete:
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")
            
            # Clear content of prompts.txt if it exists
            prompts_file = prompts_dir / "prompts.txt"
            if prompts_file.exists():
                try:
                    with open(prompts_file, 'w', encoding='utf-8') as f:
                        f.write('')  # Clear the file content
                except Exception as e:
                    print(f"Error clearing prompts.txt: {e}")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Deleted {deleted_count} prompt files and cleared prompts.txt",
                "deleted_count": deleted_count
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing prompts: {str(e)}")

@app.delete("/cache/clear/scripts")
async def clear_scripts():
    """Clear all generated Python scripts"""
    try:
        scripts_dir = BASE_DIR / "src" / "script"
        deleted_count = 0
        
        if scripts_dir.exists():
            # Get all Python files except .gitkeep
            files_to_delete = [f for f in scripts_dir.iterdir() 
                             if f.is_file() and f.suffix == '.py']
            
            for file_path in files_to_delete:
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Deleted {deleted_count} Python script files",
                "deleted_count": deleted_count
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing scripts: {str(e)}")

@app.delete("/cache/clear/mappings")
async def clear_mappings():
    """Clear all mapping configuration files"""
    try:
        data_mappings_dir = BASE_DIR / "src" / "mappings" / "data"
        script_mappings_dir = BASE_DIR / "src" / "mappings" / "script"
        deleted_count = 0
        
        # Clear data mappings
        if data_mappings_dir.exists():
            files_to_delete = [f for f in data_mappings_dir.iterdir() 
                             if f.is_file() and f.suffix == '.json']
            
            for file_path in files_to_delete:
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")
        
        # Clear script mappings
        if script_mappings_dir.exists():
            files_to_delete = [f for f in script_mappings_dir.iterdir() 
                             if f.is_file() and f.suffix == '.json']
            
            for file_path in files_to_delete:
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Deleted {deleted_count} mapping configuration files",
                "deleted_count": deleted_count
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing mappings: {str(e)}")

@app.delete("/cache/clear/all")
async def clear_all_cache():
    """Clear all cache data - uploads, downloads, JSON, prompts, scripts, and mappings"""
    try:
        total_deleted = 0
        results = []
        
        # Clear uploads
        try:
            response = await clear_uploads()
            if response.status_code == 200:
                content = json.loads(response.body)
                total_deleted += content.get("deleted_count", 0)
                results.append(f"Uploads: {content.get('deleted_count', 0)} files")
        except Exception as e:
            results.append(f"Uploads: Error - {str(e)}")
        
        # Clear downloads
        try:
            response = await clear_downloads()
            if response.status_code == 200:
                content = json.loads(response.body)
                total_deleted += content.get("deleted_count", 0)
                results.append(f"Downloads: {content.get('deleted_count', 0)} files")
        except Exception as e:
            results.append(f"Downloads: Error - {str(e)}")
        
        # Clear JSON data
        try:
            response = await clear_json_data()
            if response.status_code == 200:
                content = json.loads(response.body)
                total_deleted += content.get("deleted_count", 0)
                results.append(f"JSON: {content.get('deleted_count', 0)} files")
        except Exception as e:
            results.append(f"JSON: Error - {str(e)}")
        
        # Clear prompts
        try:
            response = await clear_prompts()
            if response.status_code == 200:
                content = json.loads(response.body)
                total_deleted += content.get("deleted_count", 0)
                results.append(f"Prompts: {content.get('deleted_count', 0)} files")
        except Exception as e:
            results.append(f"Prompts: Error - {str(e)}")
        
        # Clear scripts
        try:
            response = await clear_scripts()
            if response.status_code == 200:
                content = json.loads(response.body)
                total_deleted += content.get("deleted_count", 0)
                results.append(f"Scripts: {content.get('deleted_count', 0)} files")
        except Exception as e:
            results.append(f"Scripts: Error - {str(e)}")
        
        # Clear mappings
        try:
            response = await clear_mappings()
            if response.status_code == 200:
                content = json.loads(response.body)
                total_deleted += content.get("deleted_count", 0)
                results.append(f"Mappings: {content.get('deleted_count', 0)} files")
        except Exception as e:
            results.append(f"Mappings: Error - {str(e)}")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"All clear completed. Total files deleted: {total_deleted}",
                "total_deleted": total_deleted,
                "details": results
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing all clear: {str(e)}")

@app.get("/usermanual", response_class=HTMLResponse)
async def user_manual(request: Request):
    """
    Serve the user manual page
    """
    return templates.TemplateResponse("instructions.html", {"request": request})
