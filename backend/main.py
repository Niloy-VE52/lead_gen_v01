from fastapi import FastAPI, BackgroundTasks, HTTPException

from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Union
import uuid
import asyncio
import os

from backend.pipeline import run_full_pipeline, run_scoring_pipeline, run_email_finder_pipeline
from backend.job_store import job_status_store
from backend.sheets_helper import get_gc, get_keep_companies, append_to_email_saver, get_email_saver_entries

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


class ScoreInput(BaseModel):
    job_id: Optional[str] = None   # score a specific job by jobId; None = score all unscored


class EmailFinderInput(BaseModel):
    company_url: str
    company_name: str


class SaveEmailInput(BaseModel):
    companyName: str
    personName: str
    email: str
    designation: str
    linkedinUrl: str = ""


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

    background_tasks.add_task(run_scoring_pipeline, run_id, input_data.job_id)

    return {
        "run_id": run_id,
        "message": "Scoring started in background",
        "check_status": f"/status/{run_id}"
    }


@app.post("/run-full")
async def run_full(input_data: ScrapeInput, background_tasks: BackgroundTasks):
    """
    Runs the COMPLETE pipeline end-to-end:
    Scrape → Reviews → Funding → Score → Save to both sheets
    """
    run_id = str(uuid.uuid4())[:8]
    job_status_store[run_id] = {"status": "running", "step": "Starting full pipeline...", "run_id": run_id}

    async def full_pipeline():
        await asyncio.to_thread(run_full_pipeline, run_id, input_data.model_dump())
        if job_status_store[run_id]["status"] != "error":
            await asyncio.to_thread(run_scoring_pipeline, run_id, None)

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