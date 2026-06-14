#!/usr/bin/env python3
"""
Populate what_matt_needs_to_do and estimated_time for P1/P2 projects.
Derived from MCP signal synthesis on 2026-06-14.

Usage:
    python3 scripts/populate_actions.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import gspread
from scripts.sheets_client import get_spreadsheet

TODAY = "2026-06-14"

# (row, what_matt_needs_to_do, estimated_time)
ACTION_DATA = [
    # --- P1 CRITICAL ---
    (2,
     "Prep revised pricing and commercial strategy for Jun 23 Illumina/Mercer renewal discussion — align with Alec Greenawalt on positioning before the call",
     "45 min"),

    (10,
     "Read Three Wire cleaned redline from Matthew Lowe (Jun 11) and decide: UNLIMITED limits of liability, competing services clause, exclusivity, and PEPM rate — these are business decisions only you can make",
     "60 min"),

    (18,
     "Read Nancy Green's forwarded Salesforce RFP questions (sent Jun 9, still unanswered) and coordinate response with Madhavi Vemireddy and Chris LaFountain",
     "30 min"),

    (57,
     "Check OneMetric migration status; confirm Salesforce decommission timeline; prep talking points for HubSpot reporting sync starting Jun 16",
     "20 min"),

    # --- P2 HIGH — due Jun 15 (tomorrow) ---
    (3,
     "Email Julia Schmitt to restart Pinterest pricing negotiation — she returns from OOO today (Jun 15)",
     "10 min"),

    (5,
     "Read Ashley Huff's Jun 12 FRBSF NDA clarification response and reply or loop in legal",
     "20 min"),

    (12,
     "Read unread Reddit/Mercer POC clarity request email (May 19) and draft a response confirming POC scope",
     "20 min"),

    (16,
     "Read Sheethal's Scotiabank ROI analysis (US 0.42:1, CAN 2.42:1 at $1.75 PEPM) and send recommendation to Melissa Hildebrand",
     "15 min"),

    (27,
     "Read Heather Dalmasso's Arkema PG email (Jun 12); prep questions for Newsfront/MercerHTC meeting Jun 15",
     "20 min"),

    (28,
     "Prep for Matt/Autumn Sequoia Sync Jun 15 10am — confirm 7/1 customer onboarding path and any open items",
     "15 min"),

    (29,
     "Prep agenda and talking points for MA Tiger Team Win Room Jun 15 11am",
     "20 min"),

    (59,
     "Draft and send updated CommOps request routing message to team; verify Monday.com form is live and receiving submissions",
     "15 min"),

    (66,
     "Review and process any pending deal desk requests; prep for Proposals check-in Jun 15",
     "20 min"),

    (68,
     "Review pipeline data and prep for Growth Pipeline Call Jun 15 12:30pm",
     "15 min"),

    (75,
     "Complete ISM-6104 offboarding checklist; confirm Gong and HubSpot admin transfers are fully complete",
     "20 min"),

    (78,
     "Send Monday.com form routing instructions to all CommOps requestors — Emelia has departed and requests may be falling through",
     "10 min"),

    (79,
     "Action ISM-4751 Gong purchase approval; review Gong Access Matrix and CRM Export Report sent Jun 12-13",
     "30 min"),

    (80,
     "Check ISM-6117 Jira ticket — confirm data tools access provisioned; if not, follow up with IT directly",
     "10 min"),

    # --- P2 HIGH — due Jun 16-17 ---
    (7,
     "Draft EMY vs. PEPM talk track for Kuehne+Nagel; share with Mars Griffin-Luna and Derek before Jun 17",
     "30 min"),

    (13,
     "Pull Dayforce account ROI data and prep analysis for INTERNAL-Dayforce and Upstart Renewal Followup Jun 17",
     "30 min"),

    (33,
     "Draft EMY rate bundle architecture proposal to discuss at Matt/Mars 1:1 Jun 16",
     "30 min"),

    (67,
     "Set agenda for Jun 17 Legal/Deal Desk Weekly Sync — Three Wire unlimited liability clause should be primary topic",
     "15 min"),

    (22,
     "Review WTIA agenda and prep for WTIA+Cleo Process Discussion Jun 16 3:30pm",
     "15 min"),

    (46,
     "Prep for Matt/Autumn Partnerships meeting Jun 16 1pm — In-App Benefits SMB status",
     "15 min"),

    # --- P2 HIGH — due Jun 18+ ---
    (14,
     "Confirm you're prepared for INTERNAL-Dayforce and Upstart Renewal Followup Jun 17",
     "10 min"),

    (30,
     "Confirm DTE commercial strategy and positioning with Mars Griffin-Luna before Jun 24 Win Room",
     "15 min"),

    (40,
     "Schedule pricing committee call with Johnny Anderson, Nancy, and Madhavi on DTE commercial rate card",
     "10 min"),

    (56,
     "Reach out to Johnny Anderson and Madhavi Vemireddy to get status on exec decision regarding GTM org consolidation",
     "10 min"),

    (60,
     "Confirm Laura Botich has been provisioned HubSpot read-only and Salesforce read-only access",
     "10 min"),

    (73,
     "Email ZoomInfo rep to confirm renewal terms from Jun 12 call and lock in seat count before Jun 18 deadline",
     "15 min"),

    # --- P2 — no hard deadline but active ---
    (8,
     "Email or Slack Chad Rasmussen for a RealPage deal brief — understand current objections before next step",
     "10 min"),

    (15,
     "Check email for WTW e-auction bid update on UBS; forward status to Kyle Anderson",
     "10 min"),

    (23,
     "Check Monday.com for Bennie Reseller Amendment task status and confirm next action",
     "10 min"),

    (32,
     "Prep for Matt/Mars Pricing Huddle Jun 15 10:30am — EMY talk track progress",
     "15 min"),
]


def main():
    print("RevOps Command Center — Populate what_matt_needs_to_do")
    print("=" * 55)

    ss = get_spreadsheet()
    ws = ss.worksheet("projects")

    headers = ws.row_values(1)
    col_index = {h: i + 1 for i, h in enumerate(headers)}

    action_col = col_index.get("what_matt_needs_to_do")
    time_col = col_index.get("estimated_time")
    updated_col = col_index.get("last_updated")

    if not action_col or not time_col:
        print("ERROR: could not find what_matt_needs_to_do or estimated_time column")
        return

    cell_updates = []
    for row, action, estimated in ACTION_DATA:
        cell_updates.append(gspread.Cell(row, action_col, action))
        cell_updates.append(gspread.Cell(row, time_col, estimated))
        if updated_col:
            cell_updates.append(gspread.Cell(row, updated_col, TODAY))

    print(f"Writing {len(cell_updates)} cells across {len(ACTION_DATA)} projects…")
    ws.update_cells(cell_updates, value_input_option="USER_ENTERED")
    print("Done.")

    total_time = sum(
        int(t.split()[0]) for _, _, t in ACTION_DATA
    )
    print(f"\n{len(ACTION_DATA)} action items written.")
    print(f"Estimated total time: {total_time} min ({total_time // 60}h {total_time % 60}m)")
    print("Run: curl -X POST http://localhost:8080/api/sync  to refresh the dashboard cache.")


if __name__ == "__main__":
    main()
