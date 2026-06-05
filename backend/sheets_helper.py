import gspread
from google.oauth2.service_account import Credentials
import os
import json

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SCRAPED_SHEET_NAME  = "Scaped_v6"
SCORING_SHEET_NAME  = "Score_Listing_v6"

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
    "Enrichment Confidence", "total_score", "decision", "priority", "reason"
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

        if not existing:
            # Completely empty — write header
            ws.append_row(headers, value_input_option="RAW")
            print(f"   📋 Header written to empty sheet: {sheet_name}")
            format_header_row(ws)

        elif existing[0] != headers:
            # First row is not the header — insert it
            ws.insert_row(headers, index=1, value_input_option="RAW")
            print(f"   ⚠️ Header was missing in {sheet_name} — inserted at row 1")
            format_header_row(ws)
        else:
            # Header already exists, format it anyway
            pass

        return spreadsheet, ws

    except gspread.SpreadsheetNotFound:
        spreadsheet = gc.create(sheet_name)
        ws = spreadsheet.sheet1
        ws.append_row(headers, value_input_option="RAW")
        print(f"   🆕 Created new sheet: {sheet_name}")
        return spreadsheet, ws


import time

def format_header_row(ws):
    for attempt in range(3):
        try:
            num_cols = len(ws.row_values(1))

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
                                    "green": 1.0,
                                    "blue": 0.0
                                },
                                "textFormat": {
                                    "bold": True,
                                    "fontSize": 16
                                }
                            }
                        },
                        "fields": "userEnteredFormat"
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