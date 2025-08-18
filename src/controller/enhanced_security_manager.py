"""
Security Manager module
--------------------
Validates scripts for security before execution with enhanced protections
"""

import ast
import logging
import re
import hashlib
import time
from typing import Dict, Any, List, Set, Optional

# Configure logging
security_logger = logging.getLogger("security_manager")

class SecurityManager:
    """
    Manages security for script execution with comprehensive protections
    """
    
    def __init__(self):
        """Initialize the security manager with enhanced security"""
        # Modules that are allowed to be imported in generated scripts
        self.allowed_modules = {
            'pandas', 'pd',
            'numpy', 'np',
            'math',
            're',
            'datetime',
            'collections',
            # Removed 'os' and 'sys' for better security
        }
        
        # Functions/attributes that are forbidden - enhanced list
        self.forbidden_functions = {
            # File system operations
            'open', 'file', 'os.', 'system', 'subprocess', 'exec', 'eval',
            # Network operations
            'socket', 'requests', 'urllib', 'http', 'httplib', 'urllib2',
            # Process operations
            'process', 'fork', 'popen', 'call', 'run',
            # System info
            'sys', 'platform', 'getpass', 'environ',
            # Shell access
            'shell', 'bash', 'sh', 'cmd', 'powershell', '`', 
            # Module operations
            '__import__', 'importlib', 'reload', 'globals', 'locals',
            # Other dangerous operations
            'pickle', 'marshal', 'shelve', 'compile', 'memoryview',
            # Code injection
            'setattr', 'getattr', 'hasattr', 'delattr',
            # Dynamic execution
            'exec', 'eval', 'compile',
        }
        
        # Additional dangerous patterns
        self.dangerous_patterns = [
            r'__.*__',  # Dunder methods
            r'\bclass\s+\w+',  # Class definitions
            r'\bdef\s+\w+',  # Function definitions (except simple lambda)
            r'\bimport\s+\w+',  # Import statements
            r'\bfrom\s+\w+\s+import',  # From import statements
            r'\btry\s*:',  # Try blocks
            r'\bexcept\s*:',  # Except blocks
            r'\bfinally\s*:',  # Finally blocks
            r'\bwith\s+\w+',  # With statements
            r'\byield\s+',  # Yield statements
            r'\bglobal\s+\w+',  # Global statements
            r'\bnonlocal\s+\w+',  # Nonlocal statements
        ]
        
        # Track script executions for rate limiting
        self.script_executions = {}
        self.max_scripts_per_minute = 10
        
        # Track hash of executed scripts to detect duplicates
        self.executed_script_hashes = set()
        
        # Maximum script size
        self.max_script_size = 10000  # 10KB
        
        # Maximum lines
        self.max_lines = 100

    def log_rejection(self, script: str, reason: str):
        """
        Log the rejected script and the reason for rejection
        Args:
            script: The rejected script
            reason: The reason for rejection
        """
        security_logger.warning(f"SecurityManager: Script rejected. Reason: {reason}")
        security_logger.warning(f"Rejected script hash: {hashlib.sha256(script.encode()).hexdigest()}")
        # Don't log the full script content for security reasons

    def validate_script(self, script: str, client_ip: str = None) -> bool:
        """
        Validate a script for security concerns with enhanced checks

        Args:
            script: The Python script to validate
            client_ip: Client IP address for rate limiting

        Returns:
            bool: True if the script passes security validation, False otherwise
        """
        
        # Rate limiting check
        if client_ip and not self._check_rate_limit(client_ip):
            self.log_rejection(script, f"Rate limit exceeded for IP: {client_ip}")
            return False
        
        # Size validation
        if len(script) > self.max_script_size:
            self.log_rejection(script, f"Script too large: {len(script)} bytes")
            return False
        
        # Line count validation
        lines = script.split('\n')
        if len(lines) > self.max_lines:
            self.log_rejection(script, f"Too many lines: {len(lines)}")
            return False
        
        # Check for duplicate scripts
        script_hash = hashlib.sha256(script.encode()).hexdigest()
        if script_hash in self.executed_script_hashes:
            security_logger.warning(f"Duplicate script execution attempt: {script_hash}")
            # Allow duplicates but log them
        else:
            self.executed_script_hashes.add(script_hash)
            # Limit stored hashes to prevent memory issues
            if len(self.executed_script_hashes) > 1000:
                # Remove oldest hashes (simplified approach)
                self.executed_script_hashes = set(list(self.executed_script_hashes)[100:])
        
        # Check for basic syntax issues first
        try:
            tree = ast.parse(script)
        except SyntaxError as e:
            self.log_rejection(script, f"SyntaxError while parsing script: {str(e)}")
            return False
            
        # Allow error handling scripts that just add an error column
        if "LLM_ERROR" in script and "df['LLM_ERROR']" in script and len(script.split('\n')) <= 5:
            return True
        
        # Enhanced pattern checks
        for pattern in self.dangerous_patterns:
            if re.search(pattern, script, re.IGNORECASE):
                self.log_rejection(script, f"Dangerous pattern '{pattern}' found in script.")
                return False
        
        # Basic checks - forbidden functions
        for forbidden in self.forbidden_functions:
            if forbidden in script:
                self.log_rejection(script, f"Forbidden keyword '{forbidden}' found in script.")
                return False
        
        # Use AST to analyze the script more thoroughly
        try:
            # Enhanced AST analysis
            for node in ast.walk(tree):
                # Check for import statements
                if isinstance(node, ast.Import):
                    for name in node.names:
                        if name.name not in self.allowed_modules:
                            self.log_rejection(script, f"Forbidden import '{name.name}' found in script.")
                            return False
                
                # Check for import from statements
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module not in self.allowed_modules:
                        self.log_rejection(script, f"Forbidden import from '{node.module}' found in script.")
                        return False
                    
                # Check for calls to __import__
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id == '__import__':
                        self.log_rejection(script, "__import__ call found in script.")
                        return False
                
                # Check for exec or eval calls
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id in ['exec', 'eval', 'compile']:
                        self.log_rejection(script, f"Forbidden call '{node.func.id}' found in script.")
                        return False
                
                # Check for dangerous attribute access
                elif isinstance(node, ast.Attribute):
                    if node.attr.startswith('__') and node.attr.endswith('__'):
                        self.log_rejection(script, f"Dangerous attribute access '{node.attr}' found in script.")
                        return False
                
                # Check for class or function definitions
                elif isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    self.log_rejection(script, f"Class/function definition found in script.")
                    return False
                
                # Check for try/except blocks (can hide errors)
                elif isinstance(node, ast.Try):
                    self.log_rejection(script, "Try/except block found in script.")
                    return False
                
                # Check for with statements
                elif isinstance(node, ast.With):
                    self.log_rejection(script, "With statement found in script.")
                    return False
                
                # Check for global/nonlocal statements
                elif isinstance(node, (ast.Global, ast.Nonlocal)):
                    self.log_rejection(script, "Global/nonlocal statement found in script.")
                    return False
            
            return True
            
        except Exception as e:
            self.log_rejection(script, f"Error analyzing script: {e}")
            return False
    
    def _check_rate_limit(self, client_ip: str) -> bool:
        """
        Check if client IP is within rate limits
        """
        current_time = time.time()
        minute_ago = current_time - 60
        
        # Initialize tracking for new IPs
        if client_ip not in self.script_executions:
            self.script_executions[client_ip] = []
        
        # Remove old entries
        self.script_executions[client_ip] = [
            timestamp for timestamp in self.script_executions[client_ip]
            if timestamp > minute_ago
        ]
        
        # Check if limit exceeded
        if len(self.script_executions[client_ip]) >= self.max_scripts_per_minute:
            return False
        
        # Add current execution
        self.script_executions[client_ip].append(current_time)
        return True
    
    def get_sandbox_parameters(self) -> Dict[str, Any]:
        """
        Get parameters for sandbox environment

        Returns:
            Dict[str, Any]: Parameters for sandbox environment
        """
        return {
            'allowed_modules': list(self.allowed_modules),
            'forbidden_functions': list(self.forbidden_functions),
            'max_script_size': self.max_script_size,
            'max_lines': self.max_lines,
            'max_scripts_per_minute': self.max_scripts_per_minute
        }
    
    def get_security_stats(self) -> Dict[str, Any]:
        """
        Get security statistics
        """
        return {
            'executed_scripts_count': len(self.executed_script_hashes),
            'tracked_ips': len(self.script_executions),
            'rate_limited_ips': sum(1 for executions in self.script_executions.values() 
                                  if len(executions) >= self.max_scripts_per_minute)
        }
    
    def cleanup_old_data(self):
        """
        Cleanup old tracking data to prevent memory issues
        """
        current_time = time.time()
        minute_ago = current_time - 60
        
        # Cleanup rate limiting data
        for ip in list(self.script_executions.keys()):
            self.script_executions[ip] = [
                timestamp for timestamp in self.script_executions[ip]
                if timestamp > minute_ago
            ]
            
            # Remove empty entries
            if not self.script_executions[ip]:
                del self.script_executions[ip]
