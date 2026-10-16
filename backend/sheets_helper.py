import gspread
from google.oauth2.service_account import Credentials
import os
import json

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SCRAPED_SHEET_NAME  = "Job_Scaped_v7"
SCORING_SHEET_NAME  = "Scored_Lead_V7"
EMAIL_SAVER = "Email_saver"

EMAIL_SAVER_HEADERS = [
    "companyName", "personName", "email", "designation", "linkedinUrl", "addedAt", "subject", "emailBody", "outreachStatus", "sentAt"
]

# ── Column definitions ─────────────────────────────────────────
SCRAPED_HEADERS = [
    "jobId", "jobTitle", "jobUrl", "jobDescription",
    "companyName", "location", "publishedAt", "publishedDate",
    "contractType", "experienceLevel", "workType",
    "sector", "searchString", "companyEmployeeCount",
    "companyDescription",
    "companyUrl", "companyWebsite",
    "Repeatability",
    "Reviews",
    "total_funding", "latest_funding_round_date",
    "latest_funding_stage", "latest_funding",
]

SCORING_HEADERS = [
    "jobTitle", "jobUrl", "companyName", "location",
    "workType", "experienceLevel", "sector",
    "companyEmployeeCount","Execution Signal", "Hiring Intent", "Company Fit",
    "Remote Readiness", "Buying Trigger", "Repost Bonus",
    "Enrichment Confidence", "total_score", "decision", "priority", "reason", "Date"
]


def get_gc():
    creds_info = json.loads(os.environ["GOOGLE_CREDENTIALS_JSON"])
    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=SCOPES,
    )
    return gspread.authorize(creds)


def get_or_create_sheet(gc, sheet_name: str, headers: list):
    try:
        spreadsheet = gc.open(sheet_name)
        ws = spreadsheet.sheet1
        existing = ws.get_all_values()

        format_fn = format_email_saver_sheet if sheet_name == EMAIL_SAVER else format_header_row

        if not existing:
            # Completely empty — write header
            ws.append_row(headers, value_input_option="RAW")
            print(f"   📋 Header written to empty sheet: {sheet_name}")
            format_fn(ws)

        else:
            row0_cleaned = [str(c).strip() for c in existing[0] if str(c).strip()]
            if not row0_cleaned:
                ws.update(values=[headers], range_name="A1")
                format_fn(ws)
            elif row0_cleaned == headers:
                pass
            else:
                matches = sum(1 for h in headers if h in row0_cleaned)
                if matches >= 2:
                    # First row is already a header row. Update in place instead of inserting duplicates!
                    ws.update(values=[headers], range_name="A1")
                    format_fn(ws)
                else:
                    # Header is genuinely missing (first row is real data) — insert at row 1
                    ws.insert_row(headers, index=1, value_input_option="RAW")
                    print(f"   ⚠️ Header was missing in {sheet_name} — inserted at row 1")
                    format_fn(ws)

        return spreadsheet, ws

    except gspread.SpreadsheetNotFound:
        spreadsheet = gc.create(sheet_name)
        ws = spreadsheet.sheet1
        ws.append_row(headers, value_input_option="RAW")
        format_fn = format_email_saver_sheet if sheet_name == EMAIL_SAVER else format_header_row
        format_fn(ws)
        print(f"   🆕 Created new sheet: {sheet_name}")
        return spreadsheet, ws


import time

def format_header_row(ws):
    """Format row 1 with yellow background, bold font, and freeze row 1."""
    for attempt in range(3):
        try:
            requests = [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": ws.id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 1.0,
                                    "green": 0.95,
                                    "blue": 0.25
                                },
                                "textFormat": {
                                    "bold": True,
                                    "fontSize": 11,
                                    "foregroundColor": {"red": 0.0, "green": 0.0, "blue": 0.0}
                                },
                                "verticalAlignment": "MIDDLE",
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment)"
                    }
                },
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": ws.id,
                            "gridProperties": {
                                "frozenRowCount": 1
                            }
                        },
                        "fields": "gridProperties.frozenRowCount"
                    }
                }
            ]

            ws.spreadsheet.batch_update({"requests": requests})
            return

        except Exception as e:
            if attempt < 2:
                time.sleep(5)
            else:
                raise


