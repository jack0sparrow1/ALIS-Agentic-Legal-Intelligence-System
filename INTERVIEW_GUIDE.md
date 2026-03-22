# ALIS: Interview Explanation Guide

Use this guide to explain the Elasticsearch architecture during interviews.

---

## 🎯 Quick 2-Minute Explanation

**"ALIS is a conversational AI system that answers Indian legal questions. We use Elasticsearch as a semantic search engine to find relevant legal documents, then pass those to an LLM for reasoning and explanation."**

---

## ⏱️ 5-Minute Deep Dive

### The Problem
"Legal domain has complex, nuanced information. When someone asks 'What's the punishment for hacking?', we need to:
1. Understand they're asking about IT Act section 66 (or related sections)
2. Find all relevant sections quickly
3. Provide explainable answers backed by actual law

Traditional keyword search fails because:
- User says 'hacking', but law says 'unauthorized access'
- Same concept expressed multiple ways across different acts
- Simple pattern matching misses semantic relationships"

### Our Solution
"We use semantic search (embeddings + Elasticsearch KNN) instead of keywords:

1. **Embedding Phase**: Every legal document gets converted to a 384-dimensional vector that captures its semantic meaning. We use `all-MiniLM-L6-v2` model.

2. **Storage Phase**: Vectors stored in Elasticsearch with metadata (act name, section number, full text).

3. **Query Phase**: User's question converted to same 384-dim vector. Elasticsearch finds K-nearest neighbors using L2 distance—documents closest in vector space are most semantically similar.

4. **Result Phase**: Top-3 documents passed to Groq LLM for reasoning. LLM generates answer, and we extract sections as a reasoning graph."

### Why This Works
```
Keyword search:        Vector search:
"hacking" → NO MATCH   "hacking" → Vector space knows:
                          - Semantically = "unauthorized access"
                          - Related to = "computer", "network"
                          - Belongs to = IT Act domain
                          - FINDS: IT Act Section 66 ✅
```

---

## 🔍 Technical Details (For Senior Engineers)

### "Walk me through your retrieval system"

**Answer:**
"We indexed approximately 2,400 legal documents across three acts (IPC, IT Act, CRPC) into Elasticsearch.

**Indexing Pipeline:**
1. Raw JSONL files parsed and loaded
2. Each document's text field encoded using SentenceTransformer ('all-MiniLM-L6-v2')
3. 384-dimensional embeddings stored in Elasticsearch's `dense_vector` field
4. Complete flow: Parse → Encode (1000+ docs/sec) → Index (~1-2 MB per doc)

**Query Execution:**
1. User question encoded to same 384-dim vector
2. Elasticsearch's HNSW (Hierarchical Navigable Small World) index finds 20 candidate documents
3. L2 distance computed: score = 1 / (1 + distance)
4. Top 3 scored documents returned with full metadata
5. Latency: ~70-100ms per query

**Why L2 distance?**
- Elasticsearch optimized for L2
- Legal documents naturally cluster well in this metric
- More stable than cosine for variable-length documents"

---

### "Why not use BM25 (keyword search) alone?"

**Answer:**
"BM25 is great for exact term matching but inadequate for legal domain:

1. **Term Variation**: Law uses both formal and colloquial terms
   - Query: 'hacking'
   - Document: 'unauthorized access to computer systems'
   - BM25 score: ~0.2-0.3 (very low)
   - Semantic score: ~0.85 (high, matches intent)

2. **Concept Expansion**: Questions contain synonyms
   - Query: 'punishment'
   - Should match: 'sentence', 'imprisonment', 'fine', 'penalty'
   - BM25 can't connect these
   - Semantic search: naturally clustered

3. **Cross-Act Relationships**: Same concept in different acts
   - 'Unauthorized access' appears in:
     - IT Act Section 66
     - IPC Section 379 (related concept)
   - BM25 treats as different concepts
   - Vectors bridge the gap"

