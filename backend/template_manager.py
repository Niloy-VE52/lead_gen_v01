import os
import json
from pathlib import Path
from datetime import datetime

TEMPLATE_FILE = Path(__file__).resolve().parent / "email_template.json"

DEFAULT_TEMPLATE = {
    "sender_name": "Sandipan Sarkar",
    "sender_title": "Outsourcing & Operations",
    "sender_company": "Virtual Employee",
    "subject_instruction": "3 to 6 words maximum. Lowercase or sentence case. No spam words (e.g. Scaling support at {company_name}).",
    "value_proposition": "We provide dedicated, pre-vetted remote talent and support specialists tailored specifically to fast-growing companies, eliminating slow hiring bottlenecks, recruitment fees, and overhead of full-time staffing.",
    "closing_body": """Free Trial and Candidate Selection
To help you make an informed decision, we would be happy to offer a free trial with a suitable in-house professional. This will allow you to evaluate their technical expertise, communication, collaboration, and overall fit with your team before making any commitment.

You can also explore our [Virtual Employee Candidate Trial Portal](https://trials.virtualemployee.com/v2?utm_source=api&utm_medium=automation&utm_campaign=api_automation) to:
• Browse available candidates and filter them by domain and skill set.
• Review candidate profiles and resumes.
• Select the professional who best matches your requirements.
• Start a free trial and evaluate the engagement firsthand.

If you're open to exploring this option, I'd be happy to arrange a short call to understand your support requirements or share a few relevant candidate profiles for your review.

We look forward to the opportunity to support {company_name} in finding the right talent and building a scalable, cost-effective support team.

Best regards,
{sender_name}
{sender_title} | {sender_company}""",
    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}


def get_template() -> dict:
    """Retrieve the currently active email template. Falls back to default if file doesn't exist."""
    if TEMPLATE_FILE.exists():
        try:
            with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Ensure all default keys exist
                merged = {**DEFAULT_TEMPLATE, **data}
                return merged
        except Exception as e:
            print(f"⚠️ Error reading {TEMPLATE_FILE}: {e}. Returning default template.")
            return DEFAULT_TEMPLATE.copy()
    return DEFAULT_TEMPLATE.copy()


def save_template(new_template: dict) -> dict:
    """Save the customized email template to disk."""
    current = get_template()
    current.update({
        "sender_name": str(new_template.get("sender_name", current["sender_name"])).strip(),
        "sender_title": str(new_template.get("sender_title", current["sender_title"])).strip(),
        "sender_company": str(new_template.get("sender_company", current["sender_company"])).strip(),
        "subject_instruction": str(new_template.get("subject_instruction", current["subject_instruction"])).strip(),
        "value_proposition": str(new_template.get("value_proposition", current["value_proposition"])).strip(),
        "closing_body": str(new_template.get("closing_body", current["closing_body"])).strip(),
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2, ensure_ascii=False)

    return current


def reset_template() -> dict:
    """Reset the email template back to the default original template."""
    default_copy = DEFAULT_TEMPLATE.copy()
    default_copy["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
        json.dump(default_copy, f, indent=2, ensure_ascii=False)
    return default_copy
