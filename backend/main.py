from fastapi import FastAPI, BackgroundTasks, HTTPException

from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import uuid
import asyncio

from backend.pipeline import run_full_pipeline, run_scoring_pipeline
from backend.job_store import job_status_store

app = FastAPI(title="Job Scraper & Scorer API", version="1.0.0")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://lead-gen-v01.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request Models ─────────────────────────────────────────────
class ScrapeInput(BaseModel):
    keywords: List[str] = ["Customer Support Specialist", "Technical Support Specialist", "Support Specialist"]
    location: str = "Europe"
    experience_levels: List[str] = ["entry-level", "associate"]
    work_types: List[str] = ["remote"]
    published_at: str = "r604800"   # last 7 days
    max_items: int = 10
    min_employees: int = 50
    max_employees: int = 1000


class ScoreInput(BaseModel):
    job_id: Optional[str] = None   # score a specific job by jobId; None = score all unscored


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