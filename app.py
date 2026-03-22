import streamlit as st
import os
import json
import re
import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from groq import Groq
import faiss

# Load environment variables from .env file
load_dotenv()

# === Security & Config ===
# Load secrets from environment variables (via .env file)
# or from Streamlit's secrets management (.streamlit/secrets.toml)
# DO NOT hardcode your keys here.

def get_secret(name):
    """Retrieve secret from environment variables or Streamlit secrets."""
    # First try environment variables (from .env) - prioritize for local dev
    env_value = os.getenv(name)
    if env_value:
        return env_value

    # Then try Streamlit secrets (for deployed apps)
    try:
        return st.secrets[name]
    except Exception:
        return None

GROQ_API_KEY = get_secret("GROQ_API_KEY")
DATA_DIR = "data"

# === Cached Resource Loading ===
# Use Streamlit's caching to load models and FAISS index once.
@st.cache_resource
def load_resources():
    """Loads SentenceTransformer, FAISS index, documents, and Groq client."""
    try:
        # Load embedding model
        embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

        # Load all legal documents from JSONL files
        documents = []
        jsonl_files = [
            os.path.join(DATA_DIR, "legal_corpus.jsonl"),
            os.path.join(DATA_DIR, "preprocessed_data", "ipc_corpus.jsonl"),
            os.path.join(DATA_DIR, "preprocessed_data", "it_act_corpus.jsonl"),
            os.path.join(DATA_DIR, "preprocessed_data", "crpc_corpus.jsonl"),
        ]

        for jsonl_file in jsonl_files:
            if os.path.exists(jsonl_file):
                try:
                    with open(jsonl_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                documents.append(json.loads(line))
                except Exception as e:
                    st.warning(f"Could not load {jsonl_file}: {e}")

        if not documents:
            st.error(f"No documents found in {DATA_DIR}. Please ensure JSONL files are present.")
            return None, None, None

        # Create embeddings for all documents
        texts = [doc.get("text", "") for doc in documents]
        embeddings = embedding_model.encode(texts, show_progress_bar=False)
        embeddings = np.array(embeddings).astype('float32')

        # Build FAISS index
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings)

        st.success(f"✅ Loaded {len(documents)} legal documents into FAISS index")

    except Exception as e:
        st.error(f"Failed to load resources: {e}")
        return None, None, None

    if not GROQ_API_KEY:
        st.error("GROQ_API_KEY not found. Please set it in your environment variables or Streamlit secrets.")
        return None, None, None

    groq_client = Groq(api_key=GROQ_API_KEY)

    return index, embedding_model, documents, groq_client

# Load models at the start
resources = load_resources()
if resources and len(resources) == 4:
    faiss_index, embedding_model, documents, groq_client = resources
else:
    faiss_index, embedding_model, documents, groq_client = None, None, None, None

# === Helper: Retrieve top documents using FAISS ===
def search_faiss(model, documents, query, top_k=3):
    """Search using FAISS vector similarity."""
    query_embedding = model.encode(query).reshape(1, -1).astype('float32')
    distances, indices = faiss_index.search(query_embedding, top_k)

    results = []
    for idx in indices[0]:
        if 0 <= idx < len(documents):
            results.append(documents[idx])

    return results

# === Helper: Ask Groq ===
# (No changes from your original code, just passing client as argument)
def ask_groq(client, prompt):
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content

# === Phase 5: Structured Reasoning (Graph + Verification) ===
# (Modified to accept groq_client as an argument)
def graph_verifier(client, context_text, user_query, base_answer):
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
    extracted = ask_groq(client, extraction_prompt)

    try:
        # Use a more robust regex to find the JSON block
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", extracted, re.DOTALL)
        if not json_match:
            json_match = re.search(r"(\{.*?\})", extracted, re.DOTALL)
        
        graph_json = json.loads(json_match.group(1))
    except Exception as e:
        print(f"Graph JSON parsing failed: {e}")
        graph_json = {"nodes": [], "relations": []} # Default to empty graph

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
    verified_output = ask_groq(client, verify_prompt)
    return graph_json, verified_output

# === Streamlit UI ===

st.title("⚖️ Agentic Legal Intelligence System")
st.caption("Explainable Conversational Mode")

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display past messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # If assistant message has a graph, display it
        if "graph" in message and message["graph"].get("nodes"):
            with st.expander("Show Reasoning & Referenced Sections"):
                st.subheader("📘 Sections Referenced:")
                for node in message["graph"]["nodes"]:
                    if node.get("type", "").lower() == "section":
                        st.markdown(f"  • **{node['name']}**: {node.get('meaning', 'No meaning extracted')}")

                st.subheader("📊 Reasoning Graph:")
                for rel in message["graph"]["relations"]:
                    st.markdown(f"  `{rel['from']}` ──► (*{rel['relation']}*) ──► `{rel['to']}`")
                
                st.subheader("Raw Graph JSON")
                st.json(message["graph"])

# Stop the app if models failed to load
if not faiss_index or not embedding_model or not groq_client or not documents:
    st.error("Application resources could not be loaded. Please check configuration and restart.")
    st.stop()

# Handle new user input
if user_query := st.chat_input("Ask a legal question..."):
    # Add user message to state and display
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    # Start processing assistant response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing legal texts and building reasoning..."):
            try:
                # 1. Retrieve context
                docs = search_faiss(embedding_model, documents, user_query)
                context_text = "\n\n".join([d["text"] for d in docs])

                # 2. Generate base answer
                # Prepare conversation history for the prompt
                history_for_prompt = [
                    f"{msg['role']}: {msg['content']}" for msg in st.session_state.messages
                ]
                
                base_prompt = f"""
You are a legal assistant. Answer the user's question clearly using these legal texts.

Question: {user_query}

Context:
{context_text}

Conversation history:
{history_for_prompt}
                """
                base_answer = ask_groq(groq_client, base_prompt)

                # 3. Graph + Verification
                graph_data, verified_output = graph_verifier(
                    groq_client, context_text, user_query, base_answer
                )

                # 4. Display and store the verified response
                st.markdown(verified_output)
                
                # Display the graph components in an expander
                if graph_data.get("nodes"):
                    with st.expander("Show Reasoning & Referenced Sections"):
                        st.subheader("📘 Sections Referenced:")
                        for node in graph_data["nodes"]:
                            if node.get("type", "").lower() == "section":
                                st.markdown(f"  • **{node['name']}**: {node.get('meaning', 'No meaning extracted')}")

                        st.subheader("📊 Reasoning Graph:")
                        for rel in graph_data["relations"]:
                            st.markdown(f"  `{rel['from']}` ──► (*{rel['relation']}*) ──► `{rel['to']}`")
                        
                        st.subheader("Raw Graph JSON")
                        st.json(graph_data)

                # 5. Add full assistant response (with graph) to session state
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": verified_output,
                    "graph": graph_data  # Store the graph data with the message
                })

            except Exception as e:
                st.error(f"An error occurred: {e}")
                # Add error to memory to avoid retrying on full history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Sorry, an error occurred: {e}",
                    "graph": {}
                })