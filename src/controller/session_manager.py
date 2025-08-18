"""
Session Manager
--------------
Manages user sessions and coordinates terminal and security logging
"""

import uuid
from datetime import datetime
from typing import Dict, Optional
from src.controller.terminal_logger import terminal_logger
from src.controller.security_logger import security_logger, SecurityLevel


class SessionManager:
    """
    Manages user sessions and coordinates logging
    """
    
    def __init__(self):
        """Initialize the session manager"""
        self.active_sessions: Dict[str, dict] = {}
    
    def create_session(self, user_ip: str = "unknown", user_agent: str = "unknown") -> str:
        """
        Create a new user session
        
        Args:
            user_ip: User's IP address
            user_agent: User's browser user agent
            
        Returns:
            str: Unique session ID
        """
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Create session data
        session_data = {
            'session_id': session_id,
            'user_ip': user_ip,
            'user_agent': user_agent,
            'start_time': datetime.now().isoformat(),
            'page_views': 0,
            'terminal_commands': 0,
            'security_events': 0
        }
        
        # Store session
        self.active_sessions[session_id] = session_data
        
        # Start logging for both terminal and security
        terminal_logger.start_session(session_id, user_ip, user_agent)
        security_logger.start_session(session_id, user_ip, user_agent)
        
        # Log session creation
        security_logger.log_security_event(
            session_id, 
            SecurityLevel.LOW, 
            "session_management", 
            f"🆕 New user session created",
            {
                'session_id': session_id,
                'user_ip': user_ip,
                'user_agent': user_agent[:100] + '...' if len(user_agent) > 100 else user_agent
            },
            "SessionManager"
        )
        
        return session_id
    
    def log_page_view(self, session_id: str, page_url: str, method: str = "GET"):
        """
        Log a page view for a session
        
        Args:
            session_id: Session identifier
            page_url: URL of the page accessed
            method: HTTP method used
        """
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['page_views'] += 1
            
            # Log as terminal activity
            terminal_logger.log_terminal_output(
                session_id,
                f"🌐 Page Access: {method} {page_url}",
                f"✅ Page loaded successfully\n📊 Total page views this session: {self.active_sessions[session_id]['page_views']}",
                "success"
            )
            
            # Log as low-level security event
            security_logger.log_security_event(
                session_id,
                SecurityLevel.LOW,
                "data_access",
                f"📄 Page accessed: {page_url}",
                {
                    'url': page_url,
                    'method': method,
                    'session_page_views': self.active_sessions[session_id]['page_views']
                },
                "WebServer"
            )
    
    def log_terminal_command(self, session_id: str, command: str, output: str, status: str = "success"):
        """
        Log a terminal command execution
        
        Args:
            session_id: Session identifier
            command: Command executed
            output: Command output
            status: Execution status
        """
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['terminal_commands'] += 1
            
            # Log to terminal logger
            terminal_logger.log_terminal_output(session_id, command, output, status)
            
            # Log as security event if it's a sensitive command
            if self._is_sensitive_command(command):
                level = SecurityLevel.MEDIUM if status == "error" else SecurityLevel.LOW
                security_logger.log_security_event(
                    session_id,
                    level,
                    "system_access",
                    f"💻 Sensitive command executed: {command[:50]}{'...' if len(command) > 50 else ''}",
                    {
                        'command': command,
                        'status': status,
                        'output_preview': output[:200] + '...' if len(output) > 200 else output
                    },
                    "Terminal"
                )
    
    def log_security_event(self, session_id: str, level: SecurityLevel, event_type: str, 
                          message: str, details: Dict = None, source: str = "system"):
        """
        Log a security event
        
        Args:
            session_id: Session identifier
            level: Security level
            event_type: Type of security event
            message: Event message
            details: Additional details
            source: Event source
        """
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['security_events'] += 1
            
            # Log to security logger
            security_logger.log_security_event(session_id, level, event_type, message, details, source)
            
            # Also log high/critical events to terminal for immediate visibility
            if level in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]:
                terminal_logger.log_terminal_output(
                    session_id,
                    f"🚨 SECURITY ALERT: {event_type}",
                    f"⚠️ {level.value} SECURITY EVENT\n📝 {message}\n🔍 Source: {source}",
                    "warning" if level == SecurityLevel.HIGH else "error"
                )
    
    def end_session(self, session_id: str):
        """
        End a user session
        
        Args:
            session_id: Session identifier
        """
        if session_id in self.active_sessions:
            session_data = self.active_sessions[session_id]
            
            # Log session end
            security_logger.log_security_event(
                session_id,
                SecurityLevel.LOW,
                "session_management",
                f"👋 User session ended",
                {
                    'session_duration': str(datetime.now() - datetime.fromisoformat(session_data['start_time'])),
                    'total_page_views': session_data['page_views'],
                    'total_terminal_commands': session_data['terminal_commands'],
                    'total_security_events': session_data['security_events']
                },
                "SessionManager"
            )
            
            # End logging sessions
            terminal_logger.end_session(session_id)
            security_logger.end_session(session_id)
            
            # Remove from active sessions
            del self.active_sessions[session_id]
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """
        Get session information
        
        Args:
            session_id: Session identifier
            
        Returns:
            Optional[Dict]: Session data or None if not found
        """
        return self.active_sessions.get(session_id)
    
    def get_all_sessions(self) -> Dict[str, dict]:
        """
        Get all active sessions
        
        Returns:
            Dict[str, dict]: All active sessions
        """
        return self.active_sessions.copy()
    
    def cleanup_inactive_sessions(self, max_age_hours: int = 24):
        """
        Clean up inactive sessions
        
        Args:
            max_age_hours: Maximum age of sessions in hours
        """
        current_time = datetime.now()
        sessions_to_remove = []
        
        for session_id, session_data in self.active_sessions.items():
            session_start = datetime.fromisoformat(session_data['start_time'])
            age_hours = (current_time - session_start).total_seconds() / 3600
            
            if age_hours > max_age_hours:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            self.end_session(session_id)
    
    def _is_sensitive_command(self, command: str) -> bool:
        """
        Check if a command is considered sensitive
        
        Args:
            command: Command to check
            
        Returns:
            bool: True if command is sensitive
        """
        sensitive_commands = [
            'python', 'pip', 'install', 'uninstall', 'rm', 'del', 'mkdir', 'rmdir',
            'chmod', 'chown', 'sudo', 'su', 'passwd', 'useradd', 'userdel',
            'systemctl', 'service', 'kill', 'killall', 'ps', 'top', 'netstat',
            'wget', 'curl', 'ssh', 'scp', 'ftp', 'telnet'
        ]
        
        command_lower = command.lower().strip()
        return any(sensitive in command_lower for sensitive in sensitive_commands)


# Global session manager instance
session_manager = SessionManager()
