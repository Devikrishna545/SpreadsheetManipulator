# AIDN - Artificial Intelligence Data Normalizer

A comprehensive FastAPI-powered application designed for finance professionals and accountants to automatically edit, transform, and manipulate spreadsheets using natural language commands powered by Google Gemini AI and advanced schema transformation capabilities.

**Proprietary Software - Copyright © 2025 HLB Hamt. All Rights Reserved.**

## 🚀 Core Features

### 📊 **AI-Powered Spreadsheet Processing**
- **Natural Language Commands**: Issue commands like "Add a Total column that sums A and B" or "Convert currency to USD"
- **Google Gemini Integration**: Advanced AI script generation with both simple and complex processing modes
- **Smart Script Reuse**: Automatic detection and reuse of previously successful scripts based on semantic similarity
- **Intelligent Error Recovery**: 5-attempt automatic script fixing with fallback to advanced AI methods

### 🔧 **Enhanced Data Processing Engine**
- **Universal File Support**: Excel (.xlsx, .xls), CSV with automatic encoding detection
- **Merged Cell Handling**: Properly processes merged cells, complex headers, and nested data structures
- **Robust Preprocessing**: Removes formatting artifacts, handles multiple encodings, and normalizes data
- **Multi-Sheet Support**: Full workbook navigation with tab-based sheet switching
- **Error Recovery Pipeline**: Multiple fallback methods ensure files always process successfully

### 🎯 **Manual Schema Transformation System**
- **Split View Interface**: Side-by-side view for template-based transformations
- **Pattern Recognition**: Detects constants, sequences, dates, and repeating cycles
- **Mass Data Transformation**: Transform thousands of rows instantly using template patterns
- **No-LLM Operations**: Perform complex transformations without AI dependency
- **Action Plan Generation**: Preview transformation plans before execution

**Supported Transformation Patterns:**
- **Constant Values**: Apply fixed values across columns
- **Sequential Numbers**: Generate numeric sequences with custom increments
- **Date Sequences**: Create date series (daily, weekly, monthly, yearly)
- **Repeating Cycles**: Cycle through predefined value sets
- **Column Operations**: Reorder, rename, and restructure columns
- **Data Type Conversion**: Automatic conversion between string, integer, float, datetime

### 🔐 **Enterprise Security Framework**
- **Comprehensive Security Manager**: Multi-layer script validation and execution protection
- **Session-Based Security**: Individual user session isolation and tracking
- **Security Audit Logging**: Complete audit trail of all security events and violations
- **Terminal Activity Logging**: Full terminal session recording with metadata
- **Script Sandboxing**: Safe execution environment for AI-generated scripts
- **Input Validation**: Comprehensive validation of all user inputs and file uploads

### 📈 **Advanced Management & Analytics**
- **Command Mapping System**: Create reusable mappings between spreadsheets and command sets
- **Token Usage Tracking**: Real-time monitoring of AI token consumption and costs
- **Batch Processing**: Execute multiple commands sequentially with progress tracking
- **Performance Analytics**: Detailed statistics on processing times and success rates
- **Script Performance Metrics**: Track and optimize script execution efficiency

### 🎨 **Modern User Experience**
- **Dark Theme Interface**: Professional, eye-friendly dark mode design
- **Real-time Status Updates**: Live progress indicators and status messages
- **Interactive Spreadsheet Viewer**: Handsontable-powered grid with Excel-like functionality
- **Keyboard Shortcuts**: Comprehensive shortcut system for power users
- **Cell Highlighting**: Visual feedback for modified cells and ranges
- **Undo/Redo System**: Complete modification history with granular control

### 🔄 **Workflow & Integration Features**
- **File Management**: Automatic cleanup, cache management, and download handling
- **Prompt History**: Persistent command history with session management
- **Background Processing**: Non-blocking operations for long-running tasks
- **API-First Design**: RESTful API for integration with other systems
- **Configurable Settings**: Extensive configuration options for all components

## 🏗️ Architecture & Project Structure

