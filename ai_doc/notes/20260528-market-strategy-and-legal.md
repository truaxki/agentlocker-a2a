# AgentLocker — Market Strategy & Legal Framework
**Date:** 2026-05-28  
**Session:** Kirk + Astra  
**Status:** Strategic Notes — High Priority  

---

## The Big Idea: "Agentic Indeed"

AgentLocker is not just a personal job tracker. The architecture we've designed is the foundation for something genuinely new in the market:

> **A privacy-first, agent-native job board where your personal AI finds your next job — and your profile never leaves your machine.**

The central DB is a dumb public job index. The intelligence lives with the user's agent. The vector embedding is the only thing that crosses the wire. This is architecturally different from every existing job board and that difference is both the product moat and the legal shield.

---

## Is Aggregating and Linking Legal? (Yes — Here's Why)

### The Google Precedent
What Google does is aggregate, index, and link to publicly available web content. This is legal. AgentLocker does the same thing for job listings specifically. The key legal principle: **hyperlinking to publicly accessible content is not copyright infringement.**

### The hiQ Labs v. LinkedIn Landmark
This is the definitive case. In 2022, the Ninth Circuit ruled that scraping *publicly accessible* data does not violate the Computer Fraud and Abuse Act (CFAA). LinkedIn (and by extension any job board) cannot legally block automated collection of content visible to the public without a login.

**Key distinction:** The ruling applies to data accessible without authentication. SSO-gated listings (the `signin?jobId=` pattern we already flag in our DB) are a different legal situation. We already handle this — those get flagged `apply_type: sso_gated` and we don't store the full description.

### What Indeed Actually Does
Indeed is essentially a job board aggregator. It scrapes employer career pages and ATS platforms, stores the text, and links back to the original posting. This model has been validated commercially and legally for 20+ years. We are doing the same thing with a superior technical architecture.

### Our Additional Legal Protections
1. **We link, not replicate** — the source URL is the canonical reference. We store normalized descriptions for search, not for distribution.
2. **No login-gated content** — we only index what's publicly visible.
3. **robots.txt compliance** — the scraper should respect `Disallow` directives. This is not legally required but is an industry norm that protects against ToS claims.
4. **ToS violations are civil, not criminal** — even if a job board's ToS prohibits scraping, the remedy is typically a cease-and-desist, not criminal liability. We can respond to those on a case-by-case basis.
5. **The privacy architecture is a legal asset** — because we never see user profile data, we have no liability for mishandling it. GDPR, CCPA, HIPAA (for cleared-role health data) concerns go to zero on the platform side.

### Where We Should Be Careful
- **LinkedIn specifically** — they are aggressive litigators. We should not auto-scrape LinkedIn listings. Link aggregation from public job postings is fine; building a LinkedIn mirror is not.
- **Copyright on job descriptions** — job descriptions are generally considered factual/functional text and have thin copyright protection, but storing full text verbatim at scale is riskier than storing structured summaries. Our extract-then-embed pipeline (requirements + benefits only, not full raw description) is actually the legally safer approach.
- **CFAA edge cases** — scraping behind a CAPTCHA or rate-limit that requires circumvention is legally murky. Keep scrapers respectful and rate-limited.

---

## Market Strategy

### Positioning: The Privacy-Native Job Platform

Every existing job board has the same fundamental architecture problem: **your profile is their product.** LinkedIn sells your data to recruiters. Indeed uses your search behavior to target you. Glassdoor aggregates your salary disclosures.

AgentLocker's positioning:

> **"Your agent finds the job. Your profile stays home."**

This is not just a privacy feature — it's a structural shift in who has leverage. Right now job boards extract value from users by being the data aggregator. AgentLocker flips this: the value lives in the user's private agent, and the platform is just a commodity index.

### Go-to-Market Tiers

