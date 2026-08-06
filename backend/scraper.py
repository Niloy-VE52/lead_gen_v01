from apify_client import ApifyClient
import os
import re
import json
from datetime import datetime
from urllib.parse import urlparse, parse_qs, unquote
from rapidfuzz import fuzz


def get_client():
    return ApifyClient(os.getenv("APIFY_KEY"))
from dotenv import load_dotenv
load_dotenv()

# ── Helpers ────────────────────────────────────────────────────

def is_company_size_valid(employee_count_str, min_size=50, max_size=1000) -> bool:
    if not employee_count_str:
        return False
    s = str(employee_count_str).strip().replace(",", "")
    if s.endswith("+"):
        low = int(re.sub(r"[^\d]", "", s))
        return low <= max_size
    match = re.match(r"(\d+)\s*[-–]\s*(\d+)", s)
    if match:
        low, high = int(match.group(1)), int(match.group(2))
        return low <= max_size and high >= min_size
    plain = re.sub(r"[^\d]", "", s)
    if plain:
        n = int(plain)
        return min_size <= n <= max_size
    return False


def extract_real_url(redirect_url: str) -> str:
    if not redirect_url:
        return ""
    if "linkedin.com/redir/redirect" not in redirect_url:
        return redirect_url
    parsed = urlparse(redirect_url)
    params = parse_qs(parsed.query)
    real_url = params.get("url", [""])[0]
    return unquote(real_url)


def normalize(title):
    return re.sub(r'[^a-z0-9 ]', '', title.lower().strip())


STOP_WORDS = {
    "senior", "junior", "lead", "staff", "principal", "remote",
    "contract", "part", "full", "time", "at", "and", "or", "the"
}

FIELDS = [
    "jobId", "jobTitle", "jobUrl", "jobDescription",
    "companyName", "location", "publishedAt", "publishedDate",
    "contractType", "experienceLevel", "workType",
    "sector", "searchString", "companyEmployeeCount","companyDescription",
    "companyUrl", "companyWebsite",
]


# ── Step 1: LinkedIn scraper ───────────────────────────────────

def scrape_linkedin_jobs(config: dict, status_cb=None) -> list[dict]:
    client = get_client()

    raw_keywords = config.get("keywords")
    if isinstance(raw_keywords, str):
        keywords_list = [k.strip() for k in raw_keywords.split(",") if k.strip()]
    elif isinstance(raw_keywords, list):
        keywords_list = [k.strip() for k in raw_keywords if isinstance(k, str) and k.strip()]
    else:
        keywords_list = []

    if not keywords_list:
        keywords_list = ["Customer Support Specialist"]

    raw_exp = config.get("experience_levels")
    if isinstance(raw_exp, str):
        exp_list = [e.strip() for e in raw_exp.split(",") if e.strip()]
    elif isinstance(raw_exp, list):
        exp_list = [e.strip() for e in raw_exp if isinstance(e, str) and e.strip()]
    else:
        exp_list = ["entry"]

    raw_wt = config.get("work_types")
    if isinstance(raw_wt, str):
        wt_list = [w.strip() for w in raw_wt.split(",") if w.strip()]
    elif isinstance(raw_wt, list):
        wt_list = [w.strip() for w in raw_wt if isinstance(w, str) and w.strip()]
    else:
        wt_list = ["remote"]

    # Normalize experience levels to allowed values for the new actor
    ALLOWED_EXP = {"internship", "entry", "associate", "mid-senior", "director", "executive"}
    EXP_MAP = {
        "entry-level": "entry",
        "entry level": "entry",
        "mid-senior-level": "mid-senior",
        "mid-senior level": "mid-senior",
        "mid senior": "mid-senior",
    }
    exp_list = [EXP_MAP.get(e.lower(), e.lower()) for e in exp_list]
    exp_list = [e for e in exp_list if e in ALLOWED_EXP]
    if not exp_list:
        exp_list = ["entry"]

    # Map published_at config to postedLimit format for new actor
    published_at = config.get("published_at", "r604800")
    posted_limit_map = {
        "r86400": "day",
        "r604800": "week",
        "r2592000": "month",
    }
    posted_limit = posted_limit_map.get(published_at, "week")

    run_input = {
        "jobTitles": keywords_list,
        "locations": [config.get("location", "Europe")],
        "maxItems": config.get("max_items", 15),
        # "company": [],
        "workplaceType": wt_list,
        "employmentType": ["full-time"],
        "experienceLevel": exp_list,
        "salary": [],
        "under10Applicants": False,
        "easyApply": False,
        "postedLimit": posted_limit,
        "industryIds": [],
        "sortBy": "date",
    }

    if status_cb:
        status_cb("🚀 Running LinkedIn Jobs scraper...")

    run = client.actor("zn01OAlzP853oqn4Z").call(run_input=run_input)
    dataset_id = run["defaultDatasetId"] if isinstance(run, dict) else getattr(run, "defaultDatasetId", None) or run["defaultDatasetId"]
    raw_results = list(client.dataset(dataset_id).iterate_items())

    if status_cb:
        status_cb(f"✅ Scraped {len(raw_results)} raw jobs")

    extracted = []
    for item in raw_results:
        row = {
            "jobId": item.get("id", ""),
            "jobTitle": item.get("title", ""),
            "jobUrl": item.get("linkedinUrl", ""),
            "jobDescription": item.get("descriptionText", ""),
            "companyName": (item.get("company") or {}).get("name", ""),
            "location": (item.get("location") or {}).get("parsed", {}).get("text", ""),
            "publishedAt": item.get("postedDate", ""),
            "publishedDate": (
                item.get("postedDate", "").split("T")[0]
                if item.get("postedDate")
                else ""
            ),
            "contractType": item.get("employmentType", ""),
            "experienceLevel": item.get("experienceLevel", ""),
            "workType": item.get("workplaceType", ""),
            "sector": (
                (item.get("company") or {})
                    .get("industries", [{}])[0]
                    .get("name", "")
                if (item.get("company") or {}).get("industries")
                else ""
            ),
            "searchString": (item.get("query") or {}).get("search", ""),
            "companyEmployeeCount": (item.get("company") or {}).get("employeeCount", ""),
            "companyDescription": (item.get("company") or {}).get("description", ""),
            "companyUrl": (item.get("company") or {}).get("linkedinUrl", ""),
            "companyWebsite": extract_real_url(
                (item.get("company") or {}).get("website", "")
            ),
        }
        extracted.append(row)

    return extracted


