#!/usr/bin/env python3
"""
Bulk-populate priority/status/next_step/signal fields for all 83 projects.
Data synthesized from Gmail, Slack, Calendar, and Zoom MCP signals on 2026-06-14.

Usage:
    python3 scripts/populate_from_signals.py
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import gspread
from scripts.sheets_client import get_spreadsheet

TODAY = "2026-06-14"

# Each entry: (row, priority, status, project_owner, next_step, next_step_owner,
#              next_step_due, last_signal_date, last_signal_summary)
# project_owner="" means keep existing; next_step_owner="" means Matt Austin
PROJECT_DATA = [
    # row, priority, status, owner, next_step, ns_owner, ns_due, sig_date, sig_summary
    (2,  "P1", "Active",     "Matt Austin",
     "Lead Cleo/Illumina/Mercer Renewal Discussion Jun 23 — prep revised pricing and commercial strategy",
     "Matt Austin", "2026-06-23", "2026-06-14",
     "Renewal discussion on calendar Jun 23; work session Jun 15 with Alec Greenawalt (Mercer)"),

    (3,  "P2", "Waiting",    "Matt Austin",
     "Follow up with Julia Schmitt on pricing negotiation status (returns from OOO Jun 15)",
     "Matt Austin", "2026-06-15", "",
     "Julia Schmitt OOO through Jun 14; pricing negotiation in progress"),

    (4,  "P3", "Waiting",    "Sheethal Biju",
     "Confirm final PG structure is included in renewal proposal",
     "Sheethal Biju", "", "", ""),

    (5,  "P2", "Active",     "Matt Austin",
     "Review Ashley Huff's Jun 12 response and follow up on NDA clarification with legal team",
     "Matt Austin", "2026-06-15", "2026-06-12",
     "Ashley Huff (FRBSF) replied Jun 12 with NDA clarification questions"),

    (6,  "P3", "Active",     "Sheethal Biju",
     "", "Sheethal Biju", "", "", ""),

    (7,  "P2", "Active",     "Matt Austin",
     "Complete EMY vs. PEPM talk track and share with Mars and Derek",
     "Matt Austin", "2026-06-17", "", ""),

    (8,  "P2", "Waiting",    "Chad Rasmussen",
     "Get deal brief from Chad Rasmussen on RealPage objections",
     "Matt Austin", "", "", ""),

    (9,  "P3", "Waiting",    "Sheethal Biju",
     "", "Sheethal Biju", "", "", ""),

    (10, "P1", "Active",     "Matt Austin",
     "Review Matthew Lowe's Jun 11 cleaned doc — decide: Competing Services, Exclusivity, Payment Terms, Limits of Liability (UNLIMITED), PEPM rate",
     "Matt Austin", "2026-06-17", "2026-06-11",
     "Matthew Lowe sent cleaned redline Jun 11; UNLIMITED liability clause requires urgent business decision"),

    (11, "P3", "Waiting",    "Madhavi Vemireddy",
     "", "Madhavi Vemireddy", "", "", ""),

    (12, "P2", "Active",     "Matt Austin",
     "Review unread Reddit Cleo Renewal Request email — Mercer team asking for POC clarity",
     "Matt Austin", "2026-06-15", "2026-05-19",
     "Mercer team emailed May 19 requesting POC clarity; thread unread"),

    (13, "P2", "Active",     "Matt Austin",
     "Attend INTERNAL-Dayforce and Upstart Renewal Followup Jun 17; come prepared with ROI analysis",
     "Matt Austin", "2026-06-17", "2026-06-14",
     "Calendar: INTERNAL-Dayforce and Upstart Renewal Followup on Jun 17"),

    (14, "P2", "Active",     "Matt Austin",
     "Attend INTERNAL-Dayforce and Upstart Renewal Followup Jun 17",
     "Matt Austin", "2026-06-17", "", ""),

    (15, "P2", "Active",     "Kyle Anderson",
     "Check email for latest WTW e-auction bid status",
     "Kyle Anderson", "", "", ""),

    (16, "P2", "Active",     "Matt Austin",
     "Review Sheethal's Jun 12 ROI (US 0.42:1, CAN 2.42:1 at $1.75 PEPM) and send recommendation to Melissa",
     "Matt Austin", "2026-06-15", "2026-06-12",
     "Sheethal sent Scotiabank ROI analysis Jun 12: US 0.42:1, CAN 2.42:1 at $1.75 PEPM"),

    (17, "P3", "Waiting",    "Melissa Hildebrand",
     "", "Melissa Hildebrand", "", "", ""),

    (18, "P1", "Active",     "Matt Austin",
     "Review email forwarded by Nancy Green Jun 9 with RFP questions; coordinate response with Madhavi and Chris LaFountain",
     "Matt Austin", "2026-06-15", "2026-06-09",
     "Nancy Green forwarded Salesforce RFP questions Jun 9; response coordination needed with Madhavi and Chris LaFountain"),

    (19, "P3", "Monitoring", "Madhavi Vemireddy",
     "", "Madhavi Vemireddy", "", "", ""),

    (20, "P3", "Active",     "Kim McEwen",
     "", "Kim McEwen", "", "2026-06-12", "Kim McEwen active on Nava Benefits Jun 12"),

    (21, "P3", "Active",     "Kim McEwen",
     "", "Kim McEwen", "", "", ""),

    (22, "P3", "Active",     "Matt Austin",
     "Attend WTIA+Cleo Process Discussion Jun 16 3:30pm",
     "Matt Austin", "2026-06-16", "2026-06-12",
     "WTIA+Cleo Process Discussion on calendar Jun 16 3:30pm"),

    (23, "P2", "Active",     "Matt Austin",
     "Check Monday.com for Bennie Reseller Amendment task status",
     "Matt Austin", "", "", ""),

    (24, "P3", "Active",     "Matt Austin",
     "", "Matt Austin", "", "", ""),

    (25, "P3", "Active",     "Matt Austin",
     "", "Matt Austin", "", "", ""),

    (26, "P3", "Active",     "Sheethal Biju",
     "", "Sheethal Biju", "", "", ""),

    (27, "P2", "Active",     "Matt Austin",
     "Review Heather Dalmasso's Jun 12 email about Arkema PGs; attend Newsfront/MercerHTC meeting Jun 15",
     "Matt Austin", "2026-06-15", "2026-06-12",
     "Heather Dalmasso emailed Jun 12 re: Arkema PGs; Newsfront/MercerHTC meeting Jun 15"),

    (28, "P2", "Active",     "Matt Austin",
     "Attend Matt/Autumn Sequoia Sync Jun 15 10am; confirm 7/1 customer onboarding path",
     "Matt Austin", "2026-06-15", "2026-06-12",
     "Matt/Autumn Sequoia Sync on calendar Jun 15 10am; 7/1 onboarding path to confirm"),

    (29, "P2", "Active",     "Matt Austin",
     "Run MA Tiger Team Win Room Jun 15 11am",
     "Matt Austin", "2026-06-15", "2026-06-14",
     "MA Tiger Team Win Room on calendar Jun 15 11am"),

    (30, "P2", "Active",     "Mars Griffin-Luna",
     "Attend DTE Win Room Jun 24",
     "Mars Griffin-Luna", "2026-06-24", "2026-06-14",
     "DTE Win Room on calendar Jun 24"),

    (31, "P3", "Active",     "Kyle Anderson",
     "", "Kyle Anderson", "", "", ""),

    (32, "P3", "Active",     "Matt Austin",
     "Matt/Mars Pricing Huddle Jun 15 10:30am",
     "Matt Austin", "2026-06-15", "", ""),

    (33, "P2", "Active",     "Matt Austin",
     "Finalize EMY rate bundle architecture; discuss at Matt/Mars 1:1 Jun 16",
     "Matt Austin", "2026-06-16", "", ""),

    (34, "P3", "Active",     "Heather Dalmasso",
     "", "Heather Dalmasso", "", "", ""),

    (35, "P3", "Active",     "Mars Griffin-Luna",
     "", "Mars Griffin-Luna", "", "", ""),

    (36, "P3", "Active",     "Mars Griffin-Luna",
     "", "Mars Griffin-Luna", "", "", ""),

    (37, "P3", "Active",     "Mars Griffin-Luna",
     "", "Mars Griffin-Luna", "", "", ""),

    (38, "P3", "Active",     "Matt Austin",
     "Follow up with Kyla at Matt/Kyla Connect Jun 17",
     "Matt Austin", "2026-06-17", "", ""),

    (39, "P3", "Active",     "Royal",
     "", "Royal", "", "", ""),

    (40, "P2", "Active",     "Matt Austin",
     "Convene pricing committee with Johnny, Nancy, Madhavi on DTE rate card",
     "Matt Austin", "", "", ""),

    (41, "P3", "Active",     "Matt Austin",
     "Attend MM BiWeekly Sync Jun 15 2pm",
     "Matt Austin", "2026-06-15", "2026-06-14",
     "MM BiWeekly Sync on calendar Jun 15 2pm"),

    (42, "P3", "Active",     "Jen Vertanen",
     "Attend LOA Weekly Sync Jun 18",
     "Jen Vertanen", "2026-06-18", "", ""),

    (43, "P4", "Closed",     "Adam Beyer",
     "", "Adam Beyer", "", "", ""),

    (44, "P3", "Active",     "Kathleen Jones",
     "", "Kathleen Jones", "", "", ""),

    (45, "P3", "Active",     "Heather Dalmasso",
     "", "Heather Dalmasso", "", "", ""),

    (46, "P3", "Active",     "Matt Austin",
     "Attend Matt/Autumn Partnerships Jun 16 1pm",
     "Matt Austin", "2026-06-16", "2026-06-12",
     "Matt/Autumn Partnerships meeting on calendar Jun 16 1pm"),

    (47, "P3", "Active",     "Kyle Anderson",
     "", "Kyle Anderson", "", "", ""),

    (48, "P3", "Active",     "Ivan Paladin",
     "", "Ivan Paladin", "", "", ""),

    (49, "P4", "Active",     "Caitlyn Gemma",
     "", "Caitlyn Gemma", "", "", ""),

    (50, "P3", "Active",     "Matt Austin",
     "Attend Follow Up: Elevating Client Reporting Jun 18 11:30am",
     "Matt Austin", "2026-06-18", "2026-06-14",
     "Follow Up: Elevating Client Reporting on calendar Jun 18 11:30am"),

    (51, "P3", "Active",     "Sheethal Biju",
     "", "Sheethal Biju", "", "", ""),

    (52, "P4", "Active",     "Mars Griffin-Luna",
     "Attend Cleo Case Study Training Jun 17 3:30pm",
     "Mars Griffin-Luna", "2026-06-17", "", ""),

    (53, "P3", "Active",     "Matt Austin",
     "Matt/Mars 1:1 Jun 16 2pm",
     "Matt Austin", "2026-06-16", "", ""),

    (54, "P3", "Active",     "Matt Austin",
     "", "Matt Austin", "", "", ""),

    (55, "P4", "Monitoring", "Jen Vertanen",
     "", "Jen Vertanen", "", "", ""),

    (56, "P2", "Active",     "Matt Austin",
     "Follow up with Johnny and Madhavi on exec decision on org consolidation",
     "Matt Austin", "", "", ""),

    (57, "P1", "Active",     "Matt Austin",
     "Monitor OneMetric migration; attend HubSpot Office Hours Jun 18 and HubSpot reporting sync Jun 16-17",
     "Matt Austin", "2026-06-16", "2026-06-12",
     "OneMetric migration underway; Salesforce decommissioning within weeks; HubSpot meetings Jun 16-18"),

    (58, "P3", "Active",     "Matt Austin",
     "", "Matt Austin", "", "", ""),

    (59, "P2", "Active",     "Matt Austin",
     "Communicate updated CommOps request routing; ensure Monday.com form is configured after Emelia's departure",
     "Matt Austin", "2026-06-15", "2026-06-12",
     "Emelia departed; Monday.com routing form needs to be communicated to all requestors"),

    (60, "P2", "Active",     "Matt Austin",
     "Support Laura Botich onboarding; confirm HubSpot and Salesforce read-only access provisioned",
     "Matt Austin", "", "", ""),

    (61, "P3", "Active",     "Jen Vertanen",
     "Attend SLT::ETeam Weekly Checkin Jun 15 4pm",
     "Jen Vertanen", "2026-06-15", "", ""),

    (62, "P3", "Active",     "Kyle Anderson",
     "", "Kyle Anderson", "", "", ""),

    (63, "P4", "Active",     "Ivan Paladin",
     "", "Ivan Paladin", "", "2026-06-14",
     "Cross-functional collab update Jun 14"),

    (64, "P3", "Active",     "Matt Austin",
     "", "Matt Austin", "", "", ""),

    (65, "P3", "Active",     "Matt Austin",
     "", "Matt Austin", "", "", ""),

    (66, "P2", "Active",     "Matt Austin",
     "Process deal desk requests; attend Proposals check-in Jun 15 and Legal/Deal Desk Sync Jun 17",
     "Matt Austin", "2026-06-15", "2026-06-14",
     "Proposals check-in Jun 15 and Legal/Deal Desk Sync Jun 17 on calendar"),

    (67, "P2", "Active",     "Matt Austin",
     "Chair Cleo Legal & Deal Desk Weekly Sync Jun 17 1pm — Three Wire contract decisions primary topic",
     "Matt Austin", "2026-06-17", "2026-06-14",
     "Legal/Deal Desk Weekly Sync Jun 17 1pm; Three Wire unlimited liability clause is primary agenda item"),

    (68, "P2", "Active",     "Kyle Anderson",
     "Attend Growth Pipeline Call Jun 15 12:30pm",
     "Kyle Anderson", "2026-06-15", "2026-06-14",
     "Growth Pipeline Call on calendar Jun 15 12:30pm"),

    (69, "P3", "Active",     "Madhavi Vemireddy",
     "", "Madhavi Vemireddy", "", "", ""),

    (70, "P3", "Active",     "Matt Austin",
     "Attend MemOps/Pricing Biweekly sync Jun 18 11am",
     "Matt Austin", "2026-06-18", "2026-06-14",
     "MemOps/Pricing Biweekly on calendar Jun 18 11am"),

    (71, "P4", "Active",     "Jen Vertanen",
     "Attend Bi-Weekly GTM Jun 22",
     "Jen Vertanen", "2026-06-22", "2026-06-14",
     "Bi-Weekly GTM on calendar Jun 22"),

    (72, "P3", "Active",     "Kyle Anderson",
     "", "Kyle Anderson", "", "", ""),

    (73, "P2", "Active",     "Matt Austin",
     "Confirm ZoomInfo renewal outcome from Jun 12 call; finalize seat count before Jun 18 deadline",
     "Matt Austin", "2026-06-18", "2026-06-12",
     "ZoomInfo renewal call Jun 12; seat count to be finalized before Jun 18 deadline"),

    (74, "P3", "Active",     "Matt Austin",
     "", "Matt Austin", "", "", ""),

    (75, "P2", "Active",     "Matt Austin",
     "Complete ISM-6104 offboarding tasks; confirm all tool ownership transfers (Gong, HubSpot) are complete",
     "Matt Austin", "2026-06-15", "2026-06-12",
     "ISM-6104 offboarding in progress Jun 12; Gong and HubSpot admin transfers pending"),

    (76, "P4", "Closed",     "Matt Austin",
     "", "Matt Austin", "", "2026-06-12",
     "Outreach RingLead contract closed Jun 12"),

    (77, "P3", "Active",     "Matt Austin",
     "", "Matt Austin", "", "", ""),

    (78, "P2", "Active",     "Matt Austin",
     "Ensure all team routing requests go through Monday.com form after Emelia's departure",
     "Matt Austin", "2026-06-15", "", ""),

    (79, "P2", "Active",     "Matt Austin",
     "Review Gong Access Matrix (Jun 12); action ISM-4751 Gong purchase approval; review CRM Export Report",
     "Matt Austin", "2026-06-15", "2026-06-13",
     "Gong Access Matrix received Jun 12; ISM-4751 purchase approval pending; CRM Export Report needs review Jun 13"),

    (80, "P3", "Active",     "Matt Austin",
     "Check ISM-6117 Jira ticket status; follow up with IT if access not yet provisioned",
     "Matt Austin", "2026-06-15", "2026-06-12",
     "ISM-6117 data tools access ticket open Jun 12; provisioning status unknown"),

    (81, "P4", "Active",     "Johnny Anderson",
     "", "Johnny Anderson", "", "", ""),

    (82, "P3", "Active",     "Matt Austin",
     "", "Matt Austin", "", "", ""),

    (83, "P3", "Active",     "Matt Austin",
     "", "Matt Austin", "", "", ""),

    (84, "P4", "Active",     "MaKenzie Wangsness",
     "", "MaKenzie Wangsness", "", "", ""),
]

FIELDS = [
    "priority",
    "status",
    "project_owner",
    "next_step",
    "next_step_owner",
    "next_step_due",
    "last_signal_date",
    "last_signal_summary",
    "last_updated",
]


def main():
    print("RevOps Command Center — Bulk Signal Population")
    print("=" * 50)

    ss = get_spreadsheet()
    ws = ss.worksheet("projects")

    headers = ws.row_values(1)
    print(f"Headers loaded: {len(headers)} columns")

    col_index = {h: i + 1 for i, h in enumerate(headers)}

    missing = [f for f in FIELDS if f not in col_index]
    if missing:
        print(f"ERROR: Missing columns in sheet: {missing}")
        return

    cell_updates = []

    for entry in PROJECT_DATA:
        (row, priority, status, owner, next_step, ns_owner,
         ns_due, sig_date, sig_summary) = entry

        values = {
            "priority":           priority,
            "status":             status,
            "project_owner":      owner,
            "next_step":          next_step,
            "next_step_owner":    ns_owner,
            "next_step_due":      ns_due,
            "last_signal_date":   sig_date,
            "last_signal_summary": sig_summary,
            "last_updated":       TODAY,
        }

        for field, value in values.items():
            col = col_index.get(field)
            if col:
                cell_updates.append(gspread.Cell(row, col, value))

    print(f"Writing {len(cell_updates)} cells across {len(PROJECT_DATA)} rows…")
    ws.update_cells(cell_updates, value_input_option="USER_ENTERED")
    print("Done.")

    print(f"\n83 projects populated from MCP signals ({TODAY}).")
    print("Run: curl -X POST http://localhost:8080/api/sync  to refresh the dashboard cache.")


if __name__ == "__main__":
    main()
