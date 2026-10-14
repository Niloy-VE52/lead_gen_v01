import os
import traceback
from groq import Groq
from backend.scraper import scrape_linkedin_jobs, check_repeatability, is_company_size_valid
from backend.job_store import job_status_store
from backend.sheets_helper import (
    get_gc,
    get_or_create_sheet,
    get_existing_job_ids,
    get_existing_companies,
    get_all_rows_as_dicts,
    append_rows_safe,
    upsert_scoring_row,
    format_keep_rows_in_sheet,
    SCRAPED_SHEET_NAME,
    SCORING_SHEET_NAME,
    SCRAPED_HEADERS,
    SCORING_HEADERS,
)
from backend.scraper import run_scraper
from backend.review_finder import enrich_reviews
from backend.funding_checker import enrich_funding
from backend.scoring import LeadScorer
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

        # ── Step 3: Open Google Sheet & Duplicate Filter by Company ──
        update_status(run_id, f"📄 Checking duplicates in Google Sheet: {SCRAPED_SHEET_NAME}...")
        gc = get_gc()
        _, ws = get_or_create_sheet(gc, SCRAPED_SHEET_NAME, SCRAPED_HEADERS)
        existing_companies = get_existing_companies(ws)
        existing_ids = get_existing_job_ids(ws)

        deduped_jobs = []
        batch_seen_companies = set()

        for row in size_filtered:
            job_id = str(row.get("jobId", "")).strip()
            company_raw = row.get("companyName", "").strip()
            company_key = company_raw.lstrip("'").strip().lower()

            if not company_key:
                update_status(run_id, "⛔ Skipping job with missing company name")
                continue

            if job_id and job_id in existing_ids:
                update_status(run_id, f"⏭️ Duplicate job ID skipped: {row.get('jobTitle')} @ {company_raw}")
                continue

            if company_key in existing_companies:
                update_status(run_id, f"⏭️ Duplicate company (already in sheet): {company_raw}")
                continue

            if company_key in batch_seen_companies:
                update_status(run_id, f"⏭️ Duplicate company in batch skipped: {company_raw}")
                continue

            batch_seen_companies.add(company_key)
            deduped_jobs.append(row)

        if not deduped_jobs:
            finish(run_id, "⚠️ No new unique companies passed duplicate check", {"jobs_added": 0})
            return

        # ── Step 4: Repeatability check ────────────────────────
        update_status(run_id, f"🔍 Running repeatability on {len(deduped_jobs)} unique company jobs...")
        enriched = check_repeatability(deduped_jobs, status_cb=cb)

        # ── Step 5: Reviews ────────────────────────────────────
        update_status(run_id, f"📝 Fetching reviews for {len(enriched)} jobs...")
        enriched = enrich_reviews(enriched, status_cb=cb)

        # ── Step 6: Funding ────────────────────────────────────
        update_status(run_id, f"💰 Fetching funding for {len(enriched)} jobs...")
        enriched = enrich_funding(enriched, status_cb=cb)

        # ── Step 7: Write to sheet ─────────────────────────────
        update_status(run_id, f"📊 Writing {len(enriched)} jobs to sheet...")
        sheet_rows = [
            [row.get(h, "") for h in SCRAPED_HEADERS]
            for row in enriched
        ]
        append_rows_safe(ws, sheet_rows, SCRAPED_HEADERS)

        finish(
            run_id,
            f"✅ Done — {len(enriched)} unique company jobs saved to {SCRAPED_SHEET_NAME}",
            {"jobs_added": len(enriched)},
        )

    except Exception as e:
        fail(run_id, f"{e}\n{traceback.format_exc()}")


# ── Pipeline 2: Score jobs → Job_Scoring_List ─────────────────

