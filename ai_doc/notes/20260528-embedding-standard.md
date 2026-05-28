# AgentLocker — Embedding Standard
**Date:** 2026-05-28  
**Status:** Canonical Reference — All agents implementing `evaluate-jobs` must conform to this  

---

## The Canonical Model

| Field | Value |
|---|---|
| Model | `BAAI/bge-base-en-v1.5` |
| Dimensions | `768` |
| Provider | Local (no API key required) |
| Install | `pip install sentence-transformers` |
| HuggingFace | `sentence-transformers/all-MiniLM-L6-v2` is NOT the same — use BGE |

**Why BGE, not OpenAI text-embedding-3-small?**  
- Runs fully locally on any VPS — no API key, no per-call cost, no external data exposure  
- 768d vs 1536d cuts Supabase index storage roughly in half  
- BEIR benchmark: BGE-base outperforms ada-002 on most retrieval tasks  
- The user's profile embedding never touches an external API — this is the privacy guarantee  

**⚠️ NOTE:** The earlier `evaluate-jobs-spec.md` referenced `text-embedding-3-small (1536d)`. That is superseded by this document. Use `bge-base-en-v1.5 (768d)` everywhere.

---

## The HyDE Asymmetric Prefix Pattern

BGE models use asymmetric prefixes for better retrieval quality. **This is not optional** — omitting prefixes degrades cosine similarity scores significantly.

```python
# Profile / search query side — what the USER wants
query_text = f"query: {profile_text}"

# Job posting side — what the JOB offers  
passage_text = f"passage: {job_description_text}"
```

**Why this matters:** BGE was trained with these prefixes. Without them, the model treats both sides identically and the cosine similarity is flat/uninformative. With them, the vector space is oriented so that "what I'm looking for" aligns with "what this job offers."

---

## Agent Card Declaration (standardized block)

Every A2A-compliant agent implementing `evaluate-jobs` MUST publish this in its `agent-card.json`:

```json
{
  "id": "evaluate-jobs",
  "name": "Job Evaluation & Grading",
  "description": "Grades raw public jobs against a private user profile locally. Profile never leaves the agent.",
  "capabilities": {
    "embedding_standard": {
      "model_name": "BAAI/bge-base-en-v1.5",
      "dimensions": 768,
      "provider": "local",
      "prefix_query": "query:",
      "prefix_passage": "passage:",
      "encoding_format": "float32"
    }
  }
}
```

The AgentLocker central DB uses this declaration to confirm the agent's vectors are compatible with the public index before accepting a KNN query. Agents declaring a different model or dimension are incompatible and will receive a `400 embedding_standard_mismatch` error.

---

## The Privacy Contract

This is the core architectural guarantee that makes AgentLocker legally and ethically distinct from every other job platform:

```
agentlocker.md (user profile, salary, clearance, constraints)
        │
        │  ← stays here, on the user's machine/VPS, forever
        ▼
bge-base-en-v1.5 encodes locally
        │
        │  only this crosses the wire ↓
        ▼
float32[768] — a mathematical coordinate with no recoverable personal information
        │
        ▼
Supabase KNN query → top 50 job candidates (public text, already on the internet)
        │
        ▼
Deep LLM scoring runs locally, against private profile
        │
        ▼
Ranked results displayed in AgentLocker cockpit
```

**The central platform never receives:**
- Raw profile text
- Salary expectations
- Clearance level
- Personal notes
- Resume content
- Hard constraint rules

**The central platform only stores:**
- Public job listing text (already publicly available)
- `float32[768]` embeddings of job descriptions (no personally identifying information)

---

## Supabase Schema (Canonical)

