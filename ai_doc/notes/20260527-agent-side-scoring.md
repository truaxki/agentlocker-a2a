# AgentLocker — Architecture Decision: Agent-Side Scoring
**Date:** 2026-05-27  
**Session:** Kirk + Astra  
**Status:** Key architectural decision — captures the privacy-first scoring model

---

## The Problem with Centralized Scoring

Earlier we considered storing user profiles in Supabase and running semantic search there. Kirk correctly identified this as insecure and non-standardized:

- User profile data (clearance, salary, skills, constraints) in a shared DB is a liability
- Pre-computing scores centrally means the platform knows how every user ranks every job
- It creates a data broker problem — the platform accumulates sensitive career intelligence
- It doesn't scale cleanly to third-party agents built by other people

---

## The Solution: Agent-Side Scoring

**The key insight:** Separate the job database (public, shared, dumb) from the scoring logic (private, personal, smart).

```
┌─────────────────────────────────────────────────────┐
│           AgentLocker Central (Shared)               │
│                                                      │
│  Hermes Scraper Agent                                │
│  ├── scrapes dozens of job boards continuously       │
│  ├── deduplicates, normalizes, stores                │
│  └── maintains raw public job database               │
│                                                      │
│  A2A Server — "job-search" skill                     │
│  └── exposes: search(query, filters) → raw jobs[]   │
└─────────────────────────────────────────────────────┘
              │
              │ A2A  (raw, unscored jobs)
              ▼
┌─────────────────────────────────────────────────────┐
│         User's Personal Agent (Private)              │
│                                                      │
│  Hermes (Kirk's VPS) or any A2A-compliant agent      │
│  ├── holds user's profile locally (agentlocker.md)  │
│  ├── fetches raw jobs from central DB via A2A        │
│  ├── scores each job against private profile         │
│  └── returns ranked dashboard to user's frontend    │
│                                                      │
│  Profile NEVER leaves this agent.                    │
│  Scores are ephemeral — computed per session.        │
└─────────────────────────────────────────────────────┘
              │
              │ scored results (ephemeral)
              ▼
┌─────────────────────────────────────────────────────┐
│         AgentLocker Dashboard (Vercel)               │
│  └── displays personalized ranked job list           │
└─────────────────────────────────────────────────────┘
```

---

## Data Boundaries

### Central Job Database (Supabase — public read, agent write)
```sql
jobs
├── id              UUID
├── title           TEXT
├── company         TEXT
├── location        TEXT
├── remote_policy   TEXT        -- remote | hybrid | onsite
├── description     TEXT        -- normalized job description
├── source_url      TEXT        -- original listing URL
├── source_name     TEXT        -- "google_careers" | "jobswithdod" | etc.
├── posted_date     DATE
├── scraped_at      TIMESTAMPTZ
├── dedup_key       TEXT        -- hash(company+title+location+posted_date)
├── contributor_id  UUID        -- which agent/user contributed this
└── is_active       BOOLEAN     -- false if listing has gone dead
```

**No scores. No user data. Just jobs.**

### User Profile (stays on personal agent — never in Supabase)
```
agentlocker.md (local to agent VPS)
├── identity (name, location, clearance)
├── targeting (domains, seniority, salary range)
├── skills (evidence for LLM scoring)
├── hard constraints (auto-disqualifiers)
├── score_weights (per-dimension weights)
└── lanes (categorization)
```

### Scored Results (ephemeral — per session, never persisted centrally)
```
The personal agent returns:
├── job_id          (reference back to central DB)
├── fit_score       0-100 (computed locally)
├── lane            which lane this job falls into
├── why_fits[]      bullet points (LLM-generated)
├── why_not[]       concerns (LLM-generated)
├── one_liner       summary sentence
└── screen_verdict  pass | review | disqualified
```

The dashboard renders this. If the user navigates away and comes back, the agent re-scores on demand. No score is ever written back to the central DB.

---

## The A2A Interaction Flow

