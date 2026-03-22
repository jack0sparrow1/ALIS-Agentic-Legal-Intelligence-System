import re
import json
import zipfile
from collections import Counter

# Read the ITAct-2000.txt file
with open('E:\ALIS\IT\ITAct,2000.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace Windows line endings with Unix ones for consistency
text = text.replace('\r\n', '\n').replace('\r', '\n')

# Function to extract keywords from text
def extract_keywords(text, num_keywords=7):
    # Basic stopwords
    stopwords = {
        'the', 'and', 'or', 'a', 'an', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 
        'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'to', 'was', 'will', 
        'with', 'shall', 'may', 'such', 'any', 'not', 'his', 'her', 'this', 'are',
        'been', 'have', 'had', 'do', 'does', 'did', 'can', 'could', 'would', 'should',
        'under', 'over', 'before', 'after', 'above', 'below', 'up', 'down', 'out',
        'off', 'on', 'into', 'through', 'during', 'until', 'against', 'among', 
        'throughout', 'despite', 'towards', 'upon', 'concerning', 'between', 'across',
        'beyond', 'within', 'without', 'through', 'during', 'before', 'after', 
        'above', 'below', 'up', 'down', 'out', 'off', 'over', 'under', 'again',
        'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how',
        'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 
        'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too',
        'very', 's', 't', 'just', 'now', 'also', 'but', 'however', 'therefore',
        'thus', 'hence', 'whereas', 'unless', 'because', 'since', 'although',
        'though', 'while', 'if', 'unless', 'except', 'besides', 'moreover',
        'furthermore', 'nevertheless', 'nonetheless', 'otherwise', 'likewise',
        'similarly', 'consequently', 'accordingly', 'meanwhile', 'subsequently'
    }
    
    # Extract words that are 4+ characters and not stopwords
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    filtered_words = [w for w in words if w not in stopwords]
    
    # Count frequency and return top keywords
    word_freq = Counter(filtered_words)
    return [word for word, _ in word_freq.most_common(num_keywords)]

# Improved regex pattern to match sections more accurately
# Pattern looks for: S. <number>. <title>—<content>
section_pattern = r'(?:\n|^)S\.\s*(\d+[A-Z]*)\.\s*([^—\n]+?)—\s*((?:.|\n)*?)(?=\nS\.\s*\d+[A-Z]*\.|\n(?:CHAPTER|\Z))'

sections = []
matches = re.finditer(section_pattern, text, re.MULTILINE | re.DOTALL)

for match in matches:
    section_number = match.group(1).strip()
    section_title = match.group(2).strip()
    section_text = match.group(3).strip()
    
    # Clean up the section text - remove excessive whitespace and line breaks
    section_text = re.sub(r'\n+', ' ', section_text)
    section_text = re.sub(r'\s+', ' ', section_text)
    
    # Remove any trailing section markers that might have been included
    section_text = re.sub(r'\s*\n?S\.\s*\d+[A-Z]*\..*$', '', section_text)
    
    # Extract keywords from section text
    keywords = extract_keywords(section_text)
    
    section_obj = {
        "act_name": "Information Technology Act, 2000",
        "section_number": section_number,
        "section_title": section_title,
        "text": section_text,
        "keywords": keywords
    }
    
    sections.append(section_obj)

print(f"Found {len(sections)} sections")

# Write to JSONL file
with open('it_act_corpus.jsonl', 'w', encoding='utf-8') as f:
    for section in sections:
        f.write(json.dumps(section, ensure_ascii=False) + '\n')


print(f"Created it_act_corpus.jsonl with {len(sections)} sections")
print("Created it_act_corpus.zip containing the JSONL file")

# Show first few sections as example
for i, section in enumerate(sections[:3]):
    print(f"\nSection {i+1}:")
    print(f"Number: {section['section_number']}")
    print(f"Title: {section['section_title']}")
    print(f"Text (first 200 chars): {section['text'][:200]}...")
    print(f"Keywords: {section['keywords']}")