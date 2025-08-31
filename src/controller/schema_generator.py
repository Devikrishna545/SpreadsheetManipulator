"""Schema generation and spreadsheet transformation helpers."""

import warnings
import pandas as pd
from typing import List, Dict, Tuple

class SchemaGenerator:
    """Generate and apply schema patterns for spreadsheets."""

    def __init__(self):
        """Initialize the schema generator."""
        pass
    
    def capture_schema_structure(self, right_data: List[List]) -> dict:
        """Capture structure/schema from the right spreadsheet template."""
        if not right_data or len(right_data) == 0:
            return {"error": "Right spreadsheet is empty"}
        
        schema = {
            "row_count": len(right_data),
            "col_count": len(right_data[0]) if right_data[0] else 0,
            "column_patterns": {},
            "transformation_rules": []
        }
        
        for col_idx in range(schema["col_count"]):
            column_data = [row[col_idx] if col_idx < len(row) else '' for row in right_data]
            column_analysis = self._analyze_column_pattern(column_data, col_idx)
            schema["column_patterns"][col_idx] = column_analysis
        
        return schema
    
    def _analyze_column_pattern(self, column_data: List, col_idx: int) -> dict:
        """Analyze column to determine its pattern (constant, sequence, etc.)."""
        non_empty_values = [val for val in column_data if val != '' and val is not None]
        
        if not non_empty_values:
            return {"type": "empty", "pattern": "empty_column"}
        
        unique_values = list(set(non_empty_values))
        if len(unique_values) == 1:
            return {
                "type": "constant",
                "pattern": "constant_value",
                "value": unique_values[0]
            }
        
        try:
            numeric_values = [float(val) for val in non_empty_values if str(val).replace('.', '').replace('-', '').isdigit()]
            if len(numeric_values) >= 2:
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
        
        if self._is_date_pattern(non_empty_values):
            return {
                "type": "date_sequence",
                "pattern": "date_progression",
                "values": non_empty_values
            }
        
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
        
        return {
            "type": "rearrangement",
            "pattern": "column_mapping",
            "values": non_empty_values
        }
    
    def _is_date_pattern(self, values: List) -> bool:
        """Return True if values can be parsed as dates (tolerant)."""
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                # Try specific formats first
                try:
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S']:
                        try:
                            pd.to_datetime(values, format=fmt, errors='raise')
                            return True
                        except Exception:
                            continue
                except Exception:
                    pass
                # Fallback to general parsing
                parsed_dates = pd.to_datetime(values, errors='coerce', infer_datetime_format=False)
                return not parsed_dates.isna().all()
        except Exception:
            return False
    
    def _find_repeating_cycle(self, values: List) -> int:
        """Find the length of a repeating cycle in the values."""
        for cycle_len in range(1, min(len(values) // 2 + 1, 10)):
            is_cycle = True
            for i in range(cycle_len, len(values)):
                if values[i] != values[i % cycle_len]:
                    is_cycle = False
                    break
            if is_cycle:
                return cycle_len
        return 0
    
    def apply_schema_patterns(self, df: pd.DataFrame, schema: dict, right_data: List[List]) -> Tuple[pd.DataFrame, List[List]]:
        """Apply schema patterns to transform the dataframe."""
        new_df = pd.DataFrame()
        modified_cells = []
        
        for col_idx, pattern in schema["column_patterns"].items():
            col_name = f"Column_{col_idx}"
            
            for row_idx in range(len(df)):
                modified_cells.append([row_idx, col_idx])
            
            if pattern["type"] == "constant":
                new_df[col_name] = [pattern["value"]] * len(df)
                
            elif pattern["type"] == "sequence":
                start_val = pattern["start_value"]
                increment = pattern["increment"]
                new_df[col_name] = [start_val + (i * increment) for i in range(len(df))]
                
            elif pattern["type"] == "date_sequence":
                try:
                    with warnings.catch_warnings():
                        warnings.filterwarnings("ignore")
                        
                        base_dates = None
                        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S', '%d-%m-%Y']:
                            try:
                                base_dates = pd.to_datetime(pattern["values"], format=fmt, errors='raise')
                                break
                            except Exception:
                                continue
                        
                        if base_dates is None:
                            base_dates = pd.to_datetime(pattern["values"], errors='coerce', infer_datetime_format=False)
                    
                    if len(base_dates) >= 2 and not base_dates.isna().all():
                        time_diff = base_dates.iloc[1] - base_dates.iloc[0]
                        date_sequence = [base_dates.iloc[0] + (i * time_diff) for i in range(len(df))]
                        new_df[col_name] = date_sequence
                    else:
                        new_df[col_name] = [pattern["values"][0]] * len(df)
                except Exception:
                    new_df[col_name] = [pattern["values"][0]] * len(df)
                    
            elif pattern["type"] == "cycle":
                cycle = pattern["cycle_values"]
                cycle_values = [cycle[i % len(cycle)] for i in range(len(df))]
                new_df[col_name] = cycle_values
                
            elif pattern["type"] == "rearrangement":
                if col_idx < len(df.columns):
                    new_df[col_name] = df.iloc[:, col_idx].values
                else:
                    first_val = pattern["values"][0] if pattern["values"] else ""
                    new_df[col_name] = [first_val] * len(df)
                    
            else:
                new_df[col_name] = [""] * len(df)
        
        return new_df, modified_cells

    def generate_schema_json(self, data: List[List]) -> dict:
        """Generate JSON schema representation from spreadsheet data."""
        if not data or len(data) == 0:
            return {"error": "No data provided"}
        
        schema = self.capture_schema_structure(data)
        
        json_schema = {
            "type": "object",
            "properties": {},
            "metadata": {
                "rows": schema["row_count"],
                "columns": schema["col_count"],
                "generated_at": pd.Timestamp.now().isoformat()
            }
        }
        
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
                    "sample_values": pattern["values"][:3]
                }
            elif pattern["type"] == "cycle":
                json_schema["properties"][property_name] = {
                    "type": "array",
                    "pattern": "repeating_cycle",
                    "cycle_values": pattern["cycle_values"],
                    "cycle_length": pattern["cycle_length"]
                }
            else:
                json_schema["properties"][property_name] = {
                    "type": "string",
                    "pattern": pattern["pattern"],
                    "sample_values": pattern.get("values", [])[:3]
                }
        
        return json_schema

    def validate_schema_compatibility(self, left_data: List[List], right_data: List[List]) -> dict:
        """Validate if left spreadsheet can be transformed to match right spreadsheet schema."""
        if not left_data or not right_data:
            return {
                "compatible": False,
                "reason": "Missing data - both left and right spreadsheets required"
            }
        
        left_schema = self.capture_schema_structure(left_data)
        right_schema = self.capture_schema_structure(right_data)
        
        compatibility = {
            "compatible": True,
            "warnings": [],
            "transformations": []
        }
        
        if len(left_data[0]) != len(right_data[0]):
            compatibility["warnings"].append(
                f"Column count mismatch: Left has {len(left_data[0])} columns, "
                f"Right has {len(right_data[0])} columns"
            )
        
        if len(left_data) < len(right_data):
            compatibility["warnings"].append(
                f"Left spreadsheet has fewer rows ({len(left_data)}) than right ({len(right_data)}). "
                "Transformation will use right spreadsheet patterns for all left rows."
            )
        
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
        """Assess complexity of transforming from one pattern to another."""
        if from_pattern["type"] == to_pattern["type"]:
            return "simple"
        
        if to_pattern["type"] in ["constant", "sequence"]:
            return "simple"
        
        if to_pattern["type"] in ["date_sequence", "cycle"]:
            return "moderate"
        
        return "complex"
