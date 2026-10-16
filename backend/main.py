from fastapi import FastAPI, BackgroundTasks, HTTPException

from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Union
import uuid
import asyncio
import os

from backend.pipeline import run_full_pipeline, run_scoring_pipeline, run_email_finder_pipeline
from backend.job_store import job_status_store
from backend.sheets_helper import (
    get_gc,
    get_keep_companies,
    append_to_email_saver,
    get_email_saver_entries,
    upsert_email_saver_row,
    update_email_outreach_status,
)
from backend.email_sender import (
    get_company_context,
    build_prompt,
    generate_email_content,
    send_email,
    DEFAULT_SENDER,
    TEST_EMAIL_OVERRIDE,
)

app = FastAPI(title="Job Scraper & Scorer API", version="1.0.0")

from fastapi.middleware.cors import CORSMiddleware

env_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
allowed_origins = list(set(["http://localhost:3000", "http://127.0.0.1:3000"] + env_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request Models ─────────────────────────────────────────────
class ScrapeInput(BaseModel):
    keywords: Union[List[str], str] = ["Customer Support Specialist"]
    location: str = "Europe"
    experience_levels: Union[List[str], str] = ["entry-level", "associate"]
    work_types: Union[List[str], str] = ["remote"]
    published_at: str = "r604800"   # last 7 days
    max_items: int = 10
    min_employees: int = 50
    max_employees: int = 1000
    outreach_mode: str = "test"    # "test" (redirect to test inbox) or "live" (real prospect email)
    test_email_recipient: Optional[str] = "niloyvetesting54@gmail.com"


class ScoreInput(BaseModel):
    job_id: Optional[str] = None   # score a specific job by jobId; None = score all unscored
    outreach_mode: str = "test"
    test_email_recipient: Optional[str] = "niloyvetesting54@gmail.com"


class EmailFinderInput(BaseModel):
    company_url: str
    company_name: str


class SaveEmailInput(BaseModel):
    companyName: str
    personName: str
    email: str
    designation: str
    linkedinUrl: str = ""


class GenerateShowcaseInput(BaseModel):
    companyName: str
    personName: str
    email: str
    designation: Optional[str] = ""
    linkedinUrl: Optional[str] = ""


class SendShowcaseInput(BaseModel):
    to_email: str
    subject: str
    body: str
    original_lead_email: str
    companyName: Optional[str] = ""
    personName: Optional[str] = ""
    update_sheet: bool = True


# ── Routes ─────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "Job Scraper & Scorer API is running 🚀"}


@app.post("/run-pipeline")
async def run_pipeline(input_data: ScrapeInput, background_tasks: BackgroundTasks):
    """
    Starts the full scraping pipeline in the background:
    1. Apify LinkedIn scraper
    2. Glassdoor review finder
    3. Apollo funding checker
    Results are stored in Google Sheet: 'Scraped_Jobs_V05'
    """
    run_id = str(uuid.uuid4())[:8]
    job_status_store[run_id] = {"status": "running", "step": "Starting...", "run_id": run_id}

    background_tasks.add_task(run_full_pipeline, run_id, input_data.model_dump())

    return {
        "run_id": run_id,
        "message": "Pipeline started in background",
        "check_status": f"/status/{run_id}"
    }


@app.post("/run-scoring")
async def run_scoring(input_data: ScoreInput, background_tasks: BackgroundTasks):
    """
    Scores jobs from 'Scraped_Jobs_V05' and saves results to 'Job_Scoring_List'.
    If job_id is None: scores all unscored rows one by one.
    If job_id is provided: scores only that specific job.
    """
    run_id = str(uuid.uuid4())[:8]
    job_status_store[run_id] = {"status": "running", "step": "Starting scorer...", "run_id": run_id}

    background_tasks.add_task(
        run_scoring_pipeline,
        run_id,
        input_data.job_id,
        None,
        input_data.outreach_mode,
        input_data.test_email_recipient,
    )

    return {
        "run_id": run_id,
        "message": "Scoring started in background",
        "check_status": f"/status/{run_id}"
    }


@app.post("/run-full")
async def run_full(input_data: ScrapeInput, background_tasks: BackgroundTasks):
    """
    Runs the COMPLETE pipeline end-to-end:
    Scrape → Reviews → Funding → Score → Auto Find Emails → Outreach
    """
    run_id = str(uuid.uuid4())[:8]
    job_status_store[run_id] = {"status": "running", "step": "Starting full pipeline...", "run_id": run_id}

    async def full_pipeline():
        await asyncio.to_thread(run_full_pipeline, run_id, input_data.model_dump())
        if job_status_store[run_id]["status"] != "error":
            await asyncio.to_thread(
                run_scoring_pipeline,
                run_id,
                None,
                input_data.keywords,
                input_data.outreach_mode,
                input_data.test_email_recipient,
            )

    background_tasks.add_task(full_pipeline)

    return {
        "run_id": run_id,
        "message": "Full pipeline (scrape + score) started",
        "check_status": f"/status/{run_id}"
    }


@app.get("/status/{run_id}")
def get_status(run_id: str):
    """Check the status of a running or completed pipeline job."""
    if run_id not in job_status_store:
        raise HTTPException(status_code=404, detail="Run ID not found")
    return job_status_store[run_id]


@app.get("/status")
def list_statuses():
    """List all pipeline runs and their statuses."""
    return list(job_status_store.values())


# ── Email Finder Endpoints ─────────────────────────────────────

@app.get("/keep-companies")
def keep_companies():
    """Return all companies with KEEP decision from the scoring sheet."""
    try:
        gc = get_gc()
        companies = get_keep_companies(gc)
        return {"companies": companies}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/find-emails")
async def find_emails(input_data: EmailFinderInput, background_tasks: BackgroundTasks):
    """
    Find decision makers at a company and extract their emails.
    Runs as a background task.
    """
    run_id = str(uuid.uuid4())[:8]
    job_status_store[run_id] = {
        "status": "running",
        "step": f"Starting email finder for {input_data.company_name}...",
        "run_id": run_id,
        "company_name": input_data.company_name,
    }

    background_tasks.add_task(
        run_email_finder_pipeline,
        run_id,
        input_data.company_url,
        input_data.company_name,
    )

    return {
        "run_id": run_id,
        "message": f"Email finder started for {input_data.company_name}",
        "check_status": f"/status/{run_id}",
    }


@app.post("/save-email")
def save_email(input_data: SaveEmailInput):
    """Save a single contact to the EMAIL_SAVER Google Sheet."""
    try:
        from datetime import datetime
        gc = get_gc()
        row_data = {
            "companyName": input_data.companyName,
            "personName": input_data.personName,
            "email": input_data.email,
            "designation": input_data.designation,
            "linkedinUrl": input_data.linkedinUrl,
            "addedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        append_to_email_saver(gc, row_data)
        return {"message": "Contact saved successfully", "data": row_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Email Outreach Showcase Endpoints ─────────────────────────

@app.get("/email-saver-leads")
def get_leads_from_email_saver():
    """Retrieve all leads from Email_saver sheet with valid emails."""
    try:
        gc = get_gc()
        leads = get_email_saver_entries(gc)
        valid_leads = [
            l for l in leads
            if l.get("email") and "@" in str(l.get("email")) and str(l.get("email")).strip().lower() != "email"
        ]
        return {
            "leads": valid_leads,
            "default_sender": DEFAULT_SENDER,
            "default_test_recipient": TEST_EMAIL_OVERRIDE or "niloyvetesting54@gmail.com",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-showcase-email")
def generate_showcase_email(input_data: GenerateShowcaseInput):
    """Generate a tailored B2B outreach email for a chosen lead using company signals and LLM."""
    try:
        gc = get_gc()
        context = get_company_context(input_data.companyName, gc=gc)
        prompt = build_prompt(input_data.model_dump(), context)
        content = generate_email_content(
            prompt,
            company_name=input_data.companyName,
            person_name=input_data.personName,
        )
        return {
            "subject": content.get("subject", ""),
            "body": content.get("body", ""),
            "context": context,
            "meta": content.get("meta", {}),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Generation failed: {str(e)}")


@app.post("/send-showcase-email")
def send_showcase_email(input_data: SendShowcaseInput):
    """Safely dispatch showcase email to the manager / test recipient and update sheet."""
    try:
        if not input_data.to_email or "@" not in input_data.to_email:
            raise HTTPException(status_code=400, detail="Invalid test recipient email address")

        sent = send_email(
            to_email=input_data.to_email.strip(),
            subject=input_data.subject,
            body=input_data.body,
        )
        if not sent:
            raise HTTPException(status_code=500, detail="SMTP dispatch failed. Please verify SMTP credentials in .env")

        from datetime import datetime
        sent_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if input_data.update_sheet and input_data.original_lead_email:
            try:
                gc = get_gc()
                status_text = f"SENT (Showcase to {input_data.to_email.strip()})"
                update_email_outreach_status(
                    gc,
                    email=input_data.original_lead_email,
                    subject=input_data.subject,
                    email_body=input_data.body,
                    status=status_text,
                    sent_at=sent_at,
                )
            except Exception as sheet_err:
                print(f"⚠️ Warning: Could not update sheet status: {sheet_err}")

        return {
            "success": True,
            "message": f"Showcase email successfully sent to {input_data.to_email}!",
            "recipient": input_data.to_email,
            "sentAt": sent_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))