"""
Spreadsheet Auto-Editor Application
-----------------------------------
A Flask application that allows accountants to edit spreadsheets using natural language commands.
"""

# TO DO
# =======
# Add keyboard shortcuts for common actions ✅
# Design beautiful modern UI ✅
# Test app with various spreadsheet formats ✅
# Test app with real users
# Add predefined prompts for common tasks
# Make the "Ready" text to have a square border with rounded edges around it to match the design of the rest of the edges and borders of other elements within the app
# Shift the "Ready" text to the left a little, to mathch the gap between the right edge of the page and the right edge of the "AI Command Interface" and the "Spreadsheet Data" sections
# Change the icon of the "Auto Editor" text, to be a circular spinning gear icon, not a spreadsheet icon
# Centralise the "Auto Editor" text and its icon in the header bar area
# Add favicon
<<<<<<< Updated upstream
# Add command for entering a new command (CTRL+I) 🔁
# Add keyboard support for viewing saved prompts (CTRL+SHIFT+P) 🔁
# Add keyboard shortcuts for saving prompts (CTRL+SHIFT+S) 🔁
# Add a save button to save current text in input text box within a prompt file (static/assets/prompts/prompts.txt) ✅
# Add a delete button to remove saved prompts from within the prompt modal (static/assets/prompts/prompts.txt) 🔁
# Add escape to remove focus from input field ✅
# Increase input text box height to be above save and view prompts buttons 🔁
# Increase the background blur percentage of the view prompts modal to 70% 🔁
=======
# Add footer with copyright information
>>>>>>> Stashed changes
# Add light/dark mode toggle (dark mode by default). Modes pessist across page refresh and app restarts 
# Add support for tagging rows and columns with pop-up suggestions called using the hash-tag
# Remove particle-mouse interaction, when there is an element between the mouse and the particles (if the z-index of the element is lower than z-index of the particles stop the mouse-particle interaction).
# Add option to view previous prompts with arrow up/down keys 🔁

import os
from flask import Flask, render_template, request, jsonify, send_file, g
from dotenv import load_dotenv
from src.controller.spreadsheet_controller import SpreadsheetController
from src.model.session_manager import SessionManager
from src.model.prompt_history import PromptHistory
import threading
from flask import send_from_directory

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

PROMPT_HISTORY_FOLDER = os.path.join('static', 'json')
prompt_history = PromptHistory(PROMPT_HISTORY_FOLDER)

PROMPT_FILE = os.path.join('static', 'assets', 'prompts', 'prompts.txt')

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

@app.route('/prompt_history/<session_id>')
def prompt_history_route(session_id):
    """
    Returns the nth previous prompt for the session.
    Query param: index (int, 0=most recent)
    Response: { "prompt": "..." } or { "prompt": null }
    """
    try:
        index = int(request.args.get('index', 0))
    except Exception:
        index = 0
    prompt = prompt_history.get(session_id, index)
    return jsonify({"prompt": prompt})

@app.route('/process', methods=['POST'])
def process_command():
    """Process a user command through the LLM."""
    data = request.get_json()
    if not data or 'sessionId' not in data or 'command' not in data:
        return jsonify({'error': 'Missing session ID or command'}), 400
    
    session_id = data['sessionId']
    command = data['command']
    
    try:
        # Append prompt to history file
        prompt_history.append(session_id, command)
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

@app.route('/prompts', methods=['GET', 'POST'])
def prompts_api():
    import threading
    lock = threading.Lock()
    if request.method == 'POST':
        data = request.get_json()
        prompt = (data.get('prompt') or '').strip()
        if not prompt:
            return jsonify({'error': 'Prompt is empty'}), 400
        with lock:
            os.makedirs(os.path.dirname(PROMPT_FILE), exist_ok=True)
            # Avoid duplicates, append only if not present
            prompts = []
            if os.path.exists(PROMPT_FILE):
                with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
                    prompts = [line.strip() for line in f if line.strip()]
            if prompt not in prompts:
                with open(PROMPT_FILE, 'a', encoding='utf-8') as f:
                    f.write(prompt.replace('\n', ' ') + '\n')
        return jsonify({'success': True})
    else:
        prompts = []
        if os.path.exists(PROMPT_FILE):
            with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
                prompts = [line.strip() for line in f if line.strip()]
        return jsonify(prompts)

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
