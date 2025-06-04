"""
Spreadsheet Controller module
---------------------------
Main controller for spreadsheet operations
"""

import os
import uuid
import pandas as pd
from werkzeug.datastructures import FileStorage
from typing import Dict, Any, List
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
        
        # Prepare view data with datetime handling
        df_copy = spreadsheet.get_data().copy()
        
        # Convert datetime columns to strings for JSON serialization
        for col in df_copy.columns:
            if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
                df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
        
        # Always return data as a 2D array (list of lists), ignore headers
        data = df_copy.replace({float('nan'): None}).values.tolist()
        col_count = len(df_copy.columns)
        # Do not return headers at all
        # headers = df_copy.columns.tolist()
        
        return {
            'data': data,
            # 'headers': headers,  # REMOVE THIS LINE
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
        
        # Prepare view data with datetime handling
        df_copy = new_df.copy()
        
        # Convert datetime columns to strings for JSON serialization
        for col in df_copy.columns:
            if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
                df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
        
        data = df_copy.replace({float('nan'): None}).values.tolist()
        # Do not return headers at all
        # headers = df_copy.columns.tolist()
        
        return {
            'data': data,
            # 'headers': headers,  # REMOVE THIS LINE
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
        
        # Prepare view data with datetime handling
        df = previous_spreadsheet.get_data()
        df_copy = df.copy()
        
        # Convert datetime columns to strings for JSON serialization
        for col in df_copy.columns:
            if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
                df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
        
        data = df_copy.replace({float('nan'): None}).values.tolist()
        # Do not return headers at all
        # headers = df_copy.columns.tolist()
        
        return {
            'data': data,
            # 'headers': headers,  # REMOVE THIS LINE
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
        
        # Prepare view data with datetime handling
        df = next_spreadsheet.get_data()
        df_copy = df.copy()
        
        # Convert datetime columns to strings for JSON serialization
        for col in df_copy.columns:
            if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
                df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
        
        data = df_copy.replace({float('nan'): None}).values.tolist()
        # Do not return headers at all
        # headers = df_copy.columns.tolist()
        
        # Since we've already verified history is not None, we can safely call these methods
        return {
            'data': data,
            # 'headers': headers,  # REMOVE THIS LINE
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
            tuple: (Path to the downloadable file, original filename)
        """
        # Get session
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found or expired")
        
        # Get current spreadsheet state
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
    
    def process_table_changes(self, session_id: str, changes: list) -> dict:
        """
        Apply direct table changes (cell edits, row/col add/remove) and update history.

        Args:
            session_id: Session ID
            changes: List of change dicts from the frontend

        Returns:
            Dict[str, Any]: Updated spreadsheet view data
        """
        import pandas as pd

        # Get session and current spreadsheet
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found or expired")

        history = session.get_modification_history()
        if not history:
            raise ValueError("Modification history not found for this session")

        spreadsheet = history.get_current_state()
        if not spreadsheet:
            raise ValueError("No spreadsheet data found")

        df = spreadsheet.get_data().copy()
        modified_cells = []

        for change in changes:
            if change.get('type') == 'cell':
                for cell in change.get('changes', []):
                    row = cell['row']
                    col = cell['col']
                    old_value = cell.get('oldValue')
                    new_value = cell.get('newValue')
                    # Only update if value actually changed
                    if row < 0 or col < 0 or row >= len(df.index) or col >= len(df.columns):
                        continue
                    col_name = df.columns[col]
                    if pd.isna(df.iloc[row, col]) and new_value == "":
                        continue
                    if df.iloc[row, col] != new_value:
                        df.iloc[row, col] = new_value
                        modified_cells.append([row, col])
            elif change.get('type') == 'row':
                idx = change.get('index')
                amt = change.get('amount', 1)
                if change.get('action') == 'create':
                    # Insert new rows at idx
                    for _ in range(amt):
                        empty_row = [None] * len(df.columns)
                        df = pd.concat([
                            df.iloc[:idx],
                            pd.DataFrame([empty_row], columns=df.columns),
                            df.iloc[idx:]
                        ], ignore_index=True)
                elif change.get('action') == 'remove':
                    df = df.drop(df.index[range(idx, idx + amt)]).reset_index(drop=True)
            elif change.get('type') == 'col':
                idx = change.get('index')
                amt = change.get('amount', 1)
                if change.get('action') == 'create':
                    for i in range(amt):
                        new_col_name = self._generate_new_col_name(df)
                        df.insert(idx, new_col_name, None)
                elif change.get('action') == 'remove':
                    cols_to_remove = df.columns[idx:idx+amt]
                    df = df.drop(columns=cols_to_remove)

        # --- Ensure DataFrame is always reindexed after every operation ---
        df.reset_index(drop=True, inplace=True)
        df.columns = pd.Index(df.columns)  # Ensure columns are in current order

        # Create new spreadsheet state and update history
        new_spreadsheet = Spreadsheet(
            spreadsheet.file_id,
            spreadsheet.original_filename,
            df,
            getattr(spreadsheet, 'file_path', None)
        )
        history.add_state(new_spreadsheet)
        session.update_spreadsheet(new_spreadsheet)

        # Prepare view data with datetime handling
        df_copy = df.copy()
        for col in df_copy.columns:
            if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
                df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')

        data = df_copy.replace({float('nan'): None}).values.tolist()

        return {
            'data': data,
            'metadata': new_spreadsheet.get_metadata(),
            'can_undo': history.can_undo(),
            'can_redo': history.can_redo(),
            'modified_cells': modified_cells
        }

    def _generate_new_col_name(self, df):
        """
        Generate a new column name (e.g., 'New Column 1', 'New Column 2', etc.)
        """
        base = "New Column"
        i = 1
        while f"{base} {i}" in df.columns:
            i += 1
        return f"{base} {i}"

    def get_schema_from_df(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate a schema from the provided DataFrame
        
        Args:
            df: The pandas DataFrame to analyze
            
        Returns:
            Dict[str, Any]: JSON schema representing the structure
        """
        return self.script_executor.generate_schema_from_df(df)

    def generate_transformation_prompt(self, source_df: pd.DataFrame, target_df: pd.DataFrame) -> str:
        """
        Generate a prompt to transform source_df to match the structure of target_df
        
        Args:
            source_df: The source DataFrame to transform
            target_df: The target DataFrame with the desired structure
            
        Returns:
            str: A prompt for the LLM to generate a transformation script
        """
        return self.script_executor.generate_transformation_script(source_df, target_df)

    def get_spreadsheet_df(self, session_id: str) -> pd.DataFrame:
        """
        Get the current spreadsheet DataFrame for a session
        
        Args:
            session_id: Session ID
            
        Returns:
            pd.DataFrame: The current spreadsheet DataFrame
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
        
        return spreadsheet.get_data()