def format_email_saver_sheet(ws):
    """Format Email_saver: Row 1 is yellow header, rows 2+ are clean white, regular font, and clipped row height."""
    for attempt in range(3):
        try:
            requests = [
                # 1. Format all data rows (Row 2 to 1000): white background, regular 10pt font, clipped
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": ws.id,
                            "startRowIndex": 1,
                            "endRowIndex": 1000,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                                "textFormat": {
                                    "bold": False,
                                    "fontSize": 10,
                                    "foregroundColor": {"red": 0.1, "green": 0.1, "blue": 0.1}
                                },
                                "verticalAlignment": "MIDDLE",
                                "wrapStrategy": "CLIP"
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment,wrapStrategy)"
                    }
                },
                # 2. Format Header Row (Row 1): Yellow, bold, 11pt, vertically middle
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": ws.id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {"red": 1.0, "green": 0.95, "blue": 0.25},
                                "textFormat": {
                                    "bold": True,
                                    "fontSize": 11,
                                    "foregroundColor": {"red": 0.0, "green": 0.0, "blue": 0.0}
                                },
                                "verticalAlignment": "MIDDLE",
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment)"
                    }
                },
                # 3. Freeze Header Row
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": ws.id,
                            "gridProperties": {
                                "frozenRowCount": 1
                            }
                        },
                        "fields": "gridProperties.frozenRowCount"
                    }
                }
            ]
            ws.spreadsheet.batch_update({"requests": requests})
            return
        except Exception as e:
            if attempt < 2:
                time.sleep(5)
            else:
                print(f"   ⚠️ Could not format email saver sheet: {e}")


def format_keep_rows_in_sheet(ws):
    """Find all rows with decision == 'KEEP' in ws and format background color to #b8d7aa."""
    for attempt in range(3):
        try:
            all_values = ws.get_all_values()
            if len(all_values) <= 1:
                return
            header = all_values[0]
            try:
                decision_col = header.index("decision")
            except ValueError:
                return

            keep_row_indices = []
            for i, row in enumerate(all_values[1:], start=2):
                if len(row) > decision_col:
                    val = str(row[decision_col]).strip().upper()
                    if val == "KEEP":
                        keep_row_indices.append(i)

            if not keep_row_indices:
                return

            r = 184 / 255.0
            g = 215 / 255.0
            b = 170 / 255.0

            requests = [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": ws.id,
                            "startRowIndex": row_idx - 1,
                            "endRowIndex": row_idx,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": r,
                                    "green": g,
                                    "blue": b,
                                }
                            }
                        },
                        "fields": "userEnteredFormat.backgroundColor",
                    }
                }
                for row_idx in keep_row_indices
            ]

            ws.spreadsheet.batch_update({"requests": requests})
            print(f"   🎨 Highlighted {len(keep_row_indices)} KEEP rows with #b8d7aa")
            return
        except Exception as e:
            if attempt < 2:
                time.sleep(5)
            else:
                print(f"   ⚠️ Failed to format KEEP rows: {e}")



def get_existing_job_ids(ws) -> set:
    all_values = ws.get_all_values()
    if len(all_values) <= 1:
        return set()
    header = all_values[0]
    try:
        job_id_col = header.index("jobId")
    except ValueError:
        return set()
    return {
        row[job_id_col].lstrip("'").strip()   # ← strip leading apostrophe
        for row in all_values[1:]
        if len(row) > job_id_col
    }


def get_existing_companies(ws) -> set:
    all_values = ws.get_all_values()
    if len(all_values) <= 1:
        return set()
    header = all_values[0]
    try:
        company_col = header.index("companyName")
    except ValueError:
        return set()
    return {
        row[company_col].lstrip("'").strip().lower()
        for row in all_values[1:]
        if len(row) > company_col and row[company_col].strip()
    }



