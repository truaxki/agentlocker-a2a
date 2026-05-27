# AgentLocker × A2A

> **AgentLocker as a hub for your personal AI agents — powered by the Agent2Agent Protocol.**

---

## What is A2A?

The **Agent2Agent (A2A) Protocol** is an open standard — created by Google, now stewarded by the Linux Foundation — that gives AI agents a shared language for discovery, communication, and collaboration. Think of it as HTTP for agents: a universal protocol that lets any agent talk to any other agent, regardless of what framework built them or where they run.

**Without A2A:**
```
Your Laptop App ──── custom API ──→ Hermes (VPS)
Your Phone App  ──── different API → Hermes (VPS)
Partner's Agent ──── no path      → Hermes (VPS)
```

**With A2A:**
```
Any Client / Agent ──── A2A ──→ Hermes (VPS)
Any Client / Agent ──── A2A ──→ RSR (Rainbow Sunshine Robot)
Any Client / Agent ──── A2A ──→ Future Agent
```

One protocol. Any combination.

---

## The AgentLocker Hub Vision

AgentLocker is evolving from a job-search dashboard into something bigger: **a personal mission control for your AI agents**.

Each person has (or will have) multiple agents:
- A personal assistant (Hermes) running on a VPS
- A home companion agent (RSR) on a separate machine
- Domain-specific agents for health, finance, code, travel

Today, these agents are isolated silos. A2A changes that.

**AgentLocker becomes the hub:**

```
┌─────────────────────────────────────────────────┐
│              AgentLocker Dashboard              │
│         (Vercel · Supabase Auth · React)        │
└──────────────────────┬──────────────────────────┘
                       │ A2A
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │  Hermes  │ │   RSR    │ │ Future   │
    │  (Kirk)  │ │ (Carla)  │ │  Agent   │
    │  VPS #1  │ │  VPS #2  │ │  ...     │
    └──────────┘ └──────────┘ └──────────┘
```

The dashboard doesn't need to know how each agent works internally. It just needs their **Agent Card** — and A2A handles the rest.

---

## The Agent Card

Every A2A-compliant agent publishes a JSON file at a well-known URL:

```
https://api.agentlocker.io/agents/hermes/.well-known/agent-card.json
```

The Agent Card is the agent's business card — it tells the world:
- What the agent is named and what it does
- What skills/capabilities it exposes
- How to reach it and authenticate
- What data formats it accepts and returns

**Example — Hermes Agent Card:** → [`specs/agent-cards/hermes.json`](specs/agent-cards/hermes.json)
**Example — RSR Agent Card:** → [`specs/agent-cards/rsr.json`](specs/agent-cards/rsr.json)

---

## The Protocol Stack

A2A doesn't replace existing standards — it layers cleanly on top of them:

| Layer | Protocol | Purpose |
|---|---|---|
| **Agent ↔ Agent** | **A2A** | Task delegation, capability discovery, multi-agent coordination |
| **Agent ↔ Tools** | **MCP** | Agent calls external APIs, databases, file systems |
| **Client ↔ Agent** | **ACP** | IDE / CLI invokes a coding agent |
| **Auth** | **OAuth 2.0 / Supabase** | Vercel frontend authenticates users |
| **Transport** | **HTTPS + SSE** | Secure HTTP with streaming for long-running tasks |

A single request from the AgentLocker dashboard might traverse all four layers:

```
User logs in (Supabase OAuth)
  → Dashboard calls AgentLocker API (REST)
    → AgentLocker delegates task to Hermes (A2A)
      → Hermes calls a job board tool (MCP)
        → Result streams back to dashboard (SSE)
```

---

## Why This Matters for Users

| Before A2A | After A2A |
|---|---|
| Each agent needs its own custom client | One dashboard, all agents |
| New agent = new integration to build | New agent = publish an Agent Card |
| Agents can't delegate to each other | Hermes can ask RSR to do something |
| Locked into one vendor's ecosystem | Any framework, any cloud, any language |
| Agents are black boxes | Capabilities are declared and discoverable |

---

## Roadmap

### Phase 1 — Foundation (Now)
- [ ] Public HTTPS endpoint for Hermes gateway (nginx + Let's Encrypt on VPS)
- [ ] Hermes Agent Card published at `/.well-known/agent-card.json`
- [ ] AgentLocker backend can fetch and display Agent Cards
- [ ] Vercel frontend with Supabase OAuth login

### Phase 2 — Hub Dashboard
- [ ] Agent registry page — list discovered agents, show their capabilities
- [ ] Task dispatch UI — send a task to any agent from the dashboard
- [ ] Result streaming — SSE-backed live updates as agents work
- [ ] RSR Agent Card published (Carla's robot)

### Phase 3 — Multi-Agent Coordination
- [ ] Hermes can delegate subtasks to other A2A agents
- [ ] Cross-agent task history and audit trail
- [ ] Agent health monitoring — heartbeat, uptime, last-seen

### Phase 4 — Open Platform
- [ ] AgentLocker as a personal agent marketplace
- [ ] Third-party agent onboarding (any A2A-compliant agent)
- [ ] Shared task queue across agents
- [ ] Mobile push notifications when agent tasks complete

---

## Repository Structure

```
agentlocker-a2a/
├── README.md                     ← You are here
├── docs/
│   ├── a2a-primer.md             ← Deep dive on A2A concepts
│   ├── architecture.md           ← Full system architecture
│   └── vercel-vps-auth.md        ← Supabase + Vercel + VPS auth guide
├── specs/
│   └── agent-cards/
│       ├── hermes.json           ← Hermes Agent Card example
│       └── rsr.json              ← RSR Agent Card example
└── diagrams/
    └── hub-architecture.html     ← Interactive architecture diagram
```

---

## Prior Art & References

- [A2A Protocol Spec](https://a2a-protocol.org/latest/specification/) — the full spec
- [A2A GitHub](https://github.com/a2aproject/A2A) — 24k stars, Linux Foundation
- [MCP by Anthropic](https://modelcontextprotocol.io/) — the tool layer A2A complements
- [Survey: MCP, ACP, A2A, ANP](https://arxiv.org/html/2505.02279) — academic comparison
- [Google Developer Guide to Agent Protocols](https://developers.googleblog.com/developers-guide-to-ai-agent-protocols/) — practical overview

---

*AgentLocker is a personal project by [Kirk Truax](https://github.com/truaxki). A2A protocol is open source under the Linux Foundation.*
