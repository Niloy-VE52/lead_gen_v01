import os
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

from backend.apify_manager import apify_manager


def get_client() -> ApifyClient:
    return apify_manager.get_client()


def get_email_from_linkedin_profile(profile_url: str, status_cb=None) -> list[dict]:
    """
    Extracts email address from a LinkedIn profile URL using actor bfH8Ermocz8oYKQVO.
    Wrapped with apify_manager for zero-downtime auto-failover.
    """
    if not profile_url or not str(profile_url).strip():
        return []

    run_input = {"urls": [profile_url.strip()]}
    return apify_manager.call_actor(
        "bfH8Ermocz8oYKQVO",
        run_input=run_input,
        status_cb=status_cb,
    )


def get_decisionmakers_linkedin(company_url: str, status_cb=None) -> list[dict]:
    """
    Finds decision-maker profiles at a target company LinkedIn URL using actor Vb6LZkh4EqRlR0Ka9.
    Wrapped with apify_manager for zero-downtime auto-failover.
    """
    if not company_url or not str(company_url).strip():
        return []

    run_input = {
        "companies": [company_url.strip()],
        "jobTitles": [
            "CEO",
            "President",
            "Founder",
            "Vice President",
            "Co-Founder",
            "Director of Talent Acquisition",
            "CRO",
            "Chief Revenue Officer",
            "Director of operations",
            "Managing Director",
            "Chief People officer",
            "COO",
            "Chief Operating Officer",
            "HR head",
            "Head of Business Operations",
        ],
        "maxItems": 5,
        "profileScraperMode": "Short ($4 per 1k)",
        "recentlyChangedJobs": False,
        "seniorityLevelIds": [
            "310",
            "300",
            "220",
            "320",
            "210",
        ],
    }

    return apify_manager.call_actor(
        "Vb6LZkh4EqRlR0Ka9",
        run_input=run_input,
        status_cb=status_cb,
    )
