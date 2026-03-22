import pandas as pd, json

# Load CSV with the correct encoding and column names
crpc_df = pd.read_csv('crpc_sections.csv', encoding='latin1')

# Rename columns to match the schema
crpc_df = crpc_df.rename(columns={
    'Section': 'section_number',
    'Section _name': 'section_title',
    'Description': 'text'
})

# Drop any rows missing section_number or text
crpc_df = crpc_df.dropna(subset=['section_number', 'text'])

# Generate simple keywords list from the section title (4+ chars)
def extract_keywords(title):
    if not isinstance(title, str):
        return []
    return [w.lower() for w in title.split() if len(w) > 3]

crpc_df['keywords'] = crpc_df['section_title'].apply(extract_keywords)

# Add the 'act_name' field
crpc_df['act_name'] = 'Code of Criminal Procedure'

# Create the final structured DataFrame
crpc_corpus = crpc_df[['act_name', 'section_number', 'section_title', 'text', 'keywords']]

# Write each record to crpc_corpus.jsonl
with open('crpc_corpus.jsonl', 'w', encoding='utf-8') as f:
    for _, row in crpc_corpus.iterrows():
        json.dump(row.to_dict(), f, ensure_ascii=False)
        f.write('\n')

f"crpc_corpus.jsonl created with {len(crpc_corpus)} records."