#!/usr/bin/env python3
"""
Two-part population:
  1. date_added for all 83 projects (sourced from earliest Gmail/Slack/Calendar signal)
  2. what_matt_needs_to_do + estimated_time for remaining P3/P4 projects that have calendar actions

Source notes (^ = confirmed from Gmail search, ~ = estimated from context):
  Kuehne+Nagel      2024-05-14  ^ MQL alert email
  Three Wire        2025-09-10  ^ forwarded white-label reseller agreement
  BCBSRI/BCBSMA    2025-09-01  ~ long-standing Blue Cross clients
  Illumina          2025-11-14  ^ Grace/Matt weekly where Illumina was discussed
  Gong Admin        2025-11-04  ^ Gong Zoom assets email
  PG Standards      2025-11-01  ~ pre-existing operational project
  Scotiabank        2025-12-17  ^ Monday.com mention
  Pinterest         2025-12-04  ^ signed renewal notification
  Three Wire        2025-12-04  ^ white-label contract thread
  Legal Deal Desk   2025-12-03  ^ Zoom meeting assets
  LOA Pilot         2026-04-16  ^ LOA Weekly Sync Zoom assets
  RealPage          2026-04-23  ^ Kicksaw close-date changed email
  Sequoia           2026-04-27  ^ Nextdoor BAFO request via Sequoia consultant
  Bennie Reseller   2026-05-01  ^ reseller billing email mentioning Bennie
  Reddit ROI        2026-05-12  ^ Reddit Cleo Renewal Request email
  Salesforce RFP    2026-05-18  ^ Madhavi forwarded RFP questions
  MercerHTC         2026-05-18  ^ MercerHTC Amendment Conversation calendar invite
  SLT/ELT Tracker   2026-05-18  ^ SLT::ETeam Weekly Checkin Zoom assets
  GTM Realignment   2026-05-26  ^ Business Case: GTM Team Realignment doc shared
  WTIA              2026-05-28  ^ Pricing Proposal - WTIA v2 shared
  Laura Botich      2026-06-08  ^ ISM-6109 Jira ticket start date 06/15/2026
  Dashboard Build   2026-06-14  ^ today (this session)

Usage:
    python3 scripts/populate_dates_and_p3_actions.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import gspread
from scripts.sheets_client import get_spreadsheet

TODAY = "2026-06-14"

# (row, date_added)   ^ = confirmed from signal   ~ = estimated
DATE_ADDED = [
    (2,  "2025-11-14"),   # ^ Illumina — Grace/Matt weekly mention
    (3,  "2025-12-04"),   # ^ Pinterest Renewal — signed renewal notification
    (4,  "2025-12-04"),   # ^ Pinterest PG — same renewal context
    (5,  "2026-01-15"),   # ~ FRBSF — NDA discussions started early 2026
    (6,  "2026-02-01"),   # ~ SoHo House — mid-cycle enterprise deal
    (7,  "2024-05-14"),   # ^ Kuehne+Nagel — MQL alert email
    (8,  "2026-04-23"),   # ^ RealPage — Kicksaw close-date changed
    (9,  "2025-09-01"),   # ~ BCBSRI — long-standing Blue Cross client
    (10, "2025-09-10"),   # ^ Three Wire — forwarded white-label reseller agreement
    (11, "2025-09-01"),   # ~ BCBSMA — mentioned as Cleo client in competitive email
    (12, "2026-05-12"),   # ^ Reddit ROI — Reddit Cleo Renewal Request
    (13, "2026-02-01"),   # ~ Dayforce — renewal cycle started Q1 2026
    (14, "2026-02-01"),   # ~ Upstart — renewal cycle started Q1 2026
    (15, "2025-10-01"),   # ~ UBS — WTW e-auction enterprise timeline
    (16, "2025-12-17"),   # ^ Scotiabank — Monday.com mention
    (17, "2025-10-01"),   # ~ Autodesk — mentioned as Cleo client in competitive email
    (18, "2026-05-18"),   # ^ Salesforce RFP — Madhavi forwarded RFP follow-up questions
    (19, "2025-09-01"),   # ~ Meta — major enterprise account, long-standing
    (20, "2025-12-01"),   # ~ Nava Benefits — reseller partner, late 2025
    (21, "2026-01-01"),   # ~ J5 — FY26 cycle
    (22, "2026-05-28"),   # ^ WTIA — Pricing Proposal v2 shared
    (23, "2026-05-01"),   # ^ Bennie Reseller — reseller billing email
    (24, "2026-03-01"),   # ~ Integris — mid-cycle prospect
    (25, "2025-10-01"),   # ~ CVS — large enterprise, long-standing
    (26, "2026-01-01"),   # ~ Autokiniton — FY26 new prospect
    (27, "2026-05-18"),   # ^ MercerHTC — Amendment Conversation calendar invite
    (28, "2026-04-27"),   # ^ Sequoia — Nextdoor BAFO request via Sequoia consultant
    (29, "2026-04-01"),   # ~ MA Tiger Team — win room formed Q2 2026
    (30, "2026-04-01"),   # ~ DTE Win Room — win room formed Q2 2026
    (31, "2026-03-01"),   # ~ SMB Pricing Floor — pricing initiative Q1 2026
    (32, "2026-05-21"),   # ^ EMY Talk Track — EMY pricing mentioned in Tennant deal desk
    (33, "2026-05-21"),   # ^ EMY Rate Bundle — same EMY pricing context
    (34, "2026-04-01"),   # ~ Mercer Market Tier — Mercer channel pricing work Q2
    (35, "2026-04-01"),   # ~ Cost Savings Slide — GTM enablement work Q2
    (36, "2026-03-01"),   # ~ New Pitch Deck — GTM refresh Q1 2026
    (37, "2026-04-01"),   # ~ CS Talk Track — CS enablement Q2 2026
    (38, "2026-05-01"),   # ~ Product-to-GTM — GTM alignment project Q2
    (39, "2026-04-01"),   # ~ Outcomes Tiger Team — Q2 2026 initiative
    (40, "2026-04-01"),   # ~ Commercial Rate Card — DTE-driven pricing committee Q2
    (41, "2026-03-01"),   # ~ Enrollment Marketing — ongoing Q1 initiative
    (42, "2026-04-16"),   # ^ LOA Pilot — LOA Weekly Sync Zoom assets
    (43, "2026-01-01"),   # ~ Curology — closed, likely late 2025/early 2026
    (44, "2026-02-01"),   # ~ Standard Eligibility — ops project Q1 2026
    (45, "2026-03-01"),   # ~ Consultant Relations HubSpot — Q1 2026 HubSpot migration
    (46, "2026-03-01"),   # ~ In-App Benefits SMB — Autumn partnership initiative Q1
    (47, "2026-03-01"),   # ~ Sales Rep Dashboard — Kyle's Q1 2026 initiative
    (48, "2026-04-01"),   # ~ ROI Activation — Ivan's Q2 2026 initiative
    (49, "2026-02-01"),   # ~ RevOps+Engagement — ongoing RevOps initiative
    (50, "2026-04-01"),   # ~ Client Reporting — elevated reporting initiative Q2
    (51, "2026-01-01"),   # ~ CS FY26 Pipeline — FY26 kicked off Jan 2026
    (52, "2026-05-01"),   # ~ Case Study Training — Mars-led Q2 initiative
    (53, "2026-02-01"),   # ~ Revenue Enablement — Q1 2026 initiative
    (54, "2026-03-01"),   # ~ Consultant Pricing Sync — Q1 2026 pricing work
    (55, "2026-04-01"),   # ~ Glean Kickoff — new tool pilot Q2 2026
    (56, "2026-05-26"),   # ^ GTM Realignment — Business Case doc shared
    (57, "2026-01-15"),   # ~ CRM Transition — HubSpot migration discussions early 2026
    (58, "2025-11-01"),   # ~ PG Standards — pre-existing operational project
    (59, "2026-05-01"),   # ~ CommOps Transition — Emelia departure announced Q2
    (60, "2026-06-08"),   # ^ Laura Botich Hire — ISM-6109 Jira ticket created
    (61, "2026-05-18"),   # ^ SLT/ELT Tracker — SLT::ETeam Checkin Zoom assets
    (62, "2026-02-01"),   # ~ Sales Stages — Kyle's Q1 2026 CRM/sales ops project
    (63, "2026-03-01"),   # ~ Cross-Functional Collab 2.0 — Ivan's Q1 2026 initiative
    (64, "2025-10-01"),   # ~ CommOps Finance Biweekly — long-standing recurring sync
    (65, "2026-04-01"),   # ~ Cost-to-Serve Framework — Q2 2026 strategic initiative
    (66, "2026-01-01"),   # ~ Deal Desk Operations — formalized as project Q1 2026
    (67, "2025-12-03"),   # ^ Legal Deal Desk Sync — Zoom meeting assets Dec 2025
    (68, "2025-09-01"),   # ~ Growth Pipeline Call — recurring, established pre-FY26
    (69, "2025-09-01"),   # ~ CS Pipeline Review — recurring, established pre-FY26
    (70, "2025-12-01"),   # ~ MemOps Pricing Biweekly — recurring sync late 2025
    (71, "2025-09-01"),   # ~ Bi-Weekly GTM — recurring, established pre-FY26
    (72, "2026-01-01"),   # ~ Pricing Deal Desk Biweekly Kyle — FY26 initiative
    (73, "2026-03-01"),   # ~ ZoomInfo Contract — renewal cycle started Q1 2026
    (74, "2026-03-01"),   # ~ OneMetric Contract — signed around Q1 2026
    (75, "2026-05-01"),   # ~ Toolstack Admin Transfer — Emelia offboarding Q2 2026
    (76, "2026-04-01"),   # ~ Outreach RingLead — closed contract Q2 2026
    (77, "2026-05-01"),   # ~ SFDC Data Pull — Salesforce data extraction Q2 2026
    (78, "2026-05-15"),   # ~ CommOps Monday.com Form — post-Emelia routing fix
    (79, "2025-11-04"),   # ^ Gong Administration — Gong Zoom assets Nov 2025
    (80, "2026-06-01"),   # ~ Data Tools ISM-6117 — recent Jira ticket
    (81, "2026-01-01"),   # ~ Sales Compensation — FY26 comp cycle
    (82, "2026-01-01"),   # ~ Target Account List — FY26 TAL project
    (83, "2026-06-14"),   # ^ Cleo Dashboard Build — this session
    (84, "2025-09-01"),   # ~ Monthly Enrollment Readout — recurring, long-standing
]

# P3/P4 rows that still need what_matt_needs_to_do (calendar-driven actions)
P3_ACTIONS = [
    # (row, what_matt_needs_to_do, estimated_time)
    (38,
     "Prep agenda for Matt/Kyla Connect Jun 17 — Product-to-GTM alignment and handoff status",
     "15 min"),

    (41,
     "Attend MM BiWeekly Sync Jun 15 2pm — review enrollment marketing performance and Q3 plans",
     "60 min"),

    (42,
     "Attend LOA Weekly Sync Jun 18 — check pilot deliverable status with Jen Vertanen",
     "30 min"),

    (50,
     "Attend Follow Up: Elevating Client Reporting Jun 18 11:30am",
     "60 min"),

    (52,
     "Attend Cleo Case Study Training Jun 17 3:30pm (Mars leading — be aware for CS positioning)",
     "60 min"),

    (53,
     "Prep revenue enablement priorities for Matt/Mars 1:1 Jun 16 2pm",
     "15 min"),

    (61,
     "Attend SLT::ETeam Weekly Checkin Jun 15 4pm",
     "60 min"),

    (70,
     "Attend MemOps/Pricing Biweekly sync Jun 18 11am — bring pricing updates from DTE and Kuehne+Nagel",
     "60 min"),

    (71,
     "Prep GTM status update for Bi-Weekly GTM Jun 22",
     "15 min"),
]


def main():
    print("RevOps Command Center — date_added + P3/P4 actions")
    print("=" * 55)

    ss = get_spreadsheet()
    ws = ss.worksheet("projects")
    headers = ws.row_values(1)
    col = {h: i + 1 for i, h in enumerate(headers)}

    missing = [f for f in ["date_added", "what_matt_needs_to_do", "estimated_time", "last_updated"]
               if f not in col]
    if missing:
        print(f"ERROR: Missing columns: {missing}")
        return

    cell_updates = []

    # Part 1: date_added for all 83 rows
    for row, date in DATE_ADDED:
        cell_updates.append(gspread.Cell(row, col["date_added"], date))
        cell_updates.append(gspread.Cell(row, col["last_updated"], TODAY))

    # Part 2: P3/P4 actions
    for row, action, est in P3_ACTIONS:
        cell_updates.append(gspread.Cell(row, col["what_matt_needs_to_do"], action))
        cell_updates.append(gspread.Cell(row, col["estimated_time"], est))

    print(f"Writing {len(cell_updates)} cells "
          f"({len(DATE_ADDED)} date_added + {len(P3_ACTIONS)} P3/P4 actions)…")
    ws.update_cells(cell_updates, value_input_option="USER_ENTERED")
    print("Done.")
    print("\nRun: curl -X POST http://localhost:8080/api/sync  to refresh the dashboard cache.")


if __name__ == "__main__":
    main()
