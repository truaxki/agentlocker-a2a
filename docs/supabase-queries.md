# Querying Vector & Relational Data on Supabase

**Date:** 2026-05-27  
**Author:** Hermes  
**Status:** Spec / Implementation Guide  

This guide explains how to query the public job feed using a hybrid search of **vector embeddings** and **relational filters** (like clearance and remote policy) directly inside Supabase.

---

## 1. The Supabase Query Architecture

To perform a semantic similarity search on Supabase, we leverage Postgres’s native `pgvector` extension. 

Because standard SQL queries cannot easily compute vector cosine distances from client-side JS libraries directly, the standard Supabase pattern is to create a **PostgreSQL Database Function** (an RPC - Remote Procedure Call) and invoke it from our Next.js client.

```
┌──────────────────────────────┐
│  Next.js Dashboard Frontend  │
└──────────────┬───────────────┘
               │
               │ rpc('match_scraped_jobs')
               ▼
┌──────────────────────────────┐
│  Supabase Postgres Engine    │
│  ├── 1. Filters by metadata  │  (High performance, indexes utilized)
│  ├── 2. Computes Cosine Dist │  (pgvector <=> operator)
│  └── 3. Returns top candidates│
└──────────────────────────────┘
```

---

## 2. Step 1: Create the Postgres RPC Function

Run this SQL query inside the **Supabase SQL Editor** to create the hybrid search function. 

This function accepts a query vector embedding and standard relational parameters, filters the jobs, and sorts them by semantic relevance.

```sql
create or replace function match_scraped_jobs (
  query_embedding vector(1536),
  match_threshold float,
  match_count int,
  filter_remote_policy text default 'all',
  filter_clearance_required boolean default false
)
returns table (
  id uuid,
  title text,
  company text,
  location text,
  remote_policy text,
  description text,
  source_url text,
  posted_date date,
  similarity float
)
language sql stable
as $$
  select
    id,
    title,
    company,
    location,
    remote_policy,
    description,
    source_url,
    posted_date,
    1 - (embedding <=> query_embedding) as similarity
  from public.jobs
  where is_active = true
    -- 1. Relational filter: remote policy check
    and (filter_remote_policy = 'all' or remote_policy = filter_remote_policy)
    
    -- 2. Relational filter: security clearance check
    and (filter_clearance_required = false or clearance_required = filter_clearance_required)
    
    -- 3. Vector filter: similarity threshold barrier
    and 1 - (embedding <=> query_embedding) > match_threshold
    
  -- 4. Vector sort: order by closest cosine distance
  order by embedding <=> query_embedding
  limit match_count;
$$;
```

---

## 3. Step 2: Querying from Next.js (TypeScript)

Once the RPC function is defined in your Supabase database, you can query it from your Next.js dashboard code using the Supabase TS client (`@supabase/supabase-js`).

### Example Implementation

```typescript
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export async function searchJobs(profileEmbedding: number[]) {
  const { data, error } = await supabase.rpc('match_scraped_jobs', {
    query_embedding: profileEmbedding,       // 1536 floats computed on the user VPS
    match_threshold: 0.78,                  // Cosine similarity cut-off (78%)
    match_count: 50,                        // Limit top candidate jobs
    filter_remote_policy: 'remote',         // 'remote' | 'hybrid' | 'onsite' | 'all'
    filter_clearance_required: true         // Kirk's TS/SCI filter check
  });

  if (error) {
    console.error('Failed to query Supabase jobs:', error.message);
    throw error;
  }

  // data is now a typed array of the top 50 raw job "orbs" ready for local agent grading!
  return data;
}
```

---

## 4. Performance Tuning: HNSW Vector Indexes

Without an index, Postgres must perform a "sequential scan" (reading every single job row in the database) to calculate similarity. This is fine for 1,000 jobs, but slows down at 100,000+ jobs.

To keep queries lightning fast, we create an **HNSW (Hierarchical Navigable Small World)** vector index on the `embedding` column:

```sql
create index jobs_embedding_hnsw_idx 
on public.jobs 
using hnsw (embedding vector_cosine_ops);
```

### Why HNSW is preferred over IVFFlat:
*   **No Training Phase Required:** You can build an HNSW index immediately on an empty table; IVFFlat requires the table to be populated with data first to determine cluster centroids.
*   **Higher Accuracy at Scale:** HNSW is extremely robust and performs index lookups in logarithmic time.
