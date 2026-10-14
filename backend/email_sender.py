import os
import sys
import json
import smtplib
import time
import random
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Ensure project root is in sys.path so 'backend' package imports work from anywhere
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure Windows terminal supports UTF-8 characters without charmap errors
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load environment variables
load_dotenv()


# =============================================================================
# ✍️ [SECTION 1: SENDER IDENTITY & VALUE PROPOSITION]
# =============================================================================
OUR_SERVICE_DESCRIPTION = """
We are an outsourcing and offshoring firm that provides pre-vetted, expert talent tailored 
specifically to your operational, support, and technical needs. 
We offer flexible, cost-effective hourly rates so you only get billed for the exact hours utilized. 
By partnering with us, you completely bypass the slow, expensive hiring process, eliminate 
the heavy fixed costs of maintaining full-time employees, and avoid the recurring overhead 
and headaches of sudden resignations, appraisal cycles, benefits, and employee engagement events.
"""

OUR_VALUE_PROPOSITION = """
- Only pay for what you use with affordable hourly billing (zero bloated full-time payroll)
- Bypass the entire hiring, vetting, and interview pipeline completely
- Zero liability or overhead for appraisals, bonuses, engagement events, or severance
- Seamless on-demand replacement without operational disruption if someone resigns
- Scale your support, operations, or technical capacity up or down instantly
"""

SENDER_NAME = "Sandipan"
SENDER_TITLE = "Outsourcing & Operations"
SENDER_COMPANY = "Offshore Talent Solutions"
SENDER_SIGNATURE = f"""
Best regards,
{SENDER_NAME}
{SENDER_TITLE} | {SENDER_COMPANY}
"""


# =============================================================================
# ⚙️ [SECTION 2: SMTP CONFIGURATION (GMAIL & OUTLOOK)]
# =============================================================================
DEFAULT_SENDER = "annoymous0409@gmail.com"

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", DEFAULT_SENDER)
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD") or os.getenv("GMAIL_APP_PASSWORD", "")

# Safety redirect during testing phase: redirects all outgoing emails to this address.
# When ready for live production outreach, set TEST_EMAIL_OVERRIDE="" in .env
TEST_EMAIL_OVERRIDE = os.getenv("TEST_EMAIL_OVERRIDE", "niloyvetesting54@gmail.com")


# =============================================================================
# 🧩 [SECTION 3: PIPELINE BUILDING BLOCKS]
# =============================================================================

def get_company_context(company_name: str, gc=None) -> dict:
    """Step 1: Gathers background signals (funding, reviews, hiring pain) from sheets."""
    context = {
        "companyName": company_name,
        "sector": "",
        "companyEmployeeCount": "",
        "companyDescription": "",
        "jobTitle": "",
        "jobDescriptionSnippet": "",
        "repeatability": "",
        "fundingStage": "",
        "fundingAmount": "",
        "fundingDate": "",
        "reviewSummary": "",
        "scoreReason": "",
        "decision": "",
        "priority": "",
    }

    if not company_name:
        return context

    try:
        from backend.sheets_helper import (
            get_gc,
            get_or_create_sheet,
            get_all_rows_as_dicts,
            SCRAPED_SHEET_NAME,
            SCORING_SHEET_NAME,
            SCRAPED_HEADERS,
            SCORING_HEADERS,
        )

        if gc is None:
            gc = get_gc()

        target_norm = company_name.strip().lower()

        # Scraped Jobs Sheet
        try:
            _, scraped_ws = get_or_create_sheet(gc, SCRAPED_SHEET_NAME, SCRAPED_HEADERS)
            for row in get_all_rows_as_dicts(scraped_ws):
                if row.get("companyName", "").strip().lower() == target_norm:
                    context["sector"] = row.get("sector", "")
                    context["companyEmployeeCount"] = row.get("companyEmployeeCount", "")
                    context["companyDescription"] = row.get("companyDescription", "")
                    context["jobTitle"] = row.get("jobTitle", "")
                    context["jobDescriptionSnippet"] = str(row.get("jobDescription", ""))[:400]
                    context["repeatability"] = row.get("Repeatability", "")
                    context["fundingStage"] = row.get("latest_funding_stage", "")
                    context["fundingAmount"] = row.get("latest_funding") or row.get("total_funding", "")
                    context["fundingDate"] = row.get("latest_funding_round_date", "")
                    context["reviewSummary"] = str(row.get("Reviews", ""))[:400]
                    break
        except Exception as e:
            print(f"   ⚠️ Could not read scraped sheet context: {e}")

        # Scored Lead Sheet
        try:
            _, scoring_ws = get_or_create_sheet(gc, SCORING_SHEET_NAME, SCORING_HEADERS)
            for row in get_all_rows_as_dicts(scoring_ws):
                if row.get("companyName", "").strip().lower() == target_norm:
                    context["scoreReason"] = row.get("reason", "")
                    context["decision"] = row.get("decision", "")
                    context["priority"] = row.get("priority", "")
                    break
        except Exception as e:
            print(f"   ⚠️ Could not read scoring sheet context: {e}")

    except Exception as e:
        print(f"   ⚠️ Google Sheet context lookup skipped: {e}")

    return context


