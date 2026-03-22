from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer, util
from groq import Groq
import torch
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

# === In-memory Conversation Buffer ===
conversation_memory = []  # Stores context within a single session

# === Retrieve top conversation memory ===
def retrieve_memory(user_query, top_k=2):
    if not conversation_memory:
        return []
    query_emb = embedding_model.encode(user_query, convert_to_tensor=True)
    memory_embs = torch.tensor([m["embedding"] for m in conversation_memory])
    scores = util.cos_sim(query_emb, memory_embs)[0]
    top_results = torch.topk(scores, k=min(top_k, len(scores)))
    return [conversation_memory[i]["answer"] for i in top_results.indices]

# === Search from Elasticsearch ===
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
    hits = []
    for hit in response["hits"]["hits"]:
        src = hit["_source"]
        section_info = f"{src.get('section_title', 'N/A')} (Section {src.get('section_number', 'N/A')})"
        text_preview = src["text"][:350].strip()
        hits.append(f"{section_info}: {text_preview}")
    return hits

# === Ask Groq ===
def ask_groq(prompt):
    completion = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content

# === Agent Controller (Simple Conversation) ===
def agent_controller():
    print("\n⚖️ Legal Intelligence Chat (type 'exit' to quit)\n")

    while True:
        user_query = input("👤 You: ").strip()
        if user_query.lower() in ["exit", "quit", "bye"]:
            print("\n🧾 Session ended. Memory cleared.\n")
            break

        # Retrieve past context (in-session)
        past_context = retrieve_memory(user_query)
        memory_text = "\n\n".join(past_context)

        # Search Elastic for new info
        docs = search_elastic(user_query)
        context_text = "\n\n".join(docs)

        # Combine all context into a clean prompt
        reasoning_prompt = f"""
You are a concise Indian legal assistant.
Use the following legal text and past chat context to answer briefly and factually.
Always cite the section number and act name if available.

Past Conversation:
{memory_text}

Legal References:
{context_text}

User Question:
{user_query}

Give a short, accurate, law-focused answer (2–4 sentences max).
        """

        refined_answer = ask_groq(reasoning_prompt)

        print(f"\n⚖️ Agent: {refined_answer}\n")

        # Update ephemeral memory
        conversation_memory.append({
            "query": user_query,
            "answer": refined_answer,
            "embedding": embedding_model.encode(user_query).tolist()
        })

# === Run Agent ===
if __name__ == "__main__":
    agent_controller()
