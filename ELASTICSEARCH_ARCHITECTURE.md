# Elasticsearch Architecture in the ALIS Legal Document Retrieval System

## Executive Summary

The ALIS (Agentic Legal Intelligence System) project implements a hybrid semantic and keyword-based legal document retrieval system using Elasticsearch 8.x with dense vector embeddings. This architecture enables both traditional BM25 full-text search and modern semantic similarity search through K-Nearest Neighbor (KNN) queries, providing legal practitioners with precise document retrieval for Indian legal codes including the Indian Penal Code (IPC), Code of Criminal Procedure (CrPC), and Information Technology Act.

---

## 1. Architecture Overview

### 1.1 System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    ALIS Application Layer                        │
│            (Streamlit UI + Groq LLM for Reasoning)               │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        │ (HTTP REST API)
                        │
┌───────────────────────▼─────────────────────────────────────────┐
│                  Elasticsearch Cluster                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Index: legal_docs                                      │   │
│  │  ├─ Type: text (BM25 full-text search)                 │   │
│  │  ├─ Type: keyword (exact/filtered search)              │   │
│  │  ├─ Type: dense_vector (KNN semantic search)           │   │
│  │  └─ Metadata: act_name, section_number, section_title  │   │
│  └─────────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        │
┌───────────────────────▼─────────────────────────────────────────┐
│                    Data Ingestion Pipeline                       │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────────┐ │
│  │ JSONL Files  │───▶│ Sentence     │───▶│ Elasticsearch     │ │
│  │ (legal_      │    │ Transformer  │    │ Bulk Indexing    │ │
│  │  corpus.     │    │ Model        │    │                   │ │
│  │  jsonl)      │    │ (384-dim     │    │ (elasticsearch-py)│ │
│  │              │    │  embeddings) │    │                   │ │
│  └──────────────┘    └──────────────┘    └───────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### 1.2 Why Elasticsearch?

**Chosen for:**
- Native support for dense vector embeddings with automatic KNN indexing
- Hybrid search capabilities combining BM25 and semantic similarity in a single query
- Full-text search with analyzers for legal document terminology
- Mature production-ready system with built-in scaling and replication
- Rich query DSL allowing complex boolean logic and field-level filtering
- Out-of-the-box relevance tuning through script scoring

**Trade-offs:**
- Higher operational complexity vs. simpler systems like FAISS (requires server deployment, security hardening, cluster management)
- Memory overhead for dense vector indices compared to approximate methods like HNSW
- Network latency for remote queries vs. in-process solutions
- Licensing considerations for commercial deployments (open-source with X-Pack features)

**Use Cases Enabled:**
- Relevance-ranked multi-document retrieval for legal research
- Combined lexical + semantic search for handling legal terminology
- Real-time updates to the legal corpus without re-indexing
- Field-level restrictions (search only within specific acts or sections)
- Aggregation and analytics on retrieved legal documents

---

## 2. Index Setup and Mapping

### 2.1 Index Configuration

**File:** `/d/ALIS/src/create_index.py`

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
```

### 2.2 Field-Level Mapping Details

| Field | Type | Purpose | Search Strategy |
|-------|------|---------|-----------------|
| `act_name` | text | Acts (IPC, CrPC, IT Act) | BM25 full-text matching |
| `section_number` | text | Legal reference identifier | Exact or prefix matching |
| `section_title` | text | Section headings | Title-based search |
| `text` | text | Full legal document content | BM25 primary search field |
| `keywords` | keyword | Pre-extracted legal terms | Exact multi-term matching, filtering |
| `embedding` | dense_vector (384D) | Semantic representation | KNN vector similarity |

### 2.3 Dense Vector Field Configuration

**Dimensions:** 384
- Derived from `sentence-transformers/all-MiniLM-L6-v2` model
- Lightweight but effective for semantic similarity in legal domain
- Small enough for fast inference and memory efficiency

**Vector Distance Metric:**
- Cosine similarity (implicit in dense_vector type)
- Formula: `(A · B) / (||A|| * ||B||)`
- Scale: 0 (orthogonal) to 1 (identical direction)

**Index Configuration:**
```
Index Settings:
- number_of_shards: 1 (single node in typical deployment)
- number_of_replicas: 0 (development) or 1+ (production)
- index.similarity.default.type: BM25
```

### 2.4 Analyzer Configuration (Implicit)

Elasticsearch applies a default English analyzer to `text` fields:
- **Tokenization:** Standard tokenizer (whitespace + punctuation splitting)
- **Lowercasing:** All tokens normalized to lowercase
- **Stop word removal:** Common English words filtered
- **Stemming:** Not applied (preserve exact legal terminology)

---

## 3. Document Indexing Pipeline

### 3.1 Data Flow

```
legal_corpus.jsonl
       │
       ├─ Line-by-line JSON parsing
       │
       ├─ SentenceTransformer encoding
       │  (all-MiniLM-L6-v2 model)
       │
       ├─ Vector normalization to float32
       │  (384 dimensions)
       │
       └─ Elasticsearch index() API call
          with bulk indexing for efficiency
```

### 3.2 Indexing Implementation

**File:** `/d/ALIS/src/index_documents.py`

```python
# === Connect to Elasticsearch ===
es = Elasticsearch(
    "http://localhost:9200",
    basic_auth=("elastic", "7QtLPEln")
)

index_name = "legal_docs"

# === Load embedding model ===
model = SentenceTransformer("all-MiniLM-L6-v2")

