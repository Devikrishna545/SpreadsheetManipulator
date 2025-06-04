"""
File Manager module
----------------
Handles file operations for uploads and downloads
"""

import os
import uuid
from werkzeug.utils import secure_filename
from typing import Optional, Any
from werkzeug.datastructures import FileStorage


class FileManager:
    """
    Manages file operations for the application
    """
    def __init__(self, upload_dir: str = 'uploads', download_dir: str = 'downloads', json_dir: str = 'static/json', max_file_size: int = 16 * 1024 * 1024):
        """
        Initialize the file manager

        Args:
            upload_dir: Directory for uploaded files
            download_dir: Directory for generated download files
            json_dir: Directory for JSON cache files
            max_file_size: Maximum allowed file size in bytes
        """
        self.upload_dir = upload_dir
        self.download_dir = download_dir
        self.json_dir = json_dir
        self.max_file_size = max_file_size
        
        # Create directories if they don't exist
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs(self.json_dir, exist_ok=True)
        
        self.allowed_extensions = {'xlsx', 'xls', 'csv'}
    
    def save_uploaded_file(self, file, file_id: Optional[str] = None) -> str:
        """
        Save an uploaded file to the upload directory

        Args:
            file: The uploaded file object (FileStorage or UploadFile)
            file_id: Optional file ID, generates a new one if not provided

        Returns:
            str: Path to the saved file
        """
        # Check if file is a FastAPI UploadFile or Flask FileStorage
        is_fastapi = hasattr(file, 'file') and not hasattr(file, 'content_length')
        
        # Get filename
        filename = getattr(file, 'filename', None)
        
        # Validate file
        if filename is None or not self.validate_file_type(filename):
            raise ValueError(f"Unsupported file format. Supported formats: {', '.join(self.allowed_extensions)}")
        
        # We skip file size validation for FastAPI since it's hard to get the size without reading the file
        if not is_fastapi and hasattr(file, 'content_length') and file.content_length and file.content_length > self.max_file_size:
            raise ValueError(f"File too large. Maximum size: {self.max_file_size / (1024 * 1024)}MB")
        
        # Secure filename and add unique ID
        if file_id is None:
            file_id = str(uuid.uuid4())
            
        file_ext = os.path.splitext(secure_filename(filename))[1]
        output_filename = f"{file_id}{file_ext}"
        
        # Save file
        file_path = os.path.join(self.upload_dir, output_filename)
        
        if is_fastapi:
            # FastAPI UploadFile - needs special handling
            try:
                # Save the file
                with open(file_path, "wb") as buffer:
                    # Move to the beginning of the file
                    file.file.seek(0)
                    # Write the file
                    buffer.write(file.file.read())
            except Exception as e:
                raise ValueError(f"Failed to save file: {str(e)}")
        else:
            # Flask FileStorage
            try:
                file.save(file_path)
            except Exception as e:
                raise ValueError(f"Failed to save file: {str(e)}")
        
        return file_path
    
    def get_file(self, file_id: str) -> Optional[str]:
        """
        Get a file by ID

        Args:
            file_id: The file ID

        Returns:
            Optional[str]: Path to the file if found, None otherwise
        """
        # Try to find the file with any allowed extension
        for ext in self.allowed_extensions:
            file_path = os.path.join(self.upload_dir, f"{file_id}.{ext}")
            if os.path.exists(file_path):
                return file_path
            
        # Try download directory
        for ext in self.allowed_extensions:
            file_path = os.path.join(self.download_dir, f"{file_id}.{ext}")
            if os.path.exists(file_path):
                return file_path
                
        return None
    
    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file

        Args:
            file_path: Path to the file to delete

        Returns:
            bool: True if the file was deleted, False otherwise
        """
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                return True
            except (PermissionError, OSError) as e:
                print(f"Warning: Could not delete file {file_path}: {e}")
                return False
        
        return False
    
    def validate_file_type(self, filename: str) -> bool:
        """
        Check if a file has an allowed extension

        Args:
            filename: Name of the file to check

        Returns:
            bool: True if the file has an allowed extension
        """
        ext = os.path.splitext(filename)[1].lower()[1:]  # Remove the dot
        return ext in self.allowed_extensions
    
    def save_json_data(self, data: Any, filename: str) -> str:
        """
        Save JSON data to the json directory
        
        Args:
            data: The data to save as JSON
            filename: Name for the JSON file (without .json extension)
            
        Returns:
            str: Path to the saved JSON file
        """
        import json
        from datetime import datetime, date
        
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, (datetime, date)):
                    return o.isoformat()
                return super(DateTimeEncoder, self).default(o)
        
        # Ensure filename has .json extension
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
            
        file_path = os.path.join(self.json_dir, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, cls=DateTimeEncoder)
            
        return file_path
        
    def load_json_data(self, filename: str):
        """
        Load JSON data from the json directory
        
        Args:
            filename: Name of the JSON file (without .json extension)
            
        Returns:
            The loaded JSON data
        """
        import json
        
        # Ensure filename has .json extension
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
            
        file_path = os.path.join(self.json_dir, filename)
        
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def cleanup_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up old files

        Args:
            max_age_hours: Maximum age of files to keep in hours

        Returns:
            int: Number of files deleted
        """
        import time
        
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        deleted_count = 0
        
        # Clean up upload directory
        for root, _, files in os.walk(self.upload_dir):
            for filename in files:
                file_path = os.path.join(root, filename)
                if os.path.isfile(file_path) and now - os.path.getmtime(file_path) > max_age_seconds:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except (PermissionError, OSError) as e:
                        print(f"Warning: Could not delete file {file_path}: {e}")
        
        # Clean up download directory
        for root, _, files in os.walk(self.download_dir):
            for filename in files:
                file_path = os.path.join(root, filename)
                if os.path.isfile(file_path) and now - os.path.getmtime(file_path) > max_age_seconds:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except (PermissionError, OSError) as e:
                        print(f"Warning: Could not delete file {file_path}: {e}")
        
        # Clean up old JSON files (keep some longer)
        for root, _, files in os.walk(self.json_dir):
            for filename in files:
                # Skip manifest.json which should be in the favicon directory
                if filename == 'manifest.json':
                    continue
                    
                file_path = os.path.join(root, filename)
                # Use a longer retention for JSON files (3 days)
                if os.path.isfile(file_path) and now - os.path.getmtime(file_path) > (max_age_seconds * 3):
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except (PermissionError, OSError) as e:
                        print(f"Warning: Could not delete file {file_path}: {e}")
        
        return deleted_count
