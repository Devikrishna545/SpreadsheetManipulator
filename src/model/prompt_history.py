import os
import threading

class PromptHistory:
    """
    Handles storing and retrieving prompt history for a session.
    """
    def __init__(self, folder, suffix="_prompts.txt"):
        self.folder = folder
        self.suffix = suffix
        self.lock = threading.Lock()
        os.makedirs(self.folder, exist_ok=True)

    def _get_path(self, session_id):
        return os.path.join(self.folder, f"{session_id}{self.suffix}")

    def append(self, session_id, prompt):
        path = self._get_path(session_id)
        with self.lock:
            with open(path, "a", encoding="utf-8") as f:
                f.write(prompt.replace('\n', ' ') + "\n")

    def get(self, session_id, index):
        path = self._get_path(session_id)
        if not os.path.exists(path):
            return None
        with self.lock:
            with open(path, "r", encoding="utf-8") as f:
                lines = [line.rstrip('\n') for line in f if line.strip()]
        if not lines:
            return None
        if index < 0 or index >= len(lines):
            return None
        return lines[-(index+1)]