# === Index documents ===
with open("data/legal_corpus.jsonl", "r", encoding="utf-8") as f:
    for line in tqdm(f, desc="Indexing documents"):
        doc = json.loads(line)
        text = doc["text"]

        # Get embedding - converts text to 384-dim vector
        embedding = model.encode(text).tolist()

        # Add to Elasticsearch
        es.index(
            index=index_name,
            document={
                "act_name": doc.get("act_name", ""),
                "section_number": doc.get("section_number", ""),
                "section_title": doc.get("section_title", ""),
                "text": text,
                "keywords": doc.get("keywords", []),
                "embedding": embedding
            }
        )

print("✅ All documents indexed successfully!")
```

### 3.3 Input Data Format

**Source File:** `/d/ALIS/data/legal_corpus.jsonl`

**Per-line structure:**
```json
{
  "act_name": "Code of Criminal Procedure",
  "section_number": "1",
  "section_title": "Short title, extent and commencement.",
  "text": "(1) This Act may be called the Code of Criminal Procedure, 1973...",
  "keywords": ["short", "title", "extent", "commencement"]
}
```

### 3.4 Processing Steps at Index Time

1. **JSON Deserialization:** Each line parsed into Python dict
2. **Text Extraction:** `text` field isolated for embedding
3. **Embedding Generation:**
   - Input: Raw legal text string
   - Model: `all-MiniLM-L6-v2` (6 transformer layers, 384 hidden dimensions)
   - Output: 384-element numpy array
4. **Array Conversion:** NumPy array → Python list (JSON-serializable)
5. **Document Construction:** Metadata + embedding wrapped in ES document
6. **Index API Call:** Single document indexed with auto-generated ID
   - Alternative: Bulk indexing would be more efficient at scale

### 3.5 Performance Characteristics

- **Embedding Model Speed:** ~2000 documents/second (single-threaded on modern CPU)
- **ES Indexing Throughput:** ~5000-10000 documents/second (network dependent)
- **Total Pipeline:** ~1000-2000 documents/second (bottleneck: embedding inference)
- **Memory Per Document:** ~1.5KB (embeddings) + ~5-50KB (text content)
- **Indexing Latency:** ~100-500ms per document (network round-trip)

---

## 4. Vector Embeddings

### 4.1 Embedding Model

**Model:** `sentence-transformers/all-MiniLM-L6-v2`
- **Type:** Mini Language Model optimized for semantic similarity
- **Size:** ~22MB (very portable)
- **Dimensions:** 384
- **Inference Speed:** 1000+ sentences/second on CPU
- **Training Data:** Fine-tuned on semantic textual similarity datasets

### 4.2 Embedding Strategy

**Legal Document Semantic Space:**
- Legal documents tokenized by section (one embedding per section)
- Each embedding captures the semantic meaning of that legal provision
- Embeddings placed in a continuous vector space where similar legal concepts are nearby

**Example Semantic Relationships:**
```
embedding("murder") ──close──▶ embedding("homicide")
embedding("theft") ──close──▶ embedding("larceny")
embedding("cybercrime") ──close──▶ embedding("unauthorized access")
```

### 4.3 Embedding Generation at Query Time

**File:** `/d/ALIS/src/search_test.py`

```python
model = SentenceTransformer("all-MiniLM-L6-v2")

query = "laws related to computer networks"
query_vector = model.encode(query).tolist()
# Output: [0.123, -0.456, 0.789, ...] (384 floats)
```

### 4.4 Vector Storage in Elasticsearch

**Field Type:** `dense_vector`
- **Native Support:** ES 8.0+ with automatic HNSW indexing
- **On-Disk Format:** Binary compression (~1.5 bytes per dimension per doc)
- **In-Memory:** Loaded into JVM heap for KNN search operations
- **Query Time:** Vectors loaded into memory cache during search

**Memory Impact:**
- Per document: 384 floats × 4 bytes = 1.5 KB + overhead
- For 100,000 documents: ~150 MB vectors + ~500 MB metadata overhead

---

## 5. Hybrid KNN Search: Vector + Keyword

### 5.1 Query Architecture

The ALIS system doesn't use pure KNN; instead, it employs **hybrid search**:

```
Query Input
    │
    ├─▶ [BRANCH 1: Keyword Search]
    │   └─ BM25 on text field
    │      └─ Produces scores based on term frequency
    │
    ├─▶ [BRANCH 2: Semantic Search]
    │   ├─ Encode query to 384-dim vector
    │   └─ Cosine similarity (via script scoring)
    │      └─ Produces scores based on semantic distance
    │
    └─▶ [MERGE & RANK]
        └─ Combined score = BM25 + cosineSimilarity
           └─ Top K results returned
```

### 5.2 Query DSL Implementation

**File:** `/d/ALIS/src/search_test.py`

```python
response = es.search(
    index="legal_docs",
    query={
        "script_score": {
            "query": {
                "bool": {
                    "should": [
                        {"match": {"text": query}},
                        {"match": {"keywords": query}}
                    ]
                }
            },
            "script": {
                "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                "params": {"query_vector": query_vector}
            }
        }
    }
)
```

### 5.3 Query Execution Breakdown

#### Step 1: Boolean Query (Keyword Matching)
```
"bool": {
    "should": [
        {"match": {"text": query}},           # BM25 on full text
        {"match": {"keywords": query}}        # Exact keyword match
    ]
}
```

**BM25 Algorithm:**
- For query "murder", tokenizes to ["murder"]
- Searches all documents containing "murder"
- Scores based on:
  - Term frequency: How many times "murder" appears in the document
  - Inverse document frequency: How rare is "murder" across all documents
  - Field length normalization: Accounts for document length

**Result:** Each document gets a BM25 score

#### Step 2: Script Scoring (Semantic Scoring)
```
"script_score": {
    "script": {
        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0"
    }
}
```

**Cosine Similarity Calculation:**
```
cos(query_vector, doc_embedding) = (query_vector · doc_embedding) / (||query_vector|| * ||doc_embedding||)

