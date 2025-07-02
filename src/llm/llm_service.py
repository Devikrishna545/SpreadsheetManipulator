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
        max_attempts = 5
        last_error_msg = None
        for attempt in range(max_attempts):
            try:
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
                
                return final_script
                
            except Exception as e:
                error_msg = str(e)
                last_error_msg = error_msg
                
                if attempt == max_attempts - 1:
                    return self.handle_api_error(Exception(f"Failed to generate working script after {max_attempts} attempts. Last error: {error_msg}"))
        
        return self.handle_api_error(Exception("Unexpected error in simple script generation"))

    def _generate_complex_script(self, spreadsheet_data: Dict[str, Any], command: str) -> str:
        """Generate script using thinking and code execution for complex transformations"""
        max_attempts = 5
        last_error_msg = None
        for attempt in range(max_attempts):
            try:
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
                
                # Step 2: Generate code with execution
                code_prompt = self._create_code_generation_prompt(
                    headers_serialized, metadata_serialized, data_sample_serialized, processed_command, thinking_response,
                    last_error_msg
                )
                final_script = self._call_gemini_code_execution_api(code_prompt, headers_serialized, data_sample_serialized)
                
                print("✓ Complex script generated successfully")
                
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
            
            response = model.generate_content(execution_prompt)
            
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
            left_data: The left spreadsheet data (FULL dataset)
            right_data: The right spreadsheet data (sample/template)
            
        Returns:
            str: Generated Python script implementing the universal algorithm
        """
        max_attempts = 5
        last_error_msg = None

        # Use limited sample for analysis to avoid token limits, but make algorithm work on ALL data
        # CRITICAL: Sample is only for understanding pattern, algorithm must work on ENTIRE dataset
        MAX_SAMPLE_ROWS = 25  # Increased for better pattern understanding
        MAX_RIGHT_SAMPLE = min(len(right_data), MAX_SAMPLE_ROWS) if right_data else 0
        
        # For left data, use more rows for better pattern analysis but still limit for tokens
        MAX_LEFT_SAMPLE = min(len(left_data), 50) if left_data else 0  # Increased from 20 to 50
        
        left_sample = left_data[:MAX_LEFT_SAMPLE] if left_data and len(left_data) > 0 else []
        right_sample = right_data[:MAX_RIGHT_SAMPLE] if right_data and len(right_data) > 0 else []

        # Extract headers and full dataset info for code execution
        headers = left_data[0] if left_data and len(left_data) > 0 else []
        
        # For code execution, use a representative sample but include full dataset info
        data_rows = left_data[1:min(31, len(left_data))] if left_data and len(left_data) > 1 else []  # Use up to 30 data rows
        data_sample_for_exec = [dict(zip(headers, row)) for row in data_rows]
        
        # Store full dataset size information - THIS IS CRITICAL
        full_left_rows = len(left_data)
        full_left_cols = len(left_data[0]) if left_data and len(left_data) > 0 else 0
        
        for attempt in range(max_attempts):
            try:
                print(f"\n{'='*60}")
                print(f"GEMINI UNIVERSAL ALGORITHM GENERATION - ATTEMPT {attempt + 1}")
                print(f"{'='*60}")
                
                # Step 1: Use thinking mode to analyze the action plan
                thinking_prompt = self._create_algorithm_thinking_prompt(
                    action_plan, left_sample, right_sample, full_left_rows, full_left_cols, last_error_msg
                )
                thinking_response = self._call_gemini_thinking_api(thinking_prompt)
                
                # Step 2: Generate the universal algorithm
                algorithm_prompt = self._create_algorithm_generation_prompt(
                    action_plan, left_sample, right_sample, full_left_rows, full_left_cols, thinking_response, last_error_msg
                )
                final_script = self._call_gemini_code_execution_api(algorithm_prompt, headers, data_sample_for_exec)
                
                print("✓ Universal algorithm generated successfully")
                
                # Validate the algorithm for full dataset processing
                validation_warnings = self._validate_algorithm_for_full_dataset_processing(final_script, full_left_rows)
                if validation_warnings:
                    print("⚠️  ALGORITHM VALIDATION WARNINGS:")
                    print(validation_warnings)
                
                return final_script
                
            except Exception as e:
                error_msg = str(e)
                last_error_msg = error_msg
                print(f"❌ ATTEMPT {attempt + 1} FAILED: {error_msg}")
                
                if attempt == max_attempts - 1:
                    print(f"❌ ALL {max_attempts} ATTEMPTS FAILED")
                    return self.handle_api_error(Exception(f"Failed to generate universal algorithm after {max_attempts} attempts. Last error: {error_msg}"))
                
                print(f"🔄 RETRYING... ({attempt + 2}/{max_attempts})")
        
        return self.handle_api_error(Exception("Unexpected error in universal algorithm generation"))

    def _create_algorithm_thinking_prompt(self, action_plan: str, left_data: list, right_data: list, full_left_rows: int, full_left_cols: int, last_error_msg: str = None) -> str:
        """Create a thinking prompt for universal algorithm generation"""
        prompt = f"""<task>
