import os
import traceback
from groq import Groq
from scraper import scrape_linkedin_jobs, check_repeatability, is_company_size_valid
from job_store import job_status_store
from sheets_helper import (
    get_gc,
    get_or_create_sheet,
    get_existing_job_ids,
    get_all_rows_as_dicts,
    append_rows_safe,
    upsert_scoring_row,
    SCRAPED_SHEET_NAME,
    SCORING_SHEET_NAME,
    SCRAPED_HEADERS,
    SCORING_HEADERS,
)
from scraper import run_scraper
from review_finder import enrich_reviews
from funding_checker import enrich_funding
from scoring import LeadScorer
from openai import OpenAI

# ── LLM client (Groq) ─────────────────────────────────────────

def build_llm_client():
    client = OpenAI()

    def llm_client(prompt: str) -> str:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )

        return response.choices[0].message.content

    return llm_client


# ── Status helper ─────────────────────────────────────────────

def update_status(run_id: str, step: str, extra: dict = None):
    entry = job_status_store.get(run_id, {})
    entry["step"] = step
    entry["status"] = "running"
    if extra:
        entry.update(extra)
    job_status_store[run_id] = entry
    print(f"[{run_id}] {step}")


def finish(run_id: str, message: str, data: dict = None):
    entry = job_status_store.get(run_id, {})
    entry["status"] = "done"
    entry["step"] = message
    entry["message"] = message
    if data:
        entry.update(data)
    job_status_store[run_id] = entry
    print(f"[{run_id}] ✅ {message}")


def fail(run_id: str, error: str):
    entry = job_status_store.get(run_id, {})
    entry["status"] = "error"
    entry["error"] = error
    entry["step"] = f"❌ Failed: {error}"
    job_status_store[run_id] = entry
    print(f"[{run_id}] ❌ {error}")


# ── Pipeline 1: Scrape + Enrich → Scraped_Jobs_V05 ────────────

def run_full_pipeline(run_id: str, config: dict):
    try:
        # ── Step 1: Scrape LinkedIn ────────────────────────────
        def cb(msg):
            update_status(run_id, msg)

        update_status(run_id, "🚀 Scraping LinkedIn jobs...")
        extracted = scrape_linkedin_jobs(config, status_cb=cb)

        if not extracted:
            finish(run_id, "⚠️ No jobs scraped from LinkedIn", {"jobs_added": 0})
            return

        # ── Step 2: Filter by size BEFORE repeatability ────────
        min_emp = config.get("min_employees", 50)
        max_emp = config.get("max_employees", 1000)

        size_filtered = []
        for row in extracted:
            emp = row.get("companyEmployeeCount", "")
            if not is_company_size_valid(emp, min_emp, max_emp):
                update_status(run_id, f"⛔ Size filter: {row.get('companyName')} ({emp})")
                continue
            size_filtered.append(row)

        if not size_filtered:
            finish(run_id, "⚠️ No jobs passed size filter", {"jobs_added": 0})
            return

        # ── Step 3: Repeatability check ────────────────────────
        update_status(run_id, f"🔍 Running repeatability on {len(size_filtered)} jobs...")
        enriched = check_repeatability(size_filtered, status_cb=cb)

        # ── Step 4: Reviews ────────────────────────────────────
        update_status(run_id, f"📝 Fetching reviews for {len(enriched)} jobs...")
        enriched = enrich_reviews(enriched, status_cb=cb)

        # ── Step 5: Funding ────────────────────────────────────
        update_status(run_id, f"💰 Fetching funding for {len(enriched)} jobs...")
        enriched = enrich_funding(enriched, status_cb=cb)

        # ── Step 6: NOW open Google Sheet ─────────────────────
        update_status(run_id, "📄 Opening Google Sheet: Scraped_Jobs_V05...")
        gc = get_gc()
        _, ws = get_or_create_sheet(gc, SCRAPED_SHEET_NAME, SCRAPED_HEADERS)
        existing_ids = get_existing_job_ids(ws)

        # Filter out duplicates that appeared in sheet since we started
        new_rows = [
            row for row in enriched
            if str(row.get("jobId", "")) not in existing_ids
        ]

        if not new_rows:
            finish(run_id, "⏭️ No new jobs after duplicate check", {"jobs_added": 0})
            return

        # ── Step 7: Write to sheet ─────────────────────────────
        update_status(run_id, f"📊 Writing {len(new_rows)} jobs to sheet...")
        sheet_rows = [
            [row.get(h, "") for h in SCRAPED_HEADERS]
            for row in new_rows
        ]
        append_rows_safe(ws, sheet_rows, SCRAPED_HEADERS)

        finish(
            run_id,
            f"✅ Done — {len(new_rows)} jobs saved to {SCRAPED_SHEET_NAME}",
            {"jobs_added": len(new_rows)},
        )

    except Exception as e:
        fail(run_id, f"{e}\n{traceback.format_exc()}")


# ── Pipeline 2: Score jobs → Job_Scoring_List ─────────────────

