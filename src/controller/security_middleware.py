"""
Security Middleware module
------------------------
Implements comprehensive security middleware for the FastAPI application
"""

import time
import hashlib
import logging
from typing import Dict, List, Optional, Set
from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
import json
import re
from urllib.parse import urlparse
from collections import defaultdict, deque
import ipaddress

# Configure logging
logging.basicConfig(level=logging.INFO)
security_logger = logging.getLogger("security")

class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security middleware for the application
    """
    
    def __init__(self, app, config: Dict = None):
        super().__init__(app)
        self.config = config or {}
        
        # Rate limiting configuration
        self.rate_limit_requests = self.config.get('rate_limit_requests', 100)  # requests per window
        self.rate_limit_window = self.config.get('rate_limit_window', 300)     # 5 minutes
        self.rate_limit_storage = defaultdict(deque)
        
        # DDoS protection
        self.ddos_threshold = self.config.get('ddos_threshold', 500)
        self.ddos_window = self.config.get('ddos_window', 60)  # 1 minute
        self.ddos_storage = defaultdict(deque)
        
        # Blocked IPs (can be expanded with external threat intelligence)
        self.blocked_ips: Set[str] = set()
        self.suspicious_patterns = [
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
        ]
        
        # File type validation
        self.allowed_mime_types = {
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
            'application/vnd.ms-excel',  # .xls
            'text/csv',                  # .csv
            'text/plain',                # .txt for commands
        }
        
        # Max file sizes (in bytes)
        self.max_file_sizes = {
            'spreadsheet': 50 * 1024 * 1024,  # 50MB for spreadsheets
            'text': 1 * 1024 * 1024,          # 1MB for text files
            'default': 10 * 1024 * 1024        # 10MB default
        }

    async def dispatch(self, request: Request, call_next):
        """
        Main security middleware dispatcher
        """
        start_time = time.time()
        
        try:
            # Get client IP
            client_ip = self.get_client_ip(request)
            
            # Check if IP is blocked
            if self.is_ip_blocked(client_ip):
                security_logger.warning(f"Blocked IP attempted access: {client_ip}")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Access denied"}
                )
            
            # DDoS protection
            if self.is_ddos_attack(client_ip):
                security_logger.warning(f"Potential DDoS from IP: {client_ip}")
                self.blocked_ips.add(client_ip)
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Too many requests"}
                )
            
            # Rate limiting
            if self.is_rate_limited(client_ip):
                security_logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Rate limit exceeded"}
                )
            
            # Input validation
            await self.validate_request(request)
            
            # Process request
            response = await call_next(request)
            
            # Add security headers
            response = self.add_security_headers(response)
            
            # Log security events
            self.log_request(request, response, client_ip, time.time() - start_time)
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            security_logger.error(f"Security middleware error: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error"}
            )

    def get_client_ip(self, request: Request) -> str:
        """
        Extract the real client IP address
        """
        # Check X-Forwarded-For header (for proxies/load balancers)
        if "x-forwarded-for" in request.headers:
            ips = request.headers["x-forwarded-for"].split(",")
            return ips[0].strip()
        
        # Check X-Real-IP header
        if "x-real-ip" in request.headers:
            return request.headers["x-real-ip"]
        
        # Fall back to direct connection IP
        return request.client.host if request.client else "unknown"

    def is_ip_blocked(self, ip: str) -> bool:
        """
        Check if an IP address is blocked
        """
        if ip in self.blocked_ips:
            return True
            
        # Check for private/internal IPs in production
        try:
            ip_obj = ipaddress.ip_address(ip)
            # Allow localhost for development
            if ip in ['127.0.0.1', 'localhost', '::1']:
                return False
        except ValueError:
            return True  # Invalid IP format
            
        return False

    def is_ddos_attack(self, ip: str) -> bool:
        """
        Detect potential DDoS attacks
        """
        now = time.time()
        window_start = now - self.ddos_window
        
        # Clean old entries
        while self.ddos_storage[ip] and self.ddos_storage[ip][0] < window_start:
            self.ddos_storage[ip].popleft()
        
        # Add current request
        self.ddos_storage[ip].append(now)
        
        # Check if threshold exceeded
        return len(self.ddos_storage[ip]) > self.ddos_threshold

    def is_rate_limited(self, ip: str) -> bool:
        """
        Check if IP is rate limited
        """
        now = time.time()
        window_start = now - self.rate_limit_window
        
        # Clean old entries
        while self.rate_limit_storage[ip] and self.rate_limit_storage[ip][0] < window_start:
            self.rate_limit_storage[ip].popleft()
        
        # Check current request count
        if len(self.rate_limit_storage[ip]) >= self.rate_limit_requests:
            return True
        
        # Add current request
        self.rate_limit_storage[ip].append(now)
        return False

    async def validate_request(self, request: Request):
        """
        Validate incoming requests for security threats
        """
        # Validate URL path
        self.validate_url_path(str(request.url))
        
        # Validate headers
        self.validate_headers(request.headers)
        
        # Validate query parameters
        if request.url.query:
            self.validate_input(request.url.query, "query_params")
        
        # Validate request body for POST requests
        if request.method in ["POST", "PUT", "PATCH"]:
            await self.validate_request_body(request)

    def validate_url_path(self, url: str):
        """
        Validate URL path for security threats
        """
        parsed_url = urlparse(url)
        path = parsed_url.path
        
        # Check for suspicious patterns
        for pattern in self.suspicious_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                security_logger.warning(f"Suspicious pattern in URL: {pattern} - {url}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid request"
                )
        
        # Check for path traversal
        if "../" in path or "..\\" in path:
            security_logger.warning(f"Path traversal attempt: {url}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid path"
            )

    def validate_headers(self, headers):
        """
        Validate request headers
        """
        # Check for suspicious user agents
        user_agent = headers.get("user-agent", "").lower()
        suspicious_agents = ["sqlmap", "nikto", "nmap", "masscan", "nessus"]
        
        for agent in suspicious_agents:
            if agent in user_agent:
                security_logger.warning(f"Suspicious user agent: {user_agent}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )

    async def validate_request_body(self, request: Request):
        """
        Validate request body content
        """
        # Check content type
        content_type = request.headers.get("content-type", "")
        
        # For file uploads, validate content
        if "multipart/form-data" in content_type:
            # This will be handled by file upload validation
            return
        
        # For JSON requests, validate JSON content
        if "application/json" in content_type:
            try:
                # Read a copy of the body for validation
                body = await request.body()
                if body:
                    content = body.decode('utf-8')
                    self.validate_input(content, "json_body")
            except Exception as e:
                security_logger.warning(f"Invalid JSON body: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON"
                )

    def validate_input(self, input_text: str, input_type: str):
        """
        Validate input text for malicious content
        """
        # Check for suspicious patterns
        for pattern in self.suspicious_patterns:
            if re.search(pattern, input_text, re.IGNORECASE):
                security_logger.warning(f"Suspicious pattern in {input_type}: {pattern}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid input detected"
                )
        
        # Check input length (prevent DoS through large inputs)
        if len(input_text) > 1000000:  # 1MB text limit
            security_logger.warning(f"Oversized {input_type}: {len(input_text)} bytes")
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Input too large"
            )

    def add_security_headers(self, response: Response) -> Response:
        """
        Add security headers to response
        """
        # Prevent XSS attacks
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # HTTPS enforcement (when deployed with HTTPS)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        
        # Prevent information disclosure
        response.headers["Server"] = "EditorLive"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "camera=(), "
            "microphone=(), "
            "usb=(), "
            "magnetometer=(), "
            "accelerometer=(), "
            "gyroscope=()"
        )
        
        return response

    def log_request(self, request: Request, response: Response, client_ip: str, duration: float):
        """
        Log security-relevant information about requests
        """
        log_data = {
            "timestamp": time.time(),
            "client_ip": client_ip,
            "method": request.method,
            "path": str(request.url.path),
            "status_code": response.status_code,
            "duration": round(duration, 3),
            "user_agent": request.headers.get("user-agent", ""),
            "referer": request.headers.get("referer", ""),
            "content_length": request.headers.get("content-length", "0")
        }
        
        # Log suspicious activities
        if response.status_code >= 400:
            security_logger.warning(f"Suspicious request: {json.dumps(log_data)}")
        else:
            security_logger.info(f"Request: {log_data['method']} {log_data['path']} - {log_data['status_code']}")

    def cleanup_old_entries(self):
        """
        Cleanup old entries from rate limiting storage
        """
        now = time.time()
        
        # Cleanup rate limiting storage
        for ip in list(self.rate_limit_storage.keys()):
            window_start = now - self.rate_limit_window
            while self.rate_limit_storage[ip] and self.rate_limit_storage[ip][0] < window_start:
                self.rate_limit_storage[ip].popleft()
            
            # Remove empty entries
            if not self.rate_limit_storage[ip]:
                del self.rate_limit_storage[ip]
        
        # Cleanup DDoS storage
        for ip in list(self.ddos_storage.keys()):
            window_start = now - self.ddos_window
            while self.ddos_storage[ip] and self.ddos_storage[ip][0] < window_start:
                self.ddos_storage[ip].popleft()
            
            if not self.ddos_storage[ip]:
                del self.ddos_storage[ip]