def get_all_rows_as_dicts(ws) -> list[dict]:
    all_values = ws.get_all_values()
    if len(all_values) <= 1:
        return []
    header = all_values[0]
    rows = []
    for row in all_values[1:]:
        d = {}
        for i, h in enumerate(header):
            val = row[i] if i < len(row) else ""
            # Strip leading apostrophe Google Sheets adds to numeric-looking strings
            if isinstance(val, str):
                val = val.lstrip("'").strip()
            d[h] = val
        rows.append(d)
    return rows


def append_rows_safe(ws, rows: list[list], headers: list):
    import time
    if not rows:
        return
    for attempt in range(3):
        try:
            ws.append_rows(rows, value_input_option="RAW")
            return
        except Exception as e:
            if attempt < 2:
                print(f"   ⚠️ Sheet write failed (attempt {attempt+1}), retrying in 5s... {e}")
                time.sleep(5)
            else:
                raise


def upsert_scoring_row(ws, headers: list, score_data: dict):
    all_values = ws.get_all_values()
    if not all_values:
        ws.append_row(headers)
        format_header_row(ws)
        all_values = [headers]

    header = all_values[0]
    try:
        job_id_col = header.index("jobId")
    except ValueError:
        job_id_col = 0

    job_id = str(score_data.get("jobId", "")).lstrip("'").strip()  # ← clean
    row_data = [score_data.get(h, "") for h in header]

    for i, row in enumerate(all_values[1:], start=2):
        existing_id = row[job_id_col].lstrip("'").strip() if len(row) > job_id_col else ""
        if existing_id == job_id:
            ws.update(f"A{i}", [row_data])
            return

    ws.append_row(row_data, value_input_option="RAW")


def get_keep_companies(gc):
    """Read scoring sheet, filter KEEP decisions, join with scraped sheet for companyUrl."""
    # Open scoring sheet
    _, score_ws = get_or_create_sheet(gc, SCORING_SHEET_NAME, SCORING_HEADERS)
    score_rows = get_all_rows_as_dicts(score_ws)

    keep_rows = [r for r in score_rows if r.get("decision", "").strip().upper() == "KEEP"]

    if not keep_rows:
        return []

    # Open scraped sheet to get companyUrl (LinkedIn company page)
    _, scraped_ws = get_or_create_sheet(gc, SCRAPED_SHEET_NAME, SCRAPED_HEADERS)
    scraped_rows = get_all_rows_as_dicts(scraped_ws)

    # Build company name → companyUrl mapping
    company_url_map = {}
    for row in scraped_rows:
        name = row.get("companyName", "").strip()
        url = row.get("companyUrl", "").strip()
        if name and url and name not in company_url_map:
            company_url_map[name] = url

    # Deduplicate by company name - reverse so newest KEEP entries come first (stack order)
    seen = set()
    results = []
    for row in reversed(keep_rows):
        company = row.get("companyName", "").strip()
        if not company or company in seen:
            continue
        seen.add(company)
        results.append({
            "companyName": company,
            "companyUrl": company_url_map.get(company, ""),
            "location": row.get("location", ""),
            "sector": row.get("sector", ""),
            "priority": row.get("priority", ""),
        })

    return results


