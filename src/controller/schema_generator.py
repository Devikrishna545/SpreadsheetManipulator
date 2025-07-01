"""
Schema Generator module
-----------------------
Handles JSON schema generation and transformation logic for the "Update Schema" 
and "Transform to Schema" buttons. This module provides functionality to:
- Capture schema structure from spreadsheet data
- Analyze column patterns (constants, sequences, dates, cycles)
- Apply schema transformations to spreadsheet data
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple
import warnings


class SchemaGenerator:
    """
    Handles schema generation and transformation operations for spreadsheets
    """
    
    def __init__(self):
        """Initialize the schema generator"""
        pass
    
    def capture_schema_structure(self, right_data: List[List]) -> dict:
        """
        Capture the structure/schema from the right spreadsheet template
        
        Args:
            right_data: 2D array representing the right spreadsheet data
            
        Returns:
            dict: Schema information including patterns, structure, and transformations
        """
        if not right_data or len(right_data) == 0:
            return {"error": "Right spreadsheet is empty"}
        
        # Analyze the structure of the right spreadsheet
        schema = {
            "row_count": len(right_data),
            "col_count": len(right_data[0]) if right_data[0] else 0,
            "column_patterns": {},
            "transformation_rules": []
        }
        
        # Analyze each column for patterns
        for col_idx in range(schema["col_count"]):
            column_data = [row[col_idx] if col_idx < len(row) else '' for row in right_data]
            column_analysis = self._analyze_column_pattern(column_data, col_idx)
            schema["column_patterns"][col_idx] = column_analysis
        
        return schema
    
    def _analyze_column_pattern(self, column_data: List, col_idx: int) -> dict:
        """
        Analyze a column to determine its pattern (constant, sequence, etc.)
        
        Args:
            column_data: List of values in the column
            col_idx: Column index
            
        Returns:
            dict: Pattern analysis for the column
        """
        # Remove empty values for analysis
        non_empty_values = [val for val in column_data if val != '' and val is not None]
        
        if not non_empty_values:
            return {"type": "empty", "pattern": "empty_column"}
        
        # Check if all values are the same (constant)
        unique_values = list(set(non_empty_values))
        if len(unique_values) == 1:
            return {
                "type": "constant",
                "pattern": "constant_value",
                "value": unique_values[0]
            }
        
        # Check for numeric sequence
        try:
            numeric_values = [float(val) for val in non_empty_values if str(val).replace('.', '').replace('-', '').isdigit()]
            if len(numeric_values) >= 2:
                # Check if it's an arithmetic sequence
                diff = numeric_values[1] - numeric_values[0]
                is_sequence = all(
                    abs((numeric_values[i] - numeric_values[i-1]) - diff) < 0.001 
                    for i in range(1, len(numeric_values))
                )
                if is_sequence:
                    return {
                        "type": "sequence",
                        "pattern": "arithmetic_sequence",
                        "start_value": numeric_values[0],
                        "increment": diff
                    }
        except ValueError:
            pass
        
        # Check for date patterns
        if self._is_date_pattern(non_empty_values):
            return {
                "type": "date_sequence",
                "pattern": "date_progression",
                "values": non_empty_values
            }
        
        # Check for repeating cycle
        if len(non_empty_values) > 1:
            cycle_length = self._find_repeating_cycle(non_empty_values)
            if cycle_length > 0:
                cycle = non_empty_values[:cycle_length]
                return {
                    "type": "cycle",
                    "pattern": "repeating_cycle",
                    "cycle_values": cycle,
                    "cycle_length": cycle_length
                }
        
        # Default to column rearrangement
        return {
            "type": "rearrangement",
            "pattern": "column_mapping",
            "values": non_empty_values
        }
    
    def _is_date_pattern(self, values: List) -> bool:
        """Check if values represent a date pattern"""
        try:
            import pandas as pd
            import warnings
            # Suppress all warnings for date parsing including dateutil warnings
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")  # Suppress all warnings including dateutil
                
                # Try to parse as dates with specific formats first
                try:
                    # Try common date formats
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S']:
                        try:
                            parsed_dates = pd.to_datetime(values, format=fmt, errors='raise')
                            return True
                        except:
                            continue
                except:
                    pass
                
                # Fallback to general parsing with warnings suppressed
                parsed_dates = pd.to_datetime(values, errors='coerce', infer_datetime_format=False)
                return not parsed_dates.isna().all()
        except:
            return False
    
    def _find_repeating_cycle(self, values: List) -> int:
        """Find the length of a repeating cycle in the values"""
        for cycle_len in range(1, min(len(values) // 2 + 1, 10)):  # Limit cycle length
            is_cycle = True
            for i in range(cycle_len, len(values)):
                if values[i] != values[i % cycle_len]:
                    is_cycle = False
                    break
            if is_cycle:
                return cycle_len
        return 0
    
    def apply_schema_patterns(self, df: pd.DataFrame, schema: dict, right_data: List[List]) -> Tuple[pd.DataFrame, List[List]]:
        """
        Apply the schema patterns to transform the dataframe
        
        Args:
            df: Current dataframe to transform
            schema: Schema information from right spreadsheet
            right_data: Original right spreadsheet data
            
        Returns:
            tuple: (Transformed dataframe, list of modified cells)
        """
        import pandas as pd
        import numpy as np
        
        # Create a new dataframe with the same number of rows as original
        new_df = pd.DataFrame()
        modified_cells = []  # Track all modified cells for highlighting
        
        # Apply patterns for each column
        for col_idx, pattern in schema["column_patterns"].items():
            col_name = f"Column_{col_idx}"  # Use generic column names
            
            # Track all cells in this column as modified (since we're transforming the entire column)
            for row_idx in range(len(df)):
                modified_cells.append([row_idx, col_idx])  # [row, col] format for frontend
            
            if pattern["type"] == "constant":
                # Set all rows to the constant value
                new_df[col_name] = [pattern["value"]] * len(df)
                
            elif pattern["type"] == "sequence":
                # Generate arithmetic sequence
                start_val = pattern["start_value"]
                increment = pattern["increment"]
                new_df[col_name] = [start_val + (i * increment) for i in range(len(df))]
                
            elif pattern["type"] == "date_sequence":
                # Generate date sequence
                try:
                    import pandas as pd
                    import warnings
                    # Suppress all warnings for date parsing including dateutil warnings
                    with warnings.catch_warnings():
                        warnings.filterwarnings("ignore")  # Suppress all warnings including dateutil
                        
                        # Try specific date formats first
                        base_dates = None
                        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S', '%d-%m-%Y']:
                            try:
                                base_dates = pd.to_datetime(pattern["values"], format=fmt, errors='raise')
                                break
                            except:
                                continue
                        
                        # Fallback to general parsing with warnings suppressed
                        if base_dates is None:
                            base_dates = pd.to_datetime(pattern["values"], errors='coerce', infer_datetime_format=False)
                    
                    if len(base_dates) >= 2 and not base_dates.isna().all():
                        # Calculate the time difference
                        time_diff = base_dates.iloc[1] - base_dates.iloc[0]
                        # Generate sequence starting from first date
                        date_sequence = [base_dates.iloc[0] + (i * time_diff) for i in range(len(df))]
                        new_df[col_name] = date_sequence
                    else:
                        new_df[col_name] = [pattern["values"][0]] * len(df)
                except:
                    # Fallback to string values
                    new_df[col_name] = [pattern["values"][0]] * len(df)
                    
            elif pattern["type"] == "cycle":
                # Repeat the cycle pattern
                cycle = pattern["cycle_values"]
                cycle_values = [cycle[i % len(cycle)] for i in range(len(df))]
                new_df[col_name] = cycle_values
                
            elif pattern["type"] == "rearrangement":
                # Try to map from existing columns if possible
                if col_idx < len(df.columns):
                    # Use data from the corresponding column in original df
                    new_df[col_name] = df.iloc[:, col_idx].values
                else:
                    # Use the first value from the pattern
                    first_val = pattern["values"][0] if pattern["values"] else ""
                    new_df[col_name] = [first_val] * len(df)
                    
            else:  # empty or unknown
                new_df[col_name] = [""] * len(df)
        
        return new_df, modified_cells

    def generate_schema_json(self, data: List[List]) -> dict:
        """
        Generate a JSON schema representation from spreadsheet data
        
        Args:
            data: 2D array representing spreadsheet data
            
        Returns:
            dict: JSON schema representation
        """
        if not data or len(data) == 0:
            return {"error": "No data provided"}
        
        schema = self.capture_schema_structure(data)
        
        # Convert to a more structured JSON schema format
        json_schema = {
            "type": "object",
            "properties": {},
            "metadata": {
                "rows": schema["row_count"],
                "columns": schema["col_count"],
                "generated_at": pd.Timestamp.now().isoformat()
            }
        }
        
        # Create properties for each column
        for col_idx, pattern in schema["column_patterns"].items():
            property_name = f"column_{col_idx}"
            
            if pattern["type"] == "constant":
                json_schema["properties"][property_name] = {
                    "type": "constant",
                    "value": pattern["value"],
                    "pattern": pattern["pattern"]
                }
            elif pattern["type"] == "sequence":
                json_schema["properties"][property_name] = {
                    "type": "number",
                    "pattern": "arithmetic_sequence",
                    "start_value": pattern["start_value"],
                    "increment": pattern["increment"]
                }
            elif pattern["type"] == "date_sequence":
                json_schema["properties"][property_name] = {
                    "type": "string",
                    "format": "date",
                    "pattern": "date_progression",
                    "sample_values": pattern["values"][:3]  # First 3 values as samples
                }
            elif pattern["type"] == "cycle":
                json_schema["properties"][property_name] = {
                    "type": "array",
                    "pattern": "repeating_cycle",
                    "cycle_values": pattern["cycle_values"],
                    "cycle_length": pattern["cycle_length"]
                }
            else:  # rearrangement or empty
                json_schema["properties"][property_name] = {
                    "type": "string",
                    "pattern": pattern["pattern"],
                    "sample_values": pattern.get("values", [])[:3]
                }
        
        return json_schema

    def validate_schema_compatibility(self, left_data: List[List], right_data: List[List]) -> dict:
        """
        Validate if the left spreadsheet can be transformed to match the right spreadsheet schema
        
        Args:
            left_data: Source spreadsheet data
            right_data: Target spreadsheet schema data
            
        Returns:
            dict: Validation result with compatibility information
        """
        if not left_data or not right_data:
            return {
                "compatible": False,
                "reason": "Missing data - both left and right spreadsheets required"
            }
        
        left_schema = self.capture_schema_structure(left_data)
        right_schema = self.capture_schema_structure(right_data)
        
        # Check basic compatibility
        compatibility = {
            "compatible": True,
            "warnings": [],
            "transformations": []
        }
        
        # Check column count compatibility
        if len(left_data[0]) != len(right_data[0]):
            compatibility["warnings"].append(
                f"Column count mismatch: Left has {len(left_data[0])} columns, "
                f"Right has {len(right_data[0])} columns"
            )
        
        # Check row count
        if len(left_data) < len(right_data):
            compatibility["warnings"].append(
                f"Left spreadsheet has fewer rows ({len(left_data)}) than right ({len(right_data)}). "
                "Transformation will use right spreadsheet patterns for all left rows."
            )
        
        # Analyze transformations needed
        for col_idx, right_pattern in right_schema["column_patterns"].items():
            transformation = {
                "column": col_idx,
                "from_pattern": left_schema["column_patterns"].get(col_idx, {"type": "unknown"}),
                "to_pattern": right_pattern,
                "complexity": self._assess_transformation_complexity(
                    left_schema["column_patterns"].get(col_idx, {"type": "unknown"}),
                    right_pattern
                )
            }
            compatibility["transformations"].append(transformation)
        
        return compatibility
    
    def _assess_transformation_complexity(self, from_pattern: dict, to_pattern: dict) -> str:
        """
        Assess the complexity of transforming from one pattern to another
        
        Args:
            from_pattern: Source pattern
            to_pattern: Target pattern
            
        Returns:
            str: Complexity level ('simple', 'moderate', 'complex')
        """
        if from_pattern["type"] == to_pattern["type"]:
            return "simple"
        
        if to_pattern["type"] in ["constant", "sequence"]:
            return "simple"
        
        if to_pattern["type"] in ["date_sequence", "cycle"]:
            return "moderate"
        
        return "complex"
