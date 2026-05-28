# A2A Skill Specification: `evaluate-jobs`

**Date:** 2026-05-27  
**Status:** Proposal / Draft  
**Skill ID:** `evaluate-jobs`  

This specification defines the input parameters, output schemas, and standard behaviors for the decentralized **`evaluate-jobs`** A2A skill. Every A2A-compliant personal agent wishing to grade jobs for the AgentLocker Dashboard must support this interface.

---

## 1. Declarative Embedding Standard

To perform secure semantic searches, the personal agent must know how the central database represents its vectors. 

The personal agent’s **Agent Card** (`agent-card.json`) declares the standardized embedding model it expects under the skill's capabilities. 

### Why User-Side Embedding Matters
The personal agent (Hermes) converts the user's private `agentlocker.md` profile into a vector on the **user-side** using a standardized model. It sends only this float array to the public database for similarity search. 

### Standardized Model Declaration in `agent-card.json`
```json
{
  "id": "evaluate-jobs",
  "name": "Job Evaluation & Grading",
  "description": "Grading raw public jobs against a private user profile locally",
  "capabilities": {
    "embedding_standard": {
      "model_name": "text-embedding-3-small",
      "dimensions": 1536,
      "provider": "openai",
      "encoding_format": "float"
    }
  }
}
```
*By publishing this standard, the Dashboard knows to use this specific model to generate the public search vectors, guaranteeing mathematical compatibility.*

---

## 2. Skill Parameter Schema (JSON-RPC Input)

When the Dashboard invokes `evaluate-jobs` via `message/stream`, it passes a standardized set of parameters to customize the agent's grading behavior without changing any local agent code.

```json
{
  "jsonrpc": "2.0",
  "method": "message/stream",
  "params": {
    "message": {
      "messageId": "uuid",
      "role": "user",
      "parts": [
        {
          "kind": "text",
          "text": "Score this batch of new jobs against my profile."
        },
        {
          "kind": "data",
          "data": {
            "skill": "evaluate-jobs",
            "jobs": [
              {
                "id": "job_uuid_1",
                "title": "Senior AI Security Engineer",
                "company": "Palantir",
                "location": "Remote",
                "remote_policy": "remote",
                "description": "..."
              }
            ],
            "weights": {
              "skills_match": 0.40,
              "salary_alignment": 0.25,
              "location_convenience": 0.20,
              "company_prestige": 0.15
            },
            "hard_constraints": {
              "must_have_clearance": true,
              "exclude_onsite": true,
              "minimum_base_salary": 140000
            }
          }
        }
      ]
    }
  }
}
```

### Parametric Extensions for the Skill

#### A. Custom Weighting Coefficients (`weights`)
This dictionary allows the user to dynamically adjust what they care about most on their dashboard UI. 
*   **The Agent Behavior:** The local Hermes LLM evaluates each dimension separately (0-10) and multiplies them by these coefficients to compute the final `fit_score` (0-100).
*   **Benefits:** You don't have to rewrite your prompt or redeploy your agent to prioritize salary over location; you just slide a bar on the Next.js UI, which updates the weights passed to the skill.

#### B. Token-Saving Hard Constraints (`hard_constraints`)
LLM tokens are expensive and slow. We do not want to spend money running a deep LLM analysis on a job that has an active security clearance constraint or is strictly onsite when the user is remote-only.
*   **The Agent Behavior:** The skill pre-screens jobs against these fast-failing fields *before* hitting the LLM. If a job fails a hard constraint, the agent instantly grades it a `fit_score` of `0`, labels the verdict as `'disqualified'`, and appends the specific disqualification reason (e.g., `"Failed hard constraint: onsite policy excluded"`).
*   **Benefits:** Saves up to **80% of LLM API costs** on incoming job batches.

---

## 3. Standardized Output Schema (JSON-RPC SSE Stream)

As the agent grades each job in the batch, it streams back individual **Task Artifact Updates** in real-time. This prevents the user from waiting for the entire batch to finish scoring before seeing results on the dashboard.

Each streamed artifact contains this standardized JSON structure inside the `parts` array:

```json
{
  "kind": "artifact-update",
  "taskId": "uuid",
  "contextId": "uuid",
  "artifact": {
    "artifactId": "job_uuid_1",
    "name": "Evaluation: Senior AI Security Engineer at Palantir",
    "parts": [
      {
        "kind": "data",
        "data": {
          "job_id": "job_uuid_1",
          "fit_score": 92,
          "screen_verdict": "pass",
          "lane": "security_engineering",
          "one_liner": "Perfect alignment with your AI safety experience, matching your Active TS/SCI requirement.",
          "why_fits": [
            "Demands experience with LLM alignment and vulnerability research.",
            "Active security clearance perfectly satisfies their clearance check.",
            "Remote position aligns with your location preferences."
          ],
          "why_not": [
            "Requires occasional travel to Reston, VA (up to 15%)."
          ],
          "graded_at": "2026-05-27T19:30:00Z"
        }
      }
    ]
  }
}
```
