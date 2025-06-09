"""
Session Manager module
---------------------
Handles user sessions and manages session data
"""

import uuid
import datetime
from typing import Dict, Optional, Any
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
        self.session_data: Dict[str, Dict[str, Any]] = {}  # Store additional data for sessions
    
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
    
    def session_exists(self, session_id: str) -> bool:
        """
        Check if a session with the given ID exists
        
        Args:
            session_id: The session ID to check
            
        Returns:
            bool: True if the session exists, False otherwise
        """
        return session_id in self.sessions
    
    def update_session_data(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Store additional data for a session
        
        Args:
            session_id: The session ID to update
            data: Dictionary containing data to store
            
        Returns:
            bool: True if the data was updated, False if session doesn't exist
        """
        if not self.session_exists(session_id):
            return False
            
        # Initialize data dictionary for this session if it doesn't exist
        if session_id not in self.session_data:
            self.session_data[session_id] = {}
            
        # Update with new data
        self.session_data[session_id].update(data)
        return True
    
    def get_session_data(self, session_id: str) -> Dict[str, Any]:
        """
        Retrieve additional data stored for a session
        
        Args:
            session_id: The session ID to retrieve data for
            
        Returns:
            Dict[str, Any]: The stored data, or empty dict if none exists
        """
        if not self.session_exists(session_id):
            return {}
            
        return self.session_data.get(session_id, {})
    
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
            
            # Remove session data if exists
            if session_id in self.session_data:
                del self.session_data[session_id]
            
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
