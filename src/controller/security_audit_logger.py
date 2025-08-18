"""
Security Audit Logger module
--------------------------
Comprehensive security logging and monitoring for the finance application
"""

import os
import json
import time
import logging
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import hashlib
from collections import defaultdict, deque

class SecurityEventType(Enum):
    """Types of security events"""
    LOGIN_ATTEMPT = "login_attempt"
    SESSION_CREATED = "session_created"
    SESSION_EXPIRED = "session_expired"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    IP_BLOCKED = "ip_blocked"
    SUSPICIOUS_REQUEST = "suspicious_request"
    FILE_UPLOAD = "file_upload"
    SCRIPT_EXECUTION = "script_execution"
    SCRIPT_REJECTED = "script_rejected"
    XSS_ATTEMPT = "xss_attempt"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    PATH_TRAVERSAL_ATTEMPT = "path_traversal_attempt"
    MALWARE_DETECTED = "malware_detected"
    DDOS_ATTEMPT = "ddos_attempt"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_BREACH_ATTEMPT = "data_breach_attempt"
    CONFIGURATION_CHANGE = "configuration_change"
    SYSTEM_ERROR = "system_error"

class SecuritySeverity(Enum):
    """Security event severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SecurityAuditLogger:
    """
    Comprehensive security audit logger
    """
    
    def __init__(self, log_directory: str = "logs", max_log_size: int = 10 * 1024 * 1024):
        """
        Initialize the security audit logger
        
        Args:
            log_directory: Directory to store log files
            max_log_size: Maximum size for log files before rotation
        """
        self.log_directory = log_directory
        self.max_log_size = max_log_size
        
        # Create log directory
        os.makedirs(log_directory, exist_ok=True)
        
        # Initialize loggers
        self._setup_loggers()
        
        # Event tracking
        self.event_counts = defaultdict(int)
        self.event_history = defaultdict(deque)
        self.alert_thresholds = self._get_alert_thresholds()
        
        # Thread lock for concurrent access
        self.lock = threading.Lock()
        
        # Cache for IP geolocation (if available)
        self.ip_cache = {}
        
        # Alert notifications queue
        self.pending_alerts = deque()

    def _setup_loggers(self):
        """Setup different types of loggers"""
        
        # Security events logger
        self.security_logger = logging.getLogger("security_events")
        self.security_logger.setLevel(logging.INFO)
        
        security_handler = logging.FileHandler(
            os.path.join(self.log_directory, "security_events.log")
        )
        security_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - SECURITY - %(message)s'
        )
        security_handler.setFormatter(security_formatter)
        self.security_logger.addHandler(security_handler)
        
        # Access logger
        self.access_logger = logging.getLogger("access_log")
        self.access_logger.setLevel(logging.INFO)
        
        access_handler = logging.FileHandler(
            os.path.join(self.log_directory, "access.log")
        )
        access_formatter = logging.Formatter(
            '%(asctime)s - ACCESS - %(message)s'
        )
        access_handler.setFormatter(access_formatter)
        self.access_logger.addHandler(access_handler)
        
        # Threat intelligence logger
        self.threat_logger = logging.getLogger("threat_intelligence")
        self.threat_logger.setLevel(logging.WARNING)
        
        threat_handler = logging.FileHandler(
            os.path.join(self.log_directory, "threats.log")
        )
        threat_formatter = logging.Formatter(
            '%(asctime)s - THREAT - %(levelname)s - %(message)s'
        )
        threat_handler.setFormatter(threat_formatter)
        self.threat_logger.addHandler(threat_handler)

    def _get_alert_thresholds(self) -> Dict[SecurityEventType, Dict[str, int]]:
        """Get alert thresholds for different event types"""
        return {
            SecurityEventType.RATE_LIMIT_EXCEEDED: {"count": 5, "window": 300},
            SecurityEventType.SUSPICIOUS_REQUEST: {"count": 3, "window": 300},
            SecurityEventType.SCRIPT_REJECTED: {"count": 10, "window": 600},
            SecurityEventType.XSS_ATTEMPT: {"count": 1, "window": 300},
            SecurityEventType.SQL_INJECTION_ATTEMPT: {"count": 1, "window": 300},
            SecurityEventType.PATH_TRAVERSAL_ATTEMPT: {"count": 1, "window": 300},
            SecurityEventType.MALWARE_DETECTED: {"count": 1, "window": 300},
            SecurityEventType.DDOS_ATTEMPT: {"count": 1, "window": 60},
            SecurityEventType.UNAUTHORIZED_ACCESS: {"count": 3, "window": 300},
        }

    def log_security_event(
        self,
        event_type: SecurityEventType,
        severity: SecuritySeverity,
        client_ip: str,
        user_agent: str = "",
        request_path: str = "",
        session_id: str = "",
        details: Dict[str, Any] = None,
        additional_context: Dict[str, Any] = None
    ):
        """
        Log a security event
        
        Args:
            event_type: Type of security event
            severity: Severity level
            client_ip: Client IP address
            user_agent: User agent string
            request_path: Request path
            session_id: Session ID (if available)
            details: Event-specific details
            additional_context: Additional context information
        """
        
        with self.lock:
            timestamp = time.time()
            
            # Create event data
            event_data = {
                "timestamp": timestamp,
                "datetime": datetime.fromtimestamp(timestamp).isoformat(),
                "event_type": event_type.value,
                "severity": severity.value,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "request_path": request_path,
                "session_id": session_id,
                "details": details or {},
                "additional_context": additional_context or {}
            }
            
            # Add IP geolocation if available
            event_data["ip_info"] = self._get_ip_info(client_ip)
            
            # Generate event hash for deduplication
            event_hash = self._generate_event_hash(event_data)
            event_data["event_hash"] = event_hash
            
            # Log the event
            log_message = self._format_log_message(event_data)
            
            if severity in [SecuritySeverity.HIGH, SecuritySeverity.CRITICAL]:
                self.threat_logger.warning(log_message)
            else:
                self.security_logger.info(log_message)
            
            # Track event for alerting
            self._track_event_for_alerting(event_type, client_ip, timestamp)
            
            # Check if alert should be triggered
            self._check_alert_conditions(event_type, client_ip, severity)

    def log_access(
        self,
        client_ip: str,
        method: str,
        path: str,
        status_code: int,
        response_time: float,
        user_agent: str = "",
        session_id: str = "",
        request_size: int = 0,
        response_size: int = 0
    ):
        """
        Log access/request information
        """
        
        access_data = {
            "timestamp": time.time(),
            "client_ip": client_ip,
            "method": method,
            "path": path,
            "status_code": status_code,
            "response_time": response_time,
            "user_agent": user_agent,
            "session_id": session_id,
            "request_size": request_size,
            "response_size": response_size
        }
        
        log_message = json.dumps(access_data)
        self.access_logger.info(log_message)

    def log_file_upload(
        self,
        client_ip: str,
        filename: str,
        file_size: int,
        file_type: str,
        validation_result: Dict[str, Any],
        session_id: str = ""
    ):
        """
        Log file upload events
        """
        
        severity = SecuritySeverity.MEDIUM if validation_result.get('is_valid', True) else SecuritySeverity.HIGH
        
        details = {
            "filename": filename,
            "file_size": file_size,
            "file_type": file_type,
            "validation_result": validation_result,
            "file_hash": validation_result.get('file_info', {}).get('hash_sha256', '')
        }
        
        self.log_security_event(
            event_type=SecurityEventType.FILE_UPLOAD,
            severity=severity,
            client_ip=client_ip,
            session_id=session_id,
            details=details
        )

    def log_script_execution(
        self,
        client_ip: str,
        script_hash: str,
        execution_result: str,
        execution_time: float,
        session_id: str = ""
    ):
        """
        Log script execution events
        """
        
        details = {
            "script_hash": script_hash,
            "execution_result": execution_result,
            "execution_time": execution_time
        }
        
        severity = SecuritySeverity.LOW if execution_result == "success" else SecuritySeverity.MEDIUM
        
        self.log_security_event(
            event_type=SecurityEventType.SCRIPT_EXECUTION,
            severity=severity,
            client_ip=client_ip,
            session_id=session_id,
            details=details
        )

    def log_script_rejection(
        self,
        client_ip: str,
        script_hash: str,
        rejection_reason: str,
        session_id: str = ""
    ):
        """
        Log script rejection events
        """
        
        details = {
            "script_hash": script_hash,
            "rejection_reason": rejection_reason
        }
        
        self.log_security_event(
            event_type=SecurityEventType.SCRIPT_REJECTED,
            severity=SecuritySeverity.MEDIUM,
            client_ip=client_ip,
            session_id=session_id,
            details=details
        )

    def log_suspicious_activity(
        self,
        client_ip: str,
        activity_type: str,
        request_data: Dict[str, Any],
        user_agent: str = "",
        session_id: str = ""
    ):
        """
        Log suspicious activity
        """
        
        # Determine event type based on activity
        event_type_mapping = {
            "xss": SecurityEventType.XSS_ATTEMPT,
            "sql_injection": SecurityEventType.SQL_INJECTION_ATTEMPT,
            "path_traversal": SecurityEventType.PATH_TRAVERSAL_ATTEMPT,
            "malware": SecurityEventType.MALWARE_DETECTED,
            "ddos": SecurityEventType.DDOS_ATTEMPT,
        }
        
        event_type = event_type_mapping.get(activity_type, SecurityEventType.SUSPICIOUS_REQUEST)
        
        details = {
            "activity_type": activity_type,
            "request_data": request_data
        }
        
        self.log_security_event(
            event_type=event_type,
            severity=SecuritySeverity.HIGH,
            client_ip=client_ip,
            user_agent=user_agent,
            session_id=session_id,
            details=details
        )

    def _get_ip_info(self, ip: str) -> Dict[str, Any]:
        """
        Get IP information (geolocation, ASN, etc.)
        This is a placeholder - you can integrate with services like MaxMind GeoIP
        """
        
        if ip in self.ip_cache:
            return self.ip_cache[ip]
        
        # Basic IP classification
        ip_info = {
            "ip": ip,
            "is_private": self._is_private_ip(ip),
            "is_local": ip in ["127.0.0.1", "::1", "localhost"],
            "country": "unknown",
            "asn": "unknown",
            "organization": "unknown"
        }
        
        # Cache the result
        self.ip_cache[ip] = ip_info
        
        # Limit cache size
        if len(self.ip_cache) > 10000:
            # Remove oldest entries
            keys_to_remove = list(self.ip_cache.keys())[:1000]
            for key in keys_to_remove:
                del self.ip_cache[key]
        
        return ip_info

    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP is in private ranges"""
        try:
            import ipaddress
            ip_obj = ipaddress.ip_address(ip)
            return ip_obj.is_private
        except:
            return False

    def _generate_event_hash(self, event_data: Dict[str, Any]) -> str:
        """Generate a hash for event deduplication"""
        # Create a string representation for hashing
        hash_data = f"{event_data['event_type']}{event_data['client_ip']}{event_data.get('details', {})}"
        return hashlib.sha256(hash_data.encode()).hexdigest()[:16]

    def _format_log_message(self, event_data: Dict[str, Any]) -> str:
        """Format log message"""
        return json.dumps(event_data, separators=(',', ':'))

    def _track_event_for_alerting(self, event_type: SecurityEventType, client_ip: str, timestamp: float):
        """Track events for alerting purposes"""
        
        key = f"{event_type.value}:{client_ip}"
        
        # Add to event history
        self.event_history[key].append(timestamp)
        
        # Keep only recent events
        threshold_config = self.alert_thresholds.get(event_type, {"window": 300})
        window = threshold_config["window"]
        cutoff_time = timestamp - window
        
        while self.event_history[key] and self.event_history[key][0] < cutoff_time:
            self.event_history[key].popleft()

    def _check_alert_conditions(self, event_type: SecurityEventType, client_ip: str, severity: SecuritySeverity):
        """Check if alert conditions are met"""
        
        if event_type not in self.alert_thresholds:
            return
        
        threshold_config = self.alert_thresholds[event_type]
        key = f"{event_type.value}:{client_ip}"
        
        event_count = len(self.event_history[key])
        threshold_count = threshold_config["count"]
        
        if event_count >= threshold_count:
            self._generate_alert(event_type, client_ip, event_count, severity)

    def _generate_alert(self, event_type: SecurityEventType, client_ip: str, event_count: int, severity: SecuritySeverity):
        """Generate a security alert"""
        
        alert = {
            "timestamp": time.time(),
            "alert_type": "threshold_exceeded",
            "event_type": event_type.value,
            "client_ip": client_ip,
            "event_count": event_count,
            "severity": severity.value,
            "message": f"Alert: {event_type.value} threshold exceeded for IP {client_ip} ({event_count} events)"
        }
        
        self.pending_alerts.append(alert)
        
        # Log the alert
        self.threat_logger.critical(f"ALERT: {alert['message']}")

    def get_security_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get security summary for the specified time period
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Security summary statistics
        """
        
        cutoff_time = time.time() - (hours * 3600)
        
        summary = {
            "time_period_hours": hours,
            "event_counts": {},
            "top_threat_ips": {},
            "alert_count": len(self.pending_alerts),
            "severity_distribution": defaultdict(int)
        }
        
        # This is a simplified implementation
        # In a real scenario, you'd parse log files or query a database
        
        return summary

    def get_pending_alerts(self) -> List[Dict[str, Any]]:
        """Get and clear pending alerts"""
        
        with self.lock:
            alerts = list(self.pending_alerts)
            self.pending_alerts.clear()
            return alerts

    def cleanup_old_logs(self, days: int = 30):
        """Clean up log files older than specified days"""
        
        cutoff_time = time.time() - (days * 24 * 3600)
        
        for filename in os.listdir(self.log_directory):
            file_path = os.path.join(self.log_directory, filename)
            
            if os.path.isfile(file_path):
                file_mtime = os.path.getmtime(file_path)
                
                if file_mtime < cutoff_time:
                    try:
                        os.remove(file_path)
                        print(f"Removed old log file: {filename}")
                    except Exception as e:
                        print(f"Error removing log file {filename}: {e}")

# Global audit logger instance
audit_logger = SecurityAuditLogger()
