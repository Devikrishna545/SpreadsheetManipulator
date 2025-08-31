"""Unified session manager with integrated UserSession functionality and logging coordination."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

class UserSession:
    """Represents a user's editing session with spreadsheet data."""
    
    def __init__(self, session_id: str):
        """Initialize a user session."""
        self.session_id = session_id
        self.spreadsheet = None
        self.modification_history = None
        self.generated_script = None
        self.created_at = datetime.now()
        self.last_accessed_at = self.created_at
    
    def get_spreadsheet(self):
        """Get the current spreadsheet."""
        return self.spreadsheet
    
    def update_spreadsheet(self, spreadsheet) -> None:
        """Update the session's spreadsheet."""
        self.spreadsheet = spreadsheet
        self.update_last_access_time()
    
    def get_modification_history(self):
        """Get the modification history."""
        return self.modification_history
    
    def set_modification_history(self, history) -> None:
        """Set the modification history."""
        self.modification_history = history
    
    def set_generated_script(self, script: str) -> None:
        """Set the LLM-generated script."""
        self.generated_script = script
        self.update_last_access_time()
    
    def get_generated_script(self) -> Optional[str]:
        """Get the LLM-generated script."""
        return self.generated_script
    
    def is_expired(self, timeout_seconds: int) -> bool:
        """Check if this session has expired."""
        time_elapsed = datetime.now() - self.last_accessed_at
        return time_elapsed.total_seconds() > timeout_seconds
    
    def update_last_access_time(self) -> None:
        """Update the last accessed time to now."""
        self.last_accessed_at = datetime.now()

    def add_spreadsheet(self, spreadsheet):
        """Add a spreadsheet to the session."""
        self.update_spreadsheet(spreadsheet)

    def add_prompt_to_history(self, prompt: str):
        """Add a prompt to the session's prompt history."""
        pass  # Implementation would depend on prompt history requirements


from src.controller.terminal_logger import terminal_logger
from src.controller.security_logger import security_logger, SecurityLevel

class SessionManager:
    """Unified session manager for UserSession objects with logging coordination."""
    
    def __init__(self, session_timeout: int = 3600):
        """Initialize the session manager."""
        self.active_sessions: Dict[str, dict] = {}
        self.sessions: Dict[str, UserSession] = {}
        self.session_data: Dict[str, Dict[str, Any]] = {}
        self.session_timeout = session_timeout
    
    def create_session(self, user_ip: str = "unknown", user_agent: str = "unknown") -> str:
        """Create a new user session with UserSession object and logging."""
        session_id = str(uuid.uuid4())
        
        self.sessions[session_id] = UserSession(session_id)
        
        session_data = {
            'session_id': session_id,
            'user_ip': user_ip,
            'user_agent': user_agent,
            'start_time': datetime.now().isoformat(),
            'page_views': 0,
            'terminal_commands': 0,
            'security_events': 0
        }
        
        self.active_sessions[session_id] = session_data
        
        terminal_logger.start_session(session_id, user_ip, user_agent)
        security_logger.start_session(session_id, user_ip, user_agent)
        
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
        """Log a page view for a session."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['page_views'] += 1
            
            terminal_logger.log_terminal_output(
                session_id,
                f"🌐 Page Access: {method} {page_url}",
                f"✅ Page loaded successfully\n📊 Total page views this session: {self.active_sessions[session_id]['page_views']}",
                "success"
            )
            
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
        """Log a terminal command execution."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['terminal_commands'] += 1
            
            terminal_logger.log_terminal_output(session_id, command, output, status)
            
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
        """Log a security event."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]['security_events'] += 1
            
            security_logger.log_security_event(session_id, level, event_type, message, details, source)
            
            if level in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]:
                terminal_logger.log_terminal_output(
                    session_id,
                    f"🚨 SECURITY ALERT: {event_type}",
                    f"⚠️ {level.value} SECURITY EVENT\n📝 {message}\n🔍 Source: {source}",
                    "warning" if level == SecurityLevel.HIGH else "error"
                )
    
    def end_session(self, session_id: str):
        """End a user session and clean up all associated data."""
        if session_id in self.active_sessions:
            session_data = self.active_sessions[session_id]
            
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
            
            terminal_logger.end_session(session_id)
            security_logger.end_session(session_id)
            
            del self.active_sessions[session_id]
        
        if session_id in self.sessions:
            del self.sessions[session_id]
        if session_id in self.session_data:
            del self.session_data[session_id]

    def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get a UserSession by ID, or None if not found/expired."""
        session = self.sessions.get(session_id)
        
        if session and session.is_expired(self.session_timeout):
            self.remove_session(session_id)
            return None
        
        if session:
            session.update_last_access_time()
        
        return session

    def session_exists(self, session_id: str) -> bool:
        """Return True if a session with the given ID exists."""
        return session_id in self.sessions

    def update_session_data(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Store additional data for a session; return True if updated."""
        if not self.session_exists(session_id):
            return False
            
        if session_id not in self.session_data:
            self.session_data[session_id] = {}
            
        self.session_data[session_id].update(data)
        return True

    def get_session_data(self, session_id: str) -> Dict[str, Any]:
        """Return stored data for a session, or an empty dict if none exists."""
        if not self.session_exists(session_id):
            return {}
            
        return self.session_data.get(session_id, {})

    def remove_session(self, session_id: str) -> bool:
        """Remove a user session and any associated data."""
        removed = False
        
        if session_id in self.sessions:
            del self.sessions[session_id]
            removed = True
            
        if session_id in self.session_data:
            del self.session_data[session_id]
            
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            
        return removed

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions and return the number removed."""
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if session.is_expired(self.session_timeout):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.remove_session(session_id)
        
        return len(expired_sessions)
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get session information."""
        return self.active_sessions.get(session_id)
    
    def get_all_sessions(self) -> Dict[str, dict]:
        """Get all active sessions."""
        return self.active_sessions.copy()
    
    def cleanup_inactive_sessions(self, max_age_hours: int = 24):
        """Clean up inactive sessions and expired UserSessions."""
        current_time = datetime.now()
        sessions_to_remove = []
        
        for session_id, session_data in self.active_sessions.items():
            session_start = datetime.fromisoformat(session_data['start_time'])
            age_hours = (current_time - session_start).total_seconds() / 3600
            
            if age_hours > max_age_hours:
                sessions_to_remove.append(session_id)
        
        for session_id, user_session in list(self.sessions.items()):
            if user_session.is_expired(self.session_timeout):
                sessions_to_remove.append(session_id)
        
        for session_id in set(sessions_to_remove):
            if session_id in self.active_sessions:
                self.end_session(session_id)
            else:
                self.remove_session(session_id)
    
    def _is_sensitive_command(self, command: str) -> bool:
        """Check if a command is considered sensitive."""
        sensitive_commands = [
            'python', 'pip', 'install', 'uninstall', 'rm', 'del', 'mkdir', 'rmdir',
            'chmod', 'chown', 'sudo', 'su', 'passwd', 'useradd', 'userdel',
            'systemctl', 'service', 'kill', 'killall', 'ps', 'top', 'netstat',
            'wget', 'curl', 'ssh', 'scp', 'ftp', 'telnet'
        ]
        
        command_lower = command.lower().strip()
        return any(sensitive in command_lower for sensitive in sensitive_commands)


session_manager = SessionManager()
