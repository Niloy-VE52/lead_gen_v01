import sys
import os
import logging
from dotenv import load_dotenv

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Filter repetitive polling requests (/status/ and /outreach-status) from console output
class StatusPollingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return "/status" not in msg and "/outreach-status" not in msg

logging.getLogger("uvicorn.access").addFilter(StatusPollingFilter())

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Union
import uuid
import asyncio

from backend.pipeline import run_full_pipeline, run_scoring_pipeline
from backend.job_store import job_status_store

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
    location: Union[List[str], str] = ["Europe"]
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


class ManualSendInput(BaseModel):
    email: str
    company_name: str
    person_name: str
    subject: str
    body: str
    outreach_mode: str = "test"
    test_email_recipient: Optional[str] = "niloyvetesting54@gmail.com"


class RegenerateEmailInput(BaseModel):
    company_name: str
    person_name: str
    designation: Optional[str] = ""
    email: Optional[str] = ""





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


@app.get("/outreach-status")
def get_outreach_status():
    """Retrieve all leads from Email_saver to display live status in UI."""
    try:
        from backend.sheets_helper import get_gc, get_email_saver_entries
        gc = get_gc()
        entries = get_email_saver_entries(gc)
        return {"entries": entries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/email-template")
def get_template_endpoint():
    """Get the currently active email outreach template."""
    from backend.template_manager import get_template
    return get_template()


@app.post("/email-template")
def save_template_endpoint(payload: dict):
    """Save the customized email outreach template."""
    from backend.template_manager import save_template
    try:
        updated = save_template(payload)
        return {"success": True, "template": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/email-template/reset")
def reset_template_endpoint():
    """Reset the email template back to the original default."""
    from backend.template_manager import reset_template
    try:
        default_tpl = reset_template()
        return {"success": True, "template": default_tpl}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/manual-send")
def manual_send_endpoint(payload: ManualSendInput):
    """
    Manually sends an email for a lead and updates the Email_saver sheet.
    """
    from backend.email_sender import manual_send_email
    try:
        result = manual_send_email(
            email=payload.email,
            company_name=payload.company_name,
            person_name=payload.person_name,
            subject=payload.subject,
            body=payload.body,
            outreach_mode=payload.outreach_mode,
            test_email_recipient=payload.test_email_recipient,
        )
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Email send failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/regenerate-email")
def regenerate_email_endpoint(payload: RegenerateEmailInput):
    """
    Regenerates email subject and body using the active template and company context signals.
    """
    from backend.email_sender import get_company_context, build_prompt, generate_email_content
    from backend.sheets_helper import get_gc
    try:
        contact = {
            "companyName": payload.company_name,
            "personName": payload.person_name,
            "designation": payload.designation,
            "email": payload.email,
        }
        gc = None
        try:
            gc = get_gc()
        except Exception:
            pass

        context = get_company_context(payload.company_name, gc=gc)
        prompt = build_prompt(contact, context)
        content = generate_email_content(prompt, company_name=payload.company_name, person_name=payload.person_name)

        return {
            "success": True,
            "subject": content.get("subject", ""),
            "body": content.get("body", ""),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




