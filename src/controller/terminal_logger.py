"""
Terminal Session Logger
----------------------
Logs all terminal output for each user session with metadata
"""

import os
import logging
from datetime import datetime
from typing import Dict, Optional
import json


class TerminalSessionLogger:
    """
    Manages terminal logging for user sessions
    """
    
    def __init__(self, log_directory: str = "src/logs/terminal"):
        """
        Initialize the terminal session logger
        
        Args:
            log_directory: Directory to store terminal logs
        """
        self.log_directory = log_directory
        self.active_sessions: Dict[str, dict] = {}
        
        # Ensure log directory exists
        os.makedirs(log_directory, exist_ok=True)
    
    def start_session(self, session_id: str, user_ip: str = "unknown", user_agent: str = "unknown") -> str:
        """
        Start a new terminal logging session
        
        Args:
            session_id: Unique session identifier
            user_ip: User's IP address
            user_agent: User's browser agent
            
        Returns:
            str: Log file path for this session
        """
        # Generate timestamp-based filename (DDMMYYYYHHMMSS)
        now = datetime.now()
        timestamp = now.strftime("%d%m%Y%H%M%S")
        filename = f"{timestamp}.txt"
        filepath = os.path.join(self.log_directory, filename)
        
        # Session metadata
        session_data = {
            'session_id': session_id,
            'start_time': now.isoformat(),
            'user_ip': user_ip,
            'user_agent': user_agent,
            'log_file': filepath,
            'command_count': 0
        }
        
        # Store session info
        self.active_sessions[session_id] = session_data
        
        # Create log file with metadata header
        self._write_session_header(filepath, session_data)
        
        return filepath
    
    def log_terminal_output(self, session_id: str, command: str, output: str, status: str = "success"):
        """
        Log terminal command and output for a session
        
        Args:
            session_id: Session identifier
            command: The command that was executed
            output: The terminal output
            status: Command status (success, error, warning)
        """
        if session_id not in self.active_sessions:
            # Auto-start session if not exists
            self.start_session(session_id)
        
        session = self.active_sessions[session_id]
        session['command_count'] += 1
        
        # Prepare log entry
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status_emoji = self._get_status_emoji(status)
        
        log_entry = f"""
{'-' * 60}
🕒 [{timestamp}] Command #{session['command_count']} {status_emoji}
💻 Command: {command}
📤 Output:
{output}
{'-' * 60}
"""
        
        # Append to session log file
        try:
            with open(session['log_file'], 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            logging.error(f"Failed to write terminal log: {e}")
    
    def end_session(self, session_id: str):
        """
        End a terminal logging session
        
        Args:
            session_id: Session identifier
        """
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            
            # Write session footer
            end_time = datetime.now()
            session['end_time'] = end_time.isoformat()
            
            footer = f"""

{'=' * 60}
🏁 SESSION ENDED
{'=' * 60}
📊 Session Summary:
   • Session ID: {session_id}
   • Total Commands: {session['command_count']}
   • Started: {session['start_time']}
   • Ended: {session['end_time']}
   • Duration: {end_time - datetime.fromisoformat(session['start_time'])}
   • User IP: {session['user_ip']}
{'=' * 60}
"""
            
            try:
                with open(session['log_file'], 'a', encoding='utf-8') as f:
                    f.write(footer)
            except Exception as e:
                logging.error(f"Failed to write session footer: {e}")
            
            # Remove from active sessions
            del self.active_sessions[session_id]
    
    def _write_session_header(self, filepath: str, session_data: dict):
        """
        Write session metadata header to log file
        
        Args:
            filepath: Path to log file
            session_data: Session metadata
        """
        header = f"""{'=' * 60}
🖥️  TERMINAL SESSION LOG
{'=' * 60}
📋 Session Metadata:
   • Session ID: {session_data['session_id']}
   • Created: {session_data['start_time']}
   • User IP: {session_data['user_ip']}
   • User Agent: {session_data['user_agent']}
   • Log File: {session_data['log_file']}
{'=' * 60}
🚀 SESSION STARTED - All terminal activity will be logged below
{'=' * 60}

"""
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(header)
        except Exception as e:
            logging.error(f"Failed to create terminal log file: {e}")
    
    def _get_status_emoji(self, status: str) -> str:
        """
        Get emoji for command status
        
        Args:
            status: Command status
            
        Returns:
            str: Appropriate emoji
        """
        emoji_map = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️',
            'running': '🔄'
        }
        return emoji_map.get(status.lower(), '📝')
    
    def get_active_sessions(self) -> Dict[str, dict]:
        """
        Get all active sessions
        
        Returns:
            Dict[str, dict]: Active sessions data
        """
        return self.active_sessions.copy()
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """
        Clean up old log files
        
        Args:
            days_to_keep: Number of days to keep logs
        """
        try:
            cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
            
            for filename in os.listdir(self.log_directory):
                filepath = os.path.join(self.log_directory, filename)
                
                if os.path.isfile(filepath):
                    file_time = os.path.getmtime(filepath)
                    if file_time < cutoff_time:
                        os.remove(filepath)
                        logging.info(f"Cleaned up old terminal log: {filename}")
                        
        except Exception as e:
            logging.error(f"Failed to cleanup old terminal logs: {e}")


# Global terminal logger instance
terminal_logger = TerminalSessionLogger()