You need to analyze an action plan that describes changes made to a sample of data, and develop a universal algorithm that can apply similar changes to a much larger dataset.

<action_plan>
{action_plan}
</action_plan>

<dataset_context>
IMPORTANT: The full left spreadsheet has {full_left_rows} rows and {full_left_cols} columns.
You are only seeing a sample of {len(left_data)} rows from the left spreadsheet and {len(right_data)} rows from the right spreadsheet for analysis purposes.
Your algorithm MUST work on the ENTIRE left dataset ({full_left_rows} rows), not just this sample.

Left spreadsheet sample (first {len(left_data)} rows of {full_left_rows} total): {json.dumps(left_data)}
Right spreadsheet sample ({len(right_data)} rows): {json.dumps(right_data)}
</dataset_context>
"""
        if last_error_msg:
            prompt += f"\n<previous_error>\nThe previous attempt failed with this error:\n{last_error_msg}\n</previous_error>\n"
        
        prompt += """
Think through this problem step by step:

1. **Pattern Analysis**: What patterns can you identify in the changes described in the action plan?
2. **Data Structure Understanding**: What is the structure of the left spreadsheet data?
3. **Transformation Logic**: What are the core transformation rules that need to be applied?
4. **Universal Application**: How can these rules be applied to the ENTIRE left spreadsheet (all {full_left_rows} rows), not just the sample?
5. **Edge Cases**: What potential issues should be handled when applying to the full dataset?
6. **Implementation Strategy**: What is the best pandas-based approach to implement this universally?
7. **Scale Considerations**: How will this algorithm perform on {full_left_rows} rows?

CRITICAL: The goal is to create a universal algorithm that will normalize and organize the ENTIRE left spreadsheet ({full_left_rows} rows) based on the pattern of changes shown in the action plan. The sample data is only for understanding the pattern - the algorithm MUST process ALL {full_left_rows} rows of the left dataset.
</task>"""
        return prompt

    def _create_algorithm_generation_prompt(self, action_plan: str, left_data: list, right_data: list, full_left_rows: int, full_left_cols: int, thinking_response: str, last_error_msg: str = None) -> str:
        """Create a prompt for generating the universal algorithm"""
        prompt = f"""Based on the previous analysis, generate a Python script that implements a universal algorithm to transform the entire left spreadsheet.

<action_plan>
{action_plan}
</action_plan>

<dataset_context>
CRITICAL: The full left spreadsheet has {full_left_rows} rows and {full_left_cols} columns.
You are only seeing a sample for analysis purposes, but your algorithm MUST work on ALL {full_left_rows} rows.

Left spreadsheet sample (first {len(left_data)} rows of {full_left_rows} total): {json.dumps(left_data)}
Right spreadsheet sample ({len(right_data)} rows - this is the desired output structure): {json.dumps(right_data)}
</dataset_context>

