# ALIS Elasticsearch Architecture - Visual Summary

## 🔍 The Big Picture

```
USER ASKS: "Punishment for murder?"
        ↓
  ENCODE TO VECTOR
  [0.045, -0.234, ..., -0.089]  (384 dimensions)
        ↓
  ELASTICSEARCH KNN SEARCH
  Find 3 closest documents
        ↓
  TOP RESULTS:
  ✅ IPC Section 302 (Punishment for murder)
  ✅ IPC Section 303 (Punishment for life convict)
  ✅ IPC Section 304 (Rash/negligent act)
        ↓
  PASS TO LLM FOR REASONING
  GROQ generates answer
        ↓
  BUILD REASONING GRAPH
  Shows referenced sections
        ↓
  DISPLAY TO USER
```

---

## 📊 System Components

```
┌─────────────────────────────────────────────────────────┐
│                    ALIS APP (app.py)                    │
│  - Chat UI (Streamlit)                                  │
│  - Orchestrates search → reason → verify pipeline       │
└────────────────┬────────────────────────────────────────┘
                 │
        ┌────────▼────────────┐
        │  QUERY ENCODER      │
        │ ─────────────────   │
        │ SentenceTransformer │
        │ all-MiniLM-L6-v2    │
        │                     │
        │ Input: Text         │
        │ Output: 384-dim vec │
        └────────┬────────────┘
                 │
   Query: "murdered"          │
          [0.045, ..., -0.089]│
                 │
        ┌────────▼───────────────────────┐
        │   ELASTICSEARCH SERVER          │
        │  (Semantic Search Engine)       │
        │ ─────────────────────────────   │
        │ Index: legal_docs               │
        │ ─────────────────────────────   │
        │ Stores:                         │
        │  - 2,400 legal documents        │
        │  - 384-dim vectors for each     │
        │  - Metadata (section, act)      │
        │ ─────────────────────────────   │
        │ Sends back:                     │
        │ Top 3 most similar documents    │
        └────────┬───────────────────────┘
                 │
        ┌────────▼────────────┐
        │  TOP 3 RESULTS      │
        │                     │
        │ IPC 302: 0.918      │
        │ IPC 303: 0.857      │
        │ IPC 304: 0.835      │
        └────────┬────────────┘
                 │
        ┌────────▼────────────┐
        │   GROQ LLM          │
        │ (Reasoning)         │
        │                     │
        │ Input: Query + docs │
        │ Output: Answer      │
        └────────┬────────────┘
                 │
        ┌────────▼────────────┐
        │  GRAPH BUILDER      │
        │ (Explainability)    │
        │                     │
        │ Build structured    │
        │ reasoning chain     │
        └────────┬────────────┘
                 │
        ┌────────▼────────────┐
        │  DISPLAY TO USER    │
        │  Answer + Graph     │
        └────────────────────┘
```

---

## 🗄️ Elasticsearch Index Structure

```
INDEX: legal_docs

Document Example:
{
  "act_name": "Indian Penal Code",
  "section_number": "302",
  "section_title": "Punishment for murder",
  "text": "Whoever commits murder shall be punished...",
  "keywords": ["murder", "punishment", "death"],
  "embedding": [0.045, -0.234, 0.112, ..., -0.089]  ← 384 values
}

Field Breakdown:
┌─────────────────────────────────────┐
│ act_name: string                    │
│ section_number: string              │
│ section_title: string               │
│ text: string (analyzed by BM25)     │ ← Keyword search
│ keywords: keyword (exact match)     │
│ embedding: dense_vector (384D)      │ ← Vector search
└─────────────────────────────────────┘

Total documents in index: ~2,400
Index size: ~2-4 GB
Vector dimension: 384
Vector metric: L2 distance
```

---

## 🎯 How Vector Search Works

