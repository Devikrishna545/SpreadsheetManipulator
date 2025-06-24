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

def _serialize_for_json(obj):
    """
    Recursively convert datetime, pd.Timestamp, and similar objects to strings for JSON serialization.
    """
    import datetime
    import pandas as pd
    if isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_serialize_for_json(v) for v in obj]
    elif isinstance(obj, (datetime.datetime, datetime.date, pd.Timestamp)):
        return obj.isoformat()
    else:
        return obj

class LLMService:
    """
    Service for interacting with Google Gemini API
    """
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.model = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-thinking-exp-01-21')  # Use thinking model
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        # Configure the Gemini API
        genai.configure(api_key=self.api_key)
        
        # Set up the model configuration for thinking and code execution
        self.generation_config = {
            "temperature": 0.1,  # Lower temperature for more consistent code generation
            "top_p": 0.95,
            "top_k": 32,
            "max_output_tokens": 64000,
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

    def generate_script(self, spreadsheet_data: Dict[str, Any], command: str, use_advanced_processing: bool = False) -> str:
        """
        Generate script using appropriate processing mode based on complexity
        
        Args:
            spreadsheet_data: Spreadsheet data dictionary
            command: User command text
            use_advanced_processing: Whether to use thinking and code execution tools
            
        Returns:
            str: Generated Python script
        """
        if use_advanced_processing:
            return self._generate_complex_script(spreadsheet_data, command)
        else:
            return self._generate_simple_script(spreadsheet_data, command)
    
    def _generate_simple_script(self, spreadsheet_data: Dict[str, Any], command: str) -> str:
        """Generate script using regular Gemini model for simple commands"""
        max_attempts = 3
        last_error_msg = None
        for attempt in range(max_attempts):
            try:
                print(f"\n{'='*60}")
                print(f"GEMINI SIMPLE SCRIPT GENERATION - ATTEMPT {attempt + 1}")
                print(f"{'='*60}")
                
                # Extract data from spreadsheet_data
                data_obj = spreadsheet_data 
                headers = data_obj.get('headers', [])
                metadata = data_obj.get('metadata', {})
                data_sample = data_obj.get('data', [])[:5]
                # Serialize all data for JSON
                headers_serialized = _serialize_for_json(headers)
                metadata_serialized = _serialize_for_json(metadata)
                data_sample_serialized = _serialize_for_json(data_sample)
                
                # Process the command to handle cell references if present
                processed_command = self._process_cell_references(command)
                
                # Pass error message to prompt if previous attempt failed
                code_prompt = self._create_simple_prompt(
                    headers_serialized, metadata_serialized, data_sample_serialized, processed_command,
                    last_error_msg
                )
                final_script = self._call_gemini_simple_api(code_prompt)
                
                print("--- SIMPLE GENERATED SCRIPT ---")
                print(final_script)
                print("--- END SCRIPT ---\n")
                
                return final_script
                
            except Exception as e:
                error_msg = str(e)
                last_error_msg = error_msg
                print(f"\nSIMPLE ATTEMPT {attempt + 1} FAILED: {error_msg}")
                
                if attempt == max_attempts - 1:
                    print(f"\nALL {max_attempts} SIMPLE ATTEMPTS FAILED")
                    return self.handle_api_error(Exception(f"Failed to generate working script after {max_attempts} attempts. Last error: {error_msg}"))
                
                print(f"RETRYING... ({attempt + 2}/{max_attempts})")
        
        return self.handle_api_error(Exception("Unexpected error in simple script generation"))

    def _generate_complex_script(self, spreadsheet_data: Dict[str, Any], command: str) -> str:
        """Generate script using thinking and code execution for complex transformations"""
        max_attempts = 3
        last_error_msg = None
        for attempt in range(max_attempts):
            try:
                print(f"\n{'='*60}")
                print(f"GEMINI COMPLEX SCRIPT GENERATION - ATTEMPT {attempt + 1}")
                print(f"{'='*60}")
                
                # Extract data from spreadsheet_data
                data_obj = spreadsheet_data 
                headers = data_obj.get('headers', [])
                metadata = data_obj.get('metadata', {})
                data_sample = data_obj.get('data', [])[:5]
                # Serialize all data for JSON
                headers_serialized = _serialize_for_json(headers)
                metadata_serialized = _serialize_for_json(metadata)
                data_sample_serialized = _serialize_for_json(data_sample)
                
                # Process the command to handle cell references if present
                processed_command = self._process_cell_references(command)
                
                # Step 1: Use thinking mode to analyze and plan
                thinking_prompt = self._create_thinking_prompt(
                    headers_serialized, metadata_serialized, data_sample_serialized, processed_command,
                    last_error_msg
                )
                thinking_response = self._call_gemini_thinking_api(thinking_prompt)
                
                print("\n--- GEMINI THINKING PROCESS ---")
                print(thinking_response)
                print("--- END THINKING PROCESS ---\n")
                
                # Step 2: Generate code with execution
                code_prompt = self._create_code_generation_prompt(
                    headers_serialized, metadata_serialized, data_sample_serialized, processed_command, thinking_response,
                    last_error_msg
                )
                final_script = self._call_gemini_code_execution_api(code_prompt, headers_serialized, data_sample_serialized)
                
                print("--- COMPLEX GENERATED SCRIPT ---")
                print(final_script)
                print("--- END SCRIPT ---\n")
                
                return final_script
                
            except Exception as e:
                error_msg = str(e)
                last_error_msg = error_msg
                print(f"\nCOMPLEX ATTEMPT {attempt + 1} FAILED: {error_msg}")
                
                if attempt == max_attempts - 1:
                    print(f"\nALL {max_attempts} COMPLEX ATTEMPTS FAILED")
                    return self.handle_api_error(Exception(f"Failed to generate working script after {max_attempts} attempts. Last error: {error_msg}"))
                
                print(f"RETRYING... ({attempt + 2}/{max_attempts})")
        
        return self.handle_api_error(Exception("Unexpected error in complex script generation"))

    def _create_simple_prompt(self, headers: list, metadata: Dict[str, Any], data_sample: list, command: str, last_error_msg: str = None) -> str:
        """Create a simple prompt for regular commands"""
        prompt = f"""You are an expert Python programmer tasked with modifying a spreadsheet based on user instructions.

<spreadsheet_context>
Headers: {headers}
Row count: {metadata.get('rows', 'unknown')}
Sample data (first few rows): {json.dumps(data_sample)}
</spreadsheet_context>

<user_command>
{command}
</user_command>
"""
        if last_error_msg:
            prompt += f"\n<previous_error>\nThe previous attempt failed with this error:\n{last_error_msg}\n</previous_error>\n"
        prompt += """
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

    def _create_thinking_prompt(self, headers: list, metadata: Dict[str, Any], data_sample: list, command: str, last_error_msg: str = None) -> str:
        """Create a thinking prompt for complex commands"""
        prompt = f"""<task>
You need to analyze a spreadsheet modification request and think through the solution step by step.

<spreadsheet_context>
Headers: {headers}
Row count: {metadata.get('rows', 'unknown')}
Sample data (first few rows): {json.dumps(data_sample)}
</spreadsheet_context>

<user_command>
{command}
</user_command>
"""
        if last_error_msg:
            prompt += f"\n<previous_error>\nThe previous attempt failed with this error:\n{last_error_msg}\n</previous_error>\n"
        prompt += """
Think through this problem step by step:

1. **Understanding the Request**: What exactly is the user asking for?
2. **Data Analysis**: What is the current structure and content of the data?
3. **Solution Planning**: What pandas operations are needed?
4. **Edge Cases**: What potential issues should be handled?
5. **Implementation Strategy**: What is the best approach to implement this?

Please think through each step carefully and provide a detailed analysis.
</task>"""
        return prompt

    def _create_code_generation_prompt(self, headers: list, metadata: Dict[str, Any], data_sample: list, command: str, thinking_response: str, last_error_msg: str = None) -> str:
        prompt = f"""Based on the previous analysis, generate Python code to modify the spreadsheet.

<spreadsheet_context>
Headers: {headers}
Row count: {metadata.get('rows', 'unknown')}
Sample data: {json.dumps(data_sample)}
</spreadsheet_context>

<user_command>
{command}
</user_command>

<previous_analysis>
{thinking_response}
</previous_analysis>
"""
        if last_error_msg:
            prompt += f"\n<previous_error>\nThe previous attempt failed with this error:\n{last_error_msg}\n</previous_error>\n"
        prompt += """
<requirements>
1. Write Python code that modifies the Pandas DataFrame named 'df'
2. Only use pandas and numpy (already imported as pd and np)
3. Handle edge cases and errors gracefully
4. Do not import additional modules
5. Do not perform I/O operations
6. Test your code logic thoroughly
</requirements>

<cell_reference_guide>
When handling cell references with # notation:
- Single cell (A1): df.iloc[0, 0] (remember 0-based indexing)
- Column (A): df.iloc[:, 0] 
- Row (1): df.iloc[0, :]
- Range (A1:C3): df.iloc[0:3, 0:3]
- Column range (A:C): df.iloc[:, 0:3]
- Row range (1:3): df.iloc[0:3, :]
</cell_reference_guide>

Generate ONLY the Python code - no explanations or markdown formatting:"""
        return prompt

    def _call_gemini_simple_api(self, prompt: str) -> str:
        """Call the simple Gemini API for code generation"""
        try:
            # Use regular model for simple code generation
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash-lite-preview-06-17",
                generation_config=genai.types.GenerationConfig(**self.generation_config),
                safety_settings=self.safety_settings
            )
            
            token_count = model.count_tokens(prompt).total_tokens
            print(f"\n--- SIMPLE API PROMPT (Tokens: {token_count}) ---")
            print(prompt)
            print("--- END SIMPLE API PROMPT ---\n")
            
            response = model.generate_content(prompt)
            
            if hasattr(response, 'text') and response.text and response.text.strip():
                return self._extract_script(response.text)
            elif hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and getattr(candidate.content, 'parts', None):
                    parts = candidate.content.parts
                    if parts and hasattr(parts[0], 'text') and parts[0].text.strip():
                        return self._extract_script(parts[0].text)
            
            raise Exception("No valid response generated from simple API")
                
        except Exception as e:
            error_msg = str(e)
            print(f"Simple API Error: {error_msg}")
            raise Exception(f"Gemini simple API failed: {error_msg}")

    def _process_cell_references(self, command: str) -> str:
        """
        Process cell references in the command text
        
        Args:
            command: The original command text
            
        Returns:
            str: Processed command with cell references handled
        """
        # For now, just return the command as-is
        # This method can be enhanced later to handle specific cell reference processing
        return command

    def _call_gemini_thinking_api(self, prompt: str) -> str:
        try:
            # Use thinking model for analysis
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash-lite-preview-06-17",
                generation_config=genai.types.GenerationConfig(**self.generation_config),
                safety_settings=self.safety_settings
            )
            
            token_count = model.count_tokens(prompt).total_tokens
            print(f"\n--- THINKING API PROMPT (Tokens: {token_count}) ---")
            print(prompt)
            print("--- END THINKING API PROMPT ---\n")
            
            response = model.generate_content(prompt)

            # Try to get .text if available and non-empty
            if hasattr(response, 'text') and response.text and response.text.strip():
                return response.text

            # If .text is missing or empty, check candidates and their finish_reason
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                # finish_reason == 2 means STOP (see docs)
                finish_reason = getattr(candidate, 'finish_reason', None)
                # Try to extract text from candidate parts
                if hasattr(candidate, 'content') and getattr(candidate.content, 'parts', None):
                    parts = candidate.content.parts
                    # Concatenate all text parts if present
                    text_parts = [getattr(part, 'text', '') for part in parts if hasattr(part, 'text')]
                    combined = "\n".join([t for t in text_parts if t.strip()])
                    if combined.strip():
                        return combined.strip()
                # If finish_reason is 2 (STOP) and no text, return a safe message
                if finish_reason == 2:
                    return "(No thinking response generated: Gemini returned STOP with no content.)"
                # Otherwise, return a generic message
                return "(No thinking response generated: Gemini returned no usable content.)"

            return "(No thinking response generated: Gemini returned no candidates.)"
                
        except Exception as e:
            print(f"Thinking API Error: {str(e)}")
            return f"Thinking process failed: {str(e)}"

    def _call_gemini_code_execution_api(self, prompt: str, headers: list, data_sample: list) -> str:
        try:
            # Create model WITHOUT explicit tools parameter (let Gemini auto-enable code execution)
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash-lite-preview-06-17",
                generation_config=genai.types.GenerationConfig(**self.generation_config),
                safety_settings=self.safety_settings
            )
            
            # Enhanced prompt for code execution
            execution_prompt = f"""{prompt}

Before providing the final code, please:
1. Create a test DataFrame with the provided structure
2. Test your code to ensure it works correctly
3. Handle any errors that occur during testing
4. Provide the final working code

Test data structure:
Headers: {headers}
Sample data: {json.dumps(data_sample)}

Use code execution to verify your solution works before providing the final answer."""
            
            token_count = model.count_tokens(execution_prompt).total_tokens
            print(f"\n--- CODE EXECUTION API PROMPT (Tokens: {token_count}) ---")
            print(execution_prompt)
            print("--- END CODE EXECUTION API PROMPT ---\n")
            
            response = model.generate_content(execution_prompt)
            
            print("\n--- GEMINI CODE EXECUTION RESULTS ---")
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and getattr(candidate.content, 'parts', None):
                    for part in candidate.content.parts:
                        if hasattr(part, 'executable_code'):
                            print(f"CODE EXECUTED: {part.executable_code.code}")
                        if hasattr(part, 'code_execution_result'):
                            print(f"EXECUTION RESULT: {part.code_execution_result.output}")
                        if hasattr(part, 'text'):
                            print(f"TEXT OUTPUT: {part.text}")
            print("--- END CODE EXECUTION RESULTS ---")
            
            # Extract the final script
            if hasattr(response, 'text') and response.text and response.text.strip():
                script = self._extract_script(response.text)
                return script
            elif hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and getattr(candidate.content, 'parts', None):
                    # Look for text parts that contain the final code
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text.strip():
                            script = self._extract_script(part.text)
                            if script and 'df' in script:  # Basic validation
                                return script
            
            raise Exception("No valid code generated from code execution API")
                
        except Exception as e:
            error_msg = str(e)
            print(f"Code Execution API Error: {error_msg}")
            raise Exception(f"Gemini code execution API failed: {error_msg}")

    def _extract_script(self, response: str) -> str:
        # Look for code blocks first
        code_block_pattern = r'```(?:python)?\s*([\s\S]*?)\s*```'
        matches = re.findall(code_block_pattern, response)
        if matches:
            # Return the last code block (most likely the final solution)
            return matches[-1].strip()
        
        # If no code blocks, look for lines that seem like Python code
        lines = response.split('\n')
        code_lines = []
        in_code_section = False
        
        for line in lines:
            stripped = line.strip()
            # Start collecting if we see DataFrame operations
            if any(keyword in stripped for keyword in ['df[', 'df.', 'pd.', 'np.']):
                in_code_section = True
            
            if in_code_section:
                # Stop if we hit explanatory text
                if stripped and not (
                    stripped.startswith('#') or 
                    any(keyword in stripped for keyword in ['df', 'pd', 'np', '=', 'import', 'print']) or
                    stripped.startswith(('if', 'for', 'while', 'try', 'except', 'with'))
                ):
                    break
                code_lines.append(line)
        
        if code_lines:
            return '\n'.join(code_lines).strip()
        
        return response.strip()

    def handle_api_error(self, error: Exception) -> str:
        error_message = str(error)
        print(f"\n--- FINAL ERROR ---")
        print(f"Error: {error_message}")
        print("--- END ERROR ---\n")
        
        # Escape quotes and special characters in error message to prevent syntax errors
        safe_error_msg = error_message.replace('"', '\\"').replace("'", "\\'").replace('\n', '\\n')
        
        script = f"""# Error occurred in LLM API: {safe_error_msg}
# Returning original DataFrame without modifications
# Add error column to inform user
df['LLM_ERROR'] = "Script generation failed. Please try a different command."
"""
        return script.strip()

    def generate_universal_algorithm(self, action_plan: str, left_data: list, right_data: list) -> str:
        """
        Generate a universal algorithm from an action plan using thinking mode
        
        Args:
            action_plan: The action plan describing changes made
            left_data: The left spreadsheet data
            right_data: The right spreadsheet data
            
        Returns:
            str: Generated Python script implementing the universal algorithm
        """
        max_attempts = 3
        last_error_msg = None

        # Limit sample size to avoid exceeding token limits
        MAX_SAMPLE_ROWS = 20
        n_rows = min(len(right_data), MAX_SAMPLE_ROWS)
        left_sample = left_data[:n_rows] if n_rows > 0 else []
        right_sample = right_data[:n_rows] if n_rows > 0 else []

        # Extract headers and data for code execution
        headers = left_data[0] if left_data and len(left_data) > 0 else []
        data_rows = left_data[1:n_rows] if left_data and len(left_data) > 1 else []
        
        # Convert data to list of dicts for code execution API
        data_sample_for_exec = [dict(zip(headers, row)) for row in data_rows]
        
        for attempt in range(max_attempts):
            try:
                print(f"\n{'='*60}")
                print(f"GEMINI UNIVERSAL ALGORITHM GENERATION - ATTEMPT {attempt + 1}")
                print(f"{'='*60}")
                
                # Step 1: Use thinking mode to analyze the action plan
                thinking_prompt = self._create_algorithm_thinking_prompt(
                    action_plan, left_sample, right_sample, last_error_msg
                )
                thinking_response = self._call_gemini_thinking_api(thinking_prompt)
                
                print("\n--- GEMINI ALGORITHM THINKING PROCESS ---")
                print(thinking_response)
                print("--- END ALGORITHM THINKING PROCESS ---\n")
                
                # Step 2: Generate the universal algorithm
                algorithm_prompt = self._create_algorithm_generation_prompt(
                    action_plan, left_sample, right_sample, thinking_response, last_error_msg
                )
                final_script = self._call_gemini_code_execution_api(algorithm_prompt, headers, data_sample_for_exec)
                
                print("--- UNIVERSAL ALGORITHM GENERATED ---")
                print(final_script)
                print("--- END ALGORITHM ---\n")
                
                return final_script
                
            except Exception as e:
                error_msg = str(e)
                last_error_msg = error_msg
                print(f"\nALGORITHM GENERATION ATTEMPT {attempt + 1} FAILED: {error_msg}")
                
                if attempt == max_attempts - 1:
                    print(f"\nALL {max_attempts} ALGORITHM GENERATION ATTEMPTS FAILED")
                    return self.handle_api_error(Exception(f"Failed to generate universal algorithm after {max_attempts} attempts. Last error: {error_msg}"))
                
                print(f"RETRYING... ({attempt + 2}/{max_attempts})")
        
        return self.handle_api_error(Exception("Unexpected error in universal algorithm generation"))

    def _create_algorithm_thinking_prompt(self, action_plan: str, left_data: list, right_data: list, last_error_msg: str = None) -> str:
        """Create a thinking prompt for universal algorithm generation"""
        prompt = f"""<task>
You need to analyze an action plan that describes changes made to a sample of data, and develop a universal algorithm that can apply similar changes to a much larger dataset.

<action_plan>
{action_plan}
</action_plan>

<sample_data_context>
Left spreadsheet sample (first {len(left_data)} rows): {json.dumps(left_data)}
Right spreadsheet sample (first {len(right_data)} rows): {json.dumps(right_data)}
</sample_data_context>
"""
        if last_error_msg:
            prompt += f"\n<previous_error>\nThe previous attempt failed with this error:\n{last_error_msg}\n</previous_error>\n"
        
        prompt += """
Think through this problem step by step:

1. **Pattern Analysis**: What patterns can you identify in the changes described in the action plan?
2. **Data Structure Understanding**: What is the structure of the left spreadsheet data?
3. **Transformation Logic**: What are the core transformation rules that need to be applied?
4. **Universal Application**: How can these rules be applied to the entire left spreadsheet, not just the sample?
5. **Edge Cases**: What potential issues should be handled when applying to the full dataset?
6. **Implementation Strategy**: What is the best pandas-based approach to implement this universally?

The goal is to create a universal algorithm that will normalize and organize the entire left spreadsheet based on the pattern of changes shown in the action plan.
</task>"""
        return prompt

    def _create_algorithm_generation_prompt(self, action_plan: str, left_data: list, right_data: list, thinking_response: str, last_error_msg: str = None) -> str:
        """Create a prompt for generating the universal algorithm"""
        prompt = f"""Based on the previous analysis, generate a Python script that implements a universal algorithm to transform the entire left spreadsheet.

<action_plan>
{action_plan}
</action_plan>

<data_context>
Left spreadsheet sample (first {len(left_data)} rows): {json.dumps(left_data)}
Right spreadsheet sample (first {len(right_data)} rows): {json.dumps(right_data)}
</data_context>

<previous_analysis>
{thinking_response}
</previous_analysis>
"""
        if last_error_msg:
            prompt += f"\n<previous_error>\nThe previous attempt failed with this error:\n{last_error_msg}\n</previous_error>\n"
        
        prompt += """
<requirements>
1. Write Python code that modifies the entire pandas DataFrame named 'df' (the left spreadsheet)
2. Only use pandas and numpy (already imported as pd and np)
3. The algorithm should be universal - it should work on the entire dataset, not just the sample
4. Handle edge cases and errors gracefully
5. Focus on data normalization and organization
6. Remove or transform irrelevant data to keep only useful information
7. Apply the transformation pattern consistently across all similar data in the spreadsheet
8. Do not import additional modules
9. Do not perform I/O operations
</requirements>

<key_objectives>
- Normalize the data structure
- Remove irrelevant or duplicate information
- Organize data for better usability
- Apply consistent formatting and structure
- Handle various data patterns that might exist in the full spreadsheet
</key_objectives>

Generate ONLY the Python code - no explanations or markdown formatting:"""
        return prompt
