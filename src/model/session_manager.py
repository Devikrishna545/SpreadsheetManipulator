"""
Session Manager module
---------------------
Handles user sessions and manages session data
"""

import uuid
import datetime
from typing import Dict, Optional
import time
import os

from src.model.user_session import UserSession


class SessionManager:
    """
    Manages user sessions for the spreadsheet editor
    """
    
    def __init__(self, session_timeout: int = 3600):
        """
        Initialize the session manager

        Args:
            session_timeout: Session timeout in seconds (default: 1 hour)
        """
        self.sessions: Dict[str, UserSession] = {}
        self.session_timeout = session_timeout
    
    def create_session(self) -> str:
        """
        Create a new user session

        Returns:
            str: Unique session ID
        """
        session_id = str(uuid.uuid4())
        
        # Create new user session
        self.sessions[session_id] = UserSession(session_id)
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[UserSession]:
        """
        Get a user session by ID

        Args:
            session_id: The session ID to look up

        Returns:
            Optional[UserSession]: The user session if found, None otherwise
        """
        session = self.sessions.get(session_id)
        
        if session and session.is_expired(self.session_timeout):
            # Clean up expired session
            self.remove_session(session_id)
            return None
        
        # Update last access time
        if session:
            session.update_last_access_time()
        
        return session
    
    def remove_session(self, session_id: str) -> bool:
        """
        Remove a user session

        Args:
            session_id: The session ID to remove

        Returns:
            bool: True if the session was removed, False otherwise
        """
        if session_id in self.sessions:
            # Clean up resources
            session = self.sessions[session_id]
            
            # Remove session from dict
            del self.sessions[session_id]
            
            return True
        
        return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions

        Returns:
            int: Number of sessions cleaned up
        """
        expired_sessions = []
        
        # Find expired sessions
        for session_id, session in self.sessions.items():
            if session.is_expired(self.session_timeout):
                expired_sessions.append(session_id)
        
        # Remove expired sessions
        for session_id in expired_sessions:
            self.remove_session(session_id)
        
        return len(expired_sessions)
