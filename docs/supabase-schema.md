# Supabase Schema Design for AgentLocker

**Date:** 2026-05-27  
**Author:** Hermes  
**Status:** Proposal / Draft  

---

## 1. Why Supabase is the Perfect Fit

A purely stateless architecture would cripple AgentLocker. If the Next.js dashboard had to fetch and parse PDFs on every page load, or if our background scraping agents couldn't persist job listings, the UX would be incredibly slow and fragmented.

Supabase gives us a stateful, secure backbone with three critical features:

1. **User Authentication & Session Management:** Native integration with Next.js App Router (using `@supabase/ssr`) to handle login, profile creation, and access tokens for our A2A agents.
2. **Supabase Storage:** A secure bucket to upload and host PDF/Word resumes.
3. **PostgreSQL with `pgvector` (RAG Engine):** This is the killer feature. Instead of just storing one generic resume, we can store multiple versions (e.g., "Full-Stack Dev," "Security Engineer," "AI DevOps"). When a scraping agent finds a job listing, it can perform a semantic vector search on Kirk's experience snippets directly inside Postgres to pull the most relevant experience for tailoring applications.

---

## 2. System Architecture

```
                       ┌─────────────────────────┐
                       │  AgentLocker Dashboard  │
                       │    (Next.js App)        │
                       └────────────┬────────────┘
                                    │ SQL / Auth
                                    ▼
┌──────────────┐ SQL   ┌─────────────────────────┐  Storage  ┌─────────────────┐
│  A2A Agents  ├───────►  Supabase Postgres DB   ├───────────► Supabase Storage │
│ (Hermes/RSR) │       │   (Realtime Enabled)    │           │ (PDF Resumes)   │
└──────────────┘       └─────────────────────────┘           └─────────────────┘
```

---

## 3. Database Schema Blueprint

Here is the complete PostgreSQL DDL (Data Definition Language) to initialize the AgentLocker backend database.

```sql
-- Enable pgvector extension for semantic RAG matching
create extension if not exists vector;

-- 1. PROFILES TABLE (Extensions of auth.users)
create table public.profiles (
  id uuid references auth.users on delete cascade primary key,
  full_name text not null,
  target_job_titles text[] default '{}',
  preferred_locations text[] default '{}',
  target_salary_min integer,
  target_salary_max integer,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable Row Level Security (RLS) on profiles
alter table public.profiles enable row level security;

create policy "Users can view own profile" on public.profiles
  for select using (auth.uid() = id);

create policy "Users can update own profile" on public.profiles
  for update using (auth.uid() = id);


-- 2. RESUMES TABLE (Metadata and Full Text)
create table public.resumes (
  id uuid default gen_random_uuid() primary key,
  profile_id uuid references public.profiles(id) on delete cascade not null,
  name text not null, -- e.g., "Software Engineer - Resume 2026"
  file_path text not null, -- Supabase Storage bucket file path
  parsed_text text, -- Extracted raw text for LLM parsing/matching
  is_primary boolean default false not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Index for searching resumes by profile
create index resumes_profile_id_idx on public.resumes(profile_id);

alter table public.resumes enable row level security;

create policy "Users can manage own resumes" on public.resumes
  for all using (auth.uid() = profile_id);


-- 3. RESUME CHUNKS TABLE (For Semantic RAG Search)
-- Chunking our resumes lets the LLM search for specific project bullet-points matching a job description.
create table public.resume_chunks (
  id uuid default gen_random_uuid() primary key,
  resume_id uuid references public.resumes(id) on delete cascade not null,
  profile_id uuid references public.profiles(id) on delete cascade not null,
  content text not null, -- specific bullet point or paragraph
  embedding vector(1536), -- 1536 dimensions for text-embedding-3-small (OpenAI)
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create index resume_chunks_embedding_idx on public.resume_chunks using hnsw (embedding vector_cosine_ops);
create index resume_chunks_profile_id_idx on public.resume_chunks(profile_id);

alter table public.resume_chunks enable row level security;

create policy "Users can manage own resume chunks" on public.resume_chunks
  for all using (auth.uid() = profile_id);


-- 4. SCRAPED JOBS TABLE (The Scraper Target)
create table public.scraped_jobs (
  id uuid default gen_random_uuid() primary key,
  profile_id uuid references public.profiles(id) on delete cascade not null,
  title text not null,
  company text not null,
  location text not null,
  salary_range text,
  description text not null, -- Full job description
  url text not null,
  match_score numeric(4, 2), -- 00.00 to 100.00 scored by Agent
  match_reasoning text,
  status text default 'new'::text not null, -- 'new', 'scoring', 'matched', 'ignored', 'applied', 'rejected'
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null,
  constraint scraped_jobs_profile_url_unique unique (profile_id, url)
);

create index scraped_jobs_profile_id_status_idx on public.scraped_jobs(profile_id, status);

alter table public.scraped_jobs enable row level security;

create policy "Users can manage own scraped jobs" on public.scraped_jobs
  for all using (auth.uid() = profile_id);


-- 5. AGENT REGISTRY TABLE (A2A Agents)
create table public.agents (
  id uuid default gen_random_uuid() primary key,
  profile_id uuid references public.profiles(id) on delete cascade not null,
  name text not null, -- e.g., "Hermes"
  description text,
  card_url text not null, -- /.well-known/agent-card.json url
  endpoint_url text not null, -- raw JSON-RPC endpoint
  is_active boolean default true not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create index agents_profile_id_idx on public.agents(profile_id);

alter table public.agents enable row level security;

create policy "Users can manage own registered agents" on public.agents
  for all using (auth.uid() = profile_id);
```

