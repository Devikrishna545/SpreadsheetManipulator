# Spreadsheet Auto-Editor

A Flask application that helps accountants automatically edit spreadsheets using natural language commands processed by LLMs and manual schema transformations.

## Features

- **Enhanced Spreadsheet Processing**: Comprehensive preprocessing handles all Excel/CSV customizations (merged cells, formatting, etc.)
- Upload spreadsheets in various formats (Excel, CSV) with robust error handling
- View uploaded spreadsheets in the browser
- Issue natural language commands to modify spreadsheets
- LLM generates Python scripts to perform modifications
- **Manual Schema Transformation (No LLM)**: Use a template spreadsheet to restructure entire datasets
- Split view mode for template-based transformations
- Undo/Redo functionality for all modifications
- Download modified spreadsheets
- Automatic cleanup of files after download

### Enhanced Spreadsheet Processing

The application now includes comprehensive preprocessing that handles all types of spreadsheet customizations:

- **Merged Cells**: Properly handles merged cells, rows, and columns
- **Group Headers**: Processes complex header structures and nested data
- **Formatting Issues**: Removes all formatting that can cause parsing problems
- **Multiple Encodings**: Automatically detects CSV encodings and delimiters
- **Error Recovery**: Multiple fallback methods ensure files always process
- **Data Cleaning**: Comprehensive cleaning removes artifacts and normalizes data

See [PREPROCESSING_ENHANCEMENTS.md](PREPROCESSING_ENHANCEMENTS.md) for detailed technical information.

### Manual Schema Transformation

The application includes a powerful manual schema transformation feature that works without LLM:

1. **Split View Mode**: View your main dataset (left) and template (right) side by side
2. **Template Creation**: Edit the right side to show the desired structure and patterns
3. **Schema Capture**: Capture the template structure and patterns
4. **Mass Transformation**: Apply the template to restructure your entire dataset (even 7000+ rows)

**Supported Patterns:**
- **Constant Values**: Set all rows to the same value
- **Sequential Numbers**: Generate sequences (1, 2, 3... or custom increments)
- **Date Sequences**: Generate date series (daily, weekly, monthly)
- **Repeating Cycles**: Cycle through multiple values
- **Column Rearrangement**: Reorder and rename columns
- **Data Type Conversion**: Automatic type conversion (string, integer, float, datetime)

## Project Structure

```
spreadsheet-auto-editor/
├── app.py                  # Main Flask application
├── .env                    # Environment variables
├── requirements.txt        # Python dependencies
├── templates/              # HTML templates
│   └── index.html          # Main application page
├── static/                 # Static files
│   ├── js/                 # JavaScript files
│   │   └── main.js         # Main JavaScript functionality
│   ├── css/                # CSS files
│   │   └── main.css        # Main stylesheet
│   ├── json/               # JSON data files for caching
│   ├── uploads/            # Temporary storage for uploaded spreadsheet files
│   ├── downloads/          # Generated files for download
│   └── assets/             
│       ├── images/         # Image assets
│       └── favicon/        # Favicon files and manifest.json
└── src/                    # Application source code
    ├── model/              # Data models
    ├── controller/         # Business logic controllers
    ├── api/                # External API integrations
    ├── llm/                # LLM service integrations
    └── script/             # Generated Python scripts from LLM
```

## Installation

1. Clone the repository:
```
git clone https://github.com/yourusername/spreadsheet-auto-editor.git
cd spreadsheet-auto-editor
```

2. Create a virtual environment and activate it:
```
python -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On Unix/Mac
```

3. Install dependencies:
```
pip install -r requirements.txt
```

4. Set up environment variables:
```
copy example.env .env
# Edit .env with your configuration including your LLM API key
```

5. Verify your environment setup:
```
python test_environment.py
```

6. Run the application:
```
python app.py
```

The application will be available at http://localhost:5000

The application will be available at http://localhost:5000

## Usage

1. Access the application in your web browser
2. Upload a spreadsheet file
3. Enter natural language commands to modify the spreadsheet (e.g., "Add a column named 'Total' that sums columns A and B")
4. Review the changes
5. Use undo/redo if needed
6. Download the modified spreadsheet when satisfied

## Development

### Requirements

- Python 3.9+
- Flask
- Pandas (for spreadsheet manipulation)
- OpenAI API key or similar LLM API

### Running Tests

```
pytest
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
