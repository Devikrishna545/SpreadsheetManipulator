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
from src.controller.script_tester import ScriptTester  # Add this import

class ScriptFixer:
    """
    Handles error correction for simple scripts generated from AI commands.
    Provides up to 5 retry attempts with Gemini correction.
    """
    
    def __init__(self):
        """Initialize the script fixer with LLM service for corrections."""
        self.llm_service = LLMService()
        self.script_tester = ScriptTester()  # Add this line
        self.max_retries = 5
    
    def fix_and_execute_script(self, script: str, spreadsheet_df: pd.DataFrame, 
                              command: str, security_manager) -> Tuple[pd.DataFrame, list, bool]:
        """
        Execute a script with automatic error correction.
        
        Args:
            script: The Python script to execute
            spreadsheet_df: The pandas DataFrame containing spreadsheet data
            command: The original user command for context
            security_manager: Security manager instance for validation
            
        Returns:
            Tuple[pd.DataFrame, list, bool]: (modified_df, modified_cells, success)
        """
        last_error = None
        current_script = script
        previous_scripts = set()  # Track previous scripts to avoid infinite loops
        
        # First, try to validate and fix with the script tester
        is_valid, error_message, fixed_script = self.script_tester.test_script(current_script, spreadsheet_df.head(5))
        
        if not is_valid and fixed_script:
            print(f"⚠️ Script validation issue detected: {error_message}")
            print("🔧 Applying automatic fix from script tester...")
            current_script = fixed_script
            print("✅ Script automatically fixed by tester")
        
        for attempt in range(self.max_retries):
            try:
                print(f"⚙️  Executing script (attempt {attempt + 1}/{self.max_retries})...")
                
                # Validate script security
                if not security_manager.validate_script(current_script):
                    raise ValueError("Script validation failed due to security concerns")
                
                # Execute the script
                modified_df, modified_cells = self._execute_simple_script(current_script, spreadsheet_df)
                
                # If we get here, execution was successful
                print(f"✅ Script executed successfully - {len(modified_cells)} cells modified")
                return modified_df, modified_cells, True
                
            except Exception as e:
                last_error = e
                error_msg = str(e)
                error_traceback = traceback.format_exc()
                
                print(f"❌ Script execution failed (attempt {attempt + 1}): {error_msg}")
                
                if attempt < self.max_retries - 1:
                    # Check if we've seen this script before
                    if current_script in previous_scripts:
                        print("❌ LLM is repeating the same incorrect fix")
                        break
                    
                    previous_scripts.add(current_script)
                    
                    # Try to fix with script tester first
                    is_valid, error_message, fixed_script = self.script_tester.test_script(current_script, spreadsheet_df.head(5))
                    
                    if fixed_script:
                        print(f"🔧 Script tester generated a fix: {error_message}")
                        current_script = fixed_script
                    else:
                        # If script tester couldn't fix it, try LLM
                        print(f"🔧 Attempting to fix script with LLM...")
                        print(f"🔍 Error details: {error_msg}")
                        print(f"📝 Current script length: {len(current_script)} chars")
                        
                        corrected_script = self._fix_script_with_llm(
                            current_script, error_msg, error_traceback, command, spreadsheet_df
                        )
                        
                        if corrected_script is None or corrected_script.strip() == current_script.strip():
                            print("❌ Unable to generate meaningful script correction")
                            break
                        
                        current_script = corrected_script
                        print(f"🔧 New corrected script generated (length: {len(current_script)} chars)")
                else:
                    print(f"❌ Max retry attempts ({self.max_retries}) reached")
        
        # If we get here, all attempts failed
        print(f"❌ Script execution failed after {self.max_retries} attempts")
        print(f"Final error: {last_error}")
        
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
                print(f"🔍 isinstance not found in builtins. Available: {list(exec_globals['__builtins__'].keys())}")
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
        Use LLM to fix a script based on the error encountered.
        
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
            # Prepare context for LLM
            columns_info = f"Columns: {list(spreadsheet_df.columns)}"
            shape_info = f"Shape: {spreadsheet_df.shape[0]} rows, {spreadsheet_df.shape[1]} columns"
            
            # Create a prompt for script correction with enhanced context
            correction_prompt = f"""
You are a Python script debugging expert. Fix the following script that failed to execute.

CONTEXT:
- Original Command: {command}
- DataFrame Info: {columns_info}, {shape_info}
- Error: {error_msg}

CURRENT FAILING SCRIPT:
```python
{script}
```

EXECUTION ENVIRONMENT:
The script runs with these available variables and functions:
- df: pandas DataFrame (the main data)
- pd: pandas library
- np: numpy library
- isinstance, type, len, str, int, float, bool: Python built-ins
- pd.notna(), pd.isna(): pandas null checking functions

COMMON ERROR FIXES:
1. "name 'isinstance' is not defined" → isinstance is available, ensure proper usage
2. "name '__import__' is not defined" → avoid using __import__, use available libraries
3. Column access errors → use df.columns.get_loc('column_name') for indices
4. Index errors → check bounds with len(df) and len(df.columns)

REQUIREMENTS:
1. Fix the specific error: {error_msg}
2. Use ONLY the available functions and libraries listed above
3. Keep the original logic intact, just fix the technical issues
4. Return ONLY the corrected Python code, no explanations

CORRECTED SCRIPT:"""
            
            # Get corrected script from LLM
            corrected_script = self.llm_service.generate_script_correction(correction_prompt)
            
            # Clean up the response (remove markdown formatting if present)
            corrected_script = self._clean_script_response(corrected_script)
            
            if corrected_script and corrected_script.strip():
                print("🔧 Script correction generated")
                print(f"📝 Corrected script preview: {corrected_script[:100]}...")
                return corrected_script
            else:
                print("❌ LLM returned empty correction")
                return None
                
        except Exception as e:
            print(f"❌ Error during script correction: {e}")
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
