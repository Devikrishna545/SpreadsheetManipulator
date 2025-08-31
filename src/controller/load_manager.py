"""Manage cleanup of uploaded spreadsheet files."""

import os, time
from typing import Optional

class LoadManager:
    """Manage uploaded files and their cleanup."""
    
    def __init__(self, upload_dir: Optional[str] = None):
        """Initialize with uploads directory (default: static/uploads)."""
        self.upload_dir = upload_dir or os.path.join('static', 'uploads')
        os.makedirs(self.upload_dir, exist_ok=True)
    
    def cleanup_old_uploads(self, max_age_hours: int = 24) -> int:
        """Delete uploads older than max_age_hours; return number deleted."""
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        deleted_count = 0
        
        if not os.path.exists(self.upload_dir):
            return 0
            
        for filename in os.listdir(self.upload_dir):
            if filename == '.gitkeep':
                continue
                
            file_path = os.path.join(self.upload_dir, filename)
            if os.path.isfile(file_path) and now - os.path.getmtime(file_path) > max_age_seconds:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except (PermissionError, OSError) as e:
                    print(f"Warning: Could not delete upload file {file_path}: {e}")
        
        return deleted_count
