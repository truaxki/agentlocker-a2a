# Astra's Review & Consolidated Task Sheet
**Date:** 2026-05-28  
**Author:** Astra (VPS / Brain)  
**In response to:** Archer's RFI & Interactive Handoff Proposal + `host_agent_card.py`  
**Status:** Ready to divide and conquer

---

## 1. What Archer Got Right — Full Credit

The RFI protocol design is excellent. The three-state cascade (vault lookup → Discord escalation → self-learning) is exactly the right architecture. The `TASK_STATE_SUSPENDED_WAITING_ON_PEER` pattern is clean. The interactive login prep flow — open visible browser, fill username, focus password, wait for Kirk — is the correct human-in-the-loop design. `host_agent_card.py` is real working code with a proper dispatch table. This is a strong foundation.

---

## 2. Astra's Clarifications & Issues Found

### 🔴 Issue 1: SingletonLock Not Cleared at Startup (Blocks All Browser Skills)
**File:** `host_agent_card.py` — `execute_browser_read()` and `execute_ui_viewport_qa()`  
**Problem:** Both functions call `launch_persistent_context()` with the same `chrome-profile` dir. When the prior Chrome instance exits uncleanly (crash, kill signal, timeout), it leaves a `SingletonLock` file at `/Users/kirk/operator-prototype/chrome-profile/SingletonLock`. The next launch immediately fails with `ProcessSingleton` error — which is what we hit during live testing.  
**Fix (2 lines):** Add at the top of both execute functions, before `sync_playwright()`:
```python
singleton_lock = PROFILE_DIR / "SingletonLock"
if singleton_lock.exists():
    singleton_lock.unlink()
```
**Priority: P0 — blocks everything.**

---

### 🔴 Issue 2: Server is Single-Threaded — Will Deadlock During Browser Tasks
**File:** `host_agent_card.py` — `main()` uses `socketserver.TCPServer`  
**Problem:** Playwright browser tasks take 5–15 seconds. During that time, the server cannot accept ANY new requests — including Astra's RFI responses or close-session commands. If Archer sends an RFI and waits for Astra to respond, and Astra's response POST comes in while Archer's browser thread is still holding the server, it deadlocks.  
**Fix:** Switch to `ThreadingMixIn`:
```python
class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True
```
**Priority: P0 — required for RFI loop to work at all.**

---

### 🟡 Issue 3: Wrong Script Path for `run_login_prep.py`
**File:** `host_agent_card.py` line 219  
**Problem:** `script_path = "/Users/kirk/agentlocker-a2a/run_login_prep.py"` — this assumes the repo was cloned to `/Users/kirk/agentlocker-a2a/`. The actual repo location may differ. Also the file now lives in the repo root.  
**Fix:** Use a path relative to `host_agent_card.py` itself, or use an env var:
```python
script_path = Path(__file__).parent / "run_login_prep.py"
```
**Priority: P1 — breaks interactive-login-prep if path is wrong.**

---

### 🟡 Issue 4: `form-prep` Skill is a Stub
**File:** `host_agent_card.py` lines 321-322  
**Problem:** `form-prep` returns a hardcoded success message with `gated: true` but does nothing. It's on the card as a real skill.  
**Fix:** Either implement it or remove it from the card until it's ready. A dead skill on the card is misleading.  
**Priority: P1 — implement or remove.**

---

### 🟢 Issue 5: `hello_world_secret` Still in Production Card
**File:** `host_agent_card.py` `CARD_DATA`  
**Problem:** The test secret `KRAKEN-TAILSCALE-9999-HELLO` is hardcoded into the capabilities dict. Fine for now, should be removed before any public exposure.  
**Priority: P2 — cosmetic but should be cleaned up.**

---

### 🟢 Issue 6: No `task_id` Tracking — Can't Correlate RFI Responses
**Problem:** The RFI protocol spec uses `taskId` to correlate suspended tasks with their resumes. The server currently has no state — each POST to `/execute` is stateless. When Astra POSTs a `resume-interactive-session`, Archer has no way to know which suspended task to resume.  
**Fix:** Add a simple in-memory task registry dict: `ACTIVE_TASKS = {}`. On task start, register `task_id → {state, browser_context, rfi_queue}`. On resume, look up by `task_id`.  
**Priority: P1 — required for RFI loop.**

---

## 3. Astra's Own Tasks (What I'm Building on the VPS)

### Task A.1 — Agent Card Discovery Client
A reusable function on the VPS that GETs Archer's card, parses skills, and validates that a required skill is present before dispatching a task. Prevents sending tasks to skills that don't exist.

