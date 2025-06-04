"""
Gemini LLM Service module
-----------------
Handles interactions with the Google Gemini API to generate Python scripts
"""
import os
import json
import re
from typing import Dict, Any
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LLMService:
    """
    Service for interacting with Google Gemini API
    """
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.model = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')  # Default to gemini-2.0-flash if not set
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        # Configure the Gemini API
        genai.configure(api_key=self.api_key)
        
        # Set up the model
        self.generation_config = {
            "temperature": 0.2,
            "top_p": 1,
            "top_k": 32,
            "max_output_tokens": 2048,
        }
        
        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            }
        ]

    def generate_script(self, spreadsheet_data: Dict[str, Any], command: str) -> str:
        try:
            # The input 'spreadsheet_data' is already a dictionary.
            # No need to call json.loads()
            data_obj = spreadsheet_data 
            headers = data_obj.get('headers', [])
            metadata = data_obj.get('metadata', {})
            data_sample = data_obj.get('data', [])[:5] # Ensure data_sample is a list of dicts
            
            # If data_sample itself is a dict (e.g. from to_dict('records')), it's fine.
            # If data_obj['data'] was a list of lists, it would need conversion.
            # Based on Spreadsheet.to_json, data_obj['data'] is already a list of dicts.

            # Process the command to handle cell references if present
            processed_command = self._process_cell_references(command)
            
            prompt = self._create_prompt(headers, metadata, data_sample, processed_command)
            response = self._call_gemini_api(prompt)
            # If the response is a Gemini safety block message, return as error script
            if response.startswith("Content was blocked due to safety concerns:"):
                return self.handle_api_error(Exception(response))
            script = self._extract_script(response)
            return script
        except Exception as e:
            return self.handle_api_error(e)

    def _process_cell_references(self, command: str) -> str:
        """Process any cell references in the command to make them clearer for the LLM"""
        # First, handle complex patterns with multiple references and ranges
        # Process patterns like "#A1:#B2, #C3:#D4" or "#A:#B, #1:#2"
        def replace_complex_refs(match):
            refs = match.group(1).split(',')
            processed_refs = []
            
            for ref in refs:
                ref = ref.strip()
                if ':' in ref:  # It's a range
                    start, end = ref.split(':')
                    start = start.strip()
                    end = end.strip()
                    processed_refs.append(f"range from {start} to {end}")
                else:
                    # Single reference - will be handled by other patterns
                    processed_refs.append(ref)
            
            return "cells in " + ", ".join(processed_refs)
        
        # Handle complex ranges with comma-separated values
        pattern = r'#((?:[A-Z]+[0-9]*:[A-Z]+[0-9]*|[A-Z]+:[A-Z]+|[0-9]+:[0-9]+)(?:\s*,\s*(?:[A-Z]+[0-9]*:[A-Z]+[0-9]*|[A-Z]+:[A-Z]+|[0-9]+:[0-9]+))*)'
        processed = re.sub(pattern, replace_complex_refs, command)
        
        # Now handle individual patterns
        
        # Single cell references (e.g., #A1)
        processed = re.sub(r'#([A-Z]+)([0-9]+)', r'cell \1\2', processed)
        
        # Cell range references (e.g., #A1:#B2)
        processed = re.sub(r'#([A-Z]+[0-9]+):#([A-Z]+[0-9]+)', r'range from \1 to \2', processed)
        
        # Column references (e.g., #A)
        processed = re.sub(r'#([A-Z]+)(?!\d|:)', r'column \1', processed)
        
        # Row references (e.g., #1)
        processed = re.sub(r'#([0-9]+)(?!:)', r'row \1', processed)
        
        # Column range references (e.g., #A:#C)
        processed = re.sub(r'#([A-Z]+):#([A-Z]+)', r'columns from \1 to \2', processed)
        
        # Row range references (e.g., #1:#5)
        processed = re.sub(r'#([0-9]+):#([0-9]+)', r'rows from \1 to \2', processed)
        
        return processed

    def _create_prompt(self, headers: list, metadata: Dict[str, Any], data_sample: list, command: str) -> str:
        prompt = f"""You are an expert Python programmer tasked with modifying a spreadsheet based on user instructions.
<spreadsheet_context>
Headers: {headers}
Row count: {metadata.get('rows', 'unknown')}
Sample data (first few rows): {json.dumps(data_sample)}
</spreadsheet_context>

<user_command>
{command}
</user_command>

<task>
Write a Python script that modifies the Pandas DataFrame named 'df' according to the user's command.
The script should handle edge cases and error conditions gracefully.
DO NOT import modules other than pandas and numpy, which are already imported.
</task>

<instructions>
1. The DataFrame is already loaded and available as 'df'
2. Your modifications should be made directly to 'df'
3. Only use pandas and numpy functions
4. Do not include any explanations or comments in your response, ONLY THE PYTHON CODE
5. Do not attempt to write to files or perform any I/O operations
6. Output ONLY the Python code - no other text
7. Ensure your code handles potential errors gracefully

Important notes on cell references:
- When the user references specific cells with # notation, they're using Excel-style references
- For a single cell (like A1), use df.iloc[0, 0] (zero-indexed)
- For a column (like column A), use df.iloc[:, 0]
- For a row (like row 1), use df.iloc[0, :]
- For cell ranges (like A1:C3), use df.iloc[0:3, 0:3]
- For column ranges (like A:C), use df.iloc[:, 0:3]
- For row ranges (like 1:3), use df.iloc[0:3, :]
- Remember that Excel-style references use 1-based indexing for rows but df.iloc uses 0-based indexing
- Multiple selections may be indicated with commas (like A1, B2, C3)

Cell reference conversion examples:
- A1 = df.iloc[0, 0]
- B2 = df.iloc[1, 1] 
- Column A = df.iloc[:, 0]
- Row 5 = df.iloc[4, :]
- A1:C3 = df.iloc[0:3, 0:3]
- A:C = df.iloc[:, 0:3]
- 1:5 = df.iloc[0:5, :]
</instructions>

Provide only the Python code needed to execute the requested modification:"""
        return prompt

    def _call_gemini_api(self, prompt: str) -> str:
        try:
            # Initialize the Gemini model
            generation_config = genai.types.GenerationConfig(**self.generation_config)
            model = genai.GenerativeModel(
                model_name=self.model,
                generation_config=generation_config,
                safety_settings=self.safety_settings
            )
            
            # Generate content
            response = model.generate_content(prompt)
            
            # Robustly extract and return the text or error
            # 1. If response.text exists and is not empty, return it
            if hasattr(response, 'text') and response.text and response.text.strip():
                return response.text

            # 2. If candidates exist, check for content or safety block
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                # If content exists
                if hasattr(candidate, 'content') and getattr(candidate.content, 'parts', None):
                    parts = candidate.content.parts
                    if parts and hasattr(parts[0], 'text') and parts[0].text.strip():
                        return parts[0].text
                # If blocked by safety
                if hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
                    safety_issues = [getattr(rating, 'category', str(rating)) for rating in candidate.safety_ratings]
                    return f"Content was blocked due to safety concerns: {', '.join(safety_issues)}"
                # No valid content
                return "No valid response was generated. The model may have encountered an issue processing the request."
            # 3. Fallback: empty response
            return "Empty response received from Gemini API."
                
        except Exception as e:
            # Always return a string so the frontend can display a user-friendly error
            return f"Gemini API request failed: {str(e)}"

    def _extract_script(self, response: str) -> str:
        code_block_pattern = r'```(?:python)?\s*([\s\S]*?)\s*```'
        matches = re.findall(code_block_pattern, response)
        if matches:
            return matches[0].strip()
        return response.strip()

    def handle_api_error(self, error: Exception) -> str:
        error_message = str(error)
        script = f"""
# Error occurred in LLM API: {error_message}
# Returning original DataFrame without modifications
# Add error column to inform user
df['ERROR'] = "Failed to process command: {error_message}"
"""
        return script.strip()