def upsert_email_saver_row(gc, row_data: dict):
    """
    Upsert a contact to the EMAIL_SAVER sheet:
    - Finds existing row matching 'email' (or 'companyName' + 'personName' fallback).
    - If found, updates the specified fields in-place on that exact row without creating a duplicate.
    - If not found, appends a new row.
    """
    from datetime import datetime
    _, ws = get_or_create_sheet(gc, EMAIL_SAVER, EMAIL_SAVER_HEADERS)
    all_values = ws.get_all_values()
    if not all_values:
        ws.append_row(EMAIL_SAVER_HEADERS, value_input_option="RAW")
        format_email_saver_sheet(ws)
        all_values = [EMAIL_SAVER_HEADERS]

    header = all_values[0]

    email_col = header.index("email") if "email" in header else -1
    company_col = header.index("companyName") if "companyName" in header else -1
    person_col = header.index("personName") if "personName" in header else -1

    target_email = str(row_data.get("email", "")).strip().lower()
    target_company = str(row_data.get("companyName", "")).strip().lower()
    target_person = str(row_data.get("personName", "")).strip().lower()

    matched_row_idx = None
    for i, row in enumerate(all_values[1:], start=2):
        row_email = row[email_col].strip().lower() if email_col >= 0 and len(row) > email_col else ""
        row_company = row[company_col].strip().lower() if company_col >= 0 and len(row) > company_col else ""
        row_person = row[person_col].strip().lower() if person_col >= 0 and len(row) > person_col else ""

        # Match primarily by email
        if target_email and "@" in target_email and row_email == target_email:
            matched_row_idx = i
            break
        # Fallback match by companyName + personName
        if target_company and target_person and row_company == target_company and row_person == target_person:
            matched_row_idx = i
            break

    if matched_row_idx:
        existing_row = all_values[matched_row_idx - 1]
        updated_row = list(existing_row)
        while len(updated_row) < len(header):
            updated_row.append("")

        for col_idx, h in enumerate(header):
            if h in row_data:
                new_val = row_data[h]
                if new_val != "" or h in ["outreachStatus", "subject", "emailBody", "sentAt"]:
                    updated_row[col_idx] = str(new_val)

        ws.update(values=[updated_row], range_name=f"A{matched_row_idx}")
        print(f"   [UPDATE] Updated existing lead at row {matched_row_idx} in {EMAIL_SAVER}: {target_email or target_person}")
        return matched_row_idx
    else:
        new_row_dict = {
            "companyName": row_data.get("companyName", ""),
            "personName": row_data.get("personName", ""),
            "email": row_data.get("email", ""),
            "designation": row_data.get("designation", ""),
            "linkedinUrl": row_data.get("linkedinUrl", ""),
            "addedAt": row_data.get("addedAt") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "subject": row_data.get("subject", ""),
            "emailBody": row_data.get("emailBody", ""),
            "outreachStatus": row_data.get("outreachStatus", "PENDING"),
            "sentAt": row_data.get("sentAt", ""),
        }
        row = [str(new_row_dict.get(h, "")) for h in header]
        new_row_idx = len(all_values) + 1
        append_rows_safe(ws, [row], header)

        # Ensure the newly added row has clean white formatting and clipped text wrap
        try:
            ws.spreadsheet.batch_update({
                "requests": [{
                    "repeatCell": {
                        "range": {
                            "sheetId": ws.id,
                            "startRowIndex": new_row_idx - 1,
                            "endRowIndex": new_row_idx,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0},
                                "textFormat": {
                                    "bold": False,
                                    "fontSize": 10,
                                    "foregroundColor": {"red": 0.1, "green": 0.1, "blue": 0.1}
                                },
                                "verticalAlignment": "MIDDLE",
                                "wrapStrategy": "CLIP"
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment,wrapStrategy)"
                    }
                }]
            })
        except Exception:
            pass

        print(f"   [INSERT] Added new lead to {EMAIL_SAVER}: {target_person} ({target_email})")
        return new_row_idx


def update_email_outreach_status(gc, email: str, subject: str, email_body: str, status: str, sent_at: str = ""):
    """Update outreach columns (subject, emailBody, outreachStatus, sentAt) for an existing lead by email."""
    return upsert_email_saver_row(gc, {
        "email": email,
        "subject": subject,
        "emailBody": email_body,
        "outreachStatus": status,
        "sentAt": sent_at,
    })


def append_to_email_saver(gc, row_data: dict):
    """Upsert a contact to the EMAIL_SAVER sheet (edits existing row if present, appends otherwise)."""
    return upsert_email_saver_row(gc, row_data)


def get_email_saver_entries(gc):
    """Read all existing EMAIL_SAVER entries."""
    _, ws = get_or_create_sheet(gc, EMAIL_SAVER, EMAIL_SAVER_HEADERS)
    return get_all_rows_as_dicts(ws)