#!/usr/bin/env python
"""
Test script for environment setup verification
"""

import os
import sys
import pandas as pd
import json
from dotenv import load_dotenv

def test_environment():
    """Test the environment setup"""
    # Check Python version
    print(f"Python version: {sys.version}")
    
    # Check pandas version
    print(f"Pandas version: {pd.__version__}")
    
    # Check environment variables
    load_dotenv()
    print("\nEnvironment variables:")
    for var in ['GEMINI_API_KEY', 'SECRET_KEY']:
        value = os.getenv(var)
        masked = "Not set" if value is None else "Set" if var == 'GEMINI_API_KEY' else value[:4] + "..." if value else "Empty"
        print(f"  {var}: {masked}")

    # Check directories
    print("\nChecking directories:")
    for directory in ['static/uploads', 'static/downloads', 'static/json']:
        exists = os.path.exists(directory)
        print(f"  {directory}: {'Exists' if exists else 'Missing'}")

    # Create test JSON in static/json
    test_data = {
        "setup_test": True,
        "timestamp": pd.Timestamp.now().isoformat(),
        "message": "Environment test successful"
    }
    
    try:
        json_path = os.path.join('static', 'json', 'setup_test.json')
        with open(json_path, 'w') as f:
            json.dump(test_data, f, indent=2)
        print(f"\nCreated test JSON at {json_path}")
        
        # Read it back to verify
        with open(json_path, 'r') as f:
            read_data = json.load(f)
        print(f"Read test JSON successfully: {read_data['message']}")
        
    except Exception as e:
        print(f"Error creating/reading test JSON: {str(e)}")

if __name__ == "__main__":
    test_environment()
