import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()

from backend.apify_manager import apify_manager


ACTOR_URL = (
    "https://api.apify.com/v2/acts/"
    "getdataforme~glassdoor-reviews-scraper/"
    "run-sync-get-dataset-items"
)


def get_reviews(company_name: str, status_cb=None) -> str:
    payload = {"Keyword": company_name, "ItemLimit": 5}
    max_attempts = (
        (len(apify_manager.test_keys) + 1)
        if apify_manager.mode == "test" and apify_manager.test_keys
        else 2
    )

    for _ in range(max_attempts):
        try:
            apify_token = apify_manager.get_active_token()
            r = requests.post(
                ACTOR_URL,
                params={"token": apify_token},
                json=payload,
                timeout=60,
            )

            # Auto-failover on quota exhaustion or rate limit
            if r.status_code in (402, 429) and apify_manager.mode == "test" and len(apify_manager.test_keys) > 1:
                apify_manager.mark_current_exhausted(
                    reason=f"quota/limit reached on reviews (HTTP {r.status_code})",
                    status_cb=status_cb,
                )
                continue

            r.raise_for_status()
            reviews = r.json()

            if not reviews:
                return ""

            reviews = sorted(
                reviews,
                key=lambda x: x.get("review_date_time", ""),
                reverse=True,
            )[:5]

            review_strings = []
            for i, review in enumerate(reviews, 1):
                review_str = (
                    f"[Review {i}] "
                    f"Date: {review.get('review_date_time', '')} | "
                    f"Rating: {review.get('rating_overall', '')} | "
                    f"Title: {review.get('job_title', '')} | "
                    f"Summary: {review.get('summary', '')} | "
                    f"Pros: {review.get('pros', '')} | "
                    f"Cons: {review.get('cons', '')}"
                )
                review_strings.append(review_str)

            return " ||| ".join(review_strings)

        except Exception as e:
            err_str = str(e).lower()
            if ("402" in err_str or "quota" in err_str) and apify_manager.mode == "test" and len(apify_manager.test_keys) > 1:
                apify_manager.mark_current_exhausted(
                    reason="quota limit reached on reviews",
                    status_cb=status_cb,
                )
                continue
            print(f"❌ Error fetching reviews for '{company_name}': {e}")
            return ""

    return ""


def enrich_reviews(rows: list[dict], status_cb=None) -> list[dict]:
    """
    Adds 'Reviews' field to each row that doesn't already have one.
    Mutates rows in place and returns them.
    """
    for row in rows:
        company = row.get("companyName", "")
        if not company:
            row["Reviews"] = ""
            continue

        # Skip if already populated
        if row.get("Reviews"):
            continue

        if status_cb:
            status_cb(f"📝 Fetching reviews: {company}")

        reviews_str = get_reviews(company, status_cb=status_cb)
        row["Reviews"] = reviews_str if reviews_str else "NOT_FOUND"

        time.sleep(1)  # rate limit

    return rows
