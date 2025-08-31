"""Main controller for spreadsheet operations."""

import pandas as pd
import os, uuid, logging
from typing import Any, Dict, List

from src.llm.llm_service import LLMService
from src.model.spreadsheet_manager import SpreadsheetManager
from src.llm.token_manager import token_manager
from werkzeug.datastructures import FileStorage
from src.controller.file_manager import FileManager
from src.controller.script_reuser import ScriptReuser
from src.controller.script_manager import ScriptManager
from src.controller.script_executor import ScriptExecutor
from src.controller.session_manager import SessionManager
from src.controller.schema_generator import SchemaGenerator
from src.model.modification_history import ModificationHistory
from src.controller.script_fixer import ScriptExecutionFailureException

class SpreadsheetController:
    """Controller for spreadsheet operations."""
    
    def __init__(self, session_manager: SessionManager):
        """Initialize controller with required managers and services."""
        self.session_manager = session_manager
        self.llm_service = LLMService()
        self.script_dir = os.path.join('src', 'scripts')
        self.script_executor = ScriptExecutor(script_dir=self.script_dir)
        self.script_manager = ScriptManager(script_dir=self.script_dir)
        self.logger = logging.getLogger(__name__)
        self.file_manager = FileManager(
            upload_dir=os.path.join('static', 'uploads'),
            download_dir=os.path.join('static', 'downloads'),
            json_dir=os.path.join('static', 'json')
        )
        self.schema_generator = SchemaGenerator()
        self.parser = SpreadsheetManager()
        self.script_reuser = ScriptReuser()
    
    def upload_spreadsheet(self, file: FileStorage) -> str:
        """Upload and process a spreadsheet file."""
        if file.filename is None:
            raise ValueError("No filename provided")
            
        if not self.file_manager.validate_file_type(file.filename):
            raise ValueError("Invalid file format. Supported formats: xlsx, xls, csv")
        
        file_id = str(uuid.uuid4())
        file_path = self.file_manager.save_uploaded_file(file, file_id)
        
        try:
            self.logger.info(f"Starting comprehensive parsing for file: {file.filename}")
            df, sheets, original_file_type = self.parser.parse_file(file_path)
            
            summary = self.parser.get_parsing_summary(df, sheets)
            self.logger.info(f"Parsing completed: {summary}")
            
        except Exception as e:
            self.logger.error(f"Failed to parse file {file.filename}: {str(e)}")
            raise ValueError(f"Failed to parse file: {str(e)}")
        
        if df is None or df.empty:
            raise ValueError("No data found in the uploaded file")
            
        if sheets:
            processed_sheets = []
            for sheet_info in sheets:
                processed_sheets.append({
                    'name': sheet_info['name'],
                    'data': sheet_info['data']
                })
            sheets = processed_sheets
            
        spreadsheet = SpreadsheetManager(file_id, file.filename, df, file_path, original_file_type)
        if sheets:
            spreadsheet.workbook_sheets = sheets
        
        session_id = self.session_manager.create_session()
        session = self.session_manager.get_session(session_id)
        
        if not session:
            raise ValueError("Failed to create or retrieve session")
        
        history = ModificationHistory()
        history.add_state(spreadsheet)
        
        session.update_spreadsheet(spreadsheet)
        session.set_modification_history(history)
        
        return session_id
    
    def view_spreadsheet(self, session_id: str) -> Dict[str, Any]:
        """Get spreadsheet view data."""
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found or expired")
        
        history = session.get_modification_history()
        if not history:
            raise ValueError("Modification history not found for this session")
            
        spreadsheet = history.get_current_state()
        if not spreadsheet:
            raise ValueError("No spreadsheet data found")
        
        if hasattr(spreadsheet, 'workbook_sheets') and spreadsheet.workbook_sheets:
            sheets_data = []
            for sheet in spreadsheet.workbook_sheets:
                sheet_data = self._prepare_spreadsheet_data_for_frontend(sheet['data'])
                sheets_data.append({
                    'name': sheet['name'],
                    'data': sheet_data,
                    'metadata': {
                        'sheetName': sheet['name'],
                        'rows': len(sheet['data']),
                        'columns': len(sheet['data'].columns)
                    }
                })
            return {
                'sheets': sheets_data,
                'activeSheetIndex': 0,
                'can_undo': history.can_undo(),
                'can_redo': history.can_redo(),
                'modified_cells': [],
                'metadata': spreadsheet.get_metadata()
            }
        
        data = self._prepare_spreadsheet_data_for_frontend(spreadsheet.get_data())
        
        return {
            'data': data,
            'metadata': spreadsheet.get_metadata(),
            'can_undo': history.can_undo(),
            'can_redo': history.can_redo(),
            'modified_cells': []
        }
    
    def process_command(self, session_id: str, command: str, use_advanced_processing: bool = False) -> Dict[str, Any]:
        """Process a user command through LLM using the latest spreadsheet structure."""
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found or expired")
        
        history = session.get_modification_history()
        if not history:
            raise ValueError("Modification history not found for this session")
        current_spreadsheet = history.get_current_state()
        if not current_spreadsheet:
            raise ValueError("No spreadsheet data found")

        current_df = current_spreadsheet.get_data()

        print(f"\n🔄 [PRE-PROMPT] Ensuring up-to-date spreadsheet structure before LLM processing:")
        print(f"   - Shape: {current_df.shape[0]} rows × {current_df.shape[1]} columns")
        print(f"   - Columns: {list(current_df.columns)}")
        print(f"   - Data types: {dict(current_df.dtypes)}")
        print(f"   - Head preview:\n{current_df.head(5)}")
        
        print(f"\n🔍 [SCRIPT REUSE] Checking for similar prompts...")
        similar_mapping = self.script_reuser.find_similar_prompt(command, current_df)
        
        if similar_mapping:
            print(f"✅ [SCRIPT REUSE] Found similar prompt! Attempting to reuse script...")
            try:
                reused_df, modified_cells, reuse_success = self.script_reuser.reuse_script(
                    similar_mapping, current_df, self.file_manager, session_id
                )
                
                if reuse_success:
                    print(f"🎉 [SCRIPT REUSE] Successfully reused script!")
                    
                    new_spreadsheet = SpreadsheetManager(
                        current_spreadsheet.file_id,
                        current_spreadsheet.original_filename,
                        reused_df,
                        None,
                        current_spreadsheet.original_file_type
                    )
                    
                    history.add_state(new_spreadsheet)
                    session.update_spreadsheet(new_spreadsheet)
                    
                    data = self._prepare_spreadsheet_data_for_frontend(reused_df)
                    
                    return {
                        'data': data,
                        'metadata': new_spreadsheet.get_metadata(),
                        'can_undo': history.can_undo(),
                        'can_redo': history.can_redo(),
                        'modified_cells': modified_cells
                    }
                else:
                    print(f"❌ [SCRIPT REUSE] Script reuse failed, falling back to LLM generation...")
            except Exception as e:
                print(f"❌ [SCRIPT REUSE] Script reuse error: {e}, falling back to LLM generation...")
        else:
            print(f"🔄 [SCRIPT REUSE] No similar prompts found, generating new script...")
        
        spreadsheet_json = current_spreadsheet.to_json(save_to_file=True, file_manager=self.file_manager)
        
        script = self.llm_service.generate_script(spreadsheet_json, command, use_advanced_processing)

        script_id = self.script_manager.save_script(script, {
            'command': command,
            'session_id': session_id,
            'use_advanced_processing': use_advanced_processing
        })

        session.set_generated_script(script)

        try:
            if use_advanced_processing:
                new_df, modified_cells = self.script_executor.execute_script(
                    script,
                    current_df.copy(),
                    file_manager=self.file_manager,
                    session_id=session_id
                )
            else:
                new_df, modified_cells = self.script_executor.execute_simple_script(
                    script,
                    current_df.copy(),
                    command,
                    file_manager=self.file_manager,
                    session_id=session_id
                )
        except Exception as e:
            print(f"❌ [SCRIPT EXECUTION] First attempt failed for command: {command}")
            error_details = str(e)
            if "ScriptExecutionFailureException" in str(type(e)) and hasattr(e, 'error_details'):
                error_details = e.error_details

            try:
                print("🔁 [RETRY] Regenerating script with error feedback...")
                retry_script = self.llm_service.generate_script_with_error_feedback(
                    spreadsheet_json, command, error_details, use_advanced_processing
                )

                retry_script_id = self.script_manager.save_script(retry_script, {
                    'command': command,
                    'session_id': session_id,
                    'use_advanced_processing': use_advanced_processing,
                    'retry': True,
                    'error_feedback': error_details[:500]
                })
                session.set_generated_script(retry_script)

                if use_advanced_processing:
                    new_df, modified_cells = self.script_executor.execute_script(
                        retry_script,
                        current_df.copy(),
                        file_manager=self.file_manager,
                        session_id=session_id
                    )
                else:
                    new_df, modified_cells = self.script_executor.execute_simple_script(
                        retry_script,
                        current_df.copy(),
                        command,
                        file_manager=self.file_manager,
                        session_id=session_id
                    )

                print("✅ [RETRY] Retry succeeded after providing error feedback to LLM")
            except Exception as retry_err:
                print(f"❌ [RETRY] Retry failed: {retry_err}")
                retry_details = str(retry_err)
                if "ScriptExecutionFailureException" in str(type(retry_err)) and hasattr(retry_err, 'error_details'):
                    retry_details = retry_err.error_details
                raise ScriptExecutionFailureException(command, retry_details)
        
        new_spreadsheet = SpreadsheetManager(
            current_spreadsheet.file_id,
            current_spreadsheet.original_filename,
            new_df,
            None,
            current_spreadsheet.original_file_type
        )
        
        history.add_state(new_spreadsheet)
        session.update_spreadsheet(new_spreadsheet)
        
        data = self._prepare_spreadsheet_data_for_frontend(new_df)
        
        try:
            print(f"💾 [SCRIPT REUSE] Saving successful execution for future reuse...")
            self.script_reuser.save_successful_execution(
                command, script, script_id, session_id, current_df, use_advanced_processing
            )
            print(f"✅ [SCRIPT REUSE] Successfully saved execution mapping")
        except Exception as e:
            print(f"⚠️ [SCRIPT REUSE] Failed to save execution mapping: {e}")
        
        return {
            'data': data,
            'metadata': new_spreadsheet.get_metadata(),
            'can_undo': history.can_undo(),
            'can_redo': history.can_redo(),
            'modified_cells': modified_cells
        }
    
    def undo_modification(self, session_id: str) -> Dict[str, Any]:
        """Undo the last modification."""
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found or expired")
        
        history = session.get_modification_history()
        if not history:
            raise ValueError("No modification history found")
        previous_spreadsheet = history.undo()
        
        if not previous_spreadsheet:
            raise ValueError("Nothing to undo")
        
        session.update_spreadsheet(previous_spreadsheet)
        
        data = self._prepare_spreadsheet_data_for_frontend(previous_spreadsheet.get_data())
        
        return {
            'data': data,
            'metadata': previous_spreadsheet.get_metadata(),
            'can_undo': history.can_undo(),
            'can_redo': history.can_redo(),
            'modified_cells': []
        }
    
    def redo_modification(self, session_id: str) -> Dict[str, Any]:
        """Redo a previously undone modification."""
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found or expired")
        
        history = session.get_modification_history()
        if not history:
            raise ValueError("No modification history found")
        next_spreadsheet = history.redo()
        
        if not next_spreadsheet:
            raise ValueError("Nothing to redo")
        session.update_spreadsheet(next_spreadsheet)
        
        data = self._prepare_spreadsheet_data_for_frontend(next_spreadsheet.get_data())
        
        return {
            'data': data,
            'metadata': next_spreadsheet.get_metadata(),
            'can_undo': history.can_undo(),
            'can_redo': history.can_redo(),
            'modified_cells': []
        }
    
    def download_spreadsheet(self, session_id: str) -> tuple:
        """Generate a downloadable spreadsheet file in the original format."""
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found or expired")
        
        history = session.get_modification_history()
        if not history:
            raise ValueError("No modification history found")
            
        spreadsheet = history.get_current_state()
        if not spreadsheet:
            raise ValueError("No spreadsheet data found")
            
        download_path = spreadsheet.save(self.file_manager.download_dir)
        
        original_ext = spreadsheet.original_file_type
        if not original_ext.startswith('.'):
            original_ext = '.' + original_ext
            
        base_name = os.path.splitext(spreadsheet.original_filename)[0]
        download_filename = f"{base_name}{original_ext}"
        
        self.logger.info(f"Generated download file: {download_path} (original type: {original_ext})")
        
        return download_path, download_filename
    
    def cleanup_session(self, session_id: str) -> None:
        """Clean up a session and its resources."""
        session = self.session_manager.get_session(session_id)
        if not session:
            return
            
        history = session.get_modification_history()
        spreadsheet = history.get_current_state() if history and hasattr(history, 'get_current_state') else None
        
        if spreadsheet:
            original_file = spreadsheet.file_path
            if original_file and os.path.exists(original_file):
                try:
                    os.remove(original_file)
                except (PermissionError, OSError) as e:
                    print(f"Warning: Could not delete file {original_file}: {e}")
            
            file_id = spreadsheet.file_id
            for format_type in ['xlsx', 'csv']:
                download_path = os.path.join(self.file_manager.download_dir, f"{file_id}.{format_type}")
                if os.path.exists(download_path):
                    try:
                        os.remove(download_path)
                    except (PermissionError, OSError) as e:
                        print(f"Warning: Could not delete file {download_path}: {e}")
        
        try:
            self.script_manager.cleanup_old_scripts()
        except Exception as e:
            print(f"Warning: Error cleaning up scripts: {e}")
            
        self.session_manager.remove_session(session_id)
    
    def process_table_changes(self, session_id: str, changes: list) -> dict:
        """Apply direct table changes (cell edits, row/col add/remove) and update history."""
        import pandas as pd

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

        df.reset_index(drop=True, inplace=True)
        df.columns = pd.Index(df.columns)

        new_spreadsheet = SpreadsheetManager(
            spreadsheet.file_id,
            spreadsheet.original_filename,
            df,
            getattr(spreadsheet, 'file_path', None),
            getattr(spreadsheet, 'original_file_type', None)
        )
        history.add_state(new_spreadsheet)
        session.update_spreadsheet(new_spreadsheet)

        data = self._prepare_spreadsheet_data_for_frontend(df)

        return {
            'data': data,
            'metadata': new_spreadsheet.get_metadata(),
            'can_undo': history.can_undo(),
            'can_redo': history.can_redo(),
            'modified_cells': modified_cells
        }

    def _generate_new_col_name(self, df):
        """Generate a new column name (e.g., 'New Column 1', 'New Column 2', etc.)"""
        base = "New Column"
        i = 1
        while f"{base} {i}" in df.columns:
            i += 1
        return f"{base} {i}"

    def capture_schema_structure(self, right_data: List[List]) -> dict:
        """Capture the structure/schema from the right spreadsheet template."""
        return self.schema_generator.capture_schema_structure(right_data)
    
    def apply_manual_schema_transformation(self, session_id: str, right_data: List[List]) -> dict:
        """Apply manual schema transformation using right spreadsheet as template."""
        try:
            session = self.session_manager.get_session(session_id)
            if not session:
                raise ValueError("Session not found or expired")
            
            history = session.get_modification_history()
            if not history:
                raise ValueError("Modification history not found for this session")
                
            current_spreadsheet = history.get_current_state()
            if not current_spreadsheet:
                raise ValueError("No spreadsheet data found")
            
            current_df = current_spreadsheet.get_data().copy()
            
            schema = self.schema_generator.capture_schema_structure(right_data)
            
            transformed_df, modified_cells = self.schema_generator.apply_schema_patterns(current_df, schema, right_data)
            
            new_spreadsheet = SpreadsheetManager(
                current_spreadsheet.file_id,
                current_spreadsheet.original_filename,
                transformed_df,
                None,
                current_spreadsheet.original_file_type
            )
            
            history.add_state(new_spreadsheet)
            session.update_spreadsheet(new_spreadsheet)
            
            data = self._prepare_spreadsheet_data_for_frontend(transformed_df)
            
            return {
                'data': data,
                'metadata': new_spreadsheet.get_metadata(),
                'can_undo': history.can_undo(),
                'can_redo': history.can_redo(),
                'modified_cells': modified_cells
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
        """Generate JSON schema from current spreadsheet data."""
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found or expired")
        
        history = session.get_modification_history()
        if not history:
            raise ValueError("Modification history not found for this session")
            
        current_spreadsheet = history.get_current_state()
        if not current_spreadsheet:
            raise ValueError("No spreadsheet data found")
        
        df = current_spreadsheet.get_data()
        data = df.values.tolist()
        
        return self.schema_generator.generate_schema_json(data)
    
    def validate_schema_compatibility(self, session_id: str, right_data: List[List]) -> dict:
        """Validate if current spreadsheet can be transformed to match right spreadsheet schema."""
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found or expired")
        
        history = session.get_modification_history()
        if not history:
            raise ValueError("Modification history not found for this session")
            
        current_spreadsheet = history.get_current_state()
        if not current_spreadsheet:
            raise ValueError("No spreadsheet data found")
        
        df = current_spreadsheet.get_data()
        left_data = df.values.tolist()
        
        return self.schema_generator.validate_schema_compatibility(left_data, right_data)
    
    def get_spreadsheet_df(self, session_id: str) -> pd.DataFrame:
        """Get the current spreadsheet DataFrame for a session."""
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found or expired")
        
        history = session.get_modification_history()
        if not history:
            raise ValueError("Modification history not found for this session")
            
        spreadsheet = history.get_current_state()
        if not spreadsheet:
            raise ValueError("No spreadsheet data found")
        
        return spreadsheet.get_data()

    def execute_commands(self, session_id: str, commands: List[str]) -> None:
        """Execute a series of commands in order."""
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError("Session not found or expired")
        
        if len(commands) > 1:
            token_manager.start_batch_mode()
            print(f"🚀 Starting batch execution of {len(commands)} commands...")
        
        try:
            for i, command in enumerate(commands, 1):
                if len(commands) > 1:
                    print(f"📝 Processing command {i}/{len(commands)}: {command[:50]}{'...' if len(command) > 50 else ''}")
                self.process_command(session_id, command)
        finally:
            if len(commands) > 1:
                token_manager.end_batch_mode()
                print(f"✅ Completed batch execution of {len(commands)} commands")
    
    def generate_and_execute_algorithm(self, session_id: str, action_plan: str, left_data: list, right_data: list) -> Dict[str, Any]:
        """Generate and execute a universal algorithm based on an action plan with error handling and retry."""
        if not self.session_manager.session_exists(session_id):
            raise ValueError("Session not found")
        
        max_algorithm_attempts = 5
        
        try:
            print(f"\n{'='*50}")
            print("🤖 GENERATING UNIVERSAL ALGORITHM")
            print(f"{'='*50}")
            print(f"📋 Left dataset: {len(left_data)} rows")
            print(f"📄 Right template: {len(right_data)} rows")
            
            current_df = self.get_spreadsheet_df(session_id)
            if current_df is None:
                raise ValueError("No spreadsheet data found for session")
            
            print(f"\n🔄 ALGORITHM GENERATION - Current spreadsheet structure:")
            print(f"   📊 Shape: {current_df.shape[0]} rows × {current_df.shape[1]} columns")
            print(f"   📋 Columns: {list(current_df.columns)}")
            print(f"   📈 Data sample: {current_df.head(2).values.tolist() if len(current_df) > 0 else 'Empty'}")
            
            last_error_msg = None
            
            for algorithm_attempt in range(max_algorithm_attempts):
                print(f"\n🔄 Algorithm Generation Attempt {algorithm_attempt + 1}/{max_algorithm_attempts}")
                
                try:
                    algorithm_script = self.llm_service.generate_universal_algorithm_with_error_feedback(
                        action_plan, left_data, right_data, last_error_msg
                    )
                    
                    script_id = self.script_manager.save_script(algorithm_script, {
                        'action_plan': action_plan,
                        'session_id': session_id,
                        'attempt': algorithm_attempt + 1
                    })
                    
                    print(f"💾 Algorithm saved (ID: {script_id}, {len(algorithm_script)} chars)")
                    
                    execution_attempts = 5
                    execution_error_msg = None
                    
                    for execution_attempt in range(execution_attempts):
                        try:
                            print(f"⚙️  Executing algorithm (attempt {execution_attempt + 1}/{execution_attempts})...")
                            
                            modified_df, modified_cells = self.script_executor.execute_universal_algorithm_with_validation(
                                algorithm_script, 
                                current_df.copy(),
                                self.file_manager
                            )
                            
                            print(f"🎉 Algorithm successful! (Gen: {algorithm_attempt + 1}, Exec: {execution_attempt + 1})")
                            
                            session = self.session_manager.get_session(session_id)
                            if not session:
                                raise ValueError("Session not found or expired")
                            history = session.get_modification_history()
                            if not history:
                                raise ValueError("Modification history not found for this session")
                            current_spreadsheet = history.get_current_state()
                            if not current_spreadsheet:
                                raise ValueError("No spreadsheet data found")
                            new_spreadsheet = SpreadsheetManager(
                                current_spreadsheet.file_id,
                                current_spreadsheet.original_filename,
                                modified_df,
                                None,
                                current_spreadsheet.original_file_type
                            )
                            history.add_state(new_spreadsheet)
                            session.update_spreadsheet(new_spreadsheet)
                            
                            print(f"✅ UNIVERSAL ALGORITHM COMPLETED - {len(modified_cells)} cells modified")
                            
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
                            execution_error_msg = str(execution_error)
                            print(f"❌ Execution attempt {execution_attempt + 1} failed: {execution_error_msg}")
                            
                            if execution_attempt < execution_attempts - 1:
                                print(f"🔄 Retrying execution...")
                                continue
                            else:
                                print(f"❌ All {execution_attempts} execution attempts failed")
                                last_error_msg = f"Algorithm execution failed after {execution_attempts} attempts: {execution_error_msg}. The algorithm may not be processing the entire dataset correctly or may have fundamental logic errors."
                                break
                    
                    if algorithm_attempt < max_algorithm_attempts - 1:
                        print(f"🔄 Retrying algorithm generation with error feedback...")
                        continue
                    else:
                        raise RuntimeError(f"Algorithm execution failed after {execution_attempts} execution attempts: {execution_error_msg}")
                    
                except Exception as generation_error:
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

    def _prepare_spreadsheet_data_for_frontend(self, df: pd.DataFrame) -> List[List]:
        """Prepare DataFrame data for frontend display with preprocessed data."""
        if df is None or df.empty:
            return []
            
        df_copy = df.copy()
        
        for col in df_copy.columns:
            df_copy[col] = df_copy[col].astype(str).fillna('').replace('nan', '')
        
        data_rows = df_copy.values.tolist()
        
        print(f"🔍 [FRONTEND DATA PREP] Preprocessed data (no headers added):")
        print(f"   - Total rows: {len(data_rows)}")
        print(f"   - Columns: {len(df_copy.columns) if not df_copy.empty else 0}")
        print(f"   - First row sample: {data_rows[0][:5] if data_rows else 'No data'}{'...' if data_rows and len(data_rows[0]) > 5 else ''}")
        print(f"   - All content is preprocessed plain text")
        
        return data_rows

    def get_script_reuse_stats(self) -> Dict[str, Any]:
        """Get statistics about script reuse performance."""
        return self.script_reuser.get_mapping_stats()
    
    def cleanup_script_reuse_data(self, max_age_days: int = 30) -> Dict[str, Any]:
        """Clean up old script reuse data."""
        cleaned_count = self.script_reuser.cleanup_old_mappings(max_age_days)
        return {
            'cleaned_mappings': cleaned_count,
            'max_age_days': max_age_days,
            'remaining_mappings': len(self.script_reuser.mappings)
        }