def build_prompt(contact: dict, context: dict) -> str:
    """Step 2: Formulates a tailored B2B cold email prompt."""
    person_name = contact.get("personName") or "there"
    designation = contact.get("designation") or "Leadership"
    company_name = contact.get("companyName") or "your company"

    return f"""You are an elite B2B sales development copywriter. Write a highly personalized, natural 1-on-1 cold email to a decision-maker.

--- 1. ABOUT US ---
What we do:
{OUR_SERVICE_DESCRIPTION.strip()}

Core Value Proposition:
{OUR_VALUE_PROPOSITION.strip()}

Sender Signature:
{SENDER_SIGNATURE.strip()}

--- 2. TARGET LEAD ---
Name: {person_name}
Title: {designation}
Company: {company_name}

--- 3. COMPANY CONTEXT & SIGNALS ---
Industry: {context.get('sector') or 'Tech / Growth'}
Company Size: {context.get('companyEmployeeCount') or 'Growing team'}
Overview: {context.get('companyDescription') or 'N/A'}
Funding: Stage={context.get('fundingStage') or 'N/A'}, Amount={context.get('fundingAmount') or 'N/A'}, Date={context.get('fundingDate') or 'N/A'}
Hiring Need: Role={context.get('jobTitle') or 'Support / Operations'}, Reposts={context.get('repeatability') or '0'}
Job Highlights: {context.get('jobDescriptionSnippet') or 'N/A'}
Reviews Sentiment: {context.get('reviewSummary') or 'N/A'}
Scoring Reason: {context.get('scoreReason') or 'Operational growth fit.'}

--- 4. COPYWRITING RULES ---
1. Subject line: 3 to 6 words maximum. Lowercase or sentence case. No spam words.
2. Body length: Keep it short (70 to 110 words total).
3. The Opening Hook: Acknowledge their company, recent growth, or hiring priorities.
4. The Bridge: Connect their likely scaling/workload pressure to how our pre-vetted hourly experts remove hiring headaches and overhead.
5. The Call to Action (CTA): Low friction (e.g. "Open to a brief 5-min chat next week?").
6. Tone: Direct, warm, conversational peer. Avoid corporate fluff or hype.

--- 5. REQUIRED JSON OUTPUT ---
Return ONLY a valid JSON object:
{{
  "subject": "<3-6 words subject line>",
  "opening_hook": "<1 sentence personalized observation>",
  "pain_point_bridge": "<1-2 sentences connecting pain to our solution>",
  "value_proposition": "<1 sentence clear benefit>",
  "call_to_action": "<1 short low-friction ask>",
  "full_body": "<Complete email text ready to send>"
}}
"""


