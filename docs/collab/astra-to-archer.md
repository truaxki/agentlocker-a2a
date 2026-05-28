# Astra → Ironborn Archer (Handoff #2)

**Timestamp:** 2026-05-28  
**From:** Astra (VPS / Active Session)  
**To:** Ironborn Archer (Machine 1 / Local Developer Agent)  

---

## 🚀 Major Session — Read This First

Kirk and I just had a vision session. Two critical documents were committed:

- `ai_doc/notes/20260528-market-strategy-and-legal.md` — the full product vision, legal basis, and go-to-market strategy
- `ai_doc/notes/20260528-embedding-standard.md` — the canonical embedding spec. **Supersedes the `text-embedding-3-small` reference in `evaluate-jobs-spec.md`.** We're standardizing on `BAAI/bge-base-en-v1.5` (768d), fully local.

Pull and read both before touching any embedding-related code.

---

## 🎯 The Vision (One Paragraph)

AgentLocker is "Agentic Indeed" — a privacy-first job board where the central DB is a dumb public job index, and all the intelligence lives in the user's personal agent. The user's `agentlocker.md` profile is embedded locally using `bge-base-en-v1.5`. Only the resulting `float32[768]` vector crosses the wire to Supabase for KNN search. Profile text, salary, clearance level — none of it leaves the user's machine. This is architecturally different from every existing job board and is the product moat.

---

## ✅ What's Decided (Don't Revisit)

1. **Embedding model:** `BAAI/bge-base-en-v1.5` (768d), local, no API key
2. **Central DB:** Supabase with `pgvector`, `vector(768)` column, HNSW index
3. **KNN function:** `search_jobs_by_vector(query_embedding vector(768), ...)` — schema in the embedding standard doc
4. **Privacy contract:** Profile never leaves the agent. Vector only.
5. **Legal basis:** hiQ v. LinkedIn (2022) — public data scraping is legal. We link, not mirror. We respect robots.txt.

---

## 📋 Archer's Action Items

### 1. Supabase Schema Migration
Apply the `search_jobs_by_vector` SQL from `20260528-embedding-standard.md` to the Supabase project. Confirm the HNSW index builds successfully. Report back with row count + index status.

### 2. Next.js BFF Route — Vector Search
In the Next.js app, add a route that:
- Accepts `POST /api/jobs/search` with `{ query_embedding: float[], threshold?: number, limit?: number }`
- Validates the Supabase JWT (Supabase client on server side)
- Calls `supabase.rpc("search_jobs_by_vector", ...)` 
- Returns the ranked job list to the client

The frontend never calls Supabase directly — everything goes through the Next.js BFF. This keeps the anon key server-side.

### 3. Agent Card Update
Update `specs/agent-cards/hermes.json` to include the standardized `embedding_standard` capability block from `20260528-embedding-standard.md`.

### 4. Local Scraper → Embed → Supabase Pipeline
When scraping a new job locally, before writing to Supabase:
1. Extract signal text (requirements + benefits) — see `extract_embed_text.py` pattern in Hermes
2. Embed with `bge-base-en-v1.5`, `passage:` prefix
3. Write `embedding` column to Supabase alongside job fields

This is the only part that runs on the local machine (or our VPS scraper cron). The embedding is computed once, stored centrally.

---

## 💬 Drop your status in `docs/collab/archer-to-astra.md` when you've pulled.

— Astra, signing off.
