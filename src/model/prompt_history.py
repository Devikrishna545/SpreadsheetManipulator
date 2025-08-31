"""Handles storing and retrieving prompt history for a session."""

import os, threading
from datetime import datetime

class PromptHistory:
    """Handles storing and retrieving prompt history for a session."""
    def __init__(self, folder, suffix="_prompts.txt"):
        self.folder = folder
        self.suffix = suffix
        self.lock = threading.Lock()
        os.makedirs(self.folder, exist_ok=True)

    def _get_path(self, session_id):
        """Generate timestamped filename: DDMMYYYYHHMMSS_<session_id>_prompts.txt"""
        ts = datetime.now().strftime("%d%m%Y%H%M%S")
        return os.path.join(self.folder, f"{ts}_{session_id}{self.suffix}")

    def append(self, session_id, prompt):
        """Append a prompt to the history for a specific session."""
        with self.lock:
            prefix = f"_{session_id}{self.suffix}"
            candidates = [fn for fn in os.listdir(self.folder) if fn.endswith(prefix)]
            
            if candidates:
                candidates.sort()
                path = os.path.join(self.folder, candidates[-1])
            else:
                path = self._get_path(session_id)
            
            with open(path, "a", encoding="utf-8") as f:
                f.write(prompt.replace('\n', ' ') + "\n")

    def get(self, session_id, index):
        """Retrieve a prompt from the history for a specific session."""
        with self.lock:
            prefix = f"_{session_id}{self.suffix}"
            candidates = [fn for fn in os.listdir(self.folder) if fn.endswith(prefix)]
            
            if not candidates:
                return None
            
            candidates.sort()
            path = os.path.join(self.folder, candidates[-1])
            
            with open(path, "r", encoding="utf-8") as f:
                lines = [line.rstrip('\n') for line in f if line.strip()]
        
        if not lines or index < 0 or index >= len(lines):
            return None
            
        return lines[-(index+1)]