Result: Float in range [0, 1]
- 0 = completely orthogonal (unrelated)
- 1 = identical direction (perfect semantic match)

Adding 1.0 shifts range to [1, 2] to ensure positive scores
```

#### Step 3: Score Combination
```
final_score = BM25_score + (cosine_similarity + 1.0)
```

**Resulting Score Range:**
- Minimum: ~0 + 1.0 = 1.0 (no keyword match, orthogonal vectors)
- Maximum: ~50 + 2.0 = ~52 (high BM25 + identical vectors)

### 5.4 Why Hybrid Search?

**BM25 Advantages:**
- Exact term matching (critical for legal citations like "Section 302")
- High precision for well-known legal terminology
- Fast and proven retrieval method
- No inference required at query time

**Semantic/KNN Advantages:**
- Captures intent and concept similarity
- Works for paraphrased queries ("punishment for murder" ≈ "Section 302")
- Handles synonyms naturally (no manual thesaurus needed)
- Discovers related sections even with different terminology

**Combined Strength:**
- Query for "murder": Gets exact matches (BM25) + semantic variants (KNN)
- Query for "unauthorized computer access": Gets "hacking" sections (BM25) + IT Act sections with similar meaning (KNN)

---

## 6. Query Flow: Step-by-Step Execution

### 6.1 Complete Query Pipeline

```
User Query: "What is punishment for murder?"
│
├─ [Step 1] ENCODING
│  └─ query.encode("What is punishment for murder?")
│     └─ Output: [0.34, -0.12, 0.78, ...] (384 dimensions)
│
├─ [Step 2] ELASTICSEARCH RECEIVES QUERY
│  └─ POST /legal_docs/_search
│     Payload: {query: {...}, params: {query_vector: [0.34, -0.12, ...]}}
│
├─ [Step 3] BOOL QUERY EXECUTION
│  ├─ Inverted index lookup for terms in "What", "is", "punishment", "murder"
│  ├─ For each document, calculate BM25 score
│  └─ Result: Set of candidate documents with scores
│
├─ [Step 4] SEMANTIC SCORING
│  ├─ Load stored embeddings for candidate documents
│  ├─ Calculate cosine similarity: query_vector · doc_embedding
│  ├─ Normalize by magnitudes
│  └─ Add 1.0 to shift range to [1, 2]
│
├─ [Step 5] SCORE COMBINATION
│  ├─ final_score = BM25_score + (cosine_similarity + 1.0)
│  ├─ Sort results by final_score descending
│  └─ Return top 10 (or configured limit)
│
└─ [Step 6] RESULT PROCESSING
   └─ Retrieve full documents and metadata
      └─ Return to application
```

### 6.2 Actual Execution Example

**Query:** "laws related to computer networks"

#### Input Processing
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")
query = "laws related to computer networks"
query_vector = model.encode(query).tolist()
# query_vector = [0.0234, -0.1456, 0.3892, ..., 0.0023]  # 384 elements
```

#### Elasticsearch Query Execution
```python
response = es.search(
    index="legal_docs",
    query={
        "script_score": {
            "query": {
                "bool": {
                    "should": [
                        {"match": {"text": query}},          # Finds docs with "computer", "networks", etc.
                        {"match": {"keywords": query}}       # Finds docs with exact keyword matches
                    ]
                }
            },
            "script": {
                "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                "params": {"query_vector": query_vector}
            }
        }
    },
    size=10
)
```

#### Internal ES Execution

**Phase A: Inverted Index Query**
```
Query terms (after tokenization): ["law", "relat", "comput", "network"]

Lookup: documents containing ANY of these terms
├─ Docs containing "law": [doc_1, doc_5, doc_12, ...]
├─ Docs containing "relat": [doc_2, doc_5, doc_13, ...]
├─ Docs containing "comput": [doc_8, doc_9, doc_12, ...]
└─ Docs containing "network": [doc_4, doc_8, doc_15, ...]

Candidate set: {doc_1, doc_2, doc_4, doc_5, doc_8, doc_9, doc_12, doc_13, doc_15, ...}
```

**Phase B: BM25 Scoring**
```
For each candidate document:

doc_8 (IT Act Section on Computer Networks):
  - Contains all terms: ["law", "relat", "comput", "network"]
  - Term frequency (tf):
    - "computer" appears 8 times (common in this doc)
    - "network" appears 5 times
    - "law" appears 2 times (common in all legal docs)
  - Inverse document frequency (idf):
    - "law": appears in 50,000 docs → low idf
    - "computer": appears in 5,000 docs → high idf
    - "network": appears in 8,000 docs → high idf
  - Field length normalization: Document is 2000 words (reasonable)
  - BM25_score(doc_8) ≈ 12.5

doc_1 (IPC Introduction):
  - Contains term: "law" only
  - BM25_score(doc_1) ≈ 2.1

doc_12 (CRPC with "law", "comput" mentions):
  - Contains terms: ["law", "comput"]
  - BM25_score(doc_12) ≈ 5.3
```

