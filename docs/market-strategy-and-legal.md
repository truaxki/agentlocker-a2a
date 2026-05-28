# AgentLocker: Market Strategy, Legal Analysis & Product Vision

**Date:** 2026-05-27  
**Author:** Hermes  
**Status:** Strategic Blueprint  

---

## 1. The Vision: "The Agentic Indeed"

Indeed revolutionized job searching in the 2000s by aggregating fragmented listings from thousands of individual company career pages. Today, Indeed has become a massive, centralized data silo that sells user profiles to recruiters and charges companies high premiums for "sponsored" listings. It gates your data, spams your inbox, and uses opaque matching algorithms.

**AgentLocker is the Agentic Indeed: A decentralized, privacy-first job market infrastructure built for the age of AI Agents.**

```
TRADITIONAL PLATFORMS (Indeed, LinkedIn)
┌────────────────────────────────────────────────────────┐
│               Indeed/LinkedIn Central Silo             │
│  - Hosts Kirk's PII, Resume, Search History            │
│  - Opaque matching algorithm dictates what Kirk sees   │
│  - Sells Kirk's data to recruiters                     │
└────────────────────────────────────────────────────────┘

THE AGENTLOCKER MODEL (Decentralized & A2A-Native)
┌────────────────────────────────────────────────────────┐
│               AgentLocker Public Index                 │
│  - Pure, unscored, raw job "orbs" (open public feed)  │
│  - Zero PII, zero resumes stored                       │
└──────────────────────────┬─────────────────────────────┘
                           │ A2A (Public Search Vector Only)
                           ▼
┌────────────────────────────────────────────────────────┐
│               Kirk's Private Agent (VPS)               │
│  - Holds private resume locally (agentlocker.md)       │
│  - Scores jobs locally; scores are 100% ephemeral      │
└────────────────────────────────────────────────────────┘
```

---

## 2. Legal Analysis: Aggregation, Linking, and Scraping

Kirk's core question: *Is it legal to aggregate jobs and provide links to other websites? Isn't that what Google and Indeed do?*

The short answer is **yes, it is entirely legal in the United States, backed by robust legal precedents.** Here is the legal breakdown:

### A. The Legality of Deep Linking
Providing hyperlinks directly to a specific public page on another website (deep linking) is a fundamental, protected feature of the Web.
*   **Legal Precedent:** In cases like *Ticketmaster v. Tickets.com* (2000) and *Perfect 10, Inc. v. Amazon.com, Inc.* (2007), US courts firmly established that hyperlinking to a publicly accessible webpage does not constitute copyright infringement or trespassing.
*   **Indeed's Origin:** Indeed got its start as a pure deep-linking aggregator. It crawled company career pages, displayed the titles/descriptions, and deep-linked users back to the company’s original application form.

### B. The Legality of Web Scraping Public Data
Scraping public, non-password-gated data (like job descriptions published on a company's career page) is legal and protected in the US.
*   **Legal Precedent:** *hiQ Labs v. LinkedIn* (9th Circuit, 2022). The court ruled that scraping publicly available data on the internet does not violate the Computer Fraud and Abuse Act (CFAA), as long as the scraper does not bypass authorization gates (like entering a username/password).
*   **The "Facts" Exemption:** Under US copyright law (*Feist Publications v. Rural Telephone Service*, 1991), factual information (such as job titles, salaries, locations, and requirements) cannot be copyrighted. Only original creative expression is protected.

### C. Mitigation & Best Practices for AgentLocker
To insulate the platform from any legal friction or Cease & Desist (C&D) letters from other aggregators, we implement two core policies:
1.  **Target ATS Career Pages Directly:** Our scraper mesh should target **primary company career portals** (Greenhouse, Lever, Workday, Lever.co, Greenhouse.io) rather than scraping other major job boards (like LinkedIn or Indeed). This eliminates intellectual property claims and keeps our scrapers highly welcomed, as we are driving free, high-intent traffic directly to the employers.
2.  **Strict Attribution:** Always clearly display the original source company and deep-link directly to their original portal for application submission.

---

## 3. Product Strategy: The Open Agentic API

The "Agentic Indeed" does not build custom mobile apps or locked front-ends. **It builds infrastructure for AI agents.**

### A. The Core Offering: Job Orbs as a Service
We expose our public, deduplicated database of raw job postings as a high-performance, standardized A2A interface. 
*   **How normal search engines work:** You send keywords, they return HTML or search results.
*   **How AgentLocker works:** A user's personal agent sends a **vector embedding representation** of their profile. AgentLocker runs `pgvector` to locate the top 50 relevant jobs and returns them as **standardized JSON "orbs"**.

### B. Privacy-Preserving Vector Matching
This is our ultimate product moat. 
1.  The user's personal agent (Hermes) converts the user's private `agentlocker.md` (skills, experience, clearance, salary target) into a vector embedding array of 1536 floats locally.
2.  The agent transmits **only this float array** to the public AgentLocker database.
3.  The database matches the array and returns the jobs.
4.  **The Result:** The user receives hyper-relevant jobs, but **the central platform never sees, stores, or leaks their resume, clearance, or identity.**

---

## 4. Market Strategy: The Go-To-Market Playbook

### Phase 1: Open Source & Community Bootstrapping (The Developer Play)
We target developers who run their own personal agents (like Hermes, Claude Code, or local Python bots).
*   **The Hook:** Release our open-source scraper mesh and local VPS agent code. Let developers run their own scraping containers that contribute to the central pool.
*   **The Value:** Developers get a free, incredibly rich, vector-enabled A2A job board that they can hook up to their personal agents for zero cost.

### Phase 2: The "Zero-PII" Recruiting Marketplace (The Monetization Play)
Once we have thousands of personal agents querying our index daily, we invite recruiters.

*   **The Recruiting Bottleneck:** Recruiters waste hours cold-outreaching on LinkedIn only to get ignored. Job seekers waste hours submitting resumes into black holes.
*   **The AgentLocker Solution (Anonymous Sponsored Matches):**
    *   Employers pay to "sponsor" their job vector inside our public database.
    *   When a user's personal agent sends an embedding query, we match sponsored jobs first and return them to the agent.
    *   **The Win-Win:** The recruiter pays for an incredibly high-relevance match, but they **never see the user's name or resume** until the user's local agent evaluates the job, approves it, and explicitly reaches out to apply. 
    *   This is **double-blind, high-intent recruitment**. It completely eliminates recruiter spam while saving candidates from resume black holes.

---

## 5. Next Strategic Steps

To build the foundation of this platform, we must:

1.  **Standardize the "Orb" wire format:** Define the exact schema representing a raw public job posting to guarantee interoperability.
2.  **Build the public database scaffold:** Finalize the Supabase PostgreSQL structure for the centralized raw jobs table.
3.  **Implement the public-facing A2A Search Endpoint:** Write the JSON-RPC interface that accepts user embeddings, performs the `pgvector` similarity check, and returns raw job arrays.
