"""
LLM Service module
---------------
Handles interactions with the LLM API to generate Python scripts
"""

import os
import json
import requests
import re
from typing import Dict, Any, Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class LLMService:
    """
    Service for interacting with Large Language Models
    """
    
    def __init__(self):
        """Initialize the LLM service"""
        self.api_key = os.getenv('LLM_API_KEY')
        self.endpoint = os.getenv('LLM_ENDPOINT', 'https://api.openai.com/v1/chat/completions')
        self.model = os.getenv('LLM_MODEL', 'gpt-4-turbo')
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY environment variable not set")
    
    def generate_script(self, spreadsheet_json: str, command: str) -> str:
        """
        Generate a Python script to modify the spreadsheet based on user command

        Args:
            spreadsheet_json: JSON representation of the spreadsheet
            command: User's natural language command

        Returns:
            str: Generated Python script
        """
        try:
            # Extract metadata and a sample of the data to save tokens
            data_obj = json.loads(spreadsheet_json)
            headers = data_obj.get('headers', [])
            metadata = data_obj.get('metadata', {})
            
            # Take a sample of the data for context (first 5 rows)
            data_sample = data_obj.get('data', [])[:5]
            
            # Create a prompt for the LLM
            prompt = self._create_prompt(headers, metadata, data_sample, command)
            
            # Call the LLM API
            response = self._call_llm_api(prompt)
            
            # Extract Python script from response
            script = self._extract_script(response)
            
            return script
            
        except Exception as e:
            raise RuntimeError(f"Failed to generate script: {str(e)}")
    
    def _create_prompt(self, headers: list, metadata: Dict[str, Any], data_sample: list, command: str) -> str:
        """
        Create a prompt for the LLM

        Args:
            headers: List of column headers
            metadata: Spreadsheet metadata
            data_sample: Sample of spreadsheet data
            command: User's natural language command

        Returns:
            str: Formatted prompt for LLM
        """
        prompt = f"""
You are an expert Python programmer tasked with modifying a spreadsheet based on user instructions.

THE SPREADSHEET:
- Headers: {headers}
- Rows: {metadata.get('rows', 'unknown')}
- Sample data (first few rows): {json.dumps(data_sample)}

USER COMMAND:
{command}

YOUR TASK:
Write a Python script that modifies the Pandas DataFrame named 'df' according to the user's command.
The script should handle edge cases and error conditions gracefully.
DO NOT import modules other than pandas and numpy, which are already imported.

INSTRUCTIONS:
1. The DataFrame is already loaded and available as 'df'
2. Your modifications should be made directly to 'df'
3. Only use pandas and numpy functions
4. Do not include any explanations or comments in your response, ONLY THE PYTHON CODE
5. Do not attempt to write to files or perform any I/O operations
6. Output ONLY the Python code - no other text
"""
        return prompt
    
    def _call_llm_api(self, prompt: str) -> str:
        """
        Call the LLM API with the prompt

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            str: LLM response text
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a Python data processing assistant that helps modify spreadsheets."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.2,
            "max_tokens": 2000
        }
        
        try:
            response = requests.post(self.endpoint, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            response_data = response.json()
            message_content = response_data['choices'][0]['message']['content']
            
            return message_content
            
        except requests.RequestException as e:
            raise RuntimeError(f"API request failed: {str(e)}")
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Failed to parse LLM response: {str(e)}")
    
    def _extract_script(self, response: str) -> str:
        """
        Extract Python script from LLM response

        Args:
            response: Raw LLM response text

        Returns:
            str: Extracted Python script
        """
        # Look for code blocks
        code_block_pattern = r'```(?:python)?\s*([\s\S]*?)\s*```'
        matches = re.findall(code_block_pattern, response)
        
        if matches:
            # Return the first code block found
            return matches[0].strip()
        
        # If no code block markers, assume the entire response is code
        return response.strip()
    
    def handle_api_error(self, error: Exception) -> str:
        """
        Handle API errors gracefully

        Args:
            error: The exception that occurred

        Returns:
            str: A script that handles the error
        """
        error_message = str(error)
        
        # Generate a script that doesn't modify the data but reports the error
        script = f"""
# Error occurred in LLM API: {error_message}
# Returning original DataFrame without modifications

# Add error column to inform user
df['ERROR'] = "Failed to process command: LLM service error"
"""
        return script.strip()
