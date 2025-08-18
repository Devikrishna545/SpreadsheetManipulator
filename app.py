"""
Main application entry point
----------------------------
Initializes controllers and launches the FastAPI application using Uvicorn
"""

import os
import argparse
import uvicorn
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import from the correct paths
from src.api.endpoints import init_controllers
from src.controller.spreadsheet_controller import SpreadsheetController  
from src.model.session_manager import SessionManager 
from src.model.prompt_history import PromptHistory

# Load environment variables from .env file
load_dotenv()

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Launch the Spreadsheet Editor API")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to")
    # Only add --reload if not frozen
    if not getattr(sys, 'frozen', False):
        parser.add_argument("--reload", action="store_true", default=True, help="Enable auto-reload for development [default: True]")
    parser.add_argument("--debug", action="store_true", default=False, help="Enable debug mode [default: False]")
    return parser.parse_args()

def main():
    """Main entry point for the application"""
    args = parse_args()
    
    # Initialize controllers in the correct order
    # First, create the session_manager
    session_manager = SessionManager()
    
    # Create prompt history with the required folder parameter
    prompt_history_folder = os.path.join('static', 'json')
    prompt_history = PromptHistory(prompt_history_folder)
    
    # Then, create the SpreadsheetController with the session_manager
    spreadsheet_controller = SpreadsheetController(session_manager)
    
    # Define the path for storing saved prompts
    prompt_file = os.path.join(os.path.expanduser("~"), ".editor", "prompts.txt")
    os.makedirs(os.path.dirname(prompt_file), exist_ok=True)
    
    # Initialize the controllers in the FastAPI app
    init_controllers(spreadsheet_controller, session_manager, prompt_history, prompt_file)
    
    # Print startup message
    print(f"Starting server at http://{args.host}:{args.port}")
    print("Press CTRL+C to quit")
    
    # Run the app with Uvicorn
    uvicorn_run_kwargs = {
        "app": "src.api.endpoints:app",
        "host": args.host,
        "port": args.port,
    }
    # Only enable reload if not frozen
    if not getattr(sys, 'frozen', False):
        uvicorn_run_kwargs["reload"] = getattr(args, "reload", True)
        # Exclude the script directory from being watched to prevent reloads
        # when new scripts are generated during execution
        uvicorn_run_kwargs["reload_excludes"] = [
            "src/script/*",
            "src/script/**/*",
            "static/uploads/*",
            "static/downloads/*",
            "static/json/*",
            "__pycache__/*",
            "**/__pycache__/*",
            "*.pyc",
            "**/*.pyc"
        ]

    uvicorn.run(**uvicorn_run_kwargs)

if __name__ == "__main__":
    main()
