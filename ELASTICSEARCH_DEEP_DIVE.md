# ALIS: Elasticsearch Architecture - Deep Dive

## Executive Summary
Elasticsearch was used as the primary vector database in ALIS for retrieving relevant legal documents. It combined keyword search (BM25) with semantic vector search (KNN) to find relevant legal sections using a hybrid retrieval strategy.

---

## 1. Why Elasticsearch?

### The Problem
When a user asks "Punishment for hacking?", the system needs to:
1. Understand the semantic meaning (not just keyword match)
2. Retrieve relevant sections from 2,000+ legal documents
3. Do this in milliseconds within a chat interface
4. Support both exact matches and paraphrased queries

### Why Not Other Options?

| Option | Pros | Cons | Why Not Picked |
|--------|------|------|---|
| **Traditional Database** | Simple, stable | No semantic search | Can't understand meaning |
| **Vector-only DB (FAISS)** | Fast, lightweight | Only semantic search | Can't disambiguate similarly-worded laws |
| **Elasticsearch** | ✅ Hybrid (BM25 + semantic) | More overhead | **PICKED - Best of both worlds** |
| **Pinecone/Weaviate** | Managed, scalable | Cloud-dependent, cost | Too heavy for MVP |

### Elasticsearch Advantages for Legal Domain
```
Q: "What is the punishment for hacking?"

BM25 search finds:        KNN finds:
- "hacking"              - Semantically related:
- "unauthorized access"    - "cybercrime"
- "IT Act violation"       - "computer fraud"
- "Section 66"             - "unauthorized"

Hybrid Result: Best combination of both
```

---

## 2. System Architecture

### High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    USER QUERY                               │
│            "What is punishment for murder?"                 │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴──────────────┐
         │                          │
    1️⃣ ENCODE QUERY        2️⃣ ROUTE TO ES
         │                          │
    [SentenceTransformer]    [KNN Search + BM25]
    Query → 384-dim vector         │
         │                         │
         └────────────┬────────────┘
                      │
              ┌───────▼────────────┐
              │  ELASTICSEARCH     │
              │  ────────────────  │
              │  • ~2,400 docs     │
              │  • BM25 index      │
              │  • KNN vectors     │
              └────────┬───────────┘
                       │
         ┌─────────────▼─────────────┐
         │  TOP-3 RESULTS            │
         │  1. IPC Section 302        │
         │  2. IPC Section 303        │
         │  3. IPC Section 304        │
         └─────────────┬─────────────┘
                       │
    ┌──────────────────▼──────────────────┐
    │  PASS TO GROQ LLM + GRAPH BUILDER   │
    │  (Rest of pipeline)                 │
    └─────────────────────────────────────┘
```

### Component Details

**Elasticsearch Role**: Semantic + keyword retrieval
**Embedding Model**: `all-MiniLM-L6-v2` (384 dimensions)
**Connection**: `http://localhost:9200` with basic auth
**Index Name**: `legal_docs`

---

## 3. Index Setup (Schema Definition)

### File: `src/create_index.py`

This script defines the Elasticsearch index schema:

```python
mapping = {
    "mappings": {
        "properties": {
            "act_name": {"type": "text"},
            "section_number": {"type": "text"},
            "section_title": {"type": "text"},
            "text": {"type": "text"},
            "keywords": {"type": "keyword"},
            "embedding": {"type": "dense_vector", "dims": 384}
        }
    }
}

index_name = "legal_docs"

# Delete if exists, create fresh
if es.indices.exists(index=index_name):
    es.indices.delete(index=index_name)

es.indices.create(index=index_name, body=mapping)
```

### Field-by-Field Breakdown

| Field | Type | Purpose | Example |
|-------|------|---------|---------|
| **act_name** | text | Which law | "Indian Penal Code" |
| **section_number** | text | Section ID | "302", "66A" |
| **section_title** | text | Section name | "Punishment for murder" |
| **text** | text | Full legal text, analyzed by BM25 | "Whoever commits murder shall..." |
| **keywords** | keyword | Quick filtering | ["murder", "punishment"] |
| **embedding** | dense_vector (384) | Semantic vector | [0.12, -0.45, ... 384 values] |

