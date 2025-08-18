"""
Security Configuration module
---------------------------
Centralized security configuration for the finance application
"""

import os
from typing import Dict, List, Set, Any
from enum import Enum

class SecurityLevel(Enum):
    """Security levels for different environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class SecurityConfig:
    """
    Centralized security configuration
    """
    
    def __init__(self, environment: str = "development"):
        """
        Initialize security configuration
        
        Args:
            environment: The environment (development, staging, production)
        """
        self.environment = SecurityLevel(environment.lower())
        
        # Load configuration based on environment
        self._load_config()
    
    def _load_config(self):
        """Load configuration based on environment"""
        
        # Base security settings
        self.session_timeout = 3600  # 1 hour
        self.max_sessions_per_ip = 10
        self.rate_limit_requests = 100
        self.rate_limit_window = 300  # 5 minutes
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.allowed_file_extensions = {'xlsx', 'xls', 'csv', 'txt'}
        
        # Adjust based on environment
        if self.environment == SecurityLevel.PRODUCTION:
            self._load_production_config()
        elif self.environment == SecurityLevel.STAGING:
            self._load_staging_config()
        else:
            self._load_development_config()
    
    def _load_production_config(self):
        """Production security settings (strictest)"""
        self.session_timeout = 1800  # 30 minutes
        self.max_sessions_per_ip = 5
        self.rate_limit_requests = 50
        self.rate_limit_window = 300
        self.max_file_size = 25 * 1024 * 1024  # 25MB
        self.enable_ip_blocking = True
        self.enable_geo_blocking = True
        self.require_https = True
        self.enable_csrf_protection = True
        self.enable_content_security_policy = True
        self.log_level = "WARNING"
        
        # Security headers for production
        self.security_headers = {
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": self._get_strict_csp(),
            "Permissions-Policy": self._get_strict_permissions_policy()
        }
        
        # Allowed IP ranges (can be configured)
        self.allowed_ip_ranges = os.getenv("ALLOWED_IP_RANGES", "").split(",")
        
        # Blocked countries (ISO codes)
        self.blocked_countries = os.getenv("BLOCKED_COUNTRIES", "").split(",")
    
    def _load_staging_config(self):
        """Staging security settings (moderate)"""
        self.session_timeout = 3600  # 1 hour
        self.max_sessions_per_ip = 8
        self.rate_limit_requests = 75
        self.rate_limit_window = 300
        self.max_file_size = 40 * 1024 * 1024  # 40MB
        self.enable_ip_blocking = True
        self.enable_geo_blocking = False
        self.require_https = True
        self.enable_csrf_protection = True
        self.enable_content_security_policy = True
        self.log_level = "INFO"
        
        self.security_headers = {
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": self._get_moderate_csp(),
            "Permissions-Policy": self._get_moderate_permissions_policy()
        }
    
    def _load_development_config(self):
        """Development security settings (relaxed for debugging)"""
        self.session_timeout = 7200  # 2 hours
        self.max_sessions_per_ip = 15
        self.rate_limit_requests = 200
        self.rate_limit_window = 300
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.enable_ip_blocking = False
        self.enable_geo_blocking = False
        self.require_https = False
        self.enable_csrf_protection = False
        self.enable_content_security_policy = False
        self.log_level = "DEBUG"
        
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",
            "X-XSS-Protection": "1; mode=block"
        }
    
    def _get_strict_csp(self) -> str:
        """Get strict Content Security Policy for production"""
        return (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
    
    def _get_moderate_csp(self) -> str:
        """Get moderate Content Security Policy for staging"""
        return (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'self'; "
            "base-uri 'self';"
        )
    
    def _get_strict_permissions_policy(self) -> str:
        """Get strict Permissions Policy for production"""
        return (
            "geolocation=(), "
            "camera=(), "
            "microphone=(), "
            "usb=(), "
            "bluetooth=(), "
            "magnetometer=(), "
            "accelerometer=(), "
            "gyroscope=(), "
            "payment=(), "
            "midi=(), "
            "sync-xhr=(), "
            "fullscreen=()"
        )
    
    def _get_moderate_permissions_policy(self) -> str:
        """Get moderate Permissions Policy for staging"""
        return (
            "geolocation=(), "
            "camera=(), "
            "microphone=(), "
            "usb=(), "
            "magnetometer=(), "
            "accelerometer=(), "
            "gyroscope=(), "
            "payment=()"
        )
    
    def get_cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration"""
        if self.environment == SecurityLevel.PRODUCTION:
            return {
                "allow_origins": os.getenv("ALLOWED_ORIGINS", "").split(","),
                "allow_credentials": False,
                "allow_methods": ["GET", "POST"],
                "allow_headers": ["Content-Type", "Authorization"]
            }
        elif self.environment == SecurityLevel.STAGING:
            return {
                "allow_origins": ["https://staging.yourdomain.com"],
                "allow_credentials": False,
                "allow_methods": ["GET", "POST", "PUT", "DELETE"],
                "allow_headers": ["*"]
            }
        else:  # Development
            return {
                "allow_origins": ["*"],
                "allow_credentials": True,
                "allow_methods": ["*"],
                "allow_headers": ["*"]
            }
    
    def get_rate_limiting_config(self) -> Dict[str, Any]:
        """Get rate limiting configuration"""
        return {
            "requests_per_minute": self.rate_limit_requests,
            "window_seconds": self.rate_limit_window,
            "key_func": lambda request: request.client.host
        }
    
    def get_file_validation_config(self) -> Dict[str, Any]:
        """Get file validation configuration"""
        return {
            "max_file_size": self.max_file_size,
            "allowed_extensions": self.allowed_file_extensions,
            "scan_for_malware": self.environment == SecurityLevel.PRODUCTION,
            "validate_file_content": True,
            "check_file_signatures": True
        }
    
    def get_session_config(self) -> Dict[str, Any]:
        """Get session configuration"""
        return {
            "timeout": self.session_timeout,
            "max_sessions_per_ip": self.max_sessions_per_ip,
            "secure_cookies": self.environment != SecurityLevel.DEVELOPMENT,
            "httponly_cookies": True,
            "samesite": "strict" if self.environment == SecurityLevel.PRODUCTION else "lax"
        }
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return {
            "level": self.log_level,
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "handlers": ["console", "file"] if self.environment != SecurityLevel.DEVELOPMENT else ["console"],
            "security_log_file": "security.log",
            "access_log_file": "access.log",
            "max_log_size": 10 * 1024 * 1024,  # 10MB
            "backup_count": 5
        }
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == SecurityLevel.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == SecurityLevel.DEVELOPMENT
    
    def get_blocked_user_agents(self) -> List[str]:
        """Get list of blocked user agents"""
        return [
            "sqlmap",
            "nikto", 
            "nmap",
            "masscan",
            "nessus",
            "w3af",
            "skipfish",
            "hydra",
            "dirb",
            "dirbuster",
            "gobuster",
            "wfuzz",
            "burp"
        ]
    
    def get_suspicious_patterns(self) -> List[str]:
        """Get list of suspicious request patterns"""
        return [
            r'\.\./',              # Path traversal
            r'<script',            # XSS
            r'javascript:',        # Javascript injection
            r'vbscript:',         # VBScript injection
            r'onload=',           # Event handlers
            r'onerror=',          # Event handlers
            r'eval\(',            # Code injection
            r'exec\(',            # Code execution
            r'system\(',          # System calls
            r'subprocess',        # Subprocess calls
            r'\bselect\s+\*\s+from\b',  # SQL injection
            r'\bunion\s+select\b',      # SQL injection
            r'drop\s+table',            # SQL injection
            r'insert\s+into',           # SQL injection
            r'update\s+\w+\s+set',      # SQL injection
            r'delete\s+from',           # SQL injection
        ]

# Global security configuration instance
security_config = SecurityConfig(environment=os.getenv("ENVIRONMENT", "development"))