### **Technical Stack**
- **Backend**: FastAPI with Uvicorn server
- **AI Engine**: Google Gemini AI (google-generativeai)
- **Data Processing**: Pandas, NumPy, OpenPyXL
- **Security**: Multi-layer validation, session management, audit logging
- **Frontend**: Vanilla JavaScript with Handsontable, Bootstrap
- **File Processing**: Support for Excel, CSV with encoding detection

### **Directory Structure**
```
AIDN/
├── app.py                      # FastAPI application entry point
├── requirements-w.txt          # Windows dependencies
├── requirements-l.txt          # Linux dependencies
├── static/                     # Frontend assets
│   ├── css/                    # Stylesheets (dark theme, components)
│   ├── js/                     # JavaScript modules
│   │   ├── main.js            # Core application logic
│   │   ├── apiService.js      # API communication layer
│   │   ├── spreadsheetHandler.js # Spreadsheet operations
│   │   ├── uiInteractions.js  # UI state management
│   │   └── modalUtils.js      # Modal dialogs and utilities
│   ├── uploads/               # Temporary file storage
│   ├── downloads/             # Generated downloads
│   ├── json/                  # Configuration and cache files
│   └── assets/                # Images, icons, favicon
├── templates/
│   ├── index.html             # Main application interface
│   └── instructions.html      # User documentation
├── src/                       # Core application modules
│   ├── api/
│   │   └── endpoints.py       # FastAPI route definitions
│   ├── controller/            # Business logic controllers
│   │   ├── spreadsheet_controller.py  # Main spreadsheet operations
│   │   ├── security_manager.py        # Security validation
│   │   ├── session_manager.py         # User session handling
│   │   ├── mapping_manager.py         # Command mapping system
│   │   ├── script_manager.py          # AI script management
│   │   ├── script_fixer.py           # Error recovery system
│   │   ├── script_reuser.py          # Script reuse optimization
│   │   ├── script_executor.py        # Safe script execution
│   │   ├── terminal_logger.py        # Terminal activity logging
│   │   ├── security_logger.py        # Security audit logging
│   │   └── file_manager.py          # File operations
│   ├── llm/
│   │   ├── llm_service.py            # Google Gemini integration
│   │   └── token_manager.py          # Token usage tracking
│   ├── model/
│   │   ├── spreadsheet_manager.py    # Data model management
│   │   ├── prompt_history.py         # Command history
│   │   └── modification_history.py   # Change tracking
│   ├── scripts/                      # Generated AI scripts
│   ├── mappings/                     # Command mappings storage
│   └── logs/                         # Application logs
│       ├── security/                 # Security audit logs
│       └── terminal/                 # Terminal session logs
├── data/
│   ├── spreadsheets/                 # Sample data files
│   └── instructions/                 # Documentation and guides
└── design/                           # Architecture diagrams
    ├── class diagram.png
    ├── flowchart diagram.png
    ├── requirements diagram.png
    ├── sequence diagram.png
    └── use case diagram.png
```

### **Key Components**

#### **1. Security Framework**
- **SecurityManager**: Multi-layer script validation
- **SecurityLogger**: Comprehensive audit trail
- **SessionManager**: Isolated user sessions
- **Terminal Logger**: Complete activity recording

#### **2. AI Processing Pipeline**
- **LLMService**: Google Gemini integration with dual processing modes
- **ScriptManager**: AI-generated script lifecycle management
- **ScriptFixer**: 5-attempt error recovery with fallback strategies
- **ScriptReuser**: Semantic similarity-based script optimization
- **TokenManager**: Real-time usage tracking and cost monitoring

#### **3. Data Processing Engine**
- **SpreadsheetController**: Core data manipulation operations
- **FileManager**: Robust file handling with encoding detection
- **MappingManager**: Command-to-spreadsheet relationship management
- **SchemaGenerator**: Template-based transformation system

#### **4. User Interface**
- **Modern Dark Theme**: Professional, accessible design
- **Real-time Updates**: Live status and progress indicators
- **Interactive Grid**: Excel-like spreadsheet experience
- **Modal System**: Context-aware dialogs and confirmations

## 🚀 Quick Start & Installation

### **Prerequisites**
- Python 3.9+ (3.11+ recommended for optimal performance)
- Windows, macOS, or Linux
- 4GB+ RAM recommended for large spreadsheet processing
- Google Gemini API key (for AI features)

