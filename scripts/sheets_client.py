import os
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

KEY_PATH = os.getenv(
    "GOOGLE_SERVICE_ACCOUNT_KEY_PATH",
    "/Users/mattaustin/Documents/Rev-Ops-CommandCenter/revops-command-center-499414-7f64e03b383c.json",
)

SHEET_ID = os.getenv(
    "GOOGLE_SHEET_ID",
    "1d3QJCXcTNwWOI3xIAqPJ4pvx0AhdyzKk3NpK6mvKVUQ",
)

_client = None
_spreadsheet = None


def get_client():
    global _client
    if _client is None:
        import json as _json
        sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        if sa_json:
            info = _json.loads(sa_json)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        else:
            creds = Credentials.from_service_account_file(KEY_PATH, scopes=SCOPES)
        _client = gspread.authorize(creds)
    return _client


def get_spreadsheet():
    global _spreadsheet
    if _spreadsheet is None:
        _spreadsheet = get_client().open_by_key(SHEET_ID)
    return _spreadsheet


def get_sheet(tab_name):
    return get_spreadsheet().worksheet(tab_name)


def get_or_create_sheet(tab_name, rows=1000, cols=26):
    ss = get_spreadsheet()
    try:
        return ss.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        return ss.add_worksheet(title=tab_name, rows=rows, cols=cols)


def get_all_projects():
    ws = get_sheet("projects")
    records = ws.get_all_records(head=1)
    for i, record in enumerate(records):
        record["_row"] = i + 2  # row 1 is header; first data row is 2
    return records


def update_project_fields(row_number, updates):
    ws = get_sheet("projects")
    headers = ws.row_values(1)
    cell_updates = []
    for col_name, value in updates.items():
        if col_name in headers:
            col_idx = headers.index(col_name) + 1
            cell_updates.append(gspread.Cell(row_number, col_idx, value))
    if cell_updates:
        ws.update_cells(cell_updates)


def append_to_action_log(entry):
    ws = get_or_create_sheet("action_log")
    headers = ws.row_values(1)
    if not headers:
        ws.append_row(
            ["date", "project_name", "action_type", "changed_field", "old_value", "new_value", "source"]
        )
    ws.append_row(
        [
            entry.get("date", ""),
            entry.get("project_name", ""),
            entry.get("action_type", ""),
            entry.get("changed_field", ""),
            entry.get("old_value", ""),
            entry.get("new_value", ""),
            entry.get("source", "manual"),
        ]
    )
