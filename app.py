"""
Spreadsheet Auto-Editor Application
-----------------------------------
A Flask application that allows accountants to edit spreadsheets using natural language commands.
"""

# TO DO
# =======
# Add keyboard shortcuts for common actions
# Design beautiful modern UI ✅
# Test app with various spreadsheet formats ✅
# Test app with real users
# Add predefined prompts for common tasks
# Add support for user creating custom prompts and storing them
# Add support for tagging rows and columns with pop-up suggestions called using the hash-tag
# Add option to view previous prompts with arrow up/down keys

import os
from flask import Flask, render_template, request, jsonify, send_file, g
from dotenv import load_dotenv
from src.controller.spreadsheet_controller import SpreadsheetController
from src.model.session_manager import SessionManager

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['DOWNLOAD_FOLDER'] = os.path.join('static', 'downloads')
app.config['JSON_FOLDER'] = os.path.join('static', 'json')
app.config['SCRIPT_FOLDER'] = os.path.join('src', 'script')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 'MAX_CONTENT_LENGTH'))
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-dev-key')
app.config['LLM_API_KEY'] = os.getenv('LLM_API_KEY')
app.config['LLM_ENDPOINT'] = os.getenv('LLM_ENDPOINT')
app.config['LLM_MODEL'] = os.getenv('LLM_MODEL', 'gpt-4-turbo')

# Initialize managers
session_manager = SessionManager()
spreadsheet_controller = SpreadsheetController(session_manager)

# Ensure required directories exist
for folder in [app.config['UPLOAD_FOLDER'], app.config['DOWNLOAD_FOLDER'], app.config['JSON_FOLDER'], app.config['SCRIPT_FOLDER']]:
    os.makedirs(folder, exist_ok=True)

@app.route('/')
def index():
    """Render the main application page."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle spreadsheet file uploads."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    try:
        session_id = spreadsheet_controller.upload_spreadsheet(file)
        return jsonify({
            'success': True,
            'sessionId': session_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/view/<session_id>')
def view_spreadsheet(session_id):
    """Get the spreadsheet data for viewing."""
    try:
        spreadsheet_view = spreadsheet_controller.view_spreadsheet(session_id)
        return jsonify(spreadsheet_view)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/process', methods=['POST'])
def process_command():
    """Process a user command through the LLM."""
    data = request.get_json()
    if not data or 'sessionId' not in data or 'command' not in data:
        return jsonify({'error': 'Missing session ID or command'}), 400
    
    session_id = data['sessionId']
    command = data['command']
    
    try:
        spreadsheet_view = spreadsheet_controller.process_command(session_id, command)
        return jsonify(spreadsheet_view)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/undo/<session_id>', methods=['POST'])
def undo_modification(session_id):
    """Undo the last modification."""
    try:
        spreadsheet_view = spreadsheet_controller.undo_modification(session_id)
        return jsonify(spreadsheet_view)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/redo/<session_id>', methods=['POST'])
def redo_modification(session_id):
    """Redo a previously undone modification."""
    try:
        spreadsheet_view = spreadsheet_controller.redo_modification(session_id)
        return jsonify(spreadsheet_view)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/download/<session_id>')
def download_spreadsheet(session_id):
    """Download the modified spreadsheet."""
    try:
        # Get both file_path and original_filename
        file_path, original_filename = spreadsheet_controller.download_spreadsheet(session_id)
        
        # Schedule cleanup after download
        def cleanup():
            spreadsheet_controller.cleanup_session(session_id)
        
        if not hasattr(g, 'after_response_funcs'):
            g.after_response_funcs = []
        g.after_response_funcs.append(cleanup)
        
        # Use original filename for download
        return send_file(
            file_path,
            as_attachment=True,
            download_name=original_filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Register after_response handler
@app.after_request
def after_request(response):
    for func in getattr(g, 'after_response_funcs', []):
        func()
    # No need to clear g.after_response_funcs, as g is per-request
    return response

def cleanup_temp_dirs():
    """
    Delete all files except .gitkeep from /src/script/, /static/uploads, /static/downloads, /static/json
    """
    import glob
    temp_dirs = [
        os.path.join('src', 'script'),
        os.path.join('static', 'uploads'),
        os.path.join('static', 'downloads'),
        os.path.join('static', 'json')
    ]
    for d in temp_dirs:
        for f in glob.glob(os.path.join(d, '*')):
            if os.path.isfile(f) and not f.endswith('.gitkeep'):
                try:
                    os.remove(f)
                except Exception as e:
                    print(f"Warning: Could not delete temp file {f}: {e}")

if __name__ == '__main__':
    # Clean up temp dirs at startup
    cleanup_temp_dirs()
    # Add cleanup of expired sessions and files
    from apscheduler.schedulers.background import BackgroundScheduler

    def cleanup_expired_resources():
        # Clean up expired sessions
        session_manager.cleanup_expired_sessions()
        
        # Clean up old scripts
        from src.controller.script_manager import ScriptManager
        script_manager = ScriptManager(os.path.join('src', 'script'))
        script_manager.cleanup_old_scripts(24)  # Keep scripts for 24 hours

        # Clean up temp dirs while server is running
        cleanup_temp_dirs()

    scheduler = BackgroundScheduler()
    scheduler.add_job(cleanup_expired_resources, 'interval', hours=24)  # Keep dirs for 24 hours
    scheduler.start()
    
    app.run(debug=True)
