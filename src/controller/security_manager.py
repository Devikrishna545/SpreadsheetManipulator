"""Validate scripts for security before execution with protections and logging."""

import ast, hashlib, logging, re, time
from typing import Any, Dict, Optional

class SecurityManager:
    """Manage security for script execution with protections and session logging."""
    
    def __init__(self):
        """Initialize the security manager configuration."""
        # Allowed imports in generated scripts (restrictive set)
        self.allowed_modules = {
            'pandas', 'pd',
            'numpy', 'np',
            'math',
            're',
            'datetime',
            'collections',
        }

        # Forbidden functions/attributes (unique, consolidated)
        self.forbidden_functions = {
            'open', 'file', 'os.', 'system', 'subprocess',
            'socket', 'requests', 'urllib', 'http', 'httplib', 'urllib2',
            'process', 'fork', 'popen', 'call', 'run',
            'sys', 'platform', 'getpass', 'environ',
            'shell', 'bash', 'sh', 'cmd', 'powershell', '`',
            '__import__', 'importlib', 'reload', 'globals', 'locals',
            'pickle', 'marshal', 'shelve', 'compile', 'memoryview',
            'setattr', 'getattr', 'hasattr', 'delattr',
            'exec', 'eval',
        }

        # Dangerous regex patterns to block
        self.dangerous_patterns = [
            r'__.*__',
            r'\bclass\s+\w+',
            r'\bdef\s+\w+',
            r'\bimport\s+\w+',
            r'\bfrom\s+\w+\s+import',
            r'\btry\s*:',
            r'\bexcept\s*:',
            r'\bfinally\s*:',
            r'\bwith\s+\w+',
            r'\byield\s+',
            r'\bglobal\s+\w+',
            r'\bnonlocal\s+\w+',
        ]

        # Tracking and limits
        self.script_executions: Dict[str, list] = {}
        self.max_scripts_per_minute = 10
        self.executed_script_hashes: set[str] = set()
        self.max_script_size = 3000  # bytes
        self.max_lines = 30

    def log_rejection(self, script: str, reason: str,
                      session_id: Optional[str] = None, script_name: Optional[str] = None) -> None:
        """Log a rejected script and reason; emit session event when available."""
        print(f"SecurityManager: Script rejected. Reason: {reason}")
        logging.warning(f"SecurityManager: Script rejected. Reason: {reason}")
        
        if script_name:
            print(f"Rejected script: {script_name}")
            logging.warning(f"Rejected script: {script_name}")
        else:
            script_hash = hashlib.sha256(script.encode()).hexdigest()
            logging.warning(f"Rejected script hash: {script_hash}")
        
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
                        'script_name': script_name or 'unknown',
                        'script_preview': script[:200] + '...' if len(script) > 200 else script,
                        'script_length': len(script),
                        'validation_result': 'REJECTED',
                        'rejection_reason': reason,
                        'forbidden_content': self._identify_threats(script),
                        'script_hash': hashlib.sha256(script.encode()).hexdigest()
                    },
                    "SecurityManager"
                )
            except ImportError:
                pass

    def _is_exact_word_match(self, text: str, forbidden_word: str) -> bool:
        """Return True if forbidden_word appears as a whole word in text (case-insensitive)."""
        pattern = r'\b' + re.escape(forbidden_word) + r'\b'
        return bool(re.search(pattern, text, re.IGNORECASE))
    
    def _check_forbidden_functions(self, script: str) -> tuple[bool, str]:
        """Check forbidden functions using whole-word matching to avoid false positives."""
        for forbidden in self.forbidden_functions:
            if '.' in forbidden:
                if forbidden in script:
                    return False, forbidden
            else:
                if self._is_exact_word_match(script, forbidden):
                    return False, forbidden
        
        return True, ""

    def _check_rate_limit(self, client_ip: str) -> bool:
        """Return True if client_ip is within per-minute rate limits."""
        current_time = time.time()
        minute_ago = current_time - 60
        
        if client_ip not in self.script_executions:
            self.script_executions[client_ip] = []
        
        self.script_executions[client_ip] = [
            timestamp for timestamp in self.script_executions[client_ip]
            if timestamp > minute_ago
        ]
        
        if len(self.script_executions[client_ip]) >= self.max_scripts_per_minute:
            return False
        
        self.script_executions[client_ip].append(current_time)
        return True

    def validate_script(self, script: str, session_id: Optional[str] = None,
                        client_ip: Optional[str] = None, script_name: Optional[str] = None) -> bool:
        """Validate a script with size/line checks, content scanning, and AST analysis."""
        
        if client_ip and not self._check_rate_limit(client_ip):
            self.log_rejection(script, f"Rate limit exceeded for IP: {client_ip}", session_id, script_name)
            return False
        
        if len(script) > self.max_script_size:
            self.log_rejection(script, f"Script too large: {len(script)} bytes", session_id, script_name)
            return False
        
        lines = script.split('\n')
        if len(lines) > self.max_lines:
            self.log_rejection(script, f"Too many lines: {len(lines)}", session_id, script_name)
            return False
        
        script_hash = hashlib.sha256(script.encode()).hexdigest()
        if script_hash in self.executed_script_hashes:
            print(f"Duplicate script execution attempt: {script_hash}")
        else:
            self.executed_script_hashes.add(script_hash)
            if len(self.executed_script_hashes) > 1000:
                self.executed_script_hashes = set(list(self.executed_script_hashes)[100:])
        
        try:
            tree = ast.parse(script)
        except SyntaxError as e:
            reason = f"SyntaxError while parsing script: {str(e)}"
            self.log_rejection(script, reason, session_id, script_name)
            return False
            
        if "LLM_ERROR" in script and "df['LLM_ERROR']" in script and len(script.split('\n')) <= 5:
            success_reason = "Error handling script allowed"
            self._log_validation_success(script, success_reason, session_id, script_name)
            return True
        
        for pattern in self.dangerous_patterns:
            if re.search(pattern, script, re.IGNORECASE):
                self.log_rejection(script, f"Dangerous pattern '{pattern}' found in script.", session_id, script_name)
                return False
        
        is_safe, forbidden_word = self._check_forbidden_functions(script)
        if not is_safe:
            self.log_rejection(script, f"Forbidden keyword '{forbidden_word}' found in script.", session_id, script_name)
            return False
        
        try:
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        if name.name not in self.allowed_modules:
                            reason = f"Forbidden import '{name.name}' found in script."
                            self.log_rejection(script, reason, session_id, script_name)
                            return False
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module not in self.allowed_modules:
                        reason = f"Forbidden import from '{node.module}' found in script."
                        self.log_rejection(script, reason, session_id, script_name)
                        return False
                    
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id == '__import__':
                        reason = "__import__ call found in script."
                        self.log_rejection(script, reason, session_id, script_name)
                        return False
                
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id in ['exec', 'eval', 'compile']:
                        reason = f"Forbidden call '{node.func.id}' found in script."
                        self.log_rejection(script, reason, session_id, script_name)
                        return False
                
                elif isinstance(node, ast.Attribute):
                    if node.attr.startswith('__') and node.attr.endswith('__'):
                        reason = f"Dangerous attribute access '{node.attr}' found in script."
                        self.log_rejection(script, reason, session_id, script_name)
                        return False
                
                elif isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    reason = f"Class/function definition found in script."
                    self.log_rejection(script, reason, session_id, script_name)
                    return False
                
                elif isinstance(node, ast.Try):
                    reason = "Try/except block found in script."
                    self.log_rejection(script, reason, session_id, script_name)
                    return False
                
                elif isinstance(node, ast.With):
                    reason = "With statement found in script."
                    self.log_rejection(script, reason, session_id, script_name)
                    return False
                
                elif isinstance(node, (ast.Global, ast.Nonlocal)):
                    reason = "Global/nonlocal statement found in script."
                    self.log_rejection(script, reason, session_id, script_name)
                    return False
            
            success_reason = "Script passed security validation"
            self._log_validation_success(script, success_reason, session_id, script_name)
            return True
            
        except Exception as e:
            reason = f"Error analyzing script: {e}"
            self.log_rejection(script, reason, session_id, script_name)
            return False
    
    def _log_validation_success(self, script: str, reason: str,
                                session_id: Optional[str] = None, script_name: Optional[str] = None) -> None:
        """Log successful script validation with details and optional session event."""
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
                        'script_name': script_name or 'unknown',
                        'script_preview': script[:200] + '...' if len(script) > 200 else script,
                        'script_length': len(script),
                        'validation_result': 'APPROVED',
                        'approval_reason': reason,
                        'allowed_modules': list(self.allowed_modules),
                        'script_hash': hashlib.sha256(script.encode()).hexdigest()
                    },
                    "SecurityManager"
                )
            except ImportError:
                pass
    
    def _identify_threats(self, script: str) -> Dict[str, list]:
        """Identify threats in a script for detailed logging (forbidden functions/imports/patterns)."""
        threats = {
            'forbidden_functions': [],
            'forbidden_imports': [],
            'dangerous_patterns': []
        }
        
        for forbidden in self.forbidden_functions:
            if '.' in forbidden:
                if forbidden in script:
                    threats['forbidden_functions'].append(forbidden)
            else:
                if self._is_exact_word_match(script, forbidden):
                    threats['forbidden_functions'].append(forbidden)
        
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
        except Exception:
            pass
        
        for pattern in self.dangerous_patterns:
            if re.search(pattern, script, re.IGNORECASE):
                threats['dangerous_patterns'].append(pattern)
        
        return threats
    
    def get_sandbox_parameters(self) -> Dict[str, Any]:
        """Return parameters for the sandbox environment."""
        return {
            'allowed_modules': list(self.allowed_modules),
            'forbidden_functions': list(self.forbidden_functions),
            'dangerous_patterns': self.dangerous_patterns,
            'max_script_size': self.max_script_size,
            'max_lines': self.max_lines,
            'max_scripts_per_minute': self.max_scripts_per_minute
        }
    
    def get_security_stats(self) -> Dict[str, Any]:
        """Return high-level security statistics."""
        return {
            'executed_scripts_count': len(self.executed_script_hashes),
            'tracked_ips': len(self.script_executions),
            'rate_limited_ips': sum(1 for executions in self.script_executions.values() 
                                  if len(executions) >= self.max_scripts_per_minute),
            'allowed_modules_count': len(self.allowed_modules),
            'forbidden_functions_count': len(self.forbidden_functions),
            'dangerous_patterns_count': len(self.dangerous_patterns)
        }
    
    def cleanup_old_data(self) -> None:
        """Cleanup old tracking data to prevent memory growth."""
        current_time = time.time()
        minute_ago = current_time - 60
        
        for ip in list(self.script_executions.keys()):
            self.script_executions[ip] = [
                timestamp for timestamp in self.script_executions[ip]
                if timestamp > minute_ago
            ]
            
            if not self.script_executions[ip]:
                del self.script_executions[ip]