```
STEP 1: Create Vector Space
All legal documents embedded as points in 384D space

        Semantic Space (Simplified to 2D for illustration):

                        murder
                          ⬤ IPC 302 ← Query closest here
                         /  \
                        /    \
                       /      \
              homicide⬤        ⬤ killing
              (IPC 304)        (similar)
                   \          /
                    \        /
                     \      /
                      ⬤─⬜ ← Query vector

        Red ⬜ = User's query "Punishment for murder?"
        Blue ⬤ = Legal sections in vector space

STEP 2: Find K Nearest Neighbors (k=3)
Query vector finds 3 closest document vectors
Distance calculation: L2 = √((x₁-x₂)² + (y₁-y₂)² + ...)

Distances computed:
  Document A: distance=0.089 → score = 0.918 ✅ TOP
  Document B: distance=0.167 → score = 0.857
  Document C: distance=0.198 → score = 0.835
  Document D: distance=0.445 → score = 0.692
  Document E: distance=0.601 → score = 0.625

Return: Top 3

STEP 3: Score Calculation
Score = 1 / (1 + distance)

If distance=0: score=1.0 (perfect match)
If distance increases: score decreases (less similar)
Typical range: 0.5-0.95
```

---

## 📈 Query Execution Timeline

```
User Input: "What is punishment for murder?"
Time:  0ms   │
       │     ├─ Parse input
       │     ├─ Route to search
       5ms   │
       │     ├─ Encode query (SentenceTransformer)
       50ms  │ [SLOW] - Model processing
       │     │
       │     ├─ Create query_vector = [0.045, -0.234, ..., -0.089]
       55ms  │
       │     ├─ Send to Elasticsearch
       │     ├─ HNSW index lookup (~20 candidates)
       │     ├─ Score all 20 candidates
       105ms │ [TOTAL QUERY TIME]
       │     │
       │     └─ Return top 3:
       │        [{IPC 302, text, score: 0.918},
       │         {IPC 303, text, score: 0.857},
       │         {IPC 304, text, score: 0.835}]

       ├─ Pass to LLM (Groq)
       1000ms│ [Takes ~1 second for LLM reasoning]
       │
       ├─ Build reasoning graph
       1200ms│
       │
       ├─ Display result
       1200ms│ Total time: ~1.2 seconds
```

---

## 🔄 Data Pipeline: JSONL → Elasticsearch

```
INPUT FILES: legal_corpus.jsonl, ipc_corpus.jsonl, etc.

Each line in JSONL:
{"act_name": "IPC", "section_number": "302", "section_title": ..., "text": ...}

PIPELINE:
1️⃣  Read JSONL
    ↓
2️⃣  Parse JSON
    doc = {"act_name": "IPC", "section_number": "302", ...}
    ↓
3️⃣  Extract text
    text = "Whoever commits murder shall be punished..."
    ↓
4️⃣  Encode to vector
    embedding_model.encode(text)
    → [0.045, -0.234, 0.112, ..., -0.089]  (384D)
    ↓
5️⃣  Index in Elasticsearch
    es.index(index="legal_docs", document={
      "act_name": "IPC",
      "section_number": "302",
      "text": "Whoever commits murder...",
      "embedding": [0.045, -0.234, ...]
    })
    ↓
OUTPUT: Searchable Elasticsearch index

Performance:
- Encoding: ~1000 docs/second
- Indexing: ~1000 docs/second
- For 2,400 docs: ~2-5 minutes total
- Storage: ~1 MB per document
```

---

## 🎓 Query Examples

### Example 1: Exact Query

```
Q: "Punishment for murder?"

Encoding:
  model.encode("Punishment for murder?")
  → [0.045, -0.234, 0.156, ..., -0.089]

Elasticsearch Search:
  Find vectors similar to [0.045, -0.234, ...]

Results (Top 3):
  1. IPC 302 (score: 0.918) ← Perfect match!
     "Punishment for murder..."

  2. IPC 303 (score: 0.857)
     "Punishment for murder by life convict..."

  3. IPC 304 (score: 0.835)
     "Causing death by rash/negligent act..."
```

### Example 2: Paraphrased Query

```
Q: "What happens if someone kills another person?"

Encoding:
  model.encode("What happens if someone kills...")
  → [0.034, -0.245, 0.142, ..., -0.095]

Note: Different words than "murder", but semantic meaning captured

Elasticsearch Search:
  Even though query says "kills" not "murder",
  vector space knows they're related

Results (Top 3):
  1. IPC 302 (score: 0.89) ← Still top!
     Because embedding understands "kills" = "murder"

  2. IPC 304 (score: 0.81)
     "Death by rash act"

  3. IPC 503 (score: 0.75)
     "Criminal intimidation"

Why Vector Search Wins:
If we only used keyword search:
  "kills" ≠ "murder" → wouldn't find IPC 302!
```

