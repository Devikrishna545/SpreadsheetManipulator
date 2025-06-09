"""
Schema Generator module
------------------
Generates JSON schema from spreadsheet data and vice versa
"""

import pandas as pd
import json
from typing import Dict, Any, List, Optional

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
            
            # Get sample values (up to 3)
            sample_values = df[col_name].dropna().head(3).tolist()
            
            columns.append({
                "name": str(col_name),
                "type": dtype,
                "sample_values": sample_values
            })
        
        # Get sample rows (up to 5)
        sample_data = []
        for _, row in df.head(5).iterrows():
            sample_data.append(row.to_dict())
        
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
        to match the target schema. The script should:
        
        1. Rename columns as needed
        2. Convert data types to match the target
        3. Reorder columns to match the target
        4. Apply any necessary transformations to make the data structure match
        5. Identify and transform all similar tables within the source data
        
        The script should handle the case where the source data may contain multiple tables 
        with similar structures. Each of these tables should be transformed.
        
        Return only the Python code without explanations.
        """.format(
            source_schema=json.dumps(source_schema, indent=2),
            target_schema=json.dumps(target_schema, indent=2)
        )
        
        return prompt
