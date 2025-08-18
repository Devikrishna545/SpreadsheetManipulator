"""
Security Manager module
--------------------
Validates scripts for security before execution with integrated logging
"""

import ast
import logging
from typing import Dict, Any, Optional


class SecurityManager:
    """
    Manages security for script execution with integrated session logging
    """
    
    def __init__(self):
        """Initialize the security manager"""
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
        
        # Functions/attributes that are forbidden
        self.forbidden_functions = {
            # File system operations
            'open', 'file', 'os.', 'system', 'subprocess', 'exec', 'eval',
            # Network operations
            'socket', 'requests', 'urllib', 'http', 
            # Process operations
            'process', 'fork', 
            # System info
            'sys', 'platform', 'getpass',
            # Shell access
            'shell', 'bash', 'sh', 'cmd', '`', 
            # Module operations
            '__import__', 'importlib', 'reload', 'globals', 'locals',
            # Other dangerous operations
            'pickle', 'marshal', 'shelve'
        }

    def log_rejection(self, script: str, reason: str, session_id: Optional[str] = None):
        """
        Log the rejected script and the reason for rejection
        Args:
            script: The rejected script
            reason: The reason for rejection
            session_id: Optional session ID for enhanced logging
        """
        logging.warning(f"SecurityManager: Script rejected. Reason: {reason}")
        logging.warning(f"Rejected script:\n{script}")
        
        # Enhanced session-based logging
        if session_id:
            try:
                from src.controller.session_manager import session_manager
                from src.controller.security_logger import SecurityLevel
                
                session_manager.log_security_event(
                    session_id,
                    SecurityLevel.HIGH,
                    "script_validation",
                    f"🚫 Script validation failed: {reason}",
                    {
                        'script_preview': script[:200] + '...' if len(script) > 200 else script,
                        'script_length': len(script),
                        'validation_result': 'REJECTED',
                        'rejection_reason': reason,
                        'forbidden_content': self._identify_threats(script)
                    },
                    "SecurityManager"
                )
            except ImportError:
                pass  # Fallback if session manager not available

    def validate_script(self, script: str, session_id: Optional[str] = None) -> tuple[bool, str]:
        """
        Validate a script for security concerns with enhanced logging

        Args:
            script: The Python script to validate
            session_id: Optional session ID for enhanced logging

        Returns:
            tuple[bool, str]: (True/False if script is safe, reason message)
        """
        # Check for basic syntax issues first
        try:
            ast.parse(script)
        except SyntaxError as e:
            reason = f"SyntaxError while parsing script: {str(e)}"
            self.log_rejection(script, reason, session_id)
            return False, reason
            
        # Allow error handling scripts that just add an error column
        if "LLM_ERROR" in script and "df['LLM_ERROR']" in script and len(script.split('\n')) <= 5:
            success_reason = "Error handling script allowed"
            self._log_validation_success(script, success_reason, session_id)
            return True, success_reason
        
        # Basic checks - forbidden functions
        for forbidden in self.forbidden_functions:
            if forbidden in script:
                reason = f"Forbidden keyword '{forbidden}' found in script."
                self.log_rejection(script, reason, session_id)
                return False, reason
        
        # Use AST to analyze the script more thoroughly
        try:
            tree = ast.parse(script)
            
            # Check imports
            for node in ast.walk(tree):
                # Check for import statements
                if isinstance(node, ast.Import):
                    for name in node.names:
                        if name.name not in self.allowed_modules:
                            reason = f"Forbidden import '{name.name}' found in script."
                            self.log_rejection(script, reason, session_id)
                            return False, reason
                
                # Check for import from statements
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module not in self.allowed_modules:
                        reason = f"Forbidden import from '{node.module}' found in script."
                        self.log_rejection(script, reason, session_id)
                        return False, reason
                    
                # Check for calls to __import__
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id == '__import__':
                        reason = "__import__ call found in script."
                        self.log_rejection(script, reason, session_id)
                        return False, reason
                
                # Check for exec or eval calls
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id in ['exec', 'eval']:
                        reason = f"Forbidden call '{node.func.id}' found in script."
                        self.log_rejection(script, reason, session_id)
                        return False, reason
            
            success_reason = "Script passed security validation"
            self._log_validation_success(script, success_reason, session_id)
            return True, success_reason
            
        except SyntaxError as e:
            reason = f"SyntaxError while parsing script: {e}"
            self.log_rejection(script, reason, session_id)
            return False, reason
    
    def _log_validation_success(self, script: str, reason: str, session_id: Optional[str] = None):
        """
        Log successful script validation
        
        Args:
            script: The validated script
            reason: Success reason
            session_id: Optional session ID for enhanced logging
        """
        if session_id:
            try:
                from src.controller.session_manager import session_manager
                from src.controller.security_logger import SecurityLevel
                
                session_manager.log_security_event(
                    session_id,
                    SecurityLevel.LOW,
                    "script_validation",
                    f"✅ Script validation passed: {reason}",
                    {
                        'script_preview': script[:200] + '...' if len(script) > 200 else script,
                        'script_length': len(script),
                        'validation_result': 'APPROVED',
                        'approval_reason': reason,
                        'allowed_modules': list(self.allowed_modules)
                    },
                    "SecurityManager"
                )
            except ImportError:
                pass  # Fallback if session manager not available
    
    def _identify_threats(self, script: str) -> Dict[str, list]:
        """
        Identify specific threats in a script
        
        Args:
            script: Script to analyze
            
        Returns:
            Dict[str, list]: Categorized threats found
        """
        threats = {
            'forbidden_functions': [],
            'forbidden_imports': [],
            'dangerous_patterns': []
        }
        
        # Check for forbidden functions
        for forbidden in self.forbidden_functions:
            if forbidden in script:
                threats['forbidden_functions'].append(forbidden)
        
        # Check for dangerous imports via AST
        try:
            tree = ast.parse(script)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        if name.name not in self.allowed_modules:
                            threats['forbidden_imports'].append(name.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module not in self.allowed_modules:
                        threats['forbidden_imports'].append(node.module)
        except:
            pass
        
        # Check for dangerous patterns
        dangerous_patterns = ['system(', 'exec(', 'eval(', '__import__', 'subprocess.']
        for pattern in dangerous_patterns:
            if pattern in script:
                threats['dangerous_patterns'].append(pattern)
        
        return threats
    
    def get_sandbox_parameters(self) -> Dict[str, Any]:
        """
        Get parameters for sandbox environment

        Returns:
            Dict[str, Any]: Parameters for sandbox environment
        """
        return {
            'allowed_modules': list(self.allowed_modules),
            'forbidden_functions': list(self.forbidden_functions)
        }