---

### "What's the difference between Elasticsearch and FAISS?"

**Answer:**
"Great question. Initially we chose Elasticsearch for its hybrid capabilities (KNN + BM25). Later, we migrated to FAISS. Here's the comparison:

**Elasticsearch:**
- ✅ Distributed, scalable
- ✅ Both keyword (BM25) and vector (KNN) search
- ✅ Production-ready features (replication, persistence)
- ❌ ~1-2GB memory minimum
- ❌ Requires server running (Docker, Java)
- ❌ Setup complexity for MVP

**FAISS:**
- ✅ Lightweight, pure Python
- ✅ 1-5ms per query (10x faster)
- ✅ Minimal memory footprint
- ✅ Works offline, any environment
- ❌ Only vector search (no BM25)
- ❌ Single-machine scaling limit

**Our Decision:**
For MVP with ~2,400 documents and no distributed requirements, FAISS was overkill for Elasticsearch complexity. We chose pragmatism: sufficient speed, simpler deployment, easier to share demos and run locally."

---

### "How did you handle the vectors?"

**Answer:**
"Vectors created using SentenceTransformer model `all-MiniLM-L6-v2`:

**Model Choice:**
- 'Mini' = optimized for speed (1000+ docs/second)
- 'L6' = 6-layer architecture (efficient)
- 384-dim = good trade-off between accuracy and speed
- Trained on legal + general text relationships

**Vector Characteristics:**
- Each document collapsed into single 384-element array
- Similar meaning = nearby in vector space
- 'Murder' and 'Homicide' vectors close together
- 'Murder' and 'Bicycle' vectors far apart

**Storage:**
- Stored in Elasticsearch dense_vector field
- ~1 MB per document after compression
- Searchable via L2 distance metric

**Why 384 dimensions and not higher?**
- 768 dims: ~2x more accurate, ~2x slower, ~2x more storage
- 384 dims: sweet spot for real-time queries
- For legal domain, 384-dim vectors capture distinctions well"

---

## 🎓 Common Interview Questions

### Q: "Why vector search instead of just using an LLM with RAG?"

**Answer:**
"Good question! We actually do both:
1. **Retrieval** (Vector search): Find relevant documents quickly
2. **Reasoning** (LLM + RAG): Process documents to generate answer

The vector search phase is crucial because:
- LLMs have token limits (~4K-8K context)
- Searching 2,400 documents linearly takes too long
- Semantic search narrows to top-3 most relevant in ~100ms
- This efficiency enables real-time conversation

If we sent all 2,400 documents to the LLM:
- Would exceed token limits
- Would be 20x slower
- Would confuse the LLM (too much noise)

So retrieval (vector search) is the critical component that makes RAG practical."

---

### Q: "How did you measure retrieval quality?"

**Answer:**
"This is where we can improve. Currently:
- ✅ Qualitative testing: Manual queries to verify relevance
- ✅ User feedback: Chat interface shows user satisfaction
- ⚠️ Missing: Formal evaluation metrics

To properly measure, we'd need:
1. **Benchmark Dataset**: 100+ test queries with ground truth
2. **Metrics**:
   - Recall@K: Did top-3 contain correct sections?
   - NDCG: Are results ranked correctly?
   - MRR: Average rank of first correct result

3. **Baseline Comparison**:
   - BM25 only (keyword search)
   - Semantic search only
   - Hybrid (current approach)

For MVP, qualitative testing was sufficient. For production, we'd implement these metrics."

---

### Q: "What about updates? How do you handle new laws?"

**Answer:**
"Currently, we re-index when corpus changes. Process:
1. Add new JSONL documents to data directory
2. Run `src/index_documents.py` to encode and index
3. Restart Streamlit application
4. New documents searchable

For production scaling, you'd want:
- **Incremental Indexing**: Add single documents without full rebuild
- **Versioning**: Track which documents are current
- **A/B Testing**: Old vs. new retrieval showing both results
- **Search Analytics**: Which queries return poor results? Iterate."

