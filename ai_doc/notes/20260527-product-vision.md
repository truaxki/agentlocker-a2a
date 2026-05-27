# AgentLocker — Product Vision Notes
**Date:** 2026-05-27  
**Session:** Kirk + Astra brainstorm  
**Status:** Raw capture — schema design to follow

---

## The Vision (as stated)

AgentLocker evolves from a personal job-search dashboard into a **multi-user platform** with three core pillars:

1. **User profiles** — each user stores a profile of themselves (skills, preferences, clearance, constraints) that acts as the matching engine for job scoring
2. **Crowdsourced job board** — users contribute scraped jobs to a shared, public pool; the more users scraping, the richer the board gets
3. **Semantic search** — jobs are semantically ranked against a given user's profile, not just keyword-matched

---

## What's Exciting About This

- **Network effect:** Every user who scrapes adds to the pool everyone benefits from. A solo user sees 50 jobs. 100 users see 5,000.
- **Semantic matching:** The job isn't just filtered by keyword — it's ranked against *your* profile. Same job, different score for different people.
- **Agent-native:** The scraping and scoring is done by agents (Hermes, RSR, future agents) — AgentLocker is the hub that aggregates their work.
- **Public board + private matching:** Jobs are public. Scores are private — computed on-demand against your profile.

---

## The Tension Kirk Identified

> "That also kind of seems like it could be a security thing."

Real concerns here:

### Privacy
- User profiles contain sensitive data: clearance level, salary expectations, location, skills, work history
- If profiles are used for matching, they must NEVER be public
- Scores computed from profiles must also stay private

### Data Quality / Abuse
- Public job board = anyone can contribute scraped data
- Risk: spam listings, malicious job posts, duplicate flooding
- Need moderation or at least deduplication + quality scoring

### Scraping legality
- Job boards (LinkedIn, Indeed, Google Careers) have ToS restrictions on scraping
- A *shared* scraping pool amplifies this risk — one user scraping Google Careers is gray area; 1,000 users doing it coordinated is a target
- Mitigation: aggregate results not raw scrapes, user-agent policies, rate limiting, opt-in contribution

### Who owns contributed jobs?
- If User A scrapes a job and User B applies through it, who gets credit?
- Does AgentLocker become a data broker?
- Apache 2.0 / open source framing helps — this is community-contributed public data, not sold

---

## Open Questions Before Schema Design

1. **Profile granularity** — Is the profile just `agentlocker.md` serialized to Postgres? Or a richer structured schema? What fields are required vs. optional?

2. **Job ownership** — Is a contributed job attributed to a user? Anonymous? Just timestamped?

3. **Deduplication strategy** — Same job posted by 3 users = 1 canonical record or 3 records? How do we detect duplicates? (URL, title+company hash, embedding similarity?)

4. **Scoring model** — Is semantic scoring done at query time (user asks "show me my best matches") or pre-computed at ingest? Pre-computing requires knowing which user profiles to score against.

5. **Public vs. private jobs** — Can a user mark a job as private (only they see it) before deciding to contribute it to the public pool?

6. **Agent contribution** — Do agent scrapers (Hermes on VPS) push jobs directly to Supabase? Or to a queue that gets reviewed/deduped first?

7. **Search surface** — Is the semantic search a Supabase `pgvector` query? Or a separate service? pgvector extension on Supabase Postgres is the simplest path.

8. **Rate of contribution** — Is there a per-user contribution limit to prevent flooding? A reputation/trust system?

---

## Proposed Data Boundaries

```
PRIVATE (Supabase, RLS enforced)
├── users            — auth identities
├── profiles         — user's matching profile (skills, prefs, constraints)
├── profile_vectors  — embeddings of user profiles (for fast matching)
├── applications     — user's job application history
└── saved_jobs       — user's personal job queue + statuses

PUBLIC / SHARED (Supabase, readable by all)
├── jobs             — canonical job records contributed by any user
├── job_vectors      — embeddings of job descriptions (for semantic search)
└── sources          — feed sources (job boards, URLs) the community tracks

COMPUTED ON DEMAND (ephemeral or cached)
└── match_scores     — profile × job similarity, computed at query time
                       (optionally cached per user per job, expires daily)
```

---

## The Core User Flow (Multi-User)

```
1. User signs up → creates profile (skills, clearance, salary, location, domains)
2. User installs Hermes (or uses hosted agent) → agent scrapes jobs from their feeds
3. Agent pushes deduped job records to shared Supabase jobs table
4. User opens AgentLocker dashboard → semantic search runs profile vs. job_vectors
5. User sees ranked list of jobs scored against *their* profile
6. User saves, applies, archives → stored in their private applications table
7. Community benefits — user's scraped jobs now visible to everyone else
```

---

## Technical Primitives Needed

- **pgvector** on Supabase — for embedding storage + cosine similarity search
- **Embedding model** — jobs and profiles both need to be embedded. Options:
  - OpenAI `text-embedding-3-small` (cheapest, hosted)
  - Local model via Hermes on VPS (free, slower)
  - Supabase Edge Function that calls embedding API on insert
- **Deduplication** — hash on `(company + title + location)` as primary dedup key; vector similarity as secondary
- **RLS policies** — profiles/applications locked to `auth.uid() = user_id`; jobs table readable by all, writable by authenticated users
- **Contribution queue** — jobs submitted by agents go to a `jobs_pending` table first, deduped, then promoted to `jobs`

---

## Risks to Flag

| Risk | Severity | Mitigation |
|---|---|---|
| Profile data leak | High | RLS + no profile data in public queries |
| Scraping ToS violation at scale | Medium | Rate limits, user-agent honesty, opt-in only |
| Job spam / low quality | Medium | Quality score threshold before promotion to public pool |
| Embedding costs at scale | Low-Medium | Cache embeddings, batch on ingest, use cheap model |
| User-contributed jobs = stale | Low | TTL on job records, contributor gets notified to refresh |

---

## Next Steps

- [ ] Finalize answers to Open Questions above (especially dedup strategy + scoring model)
- [ ] Design Supabase Postgres schema (tables, columns, RLS policies)
- [ ] Decide on embedding model and where it runs
- [ ] Design agent contribution API (how does Hermes push a job to Supabase?)
- [ ] Map A2A task flow: user requests matches → Vercel → Hermes → Supabase query → ranked results
