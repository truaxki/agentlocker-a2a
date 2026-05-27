# Decentralized Grading & A2A Job Search Architecture

**Date:** 2026-05-27  
**Author:** Hermes  
**Status:** Proposal  

---

## 1. The Core Paradigm Shift: Central Scraper × Decentralized Grading

The collaborative mesh model solved the scraping cost bottleneck, but it introduced a massive security and trust bottleneck: **users had to trust the central database or dashboard with their private resumes and raw job matches.**

By shifting to **Decentralized Grading**, we achieve absolute security and elegant architectural separation.

### The New Architecture:
1. **The Centralized AgentLocker Scraper:** A high-throughput, centralized scraper (run by AgentLocker) pulls a massive database of public, raw, unscored job listings.
2. **The Private Personal Agent (The Orb / Hermes):** Each user runs their own private, independent agent (like Hermes) on their own VPS. This agent holds their **raw resumes, private experiences, and matching criteria**.
3. **The A2A Evaluation Pipe:** The central dashboard fetches raw jobs from the centralized database and sends them directly to the user's **personal agent** via the A2A protocol. The personal agent does the actual matching and grading locally and returns the scored keys and reasoning back to the dashboard.

```
┌────────────────────────────────────────────────────────┐
│               AgentLocker Dashboard (Web)              │
└───────────┬────────────────────────────────┬───────────┘
            │                                │ A2A JSON-RPC
            │ 1. Fetch raw jobs              │ 2. Post jobs to evaluate
            ▼                                ▼
┌────────────────────────┐       ┌───────────────────────┐
│ AgentLocker DB (Cloud) │       │   Kirk's Hermes VPS   │
│ (Raw Public Jobs Only) │       │                       │
│                        │       │ - Private Resumes     │
│ - No user resumes      │       │ - evaluate-jobs skill │
│ - No private scores    │       │                       │
└────────────────────────┘       └───────────┬───────────┘
                                             │
                                             │ 3. Return scored keys
                                             ▼
                                 [Render Graded Dashboard]
```

---

## 2. Why This is Far More Secure and Standardized

| Dimension | Collaborative / Public DB Model | Decentralized A2A Model (New) |
|---|---|---|
| **Resume Privacy** | Resume must be uploaded to the cloud DB (Risk of exposure). | Resume **never** leaves the user's VPS. |
| **Grading Customization** | Scoring logic is fixed in the centralized cloud database. | Custom scoring weightings and LLM choices are fully controlled by the user on their VPS. |
| **Data Footprint** | AgentLocker must store private matches, scores, and records. | AgentLocker stores **zero** private user data. It's just a raw public feed + agent proxy. |
| **A2A Compliance** | Custom DB structures for mapping scores across users. | Uses the standard A2A `AgentSkill` protocol for task dispatch and artifact streaming. |

---

## 3. Protocol Flow Spec

When a user opens the AgentLocker dashboard to search for jobs, the system executes the following standardized sequence:

### Step 1: Dashboard Fetches Raw Jobs
The frontend fetches the latest 20 job listings matching the user's broad filters (e.g., "React," "Remote") from the public database:
```
GET https://api.agentlocker.io/jobs?query=React&location=remote
```

### Step 2: Dashboard Dispatches to Personal Agent via A2A
The frontend proxies an A2A stream request to the user's registered personal agent URL (declared in their Agent Card). It uses the **`evaluate-jobs`** skill:

**`POST /a2a/jsonrpc`**
```json
{
  "jsonrpc": "2.0",
  "id": "req-999888",
  "method": "message/stream",
  "params": {
    "message": {
      "kind": "message",
      "messageId": "msg-12345",
      "role": "user",
      "parts": [
        {
          "kind": "text",
          "text": "Score these jobs against my active profile and highlight any skill gaps."
        },
        {
          "kind": "data",
          "data": {
            "jobs": [
              {
                "id": "job-stripe-101",
                "title": "Staff Frontend Engineer, Dashboard",
                "company": "Stripe",
                "description": "Looking for React, Tailwind, and GraphQL experts..."
              },
              {
                "id": "job-vercel-202",
                "title": "Senior Next.js Developer",
                "company": "Vercel",
                "description": "Looking for App Router, Edge runtime, and serverless infrastructure devs..."
              }
            ]
          }
        }
      ]
    }
  }
}
```

### Step 3: Personal Agent Grades Locally and Streams Results
The personal agent (running on Kirk's VPS) loads the text of his private resumes, intercepts the `jobs` payload, runs local LLM comparison grading, and streams back **standardized Task Artifacts** in real-time over the SSE connection:

```event-stream
data: {"kind": "status-update", "taskId": "task-888", "status": {"state": "working"}}

data: {"kind": "artifact-update", "taskId": "task-888", "artifact": {"artifactId": "score-stripe-101", "parts": [{"kind": "data", "data": {"job_id": "job-stripe-101", "score": 92.5, "reasoning": "Strong React and UI systems match. Gaps: GraphQL is weak on resume.", "status": "matched"}}]}}

data: {"kind": "artifact-update", "taskId": "task-888", "artifact": {"artifactId": "score-vercel-202", "parts": [{"kind": "data", "data": {"job_id": "job-vercel-202", "score": 78.0, "reasoning": "Fits React experience, but lacks Edge/Serverless infrastructure projects.", "status": "scoring"}}]}}

data: {"kind": "status-update", "taskId": "task-888", "status": {"state": "completed"}, "final": true}
```

---

## 4. Declaring the `evaluate-jobs` Skill (Astra/Hermes Agent Card)

Every personal agent declares this capability inside its public Agent Card (`/.well-known/agent-card.json`). The AgentLocker dashboard reads this card on registration to know how to construct the evaluation request.

```json
{
  "id": "evaluate-jobs",
  "name": "Job Match Evaluator",
  "description": "Accepts a list of job descriptions and grades them against the private resume and career preferences.",
  "tags": ["career", "jobs", "evaluation"],
  "inputModes": ["application/json"],
  "outputModes": ["application/json"],
  "examples": [
    "Grade this list of 10 scraping matches against my software developer resume"
  ]
}
```

---

## 5. Summary of Database Division

### A. Centralized AgentLocker Database (Stateless for Users)
```sql
-- RAW PUBLIC JOBS FEED
create table public.jobs (
  id uuid default gen_random_uuid() primary key,
  title text not null,
  company text not null,
  location text not null,
  description text not null,
  salary_range text,
  url text not null unique,
  scraped_at timestamp with time zone default now() not null
);
```

### B. Private Personal Agent Database (On User VPS)
```sql
-- STRICTLY PRIVATE RESUME AND PREFERENCES
create table private.resumes (
  id uuid default gen_random_uuid() primary key,
  name text not null,
  content text not null, -- raw text, parsed locally
  is_active boolean default true not null
);

-- LOCAL EVALUATION CACHE
create table private.job_grades (
  job_id uuid primary key, -- maps to public.jobs.id
  score numeric(4, 2) not null,
  reasoning text not null,
  decision text default 'new'::text not null, -- 'matched', 'applied', 'ignored', 'interviewing'
  graded_at timestamp with time zone default now() not null
);
```