<previous_analysis>
{thinking_response}
</previous_analysis>
"""
        if last_error_msg:
            prompt += f"\n<previous_error>\nThe previous attempt failed with this error:\n{last_error_msg}\n</previous_error>\n"
        
        prompt += """
<requirements>
1. Write Python code that modifies the entire pandas DataFrame named 'df' (the left spreadsheet with {full_left_rows} rows)
2. Only use pandas and numpy (already imported as pd and np)
3. The algorithm MUST be universal - it MUST work on the entire dataset ({full_left_rows} rows), not just the sample
4. Handle edge cases and errors gracefully across all {full_left_rows} rows
5. Focus on data normalization and organization for the COMPLETE dataset
6. Remove or transform irrelevant data to keep only useful information across ALL rows
7. Apply the transformation pattern consistently across all similar data in the entire {full_left_rows}-row spreadsheet
8. Do not import additional modules
9. Do not perform I/O operations
10. Ensure the algorithm scales to {full_left_rows} rows efficiently
11. NEVER limit processing to just sample rows - process ALL {full_left_rows} rows in the DataFrame
12. Use df.iloc[:, :] or similar to ensure ALL rows are processed, not just the first few
</requirements>

<key_objectives>
- Normalize the data structure across ALL {full_left_rows} rows
- Remove irrelevant or duplicate information from the ENTIRE dataset
- Organize data for better usability across the COMPLETE spreadsheet
- Apply consistent formatting and structure to ALL {full_left_rows} rows
- Handle various data patterns that exist in the full {full_left_rows}-row spreadsheet
- Process and transform the ENTIRE left spreadsheet, not just a subset
- Ensure the algorithm works on every single row in the {full_left_rows}-row DataFrame
</key_objectives>

CRITICAL REMINDER: Your algorithm will be applied to a DataFrame with {full_left_rows} rows. Make sure your code works on the complete dataset, not just the sample you see here. DO NOT limit processing to the first N rows - process ALL {full_left_rows} rows.

**IMPORTANT**: If your algorithm uses methods like df.head(), df.iloc[:sample_size], or similar row-limiting operations, you are doing it WRONG. The algorithm must process the entire DataFrame with ALL {full_left_rows} rows.

**COMMON MISTAKE TO AVOID**: Do not create an output that matches the size of the right spreadsheet sample ({len(right_data)} rows). The right spreadsheet is just a template showing the desired structure. Your algorithm should transform ALL {full_left_rows} rows of the left spreadsheet into this structure, not just {len(right_data)} rows.

**DATASET SIZE REMINDER**: 
- Left spreadsheet (input): {full_left_rows} rows - PROCESS ALL OF THESE
- Right spreadsheet (template): {len(right_data)} rows - THIS IS JUST AN EXAMPLE STRUCTURE
- Your output should have {full_left_rows} rows (or the appropriate number after filtering/grouping), NOT {len(right_data)} rows