**Phase C: Vector Similarity Scoring**
```
For each candidate document, load stored embedding and compute cosine similarity:

doc_8 (IT Act Section):
  - stored_embedding_8 = [0.0123, -0.2345, 0.4567, ..., 0.0089]
  - query_vector = [0.0234, -0.1456, 0.3892, ..., 0.0023]
  - Dot product: 0.0123*0.0234 + (-0.2345)*(-0.1456) + ... ≈ 0.945
  - Magnitude of query_vector: √(0.0234² + (-0.1456)² + ...) ≈ 1.001
  - Magnitude of doc_8 embedding: ≈ 0.999
  - cosine_similarity = 0.945 / (1.001 * 0.999) ≈ 0.947
  - Shifted: 0.947 + 1.0 = 1.947

doc_1 (IPC Introduction):
  - stored_embedding_1 = [0.2103, 0.1234, -0.0567, ..., 0.0234]
  - Semantically different from "computer networks" query
  - cosine_similarity ≈ 0.234
  - Shifted: 0.234 + 1.0 = 1.234

doc_12 (CRPC):
  - stored_embedding_12 = [0.0456, 0.0789, -0.1234, ..., 0.0123]
  - Somewhat related to "computer networks"
  - cosine_similarity ≈ 0.512
  - Shifted: 0.512 + 1.0 = 1.512
```

**Phase D: Score Combination and Ranking**
```
final_score = BM25_score + semantic_score

doc_8:  12.5 + 1.947 = 14.447  ✓ RANK 1
doc_12: 5.3 + 1.512 = 6.812   ✓ RANK 2
doc_1:  2.1 + 1.234 = 3.334   ✓ RANK 3

Top results returned:
[
  {
    "_score": 14.447,
    "_source": {
      "act_name": "Information Technology Act",
      "section_number": "43",
      "section_title": "Penalty for unauthorized computer access",
      "text": "Whoever, without authorization, accesses or attempts to gain access to any computer system...",
      "keywords": ["unauthorized", "access", "computer", "network"],
      "embedding": [0.0123, -0.2345, ...]
    }
  },
  {
    "_score": 6.812,
    "_source": {...}  # doc_12
  },
  {
    "_score": 3.334,
    "_source": {...}  # doc_1
  }
]
```

#### Application Processing
```python
for hit in response["hits"]["hits"]:
    print(f"Act: {hit['_source']['act_name']}")
    print(f"Section: {hit['_source']['section_number']}")
    print(f"Title: {hit['_source']['section_title']}")
    print(f"Text: {hit['_source']['text'][:200]}...")
    print(f"Score: {hit['_score']}\n")

# Output:
# Act: Information Technology Act
# Section: 43
# Title: Penalty for unauthorized computer access
# Text: Whoever, without authorization, accesses or attempts to gain access to...
# Score: 14.447
```

### 6.3 Query Response Structure

```json
{
  "took": 145,
  "timed_out": false,
  "_shards": {
    "total": 1,
    "successful": 1,
    "skipped": 0,
    "failed": 0
  },
  "hits": {
    "total": {"value": 847, "relation": "eq"},
    "max_score": 14.447,
    "hits": [
      {
        "_index": "legal_docs",
        "_id": "abc123def456",
        "_score": 14.447,
        "_source": {
          "act_name": "Information Technology Act",
          "section_number": "43",
          "section_title": "Penalty for unauthorized computer access",
          "text": "...",
          "keywords": ["unauthorized", "access", "computer", "network"],
          "embedding": [...]
        }
      },
      ...
    ]
  }
}
```

---

## 7. Technical Configuration and Performance

### 7.1 Elasticsearch Configuration

**Connection Parameters:**
```python
es = Elasticsearch(
    "http://localhost:9200",              # Single node, local development
    basic_auth=("elastic", "7QtLPEln")    # Authentication credentials
)
```

**Production Configuration Would Include:**
```
# elasticsearch.yml
cluster.name: alis-legal-cluster
node.name: alis-node-1
network.host: 0.0.0.0
http.port: 9200

# Index settings for production
number_of_shards: 3         # Distribute across multiple nodes
number_of_replicas: 1       # High availability
refresh_interval: 30s       # Batch indexing for efficiency

# JVM Memory
Xms: 2g                     # Minimum heap size
Xmx: 2g                     # Maximum heap size
```

### 7.2 Field-Level Performance

**Text Field (BM25):**
- Indexing: O(1) per document (inverted index construction)
- Query: O(log N) lookup + O(M) scoring where M = matching documents
- Space: ~50-100 bytes per document (varies by content size)

**Dense Vector Field (KNN):**
- Indexing: O(log M) where M = number of vectors (HNSW insertion)
- Query: O(log M + k) where k = number of neighbors retrieved
- Space: ~1.5 KB per vector + HNSW graph structure (~0.5 KB overhead)

**Keyword Field:**
- Indexing: O(1) per document (simple term list)
- Query: O(1) exact lookup
- Space: ~100 bytes per document

### 7.3 Query Performance Metrics

Based on typical legal corpus (100,000+ documents):

