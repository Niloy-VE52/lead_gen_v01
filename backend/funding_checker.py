import requests
import os


def get_company_domain(company_name: str) -> str | None:
    """Uses Clearbit autocomplete to resolve company name → domain."""
    try:
        response = requests.get(
            "https://autocomplete.clearbit.com/v1/companies/suggest",
            params={"query": company_name},
            timeout=10,
        )
        response.raise_for_status()
        companies = response.json()
        if not companies:
            return None
        return companies[0]["domain"]
    except Exception as e:
        print(f"❌ Clearbit lookup failed for '{company_name}': {e}")
        return None


def get_company_funding(domain: str) -> dict:
    """Uses Apollo.io to fetch funding details for a given domain."""
    apollo_key = os.getenv("APOLLO_API_KEY")
    try:
        response = requests.get(
            "https://api.apollo.io/api/v1/organizations/enrich",
            headers={
                "Cache-Control": "no-cache",
                "Content-Type": "application/json",
                "accept": "application/json",
                "X-Api-Key": apollo_key,
            },
            params={"domain": domain},
            timeout=15,
        )
        response.raise_for_status()
        org = response.json().get("organization", {})

        funding_events = org.get("funding_events", [])
        latest_event = funding_events[0] if funding_events else {}

        amount   = latest_event.get("amount") or ""
        currency = latest_event.get("currency") or ""
        last_amount_concat = f"{amount} {currency}".strip() if amount else "not found"

        return {
            "total_funding":               org.get("total_funding_printed", "") or "not found",
            "latest_funding_round_date":   org.get("latest_funding_round_date", "") or "not found",
            "latest_funding_stage":        org.get("latest_funding_stage", "") or "not found",
            "latest_funding":              last_amount_concat,
        }
    except Exception as e:
        print(f"❌ Apollo lookup failed for domain '{domain}': {e}")
        return {
            "total_funding": "not found",
            "latest_funding_round_date": "not found",
            "latest_funding_stage": "not found",
            "latest_funding": "not found",
        }


def enrich_funding(rows: list[dict], status_cb=None) -> list[dict]:
    """
    Adds funding fields to each row. Deduplicates by company name
    so we don't call the API multiple times for the same company.
    Mutates rows in place and returns them.
    """
    cache: dict[str, dict] = {}

    for row in rows:
        company = row.get("companyName", "")
        if not company:
            _set_empty_funding(row)
            continue

        # Already enriched in this batch
        if company in cache:
            row.update(cache[company])
            continue

        # Already has data from a previous run
        if row.get("latest_funding_stage"):
            cache[company] = {
                "total_funding":             row.get("total_funding", ""),
                "latest_funding_round_date": row.get("latest_funding_round_date", ""),
                "latest_funding_stage":      row.get("latest_funding_stage", ""),
                "latest_funding":            row.get("latest_funding", ""),
            }
            continue

        if status_cb:
            status_cb(f"💰 Fetching funding: {company}")

        # Use companyWebsite domain if available, else Clearbit lookup
        website = row.get("companyWebsite", "")
        domain = _extract_domain(website) if website else get_company_domain(company)

        if domain:
            funding = get_company_funding(domain)
        else:
            if status_cb:
                status_cb(f"⚠️ No domain found for {company}")
            funding = {"total_funding": "not found", "latest_funding_round_date": "not found",
                       "latest_funding_stage": "not found", "latest_funding": "not found"}

        cache[company] = funding
        row.update(funding)

    return rows


def _set_empty_funding(row: dict):
    row.update({
        "total_funding": "not found",
        "latest_funding_round_date": "not found",
        "latest_funding_stage": "not found",
        "latest_funding": "not found",
    })


def _extract_domain(url: str) -> str | None:
    """Extracts bare domain from a URL string."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        domain = parsed.netloc or parsed.path
        domain = domain.replace("www.", "").strip("/")
        return domain if domain else None
    except Exception:
        return None