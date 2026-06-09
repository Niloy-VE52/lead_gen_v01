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

    run_input = {
        "startUrls": [],
        "keyword": config.get("keywords", ["Customer Support Specialist"]),
        "location": config.get("location", "Europe"),
        "distance": "",
        "publishedAt": config.get("published_at", "r604800"),
        "jobType": [],
        "experienceLevel": config.get("experience_levels", ["entry-level"]),
        "workType": config.get("work_types", ["remote"]),
        "salaryBase": "",
        "maxItems": config.get("max_items", 15),
        "saveOnlyUniqueItems": False,
        "cleanDescription": True,
        "enrichCompanyData": True,
    }

    work_type_label = ", ".join(run_input["workType"])

    if status_cb:
        status_cb("🚀 Running LinkedIn Jobs scraper...")

    run = client.actor("Wnbk97HLf3dKIZ8ja").call(run_input=run_input)
    raw_results = list(client.dataset(run["defaultDatasetId"]).iterate_items())

    if status_cb:
        status_cb(f"✅ Scraped {len(raw_results)} raw jobs")

    extracted = []
    for item in raw_results:
        row = {field: item.get(field, "") for field in FIELDS}
        row["companyWebsite"] = extract_real_url(row.get("companyWebsite", ""))
        row["workType"] = work_type_label
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
        job_title_str = job_titles_for_company[0] if job_titles_for_company else ""

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
            items = list(client.dataset(repeat_run["defaultDatasetId"]).iterate_items())
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