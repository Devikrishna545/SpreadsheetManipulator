"""Test and validate scripts to catch syntax and common issues before execution."""

import numpy as np
import pandas as pd
import ast, logging, re
from typing import List, Optional, Tuple

from src.controller.security_manager import SecurityManager

class ScriptTester:
    """Tests scripts for syntax errors, security, and common issues."""
    
    def __init__(self):
        """Initialize the script tester."""
        self.security_manager = SecurityManager()
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def test_script(self, script: str, sample_df: Optional[pd.DataFrame] = None) -> Tuple[bool, str, Optional[str]]:
        """Test a script for syntax errors and common issues."""
    # Step 1: Check structure compatibility first if DataFrame is provided
        if sample_df is not None:
            is_compatible, structure_error, structure_fixed = self.validate_script_structure_compatibility(script, sample_df)
            if not is_compatible:
                if structure_fixed:
                    logging.info("🔧 Structure compatibility issues detected and fixed")
                    script = structure_fixed  # Use the structure-fixed version
                else:
                    return False, f"Structure compatibility failed: {structure_error}", None
        
        # Step 2: Check for basic syntax errors
        try:
            ast.parse(script)
        except SyntaxError as e:
            error_msg = str(e)
            logging.warning(f"Syntax error detected: {error_msg}")
            fixed_script = self._try_fix_syntax_error(script, error_msg)
            if fixed_script:
                # Re-test the fixed script
                try:
                    ast.parse(fixed_script)
                    logging.info("Successfully applied automatic syntax fix.")
                    return False, f"Original script had syntax error: {error_msg}. Automatic fix applied.", fixed_script
                except SyntaxError as e2:
                    logging.error(f"Automatic syntax fix failed with new error: {e2}")
                    return False, f"Script has syntax error: {error_msg}. Fix attempt failed with: {str(e2)}", None
            return False, f"Script has syntax error: {error_msg}", None
        
    # Step 3: Check for security concerns
        is_safe = self.security_manager.validate_script(script, script_name="script_test")
        if not is_safe:
            return False, f"Script validation failed due to security concerns", None
        
        # Step 4: Check for common logical issues
        result, issue, fixed = self._check_logical_issues(script)
        if not result:
            return False, issue, fixed
        
    # Step 5: Try to execute the script on a sample DataFrame if provided
        if sample_df is not None:
            success, error = self._test_execution(script, sample_df)
            if not success:
                logging.warning(f"Script execution test failed: {error}")
                fixed_script = self._try_fix_execution_error(script, error, sample_df)
                if fixed_script:
                    logging.info("Successfully applied automatic execution fix.")
                    return False, f"Script execution test failed: {error}. Automatic fix applied.", fixed_script
                return False, f"Script execution test failed: {error}", None
        
        return True, "Script passed all tests", None
    
    def _try_fix_syntax_error(self, script: str, error_msg: str) -> Optional[str]:
        """Try to fix common syntax errors."""
        print(f"🔧 [SCRIPT TESTER] Attempting to fix syntax error: {error_msg}")
        
        # Fix for "expected an indented block" or EOF errors
        if "expected an indented block" in error_msg or "unexpected EOF" in error_msg:
            lines = script.split('\n')
            fixed = False
            for i in range(len(lines) - 1, -1, -1):
                line = lines[i].rstrip()
                if line.endswith(':'):
                    # Check if it's the last line or the next line is not indented
                    if (i + 1 == len(lines)) or (lines[i+1].strip() == "") or \
                       (len(lines[i+1]) - len(lines[i+1].lstrip()) <= len(line) - len(line.lstrip())):
                        indentation = ' ' * (len(line) - len(line.lstrip()) + 4)
                        
                        # For specific cases, try to intelligently complete the block
                        if 'if any(' in line:
                            # Check for row deletion patterns based on context
                            deletion_keywords = ['drop', 'delete', 'remove', 'clear', 'erase']
                            searching_patterns = ['totals', 'net difference', 'sum', 'total', 'subtotal', 'header', 'footer']
                            
                            # Check the command context or the script content for deletion intent
                            script_lower = script.lower()
                            has_deletion_context = any(keyword in script_lower for keyword in deletion_keywords)
                            has_search_pattern = any(pattern in script_lower for pattern in searching_patterns)
                            
                            # Also check for iterating over rows pattern which usually indicates row-level operations
                            has_row_iteration = any(pattern in script for pattern in [
                                'for index, row in df.iterrows()',
                                'for i, row in df.iterrows()',
                                'for idx, row in df.iterrows()'
                            ])
                            
                            # If we find keyword search patterns + row iteration, it's likely a deletion operation
                            if (has_deletion_context or has_search_pattern) and has_row_iteration:
                                # This looks like a row deletion pattern
                                lines.insert(i + 1, indentation + 'df.drop(index, inplace=True)')
                                print(f"   ✓ Fixed by adding row deletion logic")
                            elif 'if any(' in line and 'keyword' in line and has_row_iteration:
                                # Even without explicit deletion words, if searching for keywords in rows, likely deletion
                                lines.insert(i + 1, indentation + 'df.drop(index, inplace=True)')
                                print(f"   ✓ Fixed by adding row deletion logic (inferred from pattern)")
                            else:
                                lines.insert(i + 1, indentation + 'pass  # TODO: Add action here')
                                print(f"   ✓ Fixed by adding placeholder with TODO")
                        elif 'for' in line and ('df.iterrows()' in line or 'enumerate(' in line):
                            # For loops without conditions usually need some action
                            lines.insert(i + 1, indentation + 'pass  # TODO: Add loop body')
                            print(f"   ✓ Fixed by adding loop body placeholder")
                        else:
                            lines.insert(i + 1, indentation + 'pass')
                            print(f"   ✓ Fixed by adding 'pass' statement")
                        
                        fixed = True
                        break
            
            if fixed:
                fixed_script = '\n'.join(lines)
                return fixed_script

        if "unindent does not match any outer indentation level" in error_msg:
            print(f"   ✓ Fixing indentation issues")
            return self._fix_indentation_issues(script)
        
        if "unexpected indent" in error_msg and any(pattern in script for pattern in ["df.iloc[i,", "df.loc[i,"]):
            print(f"   ✓ Adding missing loop")
            return self._add_missing_loop(script)
        
        if "expected ':'" in error_msg:
            print(f"   ✓ Fixing missing colons")
            return self._fix_missing_colons(script)
            
        if "invalid syntax" in error_msg:
            print(f"   ✓ Attempting to fix invalid syntax")
            brackets = {'(': ')', '[': ']', '{': '}'}
            stack = []
            for char in script:
                if char in brackets.keys():
                    stack.append(char)
                elif char in brackets.values():
                    if not stack or brackets[stack.pop()] != char:
                        fixed = script
                        for opening, closing in brackets.items():
                            opening_count = script.count(opening)
                            closing_count = script.count(closing)
                            if opening_count > closing_count:
                                fixed += closing * (opening_count - closing_count)
                            elif closing_count > opening_count:
                                fixed = opening * (closing_count - opening_count) + fixed
                        return fixed
        
        return None
    
    def _fix_indentation_issues(self, script: str) -> str:
        """Fix indentation issues in the script."""
        lines = script.split('\n')
        fixed_lines = []
        current_indent = 0

        for line in lines:
            stripped = line.lstrip()
            if not stripped or stripped.startswith('#'):
                fixed_lines.append(line)  # Keep comments and empty lines as is
                continue

            if stripped.startswith(('else:', 'elif ', 'except:', 'finally:')):
                current_indent = max(0, current_indent - 4)

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
        """Add a missing loop for iterative operations."""
        if "for " in script:
            # There's already a loop, but it might be improperly indented
            return self._fix_indentation_issues(script)

        # Look for patterns suggesting we need a loop over DataFrame rows
        contains_iloc_with_variable = any(pattern in script for pattern in ["df.iloc[i,", "df.loc[i,"])

        if contains_iloc_with_variable:
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
        """Fix missing colons in if/for statements."""
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
        """Check for common logical issues in the script."""
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
        """Fix empty control blocks by adding pass statements."""
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
        """Test execute the script on a sample DataFrame."""
        print(f"🧪 [SCRIPT TESTER] Testing script execution:")
        print(f"   Sample DataFrame shape: {sample_df.shape}")
        print(f"   Sample DataFrame columns: {list(sample_df.columns)}")
        print(f"   Sample DataFrame index: {list(sample_df.index)}")
        print(f"   Script to test:\n\n{script.strip()}\n")
        
        df = sample_df.copy()
        
        test_globals = {
            'df': df,
            'pd': pd,
            'np': np,
            'print': print
        }
        
        try:
            exec(script, test_globals)
            print(f"✅ [SCRIPT TESTER] Script execution successful")
            return True, ""
        except SyntaxError as e:
            # Align with function annotation and caller expecting two values
            return False, f"Script has syntax error: {e}"
        except Exception as e:
            error_message = f"Script execution failed: {e}"
            logging.error(error_message)
            return False, error_message
    
    def _try_fix_execution_error(self, script: str, error_msg: str, sample_df: pd.DataFrame) -> Optional[str]:
        """Try to fix errors that occur during script execution."""
        print(f"🔧 [SCRIPT TESTER] Attempting to fix error: {error_msg}")
        
        if "Index([" in error_msg and "dtype='object'" in error_msg and "drop_duplicates" in script:
            return self._fix_column_reference_error(script, error_msg, sample_df)
        
        if "not found in axis" in error_msg:
            return self._fix_drop_index_error(script, error_msg, sample_df)
        
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
    
    def _fix_drop_index_error(self, script: str, error_msg: str, sample_df: pd.DataFrame) -> Optional[str]:
        """Fix "not found in axis" errors that occur when trying to drop non-existent indices."""
        print(f"🔧 [SCRIPT TESTER] Fixing drop index error for DataFrame with {len(sample_df)} rows")
        
        # Extract the index that caused the error from the error message
        index_match = re.search(r'\[(\d+)\] not found in axis', error_msg)
        if not index_match:
            return None
        
        problematic_index = int(index_match.group(1))
        max_valid_index = len(sample_df) - 1
        
        print(f"   Problematic index: {problematic_index}, Max valid index: {max_valid_index}")
        
        # If the problematic index is out of bounds, adjust it
        if problematic_index > max_valid_index:
            if max_valid_index >= 0:
                # Replace with the last valid index
                fixed_script = script.replace(f'index={problematic_index}', f'index={max_valid_index}')
                print(f"   ✓ Fixed: Replaced index {problematic_index} with {max_valid_index}")
                return fixed_script
            else:
                # DataFrame is empty, return a script that does nothing
                print(f"   ✓ Fixed: DataFrame is empty, returning no-op script")
                return "# DataFrame is empty, no rows to drop\npass"
        
        # If index is 0 and DataFrame has rows, ensure we're using the correct method
        if problematic_index == 0 and len(sample_df) > 0:
            # Check if we're using df.drop with index=0
            if "df = df.drop(index=0" in script:
                # This is already the correct approach, issue might be elsewhere
                # Let's add some diagnostic code to check if row 0 exists
                fixed_script = """# Adding robust row deletion
if len(df) > 0:
    df = df.iloc[1:].reset_index(drop=True)
# Original attempted: df.drop(index=0)"""
                print(f"   ✓ Fixed: Using more robust iloc approach for first row deletion")
                return fixed_script
            
            # Check if we're trying to drop by label
            if "df = df.drop(" in script and "index=" not in script:
                # User might be trying to drop by label rather than position
                fixed_script = "# Ensure dropping by position, not label\ndf = df.iloc[1:].reset_index(drop=True)"
                print(f"   ✓ Fixed: Changing from label-based to position-based row deletion")
                return fixed_script
        
        return None

    def _fix_index_out_of_bounds(self, script: str, sample_df: pd.DataFrame) -> str:
        """Fix index out of bounds errors by iterating backwards when dropping rows."""
        print(f"🔧 [SCRIPT TESTER] Fixing index out of bounds error for DataFrame with {len(sample_df)} rows")
        
        # This fix is specifically for loops that drop rows
        if "df.drop" in script and "for" in script:
            print("   Applying reverse-iteration fix for row deletion loop")
            
            # Pattern 1: range(start, len(df)) -> range(len(df)-1, start-1, -1)
            range_pattern = r'range\((\d+), len\(df\)\)'
            match = re.search(range_pattern, script)
            if match:
                start_index = int(match.group(1))
                old_range = f"range({start_index}, len(df))"
                new_range = f"range(len(df)-1, {start_index-1}, -1)"
                fixed_script = script.replace(old_range, new_range)
                print(f"   ✓ Fixed: {old_range} -> {new_range}")
                return fixed_script
            
            # Pattern 2: range(len(df)) -> range(len(df)-1, -1, -1)
            if "range(len(df))" in script:
                fixed_script = script.replace("range(len(df))", "range(len(df) - 1, -1, -1)")
                print("   ✓ Fixed: range(len(df)) -> range(len(df) - 1, -1, -1)")
                return fixed_script
            
        return script
    
    def _fix_column_access(self, script: str, sample_df: pd.DataFrame) -> str:
        """Fix column access errors by replacing column names with indices."""
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
        """Fix attribute errors by replacing invalid attributes."""
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
        """Fix type errors by adding appropriate conversions."""
        if "must be str, not " in error_msg:
            # String concatenation issue
            return script.replace(" + ", " + str(") + ")"
        
        if "cannot convert the series to " in error_msg:
            # Type conversion issue
            return script.replace(".astype(", ".astype(str).astype(")
        
        return script
    
    def validate_script_structure_compatibility(self, script: str, current_df: pd.DataFrame) -> Tuple[bool, str, Optional[str]]:
        """Validate that a script is compatible with the current DataFrame structure."""
        print(f"🔍 STRUCTURE COMPATIBILITY CHECK:")
        print(f"   DataFrame: {current_df.shape[0]} rows × {current_df.shape[1]} columns")
        print(f"   Columns: {list(current_df.columns)}")
        
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
        
        # Also check for row-only iloc operations
        row_iloc_pattern = re.compile(r'df\.iloc\[(\d+)\]')
        row_matches = row_iloc_pattern.findall(script)
        
        for row_str in row_matches:
            row_idx = int(row_str)
            max_row_in_script = max(max_row_in_script, row_idx)
        
        # Check for drop operations with explicit indices
        drop_pattern = re.compile(r'df\.drop\(\s*(?:index=)?(\d+)')
        drop_matches = drop_pattern.findall(script)
        
        for row_str in drop_matches:
            row_idx = int(row_str)
            max_row_in_script = max(max_row_in_script, row_idx)
            
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
        """Try to fix structure compatibility issues."""
        fixed_script = script
        current_rows, current_cols = current_df.shape
        
        print(f"🔧 Attempting to fix {len(issues)} structure compatibility issues...")
        
        # Fix out-of-bounds iloc operations
        iloc_pattern = re.compile(r'df\.iloc\[(\d+),\s*(\d+)\]')
        
        def replace_iloc(match):
            row_idx = int(match.group(1))
            col_idx = int(match.group(2))
            
            # Clamp to valid ranges
            safe_row = min(row_idx, max(0, current_rows - 1))
            safe_col = min(col_idx, max(0, current_cols - 1))
            
            if safe_row != row_idx or safe_col != col_idx:
                print(f"   🔧 Fixed iloc[{row_idx}, {col_idx}] → iloc[{safe_row}, {safe_col}]")
            
            return f"df.iloc[{safe_row}, {safe_col}]"
        
        fixed_script = iloc_pattern.sub(replace_iloc, fixed_script)
        
        # Fix row-only iloc operations
        row_iloc_pattern = re.compile(r'df\.iloc\[(\d+)\]')
        
        def replace_row_iloc(match):
            row_idx = int(match.group(1))
            safe_row = min(row_idx, max(0, current_rows - 1))
            
            if safe_row != row_idx:
                print(f"   🔧 Fixed iloc[{row_idx}] → iloc[{safe_row}]")
            
            return f"df.iloc[{safe_row}]"
        
        fixed_script = row_iloc_pattern.sub(replace_row_iloc, fixed_script)
        
        # Fix drop operations with explicit indices
        drop_pattern = re.compile(r'(df\.drop\(\s*(?:index=)?)(\d+)([,\s\)])')
        
        def replace_drop(match):
            prefix = match.group(1)
            row_idx = int(match.group(2))
            suffix = match.group(3)
            
            safe_row = min(row_idx, max(0, current_rows - 1))
            
            if safe_row != row_idx:
                print(f"   🔧 Fixed drop index {row_idx} → {safe_row}")
            
            return f"{prefix}{safe_row}{suffix}"
        
        fixed_script = drop_pattern.sub(replace_drop, fixed_script)
        
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
        
        # Add safety check at the beginning of the script
        if "# Structure compatibility fix" not in fixed_script:
            safety_check = """# Structure compatibility fix
# Ensure DataFrame has enough rows and columns
if len(df) == 0:
    # Handle empty DataFrame
    print("Warning: DataFrame is empty, no operations will be performed")
    # Return original DataFrame
    pass
else:
    # Continue with original logic
"""
            fixed_script = safety_check + fixed_script
            
        return fixed_script

    def _fix_column_reference_error(self, script: str, error_msg: str, sample_df: pd.DataFrame) -> Optional[str]:
        """Fix column reference errors in drop_duplicates operations."""
        print(f"🔧 [SCRIPT TESTER] Fixing column reference error in drop_duplicates")
        
        
        # Fix pattern 1: [str(col_idx) for col_idx in [numbers]] -> [numbers directly]
        pattern1 = r'\[str\(col_idx\) for col_idx in \[([^\]]+)\]\]'
        match1 = re.search(pattern1, script)
        
        if match1:
            indices_str = match1.group(1)
            try:
                # Extract the column indices and use them directly
                indices = [int(x.strip()) for x in indices_str.split(',')]
                # Check if these column indices exist in the DataFrame
                valid_indices = [idx for idx in indices if idx in sample_df.columns]
                
                if valid_indices:
                    old_subset = f"[str(col_idx) for col_idx in [{indices_str}]]"
                    new_subset = str(valid_indices)
                    fixed_script = script.replace(old_subset, new_subset)
                    print(f"   ✓ Fixed column list comprehension: {old_subset} -> {new_subset}")
                    return fixed_script
            except (ValueError, TypeError):
                pass
        
        # Fix pattern 2: subset=['9', '10', '11', '12', '13'] -> subset=[9, 10, 11, 12, 13]
        pattern2 = r"subset=\[(['\"][^'\"]+['\"],?\s*)+\]"
        match2 = re.search(pattern2, script)
        
        if match2:
            # Extract quoted numbers and convert to integers
            quoted_nums = re.findall(r"['\"](\d+)['\"]", script)
            if quoted_nums:
                # Convert to integers and check if they exist as columns
                int_cols = []
                for num_str in quoted_nums:
                    try:
                        col_idx = int(num_str)
                        if col_idx in sample_df.columns:
                            int_cols.append(col_idx)
                    except ValueError:
                        continue
                
                if int_cols:
                    # Replace the string column references with integer references
                    old_match = match2.group(0)
                    new_subset = f"subset={int_cols}"
                    fixed_script = script.replace(old_match, new_subset)
                    print(f"   ✓ Fixed string column references: {old_match} -> {new_subset}")
                    return fixed_script
        
        # Fix pattern 3: If we can extract column indices from the error message itself
        # Error messages like: Index(['12', '13', '9', '11', '10'], dtype='object')
        error_pattern = r"Index\(\[([^\]]+)\], dtype='object'\)"
        error_match = re.search(error_pattern, error_msg)
        
        if error_match:
            error_cols_str = error_match.group(1)
            # Extract the quoted column names from the error
            error_cols = re.findall(r"'(\d+)'", error_cols_str)
            
            if error_cols:
                # Convert to integers and check against DataFrame
                int_cols = []
                for col_str in error_cols:
                    try:
                        col_idx = int(col_str)
                        if col_idx in sample_df.columns:
                            int_cols.append(col_idx)
                    except ValueError:
                        continue
                
                if int_cols:
                    # Replace any string column references in drop_duplicates with integer ones
                    if "drop_duplicates" in script:
                        # Try to find and replace the subset parameter
                        subset_pattern = r"subset=\[[^\]]+\]"
                        if re.search(subset_pattern, script):
                            new_subset = f"subset={int_cols}"
                            fixed_script = re.sub(subset_pattern, new_subset, script)
                            print(f"   ✓ Fixed from error message: subset={int_cols}")
                            return fixed_script
        
        print("   ❌ Could not fix column reference error")
        return None
