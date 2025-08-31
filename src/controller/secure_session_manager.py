"""Secure session manager with encryption, validation, and abuse protection."""

from cryptography.fernet import Fernet
import json, logging, os, secrets, time, hashlib
from typing import Any, Dict, List, Optional, Set

session_logger = logging.getLogger("session_security")

class SecureSessionManager:
    """Enhanced session manager with comprehensive security features."""
    
    def __init__(self, session_timeout: int = 3600, max_sessions_per_ip: int = 10):
        """Initialize the secure session manager."""
        self.session_timeout = session_timeout
        self.max_sessions_per_ip = max_sessions_per_ip
        
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.ip_sessions: Dict[str, Set[str]] = {}
        
        self.failed_attempts: Dict[str, Dict[str, Any]] = {}
        self.max_failed_attempts = 5
        self.lockout_duration = 300  # 5 minutes
        
        self.encryption_key = self._generate_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        self.secure_random = secrets.SystemRandom()
        
        self.suspicious_activities: Dict[str, List[Dict[str, Any]]] = {}

    def _generate_encryption_key(self) -> bytes:
        """Generate or load encryption key for session data."""
        key_file = "session_key.key"
        
        if os.path.exists(key_file):
            try:
                with open(key_file, 'rb') as f:
                    return f.read()
            except Exception as e:
                session_logger.warning(f"Could not load existing key: {e}")
        
        key = Fernet.generate_key()
        
        try:
            with open(key_file, 'wb') as f:
                f.write(key)
            os.chmod(key_file, 0o600)
        except Exception as e:
            session_logger.warning(f"Could not save encryption key: {e}")
        
        return key

    def create_session(self, client_ip: str, user_agent: str = "", additional_data: Dict = None) -> str:
        """Create a new secure session and return the session ID."""
        if self._is_ip_locked_out(client_ip):
            session_logger.warning(f"Session creation attempted from locked out IP: {client_ip}")
            raise SecurityError("IP address is temporarily locked out", "IP_LOCKOUT", client_ip)
        
        if client_ip in self.ip_sessions and len(self.ip_sessions[client_ip]) >= self.max_sessions_per_ip:
            session_logger.warning(f"Too many sessions for IP: {client_ip}")
            self._cleanup_expired_sessions()
            
            if client_ip in self.ip_sessions and len(self.ip_sessions[client_ip]) >= self.max_sessions_per_ip:
                raise SecurityError("Too many active sessions", "SESSION_LIMIT", client_ip)
        
        session_id = self._generate_secure_session_id()
        
        session_data = {
            'id': session_id,
            'created_at': time.time(),
            'last_accessed': time.time(),
            'client_ip': client_ip,
            'user_agent': user_agent,
            'is_active': True,
            'request_count': 0,
            'data': additional_data or {},
            'security_flags': {
                'suspicious_activity': False,
                'rate_limited': False,
                'last_validation': time.time()
            }
        }
        
        encrypted_data = self._encrypt_session_data(session_data)
        
        self.sessions[session_id] = encrypted_data
        
        if client_ip not in self.ip_sessions:
            self.ip_sessions[client_ip] = set()
        self.ip_sessions[client_ip].add(session_id)
        
        session_logger.info(f"New session created: {session_id[:8]}... for IP: {client_ip}")
        
        return session_id

    def validate_session(self, session_id: str, client_ip: str, user_agent: str = "") -> bool:
        """Validate and update session; return True if valid, else False."""
        if not session_id or session_id not in self.sessions:
            self._record_failed_attempt(client_ip, "invalid_session_id")
            return False
        
        try:
            session_data = self._decrypt_session_data(self.sessions[session_id])
            
            if time.time() - session_data['last_accessed'] > self.session_timeout:
                session_logger.info(f"Session expired: {session_id[:8]}...")
                self.destroy_session(session_id)
                return False
            
            if session_data['client_ip'] != client_ip:
                session_logger.warning(f"IP mismatch for session {session_id[:8]}...: {session_data['client_ip']} vs {client_ip}")
                self._record_suspicious_activity(client_ip, "ip_mismatch", session_id)
                self.destroy_session(session_id)
                return False
            
            if user_agent and session_data['user_agent'] != user_agent:
                session_logger.warning(f"User agent change for session {session_id[:8]}...")
                self._record_suspicious_activity(client_ip, "user_agent_change", session_id)
            
            session_data['last_accessed'] = time.time()
            session_data['request_count'] += 1
            session_data['security_flags']['last_validation'] = time.time()
            
            if self._detect_suspicious_pattern(session_data):
                session_data['security_flags']['suspicious_activity'] = True
                self._record_suspicious_activity(client_ip, "suspicious_pattern", session_id)
            
            self.sessions[session_id] = self._encrypt_session_data(session_data)
            
            return True
            
        except Exception as e:
            session_logger.error(f"Session validation error: {e}")
            self._record_failed_attempt(client_ip, "validation_error")
            return False

    def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data payload or None if not found."""
        if session_id not in self.sessions:
            return None
        
        try:
            session_data = self._decrypt_session_data(self.sessions[session_id])
            return session_data.get('data', {})
        except Exception as e:
            session_logger.error(f"Error retrieving session data: {e}")
            return None

    def update_session_data(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Update session data; return True on success."""
        if session_id not in self.sessions:
            return False
        
        try:
            session_data = self._decrypt_session_data(self.sessions[session_id])
            session_data['data'].update(data)
            session_data['last_accessed'] = time.time()
            
            self.sessions[session_id] = self._encrypt_session_data(session_data)
            return True
        except Exception as e:
            session_logger.error(f"Error updating session data: {e}")
            return False

    def destroy_session(self, session_id: str) -> bool:
        """Destroy a session; return True on success."""
        if session_id not in self.sessions:
            return False
        
        try:
            session_data = self._decrypt_session_data(self.sessions[session_id])
            client_ip = session_data['client_ip']
            
            del self.sessions[session_id]
            
            if client_ip in self.ip_sessions:
                self.ip_sessions[client_ip].discard(session_id)
                if not self.ip_sessions[client_ip]:
                    del self.ip_sessions[client_ip]
            
            session_logger.info(f"Session destroyed: {session_id[:8]}...")
            return True
            
        except Exception as e:
            session_logger.error(f"Error destroying session: {e}")
            return False

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions and return number cleaned up."""
        return self._cleanup_expired_sessions()

    def _cleanup_expired_sessions(self) -> int:
        """Internal method to clean up expired sessions."""
        current_time = time.time()
        expired_sessions = []
        
        for session_id in list(self.sessions.keys()):
            try:
                session_data = self._decrypt_session_data(self.sessions[session_id])
                if current_time - session_data['last_accessed'] > self.session_timeout:
                    expired_sessions.append(session_id)
            except Exception:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.destroy_session(session_id)
        
        if expired_sessions:
            session_logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        
        return len(expired_sessions)

    def _generate_secure_session_id(self) -> str:
        """Generate a cryptographically secure session ID."""
        random_bytes = secrets.token_bytes(32)
        
        timestamp = str(time.time()).encode()
        
        hasher = hashlib.sha256()
        hasher.update(random_bytes)
        hasher.update(timestamp)
        
        return hasher.hexdigest()

    def _encrypt_session_data(self, data: Dict[str, Any]) -> bytes:
        """Encrypt session data."""
        json_data = json.dumps(data, default=str)
        return self.cipher_suite.encrypt(json_data.encode())

    def _decrypt_session_data(self, encrypted_data: bytes) -> Dict[str, Any]:
        """Decrypt session data."""
        decrypted_data = self.cipher_suite.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode())

    def _is_ip_locked_out(self, client_ip: str) -> bool:
        """Check if IP is locked out due to failed attempts."""
        if client_ip not in self.failed_attempts:
            return False
        
        attempt_data = self.failed_attempts[client_ip]
        
        if time.time() - attempt_data.get('locked_at', 0) > self.lockout_duration:
            del self.failed_attempts[client_ip]
            return False
        
        return attempt_data.get('locked', False)

    def _record_failed_attempt(self, client_ip: str, reason: str):
        """Record a failed attempt for an IP."""
        if client_ip not in self.failed_attempts:
            self.failed_attempts[client_ip] = {
                'count': 0,
                'first_attempt': time.time(),
                'locked': False
            }
        
        attempt_data = self.failed_attempts[client_ip]
        attempt_data['count'] += 1
        attempt_data['last_attempt'] = time.time()
        attempt_data['last_reason'] = reason
        
        if attempt_data['count'] >= self.max_failed_attempts:
            attempt_data['locked'] = True
            attempt_data['locked_at'] = time.time()
            session_logger.warning(f"IP locked out due to failed attempts: {client_ip}")

    def _record_suspicious_activity(self, client_ip: str, activity_type: str, session_id: str = None):
        """Record suspicious activity."""
        if client_ip not in self.suspicious_activities:
            self.suspicious_activities[client_ip] = []
        
        activity = {
            'timestamp': time.time(),
            'type': activity_type,
            'session_id': session_id
        }
        
        self.suspicious_activities[client_ip].append(activity)
        
        hour_ago = time.time() - 3600
        self.suspicious_activities[client_ip] = [
            act for act in self.suspicious_activities[client_ip]
            if act['timestamp'] > hour_ago
        ]
        
        session_logger.warning(f"Suspicious activity recorded: {activity_type} from {client_ip}")

    def _detect_suspicious_pattern(self, session_data: Dict[str, Any]) -> bool:
        """Detect suspicious patterns in session usage."""
        session_duration = time.time() - session_data['created_at']
        if session_duration > 0:
            request_rate = session_data['request_count'] / session_duration
            if request_rate > 10:  # More than 10 requests per second
                return True
        
        if session_data['request_count'] > 1000:
            return True
        
        return False

    def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics."""
        current_time = time.time()
        
        active_sessions = 0
        for session_id in self.sessions:
            try:
                session_data = self._decrypt_session_data(self.sessions[session_id])
                if current_time - session_data['last_accessed'] <= self.session_timeout:
                    active_sessions += 1
            except Exception:
                continue
        
        return {
            'active_sessions': active_sessions,
            'total_sessions': len(self.sessions),
            'locked_ips': len([ip for ip, data in self.failed_attempts.items() if data.get('locked', False)]),
            'suspicious_ips': len(self.suspicious_activities),
            'ip_with_sessions': len(self.ip_sessions)
        }


class SecurityError(Exception):
    """Custom exception for security-related errors."""
    
    def __init__(self, message: str, error_code: str = None, client_ip: str = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.client_ip = client_ip
        
        # Log to session logger for debugging
        error_details = f"SecurityError: {message}"
        if error_code:
            error_details += f" [Code: {error_code}]"
        if client_ip:
            error_details += f" [IP: {client_ip}]"
        
        session_logger.error(error_details)
        
        # Also print to terminal for immediate visibility
        print(f"🚨 SECURITY ERROR: {error_details}")
    
    def __str__(self):
        return self.message
