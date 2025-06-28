"""
Schema Generator module
------------------
Generates JSON schema from spreadsheet data and vice versa
"""

import pandas as pd
import json
from typing import Dict, Any, List, Optional
import datetime

def _serialize_datetimes(obj):
    """
    Recursively convert datetime objects in dicts/lists to ISO format strings.
    """
    if isinstance(obj, dict):
        return {k: _serialize_datetimes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_serialize_datetimes(v) for v in obj]
    elif isinstance(obj, (datetime.datetime, pd.Timestamp)):
        return obj.isoformat()
    else:
        return obj

class SchemaGenerator:
    """
    Generates and maintains a schema representation of spreadsheet data
    """
    
    def __init__(self):
        """Initialize the schema generator"""
        self.last_schema = None
        
    def generate_schema(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate a JSON schema from a pandas DataFrame
        
        Args:
            df: The pandas DataFrame to analyze
            
        Returns:
            Dict[str, Any]: JSON schema representing the structure and sample data
        """
        if df.empty:
            return {"columns": [], "sample_data": []}
        
        # Extract column info
        columns = []
        for col_name in df.columns:
            # Get column data type
            col_data = df[col_name].dropna()
            if len(col_data) == 0:
                dtype = "unknown"
            elif pd.api.types.is_numeric_dtype(col_data):
                if all(col_data.apply(lambda x: float(x).is_integer() if pd.notnull(x) else True)):
                    dtype = "integer"
                else:
                    dtype = "float"
            elif pd.api.types.is_datetime64_dtype(col_data):
                dtype = "datetime"
            else:
                dtype = "string"
            
            # Get sample values (up to 3), convert datetimes to string
            sample_values = [
                v.isoformat() if isinstance(v, (datetime.datetime, pd.Timestamp)) else v
                for v in df[col_name].dropna().head(3).tolist()
            ]
            columns.append({
                "name": str(col_name),
                "type": dtype,
                "sample_values": sample_values
            })
        
        # Get sample rows (up to 5), convert datetimes to string
        sample_data = []
        for _, row in df.head(5).iterrows():
            row_dict = row.to_dict()
            for k, v in row_dict.items():
                if isinstance(v, (datetime.datetime, pd.Timestamp)):
                    row_dict[k] = v.isoformat()
            sample_data.append(row_dict)
        
        schema = {
            "columns": columns,
            "sample_data": sample_data,
            "row_count": len(df),
            "column_count": len(df.columns)
        }
        
        self.last_schema = schema
        return schema
    
    def get_transformation_prompt(self, source_df: pd.DataFrame, target_schema: Dict[str, Any]) -> str:
        """
        Generate a prompt for LLM to transform source data to match target schema
        
        Args:
            source_df: The source pandas DataFrame
            target_schema: The target JSON schema
            
        Returns:
            str: A prompt for the LLM
        """
        source_schema = self.generate_schema(source_df)
        # Serialize datetimes in both schemas before dumping to JSON
        source_schema_serialized = _serialize_datetimes(source_schema)
        target_schema_serialized = _serialize_datetimes(target_schema)
        
        prompt = """
        I need to transform a source spreadsheet to match a target schema.

        SOURCE SCHEMA:
        ```json
        {source_schema}
        ```

        TARGET SCHEMA:
        ```json
        {target_schema}
        ```

        Please write a Python script using pandas that transforms the source DataFrame 'df' 
        to match the target schema. The script MUST be a UNIVERSAL ALGORITHM that processes 
        the ENTIRE DATASET, not just specific rows.

        CRITICAL REQUIREMENTS:
        1. **NEVER use hardcoded row indices like df.iloc[0, 1] = "value"**
        2. **Process ALL ROWS in the DataFrame - the algorithm must work on datasets of any size**
        3. **Use vectorized operations, loops, or apply functions to transform all rows**
        4. **Every cell in the result must contain appropriate data - no empty cells allowed**
        5. **The script must work on the entire dataset from first row to last row**
        6. **If the source has 7000+ rows, your algorithm must process all 7000+ rows**
        7. Rename columns as needed using df.columns = [new_column_names]
        8. Convert data types to match the target across all rows
        9. Apply transformations using patterns that work on the entire dataset
        10. If you need to expand the DataFrame, do it BEFORE writing any data
        11. Use operations like df['column'] = value or df.loc[:, 'column'] = values

        REQUIRED UNIVERSAL PATTERNS (Choose appropriate ones):
        ```python
        # Option 1: Full column assignment (when all rows should have same value)
        df['column_name'] = 'constant_value'
        
        # Option 2: Conditional assignment (when different rows need different values)
        df.loc[condition, 'column'] = 'value'
        df.loc[df['source_col'] == 'pattern', 'target_col'] = 'new_value'
        
        # Option 3: Loop through all rows (when each row needs individual processing)
        for i in range(len(df)):
            df.loc[i, 'column'] = compute_value_for_row(i)
        
        # Option 4: Apply function to transform values
        df['new_col'] = df['old_col'].apply(lambda x: transform_function(x))
        
        # Option 5: Vectorized operations
        df.loc[:, 'column'] = df['source'].str.replace('pattern', 'replacement')
        ```

        EXAMPLES OF FORBIDDEN PATTERNS:
        - df.iloc[0, 1] = "value"  # Only affects row 0
        - df.iloc[1:10, 2] = "value"  # Only affects rows 1-10
        - Any hardcoded row indices
        - Transformations that only work on a subset of data

        VALIDATION REQUIREMENTS:
        - Your algorithm MUST process every single row in the source DataFrame
        - If source has N rows, output must have N rows (or more if expansion is needed)
        - Every cell in the output should contain meaningful data (no empty cells)
        - The transformation pattern must be consistent across the entire dataset

        DATASET SIZE AWARENESS:
        - The source dataset may have thousands of rows (7000+)
        - Your algorithm must scale to handle any number of rows
        - Use efficient pandas operations that work on the entire DataFrame at once
        - Avoid row-by-row processing unless absolutely necessary for complex logic

        The script should identify the structure/pattern from the target schema and apply 
        that pattern to ALL rows in the source data. Every row should be transformed 
        according to the same logical rules.

        Return only the Python code without explanations.
        """.format(
            source_schema=json.dumps(source_schema_serialized, indent=2),
            target_schema=json.dumps(target_schema_serialized, indent=2)
        )
        
        return prompt
