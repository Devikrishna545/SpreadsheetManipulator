"""
API Endpoints module
-----------------
Defines RESTful API endpoints for the application using FastAPI
"""

import os
import threading
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel
import pathlib
import json
import pandas as pd
from src.controller.spreadsheet_controller import SpreadsheetController
from src.model.session_manager import SessionManager
from src.model.prompt_history import PromptHistory

# Create FastAPI app
app = FastAPI()

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

class ErrorResponse(BaseModel):
    error: str

class PromptHistoryResponse(BaseModel):
    prompt: Optional[str] = None

# Add this new model class after your existing models
class TableChangesRequest(BaseModel):
    sessionId: str
    changes: List[Dict[str, Any]]

# PLACEHOLDER: SchemaRequest model removed
# This model was used for schema-related endpoints that have been removed
# New implementation will use different request models

# Dependency for controllers
class Controllers:
    spreadsheet_controller = None
    session_manager = None
    prompt_history = None
    PROMPT_FILE = None

controllers = Controllers()

def init_controllers(controller, manager, history, prompt_file):
    """Initialize controllers used by the endpoints"""
    controllers.spreadsheet_controller = controller
    controllers.session_manager = manager
    controllers.prompt_history = history
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
        version="0.1.0"
    )

@app.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Handle spreadsheet file uploads."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No selected file")
    
    try:
        # Pass the file directly to the controller which now handles FastAPI UploadFile
        session_id = controllers.spreadsheet_controller.upload_spreadsheet(file)
        
        return UploadResponse(
            success=True,
            sessionId=session_id
        )
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
            "count": len(commands)
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
