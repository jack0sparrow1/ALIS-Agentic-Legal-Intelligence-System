from groq import Groq
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
import json
from tqdm import tqdm
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# === Initialize Groq client ===
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY not found in environment variables")
client = Groq(api_key=groq_api_key)

# === Connect to Elasticsearch ===
es = Elasticsearch(
    "http://localhost:9200",
    basic_auth=("elastic", os.getenv("ES_PASS")),
    verify_certs=False
)
model = SentenceTransformer("all-MiniLM-L6-v2")

def summarize_results(query, retrieved_docs):
    """
    query: user question
    retrieved_docs: list of top-k docs from Elastic
    """
    context_text = "\n\n".join([doc["_source"]["text"] for doc in retrieved_docs])

    prompt = f"""
    Answer the following question using only the context provided.
    
    Question: {query}
    
    Context: {context_text}
    
    Provide a concise and factual answer.
    """
    # Note: The Groq client uses the 'chat.completions.create' method
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="llama-3.1-8b-instant", # Specify the model you want to use
        max_tokens=300
    )
    return chat_completion.choices[0].message.content

# --- The rest of your code for searching Elasticsearch ---
query = "What is the punishment for murder by a life-convict?"
query_vector = model.encode(query).tolist()

response = es.search(
    index="legal_docs",
    query={
        "script_score": {
            "query": {
                "bool": {"should": [{"match": {"text": query}}]}
            },
            "script": {"source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                       "params": {"query_vector": query_vector}}
        }
    }
)

top_docs = response["hits"]["hits"][:3]  # top 3 relevant docs
answer = summarize_results(query, top_docs)

print("💡 Groq Answer:\n", answer)