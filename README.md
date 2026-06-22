# Job Scraper & Scorer API

An automated pipeline that scrapes LinkedIn job postings, enriches them with company reviews and funding data, scores them as B2B sales leads using an LLM, and stores everything in Google Sheets.

## Overview

This service finds companies that are actively hiring for specific roles (e.g. Customer Support) and turns that signal into a ranked list of sales leads — useful for outbound sales/prospecting teams targeting companies with active hiring pain points.

**Flow:** `Scrape LinkedIn → Filter by company size → Check job repost frequency → Fetch Glassdoor reviews → Fetch funding data → Score with LLM → Save to Google Sheets`

## Architecture

```
FastAPI (main.py)
   │
   ├── /run-pipeline   → scrape + enrich only
   ├── /run-scoring    → score existing rows only
   └── /run-full       → scrape + enrich + score (end-to-end)
   │
   ▼
pipeline.py  (orchestrator, runs in background tasks)
   │
   ├── scraper.py          → Apify LinkedIn scraper + repeatability check
   ├── review_finder.py     → Apify Glassdoor reviews scraper
   ├── funding_checker.py   → Clearbit (domain lookup) + Apollo.io (funding data)
   ├── scoring.py            → LLM-based lead scoring (Groq/OpenAI)
   └── sheets_helper.py      → Google Sheets read/write
```

All pipeline runs are tracked asynchronously via an in-memory `job_store.py` and polled through `/status/{run_id}`.

## Features

- **LinkedIn job scraping** via Apify Actor, filtered by keyword, location, experience level, work type, and recency.
- **Company size filtering** (min/max employee count) before any expensive enrichment runs.
- **Repeatability scoring** — detects how often a company reposts similar roles (signals ongoing hiring need).
- **Glassdoor review enrichment** — pulls recent reviews for company-culture signal.
- **Funding enrichment** — resolves company domain (Clearbit) and pulls funding stage/amount/date (Apollo.io).
- **LLM lead scoring** — scores each job on 7 weighted dimensions and outputs a final decision: `KEEP / HOLD / REJECT`.
- **Google Sheets persistence** — two sheets: raw scraped+enriched jobs, and final scored leads.
- **Deduplication** — by `jobId` (jobs) and by company (funding/reviews cache) to avoid redundant API calls.

## Scoring Model

Each job is scored on 7 dimensions:

| Dimension | Range | Source | Description |
|---|---|---|---|
| Execution Signal (D1) | 0–3 | LLM | How well the role matches target job types |
| Hiring Intent (D2) | 0–3 | Rule | Based on repeatability (repost frequency) |
| Company Fit (D3) | 0–2 | LLM | Industry, size, funding stage fit |
| Remote Readiness (D4) | 0–2 | Rule | Remote / hybrid / onsite |
| Buying Trigger (D5) | 0–3 | LLM | Funding recency, scaling pressure |
| Repost Bonus (D6) | 0–2 | Rule | Derived from D2 |
| Enrichment Confidence (D7) | 0–2 | Rule | Data completeness (funding, reviews, headcount) |

**Disqualification rule:** if the company looks like a staffing/recruiting/consulting/marketplace business, D1/D3/D5 are forced to `0`, which zeroes the entire score (lead rejected).

**Decision thresholds (total score 0–17):**

| Score | Decision | Priority |
|---|---|---|
| ≥ 13 | KEEP | HIGH |
| 9–12 | KEEP | MEDIUM |
| 6–8 | HOLD | MONITOR |
| < 6 | REJECT | — |

## Tech Stack

- **API:** FastAPI + Pydantic
- **Scraping:** Apify (LinkedIn Jobs actor, Glassdoor Reviews actor)
- **Enrichment:** Clearbit Autocomplete API, Apollo.io Organization Enrichment API
- **Scoring LLM:** OpenAI (`gpt-5-mini`) via `openai` SDK (Groq client imported but unused in current flow)
- **Storage:** Google Sheets (via `gspread` + Google service account)

## Project Structure

```
.
├── main.py              # FastAPI app & routes
├── pipeline.py           # Orchestrates the full scrape → enrich → score flow
├── scraper.py            # LinkedIn scraping + size filter + repeatability check
├── review_finder.py       # Glassdoor review enrichment
├── funding_checker.py     # Clearbit domain lookup + Apollo funding enrichment
├── scoring.py             # LLM + rule-based lead scoring logic
├── sheets_helper.py        # Google Sheets read/write/format utilities
└── job_store.py            # In-memory store for background job status
```

## Setup

### Prerequisites

- Python 3.10+
- A Google Cloud service account with Sheets + Drive API access
- API keys: Apify, Apollo.io, OpenAI

### Installation

```bash
pip install fastapi uvicorn pydantic apify-client gspread google-auth openai groq python-dotenv requests
```

### Environment Variables

Create a `.env` file in the project root:

```env
APIFY_KEY=your_apify_token
APOLLO_API_KEY=your_apollo_api_key
OPENAI_API_KEY=your_openai_api_key
GOOGLE_CREDENTIALS_PATH=credentials.json
```

`credentials.json` should be your Google service account key, shared with edit access on the target Google Sheets.

### Run the API

```bash
uvicorn main:app --reload
```

## API Reference

### `POST /run-pipeline`
Scrapes LinkedIn jobs and enriches them (reviews + funding). Does **not** score.

**Body:**
```json
{
  "keywords": ["Customer Support Specialist"],
  "location": "Europe",
  "experience_levels": ["entry-level", "associate"],
  "work_types": ["remote"],
  "published_at": "r604800",
  "max_items": 10,
  "min_employees": 50,
  "max_employees": 1000
}
```

### `POST /run-scoring`
Scores unscored rows from the scraped sheet (or one specific job via `job_id`).

**Body:**
```json
{ "job_id": null }
```

### `POST /run-full`
Runs the complete pipeline end-to-end: scrape → enrich → score.

### `GET /status/{run_id}`
Returns the current status of a background run.

### `GET /status`
Lists all tracked runs.

## Google Sheets Output

**`Scaped_v6`** — raw scraped + enriched jobs (job details, company info, reviews, funding).

**`Score_Listing_v6`** — final scored leads with per-dimension scores, total score, decision, and reasoning.

Both sheets are auto-created with formatted headers if they don't exist.

## Notes & Limitations

- Pipeline runs are tracked in-memory (`job_store.py`); status is lost on server restart.
- Scoring resumes by row-count offset between sheets — reordering or manually editing the scoring sheet can cause jobs to be skipped or rescored.
- External API failures (Clearbit, Apollo, Glassdoor) degrade gracefully to `"not found"` rather than failing the run.