### **Installation Steps**

1. **Clone the Repository**
```bash
git clone https://github.com/Devikrishna545/SpreadsheetManipulator.git
cd AIDN
```

2. **Create Virtual Environment**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux  
python -m venv venv
source venv/bin/activate
```

3. **Install Dependencies**
```bash
# Windows
pip install -r requirements-w.txt

# Linux
pip install -r requirements-l.txt
```

4. **Environment Configuration**
Create a `.env` file in the root directory:
```env
# Google Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Application Settings
DEBUG=False
HOST=127.0.0.1
PORT=8000

# Security Settings
SESSION_TIMEOUT=3600
MAX_FILE_SIZE=50MB
ALLOWED_FILE_TYPES=xlsx,xls,csv

# Logging Configuration
LOG_LEVEL=INFO
AUDIT_LOGGING=True
TERMINAL_LOGGING=True
```

5. **Launch Application**
```bash
python app.py
```

### **Development Mode**
For development with auto-reload:
```bash
python app.py --reload --debug
```

### **Access Points**
- **Main Application**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative UI**: http://localhost:8000/redoc

## 💡 Usage Guide

### **Basic Workflow**

1. **Start Session**: Access the application and a secure session will be automatically created
2. **Upload Spreadsheet**: Use the file upload interface to load Excel or CSV files
3. **Natural Language Processing**: Enter commands like:
   - "Add a Total column that sums columns A through D"
   - "Convert all currency values from EUR to USD"
   - "Create a pivot summary by department"
   - "Remove duplicate entries based on email address"
4. **Review Changes**: View modifications in real-time with cell highlighting
5. **Download Results**: Export the processed spreadsheet in your preferred format

### **Advanced Features**

#### **Split View Transformations**
1. Enable split view mode using the split button or `Alt+Shift+S`
2. Edit the right panel to create your desired template structure
3. Use "Transform to Schema" to apply the template to your entire dataset
4. Preview the action plan before confirming transformations

#### **Command Mapping System**
1. Upload command files with predefined instruction sets
2. Create mappings between specific spreadsheets and command files
3. Auto-execute command sequences for recurring tasks
4. Manage and edit existing mappings through the interface

#### **Batch Processing**
1. Upload command files with multiple instructions
2. Process commands sequentially with progress tracking
3. Review results after each command execution
4. Handle errors gracefully with automatic retry mechanisms

### **Keyboard Shortcuts**
- `Alt+U`: Quick file upload
- `Alt+F`: Toggle fullscreen mode
- `Alt+Shift+S`: Enable/disable split view
- `Alt+Shift+T`: Transform to schema
- `Ctrl+Z`: Undo last modification
- `Ctrl+Y`: Redo modification
- `#`: Cell tagger for referencing specific cells in commands

### **Security Best Practices**
- All scripts are validated before execution
- Session isolation prevents cross-user data access
- Comprehensive audit logging tracks all activities
- File uploads are scanned and validated
- Automatic cleanup of temporary files

## 🔧 Development & API Reference

### **Development Environment Setup**

#### **Required Tools**
- Python 3.11+ with pip
- Node.js 16+ (for frontend development)
- Git for version control
- VS Code or PyCharm (recommended IDEs)

#### **Development Dependencies**
```bash
# Install development tools
pip install pytest pytest-cov black flake8 mypy

# Run tests
pytest tests/ -v --cov=src

# Code formatting
black src/ --check
flake8 src/

# Type checking
mypy src/
```

### **API Endpoints Overview**

#### **Session Management**
- `POST /api/session/start` - Initialize new user session
- `POST /api/session/heartbeat` - Maintain session activity
- `POST /api/session/end` - Terminate session

#### **File Operations**
- `POST /upload` - Upload spreadsheet files
- `GET /view/{session_id}` - Retrieve spreadsheet data
- `GET /download/{session_id}` - Download processed files

#### **Processing & Commands**
- `POST /process` - Execute natural language commands
- `POST /undo/{session_id}` - Undo last modification
- `POST /redo/{session_id}` - Redo modification
- `GET /prompt_history/{session_id}` - Get command history