Generate ONLY the Python code - no explanations or markdown formatting:"""
        return prompt

    def _validate_algorithm_for_full_dataset_processing(self, algorithm_script: str, full_rows: int) -> str:
        """
        Validate that the algorithm doesn't contain patterns that would limit data processing
        
        Args:
            algorithm_script: The generated algorithm script
            full_rows: Number of rows in the full dataset
            
        Returns:
            str: Warning message if issues found, empty string if no issues
        """
        warning_patterns = [
            ("df.head(", "df.head() only processes the first few rows"),
            ("df.iloc[:30", f"df.iloc[:30] only processes first 30 rows, but dataset has {full_rows} rows"),
            ("df.iloc[:20", f"df.iloc[:20] only processes first 20 rows, but dataset has {full_rows} rows"),
            ("df.iloc[:10", f"df.iloc[:10] only processes first 10 rows, but dataset has {full_rows} rows"),
            ("df.iloc[:5", f"df.iloc[:5] only processes first 5 rows, but dataset has {full_rows} rows"),
            ("for i in range(30", f"Loop range of 30 may not process all {full_rows} rows"),
            ("for i in range(20", f"Loop range of 20 may not process all {full_rows} rows"),
            ("range(len(right_", "Using right spreadsheet length for loops may limit processing to sample size"),
        ]
        
        warnings = []
        for pattern, message in warning_patterns:
            if pattern in algorithm_script:
                warnings.append(f"WARNING: {message}")
        
        if warnings:
            return "\n".join(warnings)
        return ""

    def generate_universal_algorithm_with_error_feedback(self, action_plan: str, left_data: list, right_data: list, error_feedback: str = None) -> str:
        """
        Generate a universal algorithm with optional error feedback for retry scenarios
        
        Args:
            action_plan: The action plan describing changes made
            left_data: The left spreadsheet data (FULL dataset)
            right_data: The right spreadsheet data (sample/template)
            error_feedback: Error message from previous attempt (if any)
            
        Returns:
            str: Generated Python script implementing the universal algorithm
        """
        # If no error feedback, use the regular method
        if error_feedback is None:
            return self.generate_universal_algorithm(action_plan, left_data, right_data)
        
        # Generate algorithm with error feedback
        max_attempts = 5  # Increased for better error recovery
        last_error_msg = error_feedback

        # Use limited sample for analysis to avoid token limits, but make algorithm work on ALL data
        # CRITICAL: Sample is only for understanding pattern, algorithm must work on ENTIRE dataset
        MAX_SAMPLE_ROWS = 25  # Increased for better pattern understanding
        MAX_RIGHT_SAMPLE = min(len(right_data), MAX_SAMPLE_ROWS) if right_data else 0
        
        # For left data, use more rows for better pattern analysis but still limit for tokens
        MAX_LEFT_SAMPLE = min(len(left_data), 50) if left_data else 0  # Increased from 20 to 50
        
        left_sample = left_data[:MAX_LEFT_SAMPLE] if left_data and len(left_data) > 0 else []
        right_sample = right_data[:MAX_RIGHT_SAMPLE] if right_data and len(right_data) > 0 else []

        # Extract headers and full dataset info for code execution
        headers = left_data[0] if left_data and len(left_data) > 0 else []
        
        # For code execution, use a representative sample but include full dataset info
        data_rows = left_data[1:min(31, len(left_data))] if left_data and len(left_data) > 1 else []  # Use up to 30 data rows
        data_sample_for_exec = [dict(zip(headers, row)) for row in data_rows]
        
        # Store full dataset size information - THIS IS CRITICAL
        full_left_rows = len(left_data)
        full_left_cols = len(left_data[0]) if left_data and len(left_data) > 0 else 0
        
        for attempt in range(max_attempts):
            try:
                print(f"📝 Generating algorithm with error feedback (attempt {attempt + 1}/{max_attempts})")
                
                # Step 1: Use thinking mode to analyze the action plan with error feedback
                thinking_prompt = self._create_algorithm_thinking_prompt(
                    action_plan, left_sample, right_sample, full_left_rows, full_left_cols, last_error_msg
                )
                thinking_response = self._call_gemini_thinking_api(thinking_prompt)
                
                # Step 2: Generate the universal algorithm with explicit error handling
                algorithm_prompt = self._create_algorithm_generation_prompt_with_error_feedback(
                    action_plan, left_sample, right_sample, full_left_rows, full_left_cols, thinking_response, last_error_msg
                )
                final_script = self._call_gemini_code_execution_api(algorithm_prompt, headers, data_sample_for_exec)
                
                print("✓ Algorithm with error feedback generated successfully")
                
                # Validate the algorithm for full dataset processing
                validation_warnings = self._validate_algorithm_for_full_dataset_processing(final_script, full_left_rows)
                if validation_warnings:
                    print("⚠️  ALGORITHM VALIDATION WARNINGS:")
                    print(validation_warnings)
                
                return final_script
                
            except Exception as e:
                error_msg = str(e)
                last_error_msg = f"Previous error: {error_feedback}. New error: {error_msg}"
                print(f"❌ Error feedback attempt {attempt + 1} failed: {error_msg}")
                
                if attempt == max_attempts - 1:
                    print(f"❌ All {max_attempts} error feedback attempts failed")
                    return self.handle_api_error(Exception(f"Failed to generate universal algorithm with error feedback after {max_attempts} attempts. Last error: {error_msg}"))
                
                print(f"🔄 Retrying error feedback generation... ({attempt + 2}/{max_attempts})")
        
        return self.handle_api_error(Exception("Unexpected error in universal algorithm generation with error feedback"))

    def _create_algorithm_generation_prompt_with_error_feedback(self, action_plan: str, left_data: list, right_data: list, full_left_rows: int, full_left_cols: int, thinking_response: str, error_msg: str) -> str:
        """Create a prompt for generating the universal algorithm with error feedback"""
        prompt = f"""Based on the previous analysis, generate a Python script that implements a universal algorithm to transform the entire left spreadsheet.
        
