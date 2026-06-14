#!/usr/bin/env python3
"""
Seed script — sets up Google Sheet tabs and columns for the RevOps Command Center.
Safe to re-run; skips tabs and rows that already look correct.

Usage:
    python3 scripts/seed.py
"""

import os
import sys
from datetime import datetime

# Allow importing sheets_client from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import gspread
from scripts.sheets_client import get_spreadsheet, get_or_create_sheet

TODAY = datetime.now().strftime("%Y-%m-%d")

PROJECTS_HEADERS = [
    "high_level_bucket",
    "sub_bucket",
    "project_name",
    "summary",
    "key_partners",
    "primary_source",
    "tags",
    "date_added",
    "status",
    "priority",
    "project_owner",
    "next_step",
    "next_step_owner",
    "next_step_due",
    "what_matt_needs_to_do",
    "estimated_time",
    "last_signal_date",
    "last_signal_summary",
    "last_updated",
    "notes",
]

# Map the existing sheet column names to the new schema names
OLD_HEADER_MAP = {
    "High-Level Bucket": "high_level_bucket",
    "Sub-Bucket": "sub_bucket",
    "Sub-Bucket ": "sub_bucket",
    "Project / Initiative Name": "project_name",
    "1-3 Sentence Summary": "summary",
    "Key Cross-Functional Partners": "key_partners",
    "Key Cross-Functional Partners ": "key_partners",
    "Primary Data Source": "primary_source",
    "Tags": "tags",
}


def find_source_tab(ss):
    """Find the existing audit-data tab (anything not named after our managed tabs)."""
    managed = {"projects", "action_log", "daily_briefs", "signals_raw", "config"}
    candidates = [ws for ws in ss.worksheets() if ws.title.lower().strip() not in managed]
    if not candidates:
        return None
    # Prefer the tab with the most rows
    return sorted(candidates, key=lambda ws: ws.row_count, reverse=True)[0]


def setup_projects_tab(ss):
    existing_data = []

    # Try to read existing data from the source tab
    source_ws = find_source_tab(ss)
    if source_ws:
        print(f"  Reading existing data from tab: '{source_ws.title}'")
        all_values = source_ws.get_all_values()
        if len(all_values) > 1:
            old_headers = all_values[0]
            rows = all_values[1:]
            print(f"  Found {len(rows)} rows.")

            col_map = {}
            for i, h in enumerate(old_headers):
                mapped = OLD_HEADER_MAP.get(h.strip())
                if mapped:
                    col_map[i] = mapped

            for row in rows:
                if not any(cell.strip() for cell in row):
                    continue
                record = {col_map[i]: cell.strip() for i, cell in enumerate(row) if i in col_map}
                existing_data.append(record)

    # Get or create the projects tab
    try:
        projects_ws = ss.worksheet("projects")
        current_headers = projects_ws.row_values(1)
        if current_headers == PROJECTS_HEADERS:
            print("  'projects' tab already correct — skipping seed.")
            return projects_ws
        print("  'projects' tab exists but headers differ — rebuilding.")
        projects_ws.clear()
    except gspread.WorksheetNotFound:
        print("  Creating 'projects' tab.")
        projects_ws = ss.add_worksheet(title="projects", rows=200, cols=len(PROJECTS_HEADERS))

    # Write headers
    projects_ws.update(range_name="A1", values=[PROJECTS_HEADERS])

    # Write data rows
    if existing_data:
        rows_to_write = []
        for record in existing_data:
            row = []
            for col in PROJECTS_HEADERS:
                val = record.get(col, "")
                if col == "status" and not val:
                    val = "Active"
                elif col == "project_owner" and not val:
                    val = "Matt Austin"
                elif col == "last_updated" and not val:
                    val = TODAY
                row.append(val)
            rows_to_write.append(row)

        projects_ws.update(range_name="A2", values=rows_to_write)
        print(f"  Seeded {len(rows_to_write)} projects.")

    # Bold header row
    projects_ws.format(
        "1:1",
        {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.95, "green": 0.95, "blue": 0.95}},
    )

    return projects_ws


def setup_tab_with_headers(tab_name, headers):
    ss = get_spreadsheet()
    ws = get_or_create_sheet(tab_name)
    existing = ws.row_values(1)
    if existing:
        print(f"  '{tab_name}' tab already has headers — skipping.")
    else:
        ws.append_row(headers)
        ws.format("1:1", {"textFormat": {"bold": True}})
        print(f"  Created '{tab_name}' tab.")
    return ws


def main():
    print("RevOps Command Center — Sheet Setup")
    print("=" * 45)

    ss = get_spreadsheet()
    print(f"Connected: {ss.title}\n")

    print("1. projects tab")
    setup_projects_tab(ss)

    print("\n2. action_log tab")
    setup_tab_with_headers(
        "action_log",
        ["date", "project_name", "action_type", "changed_field", "old_value", "new_value", "source"],
    )

    print("\n3. daily_briefs tab")
    setup_tab_with_headers("daily_briefs", ["date", "subject", "brief_text"])

    print("\n4. signals_raw tab")
    setup_tab_with_headers(
        "signals_raw",
        ["timestamp", "signal_type", "source", "project_name", "signal_summary", "raw_content", "matched"],
    )

    print("\n5. config tab")
    setup_tab_with_headers("config", ["key", "value"])

    print("\n✅  Sheet setup complete.")
    print(f"    Sheet: https://docs.google.com/spreadsheets/d/{ss.id}")


if __name__ == "__main__":
    main()
