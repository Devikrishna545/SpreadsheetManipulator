# Test Data for development
import os
import pandas as pd
import numpy as np

def create_test_data(output_dir="static/json", filename="test_data.json"):
    """
    Create test data for development purposes
    """
    # Create a directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create sample data
    data = {
        'Date': pd.date_range(start='2025-01-01', periods=10),
        'Customer': ['Customer ' + str(i) for i in range(1, 11)],
        'Invoice': ['INV-' + str(1000 + i) for i in range(1, 11)],
        'Amount': np.random.uniform(100, 5000, 10).round(2),
        'Tax': np.random.uniform(5, 500, 10).round(2),
        'Status': np.random.choice(['Paid', 'Pending', 'Overdue'], 10)
    }
    
    df = pd.DataFrame(data)
    
    # Save to JSON
    file_path = os.path.join(output_dir, filename)
    df.to_json(file_path, orient='records', date_format='iso')
    
    print(f"Test data created at {file_path}")
    return file_path

if __name__ == "__main__":
    create_test_data()
