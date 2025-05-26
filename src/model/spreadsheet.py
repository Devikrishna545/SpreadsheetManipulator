"""
Spreadsheet module
----------------
Represents a spreadsheet with data and operations
"""

import os
import pandas as pd
import numpy as np
import json
from typing import Dict, List, Any, Optional, Tuple

class Spreadsheet:
    """
    Represents a spreadsheet with data and operations
    """
    
    def __init__(self, file_id: str, original_filename: str, data_df: Optional[pd.DataFrame] = None, file_path: Optional[str] = None):
        """
        Initialize a spreadsheet

        Args:
            file_id: Unique identifier for the file
            original_filename: Original name of the uploaded file
            data_df: Pandas DataFrame containing the spreadsheet data
            file_path: Path to the spreadsheet file on disk
        """
        self.file_id = file_id
        self.original_filename = original_filename
        self.data_df = data_df
        self.file_path = file_path
        self.metadata = {
            'filename': original_filename,
            'columns': data_df.columns.tolist() if data_df is not None else [],
            'rows': len(data_df) if data_df is not None else 0
        }
    
    def get_data(self) -> Optional[pd.DataFrame]:
        """
        Get spreadsheet data as DataFrame

        Returns:
            Optional[pd.DataFrame]: Spreadsheet data, or None if not loaded
        """
        return self.data_df
    
    def set_data(self, data_df: pd.DataFrame) -> None:
        """
        Update spreadsheet data

        Args:
            data_df: New DataFrame
        """
        self.data_df = data_df
        self.metadata['columns'] = data_df.columns.tolist()
        self.metadata['rows'] = len(data_df)
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get spreadsheet metadata

        Returns:
            Dict[str, Any]: Metadata dict with filename and dimensions
        """
        return self.metadata
    
    def to_json(self, save_to_file: bool = False, file_manager = None) -> dict:
        """
        Convert spreadsheet to JSON format
        
        Args:
            save_to_file: Whether to save the JSON to a file
            file_manager: File manager instance for saving
            
        Returns:
            dict: JSON representation of the spreadsheet
        """
        import json
        import pandas as pd
        
        # Convert DataFrame to dict, handling datetime objects
        if self.data_df is not None:
            df_copy = self.data_df.copy()
            
            # Convert datetime columns to ISO format strings
            for col in df_copy.columns:
                if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
                    df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
            
            # Replace NaN and pd.NA values with None for JSON serialization
            # This is more effective now that object columns aren't preemptively stringified.
            df_dict = df_copy.replace({pd.NA: None, float('nan'): None}).to_dict(orient='records')
            headers = df_copy.columns.tolist()
        else:
            df_dict = []
            headers = []
        
        json_data = {
            'file_id': self.file_id,
            'original_filename': self.original_filename,
            'headers': headers,
            'data': df_dict,
            'metadata': self.get_metadata()
        }
        
        if save_to_file and file_manager:
            file_manager.save_json_data(json_data, f"spreadsheet_{self.file_id}")
            
        return json_data
    
    @classmethod
    def from_json(cls, json_input: Any, file_id: str, original_filename: str) -> 'Spreadsheet':
        """
        Create a spreadsheet from JSON string or dictionary

        Args:
            json_input: JSON string representation or dictionary of spreadsheet
            file_id: Unique identifier for the file
            original_filename: Original filename

        Returns:
            Spreadsheet: New spreadsheet instance
        """
        parsed_json_data: Dict[str, Any]
        if isinstance(json_input, str):
            parsed_json_data = json.loads(json_input)
        elif isinstance(json_input, dict):
            parsed_json_data = json_input
        else:
            raise TypeError("json_input must be a JSON string or a dictionary")

        data_list = parsed_json_data.get('data')
        headers = parsed_json_data.get('headers')

        df: pd.DataFrame
        if data_list is not None:
            if headers is not None:
                # Use headers if provided, for correct column order and handling of empty data lists
                df = pd.DataFrame(data_list, columns=headers)
            else:
                # Let pandas infer columns if headers are not provided
                df = pd.DataFrame(data_list)
        elif headers is not None:
            # No data, but headers are present (e.g., empty spreadsheet with defined columns)
            df = pd.DataFrame(columns=headers)
        else:
            # No data and no headers
            df = pd.DataFrame()
            
        return cls(file_id, original_filename, df)
    
    def save(self, save_dir: str, format: str = 'xlsx') -> str:
        """
        Save spreadsheet to file

        Args:
            save_dir: Directory to save the file to
            format: File format (xlsx, csv)

        Returns:
            str: Path to the saved file
        """
        if self.data_df is None:
            raise ValueError("Cannot save spreadsheet: no data loaded.")
            
        os.makedirs(save_dir, exist_ok=True)
        
        file_path = os.path.join(save_dir, f"{self.file_id}.{format}")
        
        if format == 'xlsx':
            self.data_df.to_excel(file_path, index=False)
        elif format == 'csv':
            self.data_df.to_csv(file_path, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        self.file_path = file_path
        return file_path