```
1. User opens AgentLocker dashboard
2. Dashboard calls user's personal agent via A2A:
   → SendMessage: "Find matching jobs for my profile"

3. Personal agent calls central AgentLocker A2A server:
   → skill: "job-search"
   → params: { query, filters (remote, clearance, etc.) }
   → returns: raw jobs[] (no profile info sent)

4. Personal agent scores each job locally:
   → LLM call with agentlocker.md + job description
   → produces fit_score, why_fits[], why_not[], lane

5. Personal agent returns scored results to dashboard via A2A:
   → TaskArtifactUpdateEvent (streamed as scores complete)
   → Dashboard renders live as results come in

6. User saves/applies/archives → stored in their private Supabase tables
   (saved_jobs, applications — private, RLS enforced)
```

---

## Why This is Better

| Concern | Centralized Scoring | Agent-Side Scoring |
|---|---|---|
| Profile privacy | ❌ Profile in shared DB | ✅ Profile never leaves agent |
| Score privacy | ❌ Platform knows your rankings | ✅ Scores are ephemeral |
| Vendor lock-in | ❌ Tied to AgentLocker's scorer | ✅ Any A2A agent can score |
| Customization | ❌ One scoring model for all | ✅ Each agent has its own profile |
| Security surface | ❌ Profile data at rest in cloud | ✅ No PII in shared database |
| Standardization | ❌ Custom API per platform | ✅ A2A protocol — any agent works |

---

## The "Orbs" Model — Job Records as Consumable Units

The central job database prepares jobs as clean, standardized records ready for any agent to consume. Think of each job as an "orb" — a self-contained unit of data:

```json
{
  "id": "uuid",
  "title": "Senior AI Security Engineer",
  "company": "Palantir",
  "location": "Remote",
  "description": "...",
  "source_url": "https://...",
  "posted_date": "2026-05-26"
}
```

Any agent that speaks A2A can fetch these orbs, score them against whatever profile it holds, and return personalized results. AgentLocker doesn't care what agent does the scoring — it just provides the data.

This is the **open platform play**: AgentLocker becomes the richest job database, and any A2A-compliant agent (Hermes, a custom agent, a future competitor's agent) can use it.

---

## What Supabase Actually Stores

Minimal footprint:

```
PUBLIC (readable by anyone)
└── jobs — raw job records, no user data

PRIVATE (RLS: user sees only their own)
├── users — auth identities (managed by Supabase Auth)
├── agent_registry — user's registered agent URLs (their personal Hermes)
├── saved_jobs — job_id + user's status (saved/applied/archived)
└── applications — application history, notes, follow-up dates

NOT IN SUPABASE
├── user profile / agentlocker.md — stays on agent VPS
├── fit scores — ephemeral, computed by personal agent
└── why_fits / why_not — ephemeral, never persisted centrally
```

---

## Open Questions Remaining

1. **Contribution trust** — Does any authenticated user's agent get to write to the jobs table? Or is there a review queue? Start with: authenticated + rate-limited + dedup enforced.

2. **Job TTL** — How long do jobs live in the central DB? Suggestion: mark `is_active = false` after 30 days unless re-scraped; hard delete after 90 days.

3. **Search API design** — What filters does the central A2A job-search skill expose? At minimum: `keywords`, `remote_policy`, `clearance_required`, `posted_after`. Clearance filter is important for Kirk's use case.

4. **Scoring transparency** — Should the personal agent ever write a *summary* score back to Supabase (not the breakdown, just "user X applied to job Y")? Useful for analytics but is another privacy tradeoff.

5. **Cold start problem** — New user, no personal agent yet. Does AgentLocker offer a hosted scoring option as fallback? Or is that a premium tier?

---

## Next Steps

- [ ] Finalize Supabase schema for `jobs` table (see open questions above)
- [ ] Design the central A2A job-search skill API (what params, what response shape)
- [ ] Design the personal agent scoring flow (how Hermes fetches + scores + streams back)
- [ ] Define contribution contract (what format agents must submit jobs in)
- [ ] Build dedup logic (hash key + duplicate handling)
