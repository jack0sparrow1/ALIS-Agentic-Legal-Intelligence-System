# ALIS Project - Complete Understanding

## What is ALIS?
**Agentic Legal Intelligence System** - An AI-powered conversational assistant that answers Indian legal questions by:
1. Retrieving relevant legal documents
2. Reasoning through context using LLM
3. Verifying answers with structured graphs
4. Providing explainable decisions with section references

## Why Elasticsearch → FAISS Transition?

### Elasticsearch Limitations (Current Implementation):
- **Resource Heavy**: Requires running Elasticsearch server locally/cloud
- **Overhead**: Needs Docker/Java runtime, additional memory
- **Cost**: Cloud deployments incur costs
- **Complexity**: Setup/maintenance burden for simple retrieval
- **Scaling Issues**: For large legal document bases

### FAISS Advantages:
- **Lightweight**: Python-only, no external services
- **Fast**: CPU/GPU optimized similarity search
- **Scalable**: Handles millions of documents efficiently
- **Free**: Just an open-source library
- **Portable**: Works anywhere Python runs
- Perfect for: RAG systems, offline use, edge deployment

**Your transition decision is technically sound** - FAISS is ideal for legal document retrieval at scale.

## Project Architecture

### 1. Data Pipeline (data_preprocessing/)
**Input**: Raw legal texts (IPC, IT Act, CRPC)
**Processing**:
- Parse raw documents into structured sections
- Extract keywords via NLP
- Convert to JSONL format (act_name, section_number, title, text, keywords)

**Files**:
- `IPC_preprocessing.py` - Indian Penal Code
- `IT_ACT_preprocessing.py` - Information Technology Act
- `crpc_preprocessing.py` - Criminal Procedure Code

### 2. Retrieval System (src/)
**Old approach (current)**: Elasticsearch + KNN vectors
**New approach (FAISS)**: In-memory vector DB + similarity search

**Key files**:
- `index_documents.py` - Load JSONL → Elasticsearch with embeddings
- `search_elastic()` - Vector similarity search
- Embeddings: `SentenceTransformer("all-MiniLM-L6-v2")` - 384-dim vectors

### 3. Reasoning Layer
**LLM**: Groq API (llama-3.1-8b-instant)
**Process**:
- Take user query
- Retrieve top-3 documents via FAISS
- Pass context to LLM for reasoning
- Get verified legal answer

### 4. Memory/Graph Verification (Phase 4-5)
**Memory**: Conversation history stored in session state
**Graph Verification**:
- Extract legal sections as nodes
- Show relationships between clauses
- Provide reasoning chain visualization
- Store conversation with embeddings

### 5. Frontend (app.py)
**Framework**: Streamlit
**Flow**:
1. User enters legal question
2. Retrieval → search FAISS
3. Reasoning → send to Groq LLM
4. Verification → build reasoning graph
5. Display answer + referenced sections + reasoning chain

## Technology Stack
| Component | Technology |
|-----------|------------|
| Vector DB | FAISS (→ migrate from Elasticsearch) |
| Embeddings | SentenceTransformer (all-MiniLM-L6-v2, 384-dim) |
| LLM Reasoning | Groq API (llama-3.1-8b-instant) |
| UI | Streamlit |
| Backend | Python (No external servers needed with FAISS) |

## Project Phases
| Phase | Status | Focus |
|-------|--------|-------|
| 1 | ✅ Done | Data indexing |
| 2 | ✅ Done | Single-turn Q&A |
| 3 | ✅ Done | Agent loop (search→reason→verify) |
| 4 | ✅ Done | Memory persistence |
| 5 | ✅ Done (Current) | Graph-based reasoning + structured analysis |
| 6 | 🚧 In Progress | UI + deployment (using Streamlit) |

## Key Interview Talking Points

### Problem Statement
- Legal domain: Complex, specialized knowledge, regulatory compliance needed
- Challenge: Making legal Q&A accessible without expensive lawyers
- Solution: AI agent that reasons and provides explainable decisions

### Architecture Highlights
1. **Retrieval Strategy**: Vector search (embeddings) instead of keyword search
   - Why: Captures semantic meaning ("punishment" ≈ "imprisonment")

2. **Reasoning**: Two-stage LLM
   - Stage 1: Generate initial answer
   - Stage 2: Verify and refine

3. **Explainability**: Graph-based reasoning
   - Show exact sections referenced
   - Display logical connections
   - Build trust with users

### Technical Decisions
1. **Elasticsearch → FAISS**: Trade-off between functionality and simplicity
2. **Groq API**: Fast, cheap LLM inference vs OpenAI
3. **SentenceTransformer**: Lightweight, no licensing issues
4. **Streamlit**: Quick iteration and prototyping

### Scalability Path
- Current: Streamlit + FAISS (single instance)
- Future: Deploy to Streamlit Cloud or FastAPI backend
- Data: Scale to 10k+ sections with FAISS indexing
- Load: Distributed LLM inference with Groq API

## Implementation Details
- **Credentials**: Now uses environment variables (.env) instead of hardcoded
- **Session State**: Chat history persists within session
- **Conversation Memory**: Stored as embeddings for semantic search
- **Error Handling**: Graph extraction may fail → fallback to empty graph

## Related Documentation
- **ELASTICSEARCH_DEEP_DIVE.md**: Comprehensive technical explanation of how ES worked
- **ELASTICSEARCH_VISUAL.md**: Visual diagrams and examples of ES architecture
- **FAISS_MIGRATION.md**: Summary of migration from ES to FAISS
