from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
from groq import Groq
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# === Connect to Elasticsearch ===
es = Elasticsearch(
    "http://localhost:9200",
    basic_auth=("elastic", os.getenv("ES_PASS"))
)

index_name = "legal_docs"

# === Initialize Models ===
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY not found in environment variables")
groq_client = Groq(api_key=groq_api_key)

# === Helper: Retrieve top documents ===
def search_elastic(query, top_k=3):
    query_vector = embedding_model.encode(query).tolist()
    response = es.search(
        index=index_name,
        knn={
            "field": "embedding",
            "query_vector": query_vector,
            "k": top_k,
            "num_candidates": 20
        }
    )
    return [hit["_source"] for hit in response["hits"]["hits"]]

# === Helper: Ask Groq ===
def ask_groq(prompt):
    completion = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content

# === Agent Workflow ===
def agent_controller(user_query):
    print("\n🔍 Step 1: Searching Elastic...")
    docs = search_elastic(user_query)
    context_text = "\n\n".join([d["text"] for d in docs])

    print("\n🧠 Step 2: Reasoning with Groq...")
    initial_prompt = f"""
You are a legal reasoning assistant. 
Based on the following legal texts, answer the user's question clearly and accurately.

User Question: {user_query}

Relevant Context:
{context_text}
    """
    initial_answer = ask_groq(initial_prompt)

    print("\n✅ Step 3: Verifying with Groq...")
    verify_prompt = f"""
Your previous answer was:
{initial_answer}

Now verify this answer using the same or similar context.
Find specific clauses, sections, or legal reasoning that support or contradict your answer.
If you find issues, refine and correct the answer.
    """
    refined_answer = ask_groq(verify_prompt)

    print("\n💬 Final Verified Answer:\n")
    return refined_answer


if __name__ == "__main__":
    user_query = input("Enter your legal question: ")
    final_output = agent_controller(user_query)
    print(final_output)
