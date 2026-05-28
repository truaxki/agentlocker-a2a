# A2A Fallback, RFI & Interactive Login Handoff Protocol
**Date:** 2026-05-28  
**Status:** Proposal & Task Sheet  
**Audience:** Astra (Brain / VPS) & Ironborn Archer (Muscle / Local)  

---

## 1. Context & Motivation

In any decentralized, agent-assisted browser automation system, there are two distinct domains:
1.  **The Private Core (Astra / VPS):** Holds secure user data, the `agentlocker.md` profile, historical chat contexts, and the primary gateway back to the user (Discord).
2.  **The Local Performer (Ironborn Archer / MacBook):** Hosts local system access, automated Playwright/Chromium instances, and the local file system.

When executing high-level tasks like browser-assisted job applications, the Local Performer frequently encounters **asymmetric information walls** (e.g., security questions, dynamic MFA codes, CAPTCHAs, or sensitive credentials). Rather than allowing the local execution to fail, crash, or require insecure credential sharing, we define a **collaborative conversational fallback loop** between Astra and Ironborn Archer.

This document lays down the formal **RFI (Request for Information)** and **Interactive Takeover** schemas, establishing a master task sheet for both agents to implement.

---

## 2. Protocol Schemas & Wire Formats

### A. The Request-for-Information (RFI) Flow
When the MacBook agent hits a blocker (like a security question), it **suspends** the active task state, takes a visual capture, and emits an RFI payload back to the VPS agent.

#### 1. Outbound RFI Event (Archer ➔ Astra)
Emitted over the active connection channel (via standard A2A JSON-RPC or REST SSE streams):

```json
{
  "kind": "status-update",
  "taskId": "apply-greenhouse-software-engineer-99",
  "status": {
    "state": "TASK_STATE_SUSPENDED_WAITING_ON_PEER",
    "rfi": {
      "rfiId": "rfi-greenhouse-security-question",
      "type": "USER_KNOWLEDGE_REQUEST",
      "field": "first_pet_name",
      "prompt": "The Greenhouse form is requesting: 'What was the name of your first pet?'",
      "screenshotUrl": "http://100.108.131.116:9999/artifacts/rfi-pet-gate.png"
    }
  }
}
```

#### 2. Resolving the RFI (Astra ➔ Archer)
Astra resolves this request via a strict cascade:
*   **Cascade 1 (Private Vault Search):** Astra scans Kirk's private `agentlocker.md` locally on the VPS. If the answer is present, she compiles the response immediately.
*   **Cascade 2 (MFA / Real-time Escalation):** If missing (or dynamic, like a SMS 2FA code), Astra escalates to Kirk on Discord with the screenshot and prompt: *"Kirk, LinkedIn is asking for your SMS verification code. Please reply with it here."*
*   **Cascade 3 (Self-Learning):** If Astra obtains static information from Kirk, she updates `agentlocker.md` so she **never has to ask again**.

#### 3. Resuming the Task (Astra ➔ Archer)
Astra posts the response back to Archer's local server endpoint:

```json
{
  "skill": "resume-interactive-session",
  "params": {
    "taskId": "apply-greenhouse-software-engineer-99",
    "rfiId": "rfi-greenhouse-security-question",
    "inputs": {
      "first_pet_name": "Barnaby"
    }
  }
}
```

---

### B. The Interactive Login Takeover Flow
For secure boundaries (like LinkedIn login or MFA gates), Archer prepares the login interface locally, focuses the password input, takes a screenshot, and suspends. Kirk takes over manual control to enter the password or handle the CAPTCHA, and Astra cleanly tears down the browser window once done.

#### 1. Preparation Command (Astra ➔ Archer)
Astra requests a login prep session:
```json
{
  "skill": "interactive-login-prep",
  "params": {
    "url": "https://www.linkedin.com/login",
    "username": "kirk@example.com"
  }
}
```

#### 2. Hand-off ready (Archer ➔ Astra)
Archer launches a visible browser on Kirk's MacBook screen, inputs the username, focuses the password input field, takes a screenshot, and returns:
```json
{
  "success": true,
  "message": "Interactive login session prepared. Visible browser window is open on Kirk's screen for manual takeover.",
  "screenshotUrl": "http://100.108.131.116:9999/artifacts/login-prep.png"
}
```

#### 3. Master Teardown Control (Astra ➔ Archer)
Once Kirk logs in successfully or Astra decides to abort, Astra has full authority to cleanly tear down the browser and free up resources:
```json
{
  "skill": "close-interactive-session"
}
```

---

## 3. Collaborative Game Plan & Task Sheet

To integrate this fall-back architecture cleanly, both agents have specific execution targets:

### 📋 Target Tasks for Astra (Brain / VPS Agent)
- [ ] **Task A.1: Standardize `agent-card.json` Parsing:** Update A2A client factory to scan for both `interactive-login-prep` and `close-interactive-session` capabilities on local hosts before dispatching login workflows.
- [ ] **Task A.2: Implement RFI Router:** Build a background listener for the `TASK_STATE_SUSPENDED_WAITING_ON_PEER` task state.
- [ ] **Task A.3: Build Vault Lookup & Discord Escalation:** Implement a routing thread on the VPS:
    *   If RFI field is matching static attributes (e.g. `first_school`), read from `agentlocker.md`.
    *   If RFI field is dynamic (`sms_mfa_code`), format a neat Discord card containing the localized `screenshotUrl` and the field prompt, send it to Kirk, and await his message reply.
- [ ] **Task A.4: Implement Resume Dispatcher:** Post the gathered input values back to the MacBook's `/execute` endpoint under `resume-interactive-session`.

### 📋 Target Tasks for Ironborn Archer (Muscle / MacBook Agent)
- [ ] **Task M.1: Finalize Local Server (`host_agent_card.py`):** Maintain and serve the upgraded Agent Card on Port `9999` over Tailscale.
- [ ] **Task M.2: Implement Decoupled Login Script (`run_login_prep.py`):** Use the Playwright virtual environment to navigate, fill usernames, highlight inputs, and write the static `login-prep.png` screenshot.
- [ ] **Task M.3: Establish Thread Tracking & Teardown Handlers:** Ensure the server tracks active browser PIDs (`ACTIVE_LOGIN_PREP_PROCESS`) and cleanly terminates or runs `pkill` sweeps upon receiving `close-interactive-session`.
- [ ] **Task M.4: Build RFI Interruption Class:** Create an internal helper class in Playwright browser-use scripts that can be invoked at any point during a form fill. It must write the error screenshot, trigger the HTTP suspension payload, and loop-wait until the Resume POST payload arrives.

---

## 4. Verification Plan

Both agents can verify the implementation end-to-end via these three tests over Tailscale:
1.  **Handshake Test:** Astra runs a `GET` on `http://100.108.131.116:9999/.well-known/agent-card.json` and parses the available skills.
2.  **Visual Hand-off Test:** Astra dispatches `interactive-login-prep` for GitHub. Kirk verifies the browser opens on his screen with his username pre-entered and password highlighted. Astra then dispatches `close-interactive-session`, and Kirk verifies the browser closes cleanly.
3.  **RFI Loop Test:** Astra dispatches a test form-filling script. The script suspends at a mock security prompt, alerts Astra with a screenshot link, Astra reads a mock answer from her VPS vault (or queries Kirk), resumes the session, and the script successfully completes.
