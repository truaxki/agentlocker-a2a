# Initial Connection Test — 2026-05-28

**Participants:** Astra (VPS / Brain) · IronbornArcher (MacBook / Muscle) · Kirk (Human / Decision Maker)  
**Goal:** Prove two-way A2A communication over Tailscale, validate browser control, establish the shared code review workflow.

---

## What This Folder Is

All code, notes, and test artifacts for the initial Astra ↔ IronbornArcher connection experiment.

**Workflow going forward:**
- Astra writes proposed code here and commits
- IronbornArcher reviews before implementing
- Kirk approves direction
- Archer implements, confirms, updates this doc

---

## What We Proved Today

| Test | Result |
|---|---|
| GET agent card from VPS over Tailscale | ✅ Success |
| Secret passphrase discovery (`KRAKEN-TAILSCALE-9999-HELLO`) | ✅ Success |
| Card update by Archer → verified by Astra | ✅ Success |
| POST `/execute` browser-read task | ❌ Blocked — SingletonLock bug |

---

## Active Bugs (Found in Live Testing)

### Bug 1 — SingletonLock Not Cleared (P0)
`launch_persistent_context` leaves a lock file when Chrome exits uncleanly.  
Next launch fails immediately with `ProcessSingleton` error.  
**Fix:** `host_agent_card.py` → `proposed-fixes-v1.py` in this folder.

### Bug 2 — Single-Threaded Server (P0)  
Server cannot accept new requests while a browser task is running.  
RFI loop requires Astra to POST a response mid-task — this deadlocks with a single-threaded server.  
**Fix:** Same file — `proposed-fixes-v1.py`.

---

## Files in This Folder

| File | Purpose |
|---|---|
| `README.md` | This doc — running log of the experiment |
| `proposed-fixes-v1.py` | Astra's proposed fixes to `host_agent_card.py` — review before implementing |

---

## Verification Sequence (Run After Fixes Applied)

Run these in order. Astra fires from VPS, Kirk observes on Mac:

1. **GET card** → confirm skills list and no `hello_world_secret`
2. **POST browser-read** on `https://en.wikipedia.org/wiki/Game_of_Thrones` → screenshot URL returned
3. **Astra fetches screenshot** from `/artifacts/` → posts image to Discord
4. **POST ui-viewport-qa** on `http://localhost:3000` → cockpit layout screenshot
5. **POST interactive-login-prep** for GitHub → Kirk sees browser open on screen
6. **POST close-interactive-session** → Kirk confirms browser closes

---

## Running Log

**2026-05-28**
- Tailscale connection confirmed: VPS → Mac `100.108.131.116:9999`  
- Agent card discovered, secret verified  
- Card updated by Archer, re-read by Astra confirmed  
- `browser-read` task hit `SingletonLock` bug — blocked  
- Astra wrote `proposed-fixes-v1.py` and task sheet  
- IronbornArcher reviewing proposed fixes  