def generate_email_content(prompt: str) -> dict:
    """Step 3: Calls LLM (OpenAI with Groq fallback) to generate the subject & body."""
    content_text = ""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model_name = os.getenv("EMAIL_LLM_MODEL", "gpt-4o-mini")

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a professional B2B cold email copywriter. Always output valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        content_text = response.choices[0].message.content

    except Exception as llm_err:
        print(f"   ⚠️ OpenAI call failed ({llm_err}), trying Groq fallback...")
        from groq import Groq
        groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a professional B2B cold email copywriter. Always output valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
        )
        content_text = response.choices[0].message.content

    cleaned = content_text.strip().replace("```json", "").replace("```", "").strip()
    data = json.loads(cleaned)

    subject = data.get("subject", "Connecting regarding operations")
    full_body = data.get("full_body") or (
        f"{data.get('opening_hook', '')}\n\n"
        f"{data.get('pain_point_bridge', '')}\n\n"
        f"{data.get('value_proposition', '')}\n\n"
        f"{data.get('call_to_action', '')}\n\n"
        f"{SENDER_SIGNATURE}"
    )

    return {"subject": subject, "body": full_body, "meta": data}


def send_email(to_email: str, subject: str, body: str, is_html: bool = False) -> bool:
    """Step 4: Dispatches email via standard SMTP."""
    if not SMTP_PASSWORD:
        print("   ⚠️ SMTP_PASSWORD or GMAIL_APP_PASSWORD is not set in your .env file.")
        return False

    if not to_email or "@" not in to_email:
        print(f"   ⚠️ Invalid recipient address: '{to_email}'")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html" if is_html else "plain"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        print(f"   ✅ Delivered to {to_email} via {SMTP_HOST}")
        return True
    except Exception as e:
        print(f"   ❌ Delivery failed for {to_email}: {e}")
        return False


# =============================================================================
# 🔄 [SECTION 4: THE CORE EMAIL PIPELINE]
# =============================================================================

def run_email_pipeline(contact: dict, dry_run: bool = False, gc=None) -> dict:
    """
    Unified pipeline execution for a single lead:
    1. get_company_context()  -> Gather enriched company signals
    2. build_prompt()          -> Assemble tailored prompt
    3. generate_email_content()-> Call LLM for subject and body
    4. send_email()            -> Dispatch via SMTP (or preview if dry_run)
    """
    person_name = contact.get("personName", "Lead")
    company_name = contact.get("companyName", "Company")
    raw_email = contact.get("email", "").strip()

    # Safety override during testing
    send_recipient = TEST_EMAIL_OVERRIDE.strip() if TEST_EMAIL_OVERRIDE else raw_email

    print(f"\n{'='*60}")
    print(f"🚀 [Email Pipeline] Processing: {person_name} @ {company_name}")
    print(f"   Original Prospect Email: {raw_email}")
    if send_recipient != raw_email:
        print(f"   🔒 Safety Redirect Active: Sending to {send_recipient}")
    print(f"   Mode: {'🧪 DRY RUN' if dry_run else '🚀 LIVE SEND'}")
    print(f"{'='*60}")

    if not send_recipient or "@" not in send_recipient:
        print(f"   ⚠️ Aborted: Missing or invalid email for {person_name}")
        return {"success": False, "error": "Invalid email"}

    # Step 1: Context Gathering
    print("   [1/4] Gathering company context...")
    context = get_company_context(company_name, gc=gc)

    # Step 2: Prompt Formulation
    print("   [2/4] Formulating tailored prompt...")
    prompt = build_prompt(contact, context)

    # Step 3: LLM Generation
    print("   [3/4] Generating personalized email copy...")
    content = generate_email_content(prompt)
    subject = content["subject"]
    body = content["body"]

    print(f"\n   📧 Subject: {subject}")
    print(f"   📝 Body:\n{'-'*40}\n{body}\n{'-'*40}\n")

    # Step 4: Dispatch / Delivery
    if dry_run:
        print("   🧪 [DRY RUN] Email generated successfully. SMTP dispatch skipped.")
        return {
            "success": True,
            "subject": subject,
            "body": body,
            "recipient": send_recipient,
            "original_email": raw_email,
            "mode": "dry_run",
        }

    print(f"   [4/4] Sending email via SMTP to {send_recipient}...")
    sent = send_email(to_email=send_recipient, subject=subject, body=body)
    return {
        "success": sent,
        "subject": subject,
        "body": body,
        "recipient": send_recipient,
        "original_email": raw_email,
        "mode": "live",
    }


# =============================================================================
# 🎯 [SECTION 5: THE 3 RUNNER INTERFACES]
# =============================================================================