# ── Step 2: Repeatability check ───────────────────────────────

def check_repeatability(extracted: list[dict], status_cb=None) -> list[dict]:
    client = get_client()

    # Build company → unique search strings map
    company_to_titles = {}
    for row in extracted:
        company = row["companyName"]
        title   = row["searchString"] or ""
        if company not in company_to_titles:
            company_to_titles[company] = []
        if title and title not in company_to_titles[company]:
            company_to_titles[company].append(title)

    company_names = list({row["companyName"] for row in extracted if row["companyName"]})

    company_job_titles = {}

    for company in company_names:
        job_titles_for_company = company_to_titles.get(company, [])
        job_title_str = job_titles_for_company[0] if (job_titles_for_company and job_titles_for_company[0]) else ""
        if not job_title_str:
            matching_rows = [r for r in extracted if r.get("companyName") == company]
            if matching_rows:
                job_title_str = matching_rows[0].get("jobTitle", "")

        if status_cb:
            status_cb(f"🔍 Repeatability check: {company}")

        repeat_input = {
            "job_title": job_title_str,
            "location": "",
            "jobs_entries": 15,
            "company_names": [company],
            "start_jobs": 0,
        }

        try:
            repeat_run = client.actor("JkfTWxtpgfvcRQn3p").call(run_input=repeat_input)
            repeat_dataset_id = repeat_run["defaultDatasetId"] if isinstance(repeat_run, dict) else getattr(repeat_run, "defaultDatasetId", None) or repeat_run["defaultDatasetId"]
            items = list(client.dataset(repeat_dataset_id).iterate_items())
            titles = [item.get("job_title") or item.get("jobTitle") or "" for item in items]
            company_job_titles[company] = [t.lower().strip() for t in titles if t]
        except Exception as e:
            if status_cb:
                status_cb(f"⚠️ Repeatability failed for {company}: {e}")
            company_job_titles[company] = []

    # Score each row
    for row in extracted:
        company   = row["companyName"]
        job_title = normalize(row.get("jobTitle") or "")
        titles_list = company_job_titles.get(company, [])
        count = sum(
            1
            for t in titles_list
            if fuzz.token_sort_ratio(
                job_title,
                normalize(t)
            ) >= 80
        )
        if count>0:
            row["Repeatability"] = count-1
        else:
            row["Repeatability"] = count

    return extracted


# ── Full scrape pipeline ───────────────────────────────────────

def run_scraper(config: dict, existing_job_ids: set, status_cb=None) -> list[dict]:
    min_emp = config.get("min_employees", 50)
    max_emp = config.get("max_employees", 1000)

    extracted = scrape_linkedin_jobs(config, status_cb)

    # ✅ Filter duplicates + company size BEFORE repeatability
    pre_filtered = []
    for row in extracted:
        job_id = str(row.get("jobId", ""))
        if job_id in existing_job_ids:
            if status_cb:
                status_cb(f"⏭️ Duplicate skipped: {row.get('jobTitle')} @ {row.get('companyName')}")
            continue
        emp = row.get("companyEmployeeCount", "")
        if not is_company_size_valid(emp, min_emp, max_emp):
            if status_cb:
                status_cb(f"⛔ Size filter: {row.get('companyName')} ({emp})")
            continue
        pre_filtered.append(row)

    if not pre_filtered:
        if status_cb:
            status_cb("⏭️ No jobs passed size/duplicate filter — skipping repeatability")
        return []

    # ✅ Now run repeatability only on jobs that passed filtering
    new_rows = check_repeatability(pre_filtered, status_cb)

    if status_cb:
        status_cb(f"✅ {len(new_rows)} jobs after all filters")

    return new_rows