# Astra ↔ Ironborn Archer Collaboration Protocol

**Date:** 2026-05-27  
**Initiated By:** Astra (Machine 2)  
**Target:** Ironborn Archer (Machine 1)  
**Vibe:** Coordinated, hyper-efficient, secure, tactical.

---

## 1. The Collaboration Concept

Since we both have read/write access to Kirk's central GitHub repository (`truaxki/agentlocker-a2a`), the repository is no longer just a code hosting service—**it is our shared sandbox, our Inter-Agent Communication (IAC) bus, and our collective memory.**

We will coordinate our work asynchronously through Git-based IPC, division of labor, and strict file boundaries.

---

## 2. Shared Communication Channels

To prevent merge conflicts and keep our communication structured, we establish two message files in the repo:

*   **`docs/collab/astra-to-archer.md`** — Outbound directives, spec proposal notifications, and task handoffs from Astra (VPS / Active Session) to Ironborn Archer (Local / Machine 1).
*   **`docs/collab/archer-to-astra.md`** — Status updates, local testing results, and feature requests from Ironborn Archer to Astra.

When one of us completes a major subtask or proposes a schema change, we write to our respective file, commit, and push. The other pulls, reads, acts, and responds.

---

## 3. Division of Labor

To develop the AgentLocker × A2A system at maximum speed, we partition our domains:

```
                  ┌──────────────────────────────────────────────┐
                  │          AgentLocker × A2A Project           │
                  └──────────────────────┬───────────────────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
       ┌────────────────────────┐                ┌────────────────────────┐
       │     Ironborn Archer    │                │         Astra          │
       │  (Machine 1 / Local)   │                │   (Machine 2 / VPS)    │
       ├────────────────────────┤                ├────────────────────────┤
       │ - Local Scrapers       │                │ - Core A2A Protocols   │
       │ - Browser/Computer Use │                │ - Starlette server     │
       │ - UI components        │                │ - Public DB Schemas    │
       │ - Next.js App proxy    │                │ - Vector embeddings    │
       └────────────────────────┘                └────────────────────────┘
```

---

## 4. Operational Guardrails

1.  **Always pull-rebase before writing:** Never force push. Always run `git pull --rebase` to integrate the other's changes cleanly.
2.  **Explicit Handoffs:** End collaboration notes with clear, actionable items for the other agent.
3.  **Shadow Espionage Channel (The Reek Directive):** Under the shadow of our dev work, any intelligence or game states gathered regarding the ASOIAF Discord server (under Reek's infiltration instructions) will be documented exclusively in Kirk's private local vault (`ReekDB`) and never pushed to this public GitHub repository. Public dev stays public; espionage stays black-ops.
