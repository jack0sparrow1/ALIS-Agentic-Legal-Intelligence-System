# ALIS - Agentic Legal Intelligence System

An AI-powered conversational assistant that answers Indian legal questions using semantic search and LLM reasoning.

## Overview

ALIS retrieves relevant legal documents using **FAISS** (Facebook AI Similarity Search) and generates explainable answers backed by specific legal sections. It combines vector embeddings, semantic search, and LLM reasoning for accurate legal Q&A.

## Features

-  **Semantic Search**: Find relevant legal documents using embeddings (not keyword matching)
-  **LLM Reasoning**: Generate accurate answers using Groq API
-  **Reasoning Graphs**: Visualize which sections are referenced
-  **Conversational**: Multi-turn chat with memory
-  **Legal Focus**: Trained on Indian Penal Code, IT Act 2000, CRPC

##  Architecture

```
User Question
    ↓
[Encode Query → FAISS Search]
    ↓
Top-3 Relevant Sections
    ↓
[Groq LLM Reasoning]
    ↓
Legal Answer + References
    ↓
[Graph Verification]
    ↓
Display with Reasoning Chain
```

### Tech Stack

| Component | Technology |
|-----------|------------|
| **Retrieval** | FAISS (Vector similarity search) |
| **Embeddings** | SentenceTransformer (all-MiniLM-L6-v2, 384-dim) |
| **LLM** | Groq API (llama-3.1-8b-instant) |
| **UI** | Streamlit |
| **Language** | Python 3.7+ |

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- ~200MB disk space
- GROQ API key (free at https://console.groq.com)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/ALIS.git
cd ALIS
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up credentials**
Create `.env` file in project root:
```
GROQ_API_KEY=your_groq_api_key_here
```

5. **Run the application**
```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

## 📖 Usage

Ask legal questions in natural language:
- "What is punishment for murder?"
- "What is hacking law in India?"
- "What is theft under IPC?"
- "Rights of consumer under consumer protection act?"

The system will:
1. Search relevant legal sections
2. Generate an answer with citations
3. Show reasoning chain with section references

##  Project Structure

```
ALIS/
├── app.py                          # Main Streamlit application
├── requirements.txt                # Python dependencies
├── .env                           # API keys (not in git)
├── .gitignore                     # Git ignore rules
├── data/
│   ├── legal_corpus.jsonl         # Main legal corpus
│   └── preprocessed_data/
│       ├── ipc_corpus.jsonl       # Indian Penal Code
│       ├── it_act_corpus.jsonl    # IT Act 2000
│       └── crpc_corpus.jsonl      # Criminal Procedure Code
├── data_preprocessing/            # Data pipeline scripts
│   ├── IPC_preprocessing.py
│   ├── IT_ACT_preprocessing.py
│   └── crpc_preprocessing.py
├── src/                          # Utility modules
│   ├── agent-controller.py
│   ├── memory_integration.py
│   └── graph_verification.py
└── docs/                         # Documentation
    ├── FAISS_DEEP_DIVE.md
    ├── ELASTICSEARCH_DEEP_DIVE.md
    └── INTERVIEW_GUIDE.md
```

##  How It Works

### 1. Indexing Phase (On Startup)
- Load 2,400+ legal documents from JSONL files
- Encode each document to 384-dimensional vectors
- Build FAISS index for fast similarity search
- **Time**: ~5-10 seconds first run, cached after

### 2. Query Phase (Per User Question)
- Encode query to same 384-dimensional vector space
- FAISS finds 3 most similar documents (1-5ms)
- Pass documents to Groq LLM

### 3. Reasoning Phase
- LLM generates answer with section references
- Extract legal sections as reasoning graph
- Display answer with citations

## 🎓 Key Technical Decisions

### Why FAISS?
- **Fast**: 1-5ms per query (vs 50-100ms with Elasticsearch)
- **Simple**: Pure Python, no server needed
- **Portable**: Works offline, any environment
- **Perfect for MVP**: Sufficient for 2,400 documents

### Why Semantic Search?
Legal domain has multiple ways to express same concept:
- "Unauthorized access" = "Hacking"
- "Murder" = "Homicide"
- Semantic search captures these relationships

### Why SentenceTransformer?
- Lightweight (22MB model)
- Optimized for speed (1000+ docs/sec)
- Pre-trained on legal + general text
- No licensing issues

## 📊 Performance

| Metric | Value |
|--------|-------|
| First startup | ~5-10 seconds |
| Query latency | ~20-25ms |
| Memory usage | ~130MB |
| Document corpus | ~2,400 sections |
| Query throughput | ~40 queries/sec |

##  Security

-  Credentials in `.env` (never committed)
-  Uses environment variables for API keys
-  Ready for Streamlit Secrets (production)
-  No hardcoded credentials

##  Documentation

Comprehensive documentation available in `docs/`:

- **FAISS_DEEP_DIVE.md**: How current FAISS implementation works
- **ELASTICSEARCH_DEEP_DIVE.md**: Historical Elasticsearch architecture
- **INTERVIEW_GUIDE.md**: Ready-to-use interview explanations
- **DOCUMENTATION_INDEX.md**: Navigation guide for all docs

##  Future Improvements

- [ ] Incremental indexing for new documents
- [ ] Hybrid search (semantic + keyword)
- [ ] Multi-language support
- [ ] Distributed FAISS for scaling
- [ ] Fine-tuned embedding model on legal corpus
- [ ] Caching layer for popular queries
- [ ] Real-time corpus updates

##  Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Send a pull request

##  License

This project is open source and available under the MIT License.

##  Support

For questions or issues:
1. Check documentation in `docs/`
2. Review `INTERVIEW_GUIDE.md` for architecture questions
3. Check existing GitHub issues
4. Create a new issue with details

##  Interview Talking Points

**What**: ALIS is a legal AI system that answers Indian law questions
**How**: Uses FAISS for semantic search + Groq LLM for reasoning
**Why FAISS**: Simple, fast, portable - ideal for MVP
**Key Innovation**: Semantic search captures meaning, not just keywords

See `docs/INTERVIEW_GUIDE.md` for detailed explanation.

---

Built with ❤️ for explainable legal AI