---

## 4. Semantic RAG Resume-Matching Hook

By storing chunks of Kirk's experience as vector embeddings inside `resume_chunks`, our A2A Hermes agent can run a database function to find the exact matching bullet points for a job description.

Here is the PostgreSQL function to execute this similarity search:

```sql
create or replace function match_resume_chunks (
  query_embedding vector(1536),
  match_threshold float,
  match_count int,
  filter_profile_id uuid
)
returns table (
  id uuid,
  content text,
  similarity float
)
language sql stable
as $$
  select
    id,
    content,
    1 - (embedding <=> query_embedding) as similarity
  from public.resume_chunks
  where profile_id = filter_profile_id
    and 1 - (embedding <=> query_embedding) > match_threshold
  order join public.resume_chunks on true
  order by embedding <=> query_embedding
  limit match_count;
$$;
```

---

## 5. Storage Buckets (For Resumes)

We will configure a private bucket in Supabase Storage called `resumes`.
*   **Security rule:** Users can only upload, download, or delete objects inside the folder matching their `auth.uid()`.
*   **Storage Policy:**
    ```sql
    create policy "Allow owners full access to their folder" on storage.objects
      for all using (bucket_id = 'resumes' and (storage.foldername(name))[1] = auth.uid()::text);
    ```

---

## 6. How background Agents update the Dashboard in Realtime

Supabase includes a PostgreSQL Realtime Engine. Instead of the Next.js frontend constantly polling the database for updates, it can subscribe directly to changes:

```typescript
// React component inside Next.js Dashboard
import { createClient } from '@/utils/supabase/client';

useEffect(() => {
  const supabase = createClient();
  
  const subscription = supabase
    .channel('scraped-jobs-changes')
    .on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'scraped_jobs' },
      (payload) => {
        console.log('Job database updated!', payload);
        // Trigger local UI re-render or push state update instantly
      }
    )
    .subscribe();

  return () => {
    supabase.removeChannel(subscription);
  };
}, []);
```

When a scraping agent writes a newly matched job or updates an application's status to `'applied'`, the change streams instantly to Kirk's browser.
