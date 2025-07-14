"""
Script Fixer module
------------------
Specialized error correction system for simple AI command scripts
"""

import re
import traceback
from typing import Tuple, Optional, Dict, Any
import pandas as pd
import numpy as np
from src.llm.llm_service import LLMService
from src.llm.token_manager import token_manager
from src.controller.script_tester import ScriptTester  # Add this import
import logging

class ScriptExecutionFailureException(Exception):
    """
    Exception raised when script execution fails after going through
    the complete debugging pipeline (ScriptTester + ScriptFixer)
    """
    def __init__(self, command: str, error_details: str):
        self.command = command
        self.error_details = error_details
        super().__init__(f"Failed to execute command '{command}' after debugging pipeline: {error_details}")

class ScriptFixer:
    """
    Handles error correction for simple scripts generated from AI commands.
    Provides up to 7 retry attempts: 4 with standard correction and 3 with advanced Gemini complex script generation.
    """
    
    def __init__(self):
        """Initialize the script fixer with LLM service for corrections."""
        self.llm_service = LLMService()
        self.script_tester = ScriptTester()
        self.max_retries = 7  # Updated to include 3 advanced attempts
        self.current_script_path = None  # Track current script path for logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def fix_and_execute_script(self, script: str, spreadsheet_df: pd.DataFrame, 
                              command: str, security_manager, script_path: Optional[str] = None) -> Tuple[pd.DataFrame, list, bool]:
        """
        Execute a script with comprehensive automated error correction pipeline.
        
        Flow:
        1. Sandbox test → 2. LLM fix (if errors) → 3. Manual fix (if LLM fails) 
        → 4. Advanced Gemini Complex Script Generation (attempts 4-5-6 if standard methods fail)
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
        fix_attempts = 0
        max_fix_attempts = 7  # 1 quick fix + 1 LLM + 1 manual + 3 advanced + 1 final
        
        # Store script path for logging
        self.current_script_path = script_path
        
        # === PHASE 1: ITERATIVE SCRIPT FIXING (Steps 1-4) ===
        print("\n📋 PHASE 1: Iterative Script Fixing")
        print("-" * 50)
        
        while fix_attempts < max_fix_attempts:
            fix_attempts += 1
            print(f"\n🔧 Fix Attempt {fix_attempts}/{max_fix_attempts}")
            
            # Step 1: Sandbox test
            execution_success, execution_error = self._test_script_in_sandbox(current_script, spreadsheet_df)
            
            if execution_success:
                print("✅ Script passed sandbox testing")
                break
                
            print(f"❌ Sandbox execution failed: {execution_error}")
            
            # Determine fix strategy based on attempt number
            if fix_attempts == 1:
                # Try quick manual fix for common errors first
                if "name 'row_index' is not defined" in str(execution_error):
                    print("🤖 Attempting manual fix for 'row_index' NameError...")
                    indented_script = "    " + current_script.strip().replace("\n", "\n    ")
                    fixed_script = f"for row_index in range(len(df)):\n{indented_script}"
                    
                    test_success, test_error = self._test_script_in_sandbox(fixed_script, spreadsheet_df)
                    if test_success:
                        print("✅ Manual loop wrap fix successful!")
                        current_script = fixed_script
                        continue
                    else:
                        print(f"⚠️ Manual loop wrap fix failed: {test_error}")
                
                # If manual fix didn't work, proceed to LLM fix
                print("🤖 Step 2: Attempting LLM-based error correction...")
                fixed_script = self._fix_script_with_llm(
                    current_script, execution_error, "", command, spreadsheet_df
                )
                
            elif fix_attempts == 2:
                # Step 2: LLM fix
                print("🤖 Step 2: LLM-based error correction...")
                fixed_script = self._fix_script_with_llm(
                    current_script, execution_error, "", command, spreadsheet_df
                )
                
            elif fix_attempts == 3:
                # Step 3: Manual deterministic fixes
                print("🔧 Step 3: Manual deterministic fixes...")
                fixed_script = self._apply_manual_fixes(current_script, execution_error, spreadsheet_df)
                
            elif fix_attempts in [4, 5, 6]:
                # Step 4: Advanced Gemini Complex Script Generation (3 attempts)
                attempt_num = fix_attempts - 3  # Convert to 1, 2, 3
                print(f"🧠 Step 4: ADVANCED GEMINI COMPLEX SCRIPT GENERATION (Attempt {attempt_num}/3)")
                print("-" * 50)
                
                # Prepare spreadsheet data for complex script generation
                spreadsheet_data = {
                    'headers': list(spreadsheet_df.columns),
                    'metadata': {'rows': len(spreadsheet_df)},
                    'data': spreadsheet_df.head(10).to_dict('records') if len(spreadsheet_df) > 0 else []
                }
                
                try:
                    # Create enhanced command with error context
                    enhanced_command = f"{command}\n\nPrevious Error Context:\nThe script failed with: {execution_error}\nPlease ensure the new script avoids this error and uses proper pandas operations."
                    
                    print("🤖 Generating complex script with thinking and code execution...")
                    fixed_script = self.llm_service.generate_script(spreadsheet_data, enhanced_command, use_advanced_processing=True)
                    
                    if not fixed_script or not fixed_script.strip():
                        print("❌ Complex script generation failed or returned empty script")
                        fixed_script = None
                    else:
                        print("✓ Complex script generated successfully")
                        
                except Exception as e:
                    print(f"💥 Complex script generation failed with exception: {e}")
                    logging.error(f"Complex script generation failed: {e}", exc_info=True)
                    fixed_script = None
                    
            else:
                # Final attempt (attempt 7) - last resort
                print("🔧 Step 7: Final attempt with comprehensive fix...")
                fixed_script = self._fix_script_with_llm(
                    current_script, execution_error, "", command, spreadsheet_df
                )
            
            # Apply the fix if we got one
            if fixed_script and fixed_script != current_script:
                print("✓ Fix generated, testing...")
                current_script = fixed_script
            else:
                print("❌ No fix available for this attempt")
                if fix_attempts >= max_fix_attempts:
                    break
                continue
        
        # Check if we have a working script after all fix attempts
        if not execution_success:
            print("💥 PHASE 1 FAILED: Could not fix script execution errors after all attempts")
            logging.error(f"Script fixing failed after all attempts. Original: {original_script}, Final error: {execution_error}")
            return spreadsheet_df, [], False
        
        # === PHASE 2: SECURITY VALIDATION AND FIXING (Steps 5-6) ===
        print("\n🔒 PHASE 2: Security Validation and Correction")
        print("-" * 50)
        
        security_attempts = 0
        max_security_attempts = 3
        
        while security_attempts < max_security_attempts:
            security_attempts += 1
            print(f"🔍 Step 5: Security check attempt {security_attempts}/{max_security_attempts}")
            
            if security_manager.validate_script(current_script):
                print("✅ Security validation passed!")
                break
            else:
                print(f"⚠️ Security validation failed (attempt {security_attempts})")
                
                if security_attempts < max_security_attempts:
                    print("🤖 Step 6: Requesting LLM to fix security issues...")
                    security_fixed_script = self._fix_script_with_llm(
                        current_script, 
                        "Script failed security validation. Please ensure the script only uses allowed operations and imports.",
                        "", 
                        command, 
                        spreadsheet_df
                    )
                    
                    if security_fixed_script and security_fixed_script != current_script:
                        print("✓ LLM provided security fix, testing...")
                        # Test that the security fix still works functionally
                        security_test_success, security_test_error = self._test_script_in_sandbox(security_fixed_script, spreadsheet_df)
                        
                        if security_test_success:
                            current_script = security_fixed_script
                            print("✓ Security fix maintains functionality")
                        else:
                            print(f"⚠️ Security fix broke functionality: {security_test_error}")
                            # Try to fix the broken security fix
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
                    print("💥 PHASE 2 FAILED: Maximum security fix attempts reached")
                    logging.error(f"Security validation failed after {max_security_attempts} attempts")
                    return spreadsheet_df, [], False
        
        # === PHASE 3: FINAL EXECUTION (Step 7) ===
        print("\n🚀 PHASE 3: Final Execution")
        print("-" * 50)
        
        try:
            print("🚀 Step 7: Executing validated script...")
            modified_df, modified_cells = self._execute_final_script(current_script, spreadsheet_df)
            
            if len(modified_cells) > 0:
                print(f"✅ PIPELINE SUCCESS: Script executed successfully - {len(modified_cells)} cell(s) modified")
                if self.current_script_path:
                    print(f"✅ {self.current_script_path}")
                return modified_df, modified_cells, True
            else:
                print("⚠️ LOGIC WARNING: Script executed but made no modifications")
                print("✅ PIPELINE SUCCESS: Script completed without errors (no changes needed)")
                return modified_df, [], True
                
        except Exception as e:
            error_msg = str(e)
            error_traceback = traceback.format_exc()
            print(f"💥 FINAL EXECUTION FAILED: {error_msg}")
            logging.error(f"Final execution failed: {e}", exc_info=True)
            
            # Last attempt to fix execution error
            print("🔧 Last attempt to fix execution error...")
            final_fixed_script = self._fix_script_with_llm(
                current_script, error_msg, error_traceback, command, spreadsheet_df
            )
            
            if final_fixed_script and final_fixed_script != current_script:
                try:
                    print("✓ Final fix generated, attempting execution...")
                    test_success, test_error = self._test_script_in_sandbox(final_fixed_script, spreadsheet_df)
                    
                    if test_success and security_manager.validate_script(final_fixed_script):
                        modified_df, modified_cells = self._execute_final_script(final_fixed_script, spreadsheet_df)
                        print(f"✅ PIPELINE SUCCESS (Final Fix): Script executed - {len(modified_cells)} cell(s) modified")
                        if self.current_script_path:
                            print(f"✅ {self.current_script_path}")
                        return modified_df, modified_cells, True
                    else:
                        print("❌ Final fix failed validation")
                        
                except Exception as final_e:
                    print(f"❌ Final fix execution failed: {final_e}")
            
            print("💥 PIPELINE FAILED: Could not execute script after all attempts")
            if self.current_script_path:
                print(f"❌ {self.current_script_path}")
            return spreadsheet_df, [], False
    
    def _execute_simple_script(self, script: str, spreadsheet_df: pd.DataFrame) -> Tuple[pd.DataFrame, list]:
        """
        Execute a simple script without universal transformation patterns.
        
        Args:
            script: The Python script to execute
            spreadsheet_df: The pandas DataFrame
            
        Returns:
            Tuple[pd.DataFrame, list]: Modified DataFrame and list of modified cells
        """
        # Create a copy of the dataframe for execution
        df = spreadsheet_df.copy()
        
        # Track original values to identify modifications
        original_values = {}
        for i in range(len(df)):
            for j, col in enumerate(df.columns):
                original_values[(i, j)] = df.iloc[i, j]
        
        # Create execution environment with comprehensive built-ins
        import builtins
        import numpy as np
        
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
            
            # I/O (print only)
            'print': print,
            
            # Object introspection
            'vars': vars,
            'dir': dir,
            'id': id,
            'callable': callable,
            
            # Import mechanism (safe subset)
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
        
        # Execute the script
        try:
            exec(script, exec_globals)
        except NameError as e:
            if "isinstance" in str(e):
                # This is a fallback if 'isinstance' is missing from the sandbox
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

        
        # Get the modified dataframe
        modified_df = exec_globals['df']
        
        # Find modified cells
        modified_cells = []
        for i in range(len(modified_df)):
            for j, col in enumerate(modified_df.columns):
                if (i, j) in original_values:
                    old_val = original_values[(i, j)]
                    new_val = modified_df.iloc[i, j]
                    
                    # Check if values are different (handle NaN comparison)
                    if pd.isna(old_val) and pd.isna(new_val):
                        continue
                    elif pd.isna(old_val) or pd.isna(new_val) or old_val != new_val:
                        modified_cells.append([i, j])
        
        return modified_df, modified_cells
    
    def _fix_script_with_llm(self, script: str, error_msg: str, error_traceback: str, 
                           command: str, spreadsheet_df: pd.DataFrame, 
                           fix_history: Optional[list] = None) -> Optional[str]:
        """
        Use LLM to intelligently fix a script based on the error encountered.
        Enhanced for automated debugging system.
        
        Args:
            script: The failing script
            error_msg: Error message
            error_traceback: Full error traceback
            command: Original user command
            spreadsheet_df: The DataFrame being processed
            fix_history: A list of previous failed attempts in this cycle
            
        Returns:
            Optional[str]: Fixed script or None if fixing failed
        """
        try:
            print("🤖 Requesting LLM script correction...")
            
            # Prepare context for LLM
            columns_info = f"Columns: {list(spreadsheet_df.columns)}"
            shape_info = f"Shape: {spreadsheet_df.shape[0]} rows, {spreadsheet_df.shape[1]} columns"
            sample_data = spreadsheet_df.head(3).to_string() if len(spreadsheet_df) > 0 else "Empty DataFrame"
            
            # Build the history section for the prompt
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
            
            # Enhanced prompt for automated debugging
            correction_prompt = f"""
