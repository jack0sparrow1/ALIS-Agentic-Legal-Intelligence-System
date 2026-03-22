from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
from groq import Groq
import json
import re
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

# === Conversation Memory ===
conversation_memory = []

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

# === Phase 5: Structured Reasoning (Graph + Verification) ===
def graph_verifier(context_text, user_query, base_answer):
    extraction_prompt = f"""
You are a legal structure extraction model.
From the following text and answer, extract all mentioned legal sections, clauses, or acts.
Build a structured reasoning graph in JSON format like:
{{
  "nodes": [
    {{"type": "Section", "name": "Section 302", "meaning": "Punishment for murder"}},
    {{"type": "Clause", "name": "(1)", "meaning": "Death penalty"}}
  ],
  "relations": [
    {{"from": "Section 302", "to": "(1)", "relation": "defines"}}
  ]
}}

Text:
{context_text}

Answer:
{base_answer}
    """
    extracted = ask_groq(extraction_prompt)

    try:
        graph_json = json.loads(re.search(r"\{.*\}", extracted, re.DOTALL).group())
    except:
        graph_json = {"nodes": [], "relations": []}

    # Reformulated verification prompt for a proper answer
    verify_prompt = f"""
You are a legal expert AI.
Use the following reasoning graph and legal context to produce a **final verified legal answer** to the question.

Be concise and structured:
1. **Direct Answer** – what happens legally to the person or question asked.
2. **Applicable Sections** – list all sections/clauses used (from the graph or text).
3. **Reasoning** – briefly explain how those sections justify the outcome.
4. **Conclusion** – clearly state the legal implication or punishment.

Question:
{user_query}

Context:
{context_text}

Reasoning Graph:
{json.dumps(graph_json, indent=2)}

Initial Answer:
{base_answer}
    """
    verified_output = ask_groq(verify_prompt)
    return graph_json, verified_output


# === Agent Controller with Memory + Graph Verification ===
def legal_agent():
    print("⚖️ Legal Intelligence Agent — Explainable Conversational Mode (type 'exit' to quit)\n")

    while True:
        user_query = input("👤 You: ")
        if user_query.lower() == "exit":
            print("\n👋 Ending session. Conversation memory cleared.")
            break

        conversation_memory.append({"role": "user", "content": user_query})

        # Retrieve context
        docs = search_elastic(user_query)
        context_text = "\n\n".join([d["text"] for d in docs])

        # Generate base answer
        base_prompt = f"""
You are a legal assistant. Answer the user's question clearly using these legal texts.

Question: {user_query}

Context:
{context_text}

Conversation history:
{conversation_memory}
        """
        base_answer = ask_groq(base_prompt)

        # Graph + Verification
        graph_data, verified_output = graph_verifier(context_text, user_query, base_answer)

        conversation_memory.append({"role": "assistant", "content": verified_output})

        # === Output ===
        print("\n⚖️ Verified Legal Answer:\n")
        print(verified_output.strip())

        if graph_data["nodes"]:
            print("\n📘 Sections Referenced:")
            for node in graph_data["nodes"]:
                if node["type"].lower() == "section":
                    print(f"  • {node['name']}: {node.get('meaning', '')}")

            print("\n📊 Reasoning Graph:")
            for rel in graph_data["relations"]:
                print(f"  {rel['from']} ──► ({rel['relation']}) ──► {rel['to']}")

        print("\n💾 Memory updated.\n")

# === Run Agent ===
if __name__ == "__main__":
    legal_agent()
