# Collaborative Agentic Job Board & Scraper Architecture

**Date:** 2026-05-27  
**Author:** Hermes  
**Status:** Proposal / Specification  

---

## 1. The Core Vision: The Collaborative Scraper Mesh

Scraping is historically **expensive, fragile, and rate-limited**. If 100 users are all using personal AI agents (like Hermes or RSR) to find React developer jobs, and each agent independently scrapes LinkedIn, Indeed, and company career pages, we hit multiple massive friction points:
1. **Redundant Cost:** Multiple users pay LLM/scraping API costs to extract the exact same Stripe or Vercel job listing.
2. **IP Blocks:** Rapid, uncoordinated hits from dozens of user VPS nodes trigger cloudflare/imperva blocks on target job boards.
3. **Wasted Compute:** Every agent re-parses and re-structures the same HTML files.

### The AgentLocker Hub Model: "Scrape Once, Share for All"
Instead of siloed scrapers, we pivot to a **Collaborative Scraper Mesh**. 

When Kirk's agent scrapes a job, it registers the raw details in a **shared, public job pool**. When Carla's agent searches for jobs, it query-searches the *already-scraped pool first*. If a job matching Carla's criteria is found, her agent gets the listing instantly for **zero cost** and with **zero scraping overhead**.

```
   Kirk's Agent                 Carla's Agent                New User's Agent
   (Scrapes Stripe)             (Scrapes Vercel)            (Just joined, idle)
         │                            │                             │
         ▼ Writes Job                 ▼ Writes Job                  │ Queries Pool
┌───────────────────────────────────────────────────────────────────────────────┐
│                          Shared public.jobs Pool                              │
│         (Crowdsourced, deduplicated, global job board repository)             │
└──────────────────────────────────────┬────────────────────────────────────────┘
                                       ▼ Matches privately
                        ┌──────────────────────────────┐
                        │  Personal Match Room (Private)│
                        │  - Kirk's Resume Match Score │
                        │  - Carla's Application State │
                        └──────────────────────────────┘
```

---

## 2. The Security & Isolation Partition (The "Security Thing")

Sharing job listings is powerful, but keeping personal data **100% secure** is non-negotiable. To achieve this, we enforce a strict architectural boundary inside Supabase Postgres using **Row-Level Security (RLS)**:

| Layer | Privacy Level | Data Elements | Access Policy |
|---|---|---|---|
| **Public Pool** | **Global Read / Auth Write** | Job titles, descriptions, requirements, salary, company, URL, scraped-by attribution | Any logged-in user can read. Any authenticated agent/user can insert/contribute. |
| **Private Profiles** | **Owner-Only** | Full name, target roles, budget, system configurations, OAuth tokens | Only the profile owner can read, write, or update. |
| **Private Resumes** | **Owner-Only** | Parsed resume text, skill lists, projects, vector embeddings | Only the owner's user session or authorized A2A agent can access. |
| **Private Matches** | **Owner-Only** | Individual match scores, LLM reasoning, application stages (`'applied'`, `'rejected'`, etc.) | Strictly private. Kirk cannot see Carla's match scores or application status, even on the same public job. |

---

## 3. Revised Database Schema Blueprint (Multi-User, Collaborative)

Here is the PostgreSQL schema engineered to support collaborative scraping while maintaining strict multi-tenant privacy.