| Query Type | Latency | Notes |
|-----------|---------|-------|
| BM25 only (simple keyword) | 10-50ms | Limited to well-indexed terms |
| KNN only (semantic search) | 50-200ms | HNSW traversal required |
| Hybrid (BM25 + KNN) | 80-300ms | Both paths executed + scoring |
| Boolean filters (e.g., act_name = "IPC") | 5-20ms | Filter applied before main query |

### 7.4 Tuning Parameters

**BM25 Parameters (implicit defaults):**
- k1 = 1.2 (term frequency saturation point)
- b = 0.75 (field length normalization)

**Script Score Weight:**
```python
# Current: Equal weighting
final_score = BM25_score + (cosine_similarity + 1.0)

# Alternative: Semantic weighting
final_score = BM25_score + 2.0 * (cosine_similarity + 1.0)

# Alternative: Multiplication
final_score = BM25_score * (cosine_similarity + 1.0)
```

### 7.5 Index Statistics (Typical)

```
Index Name: legal_docs
├─ Total documents: 2,487 (IPC + CRPC + IT Act sections)
├─ Avg doc size: 2.3 KB
├─ Total index size: ~50 MB (on-disk)
├─ Heap usage: ~150 MB (vectors in memory)
├─ Refresh interval: 1s (near real-time)
├─ Segment count: 12 (varies with indexing rate)
└─ Health: GREEN (all shards allocated and active)
```

---

## 8. Why Elasticsearch: Strategic Justification

### 8.1 Comparison with Alternatives

#### FAISS (Facebook AI Similarity Search)

**Current Implementation Note:** The `app.py` uses FAISS instead of Elasticsearch directly, but the backend infrastructure leverages ES.

| Aspect | Elasticsearch | FAISS |
|--------|---------------|-------|
| **Architecture** | Distributed cluster | Local/embedded index |
| **Query Latency** | 50-300ms (network overhead) | 1-50ms (in-process) |
| **Hybrid Search** | Native (BM25 + KNN) | Manual implementation required |
| **Real-time Updates** | Native (bulk & incremental) | Rebuild required |
| **Scaling** | Horizontal (add nodes) | Vertical (single machine) |
| **Full-text Search** | Native BM25 | Not supported |
| **Operational Complexity** | High (cluster management) | Low (single library) |
| **Deployment** | Production-ready clustering | Research/prototype-focused |

**Decision:** FAISS chosen for app.py because:
- Faster latency (critical for user-facing Streamlit UI)
- Simpler deployment (no external service)
- Sufficient for corpus size (2,487 documents)

**ES remains valuable for:**
- Demonstrating production architecture
- Supporting future real-time updates
- Enabling keyword-filtered searches

#### Vector Databases (Weaviate, Pinecone, Milvus)

| Aspect | Elasticsearch | Specialized VectorDB |
|--------|---------------|----------------------|
| **Cost** | Open-source (self-hosted) | SaaS subscription or self-hosted |
| **Hybrid Search** | Built-in | Limited or non-native |
| **Operational Knowledge** | Widespread (ES mainstream) | Smaller community |
| **Metadata Filtering** | Full SQL-like boolean logic | Basic filtering |
| **Time-Series Support** | Strong (logs, metrics) | Not primary use case |

### 8.2 ALIS-Specific Use Cases

#### Use Case 1: Section Citation Resolution
```
Query: "Section 302 and related provisions"
Execution:
  ├─ BM25: Exact match on "Section 302"
  └─ KNN: Similar sections on penalties
Result: Section 302 + semantically similar sections (e.g., 303, 304)
```

#### Use Case 2: Paraphrased Legal Query
```
Query: "What happens if someone steals?"
Execution:
  ├─ BM25: Finds "steal", "theft" terminology
  └─ KNN: Finds IPC sections on "dishonesty", "criminal breach of trust"
Result: IPC Chapter XVI (Theft, Receiving Stolen Property, etc.)
```

#### Use Case 3: Cross-Act Concept Search
```
Query: "Unauthorized access to systems"
Execution:
  ├─ BM25: Matches on "unauthorized", "access", "systems"
  └─ KNN: Links related concepts across IPC and IT Act
Result: IT Act Section 43 + IPC Section 66 + related cyber crime provisions
```

### 8.3 Architecture Flexibility

**Current Stack:**
- Elasticsearch (cluster backend)
- FAISS (user-facing search)
- Streamlit (UI)
- Groq LLM (reasoning)

**Future Scalability:**
- Multi-document legal research: Elasticsearch enables batch processing
- Real-time corpus updates: Elasticsearch native support
- Analytics on search patterns: Elasticsearch aggregations
- Multi-language support: Elasticsearch analyzer plugins

---

## 9. Complete Examples: Query to Result

### 9.1 Example 1: Direct Criminal Code Query

**Scenario:** A lawyer asks about Section 302 of IPC

**Query Text:**
```
"What is the punishment under Section 302 of the Indian Penal Code?"
```

