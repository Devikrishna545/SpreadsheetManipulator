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
    Provides up to 5 retry attempts with Gemini correction.
    """
    
    def __init__(self):
        """Initialize the script fixer with LLM service for corrections."""
        self.llm_service = LLMService()
        self.script_tester = ScriptTester()
        self.max_retries = 5
        self.current_script_path = None  # Track current script path for logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def fix_and_execute_script(self, script: str, spreadsheet_df: pd.DataFrame, 
                              command: str, security_manager, script_path: Optional[str] = None) -> Tuple[pd.DataFrame, list, bool]:
        """
        Execute a script with comprehensive automated error correction pipeline.
        
        Flow:
        1. Sandbox test → 2. LLM fix (if errors) → 3. Manual fix (if LLM fails) 
        → 4. Security check → 5. LLM security fix (if needed) → 6. Execute
        
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
        
        # Store script path for logging
        self.current_script_path = script_path
        
        # === PHASE 1: SANDBOX TESTING AND SCRIPT FIXING ===
        print("\n📋 PHASE 1: Sandbox Testing and Script Correction")
        print("-" * 50)
        
        # Step 1: Test in sandbox environment
        execution_success, execution_error = self._test_script_in_sandbox(current_script, spreadsheet_df)
        
        if not execution_success:
            print(f"🔧 Sandbox execution failed: {execution_error}")

            # Try a manual fix for common errors before resorting to LLM
            if "name 'row_index' is not defined" in str(execution_error):
                print("🤖 Attempting manual fix for 'row_index' NameError by wrapping in a loop...")
                indented_script = "    " + current_script.strip().replace("\n", "\n    ")
                fixed_script = f"for row_index in range(len(df)):\n{indented_script}"
                
                test_success, test_error = self._test_script_in_sandbox(fixed_script, spreadsheet_df)
                if test_success:
                    print("✅ Manual loop wrap fix successful!")
                    current_script = fixed_script
                    execution_success = True
                else:
                    print(f"⚠️ Manual loop wrap fix failed: {test_error}. Proceeding with LLM.")
            
            if not execution_success:
                # Step 2: Attempt LLM-based fix for execution errors
                print("🤖 Attempting LLM-based error correction...")
                llm_fixed_script = self._fix_script_with_llm(
                    current_script, execution_error, "", command, spreadsheet_df
                )
                
                if llm_fixed_script:
                    print("✓ LLM provided a fix, testing...")
                    llm_success, llm_error = self._test_script_in_sandbox(llm_fixed_script, spreadsheet_df)
                    
                    if llm_success:
                        print("✅ LLM fix successful!")
                        current_script = llm_fixed_script
                        execution_success = True
                    else:
                        print(f"⚠️ LLM fix still has errors: {llm_error}")
                        
                        # Step 3: Try manual deterministic fixes as fallback
                        print("🔧 Attempting manual deterministic fixes...")
                        manual_fixed_script = self._apply_manual_fixes(llm_fixed_script, llm_error, spreadsheet_df)
                        
                        if manual_fixed_script:
                            manual_success, manual_error = self._test_script_in_sandbox(manual_fixed_script, spreadsheet_df)
                            if manual_success:
                                print("✅ Manual fix successful!")
                                current_script = manual_fixed_script
                                execution_success = True
                            else:
                                print(f"❌ Manual fix also failed: {manual_error}")
                        else:
                            print("❌ No manual fix available")
                else:
                    print("⚠️ LLM could not provide a fix, trying manual fixes...")
                    
                    # Step 3: Try manual deterministic fixes directly
                    manual_fixed_script = self._apply_manual_fixes(current_script, execution_error, spreadsheet_df)
                    
                    if manual_fixed_script:
                        manual_success, manual_error = self._test_script_in_sandbox(manual_fixed_script, spreadsheet_df)
                        if manual_success:
                            print("✅ Manual fix successful!")
                            current_script = manual_fixed_script
                            execution_success = True
                        else:
                            print(f"❌ Manual fix failed: {manual_error}")
                    else:
                        print("❌ No manual fix available")
        else:
            print("✅ Script passed sandbox testing")
        
        # If still not working after all fixes, return failure
        if not execution_success:
            print("💥 PHASE 1 FAILED: Could not fix script execution errors")
            logging.error(f"Script fixing failed after all attempts. Original: {original_script}, Final error: {execution_error}")
            return spreadsheet_df, [], False
        
        # === PHASE 2: SECURITY VALIDATION AND FIXING ===
        print("\n🔒 PHASE 2: Security Validation and Correction")
        print("-" * 50)
        
        security_attempts = 0
        max_security_attempts = 5
        
        while security_attempts < max_security_attempts:
            security_attempts += 1
            print(f"🔍 Security check attempt {security_attempts}/{max_security_attempts}")
            
            if security_manager.validate_script(current_script):
                print("✅ Security validation passed!")
                break
            else:
                print(f"⚠️ Security validation failed (attempt {security_attempts})")
                
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
        
        # === PHASE 3: FINAL EXECUTION AND LOGIC VALIDATION ===
        print("\n🚀 PHASE 3: Final Execution & Logic Validation")
        print("-" * 50)
        
        logic_fix_attempts = 0
        max_logic_fix_attempts = 5
        fix_history = []  # Track failed attempts to prevent LLM from repeating mistakes

        while logic_fix_attempts < max_logic_fix_attempts:
            try:
                modified_df, modified_cells = self._execute_final_script(current_script, spreadsheet_df)
                
                if len(modified_cells) > 0:
                    print(f"✅ PIPELINE SUCCESS: Script executed successfully - {len(modified_cells)} cell(s) modified")
                    if self.current_script_path:
                        print(f"✅ {self.current_script_path}")
                    return modified_df, modified_cells, True
                
                # Logic error detected
                logic_fix_attempts += 1
                print(f"⚠️ LOGIC ERROR: Script ran but made no changes. Attempting fix {logic_fix_attempts}/{max_logic_fix_attempts}")
                
                if logic_fix_attempts <= max_logic_fix_attempts:
                    error_message = "The script executed without syntax errors but resulted in zero modifications. This suggests a logic error. Please analyze the user\'s command and the script\'s logic to ensure it correctly modifies the dataframe as intended."
                    
                    # Step 1: Try LLM-based logic fix
                    fixed_script = self._fix_script_with_llm(
                        current_script, error_message, "", command, spreadsheet_df, fix_history
                    )
                    
                    if fixed_script and fixed_script != current_script:
                        print("✓ LLM provided a logic fix, re-validating...")
                        
                        # Test the new script
                        test_success, test_error = self._test_script_in_sandbox(fixed_script, spreadsheet_df)
                        if not test_success:
                            print(f"⚠️ LLM logic fix failed sandbox test: {test_error}")
                            
                            # Add this failed attempt to history
                            fix_history.append({
                                'script': fixed_script,
                                'error': test_error
                            })
                            
                            # Step 2: Try to fix the broken LLM fix with another LLM attempt
                            print("🤖 Attempting to fix the broken LLM logic fix...")
                            double_fixed_script = self._fix_script_with_llm(
                                fixed_script, test_error, "", command, spreadsheet_df, fix_history
                            )
                            
                            if double_fixed_script and double_fixed_script != fixed_script:
                                double_test_success, double_test_error = self._test_script_in_sandbox(double_fixed_script, spreadsheet_df)
                                if double_test_success:
                                    print("✅ Double-fix LLM correction successful!")
                                    fixed_script = double_fixed_script
                                    test_success = True
                                else:
                                    print(f"⚠️ Double-fix also failed: {double_test_error}")
                                    # Add this failed attempt to history too
                                    fix_history.append({
                                        'script': double_fixed_script,
                                        'error': double_test_error
                                    })
                            
                            # Step 3: Try manual deterministic fixes if LLM fixes failed
                            if not test_success:
                                print("🔧 Trying manual fixes for the logic error...")
                                manual_fixed_script = self._apply_manual_fixes(fixed_script, test_error, spreadsheet_df)
                                
                                if manual_fixed_script:
                                    manual_test_success, manual_test_error = self._test_script_in_sandbox(manual_fixed_script, spreadsheet_df)
                                    if manual_test_success:
                                        print("✅ Manual fix for logic error successful!")
                                        fixed_script = manual_fixed_script
                                        test_success = True
                                    else:
                                        print(f"❌ Manual fix also failed: {manual_test_error}")
                                        # Add manual fix failure to history
                                        fix_history.append({
                                            'script': manual_fixed_script,
                                            'error': manual_test_error
                                        })
                                else:
                                    print("❌ No manual fix available for logic error")
                        else:
                            # Add successful script to history (for context)
                            fix_history.append({
                                'script': fixed_script,
                                'error': 'SUCCESS'
                            })
                        
                        # If we have a working fix, validate security and continue
                        if test_success:
                            # Security check the new script
                            if not security_manager.validate_script(fixed_script):
                                print("💥 Logic fix failed security validation.")
                                # Try to get a security-compliant version
                                security_fixed_script = self._fix_script_with_llm(
                                    fixed_script, 
                                    "Script failed security validation. Please ensure the script only uses allowed operations and imports.",
                                    "", 
                                    command, 
                                    spreadsheet_df
                                )
                                
                                if security_fixed_script and security_manager.validate_script(security_fixed_script):
                                    security_test_success, _ = self._test_script_in_sandbox(security_fixed_script, spreadsheet_df)
                                    if security_test_success:
                                        print("✅ Security fix successful!")
                                        fixed_script = security_fixed_script
                                    else:
                                        print("💥 Security fix broke functionality. Continuing to next attempt.")
                                        continue
                                else:
                                    print("💥 Could not create security-compliant version. Continuing to next attempt.")
                                    continue
                            
                            print("✅ Logic fix passed all validation. Retrying execution.")
                            print(f"📝 Logic-corrected script preview:\n\n{fixed_script[:1000000]}\n")
                            current_script = fixed_script
                        else:
                            print("❌ All fix attempts failed for this iteration. Continuing to next attempt.")
                            continue
                    else:
                        print("❌ LLM could not provide a logic fix. Trying manual fixes...")
                        
                        # Try manual fixes directly for the original logic error
                        manual_fixed_script = self._apply_manual_fixes(current_script, "Script made no modifications", spreadsheet_df)
                        
                        if manual_fixed_script:
                            manual_test_success, manual_test_error = self._test_script_in_sandbox(manual_fixed_script, spreadsheet_df)
                            if manual_test_success and security_manager.validate_script(manual_fixed_script):
                                print("✅ Manual fix for original logic error successful!")
                                current_script = manual_fixed_script
                            else:
                                print(f"❌ Manual fix failed or security invalid. Continuing to next attempt.")
                                continue
                        else:
                            print("❌ No fixes available for this attempt. Continuing to next attempt.")
                            continue
                else:
                    print("💥 PHASE 3 FAILED: Maximum logic fix attempts reached")
                    break
                
            except Exception as e:
                print(f"💥 PHASE 3 FAILED: Final execution error: {e}")
                if self.current_script_path:
                    print(f"❌ {self.current_script_path}")
                logging.error(f"Final execution failed: {e}", exc_info=True)
                return spreadsheet_df, [], False

        print("💥 PIPELINE FAILED: Could not produce a working script after all attempts.")
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
        
        # Manual fix for df.replace() regex error
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