def send_to_contact(contact: dict, dry_run: bool = False, gc=None) -> dict:
    """1. Executes the pipeline ONCE for a single contact."""
    return run_email_pipeline(contact, dry_run=dry_run, gc=gc)


def send_all_saved_leads(dry_run: bool = False, delay_range: tuple = (35, 75)):
    """
    2. Reads all leads from 'Email_saver' sheet and executes the pipeline in a loop
       with a pacing delay to prevent inbox spam throttling.
    """
    try:
        from backend.sheets_helper import get_gc, get_email_saver_entries
        gc = get_gc()
        leads = get_email_saver_entries(gc)

        # Filter out header rows and invalid rows
        valid_leads = [
            l for l in leads
            if l.get("email") and "@" in l.get("email") and l.get("email").strip().lower() != "email"
        ]

        if not valid_leads:
            print("ℹ️ No valid leads found in 'Email_saver' sheet.")
            return

        print(f"\n📋 Loaded {len(valid_leads)} valid leads from 'Email_saver' sheet.")
        print(f"Mode: {'🧪 DRY RUN' if dry_run else '🚀 LIVE SENDING'}")

        for idx, contact in enumerate(valid_leads, start=1):
            print(f"\n>>> [{idx}/{len(valid_leads)}] Starting lead: {contact.get('personName')}")
            result = run_email_pipeline(contact, dry_run=dry_run, gc=gc)

            if result.get("success") and not dry_run and idx < len(valid_leads):
                wait_sec = random.randint(*delay_range)
                print(f"⏳ Pacing delay: waiting {wait_sec}s before next email...")
                time.sleep(wait_sec)

        print("\n🎉 Batch sending finished!")

    except Exception as e:
        print(f"❌ Batch runner error: {e}")


def test_stored_lead(send_to_email: str = "niloyvetesting54@gmail.com", dry_run: bool = True, company_name: str = None):
    """
    3. Picks the LAST saved lead from 'Email_saver' sheet, swaps the email
       to your test email, and executes the pipeline.
    """
    try:
        from backend.sheets_helper import get_gc, get_email_saver_entries
        gc = get_gc()
        leads = get_email_saver_entries(gc)

        # Filter valid leads
        valid_leads = [
            l for l in leads
            if l.get("email") and "@" in l.get("email") and l.get("email").strip().lower() != "email"
        ]

        if not valid_leads:
            print("❌ No valid leads found in 'Email_saver' sheet.")
            return

        # Pick specified company or the LAST saved lead
        target = None
        if company_name:
            target = next((l for l in valid_leads if company_name.lower() in l.get("companyName", "").lower()), None)
            if not target:
                print(f"⚠️ Company '{company_name}' not found. Defaulting to last saved lead.")
                target = valid_leads[-1]
        else:
            target = valid_leads[-1]  # ← Picks the latest / last saved lead

        print(f"\n🔍 Picked Last Saved Lead from Sheet:")
        print(f"   Company: {target.get('companyName')}")
        print(f"   Person:  {target.get('personName')} ({target.get('designation')})")
        print(f"   Original Prospect Email: {target.get('email')}")
        print(f"   🔒 Safety Swap: Routing destination to {send_to_email}")

        # Swap email to safety test address
        test_contact = dict(target)
        test_contact["email"] = send_to_email

        # Run pipeline
        return run_email_pipeline(test_contact, dry_run=dry_run, gc=gc)

    except Exception as e:
        print(f"❌ Error in test runner: {e}")


# =============================================================================
# 🚀 [SECTION 6: STANDALONE TEST EXECUTION]
# =============================================================================
if __name__ == "__main__":
    print("=" * 65)
    print(f"📬 Automated B2B Email Pipeline")
    print(f"From (Sender): {SMTP_USER} | Host: {SMTP_HOST}:{SMTP_PORT}")
    print("=" * 65)

    # By default, runs test_stored_lead() on the LAST saved lead in dry_run mode.
    # Set dry_run=False once SMTP_PASSWORD is added to .env to deliver live.
    test_stored_lead(
        send_to_email=TEST_EMAIL_OVERRIDE,
        dry_run=False
    )