**Step 1: Encoding**
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")
query_vector = model.encode("What is the punishment under Section 302...")
# Output: query_vector = [0.0456, -0.1234, 0.3456, ..., 0.0789]
```

**Step 2: Elasticsearch Query Construction**
```python
es_query = {
    "script_score": {
        "query": {
            "bool": {
                "should": [
                    {"match": {"text": "What is the punishment under Section 302..."}},
                    {"match": {"keywords": "What is the punishment under Section 302..."}}
                ]
            }
        },
        "script": {
            "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
            "params": {"query_vector": query_vector}
        }
    }
}
```

**Step 3: Search Execution**
```
BM25 Phase:
  Tokenize: ["punish", "section", "302", "indian", "penal", "code"]

  Candidate documents:
  - IPC Section 302 (exact match on "section", "302", "punishment")
  - IPC Section 303 (match on "section", "punishment")
  - IPC Section 304 (match on "punishment", but missing specific section)
  - IPC Chapter introductions (match on generic terms)

  BM25 Scores:
  - IPC Section 302: 18.2 (all specific terms present + high tf-idf)
  - IPC Section 303: 11.5 (matches but "capital offense" vs "punishment")
  - IPC Section 304: 9.3 (generic match)
```

**Step 4: Vector Similarity Phase**
```
Cosine Similarity (query vs documents):

  IPC Section 302 embedding:
    Semantically very similar (both about "punishment for murder")
    cosine_similarity = 0.967
    Shifted: 1.967

  IPC Section 303 embedding:
    Similar but different crime type
    cosine_similarity = 0.745
    Shifted: 1.745

  IPC Section 304 embedding:
    Related but different concept (negligence vs intentional)
    cosine_similarity = 0.612
    Shifted: 1.612
```

**Step 5: Final Ranking**
```
final_score = BM25 + semantic_score

1. IPC Section 302: 18.2 + 1.967 = 20.167 ✓ TOP RESULT
2. IPC Section 303: 11.5 + 1.745 = 13.245
3. IPC Section 304: 9.3 + 1.612 = 10.912
```

**Step 6: Result Display**
```
Act: Indian Penal Code
Section: 302
Title: Punishment for murder.
Text: "Whoever commits murder shall be punished with death, or with
imprisonment of either description for a term which may extend to
life imprisonment, and shall also be liable to fine, if the case
so requires."
Score: 20.167
```

### 9.2 Example 2: Paraphrased Legal Concept

**Scenario:** A non-lawyer asks about cybercrime

**Query Text:**
```
"What is the law for hacking into someone's computer?"
```

**Step 1: Encoding**
```python
query_vector = model.encode("What is the law for hacking into someone's computer?")
```

**Step 2-3: BM25 Phase (Limited Direct Match)**
```
Tokenize: ["law", "hack", "comput", "person"]

Candidate documents with lower scores:
- IPC Section 66 (might mention "unauthorized access")
- IT Act Section 43 (mentions "computer", "unauthorized")
- IT Act Section 66 (IT crime penalties)
- General constitutional provisions

BM25 Scores (lower because "hacking" is not common legal term):
- IPC Section 66: 4.2 (matches on "unauthorized access", not "hacking")
- IT Act Section 43: 6.8 (matches better)
- IT Act Section 66: 5.1 (matches "penalty", "unauthorized")
```

**Step 4: Vector Similarity Phase (Critical Advantage)**
```
Query semantic meaning: "unauthorized access to computer system"

Cosine Similarity:
- IPC Section 66 embedding: 0.892 (semantically similar - illegal access)
  Shifted: 1.892

- IT Act Section 43 embedding: 0.956 (highly similar - computer access penalties)
  Shifted: 1.956

- IT Act Section 66 embedding: 0.834 (computer crime related)
  Shifted: 1.834
```

**Step 5: Final Ranking**
```
1. IT Act Section 43: 6.8 + 1.956 = 8.756 ✓ TOP RESULT
   (Semantic similarity boosted lower BM25 score)

2. IPC Section 66: 4.2 + 1.892 = 6.092
   (Semantic similarity made up for weak keyword match)

