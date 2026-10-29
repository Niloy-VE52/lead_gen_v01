# Architectural Specification: Apify Smart Key Manager & Dual-Mode System

**Document Version:** 1.1 (Updated with Simplified Numbered Key Pool)  
**Project:** Lead Generation & Outreach Engine (`lead_gen_v01`)  
**Scope:** Resilient Apify API Key Management, Pre-Flight Headroom Checks, Zero-Downtime Mid-Run Failover, Simplified Numbered `.env` Schema, and Test vs. Live UI Switching.

---

## 1. Executive Summary & Objective

In this project, the pipeline interacts with **5 distinct Apify actors**:
1. `zn01OAlzP853oqn4Z` — LinkedIn Jobs Scraper (1 run per pipeline)
2. `JkfTWxtpgfvcRQn3p` — LinkedIn Job Repeatability (up to $N$ runs, 1 per unique company)
3. `getdataforme~glassdoor-reviews-scraper` — Glassdoor Reviews (up to $N$ runs, 1 per company)
4. `Vb6LZkh4EqRlR0Ka9` — Decision Maker Finder (up to $K$ runs, 1 per qualified "KEEP" company)
5. `bfH8Ermocz8oYKQVO` — Profile Email Extractor (up to $M$ runs, 1 per decision maker contact; up to 25+ runs)

### The Core Challenges & Solution
* **Simplicity in Configuration:** Instead of forcing the user to guess and assign specific roles in `.env` (like `APIFY_KEY_SCRAPING`), keys are simply declared as `APIFY_KEY_1`, `APIFY_KEY_2`, `APIFY_KEY_3`, etc.
* **Unified Dynamic Pool:** The Key Manager automatically detects all configured `APIFY_KEY_*` variables, checks each account's real-time credit balance via the Apify API, and allocates healthy keys dynamically.
* **Mid-Run Zero-Downtime Failover:** If any key exhausts its quota mid-loop (HTTP 402), the manager flags that key and hot-swaps to the next healthy numbered key in the pool, retrying the call immediately without restarting.
* **Dual Operation Mode:** Easily switch between **Test Mode** (distributed across the numbered free key pool) and **Live Mode** (routing all 5 actors to a single premium subscription key) directly from the UI.

---

## 2. System Architecture

```
                                    ┌────────────────────────────────┐
                                    │    Frontend Config / UI        │
                                    │  [Apify Mode: Test | Premium]  │
                                    └───────────────┬────────────────┘
                                                    │
                                                    ▼
                                    ┌────────────────────────────────┐
                                    │   FastAPI backend/main.py      │
                                    │   Pre-Flight Balance Check     │
                                    └───────────────┬────────────────┘
                                                    │
                                  ┌─────────────────┴─────────────────┐
                                  │                                   │
                           [APIFY_MODE=live]                  [APIFY_MODE=test]
                                  │                                   │
                                  ▼                                   ▼
                      ┌──────────────────────┐            ┌──────────────────────┐
                      │ Single Premium Key   │            │ Unified Dynamic Pool │
                      │ (APIFY_PREMIUM_KEY)  │            │ APIFY_KEY_1 (Acc 1)  │
                      │ Used for all 5       │            │ APIFY_KEY_2 (Acc 2)  │
                      │ actors               │            │ APIFY_KEY_3 (Acc 3)  │
                      └──────────────────────┘            │ APIFY_KEY_4 (Acc 4)  │
                                                          │ APIFY_KEY_5 (Acc 5)  │
                                                          └──────────┬───────────┘
                                                                     │
                                                      ┌──────────────┴──────────────┐
                                                      │ Mid-Run Execution Wrapper   │
                                                      │  - Catches 402/429 limits   │
                                                      │  - Hot-swaps to next key    │
                                                      │  - Retries call in-flight   │
                                                      └─────────────────────────────┘
```

---

## 3. Simplified Environment Variable Schema (`.env`)

No complex role-based naming required. You simply list your available accounts sequentially:

```ini
# ==============================================================================
# APIFY KEY CONFIGURATION
# ==============================================================================
# Master Mode Toggle: "test" (uses free key pool) or "live" (uses single premium key)
APIFY_MODE=test

# ── Live Production Key (Used for all 5 actors when APIFY_MODE=live) ──────────
APIFY_PREMIUM_KEY=apify_api_live_premium_token_here

# ── Test Mode Free Key Pool (Used when APIFY_MODE=test) ────────────────────────
# Add as many accounts as you have. The manager automatically auto-discovers all APIFY_KEY_*
APIFY_KEY_1=apify_api_token_account_1
APIFY_KEY_2=apify_api_token_account_2
APIFY_KEY_3=apify_api_token_account_3
APIFY_KEY_4=apify_api_token_account_4
APIFY_KEY_5=apify_api_token_account_5
```

