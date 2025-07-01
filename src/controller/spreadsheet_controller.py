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
from src.controller.script_manager import ScriptManager
from src.controller.schema_generator import SchemaGenerator

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
        self.script_manager = ScriptManager(script_dir=self.script_dir)
        self.file_manager = FileManager(
            upload_dir=os.path.join('static', 'uploads'),
            download_dir=os.path.join('static', 'downloads'),
            json_dir=os.path.join('static', 'json')
        )
        self.schema_generator = SchemaGenerator()
    
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
        # Replace NaN, inf, -inf with None for JSON serialization
        data = df_copy.replace({float('nan'): None, float('inf'): None, float('-inf'): None, pd.NA: None}).values.tolist()
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
    
    def process_command(self, session_id: str, command: str, use_advanced_processing: bool = False) -> Dict[str, Any]:
        """
        Process a user command through LLM

        Args:
            session_id: Session ID
            command: User command text
            use_advanced_processing: Whether to use thinking and code execution tools

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
        
        # Generate script using LLM with appropriate processing mode
        script = self.llm_service.generate_script(spreadsheet_json, command, use_advanced_processing)
        
        # Save the generated script using ScriptManager
        script_id = self.script_manager.save_script(script, {
            'command': command,
            'session_id': session_id,
            'use_advanced_processing': use_advanced_processing
        })
        
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
        # Replace NaN, inf, -inf with None for JSON serialization
        data = df_copy.replace({float('nan'): None, float('inf'): None, float('-inf'): None, pd.NA: None}).values.tolist()
        
        return {
            'data': data,
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
        # Replace NaN, inf, -inf with None for JSON serialization
        data = df_copy.replace({float('nan'): None, float('inf'): None, float('-inf'): None, pd.NA: None}).values.tolist()
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
        # Replace NaN, inf, -inf with None for JSON serialization
        data = df_copy.replace({float('nan'): None, float('inf'): None, float('-inf'): None, pd.NA: None}).values.tolist()
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
        
        # Clean up old scripts
        try:
            self.script_manager.cleanup_old_scripts()
        except Exception as e:
            print(f"Warning: Error cleaning up scripts: {e}")
            
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
        # Replace NaN, inf, -inf with None for JSON serialization
        data = df_copy.replace({float('nan'): None, float('inf'): None, float('-inf'): None, pd.NA: None}).values.tolist()

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

    def capture_schema_structure(self, right_data: List[List]) -> dict:
        """
        Capture the structure/schema from the right spreadsheet template
        
        Args:
            right_data: 2D array representing the right spreadsheet data
            
        Returns:
            dict: Schema information including patterns, structure, and transformations
        """
        return self.schema_generator.capture_schema_structure(right_data)
    
    def apply_manual_schema_transformation(self, session_id: str, right_data: List[List]) -> dict:
        """
        Apply manual schema transformation using right spreadsheet as template
        
        Args:
            session_id: Session ID
            right_data: 2D array representing the right spreadsheet structure
            
        Returns:
            dict: Result with transformed spreadsheet data
        """
        try:
            # Get session and current spreadsheet
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
            
            # Get current data
            current_df = current_spreadsheet.get_data().copy()
            
            # Capture schema from right spreadsheet
            schema = self.schema_generator.capture_schema_structure(right_data)
            
            # Apply transformation based on schema patterns
            transformed_df, modified_cells = self.schema_generator.apply_schema_patterns(current_df, schema, right_data)
            
            # Create new spreadsheet state
            new_spreadsheet = Spreadsheet(
                current_spreadsheet.file_id,
                current_spreadsheet.original_filename,
                transformed_df
            )
            
            # Add to history
            history.add_state(new_spreadsheet)
            
            # Update session spreadsheet
            session.update_spreadsheet(new_spreadsheet)
            
            # Prepare view data with datetime handling (similar to process_command)
            df_copy = transformed_df.copy()
            
            # Convert datetime columns to strings for JSON serialization
            for col in df_copy.columns:
                if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
                    df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
            # Replace NaN, inf, -inf with None for JSON serialization
            data = df_copy.replace({float('nan'): None, float('inf'): None, float('-inf'): None, pd.NA: None}).values.tolist()
            
            return {
                'data': data,
                'metadata': new_spreadsheet.get_metadata(),
                'can_undo': history.can_undo(),
                'can_redo': history.can_redo(),
                'modified_cells': modified_cells  # Add this to enable cell highlighting
            }
            
        except Exception as e:
            raise Exception(f"Schema transformation failed: {str(e)}")

    # PLACEHOLDER: Schema-related methods moved to SchemaGenerator
    # The following methods were moved to the SchemaGenerator class:
    # - _analyze_column_pattern()
    # - _is_date_pattern() 
    # - _find_repeating_cycle()
    # - _apply_schema_patterns()
    # - get_schema_from_df() (previously removed)
    # - generate_transformation_prompt() (previously removed)
    # Use self.schema_generator to access these functionalities.

    def generate_schema_json(self, session_id: str) -> dict:
        """
        Generate JSON schema from current spreadsheet data
        
        Args:
            session_id: Session ID
            
        Returns:
            dict: JSON schema representation
        """
        # Get session and current spreadsheet
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found or expired")
        
        history = session.get_modification_history()
        if not history:
            raise ValueError("Modification history not found for this session")
            
        current_spreadsheet = history.get_current_state()
        if not current_spreadsheet:
            raise ValueError("No spreadsheet data found")
        
        # Convert DataFrame to 2D list for schema generation
        df = current_spreadsheet.get_data()
        data = df.values.tolist()
        
        return self.schema_generator.generate_schema_json(data)
    
    def validate_schema_compatibility(self, session_id: str, right_data: List[List]) -> dict:
        """
        Validate if current spreadsheet can be transformed to match right spreadsheet schema
        
        Args:
            session_id: Session ID
            right_data: Target spreadsheet schema data
            
        Returns:
            dict: Validation result with compatibility information
        """
        # Get session and current spreadsheet
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found or expired")
        
        history = session.get_modification_history()
        if not history:
            raise ValueError("Modification history not found for this session")
            
        current_spreadsheet = history.get_current_state()
        if not current_spreadsheet:
            raise ValueError("No spreadsheet data found")
        
        # Convert DataFrame to 2D list for validation
        df = current_spreadsheet.get_data()
        left_data = df.values.tolist()
        
        return self.schema_generator.validate_schema_compatibility(left_data, right_data)
    
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

    def execute_commands(self, session_id: str, commands: List[str]) -> None:
        """
        Execute a series of commands in order

        Args:
            session_id: Session ID
            commands: List of command strings to execute
        """
        # Get session
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found or expired")
        
        # Execute each command
        for command in commands:
            self.process_command(session_id, command)
    
    def generate_and_execute_algorithm(self, session_id: str, action_plan: str, left_data: list, right_data: list) -> Dict[str, Any]:
        """
        Generate and execute a universal algorithm based on an action plan with error handling and retry
        
        Args:
            session_id: The session identifier
            action_plan: Description of changes made to sample data
            left_data: The left spreadsheet data
            right_data: The right spreadsheet data
            
        Returns:
            Dict containing the updated spreadsheet data and metadata
        """
        if not self.session_manager.session_exists(session_id):
            raise ValueError("Session not found")
        
        max_algorithm_attempts = 5  # Increased for better reliability
        
        try:
            print(f"\n{'='*50}")
            print("🤖 GENERATING UNIVERSAL ALGORITHM")
            print(f"{'='*50}")
            print(f"📋 Left dataset: {len(left_data)} rows")
            print(f"📄 Right template: {len(right_data)} rows")
            
            # Get current spreadsheet data
            current_df = self.get_spreadsheet_df(session_id)
            if current_df is None:
                raise ValueError("No spreadsheet data found for session")
            
            last_error_msg = None
            
            for algorithm_attempt in range(max_algorithm_attempts):
                print(f"\n🔄 Algorithm Generation Attempt {algorithm_attempt + 1}/{max_algorithm_attempts}")
                
                try:
                    # Generate universal algorithm using LLM (with error feedback if available)
                    algorithm_script = self.llm_service.generate_universal_algorithm_with_error_feedback(
                        action_plan, left_data, right_data, last_error_msg
                    )
                    
                    # Save the generated script using ScriptManager
                    script_id = self.script_manager.save_script(algorithm_script, {
                        'action_plan': action_plan,
                        'session_id': session_id,
                        'attempt': algorithm_attempt + 1
                    })
                    
                    print(f"💾 Algorithm saved (ID: {script_id}, {len(algorithm_script)} chars)")
                    
                    # Execute the universal algorithm with enhanced error handling
                    execution_attempts = 5  # Try execution multiple times with increasingly detailed error feedback
                    execution_error_msg = None
                    
                    for execution_attempt in range(execution_attempts):
                        try:
                            print(f"⚙️  Executing algorithm (attempt {execution_attempt + 1}/{execution_attempts})...")
                            
                            modified_df, modified_cells = self.script_executor.execute_universal_algorithm_with_validation(
                                algorithm_script, 
                                current_df.copy(),
                                self.file_manager
                            )
                            
                            # If we get here, execution was successful
                            print(f"🎉 Algorithm successful! (Gen: {algorithm_attempt + 1}, Exec: {execution_attempt + 1})")
                            
                            # Save the modified data and create history entry
                            session = self.session_manager.get_session(session_id)
                            if not session:
                                raise ValueError("Session not found or expired")
                            history = session.get_modification_history()
                            if not history:
                                raise ValueError("Modification history not found for this session")
                            current_spreadsheet = history.get_current_state()
                            if not current_spreadsheet:
                                raise ValueError("No spreadsheet data found")
                            new_spreadsheet = Spreadsheet(
                                current_spreadsheet.file_id,
                                current_spreadsheet.original_filename,
                                modified_df
                            )
                            history.add_state(new_spreadsheet)
                            session.update_spreadsheet(new_spreadsheet)
                            
                            print(f"✅ UNIVERSAL ALGORITHM COMPLETED - {len(modified_cells)} cells modified")
                            
                            # Return the response in the same format as process_command
                            # Patch: replace NaN, inf, -inf with None in the returned data
                            safe_data = modified_df.replace({float('nan'): None, float('inf'): None, float('-inf'): None, pd.NA: None}).values.tolist()
                            return {
                                "sessionId": session_id,
                                "data": safe_data,
                                "headers": modified_df.columns.tolist(),
                                "can_undo": history.can_undo(),
                                "can_redo": history.can_redo(),
                                "modified_cells": modified_cells,
                                "metadata": {
                                    "rows": len(modified_df),
                                    "columns": len(modified_df.columns),
                                    "operation": "universal_algorithm",
                                    "action_plan": action_plan,
                                    "generation_attempts": algorithm_attempt + 1,
                                    "execution_attempts": execution_attempt + 1
                                }
                            }
                            
                        except Exception as execution_error:
                            # Get the detailed error message for better feedback
                            execution_error_msg = str(execution_error)
                            print(f"❌ Execution attempt {execution_attempt + 1} failed: {execution_error_msg}")
                            
                            if execution_attempt < execution_attempts - 1:
                                print(f"🔄 Retrying execution...")
                                continue  # Continue to next execution attempt
                            else:
                                # All execution attempts failed, break to try generating a new algorithm
                                print(f"❌ All {execution_attempts} execution attempts failed")
                                last_error_msg = f"Algorithm execution failed after {execution_attempts} attempts: {execution_error_msg}. The algorithm may not be processing the entire dataset correctly or may have fundamental logic errors."
                                break  # Break out of execution loop to generate new algorithm
                    
                    # If we reach here, execution failed for this algorithm, continue to next generation attempt
                    if algorithm_attempt < max_algorithm_attempts - 1:
                        print(f"🔄 Retrying algorithm generation with error feedback...")
                        continue  # Continue to next algorithm generation attempt
                    else:
                        raise RuntimeError(f"Algorithm execution failed after {execution_attempts} execution attempts: {execution_error_msg}")
                    
                except Exception as generation_error:
                    # Handle algorithm generation errors
                    generation_error_msg = str(generation_error)
                    last_error_msg = f"Algorithm generation failed: {generation_error_msg}"
                    
                    print(f"Algorithm generation attempt {algorithm_attempt + 1} failed: {generation_error_msg}")
                    
                    if algorithm_attempt < max_algorithm_attempts - 1:
                        print(f"Retrying algorithm generation...")
                        continue
                    else:
                        raise RuntimeError(f"All {max_algorithm_attempts} algorithm generation attempts failed. Last error: {generation_error_msg}")
            
        except Exception as e:
            error_msg = f"Universal algorithm generation/execution failed: {str(e)}"
            print(f"ERROR: {error_msg}")
            raise RuntimeError(error_msg)