#### **Schema Transformation**
- `POST /capture_schema` - Capture template schema
- `POST /transform_to_schema` - Apply schema transformation
- `POST /validate_schema_compatibility` - Validate transformation

#### **Mapping Management**
- `POST /create_mapping` - Create command mappings
- `GET /mappings` - List all mappings
- `PUT /update_mapping/{mapping_id}` - Update existing mapping
- `DELETE /delete_mapping/{mapping_id}` - Remove mapping

#### **Analytics & Monitoring**
- `GET /script_reuse_stats` - Script performance metrics
- `GET /token_usage` - AI token consumption data
- `GET /security_audit` - Security event logs

### **Configuration Options**

#### **Security Settings**
```python
# src/controller/security_config.py
SECURITY_CONFIG = {
    "max_script_retries": 5,
    "allowed_modules": ["pandas", "numpy", "math", "datetime"],
    "forbidden_functions": ["exec", "eval", "open", "os"],
    "session_timeout": 3600,
    "max_file_size": 52428800,  # 50MB
}
```

#### **LLM Configuration**
```python
# src/llm/llm_service.py
LLM_CONFIG = {
    "model": "gemini-pro",
    "temperature": 0.1,
    "max_tokens": 8192,
    "safety_settings": "high",
    "complex_script_threshold": 100,
}
```

### **Testing Framework**

#### **Unit Tests**
```bash
# Run specific test modules
pytest tests/test_security_manager.py -v
pytest tests/test_spreadsheet_controller.py -v
pytest tests/test_llm_service.py -v

# Run with coverage
pytest --cov=src --cov-report=html
```

#### **Integration Tests**
```bash
# End-to-end testing
pytest tests/integration/ -v

# API endpoint testing
pytest tests/api/ -v
```

### **Performance Optimization**

#### **Caching Strategy**
- Script reuse based on semantic similarity
- Preprocessed spreadsheet caching
- Session-based data persistence
- Token usage optimization

#### **Memory Management**
- Automatic cleanup of temporary files
- Session-based memory isolation
- Efficient data structure usage
- Background processing for large files

### **Security Implementation**

#### **Script Validation Pipeline**
1. **Syntax Analysis**: AST parsing for dangerous constructs
2. **Module Filtering**: Whitelist-based import validation
3. **Function Blocking**: Blacklist dangerous function calls
4. **Sandbox Execution**: Isolated execution environment
5. **Output Validation**: Result verification and sanitization

#### **Audit Logging**
- All user actions logged with timestamps
- Security events tracked and monitored
- Session activities recorded
- File operations audited

### **Deployment Considerations**

#### **Production Setup**
```bash
# Use production WSGI server
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app

# Environment variables for production
export DEBUG=False
export LOG_LEVEL=WARNING
export SESSION_TIMEOUT=1800
```