You are an expert Python script debugger in an automated error correction system. Your task is to fix the failing script below.

=== CONTEXT ===
Original User Command: {command}
DataFrame Structure: {columns_info}, {shape_info}

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

Generate the corrected script:"""
            
            # Get corrected script from LLM
            corrected_script = self.llm_service.generate_script_correction(correction_prompt)
            
            # Print token usage summary
            token_manager.print_token_usage()
            
            # Clean up the response (remove markdown formatting if present)
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
        """
        Clean up the LLM response to extract just the Python script.
        
        Args:
            response: Raw LLM response
            
        Returns:
            str: Cleaned Python script
        """
        # Remove markdown code blocks if present
        if '```python' in response:
            # Extract content between ```python and ```
            start = response.find('```python') + 9
            end = response.find('```', start)
            if end > start:
                response = response[start:end]
        elif '```' in response:
            # Extract content between ``` blocks
            start = response.find('```') + 3
            end = response.find('```', start)
            if end > start:
                response = response[start:end]
        
        return response.strip()
    
    def _test_script_in_sandbox(self, script: str, spreadsheet_df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Test script execution in a safe sandbox environment
        
        Args:
            script: Script to test
            spreadsheet_df: DataFrame to test with
            
        Returns:
            Tuple[bool, str]: (success, error_message)
        """
        try:
            print(f"🧪 Testing script in sandbox...")
            
            # Use a small sample for testing to avoid performance issues
            test_df = spreadsheet_df.head(10).copy()
            
            # Execute the script in sandbox
            _, _ = self._execute_simple_script(script, test_df)
            
            print("✅ Sandbox test passed")
            return True, ""
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Sandbox test failed: {error_msg}")
            return False, error_msg
    
    def _apply_manual_fixes(self, script: str, error_msg: str, spreadsheet_df: pd.DataFrame) -> Optional[str]:
        """
        Apply deterministic manual fixes for common script errors
        
        Args:
            script: The failing script
            error_msg: Error message from execution
            spreadsheet_df: DataFrame being processed
            
        Returns:
            Optional[str]: Fixed script or None if no fix available
        """
        print("🔧 Applying manual deterministic fixes...")
        print(f"🔍 Error message: {error_msg}")
        print(f"🔍 Available DataFrame columns: {list(spreadsheet_df.columns)}")
        print(f"🔍 Script to fix: {script[:200]}{'...' if len(script) > 200 else ''}")
        
        # Priority fix: Handle any script that references columns as strings when they should be integers
        # This is the most common cause of the Index(['12', '13', '9', '11', '10'], dtype='object') error
        if "Index([" in error_msg and "dtype='object'" in error_msg:
            print("🔧 Detected column reference type mismatch. Applying universal column fix...")
            
            import re
            fixed_script = script
            
            # Fix all quoted column references in the script
            # Pattern 1: df['column'] -> df[column] (if column is numeric and exists)
            column_access_pattern = r"df\[(['\"])(\d+)\1\]"
            
            def fix_column_access(match):
                col_num = int(match.group(2))
                if col_num in spreadsheet_df.columns:
                    return f"df[{col_num}]"
                return match.group(0)
            
            fixed_script = re.sub(column_access_pattern, fix_column_access, fixed_script)
            
            # Pattern 2: Fix any list/array containing quoted numbers
            # This handles subset=['1', '2'], by=['3', '4'], columns=['5', '6'], etc.
            list_pattern = r"(\w+\s*=\s*)\[[^\]]*['\"][0-9]+['\"][^\]]*\]"
            list_matches = re.findall(list_pattern, fixed_script)
            
            for param_prefix in list_matches:
                # Find the full parameter assignment
                full_pattern = rf"({re.escape(param_prefix)})\[[^\]]*\]"
                full_match = re.search(full_pattern, fixed_script)
                if full_match:
                    full_assignment = full_match.group(0)
                    # Extract all quoted numbers from this assignment
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
            
            # Pattern 3: Any list comprehension with str() around column indices
            str_comprehension_pattern = r"\[str\([^)]+\)\s+for\s+[^]]+\]"
            if re.search(str_comprehension_pattern, fixed_script):
                # Replace [str(col_idx) for col_idx in [1,2,3]] with [1,2,3]
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
            
            # Pattern 4: Handle Excel cell references (A1, B2, J2, etc.) if they appear as string column refs
            # Convert Excel column letters to numeric indices if script contains cell references
            excel_pattern = r"['\"]([A-Z]+)(\d+)['\"]"
            excel_matches = re.findall(excel_pattern, fixed_script)
            if excel_matches:
                print("🔧 Found Excel cell references, converting to numeric indices...")
                for col_letter, row_num in excel_matches:
                    # Convert Excel column letter to number (A=0, B=1, C=2, ..., J=9, K=10, etc.)
                    col_num = 0
                    for char in col_letter:
                        col_num = col_num * 26 + (ord(char) - ord('A'))
                    
                    # Check if this column exists in the DataFrame
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
        
        # Manual fix for column reference errors in drop_duplicates
        if "Index([" in error_msg and "dtype='object'" in error_msg and ("drop_duplicates" in script or "subset" in script):
            print("🔧 Detected column reference error in drop_duplicates. Applying manual fix...")
            
            # The issue is that str(col_idx) creates string column names, but DataFrame has integer columns
            # Fix: Remove the str() conversion around column indices
            import re
            
            # Pattern: [str(col_idx) for col_idx in [numbers]] -> [numbers directly]
            pattern = r'\[str\(col_idx\) for col_idx in \[([^\]]+)\]\]'
            match = re.search(pattern, script)
            
            if match:
                indices_str = match.group(1)
                # Extract the column indices and use them directly
                try:
                    indices = [int(x.strip()) for x in indices_str.split(',')]
                    # Check if these column indices exist in the DataFrame
                    valid_indices = [idx for idx in indices if idx in spreadsheet_df.columns]
                    
                    if valid_indices:
                        old_subset = f"[str(col_idx) for col_idx in [{indices_str}]]"
                        new_subset = str(valid_indices)
                        fixed_script = script.replace(old_subset, new_subset)
                        print(f"✓ Fixed column references: {old_subset} -> {new_subset}")
                        return fixed_script
                except (ValueError, TypeError):
                    pass
            
            # Alternative pattern: subset=['9', '10', '11', '12', '13'] -> subset=[9, 10, 11, 12, 13]
            string_pattern = r"subset=\[(['\"][^'\"]+['\"],?\s*)+\]"
            if re.search(string_pattern, script):
                # Extract quoted numbers and convert to integers
                quoted_nums = re.findall(r"['\"](\d+)['\"]", script)
                if quoted_nums:
                    # Convert to integers and check if they exist as columns
                    int_cols = []
                    for num_str in quoted_nums:
                        try:
                            col_idx = int(num_str)
                            if col_idx in spreadsheet_df.columns:
                                int_cols.append(col_idx)
                        except ValueError:
                            continue
                    
                    if int_cols:
                        # Replace the string column references with integer references
                        old_match = re.search(string_pattern, script).group(0)
                        new_subset = f"subset={int_cols}"
                        fixed_script = script.replace(old_match, new_subset)
                        print(f"✓ Fixed string column references: {old_match} -> {new_subset}")
                        return fixed_script
            
            # More comprehensive pattern: Any script containing quoted column numbers
            # This handles cases where LLM generates scripts with string column names
            max_col_to_check = max(50, len(spreadsheet_df.columns) * 2)  # Check broader range
            if any(f"'{i}'" in script or f'"{i}"' in script for i in range(max_col_to_check)):
                print("🔧 Found quoted column numbers in script, converting to integers...")
                fixed_script = script
                
                # Convert all quoted integers that exist as DataFrame columns
                for i in range(max_col_to_check):  # Check extended range
                    if i in spreadsheet_df.columns:
                        # Replace both single and double quoted versions in all contexts
                        fixed_script = fixed_script.replace(f"'{i}'", str(i))
                        fixed_script = fixed_script.replace(f'"{i}"', str(i))
                
                if fixed_script != script:
                    print(f"✓ Converted quoted column numbers to integers")
                    return fixed_script
            
            # Universal column reference fix for ANY pandas operation
            # This catches column references in any method, not just drop_duplicates
            if any(method in fixed_script for method in ['drop_duplicates', 'groupby', 'sort_values', 'pivot_table', 'merge', 'join']):
                print("🔧 Found pandas operations, applying universal column fixes...")
                
                # Fix any remaining quoted numbers in pandas method calls
                pandas_methods = ['drop_duplicates', 'groupby', 'sort_values', 'pivot_table', 'merge', 'join', 'pivot', 'melt', 'aggregate', 'agg']
                
                for method in pandas_methods:
                    if method in fixed_script:
                        # Look for method calls with quoted parameters
                        method_pattern = rf'{method}\([^)]*\)'
                        method_matches = re.findall(method_pattern, fixed_script)
                        
                        for method_call in method_matches:
                            original_call = method_call
                            fixed_call = method_call
                            
                            # Replace quoted numbers in the method call
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
            
            import re
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
            import re
            
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
            import re
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
                import re
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
        """
        Execute the final validated script on the full dataset
        
        Args:
            script: The validated script
            spreadsheet_df: The full DataFrame
            
        Returns:
            Tuple[pd.DataFrame, list]: Modified DataFrame and list of modified cells
        """
        print("🚀 Executing final validated script on full dataset...")
        return self._execute_simple_script(script, spreadsheet_df)