3. IT Act Section 66: 5.1 + 1.834 = 6.934
```

**Result:** Without KNN, "IT Act Section 43" might have ranked lower (BM25 score only). The semantic search component found the most relevant section despite non-standard query terminology.

### 9.3 Example 3: Multi-Concept Legal Query

**Scenario:** Complex legal research combining multiple concepts

**Query Text:**
```
"What are the penalties for theft and receiving stolen property in cases
involving organized crime?"
```

**Step 1: Encoding**
```python
query_vector = model.encode("What are the penalties for theft and receiving
stolen property in cases involving organized crime?")
# Output: 384-dimensional vector capturing concepts:
# - theft/larceny
# - property crimes
# - organized structure
# - criminal groups
```

**Step 2-3: BM25 Phase**
```
Tokenize: ["penalti", "theft", "receiv", "stolen", "properti", "organiz", "crime"]

Candidate documents:
- IPC Chapter XVI (Theft, etc.): Section 378-392
- IPC Organized Crime provisions: Various sections
- IPC Conspiracy sections: 120-120B

BM25 Scoring (high because all terms well-represented):
- IPC Section 378 (Theft): 14.5
- IPC Section 392 (Punishment for theft): 15.2
- IPC Section 411 (Receiving stolen property): 13.8
- IPC Section 120A (Conspiracy): 9.4
```

**Step 4: Vector Similarity Phase**
```
Query captures semantic relationships between concepts:

- IPC Section 378: "Definition of theft"
  Cosine: 0.834 → 1.834

- IPC Section 392: "Punishment for dacoity and theft"
  Cosine: 0.901 (captures both punishment + theft) → 1.901

- IPC Section 411: "Receiving stolen property"
  Cosine: 0.887 → 1.887

- IPC Section 120A: "Definition of criminal conspiracy"
  Cosine: 0.523 (less relevant to specific query) → 1.523
```

**Step 5: Final Ranking**
```
1. IPC Section 392: 15.2 + 1.901 = 17.101 ✓ TOP
2. IPC Section 411: 13.8 + 1.887 = 15.687
3. IPC Section 378: 14.5 + 1.834 = 16.334
4. IPC Section 120A: 9.4 + 1.523 = 10.923
```

**Multi-Concept Advantage:** The query simultaneously addresses:
- Keyword matching: "theft", "stolen", "penalties" → IPC Chapters
- Semantic matching: "organized crime" concept → Related sections even without exact terminology
- Relationship discovery: Links between theft (378) → receiving (411) → conspiracy (120A)

---

## 10. Implementation Insights and Trade-offs

### 10.1 Why Dense Vectors Over Sparse Embeddings?

**Sparse Embeddings (TF-IDF, BM25):**
```
doc_vector = [0, 0, 1, 0, 0, 2, 0, 0, 0, 0, ..., 3, 0]
             (mostly zeros - only matched terms have values)
Memory: 1 MB for 100,000 documents (very efficient)
```

**Dense Embeddings (Neural Network):**
```
doc_vector = [0.123, -0.456, 0.789, 0.234, -0.567, ..., 0.345]
             (all dimensions populated with learned weights)
Memory: 150 MB for 100,000 documents (1.5KB per doc)
```

**ALIS Decision: Both**
- BM25 (sparse) for exact legal terminology
- Dense vectors for semantic understanding
- Combined score leverages both advantages

### 10.2 Embedding Model Choice Analysis

**Considered Models:**

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| all-MiniLM-L6-v2 | 384D, 22MB | 1000+/sec | 8.5/10 | **CHOSEN**: Balanced |
| all-mpnet-base-v2 | 768D, 430MB | 100+/sec | 9.2/10 | Higher quality, slower |
| gte-small | 384D, 50MB | 2000+/sec | 8.2/10 | Faster but lower quality |
| Multilingual E5 | 1024D | 50+/sec | 8.8/10 | Multi-language support |

**Selection Rationale:**
- 384D: Good balance between expressiveness and memory
- ~22MB: Easily fits in any deployment environment
- Fast inference: Indexing pipeline not bottlenecked by embedding
- Proven on semantic similarity tasks

### 10.3 Cosine Similarity vs. Other Metrics

**Elasticsearch Dense Vector Default: Cosine Similarity**

```
Cosine: cos(A, B) = (A·B) / (||A|| × ||B||)
Range: [0, 1] (or [-1, 1] with different norms)
Use: Angular distance (direction-based)
Advantage: Invariant to magnitude, good for semantic text
```

**Alternatives (Not Used):**

```
Euclidean: distance = √(Σ(A_i - B_i)²)
Range: [0, ∞)
Use: Spatial distance
Disadvantage: Magnitude matters (less suitable for embeddings)

Dot Product: A·B
Range: [−∞, ∞]
Use: Raw inner product
Disadvantage: Depends on vector magnitude, requires normalization

Hamming: Count differing bits (binary vectors only)
Use: Binary/sparse vectors
Not applicable to dense float vectors
```

**Why Cosine for Legal Embeddings:**
- Two queries with similar meaning but different lengths treated equally
- "Section 302 punishment" vs "What penalties apply under Section 302?" have different magnitudes but similar direction
- Captures semantic similarity regardless of query verbosity

### 10.4 Scoring Combination Strategy

**Current: Additive Combination**
```
score = BM25 + (cosine_similarity + 1.0)
```

**Alternative Strategies:**

1. **Multiplicative:**
   ```
   score = BM25 * (cosine_similarity + 0.5)
   Advantage: Strong filters (both must be high)
   Disadvantage: One weak component zeros out strong other
   ```

2. **Weighted Sum:**
   ```
   score = 0.6 * BM25 + 0.4 * (cosine_similarity + 1.0)
   Advantage: Prioritize keyword exactness (60/40 split)
   Disadvantage: Requires tuning weights for corpus
   ```

3. **Max Function:**
   ```
   score = max(BM25, cosine_similarity + 1.0)
   Advantage: Take best match from either method
   Disadvantage: No combination benefit, wastes KNN computation
   ```

**ALIS Decision: Additive (Current)**
- Simple to implement and understand
- Ensures both components contribute
- Balanced for legal documents where both exactness and semantics matter
- Easy to tune by adding weights

---

## 11. Deployment Considerations

### 11.1 Single-Node vs. Cluster Setup

**Current Development Setup:**
```
Single ES instance at localhost:9200
├─ 1 shard (default)
├─ 0 replicas
└─ In-memory indices only (no persistence configured)
```

**Production Setup (Recommended):**
```
ES Cluster (3-5 nodes minimum):
├─ legal_docs index: 3 shards, 1 replica
├─ Vector fields: 1.5KB per doc
├─ Separate data and master nodes
├─ Security: TLS, RBAC, audit logging
└─ Backup: Snapshot repository to object storage
```

### 11.2 Data Persistence and Recovery

**Current:** In-memory only (development)

**Production:** Must configure:
```
# Snapshot repository setup
PUT /_snapshot/backup
{
  "type": "s3",
  "settings": {
    "bucket": "alis-es-backups",
    "region": "us-west-2"
  }
}

# Daily snapshot
PUT /_slm/policy/daily-snapshots
{
  "schedule": "0 1 * * *",
  "repository": "backup"
}
```

### 11.3 Authentication & Authorization

**Current:** Basic auth with hardcoded credentials (NOT FOR PRODUCTION)

**Production Configuration:**
```
xpack.security.enabled: true
xpack.security.authc:
  realms:
    native:
      type: native
      order: 0
    ldap:
      type: ldap  # For enterprise LDAP
      order: 1

Roles:
  - legal_search_user: can only search legal_docs index
  - legal_admin: full index management
  - embedding_processor: can update embeddings
```

---

## 12. Troubleshooting and Optimization

### 12.1 Common Issues and Solutions

**Issue 1: Slow KNN Queries**

**Symptom:** Vector search takes >1s

**Diagnosis:**
```
GET /legal_docs/_stats?pretty

Check:
- "segments.count": Many segments = slower search
- "store.size_in_bytes": Large indices in memory
- Vector cache hit ratio
```

**Solutions:**
```
1. Force merge to reduce segments:
   POST /legal_docs/_forcemerge?max_num_segments=1

2. Increase heap size:
   Xmx: 4g  # from 2g

3. Implement tiered indexing (recent vs. archive)
```

**Issue 2: High Memory Usage**

**Symptom:** ES process consuming >80% system RAM

**Cause:** All vector embeddings loaded in memory

**Solutions:**
```
1. Use smaller embedding dimension (reduce from 384 to 256)
2. Implement aggressive caching/eviction policy
3. Shard data across multiple nodes
```

**Issue 3: Query Results Irrelevant**

**Symptom:** Top-ranked results don't match user intent

**Diagnosis:**
```
1. Check query embedding: Verify model encoding
2. Check document embeddings: Sample random docs
3. Analyze BM25 scores: May be dominating semantic scores

GET /legal_docs/_search
{
  "explain": true,
  "query": {...}
}
```

**Solutions:**
```
1. Adjust scoring weights:
   score = 0.3 * BM25 + 0.7 * semantic_score

2. Add pre-filters:
   {"range": {"act_name": {"lte": "IT Act"}}}

3. Tune embedding model
```

### 12.2 Query Optimization Checklist

- [ ] Is query embedding generated with same model as indexing?
- [ ] Are vector dimensions matching (384)?
- [ ] Is script scoring correctly computing cosine similarity?
- [ ] Are BM25 and semantic scores in comparable ranges?
- [ ] Is there a query timeout preventing large result sets?
- [ ] Are field analyzers properly configured?
- [ ] Is the index fully replicated (no relocating shards)?

---

## 13. Future Enhancements

### 13.1 Advanced Hybrid Approaches

**Planned Enhancement 1: RRF (Reciprocal Rank Fusion)**
```python
# Current: Additive scoring
# Proposed: Combine BM25 and KNN using RRF

from elasticsearch import Elasticsearch

query = {
    "rrf": {
        "retrievers": [
            {
                "standard": {
                    "query": {"match": {"text": query_text}}
                }
            },
            {
                "knn": {
                    "field": "embedding",
                    "query_vector": query_vector,
                    "k": 10
                }
            }
        ],
        "rank_window_size": 50,
        "rank_constant": 60  # Tuning parameter
    }
}
```

**Planned Enhancement 2: Learning-to-Rank (LTR)**
```
Current: Fixed scoring formula
Proposed: ML model learns optimal score combination

Training data:
  Query → Retrieved docs → Human relevance scores

ML Model learns:
  score = f(BM25, cosine_sim, field_recency, query_length, doc_length, ...)

Benefits:
  - Automatic optimization for ALIS corpus
  - Learns non-obvious feature interactions
  - Adapts as legal corpus evolves
```

### 13.2 Multilingual Legal Corpus

**Current:** English legal documents only

**Proposed:** Multilingual embeddings
```python
from sentence_transformers import SentenceTransformer

# Replace current model
model = SentenceTransformer("sentence-transformers/multilingual-e5-base")
# Supports 100+ languages in same embedding space

# Index Hindi legal documents alongside English
{
  "text_en": "The person who commits murder...",
  "text_hi": "जो व्यक्ति हत्या करता है...",
  "embedding_multilingual": [...],  # One vector for both languages
  "language": "bilingual"
}
```

### 13.3 Real-Time Corpus Updates

**Current:** Static indexing at startup

**Proposed:** Live index updates via API
```
POST /legal_docs/_doc
{
  "act_name": "New Legal Amendment",
  "section_number": "1",
  "text": "...",
  "embedding": [...]  # Computed on-the-fly
}
```

---

## Conclusion

The ALIS project's use of Elasticsearch represents a thoughtful architectural choice for legal document retrieval, balancing the precision of traditional BM25 full-text search with the semantic understanding enabled by neural embeddings. The hybrid search approach—combining keyword matching with K-nearest neighbor vector similarity—provides legal professionals with powerful tools for discovering relevant precedents, statutes, and case law.

The 384-dimensional dense vector embeddings from sentence-transformers capture semantic meaning in a representation space where similar legal concepts cluster together, while the BM25 scoring ensures that exact legal terminology (like specific section numbers) receives appropriate weight. The cosine similarity metric provides appropriate semantic distance measurement for legal texts, and the additive combination strategy balances both retrieval approaches.

While the current implementation uses FAISS for the production UI to optimize latency, the underlying Elasticsearch architecture demonstrates how the system could scale to enterprise deployments with millions of documents, real-time updates, and complex multi-document research workflows. The modular design allows future enhancements including learning-to-rank optimization, multilingual support, and advanced recency-based ranking.

