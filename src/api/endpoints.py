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

# Update the SchemaRequest model to include the new fields
class SchemaRequest(BaseModel):
    sessionId: str
    rightSpreadsheetData: List[Dict[str, Any]]
    columnNames: Optional[List[str]] = None
    useFirstRowAsHeader: Optional[bool] = False
    transformLeft: bool = False

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
        spreadsheet_view = controllers.spreadsheet_controller.process_command(
            request.sessionId, request.command
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

# Add these new endpoints after the existing endpoints
@app.post("/update_schema")
def update_schema(request: SchemaRequest):
    """Update the schema based on the right spreadsheet data."""
    try:
        session_id = request.sessionId
        
        # Check if session exists
        if not controllers.session_manager.session_exists(session_id):
            raise ValueError(f"Session {session_id} not found")
        
        # Convert right spreadsheet data to DataFrame with proper handling of headers
        if request.columnNames:
            # Use provided column names
            right_df = pd.DataFrame(request.rightSpreadsheetData)
            
            # If we're using custom column names, ensure they're properly set
            if len(right_df.columns) == len(request.columnNames):
                right_df.columns = request.columnNames
        else:
            # No column names provided, just use the data as is
            right_df = pd.DataFrame(request.rightSpreadsheetData)
        
        # Generate schema from right spreadsheet
        schema = controllers.spreadsheet_controller.get_schema_from_df(right_df)
        
        # Store the schema and data in the session
        controllers.session_manager.update_session_data(
            session_id, 
            {
                'target_schema': schema,
                'right_df': right_df.to_dict(),
                'column_names': request.columnNames,
                'use_first_row_as_header': request.useFirstRowAsHeader
            }
        )
        
        # If transformLeft is true, also generate and apply transformation
        if request.transformLeft:
            return transform_to_schema(session_id)
        
        return {"success": True, "schema": schema}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/transform_to_schema/{session_id}")
def transform_to_schema(session_id: str):
    """Transform the left spreadsheet to match the right spreadsheet schema."""
    try:
        # Check if session exists
        if not controllers.session_manager.session_exists(session_id):
            raise ValueError(f"Session {session_id} not found")
        
        # Get session data
        session_data = controllers.session_manager.get_session_data(session_id)
        
        if 'target_schema' not in session_data:
            raise ValueError("No target schema found. Please update the right spreadsheet first.")
        
        # Get the left spreadsheet data
        left_df = controllers.spreadsheet_controller.get_spreadsheet_df(session_id)
        
        # Get the right spreadsheet data
        right_df = pd.DataFrame.from_dict(session_data['right_df'])
        
        # Generate transformation prompt
        transformation_prompt = controllers.spreadsheet_controller.generate_transformation_prompt(
            left_df, right_df
        )
        
        # Process the transformation command
        spreadsheet_view = controllers.spreadsheet_controller.process_command(
            session_id, transformation_prompt
        )
        
        # Ensure the response includes a success key
        if isinstance(spreadsheet_view, dict) and 'error' not in spreadsheet_view:
            spreadsheet_view['success'] = True
        
        return spreadsheet_view
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in transform_to_schema: {str(e)}\n{error_details}")
        return {"success": False, "error": str(e), "details": error_details}