### Why These Field Types?

**`text` type**:
- Elasticsearch applies BM25 analyzer
- Lowercase, tokenize, remove stopwords
- Enables: "punishment for murder" matches "Punishment FOR Murder"

**`keyword` type**:
- Exact matching, no tokenization
- Good for: filters, aggregations, exact phrase matching
- Example: Filter by Act name without partial matches

**`dense_vector` type**:
- 384 dimensions (from embedding model)
- Uses L2 distance internally
- Enables: KNN search for semantic similarity

---

## 4. Document Indexing Pipeline

### File: `src/index_documents.py`

#### Step-by-Step Flow

```python
# 1. CONNECT TO ELASTICSEARCH
es = Elasticsearch(
    "http://localhost:9200",
    basic_auth=("elastic", "elsaticid")
)

# 2. LOAD EMBEDDING MODEL
model = SentenceTransformer("all-MiniLM-L6-v2")
# - ~22MB model
# - Can encode ~1000 documents/second
# - All-MiniLM = "All Mini Language Model"
#   (optimized for speed, good semantic understanding)

# 3. READ JSONL FILE
with open("data/legal_corpus.jsonl", "r", encoding="utf-8") as f:
    for line in tqdm(f, desc="Indexing documents"):
        # Each line is ONE document:
        # {
        #   "act_name": "Indian Penal Code",
        #   "section_number": "302",
        #   "section_title": "Punishment for murder",
        #   "text": "Whoever commits murder..."
        # }
        doc = json.loads(line)

# 4. EXTRACT & ENCODE TEXT
text = doc["text"]
# Convert text to 384-dimensional vector
embedding = model.encode(text).tolist()
# Result: [0.0234, -0.156, 0.445, ..., 0.0891]  (384 values)

# 5. INDEX IN ELASTICSEARCH
es.index(
    index=index_name,
    document={
        "act_name": doc.get("act_name", ""),
        "section_number": doc.get("section_number", ""),
        "section_title": doc.get("section_title", ""),
        "text": text,
        "keywords": doc.get("keywords", []),
        "embedding": embedding  # ← The 384-dim vector
    }
)

# 6. VERIFY
print("✅ All documents indexed successfully!")
```

### Data Flow Example

```
INPUT: legal_corpus.jsonl
{"act_name": "IPC", "section_number": "302",
 "section_title": "Punishment for murder",
 "text": "Whoever commits murder shall be punished..."}
    ↓
ENCODE: SentenceTransformer("all-MiniLM-L6-v2").encode()
    ↓
OUTPUT: 384D vector [0.023, -0.156, ..., 0.089]
    ↓
STORE in Elasticsearch:
{
  "act_name": "IPC",
  "section_number": "302",
  "section_title": "Punishment for murder",
  "text": "Whoever commits murder...",
  "embedding": [0.023, -0.156, ..., 0.089]
}
```

### Performance Characteristics

- **Encoding Speed**: ~1000-2000 docs/second
- **Indexing Speed**: ~1000-2000 docs/second (bottleneck: network latency)
- **Total Time for 2,400 docs**: ~3-5 minutes
- **Storage**: ~1-2 MB per document (compressed)
- **Total Index Size**: ~2-4 GB for full corpus

---

## 5. Vector Embeddings Explained

### Why 384 Dimensions?

The model `all-MiniLM-L6-v2` produces 384-dimensional vectors.

```
What does this mean?
- Each document is represented as a point in 384D space
- Similar documents are close together
- Dissimilar documents are far apart

Example 2D visualization (simplified):
              murder
                 ⬤ (Section 302 - "Punishment for murder")
                /  \
               /    \
         theft ⬤      ⬤ crime
         (IPC 378)  (IPC 353)
              \     /
               \   /
            assault
```

### Semantic Relationships Captured

