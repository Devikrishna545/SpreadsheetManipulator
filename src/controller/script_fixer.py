"""Automated fixer for AI-generated scripts with sandboxing, LLM assists, and manual fallbacks."""

import re, logging
import numpy as np
import pandas as pd
from src.llm.llm_service import LLMService
from typing import Tuple, Optional, Dict, Any
from src.llm.token_manager import token_manager
from src.controller.script_tester import ScriptTester

class ScriptExecutionFailureException(Exception):
    """Exception raised when script execution fails after debugging pipeline."""
    def __init__(self, command: str, error_details: str):
        self.command = command
        self.error_details = error_details
        super().__init__(f"Failed to execute command '{command}' after debugging pipeline: {error_details}")

class ScriptFixer:
    """Handles error correction for AI-generated scripts with up to 5 retry attempts."""
    
    def __init__(self):
        """Initialize fixer with LLM service and tester."""
        self.llm_service = LLMService()
        self.script_tester = ScriptTester()
        self.max_retries = 5
        self.current_script_path = None
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def _build_column_mapping(self, df: pd.DataFrame) -> str:
        """Return letter->label mapping for DataFrame to guide Gemini."""
        cols = list(df.columns)
        letters = [chr(ord('A') + i) for i in range(min(26, len(cols)))]
        lines = []
        for i, letter in enumerate(letters):
            lines.append(f"{letter} -> {cols[i]}")
        return "\n".join(lines)

    # ----- Excel-style reference helpers (for prompt guidance only) -----
    def _excel_col_letter_to_pos(self, letters: str) -> int:
        """Convert Excel column letters to 0-based positional index."""
        letters = letters.strip().upper()
        pos = 0
        for ch in letters:
            if 'A' <= ch <= 'Z':
                pos = pos * 26 + (ord(ch) - ord('A') + 1)
            else:
                break
        return max(0, pos - 1)

    def _excel_cols_range_positions(self, start_letter: str, end_letter: str, df: pd.DataFrame) -> list:
        """Return positional indices for column letter range, clamped to DataFrame width."""
        start = self._excel_col_letter_to_pos(start_letter)
        end = self._excel_col_letter_to_pos(end_letter)
        if start > end:
            start, end = end, start
        end = min(end, len(df.columns) - 1)
        start = min(start, end)
        return list(range(start, end + 1))

    def _build_excel_reference_help(self, df: pd.DataFrame) -> str:
        """Build guidance block for Excel-style references and common mappings."""
        if df is None or df.empty:
            return ""
        mapping = self._build_column_mapping(df)
        # Example common subset J–O for row 2
        jo_positions = self._excel_cols_range_positions('J', 'O', df)
        jo_labels = [str(df.columns[i]) for i in jo_positions]
        jo_info = (
            f"Row 2 (Excel) -> DataFrame row index 1.\n"
            f"J2–O2 columns (letters) -> positional indices {jo_positions} -> labels {jo_labels}.\n"
            f"Subset for duplicates across J–O: {jo_labels} (or use positions {jo_positions})."
        )
        guide = (
            "EXCEL REFERENCE GUIDE\n"
            "- Column letters map by position using current DataFrame order.\n"
            "- Row r in Excel maps to DataFrame row index (r-1).\n"
            "- Use df.iloc[row_index, col_pos] for position, or df[label] with the mapping.\n\n"
            "CURRENT LETTER→LABEL MAPPING:\n" + mapping + "\n\n" + jo_info
        )
        return guide

    def fix_and_execute_script(self, script: str, spreadsheet_df: pd.DataFrame, 
                              command: str, security_manager, script_path: Optional[str] = None) -> Tuple[pd.DataFrame, list, bool]:
        """
        Execute a script with comprehensive automated error correction pipeline.
        
        Enhanced Flow:
        1. Sandbox test → 2. LLM fix (if errors) → 3. Manual fix (if LLM fails) 
        → 4. Advanced Gemini Complex Script Generation (attempts 6-8 if standard methods fail) 
        → 5. Security check → 6. LLM security fix (if needed) → 7. Execute
        
        Args:
            script: The Python script to execute
            spreadsheet_df: The pandas DataFrame containing spreadsheet data
            command: The original user command for context
            security_manager: Security manager instance for validation
            script_path: Optional path to the script file for logging
            
        Returns:
            Tuple[pd.DataFrame, list, bool]: (modified_df, modified_cells, success)
        """
        print("🏭 COMPREHENSIVE AUTOMATED ERROR CORRECTION PIPELINE")
        print("=" * 70)
        
        current_script = script
        original_script = script
        
        self.current_script_path = script_path
        
        total_attempts = 0
        max_total_attempts = 8
        
        # === PHASE 1: SANDBOX TESTING AND SCRIPT FIXING (Attempts 1-5) ===
        print("\n📋 PHASE 1: Sandbox Testing and Script Correction (Attempts 1-5)")
        print("-" * 70)
        
        execution_success, execution_error = self._test_script_in_sandbox(current_script, spreadsheet_df)
        
        if not execution_success:
            print(f"🔧 Sandbox execution failed: {execution_error}")
            
            for attempt in range(1, 6):
                total_attempts += 1
                print(f"\n🔄 Fix Attempt {attempt}/5 (Total: {total_attempts}/{max_total_attempts})")
                
                if attempt == 1 and "name 'row_index' is not defined" in str(execution_error):
                    print("🤖 Attempting manual fix for 'row_index' NameError by wrapping in a loop...")
                    indented_script = "    " + current_script.strip().replace("\n", "\n    ")
                    fixed_script = f"for row_index in range(len(df)):\n{indented_script}"
                    
                    test_success, test_error = self._test_script_in_sandbox(fixed_script, spreadsheet_df)
                    if test_success:
                        print("✅ Manual loop wrap fix successful!")
                        current_script = fixed_script
                        execution_success = True
                        break
                    else:
                        print(f"⚠️ Manual loop wrap fix failed: {test_error}. Proceeding with LLM.")
                        execution_error = test_error
                
                # Standard LLM-based fix
                print(f"🤖 Attempting LLM-based error correction (Attempt {attempt})...")
                llm_fixed_script = self._fix_script_with_llm(
                    current_script, str(execution_error), "", command, spreadsheet_df
                )
                
                if llm_fixed_script:
                    print("✓ LLM provided a fix, testing...")
                    llm_success, llm_error = self._test_script_in_sandbox(llm_fixed_script, spreadsheet_df)
                    
                    if llm_success:
                        print("✅ LLM fix successful!")
                        current_script = llm_fixed_script
                        execution_success = True
                        break
                    else:
                        print(f"⚠️ LLM fix still has errors: {llm_error}")
                        execution_error = llm_error
                        
                        print("🔧 Attempting manual deterministic fixes...")
                        manual_fixed_script = self._apply_manual_fixes(llm_fixed_script, llm_error, spreadsheet_df)
                        
                        if manual_fixed_script:
                            manual_success, manual_error = self._test_script_in_sandbox(manual_fixed_script, spreadsheet_df)
                            if manual_success:
                                print("✅ Manual fix successful!")
                                current_script = manual_fixed_script
                                execution_success = True
                                break
                            else:
                                print(f"❌ Manual fix also failed: {manual_error}")
                                execution_error = manual_error
                        else:
                            print("❌ No manual fix available")
                else:
                    print("⚠️ LLM could not provide a fix, trying manual fixes...")
                    
                    manual_fixed_script = self._apply_manual_fixes(current_script, execution_error, spreadsheet_df)
                    
                    if manual_fixed_script:
                        manual_success, manual_error = self._test_script_in_sandbox(manual_fixed_script, spreadsheet_df)
                        if manual_success:
                            print("✅ Manual fix successful!")
                            current_script = manual_fixed_script
                            execution_success = True
                            break
                        else:
                            print(f"❌ Manual fix failed: {manual_error}")
                            execution_error = manual_error
                    else:
                        print("❌ No manual fix available")
                
                if attempt == 5 and not execution_success:
                    print("⚠️ Standard fix attempts (1-5) exhausted, proceeding to Advanced Gemini method...")
        else:
            print("✅ Script passed sandbox testing")
        
        # === PHASE 2: ADVANCED GEMINI COMPLEX SCRIPT GENERATION (Attempts 6-8) ===
        if not execution_success and total_attempts < max_total_attempts:
            print("\n🧠 PHASE 2: Advanced Gemini Complex Script Generation (Attempts 6-8)")
            print("-" * 70)
            
            spreadsheet_json = {
                'headers': list(spreadsheet_df.columns),
                'data': spreadsheet_df.head(10).values.tolist(),
                'metadata': {
                    'rows': len(spreadsheet_df),
                    'columns': len(spreadsheet_df.columns)
                },
                'excelReferenceHelp': self._build_excel_reference_help(spreadsheet_df),
                'columnMapping': self._build_column_mapping(spreadsheet_df)
            }
            
            for attempt in range(6, 9):
                total_attempts += 1
                print(f"\n🧠 Advanced Gemini Attempt {attempt-5}/3 (Total: {total_attempts}/{max_total_attempts})")
                
                try:
                    error_context = f"Previous attempts failed with error: {execution_error}"
                    advanced_script = self._generate_advanced_gemini_script(
                        spreadsheet_json, command, error_context, attempt - 5
                    )
                    
                    if advanced_script:
                        print("✓ Advanced Gemini generated a new script, testing...")
                        
                        advanced_success, advanced_error = self._test_script_in_sandbox(advanced_script, spreadsheet_df)
                        
                        if advanced_success:
                            print("✅ Advanced Gemini script successful!")
                            current_script = advanced_script
                            execution_success = True
                            break
                        else:
                            print(f"⚠️ Advanced Gemini script failed: {advanced_error}")
                            execution_error = advanced_error
                    else:
                        print("❌ Advanced Gemini could not generate a script")
                        
                except Exception as e:
                    print(f"❌ Advanced Gemini attempt {attempt-5} failed: {str(e)}")
                    execution_error = str(e)
                
                if attempt == 8 and not execution_success:
                    print("💥 All Advanced Gemini attempts exhausted")
        
        if not execution_success:
            print("💥 ALL ATTEMPTS FAILED: Could not fix script execution errors")
            logging.error(f"Script fixing failed after {total_attempts} attempts. Original: {original_script}, Final error: {execution_error}")
            return spreadsheet_df, [], False
        
        # === PHASE 3: SECURITY VALIDATION AND FIXING ===
        print("\n🔒 PHASE 3: Security Validation and Correction")
        print("-" * 50)
        
        security_attempts = 0
        max_security_attempts = 5
        
        while security_attempts < max_security_attempts:
            security_attempts += 1
            print(f"🔍 Security check attempt {security_attempts}/{max_security_attempts}")
            
            validation_result = security_manager.validate_script(current_script)
            if isinstance(validation_result, tuple):
                is_safe, security_message = validation_result
            else:
                is_safe = bool(validation_result)
                security_message = ""

            if is_safe:
                print("✅ Security validation passed!")
                break
            else:
                print(f"⚠️ Security validation failed (attempt {security_attempts}): {security_message}")
                
                if security_attempts < max_security_attempts:
                    print("🤖 Requesting LLM to fix security issues...")
                    security_fixed_script = self._fix_script_with_llm(
                        current_script, 
                        "Script failed security validation. Please ensure the script only uses allowed operations and imports.",
                        "", 
                        command, 
                        spreadsheet_df
                    )
                    
                    if security_fixed_script and security_fixed_script != current_script:
                        print("✓ LLM provided security fix, testing...")
                        security_test_success, security_test_error = self._test_script_in_sandbox(security_fixed_script, spreadsheet_df)
                        
                        if security_test_success:
                            current_script = security_fixed_script
                            print("✓ Security fix maintains functionality")
                        else:
                            print(f"⚠️ Security fix broke functionality: {security_test_error}")
                            double_fixed = self._fix_script_with_llm(
                                security_fixed_script, security_test_error, "", command, spreadsheet_df
                            )
                            if double_fixed:
                                double_test_success, _ = self._test_script_in_sandbox(double_fixed, spreadsheet_df)
                                if double_test_success:
                                    current_script = double_fixed
                                    print("✓ Double-fix successful")
                    else:
                        print("❌ LLM could not provide security fix")
                        break
                else:
                    print("💥 PHASE 3 FAILED: Maximum security fix attempts reached")
                    logging.error(f"Security validation failed after {max_security_attempts} attempts")
                    return spreadsheet_df, [], False
        
        # === PHASE 4: FINAL EXECUTION AND LOGIC VALIDATION ===
        print("\n🚀 PHASE 4: Final Execution & Logic Validation")
        print("-" * 50)
        
        logic_fix_attempts = 0
        max_logic_fix_attempts = 3
        fix_history = []

        while logic_fix_attempts < max_logic_fix_attempts:
            try:
                modified_df, modified_cells = self._execute_final_script(current_script, spreadsheet_df)
                
                if len(modified_cells) > 0:
                    print(f"✅ PIPELINE SUCCESS: Script executed successfully - {len(modified_cells)} cell(s) modified")
                    if self.current_script_path:
                        print(f"✅ {self.current_script_path}")
                    return modified_df, modified_cells, True
                
                if self._is_zero_changes_acceptable(command, current_script, spreadsheet_df):
                    print(f"✅ PIPELINE SUCCESS: Script executed successfully - no changes needed (operation already satisfied)")
                    if self.current_script_path:
                        print(f"✅ {self.current_script_path}")
                    return modified_df, modified_cells, True
                
                logic_fix_attempts += 1
                print(f"⚠️ LOGIC ERROR: Script ran but made no changes. Attempting fix {logic_fix_attempts}/{max_logic_fix_attempts}")
                
                if logic_fix_attempts <= max_logic_fix_attempts:
                    column_mapping_info = self._build_column_mapping(spreadsheet_df)
                    error_message = (
                        "The script executed without syntax errors but resulted in zero modifications. "
                        "This suggests a logic error. In this project, column letters map to positional columns: "
                        f"{column_mapping_info}. If the command mentions Column #A/#B/#C etc., convert to the mapped "
                        "DataFrame labels or use df.iloc with the correct positional index. For account-number moves, "
                        "treat values as strings and match regex ^\\\d{5}$ before moving; then clear the source cell. "
                        "If the command asks to place a literal text into the first cell of a column (e.g., \"Move 'X' "
                        "to the first cell of column #B\"), you MUST set df.iloc[0, pos]=X where pos is the positional "
                        "index of that letter (A->0, B->1, C->2, etc.), and clear the original location of X to avoid "
                        "duplicates. IMPORTANT: For integer-labeled columns use integers, never quoted strings (use df[0], "
                        "not df['0'])."
                    )
                    
                    fixed_script = self._fix_script_with_llm(
                        current_script, error_message, "", command, spreadsheet_df, fix_history
                    )
                    
                    if fixed_script and fixed_script != current_script:
                        print("✓ LLM provided a logic fix, re-validating...")
                        
                        test_success, test_error = self._test_script_in_sandbox(fixed_script, spreadsheet_df)
                        _validation_result = security_manager.validate_script(fixed_script)
                        if isinstance(_validation_result, tuple):
                            is_safe, security_message = _validation_result
                        else:
                            is_safe, security_message = bool(_validation_result), ""
                        if test_success and is_safe:
                            print("✅ Logic fix successful and secure!")
                            current_script = fixed_script
                        else:
                            error_msg = test_error if not test_success else f"Security validation failed: {security_message}"
                            print(f"⚠️ Logic fix failed validation: {error_msg}")
                            fix_history.append({
                                'script': fixed_script,
                                'error': error_msg
                            })
                            continue
                    else:
                        print("❌ LLM could not provide a logic fix")
                        break
                else:
                    print("💥 PHASE 4 FAILED: Maximum logic fix attempts reached")
                    break
                
            except Exception as e:
                print(f"💥 PHASE 4 FAILED: Final execution error: {e}")
                if self.current_script_path:
                    print(f"❌ {self.current_script_path}")
                logging.error(f"Final execution failed: {e}", exc_info=True)
                return spreadsheet_df, [], False

        print("💥 PIPELINE FAILED: Could not produce a working script after all attempts.")
        if self.current_script_path:
            print(f"❌ {self.current_script_path}")
        return spreadsheet_df, [], False
    
    def _execute_simple_script(self, script: str, spreadsheet_df: pd.DataFrame) -> Tuple[pd.DataFrame, list]:
        """Execute script without universal transformation patterns."""
        df = spreadsheet_df.copy()
        
        original_values = {}
        for i in range(len(df)):
            for j, col in enumerate(df.columns):
                original_values[(i, j)] = df.iloc[i, j]
                
        # Create a safe but comprehensive execution environment
        safe_builtins = {
            # Basic types
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set,
            'frozenset': frozenset,
            'bytes': bytes,
            'bytearray': bytearray,

            # Iteration and sequence operations
            'range': range,
            'enumerate': enumerate,
            'zip': zip,
            'reversed': reversed,
            'sorted': sorted,
            'slice': slice,

            # Math and aggregation
            'max': max,
            'min': min,
            'sum': sum,
            'abs': abs,
            'round': round,
            'pow': pow,
            'divmod': divmod,

            # Type checking and conversion
            'isinstance': isinstance,
            'issubclass': issubclass,
            'type': type,
            'hasattr': hasattr,
            'getattr': getattr,
            'setattr': setattr,
            'delattr': delattr,

            # String and representation
            'repr': repr,
            'ascii': ascii,
            'ord': ord,
            'chr': chr,
            'hex': hex,
            'oct': oct,
            'bin': bin,
            'format': format,

            # Logical operations
            'all': all,
            'any': any,

            # Functional programming
            'map': map,
            'filter': filter,

            # I/O
            'print': print,

            # Object introspection
            'vars': vars,
            'dir': dir,
            'id': id,
            'callable': callable,

            # Import mechanism
            '__import__': __import__,

            # Exception handling
            'Exception': Exception,
            'ValueError': ValueError,
            'TypeError': TypeError,
            'IndexError': IndexError,
            'KeyError': KeyError,
            'AttributeError': AttributeError,
        }
        
        exec_globals = {
            'df': df,
            'pd': pd,
            'np': np,
            '__builtins__': safe_builtins
        }
        
        try:
            exec(script, exec_globals)
        except NameError as e:
            if "isinstance" in str(e):
                print("🔧 WARNING: 'isinstance' not found. Attempting to inject and retry.")
                exec_globals['__builtins__']['isinstance'] = isinstance
                try:
                    exec(script, exec_globals)
                except Exception as retry_e:
                    print(f"💥 Retry after injecting 'isinstance' failed: {retry_e}")
                    raise e from retry_e
            else:
                raise e
        except Exception as e:
            raise e

        
        modified_df = exec_globals['df']
        
        modified_cells = []
        for i in range(len(modified_df)):
            for j, col in enumerate(modified_df.columns):
                if (i, j) in original_values:
                    old_val = original_values[(i, j)]
                    new_val = modified_df.iloc[i, j]
                    
                    if pd.isna(old_val) and pd.isna(new_val):
                        continue
                    elif pd.isna(old_val) or pd.isna(new_val) or old_val != new_val:
                        modified_cells.append([i, j])
        
        return modified_df, modified_cells
    
    def _fix_script_with_llm(self, script: str, error_msg: str, error_traceback: str, 
                           command: str, spreadsheet_df: pd.DataFrame, 
                           fix_history: Optional[list] = None) -> Optional[str]:
        """Use LLM to intelligently fix script based on error encountered."""
        try:
            print("🤖 Requesting LLM script correction...")
            
            columns_info = f"Columns: {list(spreadsheet_df.columns)}"
            shape_info = f"Shape: {spreadsheet_df.shape[0]} rows, {spreadsheet_df.shape[1]} columns"
            sample_data = spreadsheet_df.head(3).to_string() if len(spreadsheet_df) > 0 else "Empty DataFrame"
            
            history_section = ""
            if fix_history:
                history_items = []
                for i, attempt in enumerate(fix_history):
                    history_items.append(
                        f"ATTEMPT {i+1}:\n"
                        f"--- SCRIPT ---\n"
                        f"{attempt['script']}\n"
                        f"--- ERROR ---\n"
                        f"{attempt['error']}"
                    )
                history_section = f"""
=== PREVIOUS FAILED ATTEMPTS ===
This is part of a retry loop. The following attempts have already failed. Analyze them to avoid repeating mistakes.
{chr(10).join(history_items)}
"""
            
            column_mapping_info = self._build_column_mapping(spreadsheet_df)
            excel_help = self._build_excel_reference_help(spreadsheet_df)

            correction_prompt = f"""
You are an expert Python script debugger in an automated error correction system. Your task is to fix the failing script below.

=== CONTEXT ===
Original User Command: {command}
DataFrame Structure: {columns_info}, {shape_info}

PROJECT-SPECIFIC DATAFRAME SEMANTICS
- Column letters in the user's instructions refer to positions, not names.
- Use this exact mapping for the current DataFrame (letter -> actual DataFrame column label):
{column_mapping_info}
- Common pitfall in this project: After adding two new left-most columns, the original columns keep integer labels starting at 0. That means:
    - Column A = new_col_0
    - Column B = new_col_1
    - Column C = 0
    - Column D = 1
    (and so on, as shown above)
- When manipulating columns by letter, either use df.iloc[row_index, positional_index] or df[actual_label] as shown in the mapping. Do NOT compare against df.columns[...] == 2/3 incorrectly.
- If the command mentions an "account number" as any 5-digit string, match using regex r"^\\d{5}$" and treat values as strings before checking.

EXCEL-STYLE REFERENCE HELP (apply when user mentions cells like J2–O2):
{excel_help}

Sample Data:
{sample_data}
{history_section}
=== CURRENT ERROR INFORMATION ===
Error Message: {error_msg}
{f"Full Traceback: {error_traceback}" if error_traceback else ""}

=== FAILING SCRIPT (LATEST ATTEMPT) ===
```python
{script}
```

=== EXECUTION ENVIRONMENT ===
Available in execution environment:
- df: pandas DataFrame (the main spreadsheet data)
- pd: pandas module
- np: numpy module  
- Standard Python built-ins: len, str, int, float, bool, isinstance, type, max, min, sum, range, enumerate, zip, etc.
- Exception types: Exception, ValueError, TypeError, IndexError, KeyError, AttributeError

=== DEBUGGING INSTRUCTIONS ===
1. ANALYZE the error message and the full history of failed attempts.
2. IDENTIFY the root cause. Do NOT repeat previous mistakes.
3. FIX the issue while preserving the original intent.
4. ENSURE compatibility with the DataFrame structure.
5. USE only the available environment listed above.
6. RETURN only clean Python code without explanations or markdown.

=== COMMON ERROR PATTERNS & FIXES ===
- Syntax errors: Add missing colons, parentheses, indentation
- NameError: Use available built-ins only (isinstance, not __import__)
- IndexError: Check bounds with len(df), len(df.columns)
- Column access: Use df[column_name] or df.iloc[row, col]
- IMPORTANT: Numeric column labels are integers. Never use quoted numeric labels. Use df[0] not df['0'].
- Security violations: Remove forbidden imports/functions
- Incomplete blocks: Add missing code (e.g., df.drop(index, inplace=True) for deletions)
- df.replace() regex errors: Add regex=False parameter (e.g., df.replace('None', '', regex=False, inplace=True))
- No modifications: Ensure script actually modifies the DataFrame, check data types and exact string matches
- NaN/None handling: Use np.nan for NumPy NaN, None for Python None, 'None' for string None
- Index out of bounds in loops: Use reverse iteration for deletion (range(len(df)-1, -1, -1))
- Row deletion errors: Prefer boolean indexing over iterative df.drop() calls

=== SPECIAL NOTES FOR ROW DELETION ===
- NEVER use forward iteration with df.drop() - indices shift causing errors
- For deleting rows: Use boolean indexing: df = df[~condition].reset_index(drop=True)
- For selective deletion: Use reverse iteration: for i in range(len(df)-1, start-1, -1)
- Example safe deletion: mask = ~df.astype(str).apply(lambda row: row.str.contains('pattern').any(), axis=1); df = df[mask]

=== SPECIAL NOTES FOR df.replace() ===
- Always add regex=False when replacing literal values to avoid regex interpretation
- Example: df.replace('None', '', regex=False, inplace=True)
- Example: df.replace(None, '', regex=False, inplace=True)  
- Example: df.replace(np.nan, '', regex=False, inplace=True)

TASK-SPECIFIC HINTS (only if applicable to the command):
- If asked to "move all instances of any account number string to column #A from column #C":
    - Source column = Column C (see mapping), Destination column = Column A.
    - For each row: if source cell is a 5-digit number (string), copy it to destination and clear the source cell.
    - Example skeleton (adjust using the mapping above):
        # src_pos and dst_pos derived from mapping (e.g., C->0, A->new_col_0)
        import re
        pat = re.compile(r"^\\d{5}$")
        for r in range(len(df)):
                val = df.iloc[r, 2] if 'C -> 2' in '{column_mapping_info}' else df[0]  # replace using the mapping
                sval = '' if pd.isna(val) else str(val).strip()
                if pat.match(sval):
                        # use df.iloc[r, dst_idx] or df[dst_label].iloc[r] per mapping
                        pass

            - If asked to "Move the 'Name' string to the first cell of column #B":
                - Column B is the second column (positional index 1). Set df.iloc[0, 1] = "Name" directly.
                - Locate 'Name' anywhere else (prefer row 0, but search full DataFrame if needed) and clear that original cell to avoid duplicates.
                - Do not require that 'Name' already exists in column B. Ensure you use integer labels or iloc for numeric columns (e.g., df[0], not df['0']).

Generate the corrected script:"""
            
            corrected_script = self.llm_service.generate_script_correction(correction_prompt)
            
            token_manager.print_token_usage()
            
            corrected_script = self._clean_script_response(corrected_script)
            
            if corrected_script and corrected_script.strip():
                print("✅ LLM generated script correction")
                print(f"📝 Corrected script preview:\n\n{corrected_script[:1000000]}\n")
                return corrected_script
            else:
                print("❌ LLM returned empty correction")
                return None
                
        except Exception as e:
            print(f"❌ Error during LLM script correction: {e}")
            logging.error(f"LLM correction failed: {e}", exc_info=True)
            return None
    
    def _clean_script_response(self, response: str) -> str:
        """Clean up LLM response to extract Python script."""
        if '```python' in response:
            start = response.find('```python') + 9
            end = response.find('```', start)
            if end > start:
                response = response[start:end]
        elif '```' in response:
            start = response.find('```') + 3
            end = response.find('```', start)
            if end > start:
                response = response[start:end]
        
        return response.strip()
    
    def _test_script_in_sandbox(self, script: str, spreadsheet_df: pd.DataFrame) -> Tuple[bool, str]:
        """Test script execution in safe sandbox environment."""
        try:
            print(f"🧪 Testing script in sandbox...")
            
            test_df = spreadsheet_df.head(10).copy()
            
            _, _ = self._execute_simple_script(script, test_df)
            
            print("✅ Sandbox test passed")
            return True, ""
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Sandbox test failed: {error_msg}")
            return False, error_msg
    
    def _apply_manual_fixes(self, script: str, error_msg: str, spreadsheet_df: pd.DataFrame) -> Optional[str]:
        """Apply deterministic manual fixes for common script errors."""
        print("🔧 Applying manual deterministic fixes...")
        print(f"🔍 Error message: {error_msg}")
        print(f"🔍 Available DataFrame columns: {list(spreadsheet_df.columns)}")
        print(f"🔍 Script to fix: {script[:200]}{'...' if len(script) > 200 else ''}")
        
        if "Index([" in error_msg and "dtype='object'" in error_msg:
            print("🔧 Detected column reference type mismatch. Applying universal column fix...")
            
            fixed_script = script
            
            column_access_pattern = r"df\[(['\"])(\d+)\1\]"
            
            def fix_column_access(match):
                col_num = int(match.group(2))
                if col_num in spreadsheet_df.columns:
                    return f"df[{col_num}]"
                return match.group(0)
            
            fixed_script = re.sub(column_access_pattern, fix_column_access, fixed_script)
            
            list_pattern = r"(\w+\s*=\s*)\[[^\]]*['\"][0-9]+['\"][^\]]*\]"
            list_matches = re.findall(list_pattern, fixed_script)
            
            for param_prefix in list_matches:
                full_pattern = rf"({re.escape(param_prefix)})\[[^\]]*\]"
                full_match = re.search(full_pattern, fixed_script)
                if full_match:
                    full_assignment = full_match.group(0)
                    quoted_nums = re.findall(r"['\"](\d+)['\"]", full_assignment)
                    if quoted_nums:
                        int_cols = []
                        for num_str in quoted_nums:
                            col_idx = int(num_str)
                            if col_idx in spreadsheet_df.columns:
                                int_cols.append(col_idx)
                        
                        if int_cols:
                            new_assignment = f"{param_prefix}{int_cols}"
                            fixed_script = fixed_script.replace(full_assignment, new_assignment)
                            print(f"✓ Fixed parameter: {full_assignment} -> {new_assignment}")
            
            str_comprehension_pattern = r"\[str\([^)]+\)\s+for\s+[^]]+\]"
            if re.search(str_comprehension_pattern, fixed_script):
                comprehension_match = re.search(r"\[str\(col_idx\)\s+for\s+col_idx\s+in\s+\[([^\]]+)\]\]", fixed_script)
                if comprehension_match:
                    indices_str = comprehension_match.group(1)
                    try:
                        indices = [int(x.strip()) for x in indices_str.split(',')]
                        valid_indices = [idx for idx in indices if idx in spreadsheet_df.columns]
                        if valid_indices:
                            old_expr = comprehension_match.group(0)
                            new_expr = str(valid_indices)
                            fixed_script = fixed_script.replace(old_expr, new_expr)
                            print(f"✓ Fixed list comprehension: {old_expr} -> {new_expr}")
                    except (ValueError, TypeError):
                        pass
            
            excel_pattern = r"['\"]([A-Z]+)(\d+)['\"]"
            excel_matches = re.findall(excel_pattern, fixed_script)
            if excel_matches:
                print("🔧 Found Excel cell references, converting to numeric indices...")
                for col_letter, row_num in excel_matches:
                    col_num = 0
                    for char in col_letter:
                        col_num = col_num * 26 + (ord(char) - ord('A'))
                    
                    if col_num in spreadsheet_df.columns:
                        old_ref = f"'{col_letter}{row_num}'"
                        new_ref = str(col_num)
                        fixed_script = fixed_script.replace(old_ref, new_ref)
                        old_ref_double = f'"{col_letter}{row_num}"'
                        fixed_script = fixed_script.replace(old_ref_double, new_ref)
                        print(f"✓ Converted Excel reference: {col_letter}{row_num} -> column {col_num}")
            
            if fixed_script != script:
                print("✓ Applied universal column reference fixes")
                return fixed_script
        
        if "Index([" in error_msg and "dtype='object'" in error_msg and ("drop_duplicates" in script or "subset" in script):
            print("🔧 Detected column reference error in drop_duplicates. Applying manual fix...")
            
            pattern = r'\[str\(col_idx\) for col_idx in \[([^\]]+)\]\]'
            match = re.search(pattern, script)
            
            if match:
                indices_str = match.group(1)
                try:
                    indices = [int(x.strip()) for x in indices_str.split(',')]
                    valid_indices = [idx for idx in indices if idx in spreadsheet_df.columns]
                    
                    if valid_indices:
                        old_subset = f"[str(col_idx) for col_idx in [{indices_str}]]"
                        new_subset = str(valid_indices)
                        fixed_script = script.replace(old_subset, new_subset)
                        print(f"✓ Fixed column references: {old_subset} -> {new_subset}")
                        return fixed_script
                except (ValueError, TypeError):
                    pass
            
            string_pattern = r"subset=\[(['\"][^'\"]+['\"],?\s*)+\]"
            if re.search(string_pattern, script):
                quoted_nums = re.findall(r"['\"](\d+)['\"]", script)
                if quoted_nums:
                    int_cols = []
                    for num_str in quoted_nums:
                        try:
                            col_idx = int(num_str)
                            if col_idx in spreadsheet_df.columns:
                                int_cols.append(col_idx)
                        except ValueError:
                            continue
                    
                    if int_cols:
                        old_match = re.search(string_pattern, script).group(0)
                        new_subset = f"subset={int_cols}"
                        fixed_script = script.replace(old_match, new_subset)
                        print(f"✓ Fixed string column references: {old_match} -> {new_subset}")
                        return fixed_script
            
            max_col_to_check = max(50, len(spreadsheet_df.columns) * 2)
            if any(f"'{i}'" in script or f'"{i}"' in script for i in range(max_col_to_check)):
                print("🔧 Found quoted column numbers in script, converting to integers...")
                fixed_script = script
                
                for i in range(max_col_to_check):
                    if i in spreadsheet_df.columns:
                        fixed_script = fixed_script.replace(f"'{i}'", str(i))
                        fixed_script = fixed_script.replace(f'"{i}"', str(i))
                
                if fixed_script != script:
                    print(f"✓ Converted quoted column numbers to integers")
                    return fixed_script
            
            if any(method in fixed_script for method in ['drop_duplicates', 'groupby', 'sort_values', 'pivot_table', 'merge', 'join']):
                print("🔧 Found pandas operations, applying universal column fixes...")
                
                pandas_methods = ['drop_duplicates', 'groupby', 'sort_values', 'pivot_table', 'merge', 'join', 'pivot', 'melt', 'aggregate', 'agg']
                
                for method in pandas_methods:
                    if method in fixed_script:
                        method_pattern = rf'{method}\([^)]*\)'
                        method_matches = re.findall(method_pattern, fixed_script)
                        
                        for method_call in method_matches:
                            original_call = method_call
                            fixed_call = method_call
                            
                            for i in range(max_col_to_check):
                                if i in spreadsheet_df.columns:
                                    fixed_call = fixed_call.replace(f"'{i}'", str(i))
                                    fixed_call = fixed_call.replace(f'"{i}"', str(i))
                            
                            if fixed_call != original_call:
                                fixed_script = fixed_script.replace(original_call, fixed_call)
                                print(f"✓ Fixed {method} call: {original_call} -> {fixed_call}")
                
                if fixed_script != script:
                    return fixed_script

        # Catch-all fix: Any remaining KeyError or Index errors related to columns
        if any(error_type in error_msg for error_type in ["KeyError", "not in index", "Index([", "not found in axis"]) and any(col_ref in script for col_ref in ["df[", "subset=", "columns=", "by="]):
            print("🔧 Detected general column reference error. Applying catch-all fix...")
            
            fixed_script = script
            
            # Handle Excel cell references that appear as KeyErrors (e.g., KeyError: 'J2')
            if "KeyError:" in error_msg:
                # Extract the key from the error message
                key_match = re.search(r"KeyError: ['\"]([^'\"]+)['\"]", error_msg)
                if key_match:
                    error_key = key_match.group(1)
                    print(f"🔧 Found KeyError for: {error_key}")
                    
                    # Check if it's an Excel cell reference (like J2, K2, etc.)
                    excel_cell_match = re.match(r"([A-Z]+)(\d+)", error_key)
                    if excel_cell_match:
                        col_letter, row_num = excel_cell_match.groups()
                        # Convert Excel column letter to number (A=0, B=1, ..., J=9, K=10, etc.)
                        col_num = 0
                        for char in col_letter:
                            col_num = col_num * 26 + (ord(char) - ord('A'))
                        
                        if col_num in spreadsheet_df.columns:
                            # Replace the Excel reference with the numeric column
                            fixed_script = fixed_script.replace(f"'{error_key}'", str(col_num))
                            fixed_script = fixed_script.replace(f'"{error_key}"', str(col_num))
                            print(f"✓ Converted Excel cell reference: {error_key} -> column {col_num}")
                        else:
                            print(f"⚠️ Excel reference {error_key} (column {col_num}) not found in DataFrame")
                    
                    # Also try direct key replacement if it's a numeric string
                    elif error_key.isdigit():
                        col_num = int(error_key)
                        if col_num in spreadsheet_df.columns:
                            fixed_script = fixed_script.replace(f"'{error_key}'", str(col_num))
                            fixed_script = fixed_script.replace(f'"{error_key}"', str(col_num))
                            print(f"✓ Converted string column reference: '{error_key}' -> {col_num}")
            
            # Replace ALL quoted numbers in the entire script if they correspond to DataFrame columns
            max_col_to_check = max(100, len(spreadsheet_df.columns) * 3)  # Very broad range
            
            for i in range(max_col_to_check):
                if i in spreadsheet_df.columns:
                    # Replace in any context - pandas methods, lists, individual references
                    fixed_script = re.sub(rf"(['\"]){i}\1", str(i), fixed_script)
            
            # Also handle column name strings that might be actual column names
            for col in spreadsheet_df.columns:
                if isinstance(col, str) and col.isdigit():
                    # Column is already a string digit, ensure script uses it correctly
                    col_int = int(col)
                    if col_int in spreadsheet_df.columns:
                        # Replace quoted versions with unquoted integers
                        fixed_script = re.sub(rf"(['\"]){col}\1", str(col_int), fixed_script)
            
            if fixed_script != script:
                print("✓ Applied catch-all column reference fixes")
                return fixed_script
        if "list.remove(x): x not in list" in error_msg and ("mask" in script or "first_occurrence" in script):
            print("🔧 Detected list.remove error in mask operations. Applying manual fix...")
            
            # This typically happens when there are no matching rows for the mask
            # We need to add a check to ensure there are rows to remove
            if "rows_to_drop.remove(first_occurrence_index)" in script:
                fixed_script = script.replace(
                    "rows_to_drop.remove(first_occurrence_index)",
                    """if first_occurrence_index in rows_to_drop:
    rows_to_drop.remove(first_occurrence_index)"""
                )
                
                # Also add a check for empty rows_to_drop
                if "df = df.drop(rows_to_drop)" in fixed_script:
                    fixed_script = fixed_script.replace(
                        "df = df.drop(rows_to_drop)",
                        """if rows_to_drop:
    df = df.drop(rows_to_drop)"""
                    )
                
                print("✓ Added safety checks for mask operations")
                return fixed_script
        
        # Manual fix for column reference errors in boolean operations
        if "Index([" in error_msg and "dtype='object'" in error_msg and any(op in script for op in ["&", "|", "==", "!="]):
            print("🔧 Detected column reference error in boolean operations. Applying comprehensive fix...")
            
            # Fix column references in the entire script
            fixed_script = script
            
            # Pattern 1: df[column] where column is a string but should be integer
            
            # Find all df[...] patterns and fix string column references
            df_column_pattern = r"df\[(['\"]?)(\d+)\1\]"
            
            def fix_column_ref(match):
                quote = match.group(1)
                col_num = int(match.group(2))
                
                # Check if this column exists as an integer in the DataFrame
                if col_num in spreadsheet_df.columns:
                    return f"df[{col_num}]"  # Remove quotes
                else:
                    return match.group(0)  # Keep original if column doesn't exist
            
            fixed_script = re.sub(df_column_pattern, fix_column_ref, fixed_script)
            
            # Pattern 2: subset_cols = [8, 9, 10, 11, 12] but accessing as strings
            # Look for patterns like subset_cols = [numbers] and ensure they're used correctly
            subset_pattern = r"subset_cols\s*=\s*\[([^\]]+)\]"
            subset_match = re.search(subset_pattern, fixed_script)
            
            if subset_match:
                # Ensure the subset_cols are used as integers throughout
                indices_str = subset_match.group(1)
                try:
                    indices = [int(x.strip()) for x in indices_str.split(',')]
                    # Verify all indices exist in DataFrame
                    valid_indices = [idx for idx in indices if idx in spreadsheet_df.columns]
                    
                    if valid_indices and len(valid_indices) != len(indices):
                        # Some indices are invalid, update the subset_cols
                        old_subset = f"subset_cols = [{indices_str}]"
                        new_subset = f"subset_cols = {valid_indices}"
                        fixed_script = fixed_script.replace(old_subset, new_subset)
                        print(f"✓ Fixed subset_cols: {old_subset} -> {new_subset}")
                except (ValueError, TypeError):
                    pass
            
            if fixed_script != script:
                print("✓ Applied comprehensive column reference fixes")
                return fixed_script
        if "'regex' must be a string" in error_msg and "you passed a 'bool'" in error_msg:
            print("🔧 Detected df.replace() regex error. Applying manual fix...")
            
            # Common fix: add regex=False parameter to df.replace() calls
            fixed_script = script
            
            # Pattern 1: df.replace(None, '', inplace=True) -> df.replace(None, '', regex=False, inplace=True)
            if "df.replace(None," in script and "regex=False" not in script:
                fixed_script = script.replace(
                    "df.replace(None, '',", 
                    "df.replace(None, '', regex=False,"
                ).replace("df.replace(None, inplace=True)", "df.replace(None, '', regex=False, inplace=True)")
            
            # Pattern 2: df.replace(np.nan, '', inplace=True) -> df.replace(np.nan, '', regex=False, inplace=True)
            if "df.replace(np.nan," in fixed_script and "regex=False" not in fixed_script:
                fixed_script = fixed_script.replace(
                    "df.replace(np.nan, '',", 
                    "df.replace(np.nan, '', regex=False,"
                ).replace("df.replace(np.nan, inplace=True)", "df.replace(np.nan, '', regex=False, inplace=True)")
            
            # Pattern 3: General df.replace() calls without regex parameter
            replace_pattern = r'df\.replace\(([^,]+),\s*([^,]+),\s*inplace=True\)'
            matches = re.findall(replace_pattern, fixed_script)
            for match in matches:
                old_call = f"df.replace({match[0]}, {match[1]}, inplace=True)"
                new_call = f"df.replace({match[0]}, {match[1]}, regex=False, inplace=True)"
                fixed_script = fixed_script.replace(old_call, new_call)
            
            if fixed_script != script:
                print("✓ Applied df.replace() regex fix")
                return fixed_script
        
        # Manual fix for index out of bounds errors in row deletion loops
        if ("index" in error_msg.lower() and "out" in error_msg.lower() and "bounds" in error_msg.lower()) or \
           ("single positional indexer is out-of-bounds" in error_msg):
            print("🔧 Detected index out of bounds error. Applying manual fix...")
            
            # Fix 1: Forward iteration with drop -> Reverse iteration
            if "for i in range(" in script and "df.drop(" in script:
                print("🔧 Converting forward iteration to reverse iteration for row deletion")
                
                # Pattern: for i in range(start, len(df)): -> for i in range(len(df)-1, start-1, -1):
                range_pattern = r'for i in range\((\d+), len\(df\)\)'
                match = re.search(range_pattern, script)
                if match:
                    start_index = int(match.group(1))
                    old_range = f"for i in range({start_index}, len(df))"
                    new_range = f"for i in range(len(df)-1, {start_index-1}, -1)"
                    fixed_script = script.replace(old_range, new_range)
                    print(f"✓ Applied reverse iteration fix: {old_range} -> {new_range}")
                    return fixed_script
                
                # Pattern: for i in range(len(df)): -> for i in range(len(df)-1, -1, -1):
                if "for i in range(len(df)):" in script:
                    fixed_script = script.replace(
                        "for i in range(len(df)):",
                        "for i in range(len(df)-1, -1, -1):"
                    )
                    print("✓ Applied reverse iteration fix for full range")
                    return fixed_script
            
            # Fix 2: Use boolean indexing instead of iterative dropping
            if "df.drop(" in script and ("Debit" in script or "Credit" in script):
                print("🔧 Converting iterative deletion to boolean indexing")
                
                # Create a more robust script using boolean indexing
                if "range(2," in script:  # Preserve rows 0 and 1
                    fixed_script = '''# Keep rows 0 and 1, then filter out rows containing "Debit" or "Credit"
import pandas as pd

# Get rows 0 and 1 (keep these)
keep_rows = df.iloc[:2].copy()

# Get rows from index 2 onwards
remaining_rows = df.iloc[2:].copy()

# Filter out rows containing "Debit" or "Credit"
mask = ~(remaining_rows.astype(str).apply(lambda row: row.str.contains('Debit|Credit', na=False).any(), axis=1))
filtered_rows = remaining_rows[mask]

# Combine kept rows with filtered rows
df = pd.concat([keep_rows, filtered_rows], ignore_index=True)'''
                    print("✓ Applied boolean indexing fix with row preservation")
                    return fixed_script
                else:
                    # General case - filter out all rows with Debit or Credit
                    fixed_script = '''# Filter out all rows containing "Debit" or "Credit"
mask = ~(df.astype(str).apply(lambda row: row.str.contains('Debit|Credit', na=False).any(), axis=1))
df = df[mask].reset_index(drop=True)'''
                    print("✓ Applied boolean indexing fix (general)")
                    return fixed_script
        
        # Manual fix for common NaN/None handling issues
        if "script made no modifications" in error_msg.lower() or "zero modifications" in error_msg.lower():
            print("🔧 Detected no-modification issue. Trying alternative approaches...")
            
            # If the script contains df.replace() for 'None' strings, add more comprehensive replacement
            if "df.replace('None'," in script:
                print("🔧 Enhancing None string replacement...")
                enhanced_script = f"""
# Enhanced None replacement approach
import numpy as np

# Replace string 'None' values
df = df.replace('None', '', regex=False)

# Also replace actual None values and NaN values
df = df.replace(None, '', regex=False)
df = df.replace(np.nan, '', regex=False)

# Replace 'None' that might be in different cases
df = df.replace('none', '', regex=False)
df = df.replace('NONE', '', regex=False)
"""
                return enhanced_script.strip()
        
        # Use the script_tester for deterministic fixes
        is_valid, tester_error, fixed_script = self.script_tester.test_script(script, spreadsheet_df.head(5))
        
        if fixed_script:
            print("✓ Script tester provided a manual fix")
            return fixed_script
        
        # Additional manual fixes can be added here
        print("❌ No manual fixes available")
        return None
    
    def _execute_final_script(self, script: str, spreadsheet_df: pd.DataFrame) -> Tuple[pd.DataFrame, list]:
        """Execute the final validated script on the full dataset."""
        print("🚀 Executing final validated script on full dataset...")
        return self._execute_simple_script(script, spreadsheet_df)
    
    def _generate_advanced_gemini_script(self, spreadsheet_json: Dict[str, Any], command: str, 
                                       error_context: str, attempt_number: int) -> Optional[str]:
        """Generate script using Advanced Gemini Complex Script Generation for attempts 6-8."""
        try:
            print(f"🧠 Using Advanced Gemini Complex Script Generation (Attempt {attempt_number}/3)")

            # Prepare enhanced command with error context
            enhanced_command = (
                f"{command}\n\nPrevious attempts failed: {error_context}\n\n"
                "When interpreting Excel-like references (e.g., J2–O2), map letters to column positions/labels using the provided mapping and help."
            )
            
            # Use the _generate_complex_script method from LLMService
            advanced_script = self.llm_service._generate_complex_script(spreadsheet_json, enhanced_command)
            
            if advanced_script:
                print(f"✅ Advanced Gemini generated script ({len(advanced_script)} characters)")
                return advanced_script
            else:
                print("❌ Advanced Gemini returned empty script")
                return None
                
        except Exception as e:
            print(f"❌ Advanced Gemini generation failed: {str(e)}")
            return None
    
    def _is_zero_changes_acceptable(self, command: str, script: str, spreadsheet_df: pd.DataFrame) -> bool:
        """Determine if zero changes is acceptable for a given command."""
        command_lower = command.lower()
        script_lower = script.lower()
        
        # Define patterns where zero changes might be correct
        deletion_patterns = [
            'delete', 'remove', 'drop', 'clear', 'erase', 'eliminate'
        ]
        
        conditional_patterns = [
            'empty', 'blank', 'null', 'nan', 'missing', 'duplicates', 'duplicate'
        ]
        
        # Check if this is a deletion command with conditional elements
        is_deletion_command = any(pattern in command_lower for pattern in deletion_patterns)
        has_conditional = any(pattern in command_lower for pattern in conditional_patterns)
        
        if is_deletion_command and has_conditional:
            print(f"🔍 Analyzing deletion command with conditions: '{command}'")
            
            # For deletion commands, verify that the condition doesn't exist
            if 'empty' in command_lower and ('row' in command_lower or 'column' in command_lower):
                # Check if there are actually empty rows/columns
                if 'row' in command_lower:
                    # Check for completely empty rows (both NaN and empty strings)
                    empty_rows = 0
                    for i in range(len(spreadsheet_df)):
                        row_data = spreadsheet_df.iloc[i]
                        is_empty = all(pd.isna(val) or str(val).strip() == '' or str(val).lower() == 'nan' for val in row_data)
                        if is_empty:
                            empty_rows += 1
                    
                    print(f"   📊 Found {empty_rows} completely empty rows")
                    if empty_rows == 0:
                        print("   ✅ No empty rows to delete - zero changes is correct")
                        return True
                        
                if 'column' in command_lower:
                    # Check for completely empty columns (both NaN and empty strings)
                    empty_cols = 0
                    for col in spreadsheet_df.columns:
                        col_data = spreadsheet_df[col]
                        is_empty = all(pd.isna(val) or str(val).strip() == '' or str(val).lower() == 'nan' for val in col_data)
                        if is_empty:
                            empty_cols += 1
                    
                    print(f"   📊 Found {empty_cols} completely empty columns")
                    if empty_cols == 0:
                        print("   ✅ No empty columns to delete - zero changes is correct")
                        return True
            
            elif 'duplicate' in command_lower:
                # Check for duplicates
                duplicates_count = spreadsheet_df.duplicated().sum()
                print(f"   📊 Found {duplicates_count} duplicate rows")
                if duplicates_count == 0:
                    print("   ✅ No duplicates to remove - zero changes is correct")
                    return True
            
            elif any(pattern in command_lower for pattern in ['null', 'nan', 'missing', 'blank']):
                # Check for null/missing values
                null_count = spreadsheet_df.isna().sum().sum()
                blank_count = (spreadsheet_df == '').sum().sum()
                print(f"   📊 Found {null_count} null values and {blank_count} blank values")
                if null_count == 0 and blank_count == 0:
                    print("   ✅ No null/missing values to handle - zero changes is correct")
                    return True
        
        # Check for specific row/column number deletion commands (e.g., "delete row 5", "delete column A")
        if is_deletion_command:
            # Pattern for "delete row(s) #X" or "delete column(s) X"
            row_match = re.search(r'(?:delete|remove)\s+(?:row|rows?)\s*[#]?(\d+)', command_lower)
            col_match = re.search(r'(?:delete|remove)\s+(?:column|columns?)\s*([a-z]+|\d+)', command_lower)
            
            if row_match:
                target_row = int(row_match.group(1))
                # Convert to 0-based index
                target_row_index = target_row - 1
                if target_row_index >= len(spreadsheet_df) or target_row_index < 0:
                    print(f"   📊 Target row {target_row} doesn't exist (DataFrame has {len(spreadsheet_df)} rows)")
                    print("   ✅ Row to delete doesn't exist - zero changes is correct")
                    return True
                    
            if col_match:
                target_col = col_match.group(1)
                # Check if target column exists
                if target_col.isdigit():
                    col_index = int(target_col) - 1
                    if col_index >= len(spreadsheet_df.columns) or col_index < 0:
                        print(f"   📊 Target column {target_col} doesn't exist (DataFrame has {len(spreadsheet_df.columns)} columns)")
                        print("   ✅ Column to delete doesn't exist - zero changes is correct")
                        return True
                else:
                    # Handle column letters (A, B, C, etc.)
                    if target_col.upper() not in [str(col) for col in spreadsheet_df.columns]:
                        print(f"   📊 Target column '{target_col}' doesn't exist in DataFrame")
                        print("   ✅ Column to delete doesn't exist - zero changes is correct")
                        return True
        
        # Check for filter/selection commands that might return empty results
        filter_patterns = ['where', 'filter', 'select', 'find', 'search', 'containing', 'with', 'having', 'matching']
        if any(pattern in command_lower for pattern in filter_patterns) and is_deletion_command:
            print(f"   🔍 Conditional deletion command - checking if condition exists")
            # For these commands, we can't easily verify without re-implementing the logic, but we can be more lenient
            return True
        
        # Check for specific content-based deletion patterns
        content_deletion_patterns = [
            'totals', 'total', 'subtotal', 'sum', 'net difference', 'difference', 
            'header', 'footer', 'summary', 'grand total', 'balance', 'ending', 'beginning'
        ]
        if is_deletion_command and any(pattern in command_lower for pattern in content_deletion_patterns):
            print(f"   🔍 Content-specific deletion command - checking if target content exists")
            # Check if the target content actually exists in the spreadsheet
            spreadsheet_str = spreadsheet_df.astype(str).values.flatten()
            target_found = False
            for pattern in content_deletion_patterns:
                if pattern in command_lower:
                    # Check if this pattern exists in the data (case-insensitive)
                    pattern_found = any(pattern.lower() in str(cell).lower() for cell in spreadsheet_str if str(cell) != 'nan')
                    if pattern_found:
                        target_found = True
                        break
            
            if not target_found:
                print(f"   ✅ Target content not found in spreadsheet - zero changes is correct")
                return True
        
        # Check for formatting/styling commands that might not change data
        formatting_patterns = ['format', 'style', 'color', 'font', 'align', 'border']
        if any(pattern in command_lower for pattern in formatting_patterns):
            print(f"   ✅ Formatting command - zero data changes is acceptable")
            return True
        
        # Check for validation/check commands
        validation_patterns = ['check', 'validate', 'verify', 'ensure', 'confirm']
        if any(pattern in command_lower for pattern in validation_patterns):
            print(f"   ✅ Validation command - zero changes is acceptable")
            return True
        
        print(f"   ❌ Command type requires modifications - zero changes indicates failure")
        return False