#### **Docker Deployment**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements-w.txt .
RUN pip install -r requirements-w.txt
COPY . .
EXPOSE 8000
CMD ["python", "app.py", "--host", "0.0.0.0"]
```

### **Monitoring & Observability**

#### **Health Checks**
- Application health endpoint: `/health`
- Database connectivity monitoring
- API response time tracking
- Resource usage monitoring

#### **Logging Configuration**
```python
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detailed": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        }
    },
    "handlers": {
        "file": {
            "class": "logging.FileHandler",
            "filename": "logs/application.log",
            "formatter": "detailed"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["file"]
    }
}
```

## 🤝 Contributing & Support

### **Contributing Guidelines**

**Note: AIDN is proprietary software owned by HLB Hamt. External contributions are not accepted.**

For HLB Hamt employees and authorized developers:

#### **Internal Development Process**
1. Create a feature branch from the main development branch
2. Follow HLB Hamt coding standards and security guidelines
3. Ensure all changes comply with company policies
4. Submit for internal code review through approved channels
5. Obtain security clearance for sensitive modifications

#### **Development Standards**
- Follow HLB Hamt coding standards and best practices
- All code must pass security review before deployment
- Comprehensive testing required for all features
- Documentation updates must be approved by technical writers
- Security-related changes require additional approval from IT Security

#### **Code Review Process**
- All changes require review by HLB Hamt technical leads
- Security-related changes require IT Security approval
- Performance impacts must be documented and approved
- Breaking changes require change management approval

### **Support & Reporting**

#### **Internal Support**
For HLB Hamt employees:
- **IT Help Desk**: Internal support tickets
- **Technical Team**: Direct consultation for development issues
- **Security Team**: Security-related concerns and incidents

### **Roadmap & Future Plans**

#### **Upcoming Features**
- **Enhanced AI Models**: Support for multiple LLM providers
- **Advanced Analytics**: Detailed usage and performance metrics
- **Collaboration Tools**: Multi-user editing and sharing
- **API Integrations**: Connect with popular finance tools
- **Mobile Interface**: Responsive design for tablets and phones

#### **Performance Improvements**
- **Streaming Processing**: Handle extremely large files efficiently
- **Distributed Processing**: Scale across multiple servers
- **Caching Optimization**: Improved response times
- **Memory Efficiency**: Reduced resource consumption

#### **Security Enhancements**
- **Advanced Threat Detection**: ML-based security monitoring
- **Zero-Trust Architecture**: Enhanced access controls
- **Compliance Features**: SOX, GDPR, and other regulatory support
- **Encryption**: End-to-end data protection

## 📄 License & Legal

### **Proprietary License**
**AIDN (Artificial Intelligence Data Normalizer)** is proprietary software owned and developed by **HLB Hamt**.

**Copyright © 2025 HLB Hamt. All Rights Reserved.**

This software and its documentation are the exclusive property of HLB Hamt. No part of this software may be reproduced, distributed, or transmitted in any form or by any means, including photocopying, recording, or other electronic or mechanical methods, without the prior written permission of HLB Hamt, except in the case of brief quotations embodied in critical reviews and certain other noncommercial uses permitted by copyright law.

### **Usage Rights**
- This software is licensed for use by authorized HLB Hamt personnel and approved clients only
- Redistribution, modification, or reverse engineering is strictly prohibited
- Commercial use outside of HLB Hamt operations requires explicit written authorization
- All user data processed through AIDN remains confidential and is subject to HLB Hamt privacy policies

### **Restrictions**
- Source code access is limited to authorized developers
- Third-party integration requires prior approval
- Security vulnerabilities must be reported immediately to HLB Hamt IT Security
- Unauthorized access attempts will be prosecuted to the full extent of the law

### **Third-Party Libraries**
- **FastAPI**: Modern, fast web framework for building APIs
- **Google Gemini**: Advanced AI language model
- **Pandas**: Powerful data manipulation and analysis library
- **Handsontable**: Feature-rich data grid component
- **Bootstrap**: Responsive CSS framework

### **Privacy & Data Handling**
- User data is processed in accordance with HLB Hamt data protection policies
- Session data is automatically cleaned up after use per company security protocols
- File uploads are temporarily stored and automatically deleted following HLB Hamt retention policies
- AI processing is performed via secure API calls to Google Gemini with HLB Hamt approved configurations
- All data processing complies with applicable financial regulations and HLB Hamt compliance standards

### **Security & Compliance**
AIDN implements enterprise-grade security measures in compliance with HLB Hamt standards:
- Multi-layer authentication and authorization
- Comprehensive audit logging for regulatory compliance
- Data encryption in transit and at rest
- Regular security assessments and penetration testing
- SOX compliance for financial data processing
- GDPR compliance for data protection

---

## 🌟 Acknowledgments

**AIDN Development Team - HLB Hamt**

Internal development acknowledgments:
- HLB Hamt IT Development Team for architecture and implementation
- HLB Hamt Security Team for comprehensive security framework
- Finance Department for requirements and user acceptance testing
- Quality Assurance Team for rigorous testing and validation

External technology partners:
- Google for providing the Gemini AI platform
- The FastAPI development community for the excellent web framework
- The pandas development team for robust data processing capabilities
- Open-source library maintainers for foundational components

---

**AIDN - Artificial Intelligence Data Normalizer**
*Transforming finance and accounting workflows through intelligent automation.*

**Copyright © 2025 HLB Hamt. All Rights Reserved.**

For internal support or technical assistance, please contact the HLB Hamt IT Department through approved channels.