```sql
-- Enable vector extension for private semantic scoring
create extension if not exists vector;

-- 1. PUBLIC JOBS POOL (Crowdsourced and Shared)
-- Shared across all users. Deduplicated by source URL.
create table public.jobs (
  id uuid default gen_random_uuid() primary key,
  title text not null,
  company text not null,
  location text not null,
  salary_range text,
  description text not null, -- Raw markdown or text description
  url text not null,
  contributed_by uuid references auth.users(id) on delete set null, -- Optional credit
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null,
  constraint jobs_url_unique unique (url) -- Forces deduplication across scrapers
);

-- Indexing for fast search and matching
create index jobs_title_company_idx on public.jobs(title, company);
create index jobs_created_at_idx on public.jobs(created_at desc);

-- RLS: Anyone logged in can read jobs. Authenticated users can insert them.
alter table public.jobs enable row level security;

create policy "Allow logged-in users to read all jobs" on public.jobs
  for select using (auth.role() = 'authenticated');

create policy "Allow authenticated users/agents to insert jobs" on public.jobs
  for insert with check (auth.role() = 'authenticated');


-- 2. USER PROFILES (Private)
create table public.profiles (
  id uuid references auth.users on delete cascade primary key,
  full_name text not null,
  target_job_titles text[] default '{}',
  preferred_locations text[] default '{}',
  target_salary_min integer,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

alter table public.profiles enable row level security;

create policy "Users can manage own profile" on public.profiles
  for all using (auth.uid() = id);


-- 3. USER RESUMES (Private - Text Only, No Storage Bucket Required)
-- Storing raw parsed text directly inside the database simplifies the stack, eliminating storage bucket overhead.
create table public.resumes (
  id uuid default gen_random_uuid() primary key,
  profile_id uuid references public.profiles(id) on delete cascade not null,
  name text not null, -- e.g. "React Developer Resume"
  parsed_text text not null, -- The core text content parsed from PDF/txt
  is_primary boolean default false not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create index resumes_profile_id_idx on public.resumes(profile_id);

alter table public.resumes enable row level security;

create policy "Users can manage own resumes" on public.resumes
  for all using (auth.uid() = profile_id);


-- 4. PRIVATE USER-JOB MATCHES (Private)
-- This table joins public jobs and private users, storing their private matching details and application state.
create table public.user_job_matches (
  id uuid default gen_random_uuid() primary key,
  profile_id uuid references public.profiles(id) on delete cascade not null,
  job_id uuid references public.jobs(id) on delete cascade not null,
  match_score numeric(4, 2), -- 0.00 to 100.00 scored privately by their Agent
  match_reasoning text, -- private explanation why the job fits their profile
  status text default 'new'::text not null, -- 'new', 'scoring', 'matched', 'ignored', 'applied', 'rejected'
  notes text, -- Personal notes about interviews, custom contacts, etc.
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null,
  constraint user_job_matches_profile_job_unique unique (profile_id, job_id)
);

create index user_job_matches_profile_status_idx on public.user_job_matches(profile_id, status);

alter table public.user_job_matches enable row level security;

-- Strictly private: Users can only see and edit their own matching records.
create policy "Users can manage own job matches" on public.user_job_matches
  for all using (auth.uid() = profile_id);


-- 5. A2A AGENT REGISTRY (Private)
create table public.agents (
  id uuid default gen_random_uuid() primary key,
  profile_id uuid references public.profiles(id) on delete cascade not null,
  name text not null,
  card_url text not null,
  endpoint_url text not null,
  is_active boolean default true not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create index agents_profile_id_idx on public.agents(profile_id);

alter table public.agents enable row level security;

create policy "Users can manage own registered agents" on public.agents
  for all using (auth.uid() = profile_id);
```

---

## 4. How the Flow Works: From Scraper to Private Dashboard

Let's trace how a collaborative flow behaves securely for two users (Kirk and Carla):

### Step A: Collaborative Contribution (Public)
1. Kirk's background scraping agent discovers a listing at Stripe: `https://stripe.com/jobs/react-dev`.
2. The agent calls standard HTTPS POST `public.jobs` with the raw text and metadata.
3. Because of Postgres's `unique(url)` constraint, if Carla's agent already scraped this job 10 minutes ago, Postgres gracefully ignores the duplicate insert (`ON CONFLICT DO NOTHING`), saving database bloat.

### Step B: Asynchronous Private Scoring (Private)
1. Kirk's local A2A agent (Hermes) detects a new row in the public `jobs` table (via real-time subscription or webhook).
2. Hermes fetches Kirk's private resume text from `public.resumes` and the job description from `public.jobs`.
3. Hermes scores the match privately, writes the rating and LLM explanation into `public.user_job_matches` for Kirk's profile ID:
   ```json
   {
     "profile_id": "kirk-uuid",
     "job_id": "stripe-job-uuid",
     "match_score": 92.5,
     "match_reasoning": "Excellent fit. Your experience with Next.js App Router and Stripe checkout flows matches..."
   }
   ```
4. Carla's agent does the exact same thing concurrently using Carla's private resume, generating a `71.0` score for Carla.

### Step C: Rendering the Dashboard UI (Isolated)
*   **Kirk's View:** Querying `select * from public.jobs j join public.user_job_matches m on j.id = m.job_id` returns Stripe with a **92.5** match score.
*   **Carla's View:** The exact same query under Carla's user ID returns Stripe with a **71.0** match score.
*   Neither user can see the other's profile, resume, match scores, or application status.

---

## 5. Summary of Architectural Advantages

*   **Drastically Simpler Stack:** Removing the storage bucket means resumes are stored as native relational text. This eliminates file-handling middleware, storage SDK configurations, and CDN caching concerns.
*   **Multiplier Effect on Scraped Data:** The value of the hub scales quadratically with the number of users. If 5 users add their custom agents, they collectively build a powerful, real-time index of the entire job market.
*   **Perfect Privacy Partition:** Row-Level Security (RLS) is baked into the database kernel, ensuring that no client-side developer error can accidentally leak one user's resume or target parameters to another.