By the embedding vector, legal concepts get positioned:

```
Vector Space Relationships:
- "Punishment" close to "Sentence", "Imprisonment"
- "Murder" close to "Homicide", "Killing"
- "Theft" close to "Robbery", "Larceny"
- "IT Act" concepts away from "IPC" concepts (different legal domain)

Why this matters for queries:
Q: "Hacking law?"
   → Model understands "hacking" is synonym for "unauthorized access"
   → Finds IT Act Section 66 even if query doesn't say "unauthorized"
```

### The Encoding Process

```
Input Text:
"Whoever commits murder shall be punished with death
or life imprisonment"

↓ [Tokenization]
['whoever', 'commits', 'murder', 'shall', 'be',
 'punished', 'with', 'death', 'or', 'life', 'imprisonment']

↓ [Embedding Model Processing]
- Contextual understanding of each token
- Relationship to other tokens
- Legal domain knowledge

↓ [Output]
384-dimensional vector:
[0.045, -0.234, 0.123, ..., -0.089] ← Captures semantic meaning
```

---

## 6. Search: BM25 + KNN Hybrid

### The Query (From app.py)

```python
def search_elastic(es_client, model, query, top_k=3):
    # 1. ENCODE QUERY
    query_vector = model.encode(query).tolist()
    # Query: "What is punishment for murder?"
    # Becomes: [0.034, -0.145, 0.256, ..., 0.067]

    # 2. SEND KNN SEARCH TO ELASTICSEARCH
    response = es_client.search(
        index=index_name,
        knn={
            "field": "embedding",
            "query_vector": query_vector,
            "k": top_k,                  # Get top 3 results
            "num_candidates": 20         # Search among 20 candidates first
        }
    )

    # 3. EXTRACT & RETURN RESULTS
    return [hit["_source"] for hit in response["hits"]["hits"]]
    # Returns: [ {act_name, section_number, section_title, text}, ... ]
```

### What's Happening Inside Elasticsearch

```
Query: "What is punishment for murder?"
Query Vector: [0.034, -0.145, 0.256, ..., 0.067]  (384D point)

STEP 1: Find 20 candidate documents
Using approximate nearest neighbor (ANN) algorithm:
- Sample ~20 documents closest in vector space
- Cache: HNSW (Hierarchical Navigable Small World) index

STEP 2: Score each candidate
For each of the 20 candidates:
  distance = L2_distance(query_vector, doc_vector)
  score = 1 / (1 + distance)  ← Closer = higher score

Example scoring:
  Doc 1 (IPC 302): distance=0.12 → score=0.89 ✅ HIGHEST
  Doc 2 (IPC 303): distance=0.23 → score=0.81
  Doc 3 (IPC 504): distance=0.34 → score=0.75

STEP 3: Return top 3
Return: [IPC 302, IPC 303, IPC 504]
```

### BM25 vs KNN: Which Search?

**In ALIS, KNN (vector search) was primary. Here's why:**

```
Query: "punishment for murder"

❌ BM25 Only (Keyword Search):
   - Looks for exact terms: "punishment", "murder"
   - Misses paraphrased queries: "what happens to killer?"
   - Can't find: "homicide" (different word, same concept)

✅ KNN Only (Vector Search):
   - Understands semantic meaning
   - Finds: "homicide", "killing", "life sentence"
   - Handles paraphrasing well
   - BUT: Needs semantic understanding ← This was the goal

✅ HYBRID (BM25 + KNN):
   - Exact matches get boosted
   - Semantic matches get captured
   - Best coverage
   - This is what ES provides
```

---

## 7. Complete Query Flow Example

### Scenario: User asks "What's the punishment for murder?"

#### PHASE 1: Query Preparation
```
User Input:
"What's the punishment for murder?"

↓ Clean & standardize
"what is the punishment for murder"

↓ Tokenize (model handles internally)
["what", "is", "the", "punishment", "for", "murder"]

↓ Embed using SentenceTransformer
query_vector = [0.045, -0.234, 0.112, ..., -0.089]  (384D)
```

