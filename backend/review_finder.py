import requests
import os
import time


ACTOR_URL = (
    "https://api.apify.com/v2/acts/"
    "getdataforme~glassdoor-reviews-scraper/"
    "run-sync-get-dataset-items"
)


def get_reviews(company_name: str) -> str:
    """Fetches up to 5 Glassdoor reviews and returns them as a concatenated string."""
    apify_token = os.getenv("APIFY_KEY")
    try:
        payload = {"Keyword": company_name, "ItemLimit": 5}
        r = requests.post(
            ACTOR_URL,
            params={"token": apify_token},
            json=payload,
            timeout=60,
        )
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
        print(f"❌ Error fetching reviews for '{company_name}': {e}")
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

        reviews_str = get_reviews(company)
        row["Reviews"] = reviews_str if reviews_str else "NOT_FOUND"

        time.sleep(1)  # rate limit

    return rows