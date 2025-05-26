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
        self.model = os.getenv('GEMINI_MODEL', 'gemini-pro')  # Default to gemini-pro if not set
        
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
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
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

            prompt = self._create_prompt(headers, metadata, data_sample, command)
            response = self._call_gemini_api(prompt)
            script = self._extract_script(response)
            return script
        except Exception as e:
            raise RuntimeError(f"Failed to generate script: {str(e)}")

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
            
            # Extract and return the text
            if hasattr(response, 'text'):
                return response.text
            else:
                # For some versions of the API, response might be handled differently
                return response.candidates[0].content.parts[0].text
                
        except Exception as e:
            raise RuntimeError(f"Gemini API request failed: {str(e)}")

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
df['ERROR'] = "Failed to process command: LLM service error"
"""
        return script.strip()