IMPORTANT: The previous algorithm attempt failed with this error:
{error_msg}

Please analyze this error and generate a corrected algorithm that avoids this issue.

<action_plan>
{action_plan}
</action_plan>

<dataset_context>
CRITICAL: The full left spreadsheet has {full_left_rows} rows and {full_left_cols} columns.
You are only seeing a sample for analysis purposes, but your algorithm MUST work on ALL {full_left_rows} rows.

Left spreadsheet sample (first {len(left_data)} rows of {full_left_rows} total): {json.dumps(left_data)}
Right spreadsheet sample ({len(right_data)} rows - this is the desired output structure): {json.dumps(right_data)}
</dataset_context>

<previous_analysis>
{thinking_response}
</previous_analysis>

<error_analysis>
The previous algorithm failed with this error: {error_msg}
Please ensure your new algorithm:
1. Handles this specific error case
2. Includes proper error checking and validation
3. Uses try-catch blocks where appropriate
4. Validates data types and structures before processing
5. Handles edge cases that might cause similar errors
6. PROCESSES THE ENTIRE DATASET - if the error suggests only partial data processing, ensure your algorithm works on ALL {full_left_rows} rows
7. Does not use any row-limiting operations like df.head(), df.iloc[:n], or similar that would only process a subset of rows
8. Uses vectorized operations that naturally work on the entire DataFrame
</error_analysis>

<requirements>
1. Write Python code that modifies the entire pandas DataFrame named 'df' (the left spreadsheet with {full_left_rows} rows)
2. Only use pandas and numpy (already imported as pd and np)
3. The algorithm MUST be universal - it MUST work on the entire dataset ({full_left_rows} rows), not just the sample
4. Handle edge cases and errors gracefully across all {full_left_rows} rows
5. Include proper error handling to prevent the error that occurred previously
6. Focus on data normalization and organization for the COMPLETE dataset
7. Remove or transform irrelevant data to keep only useful information across ALL rows
8. Apply the transformation pattern consistently across all similar data in the entire {full_left_rows}-row spreadsheet
9. Do not import additional modules
10. Do not perform I/O operations
11. Ensure the algorithm scales to {full_left_rows} rows efficiently
12. Add validation checks to prevent the specific error that occurred: {error_msg}
13. CRITICAL: Ensure your algorithm processes ALL {full_left_rows} rows, not just a subset
14. Use operations like df.iloc[:, :] or full DataFrame operations to ensure complete processing
15. Never use row-limiting operations unless specifically required for the transformation logic
</requirements>

<key_objectives>
- Normalize the data structure across ALL {full_left_rows} rows
- Remove irrelevant or duplicate information from the ENTIRE dataset
- Organize data for better usability across the COMPLETE spreadsheet
- Apply consistent formatting and structure to ALL {full_left_rows} rows
- Handle various data patterns that exist in the full {full_left_rows}-row spreadsheet
- Process and transform the ENTIRE left spreadsheet, not just a subset
- Avoid the error that occurred previously by adding proper validation and error handling
</key_objectives>

