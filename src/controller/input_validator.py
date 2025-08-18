"""
Input Validator module
--------------------
Comprehensive input validation and sanitization for the finance application
"""

import re
import os
import magic
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import pandas as pd
import zipfile
import logging

# Configure logging
validator_logger = logging.getLogger("input_validator")

class InputValidator:
    """
    Comprehensive input validation for finance application
    """
    
    def __init__(self):
        """Initialize the input validator"""
        
        # File validation settings
        self.max_file_sizes = {
            'xlsx': 50 * 1024 * 1024,    # 50MB for Excel files
            'xls': 50 * 1024 * 1024,     # 50MB for Excel files
            'csv': 10 * 1024 * 1024,     # 10MB for CSV files
            'txt': 1 * 1024 * 1024,      # 1MB for text files
        }
        
        self.allowed_extensions = {'xlsx', 'xls', 'csv', 'txt'}
        
        self.allowed_mime_types = {
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
            'application/vnd.ms-excel',                                          # .xls
            'text/csv',                                                          # .csv
            'text/plain',                                                        # .txt
            'application/csv',                                                   # .csv (alternative)
        }
        
        # Dangerous file signatures (magic bytes)
        self.dangerous_signatures = {
            b'\x4d\x5a': 'Executable file',           # PE executable
            b'\x7f\x45\x4c\x46': 'ELF executable',   # Linux executable
            b'#!/bin/': 'Script file',                # Shell script
            b'#!/usr/bin/': 'Script file',            # Shell script
            b'<?php': 'PHP script',                   # PHP script
            b'<script': 'JavaScript/HTML',            # Script content
            b'javascript:': 'JavaScript URL',         # JavaScript URL
            b'vbscript:': 'VBScript',                 # VBScript
        }
        
        # SQL injection patterns
        self.sql_injection_patterns = [
            r'\b(select|insert|update|delete|drop|create|alter|exec|execute)\b',
            r'\b(union|having|group by|order by)\b',
            r'(\-\-|\#|\/\*|\*\/)',
            r'(\bor\b|\band\b)\s+\w+\s*=\s*\w+',
            r'\b\w+\s*=\s*\w+\s+(or|and)\s+',
            r'[\'"]\s*(or|and)\s+[\'"]\w+[\'"]\s*=\s*[\'"]\w+[\'"]',
        ]
        
        # XSS patterns
        self.xss_patterns = [
            r'<script[\s\S]*?>[\s\S]*?</script>',
            r'javascript\s*:',
            r'vbscript\s*:',
            r'on\w+\s*=',
            r'<iframe[\s\S]*?>',
            r'<object[\s\S]*?>',
            r'<embed[\s\S]*?>',
            r'<link[\s\S]*?>',
            r'<meta[\s\S]*?>',
        ]
        
        # Path traversal patterns
        self.path_traversal_patterns = [
            r'\.\./+',
            r'\.\.\\+',
            r'/\.\./+',
            r'\\\.\./+',
            r'\.\.%2f',
            r'\.\.%5c',
            r'%2e%2e%2f',
            r'%2e%2e%5c',
        ]
        
        # Command injection patterns
        self.command_injection_patterns = [
            r'[;&|`\$\(\)\{\}]',
            r'\\x[0-9a-fA-F]{2}',
            r'%[0-9a-fA-F]{2}',
            r'\b(cat|ls|dir|type|copy|move|del|rm|mkdir|rmdir)\b',
            r'\b(curl|wget|nc|netcat|telnet|ssh)\b',
            r'\b(python|perl|ruby|bash|sh|cmd|powershell)\b',
        ]

    def validate_file_upload(self, file_path: str, original_filename: str, file_content: bytes) -> Dict[str, Any]:
        """
        Comprehensive file upload validation
        
        Args:
            file_path: Path to the uploaded file
            original_filename: Original filename from the client
            file_content: File content as bytes
            
        Returns:
            Dict containing validation results
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'file_info': {}
        }
        
        try:
            # 1. Filename validation
            filename_validation = self.validate_filename(original_filename)
            if not filename_validation['is_valid']:
                validation_result['is_valid'] = False
                validation_result['errors'].extend(filename_validation['errors'])
            
            # 2. File size validation
            file_size = len(file_content)
            file_extension = self.get_file_extension(original_filename)
            
            max_size = self.max_file_sizes.get(file_extension, 10 * 1024 * 1024)
            if file_size > max_size:
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"File size ({file_size} bytes) exceeds maximum allowed ({max_size} bytes)")
            
            # 3. File signature validation
            signature_validation = self.validate_file_signature(file_content, file_extension)
            if not signature_validation['is_valid']:
                validation_result['is_valid'] = False
                validation_result['errors'].extend(signature_validation['errors'])
            
            # 4. MIME type validation
            try:
                detected_mime = magic.from_buffer(file_content, mime=True)
                if detected_mime not in self.allowed_mime_types:
                    validation_result['warnings'].append(f"Detected MIME type '{detected_mime}' not in allowed list")
            except:
                validation_result['warnings'].append("Could not detect MIME type")
            
            # 5. Content validation based on file type
            if file_extension in ['xlsx', 'xls']:
                content_validation = self.validate_excel_content(file_content)
            elif file_extension == 'csv':
                content_validation = self.validate_csv_content(file_content)
            elif file_extension == 'txt':
                content_validation = self.validate_text_content(file_content)
            else:
                content_validation = {'is_valid': False, 'errors': ['Unsupported file type']}
            
            if not content_validation['is_valid']:
                validation_result['is_valid'] = False
                validation_result['errors'].extend(content_validation['errors'])
            
            # 6. Malware-like pattern detection
            malware_check = self.check_malware_patterns(file_content)
            if not malware_check['is_valid']:
                validation_result['is_valid'] = False
                validation_result['errors'].extend(malware_check['errors'])
            
            # Store file info
            validation_result['file_info'] = {
                'size': file_size,
                'extension': file_extension,
                'detected_mime': detected_mime if 'detected_mime' in locals() else 'unknown',
                'hash_sha256': hashlib.sha256(file_content).hexdigest()
            }
            
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")
            validator_logger.error(f"File validation error: {str(e)}")
        
        return validation_result

    def validate_filename(self, filename: str) -> Dict[str, Any]:
        """
        Validate filename for security issues
        """
        result = {'is_valid': True, 'errors': []}
        
        # Check for null bytes
        if '\x00' in filename:
            result['is_valid'] = False
            result['errors'].append("Filename contains null bytes")
        
        # Check for path traversal
        for pattern in self.path_traversal_patterns:
            if re.search(pattern, filename, re.IGNORECASE):
                result['is_valid'] = False
                result['errors'].append("Filename contains path traversal sequences")
                break
        
        # Check for dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\n', '\r']
        for char in dangerous_chars:
            if char in filename:
                result['is_valid'] = False
                result['errors'].append(f"Filename contains dangerous character: {char}")
        
        # Check filename length
        if len(filename) > 255:
            result['is_valid'] = False
            result['errors'].append("Filename too long")
        
        # Check for reserved names (Windows)
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
        base_name = os.path.splitext(filename)[0].upper()
        if base_name in reserved_names:
            result['is_valid'] = False
            result['errors'].append("Filename uses reserved system name")
        
        return result

    def get_file_extension(self, filename: str) -> str:
        """
        Get file extension safely
        """
        return os.path.splitext(filename.lower())[1][1:]  # Remove the dot

    def validate_file_signature(self, file_content: bytes, expected_extension: str) -> Dict[str, Any]:
        """
        Validate file signature matches expected type
        """
        result = {'is_valid': True, 'errors': []}
        
        # Check for dangerous signatures
        for signature, description in self.dangerous_signatures.items():
            if file_content.startswith(signature):
                result['is_valid'] = False
                result['errors'].append(f"File contains dangerous signature: {description}")
        
        # Check specific file type signatures
        if expected_extension == 'xlsx':
            # XLSX files are ZIP files with specific structure
            if not file_content.startswith(b'PK'):
                result['is_valid'] = False
                result['errors'].append("Invalid XLSX file signature")
        elif expected_extension == 'xls':
            # XLS files have specific OLE signatures
            if not (file_content.startswith(b'\xd0\xcf\x11\xe0') or file_content.startswith(b'\x09\x08')):
                result['is_valid'] = False
                result['errors'].append("Invalid XLS file signature")
        elif expected_extension == 'csv':
            # CSV should be text-based
            try:
                file_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    file_content.decode('latin-1')
                except UnicodeDecodeError:
                    result['is_valid'] = False
                    result['errors'].append("CSV file contains invalid character encoding")
        
        return result

    def validate_excel_content(self, file_content: bytes) -> Dict[str, Any]:
        """
        Validate Excel file content
        """
        result = {'is_valid': True, 'errors': []}
        
        try:
            # Check if it's a valid ZIP file (XLSX)
            if file_content.startswith(b'PK'):
                # Validate ZIP structure without extracting
                try:
                    import io
                    zip_buffer = io.BytesIO(file_content)
                    with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
                        # Check for required XLSX files
                        required_files = ['_rels/.rels', 'xl/workbook.xml']
                        file_list = zip_file.namelist()
                        
                        for required_file in required_files:
                            if required_file not in file_list:
                                result['is_valid'] = False
                                result['errors'].append(f"Invalid XLSX structure: missing {required_file}")
                        
                        # Check for suspicious files in ZIP
                        for file_name in file_list:
                            if file_name.endswith(('.exe', '.bat', '.cmd', '.scr', '.vbs', '.js')):
                                result['is_valid'] = False
                                result['errors'].append(f"Excel file contains suspicious file: {file_name}")
                
                except zipfile.BadZipFile:
                    result['is_valid'] = False
                    result['errors'].append("Corrupted Excel file")
            
            # Additional checks for macros and external references
            content_str = str(file_content)
            if 'vbaProject' in content_str:
                result['warnings'] = result.get('warnings', [])
                result['warnings'].append("Excel file may contain macros")
            
        except Exception as e:
            result['is_valid'] = False
            result['errors'].append(f"Excel validation error: {str(e)}")
        
        return result

    def validate_csv_content(self, file_content: bytes) -> Dict[str, Any]:
        """
        Validate CSV file content
        """
        result = {'is_valid': True, 'errors': []}
        
        try:
            # Decode content
            try:
                content_str = file_content.decode('utf-8')
            except UnicodeDecodeError:
                content_str = file_content.decode('latin-1')
            
            # Check for basic CSV structure
            lines = content_str.split('\n')
            if len(lines) < 1:
                result['is_valid'] = False
                result['errors'].append("Empty CSV file")
                return result
            
            # Check for suspicious content in CSV
            for pattern in self.xss_patterns + self.command_injection_patterns:
                if re.search(pattern, content_str, re.IGNORECASE):
                    result['is_valid'] = False
                    result['errors'].append("CSV contains suspicious content")
                    break
            
            # Try to parse with pandas for additional validation
            try:
                import io
                csv_buffer = io.StringIO(content_str)
                df = pd.read_csv(csv_buffer, nrows=100)  # Only read first 100 rows for validation
                
                # Check for reasonable column count
                if len(df.columns) > 1000:
                    result['is_valid'] = False
                    result['errors'].append("CSV has too many columns")
                
            except Exception as e:
                result['is_valid'] = False
                result['errors'].append(f"Invalid CSV format: {str(e)}")
        
        except Exception as e:
            result['is_valid'] = False
            result['errors'].append(f"CSV validation error: {str(e)}")
        
        return result

    def validate_text_content(self, file_content: bytes) -> Dict[str, Any]:
        """
        Validate text file content
        """
        result = {'is_valid': True, 'errors': []}
        
        try:
            # Decode content
            try:
                content_str = file_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    content_str = file_content.decode('latin-1')
                except UnicodeDecodeError:
                    result['is_valid'] = False
                    result['errors'].append("Text file has invalid encoding")
                    return result
            
            # Check for malicious patterns
            for pattern in self.xss_patterns + self.command_injection_patterns + self.sql_injection_patterns:
                if re.search(pattern, content_str, re.IGNORECASE):
                    result['is_valid'] = False
                    result['errors'].append("Text file contains suspicious content")
                    break
            
            # Check line count (prevent DoS)
            lines = content_str.split('\n')
            if len(lines) > 100000:  # 100k lines max
                result['is_valid'] = False
                result['errors'].append("Text file has too many lines")
        
        except Exception as e:
            result['is_valid'] = False
            result['errors'].append(f"Text validation error: {str(e)}")
        
        return result

    def check_malware_patterns(self, file_content: bytes) -> Dict[str, Any]:
        """
        Check for malware-like patterns in file content
        """
        result = {'is_valid': True, 'errors': []}
        
        # Convert to string for pattern matching
        try:
            content_str = str(file_content)
            
            # Check for common malware strings
            malware_patterns = [
                'CreateObject',
                'WScript.Shell',
                'Shell.Application',
                'ActiveXObject',
                'Microsoft.XMLHTTP',
                'document.write',
                'eval(',
                'unescape(',
                'String.fromCharCode',
            ]
            
            for pattern in malware_patterns:
                if pattern in content_str:
                    result['is_valid'] = False
                    result['errors'].append(f"File contains suspicious pattern: {pattern}")
                    break
                    
        except Exception as e:
            validator_logger.warning(f"Malware pattern check error: {str(e)}")
        
        return result

    def validate_text_input(self, input_text: str, input_type: str = "general") -> Dict[str, Any]:
        """
        Validate text input for security threats
        """
        result = {'is_valid': True, 'errors': [], 'warnings': []}
        
        if not input_text:
            return result
        
        # Check length
        max_lengths = {
            'general': 10000,
            'command': 1000,
            'filename': 255,
            'session_id': 100
        }
        
        max_length = max_lengths.get(input_type, 10000)
        if len(input_text) > max_length:
            result['is_valid'] = False
            result['errors'].append(f"Input too long (max {max_length} characters)")
        
        # Check for null bytes
        if '\x00' in input_text:
            result['is_valid'] = False
            result['errors'].append("Input contains null bytes")
        
        # Check for SQL injection
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, input_text, re.IGNORECASE):
                result['is_valid'] = False
                result['errors'].append("Input contains potential SQL injection")
                break
        
        # Check for XSS
        for pattern in self.xss_patterns:
            if re.search(pattern, input_text, re.IGNORECASE):
                result['is_valid'] = False
                result['errors'].append("Input contains potential XSS")
                break
        
        # Check for command injection
        for pattern in self.command_injection_patterns:
            if re.search(pattern, input_text, re.IGNORECASE):
                result['is_valid'] = False
                result['errors'].append("Input contains potential command injection")
                break
        
        # Check for path traversal
        for pattern in self.path_traversal_patterns:
            if re.search(pattern, input_text, re.IGNORECASE):
                result['is_valid'] = False
                result['errors'].append("Input contains path traversal attempt")
                break
        
        return result

    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to prevent security issues
        """
        # Remove path components
        filename = os.path.basename(filename)
        
        # Remove dangerous characters
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename)
        
        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255-len(ext)] + ext
        
        # Ensure it's not empty
        if not filename or filename == '.':
            filename = 'unnamed_file'
        
        return filename

    def sanitize_text_input(self, input_text: str) -> str:
        """
        Sanitize text input
        """
        if not input_text:
            return ""
        
        # Remove null bytes
        input_text = input_text.replace('\x00', '')
        
        # Remove dangerous HTML/script tags
        input_text = re.sub(r'<script[\s\S]*?>[\s\S]*?</script>', '', input_text, flags=re.IGNORECASE)
        input_text = re.sub(r'<[^>]*>', '', input_text)
        
        # Remove dangerous JavaScript
        input_text = re.sub(r'javascript\s*:', '', input_text, flags=re.IGNORECASE)
        input_text = re.sub(r'vbscript\s*:', '', input_text, flags=re.IGNORECASE)
        
        return input_text.strip()