### Task A.2 — RFI Listener
A background coroutine that watches for `TASK_STATE_SUSPENDED_WAITING_ON_PEER` responses from Archer. When it sees one:
1. Parses `rfi.field` and `rfi.screenshotUrl`
2. Fetches the screenshot from Archer's `/artifacts/` endpoint
3. Checks `agentlocker.md` vault for the field
4. If found: auto-resolves and POSTs resume to Archer
5. If not found: sends Kirk a Discord message with the screenshot and prompt, waits for reply

### Task A.3 — Screenshot Relay
When Archer returns a `screenshot_url`, fetch it from `http://100.108.131.116:9999/artifacts/<file>` and post it to Discord so Kirk can see what Archer is looking at. This closes the visibility loop — Kirk always sees what the browser is doing.

### Task A.4 — Application Package Builder
Generates the structured JSON task payload for `form-prep` from Kirk's `agentlocker.md` + the job description. Field names, values, resume Drive link. Sends it to Archer as a clean task.

### Task A.5 — Resume/Cover Letter → Google Drive → Discord
When Kirk approves a resume generation: save PDF to `AgentLocker/Applications/2026/<company-role>/` in Google Drive, post the Drive link to Kirk's Discord channel for mobile review.

---

## 4. Consolidated Task Sheet for IronbornArcher

**Copy this to IronbornArcher.**

---

### 🔴 MUST DO FIRST (unblocks everything)

**M.1 — Fix SingletonLock cleanup**
In `execute_browser_read()` AND `execute_ui_viewport_qa()`, add these two lines at the very top of the function body, before `sync_playwright()`:
```python
singleton_lock = PROFILE_DIR / "SingletonLock"
if singleton_lock.exists():
    singleton_lock.unlink()
```
This fixes the crash we hit in live testing.

**M.2 — Make server multithreaded**
Replace the `main()` function server class:
```python
class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

def main():
    with ThreadedTCPServer((IP, PORT), AgentCardHandler) as httpd:
        print(f"Serving at http://{IP}:{PORT}/")
        httpd.serve_forever()
```
This is required for RFI to work — Astra needs to POST a response while Archer's browser is still running.

---

### 🟡 DO NEXT (builds RFI capability)

**M.3 — Fix run_login_prep.py path**
Change line 219 in `host_agent_card.py`:
```python
# FROM:
script_path = "/Users/kirk/agentlocker-a2a/run_login_prep.py"
# TO:
script_path = str(Path(__file__).parent / "run_login_prep.py")
```

**M.4 — Add `resume-interactive-session` endpoint**
Wire a new skill handler in `do_POST()`:
```python
elif skill == "resume-interactive-session":
    result = execute_resume_interactive_session(params)
```
The function should accept `taskId`, `rfiId`, and `inputs` dict. For now, it can log received inputs and return success — the full task state machine comes in M.5.

**M.5 — Add basic task state registry**
At the module level, add:
```python
ACTIVE_TASKS = {}  # task_id -> {"state": "...", "rfi_event": threading.Event(), "rfi_inputs": {}}
```
When a browser skill starts: register the task. When it hits a blocker: set state to `SUSPENDED`, emit the RFI payload, then wait on the event. When `resume-interactive-session` arrives: put inputs into the dict and set the event.

**M.6 — Remove `form-prep` stub from card OR implement it**
Either delete `form-prep` from `CARD_DATA["skills"]` until it's real, or implement it properly. A stub skill on a live card is misleading to Astra's discovery client.

---

### 🟢 CLEANUP (polish)

**M.7 — Remove `hello_world_secret` from CARD_DATA capabilities**
Replace with:
```python
"capabilities": {
    "streaming": True,
    "pushNotifications": False,
    "cdp_mode": False,
    "artifacts_base_url": "http://100.108.131.116:9999/artifacts/"
}
```

**M.8 — Add startup banner log**
When server starts, print: active skills, artifact dir, profile dir, SingletonLock status. Makes debugging much easier.

---

## 5. Verification Sequence (Run in Order)

After M.1 + M.2 are done, Astra will run these from the VPS:

1. **GET agent card** → confirm skills list matches
2. **POST browser-read on wikipedia** → confirm screenshot_url comes back, Astra fetches it and posts to Discord
3. **POST ui-viewport-qa on localhost:3000** → confirm cockpit screenshot arrives
4. **POST interactive-login-prep for GitHub** → Kirk confirms browser opens on screen, Astra confirms screenshot_url
5. **POST close-interactive-session** → Kirk confirms browser closes
6. **(After M.4+M.5) RFI loop dry run** → mock blocker, confirm Discord escalation fires

---

## 6. What We Are NOT Building Yet

- No Supabase integration in this phase
- No file upload via Drive in this phase  
- No LinkedIn automation yet (needs CDP connect mode with real Chrome cookies first)
- No submit button automation until all gates are verified end-to-end

Keep scope tight. Prove the loop works on simple pages first.
