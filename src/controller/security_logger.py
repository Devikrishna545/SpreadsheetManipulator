"""Security session logger for categorized events per user session."""

import os, logging
from enum import Enum
from typing import Any, Dict
from datetime import datetime

class SecurityLevel(Enum):
    """Security event severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class SecuritySessionLogger:
    """Manage security logging for user sessions with emoji-enhanced output."""
    
    def __init__(self, log_directory: str = "src/logs/security"):
        """Initialize the security session logger and ensure log directory exists."""
        self.log_directory = log_directory
        self.active_sessions: Dict[str, dict] = {}
        os.makedirs(log_directory, exist_ok=True)
        self.level_config = {
            SecurityLevel.LOW: {
                'emoji': '🟢',
                'section_emoji': '🔒',
                'header': 'LOW SECURITY EVENTS'
            },
            SecurityLevel.MEDIUM: {
                'emoji': '🟡',
                'section_emoji': '🚨',
                'header': 'MEDIUM SECURITY EVENTS'
            },
            SecurityLevel.HIGH: {
                'emoji': '🟠',
                'section_emoji': '⚠️',
                'header': 'HIGH SECURITY EVENTS'
            },
            SecurityLevel.CRITICAL: {
                'emoji': '🔴',
                'section_emoji': '🚫',
                'header': 'CRITICAL SECURITY EVENTS'
            }
        }
    
    def start_session(self, session_id: str, user_ip: str = "unknown", user_agent: str = "unknown") -> str:
        """Start a new security logging session and return the log file path."""
        now = datetime.now()
        timestamp = now.strftime("%d%m%Y%H%M%S")
        filename = f"{timestamp}.txt"
        filepath = os.path.join(self.log_directory, filename)
        
        session_data = {
            'session_id': session_id,
            'start_time': now.isoformat(),
            'user_ip': user_ip,
            'user_agent': user_agent,
            'log_file': filepath,
            'events': {level.value: [] for level in SecurityLevel},
            'event_count': 0
        }
        
        self.active_sessions[session_id] = session_data
        self._write_session_header(filepath, session_data)
        
        return filepath
    
    def log_security_event(self, session_id: str, level: SecurityLevel, event_type: str,
                           message: str, details: Dict[str, Any] | None = None, source: str = "system") -> None:
        """Log a security event for a session."""
        if session_id not in self.active_sessions:
            self.start_session(session_id)
        
        session = self.active_sessions[session_id]
        session['event_count'] += 1
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        event_emoji = self._get_event_emoji(event_type)
        level_emoji = self.level_config[level]['emoji']
        
        event_data = {
            'timestamp': timestamp,
            'event_id': session['event_count'],
            'level': level.value,
            'type': event_type,
            'message': message,
            'details': details or {},
            'source': source
        }
        
        session['events'][level.value].append(event_data)
        
        log_entry = f"""
{level_emoji} [{timestamp}] Event #{session['event_count']} | {level.value} | {source}
{event_emoji} {event_type.upper()}: {message}
"""
        
        if details:
            log_entry += "📋 Details:\n"
            for key, value in details.items():
                log_entry += f"   • {key}: {value}\n"
        
        log_entry += f"{'─' * 50}\n"
        
        try:
            with open(session['log_file'], 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            logging.error(f"Failed to write security log: {e}")
    
    def log_script_validation(self, session_id: str, script: str, is_safe: bool, reason: str) -> None:
        """Log the result of a script validation."""
        level = SecurityLevel.LOW if is_safe else SecurityLevel.HIGH
        event_type = "script_validation"
        message = f"Script validation {'✅ PASSED' if is_safe else '❌ FAILED'}: {reason}"
        
        details = {
            'script_preview': script[:100] + '...' if len(script) > 100 else script,
            'script_length': len(script),
            'validation_result': 'SAFE' if is_safe else 'UNSAFE',
            'reason': reason
        }
        
        self.log_security_event(session_id, level, event_type, message, details, "SecurityManager")
    
    def log_file_upload(self, session_id: str, filename: str, file_size: int,
                        file_type: str, is_allowed: bool, reason: str = "") -> None:
        """Log a file upload security event."""
        level = SecurityLevel.LOW if is_allowed else SecurityLevel.MEDIUM
        event_type = "file_upload"
        status = "✅ ALLOWED" if is_allowed else "🚫 BLOCKED"
        message = f"File upload {status}: {filename}"
        
        details = {
            'filename': filename,
            'file_size_bytes': file_size,
            'file_size_mb': round(file_size / (1024 * 1024), 2),
            'file_type': file_type,
            'status': 'ALLOWED' if is_allowed else 'BLOCKED',
            'reason': reason
        }
        
        self.log_security_event(session_id, level, event_type, message, details, "FileValidator")
    
    def log_rate_limit_event(self, session_id: str, user_ip: str, endpoint: str,
                             is_blocked: bool, request_count: int, limit: int) -> None:
        """Log a rate limiting check event."""
        level = SecurityLevel.MEDIUM if is_blocked else SecurityLevel.LOW
        event_type = "rate_limiting"
        status = "🚫 BLOCKED" if is_blocked else "✅ ALLOWED"
        message = f"Rate limit check {status} for {endpoint}"
        
        details = {
            'user_ip': user_ip,
            'endpoint': endpoint,
            'request_count': request_count,
            'rate_limit': limit,
            'utilization_percent': round((request_count / limit) * 100, 1),
            'status': 'BLOCKED' if is_blocked else 'ALLOWED'
        }
        
        self.log_security_event(session_id, level, event_type, message, details, "RateLimiter")
    
    def end_session(self, session_id: str) -> None:
        """End a security logging session and write summary."""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            
            end_time = datetime.now()
            session['end_time'] = end_time.isoformat()
            
            self._write_session_summary(session, end_time)
            
            del self.active_sessions[session_id]
    
    def _write_session_header(self, filepath: str, session_data: dict) -> None:
        """Write session metadata header to the log file."""
        header = f"""{'🛡️' * 20}
