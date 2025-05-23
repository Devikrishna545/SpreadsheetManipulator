"""
Spreadsheet Parser module
-----------------------
Handles parsing of spreadsheet files into suitable formats
"""

import os
import pandas as pd
from typing import Union, Dict, Any, Tuple


class SpreadsheetParser:
    """
    Handles parsing of spreadsheet files
    """
    
    @staticmethod
    def parse_to_json(file_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse a spreadsheet file to JSON

        Args:
            file_path: Path to the spreadsheet file

        Returns:
            Tuple[str, Dict]: JSON representation and metadata
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Read file based on extension
        if file_ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        elif file_ext == '.csv':
            df = pd.read_csv(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        # Convert to JSON
        data = df.to_json(orient='records')
        
        # Prepare metadata
        metadata = {
            'columns': df.columns.tolist(),
            'rows': len(df),
            'file_type': file_ext[1:]  # Remove the dot
        }
        
        return data, metadata
    
    @staticmethod
    def detect_file_format(file_path: str) -> str:
        """
        Detect the format of a spreadsheet file

        Args:
            file_path: Path to the spreadsheet file

        Returns:
            str: Detected format (excel, csv)
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext in ['.xlsx', '.xls']:
            return 'excel'
        elif file_ext == '.csv':
            return 'csv'
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
    
    @staticmethod
    def parse_from_pandas(df: pd.DataFrame) -> str:
        """
        Convert a pandas DataFrame to JSON string

        Args:
            df: Pandas DataFrame

        Returns:
            str: JSON representation of the DataFrame
        """
        return df.to_json(orient='records')