def run_scoring_pipeline(run_id: str, target_job_id: str | None = None, keywords: list[str] | None = None):
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
            llm_client=build_llm_client(),
            keywords=keywords
        )

        rows_to_write = []
        scored = 0
        keep_companies = []
        seen_keep_companies = set()

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

                if str(result.get("decision", "")).strip().upper() == "KEEP":
                    company_norm = company.strip().lower()
                    if company_norm and company_norm not in seen_keep_companies:
                        seen_keep_companies.add(company_norm)
                        keep_companies.append({
                            "companyName": company,
                            "companyUrl": job.get("companyUrl", "").strip()
                        })

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

            # Format KEEP rows in green (#b8d7aa)
            try:
                format_keep_rows_in_sheet(score_ws)
            except Exception as format_err:
                print(f"[{run_id}] ⚠️ Failed to format KEEP rows: {format_err}")

        # ── Step 4: Auto Find & Save Emails for KEEP companies ──────
        total_emails_saved = 0
        total_emails_sent = 0
        if keep_companies:
            from datetime import datetime
            from backend.emailFinder import get_decisionmakers_linkedin, get_email_from_linkedin_profile
            from backend.sheets_helper import append_to_email_saver, get_email_saver_entries
            from backend.email_sender import run_email_pipeline

            update_status(run_id, f"🔍 Auto Email Finder: Finding emails for {len(keep_companies)} KEEP companies...")

            try:
                existing_saved = get_email_saver_entries(gc)
                already_saved_companies = set(
                    r.get("companyName", "").strip().lower()
                    for r in existing_saved if r.get("companyName")
                )
            except Exception as e:
                print(f"[{run_id}] ⚠️ Could not fetch existing Email_saver entries: {e}")
                already_saved_companies = set()

            for k_idx, k_comp in enumerate(keep_companies, start=1):
                c_name = k_comp["companyName"]
                c_url = k_comp["companyUrl"]

                if not c_url:
                    print(f"[{run_id}] ⚠️ Skipping email finder for {c_name}: No companyUrl")
                    continue

                if c_name.strip().lower() in already_saved_companies:
                    print(f"[{run_id}] ⏭️ Skipping email finder for {c_name}: Already in Email_saver")
                    continue

                update_status(run_id, f"👥 Finding decision makers ({k_idx}/{len(keep_companies)}): {c_name}...")
                try:
                    decision_makers = get_decisionmakers_linkedin(c_url)
                    if not decision_makers:
                        print(f"[{run_id}] ⚠️ No decision makers found at {c_name}")
                        continue

                    update_status(run_id, f"📧 Extracting emails for {len(decision_makers)} contacts at {c_name}...")
                    for person in decision_makers:
                        first_name = person.get("firstName", "")
                        last_name = person.get("lastName", "")
                        full_name = f"{first_name} {last_name}".strip()
                        linkedin_url = person.get("linkedinUrl", "")

                        designation = ""
                        current_pos = person.get("currentPositions", [])
                        if current_pos and isinstance(current_pos, list):
                            designation = current_pos[0].get("title", "")

                        email = ""
                        if linkedin_url:
                            try:
                                email_results = get_email_from_linkedin_profile(linkedin_url)
                                if email_results and isinstance(email_results, list):
                                    for res in email_results:
                                        found_email = res.get("email", "")
                                        if found_email:
                                            email = found_email
                                            break
                            except Exception as email_err:
                                print(f"[{run_id}] ⚠️ Email lookup failed for {full_name}: {email_err}")

                        if email:
                            # ── Auto Email Generation & Sending ─────────────────
                            contact_data = {
                                "companyName": c_name,
                                "personName": full_name,
                                "email": email,
                                "designation": designation,
                                "linkedinUrl": linkedin_url,
                            }

                            update_status(run_id, f"✉️ Generating & sending email to {full_name} ({c_name})...")

                            email_body = ""
                            outreach_status = "PENDING"
                            sent_at = ""

                            try:
                                send_res = run_email_pipeline(contact_data, dry_run=False, gc=gc)
                                if send_res.get("success"):
                                    sent_recipient = send_res.get("recipient", email)
                                    outreach_status = f"SENT (to {sent_recipient})" if sent_recipient != email else "SENT"
                                    email_body = f"Subject: {send_res.get('subject')}\n\n{send_res.get('body')}"
                                    sent_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    total_emails_sent += 1
                                else:
                                    outreach_status = f"FAILED: {send_res.get('error', 'SMTP Error')}"
                            except Exception as send_err:
                                print(f"[{run_id}] ⚠️ Auto email sending failed for {full_name}: {send_err}")
                                outreach_status = f"FAILED: {send_err}"

                            row_data = {
                                "companyName": c_name,
                                "personName": full_name,
                                "email": email,
                                "designation": designation,
                                "linkedinUrl": linkedin_url,
                                "addedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "emailBody": email_body,
                                "outreachStatus": outreach_status,
                                "sentAt": sent_at,
                            }
                            append_to_email_saver(gc, row_data)
                            total_emails_saved += 1
                            print(f"[{run_id}] 💾 Saved: {full_name} ({email}) | {outreach_status}")

                            # Pacing delay between automated sends
                            import time
                            time.sleep(5)

                except Exception as comp_err:
                    print(f"[{run_id}] ❌ Auto email finder error for {c_name}: {comp_err}")

        finish(
            run_id,
            f"✅ Scored {scored} jobs | Saved {total_emails_saved} emails | Sent {total_emails_sent} outreach emails",
            {"scored": scored, "emails_saved": total_emails_saved, "emails_sent": total_emails_sent}
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
            format_keep_rows_in_sheet(score_ws)
            return
        except Exception as e:
            last_error = e
            wait = 5 * (attempt + 1)
            print(f"[{run_id}] ⚠️ Write failed (attempt {attempt+1}/3), retrying in {wait}s... {e}")
            time.sleep(wait)
    raise RuntimeError(f"Sheet write failed after {max_attempts} attempts: {last_error}")


# ── Pipeline 3: Email Finder for KEEP companies ───────────────

def run_email_finder_pipeline(run_id: str, company_url: str, company_name: str):
    """Find decision makers at a company and extract their emails."""
    from backend.emailFinder import get_decisionmakers_linkedin, get_email_from_linkedin_profile

    try:
        # ── Step 1: Find decision makers ──────────────────────
        update_status(run_id, f"🔍 Finding decision makers at {company_name}...")

        decision_makers = get_decisionmakers_linkedin(company_url)

        if not decision_makers:
            finish(run_id, f"⚠️ No decision makers found at {company_name}", {
                "company_name": company_name,
                "contacts": []
            })
            return

        update_status(run_id, f"👥 Found {len(decision_makers)} decision makers. Extracting emails...")

        # ── Step 2: Extract emails for each person ────────────
        contacts = []
        for idx, person in enumerate(decision_makers, start=1):
            first_name = person.get("firstName", "")
            last_name = person.get("lastName", "")
            full_name = f"{first_name} {last_name}".strip()
            linkedin_url = person.get("linkedinUrl", "")

            # Get designation from current positions
            designation = ""
            current_positions = person.get("currentPositions", [])
            if current_positions and isinstance(current_positions, list):
                designation = current_positions[0].get("title", "")

            update_status(
                run_id,
                f"📧 Getting email ({idx}/{len(decision_makers)}): {full_name}..."
            )

            email = ""
            try:
                if linkedin_url:
                    email_results = get_email_from_linkedin_profile(linkedin_url)
                    if email_results and isinstance(email_results, list):
                        # The email scraper returns a list of profile data
                        for result in email_results:
                            found_email = result.get("email", "")
                            if found_email:
                                email = found_email
                                break
            except Exception as e:
                print(f"[{run_id}] ⚠️ Email lookup failed for {full_name}: {e}")

            contacts.append({
                "personName": full_name,
                "designation": designation,
                "email": email,
                "linkedinUrl": linkedin_url,
                "companyName": company_name,
            })

            print(f"[{run_id}] {full_name} | {designation} | {email or 'No email found'}")

        finish(run_id, f"✅ Found {len(contacts)} contacts at {company_name}", {
            "company_name": company_name,
            "contacts": contacts,
        })

    except Exception as e:
        fail(run_id, f"{e}\n{traceback.format_exc()}")