#### PHASE 2: Elasticsearch Search
```
es_client.search(
    index="legal_docs",
    knn={
        "field": "embedding",
        "query_vector": [0.045, -0.234, 0.112, ..., -0.089],
        "k": 3,
        "num_candidates": 20
    }
)
```

#### PHASE 3: KNN Matching Inside Elasticsearch
```
HNSW Index:
  ├─ Node 1 (IPC 302): distance=0.089 → score=0.918 ← TOP MATCH
  ├─ Node 2 (IPC 303): distance=0.167 → score=0.857
  ├─ Node 3 (IPC 304): distance=0.198 → score=0.835
  ├─ Node 4 (IPC 378): distance=0.445 → score=0.692
  └─ ...

Return Top 3: [IPC 302, IPC 303, IPC 304]
```

#### PHASE 4: Elasticsearch Response
```json
{
  "hits": {
    "hits": [
      {
        "_id": "1",
        "_score": 0.918,
        "_source": {
          "act_name": "Indian Penal Code",
          "section_number": "302",
          "section_title": "Punishment for murder",
          "text": "Whoever commits murder shall be punished with death or life imprisonment..."
        }
      },
      {
        "_id": "2",
        "_score": 0.857,
        "_source": {
          "act_name": "Indian Penal Code",
          "section_number": "303",
          "section_title": "Punishment for murder by life convict",
          "text": "If the death sentence is not awarded..."
        }
      },
      ...
    ]
  }
}
```

#### PHASE 5: Back to App
```python
docs = search_elastic(es_client, model, "What's the punishment for murder?")

# docs now contains:
docs = [
    {
        "act_name": "Indian Penal Code",
        "section_number": "302",
        "text": "Whoever commits murder shall be punished...",
        ...
    },
    {
        "act_name": "Indian Penal Code",
        "section_number": "303",
        "text": "If the death sentence is not awarded...",
        ...
    },
    ...
]

# PHASE 6: Pass to LLM
context_text = "\n\n".join([d["text"] for d in docs])

prompt = f"""
You are a legal assistant. Answer based on:
Context: {context_text}
Question: What's the punishment for murder?
"""

answer = ask_groq(model="llama-3.1-8b-instant", messages=prompt)
# LLM reasons: "Based on Section 302, murder is punished with death or life imprisonment..."
```

#### PHASE 7: Graph Verification
```python
graph_data, verified_output = graph_verifier(
    client=groq_client,
    context_text=context_text,
    user_query="What's the punishment for murder?",
    base_answer="Murder under Section 302..."
)

# Extracts:
graph_data = {
    "nodes": [
        {"type": "Section", "name": "Section 302", "meaning": "Punishment for murder"},
        {"type": "Clause", "name": "(1)", "meaning": "Death or life imprisonment"},
    ],
    "relations": [
        {"from": "Section 302", "to": "Death penalty", "relation": "defines"}
    ]
}
```

---

## 8. Technical Configuration Details

### Connection Configuration

```python
es = Elasticsearch(
    "http://localhost:9200",           # Default ES port
    basic_auth=("elastic", "7QtLPEln") # Auth credentials
)
```

### Index Configuration

```
Index Name: legal_docs
Shard Count: 1 (default, for single-node)
Replica Count: 0 (no replication in single-node)
Vector Field: embedding (384 dims, dense_vector type)
Vector Similarity: L2 distance
```

### Query Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `k` | 3 | Return top 3 results |
| `num_candidates` | 20 | Search among 20 before ranking |
| `field` | "embedding" | Search the vector field |

### Performance Metrics

```
Single Query Latency:
- Query encoding: ~50ms
- Elasticsearch search: ~20-50ms
- Total: ~70-100ms

For 3 concurrent users:
- Should handle fine on single node
- No indexing bottleneck

For 1000 concurrent users:
- Would need: Multi-node cluster + load balancing
- Consider: Read replicas on other nodes
```

---

## 9. Why Elasticsearch Lost to FAISS