CRITICAL REMINDER: Your algorithm will be applied to a DataFrame with {full_left_rows} rows. Make sure your code works on the complete dataset, not just the sample you see here. Also ensure it handles the error case that occurred previously.

**COMMON MISTAKE TO AVOID**: Do not create an output that matches the size of the right spreadsheet sample ({len(right_data)} rows). The right spreadsheet is just a template showing the desired structure. Your algorithm should transform ALL {full_left_rows} rows of the left spreadsheet into this structure, not just {len(right_data)} rows.

**DATASET SIZE REMINDER**: 
- Left spreadsheet (input): {full_left_rows} rows - PROCESS ALL OF THESE
- Right spreadsheet (template): {len(right_data)} rows - THIS IS JUST AN EXAMPLE STRUCTURE
- Your output should have {full_left_rows} rows (or the appropriate number after filtering/grouping), NOT {len(right_data)} rows

Generate ONLY the Python code - no explanations or markdown formatting:"""
        return prompt

    def generate_universal_algorithm_with_auto_retry(self, action_plan: str, left_data: list, right_data: list, max_retries: int = 5) -> str:
        """
        Generate a universal algorithm with automatic retry on execution errors
        
        Args:
            action_plan: The action plan describing changes made
            left_data: The left spreadsheet data (FULL dataset)
            right_data: The right spreadsheet data (sample/template)
            max_retries: Maximum number of retries on execution errors
            
        Returns:
            str: Generated Python script implementing the universal algorithm
        """
        last_error_msg = None
        
        for retry_attempt in range(max_retries):
            try:
                print(f"🔄 Auto-retry generation attempt {retry_attempt + 1}/{max_retries}")
                
                # Generate algorithm (with error feedback if available)
                if retry_attempt == 0:
                    # First attempt - use regular generation
                    algorithm_script = self.generate_universal_algorithm(action_plan, left_data, right_data)
                else:
                    # Subsequent attempts - use error feedback
                    algorithm_script = self.generate_universal_algorithm_with_error_feedback(
                        action_plan, left_data, right_data, last_error_msg
                    )
                
                # Validate the generated algorithm for full dataset processing
                validation_warnings = self._validate_algorithm_for_full_dataset_processing(algorithm_script, len(left_data))
                if validation_warnings:
                    print("⚠️  Validation warnings found in generated algorithm:")
                    print(validation_warnings)
                
                print(f"✓ Algorithm auto-retry successful on attempt {retry_attempt + 1}")
                return algorithm_script
                
            except Exception as e:
                error_msg = str(e)
                last_error_msg = f"Attempt {retry_attempt + 1} failed: {error_msg}"
                print(f"❌ Auto-retry attempt {retry_attempt + 1} failed: {error_msg}")
                
                if retry_attempt < max_retries - 1:
                    print(f"🔄 Retrying... ({retry_attempt + 2}/{max_retries})")
                    continue
                else:
                    print(f"❌ All {max_retries} auto-retry attempts failed")
                    return self.handle_api_error(Exception(f"Failed to generate universal algorithm after {max_retries} attempts. Last error: {error_msg}"))
        
        return self.handle_api_error(Exception("Unexpected error in universal algorithm generation with auto-retry"))

    def generate_script_correction(self, correction_prompt: str) -> str:
        """
        Generate a corrected script based on error feedback.
        
        Args:
            correction_prompt: Prompt containing the failing script and error details
            
        Returns:
            str: Corrected Python script
        """
        try:
            # Use the regular model for script corrections
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash-exp",
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            response = model.generate_content(correction_prompt)
            
            if response.text:
                return response.text.strip()
            else:
                return ""
                
        except Exception as e:
            print(f"❌ Error generating script correction: {e}")
            return ""