### Example 3: Domain-Specific Query

```
Q: "Hacking law?"

Encoding:
  model.encode("Hacking law?")
  → [0.023, -0.267, 0.198, ..., -0.107]

Elasticsearch Search:
  Vectors for IT Act sections are different region of space
  But semantic model knows "hacking" relates to IT Act

Results (Top 3):
  1. IT Act Section 66 (score: 0.91)
     "Unlawful access to computer systems"

  2. IT Act Section 66A (score: 0.84)
     "Punishment for sending offensive material"

  3. IPC Section 420 (score: 0.72)
     "Cheating" (related but different)

Why This Works:
Encoding model trained on general text + legal concepts
understands relationship between "hacking" and "unauthorized access"
even if they're different words
```

---

## ⚖️ Elasticsearch vs FAISS Decision

```
                  ELASTICSEARCH        FAISS
                  ─────────────────    ──────────────
Setup Time        30 minutes            5 minutes
Query Speed       50-100ms              1-5ms
Memory Usage      1-2GB                 100MB
Deployment        Docker/Cloud          Plain Python
Infrastructure    Complex               Simple
Distributed       ✅ Yes               ❌ No
For MVP           ⚠️ Overkill          ✅ Perfect

Decision Timeline:

Early Development: "We need production-ready search" → Choose ES
Mid Development: "ES is complex to share/demo" → Consider FAISS
Late MVP: "Do we really need ES features?" → Answer: NO

Conclusion: Migrate to FAISS
```

---

## 💡 Key Insights

### Why Vector (KNN) Over Keyword (BM25)?

```
Legal domain characteristic: Same concept expressed multiple ways

Example:
  "Unlawful access" (official legal term)
  "Hacking"         (common term)
  "Breaking in"     (informal)
  "Unauthorized entry" (formal)

All refer to same law (IT Act Section 66)

Keyword search: Only finds "unlawful access"
Vector search: Finds all 4 (+ more variations)

Advantage: Users don't need to speak like lawyers
```

### Why 384 Dimensions?

```
Trade-off: Accuracy vs Speed

Options:
- 96 dims:   Very fast, lower accuracy
- 384 dims:  CHOSEN - Good balance
- 768 dims:  Higher accuracy, slower
- 1536 dims: Very accurate, very slow

Why 384?
- Model: all-MiniLM-L6-v2
- "Mini" = optimized for speed
- "L6" = 6 layers (efficient)
- Encodes 1000+ docs/second
- Still captures legal semantics well
```

### Why L2 Distance?

```
Distance metrics:
- L2 (Euclidean): √(Σ(x-y)²)    ← Used in ALIS
- Cosine: 1 - (A·B)/(|A||B|)
- Manhattan: Σ|x-y|

For legal domain:
L2 works well because:
- Documents have varied vocabulary length
- Legal terms cluster naturally
- Stable performance
- ES optimized for L2
```

---

## 🎯 Interview Talking Points

**What you optimized:**
```
"We chose vector search over keyword because legal concepts
are expressed multiple ways. A user might ask for 'hacking'
but the law is called 'unauthorized computer access'.
Vector search understands this semantic relationship."
```

**Why Elasticsearch initially:**
```
"Elasticsearch provided both semantic (KNN) and keyword
search. For a production system, this was prudent. However,
we realized that for our MVP, we only needed semantic search.
Simpler is better when scaling isn't needed yet."
```

**What you learned:**
```
"The lesson: Don't over-engineer for scale. Start simple,
migrate only when needed. We started with the distributed
option (ES) but switched to the lightweight option (FAISS)
when we realized we didn't need distribution."
```

---

## 📚 Additional Resources

- **config**: `localhost:9200` (Elasticsearch default port)
- **embedding model**: `all-MiniLM-L6-v2` (22MB, distilbert-based)
- **vector dimension**: 384 (standard for MiniLM)
- **corpus size**: ~2,400 legal documents
- **query latency**: 50-100ms per query
- **index size**: 2-4GB total storage