---

### Q: "Any limitations you ran into?"

**Answer:**
"Yes, several:

1. **Embedding Quality**: Model trained on general text, not all legal concepts
   - Solution: Fine-tune embedding model on legal corpus

2. **Exact Matches Needed**: Sometimes user wants EXACT section text
   - Vector search may return similar but wrong section
   - Solution: Hybrid approach (keyword + semantic)

3. **Negation Handling**: 'NOT liable' vs 'liable' become similar vectors
   - Solution: Better prompting for LLM to handle nuance

4. **Cross-Act References**: One act references another
   - Currently: Separate queries
   - Future: Graph-based document linking

5. **Scalability**: FAISS limited to single machine
   - Future: Sharded FAISS or move to vector database"

---

### Q: "Why Groq API instead of OpenAI?"

**Answer:**
"Cost and speed:
- **Groq**: Fast inference, cheap ($0.02-0.10 per million tokens)
- **OpenAI GPT-4**: Better quality, expensive ($15-30 per million tokens)

Given:
- Use case: Legal Q&A (not super complex reasoning)
- Volume: Potential high volume (cost matters)
- Latency: Real-time chat (fast inference matters)

Groq's llama-3.1-8b was the right choice. If we needed GPT-4 level reasoning, we'd pay for OpenAI, but llama-3.1 is excellent for legal domain."

---

## 💼 How to Frame It (By Interview Type)

### For Startup/Fast-Paced Company
**Emphasize:**
- Quick MVP development (3-4 months to production-ready)
- Pragmatic architecture decisions
- Willingness to refactor when needed (ES → FAISS)

**Quote:** "We shipped fast with Elasticsearch, learned it was overkill, and switched to FAISS without disruption. That's the startup mindset: iterate quickly."

---

### For Big Tech (Google, Microsoft)
**Emphasize:**
- Scalability considerations
- Proper architecture decisions
- Trade-offs analysis

**Quote:** "For MVP, FAISS was sufficient. For scaling to millions of queries, we'd consider: distributed vector databases, caching layers, and multi-model inference."

---

### For AI/ML-Focused Company
**Emphasize:**
- Embedding selection and tuning
- Retrieval quality metrics
- Fine-tuning opportunities

**Quote:** "SentenceTransformer's all-MiniLM-L6-v2 was a good starting point, but for production, we'd fine-tune on legal domain corpus to improve precision."

---

### For Enterprise/Compliance
**Emphasize:**
- Data security (credentials in env vars)
- Explainability (reasoning graphs)
- Audit trail (which sections used)

**Quote:** "Every answer is fully traceable to specific legal sections. The reasoning graph shows exactly which provisions were considered, enabling audit and compliance verification."

---

## 📝 2-Minute Elevator Pitch

*"ALIS is a legal AI chat that answers questions about Indian law. The core technical challenge was semantic retrieval—users ask questions in plain language, but laws use specific terminology. We solved this using semantic embeddings: every legal document is converted to a 384-dimensional vector representing its meaning, then stored in Elasticsearch. When a user asks a question, we convert it to the same vector space and find the k-nearest neighbors—the most semantically similar documents. These are passed to an LLM (Groq) for reasoning, which generates a clear answer backed by specific legal sections. The reasoning is visualized as a graph showing exactly which sections were referenced and how they relate. We've since migrated from Elasticsearch to FAISS for simpler deployment and 10x faster queries."*

---

## Final Tips

✅ **Do:**
- Explain the problem first (why semantic search matters)
- Show concrete examples
- Admit limitations and future improvements
- Discuss trade-offs you made
- Emphasize learning and iteration

❌ **Don't:**
- Use jargon without explaining
- Claim your solution is perfect
- Avoid discussing why you chose tool X over Y
- Oversell the MVP—be honest about scale
- Forget to mention what you'd do differently