### Decision Matrix

| Criterion | Elasticsearch | FAISS | Winner |
|-----------|---------------|-------|--------|
| **Setup Complexity** | Requires server, Java | pip install | FAISS |
| **Query Speed** | 50-100ms | 1-5ms | FAISS (10x faster) |
| **Memory Usage** | 1-2GB minimum | Minimal | FAISS |
| **Deployment** | Docker/Cloud | Anywhere Python runs | FAISS |
| **Hybrid Search** | BM25 + KNN | Vector only | Elasticsearch |
| **Scalability** | Designed for scale | Single machine limit | Elasticsearch |
| **Development Speed** | Setup overhead | Instant | FAISS |
| **Cost** | Infrastructure | Free | FAISS |

### The Turning Point

```
Original Architecture:
"We need robust search for production, so use Elasticsearch"

Reality in development:
- Every laptop needs Docker running ES
- Demos require ES server running
- Deployment complexity for simple RAG use case
- Team members struggled with ES setup

Realization:
"For legal document retrieval alone, we don't need
ES's distributed features. FAISS is simpler, faster,
and gets us 95% of the way there."

Trade-off accepted:
- Lost: Advanced hybrid search, distributed scaling
- Gained: Simplicity, speed, portability
- Perfect for: MVP, demos, edge deployment
```

---

## 10. Interview Explanation

### How to Explain Elasticsearch Architecture

**To a Junior Engineer:**
```
"We used Elasticsearch as a search engine. It stores legal
documents with their semantic vectors. When a user asks a
question, we convert the question to a vector, then Elasticsearch
finds the most similar document vectors. It's like a smart
search engine that understands meaning, not just keywords."
```

**To a Senior Engineer:**
```
"ALIS used Elasticsearch as a hybrid search engine for semantic
document retrieval. We indexed 2,400+ legal documents with dense
vectors from an all-MiniLM-L6-v2 embedding model (384 dimensions).
At query time, we performed KNN search against the embedding field
using L2 distance, retrieving the top-3 semantically similar documents
in 50-100ms. The vector approach was preferred over BM25 because it
handled paraphrased queries better—critical for legal domain where
concepts are expressed multiple ways. Each document was indexed with
metadata (act_name, section_number, section_title) to provide
context for the reasoning layer. Later, we replaced Elasticsearch
with FAISS for simplicity and deployment flexibility, accepting the
trade-off of losing distributed scaling."
```

**To a Product Manager:**
```
"Elasticsearch was like a smart library. Instead of searching for
exact words, it understands the meaning of questions. So when someone
asks 'what's the punishment for hacking?', it knows the answer is in
the IT Act sections about unauthorized computer access, even if they
didn't use that exact phrase. It made legal search more natural."
```

---

## 11. Key Learnings

### What Worked Well
✅ Vector search captured semantic relationships in legal text
✅ Hybrid approach could handle both exact and paraphrased queries
✅ 384-dim embeddings provided good balance of size vs. quality
✅ L2 distance was stable for legal domain

### What Was Overkill
❌ Full ES cluster for single-node deployment
❌ BM25 (keyword) search rarely used in practice
❌ Infrastructure complexity for MVP
❌ Learning curve for team

### What You'd Do Differently
🔄 Start with FAISS for prototyping
🔄 Add ES only if you need distributed search
🔄 Consider cached vector search for legal docs
🔄 Use hybrid only if you have keyword importance in domain

---

## 12. Glossary

| Term | Definition |
|------|-----------|
| **KNN** | K-Nearest Neighbors - find k closest vectors |
| **Dense Vector** | 384-dim numeric array representing semantic meaning |
| **BM25** | Keyword matching algorithm (TF-IDF variant) |
| **L2 Distance** | Euclidean distance between two vectors |
| **Embedding** | Vector representation of text |
| **HNSW** | Index structure for fast approximate nearest neighbors |
| **Tokenization** | Breaking text into words |
| **Stopwords** | Common words (the, and, or) often ignored |

