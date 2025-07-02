"""
Script Tester module
------------------
Tests and validates scripts before execution to catch syntax errors and common issues
"""

import ast
import re
import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict, Any, List
from src.controller.security_manager import SecurityManager

class ScriptTester:
    """
    Tests scripts for syntax errors and common issues before execution
    """
    
    def __init__(self):
        """Initialize the script tester"""
        self.security_manager = SecurityManager()
    
    def test_script(self, script: str, sample_df: Optional[pd.DataFrame] = None) -> Tuple[bool, str, Optional[str]]:
        """
        Test a script for syntax errors and common issues
        
        Args:
            script: The Python script to test
            sample_df: Optional sample DataFrame for test execution
            
        Returns:
            Tuple[bool, str, Optional[str]]: (is_valid, error_message, fixed_script)
        """
        # Step 1: Check structure compatibility first if DataFrame is provided
        if sample_df is not None:
            is_compatible, structure_error, structure_fixed = self.validate_script_structure_compatibility(script, sample_df)
            if not is_compatible:
                if structure_fixed:
                    print("🔧 Structure compatibility issues detected and fixed")
                    script = structure_fixed  # Use the structure-fixed version
                else:
                    return False, f"Structure compatibility failed: {structure_error}", None
        
        # Step 2: Check for basic syntax errors
        try:
            ast.parse(script)
        except SyntaxError as e:
            fixed_script = self._try_fix_syntax_error(script, str(e))
            if fixed_script:
                # Re-test the fixed script
                try:
                    ast.parse(fixed_script)
                    return False, f"Original script had syntax error: {str(e)}. Automatic fix applied.", fixed_script
                except SyntaxError as e2:
                    return False, f"Script has syntax error: {str(e)}. Fix attempt failed with: {str(e2)}", None
            return False, f"Script has syntax error: {str(e)}", None
        
        # Step 3: Check for security concerns
        if not self.security_manager.validate_script(script):
            return False, "Script validation failed due to security concerns", None
        
        # Step 4: Check for common logical issues
        result, issue, fixed = self._check_logical_issues(script)
        if not result:
            return False, issue, fixed
        
        # Step 5: Try to execute the script on a sample DataFrame if provided
        if sample_df is not None:
            success, error = self._test_execution(script, sample_df)
            if not success:
                fixed_script = self._try_fix_execution_error(script, error, sample_df)
                if fixed_script:
                    return False, f"Script execution test failed: {error}. Automatic fix applied.", fixed_script
                return False, f"Script execution test failed: {error}", None
        
        return True, "Script passed all tests", None
    
    def _try_fix_syntax_error(self, script: str, error_msg: str) -> Optional[str]:
        """
        Try to fix common syntax errors
        
        Args:
            script: The script with syntax error
            error_msg: The error message
            
        Returns:
            Optional[str]: Fixed script if possible, None otherwise
        """
        # Fix indentation issues
        if "unindent does not match any outer indentation level" in error_msg:
            return self._fix_indentation_issues(script)
        
        # Fix missing loops for iterative operations
        if "unexpected indent" in error_msg and any(pattern in script for pattern in ["df.iloc[i,", "df.loc[i,"]):
            return self._add_missing_loop(script)
        
        # Fix missing colons in if/for statements
        if "expected ':'" in error_msg:
            return self._fix_missing_colons(script)
        
        return None
    
    def _fix_indentation_issues(self, script: str) -> str:
        """
        Fix indentation issues in the script
        
        Args:
            script: The script with indentation issues
            
        Returns:
            str: Fixed script
        """
        lines = script.split('\n')
        fixed_lines = []
        current_indent = 0
        
        for line in lines:
            stripped = line.lstrip()
            if not stripped or stripped.startswith('#'):
                fixed_lines.append(line)  # Keep comments and empty lines as is
                continue
                
            # Detect indentation decrease
            if stripped.startswith(('else:', 'elif ', 'except:', 'finally:')):
                current_indent = max(0, current_indent - 4)
                
            # Apply current indentation
            fixed_lines.append(' ' * current_indent + stripped)
            
            # Detect indentation increase
            if stripped.endswith(':'):
                current_indent += 4
        
        # If script contains conditional blocks but no outer loop, add a loop
        fixed_script = '\n'.join(fixed_lines)
        if any(pattern in fixed_script for pattern in ["if pd.notna(df.iloc", "if isinstance(df.iloc"]):
            if not any(pattern in fixed_script for pattern in ["for i in range", "for i, row in df.iterrows()"]):
                fixed_script = self._add_missing_loop(fixed_script)
        
        return fixed_script
    
    def _add_missing_loop(self, script: str) -> str:
        """
        Add a missing loop for iterative operations
        
        Args:
            script: The script missing a loop
            
        Returns:
            str: Fixed script with added loop
        """
        if "for " in script:
            # There's already a loop, but it might be improperly indented
            return self._fix_indentation_issues(script)
        
        # Look for patterns suggesting we need a loop over DataFrame rows
        contains_iloc_with_variable = any(pattern in script for pattern in ["df.iloc[i,", "df.loc[i,"])
        
        if contains_iloc_with_variable:
            # Add a loop over all rows
            loop_header = "for i in range(len(df)):\n"
            indented_script = "    " + script.replace("\n", "\n    ")
            return loop_header + indented_script
        
        # Check if we need row/column iteration
        if "df.iloc" in script:
            # This script uses iloc indexing but without a loop
            # Let's analyze the script to see if it's using numeric indices
            operations = re.findall(r'df\.iloc\[(\d+),\s*(\d+)\]', script)
            if operations:
                # Script uses hardcoded indices, no need for a loop
                return script
            
            # If we can't determine the pattern, add a general loop
            loop_header = "for i in range(len(df)):\n"
            indented_script = "    " + script.replace("\n", "\n    ")
            return loop_header + indented_script
        
        # No clear pattern, return as is
        return script
    
    def _fix_missing_colons(self, script: str) -> str:
        """
        Fix missing colons in if/for statements
        
        Args:
            script: The script with missing colons
            
        Returns:
            str: Fixed script
        """
        # Common control structures that need colons
        control_patterns = [
            (r'(if\s+[^:]+)(?!\s*:)', r'\1:'),  # if statements
            (r'(elif\s+[^:]+)(?!\s*:)', r'\1:'),  # elif statements
            (r'(else)(?!\s*:)', r'else:'),  # else statements
            (r'(for\s+[^:]+)(?!\s*:)', r'\1:'),  # for loops
            (r'(while\s+[^:]+)(?!\s*:)', r'\1:'),  # while loops
            (r'(try)(?!\s*:)', r'try:'),  # try blocks
            (r'(except\s*[^:]*?)(?!\s*:)', r'\1:'),  # except blocks
            (r'(finally)(?!\s*:)', r'finally:')  # finally blocks
        ]
        
        fixed = script
        for pattern, replacement in control_patterns:
            fixed = re.sub(pattern, replacement, fixed)
        
        return fixed
    
    def _check_logical_issues(self, script: str) -> Tuple[bool, str, Optional[str]]:
        """
        Check for common logical issues in the script
        
        Args:
            script: The script to check
            
        Returns:
            Tuple[bool, str, Optional[str]]: (is_valid, error_message, fixed_script)
        """
        # Check for missing loop when using df.iloc with row index 'i'
        if re.search(r'df\.iloc\[i,', script) and not re.search(r'for\s+i\s+in', script):
            fixed = self._add_missing_loop(script)
            return False, "Script uses 'i' as index but has no loop. Added missing loop.", fixed
        
        # Check for empty blocks (if/for statements without body)
        if re.search(r'(if|for|while).+:\s*$', script):
            fixed = self._fix_empty_blocks(script)
            return False, "Script has empty control blocks. Added pass statements.", fixed
        
        # Check for possible infinite loops
        if "while" in script and "break" not in script:
            return False, "Script contains a while loop without a break statement, which might cause an infinite loop.", None
        
        return True, "", None
    
    def _fix_empty_blocks(self, script: str) -> str:
        """
        Fix empty control blocks by adding pass statements
        
        Args:
            script: The script with empty blocks
            
        Returns:
            str: Fixed script
        """
        lines = script.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            fixed_lines.append(line)
            if re.search(r'(if|for|while|else|elif|try|except|finally).+:\s*$', line):
                # This line has a control statement ending with a colon
                # Check if the next line is indented
                if i == len(lines) - 1 or not lines[i+1].startswith(' '):
                    # No indented block, add a pass statement
                    indent = len(line) - len(line.lstrip())
                    fixed_lines.append(' ' * (indent + 4) + 'pass')
        
        return '\n'.join(fixed_lines)
    
    def _test_execution(self, script: str, sample_df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Test execute the script on a sample DataFrame
        
        Args:
            script: The script to test
            sample_df: Sample DataFrame for testing
            
        Returns:
            Tuple[bool, str]: (success, error_message)
        """
        # Create a copy of the sample DataFrame
        df = sample_df.copy()
        
        # Create a test environment
        test_globals = {
            'df': df,
            'pd': pd,
            'np': np,
            'print': print
        }
        
        # Execute the script in the test environment
        try:
            exec(script, test_globals)
            return True, ""
        except Exception as e:
            return False, str(e)
    
    def _try_fix_execution_error(self, script: str, error_msg: str, sample_df: pd.DataFrame) -> Optional[str]:
        """
        Try to fix errors that occur during script execution
        
        Args:
            script: The script with execution error
            error_msg: The error message
            sample_df: Sample DataFrame used in testing
            
        Returns:
            Optional[str]: Fixed script if possible, None otherwise
        """
        # Fix out of bounds errors
        if "index out of bounds" in error_msg or "IndexError: single positional indexer is out-of-bounds" in error_msg:
            return self._fix_index_out_of_bounds(script, sample_df)
        
        # Fix column access errors
        if "not in index" in error_msg:
            return self._fix_column_access(script, sample_df)
        
        # Fix attribute errors
        if "has no attribute" in error_msg:
            return self._fix_attribute_errors(script, error_msg)
        
        # Fix type errors
        if "TypeError" in error_msg:
            return self._fix_type_errors(script, error_msg)
        
        return None
    
    def _fix_index_out_of_bounds(self, script: str, sample_df: pd.DataFrame) -> str:
        """
        Fix index out of bounds errors by adding bounds checks
        
        Args:
            script: The script with index errors
            sample_df: Sample DataFrame
            
        Returns:
            str: Fixed script
        """
        row_count = len(sample_df)
        col_count = len(sample_df.columns)
        
        lines = script.split('\n')
        fixed_lines = []
        
        for line in lines:
            # Skip comments and empty lines
            if not line.strip() or line.strip().startswith('#'):
                fixed_lines.append(line)
                continue
            
            # Find df.iloc operations
            iloc_ops = re.findall(r'df\.iloc\[(\d+),\s*(\d+)\]', line)
            needs_bounds_check = False
            
            for row_idx_str, col_idx_str in iloc_ops:
                row_idx = int(row_idx_str)
                col_idx = int(col_idx_str)
                
                if row_idx >= row_count or col_idx >= col_count:
                    needs_bounds_check = True
                    break
            
            if needs_bounds_check:
                # Add a bounds check
                indent = len(line) - len(line.lstrip())
                bounds_check = ' ' * indent + f"if {row_idx} < len(df) and {col_idx} < len(df.columns):"
                fixed_lines.append(bounds_check)
                fixed_lines.append(' ' * (indent + 4) + line.strip())
            else:
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _fix_column_access(self, script: str, sample_df: pd.DataFrame) -> str:
        """
        Fix column access errors by replacing column names with indices
        
        Args:
            script: The script with column access errors
            sample_df: Sample DataFrame
            
        Returns:
            str: Fixed script
        """
        # Get column names and indices
        column_indices = {col: i for i, col in enumerate(sample_df.columns)}
        
        lines = script.split('\n')
        fixed_lines = []
        
        for line in lines:
            # Replace df['column_name'] with df.iloc[:, column_index]
            for col, idx in column_indices.items():
                # Skip numeric column names to avoid false replacements
                if isinstance(col, (int, float)) or (isinstance(col, str) and col.isdigit()):
                    continue
                
                # Replace quoted column names
                line = line.replace(f"df['{col}']", f"df.iloc[:, {idx}]")
                line = line.replace(f'df["{col}"]', f"df.iloc[:, {idx}]")
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _fix_attribute_errors(self, script: str, error_msg: str) -> str:
        """
        Fix attribute errors by replacing invalid attributes
        
        Args:
            script: The script with attribute errors
            error_msg: The error message
            
        Returns:
            str: Fixed script
        """
        # Extract the object and attribute from the error message
        match = re.search(r"'(.+?)' object has no attribute '(.+?)'", error_msg)
        if not match:
            return script
            
        obj_type, invalid_attr = match.groups()
        
        # Common attribute error fixes
        replacements = {
            # DataFrame attribute fixes
            ("DataFrame", "len"): "lambda df: len(df)",
            ("DataFrame", "shape[0]"): "len",
            ("DataFrame", "shape[1]"): "lambda df: len(df.columns)",
            # Series attribute fixes
            ("Series", "len"): "lambda s: len(s)",
            # Common typos
            ("DataFrame", "colums"): "columns",
            ("DataFrame", "column"): "columns",
            ("DataFrame", "row"): "index",
            ("DataFrame", "rows"): "index",
        }
        
        key = (obj_type, invalid_attr)
        if key in replacements:
            replacement = replacements[key]
            return script.replace(f".{invalid_attr}", f".{replacement}")
        
        return script
    
    def _fix_type_errors(self, script: str, error_msg: str) -> str:
        """
        Fix type errors by adding appropriate conversions
        
        Args:
            script: The script with type errors
            error_msg: The error message
            
        Returns:
            str: Fixed script
        """
        # Extract information from the error message
        if "must be str, not " in error_msg:
            # String concatenation issue
            return script.replace(" + ", " + str(") + ")"
        
        if "cannot convert the series to " in error_msg:
            # Type conversion issue
            return script.replace(".astype(", ".astype(str).astype(")
        
        return script
    
    def validate_script_structure_compatibility(self, script: str, current_df: pd.DataFrame) -> Tuple[bool, str, Optional[str]]:
        """
        Validate that a script is compatible with the current DataFrame structure
        
        Args:
            script: The script to validate
            current_df: The current DataFrame structure
            
        Returns:
            Tuple[bool, str, Optional[str]]: (is_compatible, error_message, fixed_script)
        """
        print(f"🔍 STRUCTURE COMPATIBILITY CHECK:")
        print(f"   DataFrame: {current_df.shape[0]} rows × {current_df.shape[1]} columns")
        print(f"   Columns: {list(current_df.columns)}")
        
        # Check for hardcoded row/column indices that might be out of bounds
        max_row_in_script = -1
        max_col_in_script = -1
        
        # Find all iloc operations in the script
        iloc_pattern = re.compile(r'df\.iloc\[(\d+),\s*(\d+)\]')
        matches = iloc_pattern.findall(script)
        
        for row_str, col_str in matches:
            row_idx = int(row_str)
            col_idx = int(col_str)
            max_row_in_script = max(max_row_in_script, row_idx)
            max_col_in_script = max(max_col_in_script, col_idx)
        
        current_rows, current_cols = current_df.shape
        
        # Check for out-of-bounds access
        structure_issues = []
        
        if max_row_in_script >= current_rows:
            structure_issues.append(f"Script tries to access row {max_row_in_script}, but DataFrame only has {current_rows} rows")
        
        if max_col_in_script >= current_cols:
            structure_issues.append(f"Script tries to access column {max_col_in_script}, but DataFrame only has {current_cols} columns")
        
        # Check for column name references that might not exist
        column_pattern = re.compile(r'df\[[\'"](.*?)[\'"]\]')
        column_refs = column_pattern.findall(script)
        
        for col_name in column_refs:
            if col_name not in current_df.columns:
                structure_issues.append(f"Script references column '{col_name}', but it doesn't exist in current DataFrame")
        
        if structure_issues:
            error_msg = "Script structure compatibility issues:\n" + "\n".join([f"  - {issue}" for issue in structure_issues])
            
            # Try to fix the issues
            fixed_script = self._fix_structure_compatibility_issues(script, current_df, structure_issues)
            
            return False, error_msg, fixed_script
        
        print("✅ Script is compatible with current DataFrame structure")
        return True, "", None
    
    def _fix_structure_compatibility_issues(self, script: str, current_df: pd.DataFrame, issues: List[str]) -> str:
        """
        Try to fix structure compatibility issues
        
        Args:
            script: The script with issues
            current_df: The current DataFrame
            issues: List of structure issues
            
        Returns:
            str: Fixed script
        """
        fixed_script = script
        current_rows, current_cols = current_df.shape
        
        print(f"🔧 Attempting to fix {len(issues)} structure compatibility issues...")
        
        # Fix out-of-bounds iloc operations
        iloc_pattern = re.compile(r'df\.iloc\[(\d+),\s*(\d+)\]')
        
        def replace_iloc(match):
            row_idx = int(match.group(1))
            col_idx = int(match.group(2))
            
            # Clamp to valid ranges
            safe_row = min(row_idx, current_rows - 1)
            safe_col = min(col_idx, current_cols - 1)
            
            if safe_row != row_idx or safe_col != col_idx:
                print(f"   🔧 Fixed iloc[{row_idx}, {col_idx}] → iloc[{safe_row}, {safe_col}]")
            
            return f"df.iloc[{safe_row}, {safe_col}]"
        
        fixed_script = iloc_pattern.sub(replace_iloc, fixed_script)
        
        # Fix column name references
        column_pattern = re.compile(r'df\[[\'"](.*?)[\'"]\]')
        available_columns = list(current_df.columns)
        
        def replace_column_ref(match):
            col_name = match.group(1)
            
            if col_name not in available_columns:
                # Try to find a similar column name
                if available_columns:
                    # Use the first available column as a fallback
                    fallback_col = available_columns[0]
                    print(f"   🔧 Fixed column reference '{col_name}' → '{fallback_col}'")
                    return f"df['{fallback_col}']"
                else:
                    # No columns available, replace with iloc
                    print(f"   🔧 Fixed column reference '{col_name}' → df.iloc[:, 0]")
                    return "df.iloc[:, 0]"
            
            return match.group(0)  # Return original if column exists
        
        fixed_script = column_pattern.sub(replace_column_ref, fixed_script)
        
        return fixed_script