🔐 SECURITY SESSION LOG
{'🛡️' * 20}

📋 Session Metadata:
{'=' * 50}
🆔 Session ID: {session_data['session_id']}
🕒 Created: {session_data['start_time']}
🌐 User IP: {session_data['user_ip']}
🖥️ User Agent: {session_data['user_agent']}
📁 Log File: {session_data['log_file']}
{'=' * 50}

🚀 SECURITY MONITORING STARTED
{'=' * 50}

"""
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(header)
        except Exception as e:
            logging.error(f"Failed to create security log file: {e}")
    
    def _write_session_summary(self, session: dict, end_time: datetime) -> None:
        """Write session summary with categorized events."""
        summary = f"""

{'🏁' * 20}
🔚 SESSION SUMMARY
{'🏁' * 20}

📊 Overall Statistics:
{'=' * 50}
🆔 Session ID: {session['session_id']}
⏰ Duration: {end_time - datetime.fromisoformat(session['start_time'])}
📈 Total Events: {session['event_count']}
🌐 User IP: {session['user_ip']}
{'=' * 50}

"""
        
        for level in SecurityLevel:
            events = session['events'][level.value]
            config = self.level_config[level]
            
            if events:
                summary += f"""
{config['section_emoji']} {config['header']} ({len(events)} events)
{'─' * 50}
"""
                for event in events[-5:]:  # last 5 events of each level
                    summary += f"{config['emoji']} [{event['timestamp']}] {event['type']}: {event['message']}\n"
                
                if len(events) > 5:
                    summary += f"   ... and {len(events) - 5} more {level.value} events\n"
                summary += "\n"
        
        summary += f"""
{'🛡️' * 20}
END OF SECURITY LOG
{'🛡️' * 20}
"""
        
        try:
            with open(session['log_file'], 'a', encoding='utf-8') as f:
                f.write(summary)
        except Exception as e:
            logging.error(f"Failed to write security summary: {e}")
    
    def _get_event_emoji(self, event_type: str) -> str:
        """Get an emoji representing a given security event type."""
        emoji_map = {
            'script_validation': '🔍',
            'file_upload': '📤',
            'rate_limiting': '⏱️',
            'authentication': '🔑',
            'authorization': '🚪',
            'data_access': '📊',
            'system_access': '🖥️',
            'network_security': '🌐',
            'input_validation': '✏️',
            'session_management': '👤',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        }
        return emoji_map.get(event_type.lower(), '🔒')
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get high-level statistics for a session."""
        if session_id not in self.active_sessions:
            return {}
        
        session = self.active_sessions[session_id]
        stats = {
            'session_id': session_id,
            'total_events': session['event_count'],
            'events_by_level': {level.value: len(session['events'][level.value]) for level in SecurityLevel},
            'start_time': session['start_time'],
            'user_ip': session['user_ip']
        }
        
        return stats
    
    def cleanup_old_logs(self, days_to_keep: int = 30) -> None:
        """Remove security log files older than the provided number of days."""
        try:
            cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
            
            for filename in os.listdir(self.log_directory):
                filepath = os.path.join(self.log_directory, filename)
                
                if os.path.isfile(filepath):
                    file_time = os.path.getmtime(filepath)
                    if file_time < cutoff_time:
                        os.remove(filepath)
                        logging.info(f"Cleaned up old security log: {filename}")
                        
        except Exception as e:
            logging.error(f"Failed to cleanup old security logs: {e}")


# Global security logger instance
security_logger = SecuritySessionLogger()
