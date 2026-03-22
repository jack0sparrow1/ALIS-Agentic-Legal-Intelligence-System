import pandas as pd
import json
import re

# --- Configuration ---
INPUT_CSV_FILE = "IPC.csv"
OUTPUT_JSONL_FILE = "ipc_corpus.jsonl"
ACT_NAME = "Indian Penal Code"

# --- Main Conversion Logic ---
print(f"🚀 Starting conversion of '{INPUT_CSV_FILE}'...")

try:
    # 1. Load the CSV file into a pandas DataFrame
    # Assuming the column names are 'Section' and 'Description'. 
    # If they are different, change them in the line below.
    df = pd.read_csv(INPUT_CSV_FILE)
    
    # Check for expected columns
    if 'prompts' not in df.columns or 'response' not in df.columns:
        print(f"Error: The CSV must contain 'Section' and 'Description' columns.")
        print(f"Found columns: {list(df.columns)}")
        exit()

    all_records = []
    
    # 2. Iterate through each row of the DataFrame
    for index, row in df.iterrows():
        section_str = str(row['prompts'])
        description_str = str(row['response'])
        
        # Split the description into title and text. 
        # Assumes the first sentence ending with a period is the title.
        parts = description_str.split('. ', 1)
        section_title = parts[0].strip()
        text = parts[1].strip() if len(parts) > 1 else ""
        
        # 3. Create a dictionary matching the desired schema
        record = {
            "act_name": ACT_NAME,
            "section_number": section_str,
            "section_title": section_title,
            "text": text
            # The "keywords" field is omitted as it requires a separate NLP step.
        }
        all_records.append(record)
        
    # 4. Write the records to a JSONL file
    with open(OUTPUT_JSONL_FILE, 'w', encoding='utf-8') as f:
        for record in all_records:
            f.write(json.dumps(record) + '\n')
            
    print(f"\n✅ Success! Converted {len(all_records)} records.")
    print(f"Output saved to '{OUTPUT_JSONL_FILE}'.")

except FileNotFoundError:
    print(f"Error: The file '{INPUT_CSV_FILE}' was not found in this directory.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")