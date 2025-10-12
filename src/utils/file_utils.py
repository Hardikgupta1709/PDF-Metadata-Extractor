# src/utils/file_utils.py

import json
import pandas as pd
from typing import Dict, Any

def save_to_json(data: Dict[str, Any], output_path: str):
    """
    Saves a dictionary to a JSON file.
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def save_to_csv(data: Dict[str, Any], output_path: str):
    """
    Saves a dictionary to a CSV file using pandas.
    """
    # Pandas DataFrame is well-suited for tabular data like CSV.
    # We need to handle list-like data by converting it to a string.
    processed_data = {}
    for key, value in data.items():
        if isinstance(value, list):
            processed_data[key] = "; ".join(map(str, value))
        else:
            processed_data[key] = value
            
    df = pd.DataFrame([processed_data])
    df.to_csv(output_path, index=False, encoding='utf-8')