```sql
-- Enable vector extension (already enabled on Supabase by default)
create extension if not exists vector;

-- Jobs table with 768-dim embedding column
alter table public.jobs 
  add column if not exists embedding vector(768);

-- HNSW index for fast approximate nearest neighbor search
create index if not exists jobs_embedding_hnsw_idx 
  on public.jobs using hnsw (embedding vector_cosine_ops);

-- Search function — accepts query vector and optional metadata filters, returns ranked candidates
create or replace function public.search_jobs_by_vector(
  query_embedding            vector(768),
  match_threshold            float   default 0.35,
  match_count                int     default 50,
  filter_remote_policy       text    default 'all',
  filter_clearance_required  boolean default null
)
returns table (
  id               uuid,
  title            text,
  company          text,
  location         text,
  remote_policy    text,
  description      text,
  source_url       text,
  similarity       float
)
language sql stable security definer as $$
  select
    id, title, company, location, remote_policy, description, source_url,
    1 - (embedding <=> query_embedding) as similarity
  from public.jobs
  where embedding is not null
    and 1 - (embedding <=> query_embedding) > match_threshold
    -- Relational metadata filter 1: remote policy check
    and (filter_remote_policy = 'all' or remote_policy = filter_remote_policy)
    -- Relational metadata filter 2: clearance requirement check (optional)
    and (filter_clearance_required is null or clearance_required = filter_clearance_required)
  order by embedding <=> query_embedding
  limit match_count;
$$;
```

---

## Python: Embedding a Profile (User Side)

```python
from sentence_transformers import SentenceTransformer
from pathlib import Path
import numpy as np

MODEL_NAME = "BAAI/bge-base-en-v1.5"
EMBED_DIM  = 768

_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model

def embed_profile(profile_text: str) -> list[float]:
    """Encode user profile as a query vector. Returns float32 list for Supabase."""
    vec = get_model().encode(f"query: {profile_text}", normalize_embeddings=False)
    return np.array(vec, dtype=np.float32).tolist()

def embed_job(job_text: str) -> list[float]:
    """Encode job description as a passage vector. Used by central scraper."""
    vec = get_model().encode(f"passage: {job_text}", normalize_embeddings=False)
    return np.array(vec, dtype=np.float32).tolist()
```

---

## Python: Querying Supabase from Hermes VPS

```python
from supabase import create_client
import os

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_ANON_KEY"]  # anon key is fine — function is security definer
)

def semantic_job_search(
    profile_text: str,
    threshold: float = 0.35,
    limit: int = 50
) -> list[dict]:
    """
    Embed profile locally, send only the vector to Supabase.
    Profile text never leaves this machine.
    """
    query_vec = embed_profile(profile_text)  # local computation
    
    result = supabase.rpc("search_jobs_by_vector", {
        "query_embedding": query_vec,  # only the vector crosses the wire
        "match_threshold": threshold,
        "match_count": limit
    }).execute()
    
    return result.data
```

---

## The Text Extraction Step (Don't Skip This)

Raw job HTML is 40-60% boilerplate (EEO statements, legal disclaimers, application instructions). Embedding raw text pollutes the vector space. Always extract signal text before embedding:

**What to extract:**
- Requirements: skills, experience, clearance, responsibilities
- Benefits: salary range, remote policy, equity

**What to strip:**
- "We are an equal opportunity employer..."
- "To apply, submit your resume to..."
- Repeated marketing copy
- Legal boilerplate

This step runs via `cron/job_search/extract_embed_text.py` in Hermes. The extracted `embed_text` is what gets embedded — not the raw description.

**Impact:** 15-20% improvement in retrieval precision (ArXiv:2310.05461, 2023).

---

## sqlite-vec (Local DB) — Known Pitfalls

For the local `job_search.db` (personal agent side), vectors are stored in sqlite-vec:

**Upsert pattern — DO NOT use `INSERT OR REPLACE`:**
```python
# WRONG — raises UNIQUE constraint on vec0 virtual tables
conn.execute("INSERT OR REPLACE INTO jobs_vec(job_id, embedding) VALUES (?, ?)", ...)

# CORRECT — always DELETE then INSERT
conn.execute("DELETE FROM jobs_vec WHERE job_id = ?", (job_id,))
conn.execute("INSERT INTO jobs_vec(job_id, embedding) VALUES (?, ?)", (job_id, vec_bytes))
```

**KNN query pattern:**
```sql
SELECT job_id, distance
FROM jobs_vec
WHERE embedding MATCH ?    -- pass vector as bytes
ORDER BY distance
LIMIT 20;
```

---

## Version Tracking

When the embedding model or prompt changes, bump `EMBED_VERSION` in `embedder.py` and re-embed all active jobs. Stale vectors from a different model version produce meaningless cosine similarities.

```python
EMBED_VERSION = "bge-base-en-v1.5-v1.0"  # model-name + pipeline-version
```

Store this on each job: `metadata_json.embed_version`. Query for jobs where this doesn't match the current version to identify stale embeddings.