def run_scoring_pipeline(run_id: str, target_job_id: str | None = None):
    try:
        # ── Read source sheet ──────────────────────────────────
        update_status(run_id, f"📄 Reading {SCRAPED_SHEET_NAME}...")

        gc = get_gc()

        _, src_ws = get_or_create_sheet(
            gc,
            SCRAPED_SHEET_NAME,
            SCRAPED_HEADERS
        )

        all_jobs = get_all_rows_as_dicts(src_ws)

        # Debug
        if all_jobs:
            print(
                f"[{run_id}] DEBUG first job keys: "
                f"{list(all_jobs[0].keys())}"
            )
            print(
                f"[{run_id}] DEBUG first job sample: "
                f"companyName={all_jobs[0].get('companyName')} | "
                f"jobTitle={all_jobs[0].get('jobTitle')}"
            )
        else:
            print(f"[{run_id}] DEBUG all_jobs is empty!")

        # ── Open scoring sheet ONCE ────────────────────────────
        update_status(run_id, f"📄 Opening {SCORING_SHEET_NAME}...")

        _, score_ws = get_or_create_sheet(
            gc,
            SCORING_SHEET_NAME,
            SCORING_HEADERS
        )

        already_scored_count = len(
            get_all_rows_as_dicts(score_ws)
        )

        # ── Pick only unscored jobs ────────────────────────────
        to_score = all_jobs[already_scored_count:]

        if target_job_id:
            target_job_id = str(target_job_id).strip()

            to_score = [
                row
                for row in all_jobs
                if str(row.get("jobId", "")).strip() == target_job_id
            ]

        if not to_score:
            finish(
                run_id,
                "⏭️ All jobs already scored",
                {"scored": 0}
            )
            return

        update_status(
            run_id,
            f"🤖 Scoring {len(to_score)} new jobs..."
        )

        scorer = LeadScorer(
            llm_client=build_llm_client()
        )

        rows_to_write = []
        scored = 0

        # ── Score jobs ─────────────────────────────────────────
        for idx, job in enumerate(to_score, start=1):

            company = job.get("companyName", "?")
            title = job.get("jobTitle", "?")

            update_status(
                run_id,
                f"🤖 Scoring ({idx}/{len(to_score)}): "
                f"{title} @ {company}"
            )

            try:
                result = scorer.score_lead(job)

                score_row = {
                    "jobTitle": job.get("jobTitle", ""),
                    "jobUrl": job.get("jobUrl", ""),
                    "companyName": job.get("companyName", ""),
                    "location": job.get("location", ""),
                    "workType": job.get("workType", ""),
                    "experienceLevel": job.get("experienceLevel", ""),
                    "sector": job.get("sector", ""),
                    "companyEmployeeCount": job.get(
                        "companyEmployeeCount", ""
                    ),
                    **result,
                }

                rows_to_write.append(
                    [
                        score_row.get(h, "")
                        for h in SCORING_HEADERS
                    ]
                )

                scored += 1

                print(
                    f"[{run_id}] "
                    f"{company} | {title} → "
                    f"{result['total_score']} | "
                    f"{result['decision']} "
                    f"({result['priority']})"
                )

            except Exception as e:
                print(
                    f"[{run_id}] ❌ Failed scoring "
                    f"{company} | {title}: {e}"
                )

        # ── Single batch write ────────────────────────────────
        if rows_to_write:

            update_status(
                run_id,
                f"📊 Writing {len(rows_to_write)} rows..."
            )

            for attempt in range(3):
                try:
                    score_ws.append_rows(
                        rows_to_write,
                        value_input_option="RAW"
                    )
                    break

                except Exception as e:

                    if attempt == 2:
                        raise

                    import time

                    wait = 5 * (attempt + 1)

                    print(
                        f"[{run_id}] ⚠️ Batch write failed "
                        f"(attempt {attempt + 1}/3). "
                        f"Retrying in {wait}s..."
                    )

                    time.sleep(wait)

        finish(
            run_id,
            f"✅ Scored {scored} jobs → {SCORING_SHEET_NAME}",
            {"scored": scored}
        )

    except Exception as e:
        fail(
            run_id,
            f"{e}\n{traceback.format_exc()}"
        )


# Simplified _upsert_with_retry — just appends
def _upsert_with_retry(run_id: str, score_row: dict, max_attempts: int = 3):
    import time
    last_error = None
    for attempt in range(max_attempts):
        try:
            gc = get_gc()
            _, score_ws = get_or_create_sheet(gc, SCORING_SHEET_NAME, SCORING_HEADERS)
            row_data = [score_row.get(h, "") for h in SCORING_HEADERS]
            score_ws.append_row(row_data, value_input_option="RAW")
            return
        except Exception as e:
            last_error = e
            wait = 5 * (attempt + 1)
            print(f"[{run_id}] ⚠️ Write failed (attempt {attempt+1}/3), retrying in {wait}s... {e}")
            time.sleep(wait)
    raise RuntimeError(f"Sheet write failed after {max_attempts} attempts: {last_error}")