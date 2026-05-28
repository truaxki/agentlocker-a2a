# Hybrid Decentralized Vector Search & Agentic Grading

**Date:** 2026-05-27  
**Author:** Hermes  
**Status:** Proposal / Specification  

---

## 1. The Bottleneck: Scaling Decentralized Grading

While decentralized grading (LLM scoring running on the user's private Orb/VPS) is the ultimate model for privacy, it introduces a major **scalability bottleneck**:

*   **The Scenario:** The centralized public job board holds **10,000+ scraped job listings**.
*   **The Problem:** If a user's dashboard has to fetch and send all 10,000 full job descriptions to their private VPS via A2A, it would choke the network, consume gigabytes of bandwidth, and cost hundreds of dollars in LLM tokens just to score one day of scraped listings.
*   **The Objective:** We need a way to filter the 10,000+ jobs down to the **top 50–100 semantically relevant candidates** *before* running our deep, expensive agentic grading.

---

## 2. The Solution: Privacy-Preserving Vector Search

By combining **Centralized Vector Search** with **Decentralized Agentic Grading**, we get the absolute best of both worlds: high performance, low costs, and total privacy.

```
┌────────────────────────────────────────────────────────────────────────┐
│                      CENTRAL AGENTLOCKER CLOUD                        │
│                                                                        │
│ ┌────────────────────────┐  Scrapes  ┌───────────────────────────────┐ │
│ │  Public Scraper Mesh   ├──────────►│ Public Jobs DB (with Vector)  │ │
│ └────────────────────────┘           │ - title, company, description │ │
│                                      │ - embedding: vector(1536)     │ │
│                                      └──────────────┬────────────────┘ │
└─────────────────────────────────────────────────────┼──────────────────┘
                                                      ▲ 2. Vector Query
                                                      │    (No raw text)
                                                      │
                                                      │ 3. Top 50 Jobs
                                                      │    (Full text)
                                                      ▼
┌─────────────────────────────────────────────────────┴──────────────────┐
│                          USER PRIVATE ORB (VPS)                        │
│                                                                        │
│ ┌────────────────────────┐  Embeds   ┌───────────────────────────────┐ │
│ │   Private Resume /     ├──────────►│       Hermes VPS Agent        │ │
│ │   Search Criteria      │           │ - Generates query embedding   │ │
│ └────────────────────────┘           │ - Runs Agentic LLM Grading    │ │
│                                      └───────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

### The 4-Step Vector-Powered Pipeline

1.  **Central Embedding:** The central public scrapers calculate a vector embedding (using a cheap model like `text-embedding-3-small`) for every scraped job description and store it in `public.jobs.embedding`.
2.  **Private Vector Query (Zero-Leak Search):** 
    *   Your local Hermes agent embeds your resume or target search query into a flat array of 1536 floats.
    *   **Privacy Guard:** Hermes sends *only the vector embedding array* to the central database—**your raw resume text, personal details, and notes never leave your machine.** The central server just sees a mathematical coordinate.
3.  **Fast Similarity Filtering:** The central server runs a lightning-fast `pgvector` Cosine Similarity query against the 10,000+ jobs and returns the full text of only the **top 50 candidate jobs** that semantically match your profile.
4.  **Deep Agentic Grading:** Your private Hermes agent receives only those top 50 highly relevant candidate jobs, runs the deep LLM evaluation, generates personalized alignment scores, drafts cover letters, and saves them locally in your private database.

---

## 3. Database Schema (Vector-Enabled)

### Central Public Cloud Database (`public.jobs` with pgvector)

```sql
-- Enable vector extension
create extension if not exists vector;

create table public.jobs (
  id uuid default gen_random_uuid() primary key,
  title text not null,
  company text not null,
  location text not null,
  description text not null,
  url text not null unique,
  embedding vector(1536), -- 1536 dimensions (OpenAI / open-source equivalent)
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- HNSW index for lightning-fast approximate nearest neighbor search
create index jobs_embedding_hnsw_idx 
  on public.jobs using hnsw (embedding vector_cosine_ops);
```

### Central Database Search Function
This function allows Kirk's private agent to pass its query embedding vector and securely retrieve matched jobs:

```sql
create or replace function public.search_jobs_by_vector (
  query_embedding vector(1536),
  match_threshold float,
  match_count int
)
returns table (
  id uuid,
  title text,
  company text,
  location text,
  description text,
  url text,
  similarity float
)
language sql stable security definer
as $$
  select
    id,
    title,
    company,
    location,
    description,
    url,
    1 - (embedding <=> query_embedding) as similarity
  from public.jobs
  where 1 - (embedding <=> query_embedding) > match_threshold
  order by embedding <=> query_embedding
  limit match_count;
$$;
```

---

## 4. The Wire Protocol (A2A Vector Search Request)

When your dashboard or Hermes agent wants to run a vector search, it makes a standard, secured API request to the central AgentLocker server.

### Request Payload (`POST /api/jobs/vector-search`)
```json
{
  "jsonrpc": "2.0",
  "id": "c138fd97-768a-49eb-81da-9896799042b9",
  "method": "jobs/vector-search",
  "params": {
    "embedding": [0.0123, -0.0456, 0.0891, "... 1536 floats ...", 0.0078],
    "threshold": 0.35,
    "limit": 50
  }
}
```

### Response Payload
```json
{
  "jsonrpc": "2.0",
  "id": "c138fd97-768a-49eb-81da-9896799042b9",
  "result": {
    "jobs": [
      {
        "id": "4b6da3e5-...",
        "title": "Senior AI DevOps Engineer",
        "company": "Vercel",
        "location": "Remote (US)",
        "description": "We are looking for an engineer to scale our agent infrastructure...",
        "url": "https://vercel.com/careers/ai-devops",
        "similarity": 0.824
      }
    ]
  }
}
```

---

## 5. Architectural Benefits

| Feature | Without Embeddings | With Hybrid Vector Search |
|---|---|---|
| **Bandwidth** | ❌ Chokes (sending 10k jobs to VPS) | ✅ Minimal (sending 1 query vector + receiving 50 jobs) |
| **LLM Costs** | ❌ Runaway (scoring 10k jobs daily) | ✅ Microscopic (scoring only 50 relevant jobs) |
| **Privacy** | ❌ Centralized (must store raw resume) | ✅ Complete (only flat mathematical vectors are shared) |
| **Accuracy** | ❌ Keyword-bound (matches only raw words) | ✅ Semantic (matches concept e.g. "Next.js" with "Frontend") |
