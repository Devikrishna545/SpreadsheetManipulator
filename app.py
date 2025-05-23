"""
Spreadsheet Auto-Editor Application
-----------------------------------
A Flask application that allows accountants to edit spreadsheets using natural language commands.
"""

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
        file_path, original_filename = spreadsheet_controller.download_spreadsheet(session_id)
        
        # Preserve original file extension
        original_ext = os.path.splitext(original_filename)[1].lower()
        
        # Schedule cleanup after download
        def cleanup():
            spreadsheet_controller.cleanup_session(session_id)
        
        # Use Flask's g context to store after_response_funcs per request
        if not hasattr(g, 'after_response_funcs'):
            g.after_response_funcs = []
        g.after_response_funcs.append(cleanup)
        
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


if __name__ == '__main__':
    # Add cleanup of expired sessions and files
    from apscheduler.schedulers.background import BackgroundScheduler
    from src.controller.script_manager import ScriptManager
    from src.controller.file_manager import FileManager
    
    def cleanup_expired_resources():
        # Clean up expired sessions
        session_manager.cleanup_expired_sessions()
        
        # Clean up old scripts
        script_manager = ScriptManager(os.path.join('src', 'script'))
        script_manager.cleanup_old_scripts(24)  # Keep scripts for 24 hours
        
        # Clean up uploaded and downloaded files
        file_manager = FileManager(
            upload_dir=app.config['UPLOAD_FOLDER'],
            download_dir=app.config['DOWNLOAD_FOLDER'],
            json_dir=app.config['JSON_FOLDER']
        )
        file_manager.cleanup_files(24)  # Keep files for 24 hours
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(cleanup_expired_resources, 'interval', minutes=30)
    scheduler.start()
    
    app.run(debug=True)