---

## 4. Component 1: Central Key Manager (`backend/apify_manager.py`)

A single helper module that handles key auto-discovery, balance inspection, and failover retries.

### A. Auto-Discovery & Health Inspection
* **Auto-Discovery:** At initialization, scans environment variables for all matching `APIFY_KEY_1`, `APIFY_KEY_2`, ..., `APIFY_KEY_N`.
* **Pre-Flight Balance Check:** Calls Apify's `/v2/users/me` endpoint (`client.user().get()`) for each key to calculate:
  $$\text{Remaining Headroom} = \text{monthlyUsageLimitUsd} - \text{monthlyUsageUsd}$$
* **State Categorization:**
  * Keys with sufficient headroom ($>\$0.15$) are tagged `HEALTHY`.
  * Keys with low credit ($<\$0.15$) or $0 balance are tagged `EXHAUSTED` and moved to the back of the queue.
* **Early Guard:** If **zero** keys have usable credit, the backend halts immediately with an HTTP 400 error before running scrapers:
  `"Pipeline Aborted: All Apify test keys (APIFY_KEY_1 to N) are exhausted. Please add a fresh key."`

### B. In-Flight Failover Wrapper (`call_actor_with_failover`)
Wraps every Apify actor call across the codebase:
1. Calls the actor using the currently active healthy key from the pool.
2. If Apify throws `ApifyApiError` with status `402` (Payment/Usage limit reached) or `429` (Rate limit):
   * Logs a clean alert: `⚠️ Account APIFY_KEY_2 reached limit! Auto-switching to APIFY_KEY_3...`
   * Flags that token as `EXHAUSTED`.
   * Automatically switches the client instance to the next available healthy key.
   * **Immediately retries the exact same call in-flight.**
3. The outer loops (processing companies or extracting emails) are never broken.

---

## 5. Component 2: Dual Mode & UI Toggle Integration

### A. Backend Data Model (`backend/main.py`)
Update `ScrapeInput`:
```python
class ScrapeInput(BaseModel):
    ...
    outreach_mode: str = "test"        # "test" (safe redirect) or "live" (real prospects)
    test_email_recipient: Optional[str] = "niloyvetesting54@gmail.com"
    apify_mode: str = "test"           # "test" (free key pool) or "live" (single premium key)
```

### B. Frontend UI Toggle (`frontend/src/components/ConfigPanel.jsx`)
Add an Apify Key Mode selector alongside the existing Outreach Mode selector:
* **Option 1: 🧪 Free Test Pool** — Distributes load across `APIFY_KEY_1`, `APIFY_KEY_2`, etc., with auto-failover.
* **Option 2: 👑 Premium Live Key** — Routes all 5 actors directly to `APIFY_PREMIUM_KEY`.
* Set default in `frontend/src/constants/defaults.js`: `apify_mode: "test"`.

---

## 6. Zero-Downtime Resume Architecture

1. **Micro-Level (In-Flight):**
   When an individual email lookup fails at person #4, the exception is caught *inside* the email extraction function. The key is swapped and retried in $<1.5$ seconds. The parent loop never breaks.
2. **Macro-Level (Persistent State Checkpointing):**
   * Jobs are deduplicated against Google Sheets (`Scraped_Jobs_V05`).
   * Company emails are deduplicated against Google Sheets (`Email_saver`).
   * If the server process is forcefully terminated, re-running the pipeline checks Google Sheets and automatically skips all already-completed companies.

---

## 7. Step-by-Step Implementation Roadmap

| Step | Target File | Action |
|---|---|---|
| **1** | `backend/apify_manager.py` | Create the token manager that auto-detects `APIFY_KEY_1`...`N`, checks balances, and handles failover retries. |
| **2** | `backend/scraper.py` | Update `scrape_linkedin_jobs` and `check_repeatability` to use `apify_manager.call_actor(...)`. |
| **3** | `backend/review_finder.py` | Update `get_reviews` to obtain its token/call via `apify_manager`. |
| **4** | `backend/emailFinder.py` | Update `get_decisionmakers_linkedin` and `get_email_from_linkedin_profile` to use `apify_manager.call_actor(...)`. |
| **5** | `backend/main.py` | Add pre-flight balance validation before launching background jobs; accept `apify_mode` in request payloads. |
| **6** | `frontend/src/constants/defaults.js` | Add `apify_mode: "test"` to default configuration. |
| **7** | `frontend/src/components/ConfigPanel.jsx` | Add Apify Key Mode toggle switch matching the UI style of Outreach Mode. |
| **8** | `.env` | Configure `APIFY_MODE`, `APIFY_PREMIUM_KEY`, and numbered test keys `APIFY_KEY_1`, `APIFY_KEY_2`, `APIFY_KEY_3`, etc. |
