"""
Spreadsheet Controller module
---------------------------
Main controller for spreadsheet operations
"""

import os
import uuid
import pandas as pd
from werkzeug.datastructures import FileStorage
from typing import Dict, Any
from src.model.session_manager import SessionManager
from src.model.spreadsheet import Spreadsheet
from src.model.modification_history import ModificationHistory
from src.llm.llm_service import LLMService
from src.controller.script_executor import ScriptExecutor
from src.controller.file_manager import FileManager


class SpreadsheetController:
    """
    Controller for spreadsheet operations
    """
    
    def __init__(self, session_manager: SessionManager):
        """
        Initialize controller

        Args:
            session_manager: Session manager instance
        """
        self.session_manager = session_manager
        self.llm_service = LLMService()
        self.script_dir = os.path.join('src', 'script')
        self.script_executor = ScriptExecutor(script_dir=self.script_dir)
        self.file_manager = FileManager(
            upload_dir=os.path.join('static', 'uploads'),
            download_dir=os.path.join('static', 'downloads'),
            json_dir=os.path.join('static', 'json')
        )
    
    def upload_spreadsheet(self, file: FileStorage) -> str:
        """
        Upload and process a spreadsheet file

        Args:
            file: The uploaded file

        Returns:
            str: Session ID for the new session
        """
        # Validate file
        if file.filename is None:
            raise ValueError("No filename provided")
            
        if not self.file_manager.validate_file_type(file.filename):
            raise ValueError("Invalid file format. Supported formats: xlsx, xls, csv")
        
        # Save file
        file_id = str(uuid.uuid4())
        file_path = self.file_manager.save_uploaded_file(file, file_id)
        
        # Parse file
        df = None
        if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
            df = pd.read_excel(file_path)
        elif file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        
        # Check if df is None
        if df is None:
            raise ValueError(f"Unsupported file format: {file_path}")
            
        # Create spreadsheet object
        spreadsheet = Spreadsheet(file_id, file.filename, df, file_path)
        
        # Create session
        session_id = self.session_manager.create_session()
        session = self.session_manager.get_session(session_id)
        
        # Check if session exists
        if not session:
            raise ValueError("Failed to create or retrieve session")
        
        # Create modification history and add initial state
        history = ModificationHistory()
        history.add_state(spreadsheet)
        
        # Update session
        session.update_spreadsheet(spreadsheet)
        session.set_modification_history(history)
        
        return session_id
    
    def view_spreadsheet(self, session_id: str) -> Dict[str, Any]:
        """
        Get spreadsheet view data

        Args:
            session_id: Session ID

        Returns:
            Dict[str, Any]: Spreadsheet view data
        """
        # Get session
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found or expired")
        
        # Get current spreadsheet state
        history = session.get_modification_history()
        if not history:
            raise ValueError("Modification history not found for this session")
            
        spreadsheet = history.get_current_state()
        if not spreadsheet:
            raise ValueError("No spreadsheet data found")
        
        # Prepare view data
        data = spreadsheet.get_data().replace({float('nan'): None}).values.tolist()
        headers = spreadsheet.get_data().columns.tolist()
        
        return {
            'data': data,
            'headers': headers,
            'metadata': spreadsheet.get_metadata(),
            'can_undo': history.can_undo(),
            'can_redo': history.can_redo(),
            'modified_cells': []  # No cells modified in view operation
        }
    
    def process_command(self, session_id: str, command: str) -> Dict[str, Any]:
        """
        Process a user command through LLM

        Args:
            session_id: Session ID
            command: User command text

        Returns:
            Dict[str, Any]: Updated spreadsheet view data
        """
        # Get session
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found or expired")
        
        # Get current spreadsheet state
        history = session.get_modification_history()
        if not history:
            raise ValueError("Modification history not found for this session")
            
        current_spreadsheet = history.get_current_state()
        if not current_spreadsheet:
            raise ValueError("No spreadsheet data found")
        
        # Convert spreadsheet to JSON format for LLM and save a copy to static/json
        spreadsheet_json = current_spreadsheet.to_json(save_to_file=True, file_manager=self.file_manager)
        
        # Generate script using LLM
        script = self.llm_service.generate_script(spreadsheet_json, command)
        
        # Store generated script
        session.set_generated_script(script)
          # Execute script on spreadsheet data
        new_df, modified_cells = self.script_executor.execute_script(
            script, 
            current_spreadsheet.get_data(),
            file_manager=self.file_manager
        )
        
        # Create new spreadsheet state
        new_spreadsheet = Spreadsheet(
            current_spreadsheet.file_id,
            current_spreadsheet.original_filename,
            new_df
        )
        
        # Add to history
        history.add_state(new_spreadsheet)
        
        # Update session spreadsheet
        session.update_spreadsheet(new_spreadsheet)
        
        # Prepare view data
        data = new_df.replace({float('nan'): None}).values.tolist()
        headers = new_df.columns.tolist()
        
        return {
            'data': data,
            'headers': headers,
            'metadata': new_spreadsheet.get_metadata(),
            'can_undo': history.can_undo(),
            'can_redo': history.can_redo(),
            'modified_cells': modified_cells
        }
    
    def undo_modification(self, session_id: str) -> Dict[str, Any]:
        """
        Undo the last modification

        Args:
            session_id: Session ID

        Returns:
            Dict[str, Any]: Previous spreadsheet state
        """
        # Get session
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found or expired")
        
        # Get history and undo
        history = session.get_modification_history()
        if not history:
            raise ValueError("No modification history found")
        previous_spreadsheet = history.undo()
        
        if not previous_spreadsheet:
            raise ValueError("Nothing to undo")
        
        # Update session
        session.update_spreadsheet(previous_spreadsheet)
        
        # Prepare view data
        df = previous_spreadsheet.get_data()
        data = df.replace({float('nan'): None}).values.tolist()
        headers = df.columns.tolist()
        
        return {
            'data': data,
            'headers': headers,
            'metadata': previous_spreadsheet.get_metadata(),
            'can_undo': history.can_undo(),
            'can_redo': history.can_redo(),
            'modified_cells': []  # No specific cells to highlight in undo
        }
    
    def redo_modification(self, session_id: str) -> Dict[str, Any]:
        """
        Redo a previously undone modification

        Args:
            session_id: Session ID

        Returns:
            Dict[str, Any]: Next spreadsheet state
        """
        # Get session
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found or expired")
        
        # Get history and redo
        history = session.get_modification_history()
        if not history:
            raise ValueError("No modification history found")
        next_spreadsheet = history.redo()
        
        if not next_spreadsheet:
            raise ValueError("Nothing to redo")
        
        # Update session
        session.update_spreadsheet(next_spreadsheet)
        
        # Prepare view data
        df = next_spreadsheet.get_data()
        data = df.replace({float('nan'): None}).values.tolist()
        headers = df.columns.tolist()
        
        # Since we've already verified history is not None, we can safely call these methods
        return {
            'data': data,
            'headers': headers,
            'metadata': next_spreadsheet.get_metadata(),
            'can_undo': history.can_undo(),
            'can_redo': history.can_redo(),
            'modified_cells': []  # No specific cells to highlight in redo
        }
    
    def download_spreadsheet(self, session_id: str) -> tuple:
        """
        Generate a downloadable spreadsheet file

        Args:
            session_id: Session ID

        Returns:
            tuple: (Path to the downloadable file, Original filename)
        """
        # Get session
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found or expired")
        
        # Get current spreadsheet
        history = session.get_modification_history()
        if not history:
            raise ValueError("No modification history found")
        spreadsheet = history.get_current_state()
        if not spreadsheet:
            raise ValueError("No spreadsheet data found")
        
        # Determine output format based on original file
        original_ext = os.path.splitext(spreadsheet.original_filename)[1].lower()
        format_type = 'xlsx' if original_ext in ['.xlsx', '.xls'] else 'csv'
        
        # Save to download directory
        download_path = spreadsheet.save(self.file_manager.download_dir, format_type)
        
        # Return both the file path and the original filename
        return download_path, spreadsheet.original_filename
    
    def cleanup_session(self, session_id: str) -> None:
        """
        Clean up a session and its resources

        Args:
            session_id: Session ID
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            return
        
        # Get spreadsheet for file cleanup
        history = session.get_modification_history()
        spreadsheet = history.get_current_state() if history and hasattr(history, 'get_current_state') else None
        
        # Get associated script if available
        generated_script = session.get_generated_script()
        
        if spreadsheet:
            # Clean up files
            original_file = spreadsheet.file_path
            if original_file and os.path.exists(original_file):
                try:
                    os.remove(original_file)
                except (PermissionError, OSError) as e:
                    print(f"Warning: Could not delete file {original_file}: {e}")
            
            # Remove download files (they're temporary)
            file_id = spreadsheet.file_id
            for format_type in ['xlsx', 'csv']:
                download_path = os.path.join(self.file_manager.download_dir, f"{file_id}.{format_type}")
                if os.path.exists(download_path):
                    try:
                        os.remove(download_path)
                    except (PermissionError, OSError) as e:
                        print(f"Warning: Could not delete file {download_path}: {e}")
        
        # Remove session
        self.session_manager.remove_session(session_id)
