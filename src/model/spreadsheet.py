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
    
    def to_json(self, save_to_file: bool = False, file_manager = None) -> str:
        """
        Convert spreadsheet to JSON string

        Args:
            save_to_file: Whether to save the JSON to a file in static/json
            file_manager: FileManager instance to use for saving (if save_to_file is True)

        Returns:
            str: JSON representation of spreadsheet
        """
        if self.data_df is not None:
            # Handle NaN values and other non-serializable types
            df_json = self.data_df.replace({np.nan: None}).to_dict(orient='records')
            headers = self.data_df.columns.tolist()
        else:
            df_json = []
            headers = []
        
        data = {
            'metadata': self.metadata,
            'data': df_json,
            'headers': headers
        }
        
        json_str = json.dumps(data)
        
        # Save to file if requested
        if save_to_file and file_manager is not None:
            file_manager.save_json_data(data, f"spreadsheet_{self.file_id}")
        
        return json_str
    
    @classmethod
    def from_json(cls, json_str: str, file_id: str, original_filename: str) -> 'Spreadsheet':
        """
        Create a spreadsheet from JSON string

        Args:
            json_str: JSON string representation of spreadsheet
            file_id: Unique identifier for the file
            original_filename: Original filename

        Returns:
            Spreadsheet: New spreadsheet instance
        """
        data = json.loads(json_str)
        df = pd.DataFrame(data['data'])
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
