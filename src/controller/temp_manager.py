"""Manages temporary files and cleanup operations."""

import os, glob
from typing import List, Optional

class TempManager:
    """Manages temporary files and cleanup operations."""
    
    def __init__(self, temp_dirs: Optional[List[str]] = None):
        """Initialize the temp manager."""
        self.temp_dirs = temp_dirs or [
            os.path.join('static', 'json'),
            os.path.join('static', 'prompts'),
            os.path.join('static', 'downloads'),
            os.path.join('static', 'uploads'),
            os.path.join('src', 'scripts')
        ]
        
        for directory in self.temp_dirs:
            os.makedirs(directory, exist_ok=True)
    
    def cleanup_temp_dirs(self) -> int:
        """Delete all files except .gitkeep from temporary directories."""
        deleted_count = 0
        
        for directory in self.temp_dirs:
            if not os.path.exists(directory):
                continue
                
            for file_path in glob.glob(os.path.join(directory, '*')):
                if os.path.isfile(file_path) and not ((os.path.basename(file_path) == '.gitkeep') or (os.path.basename(file_path) == 'prompts.txt')):
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except Exception as e:
                        print(f"Warning: Could not delete temp file {file_path}: {e}")
        
        return deleted_count
    
    def cleanup_expired_resources(self, session_manager, script_manager, upload_manager, hours: int = 24) -> None:
        """Clean up expired sessions and files."""
        session_manager.cleanup_expired_sessions()
        script_manager.cleanup_old_scripts(hours)
        upload_manager.cleanup_old_uploads(hours)
        self.cleanup_temp_dirs()
