"""
Security Manager module
--------------------
Validates scripts for security before execution
"""

import ast
import logging
from typing import Dict, Any


class SecurityManager:
    """
    Manages security for script execution
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
            'os',      # <--- add if needed
            'sys',      # <--- add if needed   
        }
        
        # Functions/attributes that are forbidden
        self.forbidden_functions = {
            # # File system operations
            # 'open', 'file', 'os.', 'system', 'subprocess', 'exec', 'eval',
            # # Network operations
            # 'socket', 'requests', 'urllib', 'http', 
            # # Process operations
            # 'process', 'fork', 
            # # System info
            # 'sys', 'platform', 'getpass',
            # # Shell access
            # 'shell', 'bash', 'sh', 'cmd', '`', 
            # # Module operations
            # '__import__', 'importlib', 'reload', 'globals', 'locals',
            # # Other dangerous operations
            # 'pickle', 'marshal', 'shelve'
        }
    
    def log_rejection(self, script: str, reason: str):
        """
        Log the rejected script and the reason for rejection
        Args:
            script: The rejected script
            reason: The reason for rejection
        """
        logging.warning(f"SecurityManager: Script rejected. Reason: {reason}")
        logging.warning(f"Rejected script:\n{script}")

    def validate_script(self, script: str) -> bool:
        """
        Validate a script for security concerns

        Args:
            script: The Python script to validate

        Returns:
            bool: True if the script passes security validation, False otherwise
        """
        # Check for basic syntax issues first
        try:
            ast.parse(script)
        except SyntaxError as e:
            self.log_rejection(script, f"SyntaxError while parsing script: {str(e)}")
            return False
            
        # Allow error handling scripts that just add an error column
        if "LLM_ERROR" in script and "df['LLM_ERROR']" in script and len(script.split('\n')) <= 5:
            return True
        
        # Basic checks - forbidden functions
        for forbidden in self.forbidden_functions:
            if forbidden in script:
                self.log_rejection(script, f"Forbidden keyword '{forbidden}' found in script.")
                return False
        
        # Use AST to analyze the script more thoroughly
        try:
            tree = ast.parse(script)
            
            # Check imports
            for node in ast.walk(tree):
                # Check for import statements
                if isinstance(node, ast.Import):
                    for name in node.names:
                        if name.name not in self.allowed_modules:
                            self.log_rejection(script, f"Forbidden import '{name.name}' found in script.")
                            return False
                
                # Check for import from statements
                elif isinstance(node, ast.ImportFrom):
                    if node.module not in self.allowed_modules:
                        self.log_rejection(script, f"Forbidden import from '{node.module}' found in script.")
                        return False
                    
                # Check for calls to __import__
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id == '__import__':
                        self.log_rejection(script, "__import__ call found in script.")
                        return False
                
                # Check for exec or eval calls
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id in ['exec', 'eval']:
                        self.log_rejection(script, f"Forbidden call '{node.func.id}' found in script.")
                        return False
            
            return True
            
        except SyntaxError as e:
            self.log_rejection(script, f"SyntaxError while parsing script: {e}")
            return False
    
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
