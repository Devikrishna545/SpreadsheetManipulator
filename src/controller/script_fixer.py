"""
Script Fixer module
------------------
Specialized error correction system for simple AI command scripts
"""

import re
import traceback
from typing import Tuple, Optional, Dict, Any
import pandas as pd
from src.llm.llm_service import LLMService
from src.llm.token_manager import token_manager
from src.controller.script_tester import ScriptTester  # Add this import
import logging

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
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def fix_and_execute_script(self, script: str, spreadsheet_df: pd.DataFrame, 
                              command: str, security_manager) -> Tuple[pd.DataFrame, list, bool]:
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
            
        Returns:
            Tuple[pd.DataFrame, list, bool]: (modified_df, modified_cells, success)
        """
        print("🏭 COMPREHENSIVE AUTOMATED ERROR CORRECTION PIPELINE")
        print("=" * 70)
        
        current_script = script
        original_script = script
        
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
        max_logic_fix_attempts = 2

        while logic_fix_attempts < max_logic_fix_attempts:
            try:
                modified_df, modified_cells = self._execute_final_script(current_script, spreadsheet_df)
                
                if len(modified_cells) > 0:
                    print(f"✅ PIPELINE SUCCESS: Script executed successfully - {len(modified_cells)} cell(s) modified")
                    return modified_df, modified_cells, True
                
                # Logic error detected
                logic_fix_attempts += 1
                print(f"⚠️ LOGIC ERROR: Script ran but made no changes. Attempting fix {logic_fix_attempts}/{max_logic_fix_attempts}")
                
                if logic_fix_attempts <= max_logic_fix_attempts:
                    error_message = "The script executed without syntax errors but resulted in zero modifications. This suggests a logic error. Please analyze the user\'s command and the script\'s logic to ensure it correctly modifies the dataframe as intended."
                    
                    fixed_script = self._fix_script_with_llm(
                        current_script, error_message, "", command, spreadsheet_df
                    )
                    
                    if fixed_script and fixed_script != current_script:
                        print("✓ LLM provided a logic fix, re-validating...")
                        
                        # Test the new script
                        test_success, test_error = self._test_script_in_sandbox(fixed_script, spreadsheet_df)
                        if not test_success:
                            print(f"💥 Logic fix failed sandbox test: {test_error}")
                            # End of the line for this attempt
                            break

                        # Security check the new script
                        if not security_manager.validate_script(fixed_script):
                            print("💥 Logic fix failed security validation.")
                            # End of the line for this attempt
                            break
                            
                        print("✅ Logic fix passed all validation. Retrying execution.")
                        print(f"📝 Logic-corrected script preview:\n\n{fixed_script[:1000000]}\n")
                        current_script = fixed_script
                    else:
                        print("❌ LLM could not provide a logic fix. Aborting.")
                        break
                
            except Exception as e:
                print(f"💥 PHASE 3 FAILED: Final execution error: {e}")
                logging.error(f"Final execution failed: {e}", exc_info=True)
                return spreadsheet_df, [], False

        print("💥 PIPELINE FAILED: Could not produce a working script after all attempts.")
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
                           command: str, spreadsheet_df: pd.DataFrame) -> Optional[str]:
        """
        Use LLM to intelligently fix a script based on the error encountered.
        Enhanced for automated debugging system.
        
        Args:
            script: The failing script
            error_msg: Error message
            error_traceback: Full error traceback
            command: Original user command
            spreadsheet_df: The DataFrame being processed
            
        Returns:
            Optional[str]: Fixed script or None if fixing failed
        """
        try:
            print("🤖 Requesting LLM script correction...")
            
            # Prepare context for LLM
            columns_info = f"Columns: {list(spreadsheet_df.columns)}"
            shape_info = f"Shape: {spreadsheet_df.shape[0]} rows, {spreadsheet_df.shape[1]} columns"
            sample_data = spreadsheet_df.head(3).to_string() if len(spreadsheet_df) > 0 else "Empty DataFrame"
            
            # Enhanced prompt for automated debugging
            correction_prompt = f"""
You are an expert Python script debugger in an automated error correction system. Your task is to fix the failing script below.

=== CONTEXT ===
Original User Command: {command}
DataFrame Structure: {columns_info}, {shape_info}

Sample Data:
{sample_data}

=== ERROR INFORMATION ===
Error Message: {error_msg}
{f"Full Traceback: {error_traceback}" if error_traceback else ""}

=== FAILING SCRIPT ===
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
1. ANALYZE the error message carefully
2. IDENTIFY the root cause (syntax, logic, data access, security, etc.)
3. FIX the issue while preserving the original intent
4. ENSURE compatibility with the DataFrame structure
5. USE only the available environment listed above
6. RETURN only clean Python code without explanations or markdown

=== COMMON ERROR PATTERNS & FIXES ===
- Syntax errors: Add missing colons, parentheses, indentation
- NameError: Use available built-ins only (isinstance, not __import__)
- IndexError: Check bounds with len(df), len(df.columns)
- Column access: Use df[column_name] or df.iloc[row, col]
- Security violations: Remove forbidden imports/functions
- Incomplete blocks: Add missing code (e.g., df.drop(index, inplace=True) for deletions)

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