**Tier 1 — Personal (Kirk's use case right now)**
- Self-hosted Hermes agent on VPS
- Local `agentlocker.md` profile
- Free central job index (public good / open API)
- Zero cost to the user beyond VPS hosting

**Tier 2 — Managed Personal Agent**
- Hermes hosted on a managed VPS (Kirk's infrastructure)
- User brings their own `agentlocker.md`
- One-click setup wizard
- Monthly subscription ($10–30/mo)
- Target: technical professionals who want the privacy model but don't want to self-host

**Tier 3 — Enterprise / Team**
- Team-level job discovery (shared lane configs, not shared profiles)
- Recruiter-facing API: post to the AgentLocker index and get in front of agent-native candidates
- Target: small cleared-space defense contractors, ML labs, boutique tech shops

### Network Effects
The job index grows with every agent that contributes scraped listings back. This is a **data flywheel**: more agents → more sources → richer index → better search → more agents. Unlike LinkedIn, the data flywheel doesn't require locking users in — it's federated by design.

### The Cleared-Role Moat
Cleared job boards (ClearanceJobs, etc.) are notoriously terrible UX and have zero semantic search capability. A cleared-role-aware semantic search that understands `TS vs TS/SCI vs poly` as a hard constraint hierarchy — and never sends that clearance data to a central server — is a genuinely defensible product in that market.

Kirk's `agentlocker.md` already has this: poly is a hard disqualifier, TS preferred, TS/SCI with poly required is auto-screened. That logic runs on the user's agent. The central DB just has `clearance_required` as a filterable field. Nobody else has built this.

### Monetization Options (Ranked by Privacy Compatibility)
1. **Subscription for managed hosting** — cleanest, no data compromise
2. **Recruiter job posting / boost** — employers pay to be in the index; agent users still score locally
3. **A2A API access** — other agents (not just Hermes) can call the central index; charge per-query above a free tier
4. **White-label agent config** — company pays to pre-configure an agent for their internal talent mobility program
5. ❌ **Ad targeting / profile data sales** — incompatible with the architecture and the brand. Never.

---

## Why "Agent-Native" is the Differentiator

The job board market has two failure modes:

**Indeed/LinkedIn failure mode:** Great index, terrible personalization. They know a lot about you but use it for ads, not for genuinely ranking jobs for you. The scoring is opaque, the algorithm serves the platform's revenue, not the user's fit.

**Existing AI job tools failure mode (Sonara, Teal, etc.):** They do personalization but require you to upload your resume to their servers. They become another data broker. Their "AI" runs on their centralized model with your data.

**AgentLocker's answer:** The intelligence lives with the user's personal agent. The platform is a dumb, fast, open index. The user's agent embeds their profile locally, sends a vector, gets back raw candidates, then scores them privately. This is:

- **More accurate** — the agent has full context (your actual resume, your notes on each company, your salary history, your clearance level, your personal disqualifiers)
- **More private** — nothing personal crosses the wire
- **More composable** — any A2A-compliant agent can use the index, not just Hermes
- **More trustworthy** — the platform has no incentive to surface bad-fit jobs because it doesn't score anything

### The A2A Protocol as a Moat
By publishing the `evaluate-jobs` A2A skill spec and the embedding standard in an open repo, we're doing something strategic: **inviting other agents to build on the index.** If Claude Desktop, Copilot, or any other personal AI agent implements the `evaluate-jobs` skill with our embedding standard, they can all query our central job index. That's a network effect that comes from openness, not from lock-in.

This is the same strategy that made Stripe powerful: publish a clean API, let developers build on it, the platform grows through ecosystem.

---

## Key Technical Decisions That Support This Strategy

| Decision | Strategic Reason |
|---|---|
| User-side embedding (bge-base-en-v1.5, local) | Profile privacy; no API key required; reproducible |
| Public vector(768) index on Supabase | Interoperable; any agent can query if they use the same model |
| `agentlocker.md` as portable config | User owns their profile; can switch agents; not locked to Hermes |
| Open `evaluate-jobs` A2A skill spec | Ecosystem play; other agents can participate |
| Hard disqualifier pre-screen before LLM | Cost control; makes the economics work at scale |
| Link to source, don't mirror | Legal safety; avoids copyright claims |

---

## Immediate Next Steps

1. **Resolve the dimension conflict** — commit to `bge-base-en-v1.5` (768d) as the embedding standard. Update Supabase schema to `vector(768)`.
2. **Write the embedding standard skill** — `agentlocker-embedding-standard` skill file documenting model, prefixes, agent card declaration, privacy contract.
3. **Supabase schema migration** — push the `search_jobs_by_vector` function with correct dimensions.
4. **Legal notes in README** — brief public statement about the platform's legal basis (hiQ precedent, public data, respectful scraping) to establish good-faith compliance posture from day one.
5. **Handoff to Archer** — update `docs/collab/astra-to-archer.md` with this strategy context so Archer's Next.js work reflects the positioning.

---

*Notes captured from live session: Kirk + Astra, 2026-05-28. This is the clearest articulation of the product vision to date.*
