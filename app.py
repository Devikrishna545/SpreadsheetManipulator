"""
Main application entry point
----------------------------
Initializes controllers and launches the FastAPI application using Uvicorn
"""

# TO DO
# =======
# Add keyboard shortcuts for common actions ✅
# Design beautiful modern UI ✅
# Test app with various spreadsheet formats ✅
# Test app with real users
# Add predefined prompts for common tasks
# Make the "Ready" text to have a square border with rounded edges around it to match the design of the rest of the edges and borders of other elements within the app
# Shift the "Ready" text to the left a little, to mathch the gap between the right edge of the page and the right edge of the "AI Command Interface" and the "Spreadsheet Data" sections
# Change the icon of the "Auto Editor" text, to be a circular spinning gear icon, not a spreadsheet icon
# Centralise the "Auto Editor" text and its icon in the header bar area
# Add favicon ✅
# Add column and row header highlighting to form a cell, when handsonTable selection is over that call.
# Enter button should use an enter icon, not a pencil icon
# Create another HTML page with a well formated usermanual of the app, with gifs. (The new HTML page should use same design as the index.html page). Add all error messages, and how to resolve them (from a user perspective)
# Add command for entering a new command (CTRL+I) 🔁
# Add keyboard support for viewing saved prompts (CTRL+SHIFT+P) 🔁
# Add keyboard shortcuts for saving prompts (CTRL+SHIFT+S) 🔁
# Add a save button to save current text in input text box within a prompt file (static/assets/prompts/prompts.txt) ✅
# Add a delete button to remove saved prompts from within the prompt modal (static/assets/prompts/prompts.txt) 🔁
# Add escape to remove focus from input field ✅
# Increase input text box height to be above save and view prompts buttons 🔁
# Increase the background blur percentage of the view prompts modal to 70% 🔁
# Add footer with copyright information
# Add light/dark mode toggle (dark mode by default). Modes pessist across page refresh and app restarts 
# Add support for tagging rows and columns with pop-up suggestions called using the hash-tag
# Remove particle-mouse interaction, when there is an element between the mouse and the particles (if the z-index of the element is lower than z-index of the particles stop the mouse-particle interaction).
# Add option to view previous prompts with arrow up/down keys 🔁
# Add option to read spreadsheet from workbook file, currently only supports reading from single file.
# The top row should not be column headers from spreadsheet, but rather column letters (A, B, C, etc.) as in excel. 🔁
# Add button on right side of the maximize/restore spreadsheet view, the button should open a split view of spreadsheet with editing mode on the right side, and visual editing enabled on the left side, where user can edit the spreadsheet in a visual way 🔁 
# Add visual programming option from frontend where user can create new spreadsheet json format on frontend and ask AI to generate script for applying it to the spreadsheet 🔁
# Modify system to use default python script, if prompt operation becomes complex (pandas operation requires more than 2 steps).
# Add auto code executor and interpreter to test script from LLM and ask LLM to regenerate the script, if test is unsuccessful. This will help reduce number of errors cuased by complex prompts requiring multiple operations.
# This cycle should occur 3 times, after 3rd trial, system should breakout and show user error (Failed to generate script for set of instructions).

import os
import argparse
import uvicorn
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import from the correct paths
from src.api.endpoints import init_controllers
from src.controller.spreadsheet_controller import SpreadsheetController  
from src.model.session_manager import SessionManager 
from src.model.prompt_history import PromptHistory

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Launch the Spreadsheet Editor API")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to")
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
    uvicorn.run(
        "src.api.endpoints:app", 
        host=args.host, 
        port=args.port,
        reload=args.reload
    )

if __name__ == "__main__":
    main()
