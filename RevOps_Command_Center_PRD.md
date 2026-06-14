# RevOps Command Center — Product Requirements Document
**Owner:** Matt Austin, Director Finance & Revenue Operations, Cleo  
**Document Purpose:** Specification for a Claude Code–powered project intelligence system  
**Date:** June 14, 2026  
**Status:** Baseline v1.0 — ready for Claude Code implementation

---

## 1. Problem Statement

Matt operates across 78 active projects and initiatives spanning four workstream buckets, five data sources (Gmail, Slack, Google Calendar, Google Drive, Zoom), and dozens of internal and external stakeholders. Currently:

- There is no single place to see all active work with current status
- Prioritization is manual and reactive
- Unanswered Slacks and emails create invisible debt with no capture mechanism
- Morning time is spent reconstructing context rather than acting on it
- Next steps and ownership are undocumented across most initiatives
- The existing audit table (Google Sheets) has no mechanism for daily refresh, re-prioritization, or action tracking

---

## 2. Solution Overview

Build a **RevOps Command Center** — a Claude Code–powered application that:

1. **Reads live data daily** from Gmail, Slack, Google Calendar, Google Drive, and Zoom
2. **Maintains and enriches a project registry** (the 78-item audit table as baseline) with status, next steps, owner, and daily actions
3. **Produces a Daily Brief** — a prioritized email/dashboard digest delivered each morning
4. **Provides an interactive dashboard UI** for viewing, filtering, sorting, and editing the project registry
5. **Manages its own storage** in Google Sheets (replacing the manual spreadsheet) as the persistent backend

---

## 3. Data Sources & Integration Architecture

### 3.1 Connected Sources (MCP via Claude)

| Source | What to Pull | Frequency |
|---|---|---|
| **Gmail** | Unread threads, sent mail, threads with no reply from Matt, threads with external parties awaiting response | Daily at run time |
| **Slack** | DMs and channel mentions directed at Matt, threads Matt is in with unread replies, new messages in key channels (`#commercial-team`, `#team-slt-elt`, `#rfp-salesforce-renewal-2026`, deal-specific channels) | Daily at run time |
| **Google Calendar** | Today's events + next 5 work days; event titles, attendees, descriptions, attached Drive files | Daily at run time |
| **Google Drive** | Recently modified files owned by or shared with Matt; files attached to calendar events | Daily at run time |
| **Zoom** | Meeting summaries and AI-generated summaries from past 48 hours | Daily at run time |

### 3.2 Data Flow

```
[Gmail] [Slack] [Calendar] [Drive] [Zoom]
           ↓ (MCP reads via Claude)
     [Signal Extraction Layer]
           ↓
   [Project Matching Engine]  ←→  [Project Registry (Google Sheets)]
           ↓
   [Action Item Generator]
           ↓
   [Daily Brief Builder]  →  [Email Delivery]
           ↓
   [Dashboard UI]  →  [Interactive Web Interface]
```

### 3.3 Storage Recommendation

**Use Google Sheets as the persistent backend.** Rationale:

- Already familiar; Matt has the audit table started there
- Accessible outside the app (can view/edit directly in browser)
- Claude Code can read/write via the Google Sheets API (or Drive MCP)
- No database infrastructure required
- Easy to export, share with ELT, or migrate later

**Sheet structure (tabs):**

| Tab Name | Purpose |
|---|---|
| `projects` | The main 78-row registry (all columns defined in Section 5) |
| `action_log` | Append-only log of every action item generated, with date, project ID, action text, status |
| `daily_briefs` | Archive of each day's brief (date + full text) |
| `signals_raw` | Raw signal log — every email/Slack/calendar event matched to a project, timestamped |
| `config` | User preferences, thresholds, notification settings |

**Alternative if Google Sheets API proves limiting:** SQLite file stored in Google Drive (Drive MCP can read/write files). More powerful for querying but loses native spreadsheet editing. Recommend starting with Sheets and migrating if needed.

---

## 4. Project Registry Schema

The registry extends the existing 7-column audit table with the following full schema:

### 4.1 Existing Columns (preserved from audit)

| # | Column | Type | Notes |
|---|---|---|---|
| 1 | `high_level_bucket` | Enum | Account Strategy / Segment Strategy / Cross-Functional Enablement / Commercial Operations |
| 2 | `sub_bucket` | String | Inter-Team or Intra-Team (CommOps only) |
| 3 | `project_name` | String | Canonical name |
| 4 | `summary` | Text | 1-3 sentence description |
| 5 | `key_partners` | String | Comma-separated names |
| 6 | `primary_source` | String | Where originally surfaced |
| 7 | `tags` | String | e.g., `Recurring \| DTE Win Room` |

### 4.2 New Columns (added by this system)

| # | Column | Type | Notes |
|---|---|---|---|
| 8 | `date_added` | Date | When this item first landed on Matt's plate (sourced from signals) |
| 9 | `status` | Enum | `Active` / `Waiting` / `Blocked` / `Monitoring` / `Closed` |
| 10 | `priority` | Enum | `P1 — Critical` / `P2 — High` / `P3 — Normal` / `P4 — Low` |
| 11 | `project_owner` | String | Who ultimately owns the outcome (often Matt, sometimes a CSM or rep) |
| 12 | `next_step` | Text | The single most important next action on this project |
| 13 | `next_step_owner` | String | Who is responsible for executing the next step |
| 14 | `next_step_due` | Date | When the next step should happen by (can be approximate) |
| 15 | `what_matt_needs_to_do` | Text | Null if nothing. Otherwise: specific action Matt needs to take today or soon. Auto-generated from signal matching. |
| 16 | `estimated_time` | String | e.g., `3 min — send email reply` / `30 min — build pricing model` / `null` |
| 17 | `last_signal_date` | Date | Date of most recent email/Slack/Zoom/calendar signal matched to this project |
| 18 | `last_signal_summary` | Text | One-line summary of what the most recent signal was |
| 19 | `last_updated` | Date | When the registry row was last modified by the system or by Matt |
| 20 | `notes` | Text | Free-form field Matt can edit manually via UI |

### 4.3 Priority Logic

The system auto-assigns priority on each daily run. Matt can override manually via the UI. Auto-logic:

- **P1 — Critical:** Active at-risk client (e.g., Illumina), proposal deadline within 48h, unanswered external party more than 24h, meeting today requiring prep not yet done
- **P2 — High:** Active deal in pipeline, internal deadline within 1 week, awaiting Matt's response to a named stakeholder, recurring weekly meeting with agenda gaps
- **P3 — Normal:** Active project, no immediate deadline, next step owned by someone else and not yet overdue
- **P4 — Low:** Monitoring only, no near-term action, recurring meeting where Matt is an attendee not a driver

---

## 5. Signal Extraction & Project Matching

### 5.1 What Counts as a Signal

A **signal** is any data point from any connected source that implies action, status change, or new information relevant to a known project. Signal types:

| Signal Type | Source | Example |
|---|---|---|
| Unanswered email | Gmail | External party emailed Matt 2 days ago, no reply |
| Unread mention | Slack | `@Matt` in a channel thread |
| Unanswered DM | Slack | DM from internal stakeholder with no response from Matt |
| Meeting today | Calendar | Event in next 24h with project-relevant attendees |
| New meeting summary | Zoom | AI summary from meeting in past 48h |
| Modified file | Drive | A file tied to a project was edited in past 24h |
| New deal stage change | Gmail (Kicksaw alerts) | Opp moved to new stage |
| Monday.com assignment | Gmail (Monday notifications) | Task assigned to Matt |

### 5.2 Project Matching Logic

For each signal, the system attempts to match it to one or more rows in the project registry. Matching strategy (in order of confidence):

1. **Exact name match** — email subject or Slack message contains the project name verbatim (e.g., "Illumina")
2. **Key partner match** — signal involves a person listed in `key_partners` for a project
3. **Keyword match** — signal contains key terms from the project summary (e.g., "PEPM", "redline", "renewal", "LOA")
4. **Calendar attendee match** — meeting attendees overlap with a project's key partners
5. **No match** — signal is flagged as `unmatched` and surfaced in the Daily Brief for Matt to manually assign or dismiss

Unmatched signals that appear substantive (new external party, new Slack channel, new file with commercial keywords) are flagged as potential **new project candidates** for Matt to confirm or dismiss.

### 5.3 Action Item Generation

Once a signal is matched to a project, the system generates a `what_matt_needs_to_do` entry using this logic:

```
IF signal = unanswered email from external party > 24h:
  → "Reply to [Name] re: [subject snippet]. Expected: [2-5 min]"

IF signal = unanswered email from internal stakeholder > 48h:
  → "Reply to [Name] re: [subject snippet]. Expected: [2-3 min]"

IF signal = @mention in Slack not yet responded to:
  → "Respond to [Name]'s Slack in [#channel]. Expected: [2-5 min]"

IF signal = meeting today AND no prep doc found in Drive:
  → "Prep for [Meeting Name] at [time] with [attendees]. Expected: [15-30 min]"

IF signal = meeting today AND prep doc exists:
  → "Review [doc name] before [Meeting Name] at [time]. Expected: [5-10 min]"

IF signal = Zoom summary from yesterday's meeting AND has action items:
  → "Review action items from [meeting name]. Expected: [5 min]"

IF signal = new file modified on a project AND Matt is not editor:
  → "Review updated [file name] for [project]. Expected: [5-15 min]"

IF signal = deal stage change:
  → "Acknowledge [opp name] stage change to [stage]. Review for Deal Desk implications. Expected: [5 min]"
```

**Time estimates** use these rough benchmarks and can be overridden in `config`:

| Action Type | Default Estimate |
|---|---|
| Send a short email reply | 2–5 min |
| Send a substantive email (pricing, strategy) | 15–30 min |
| Respond to Slack message | 2–3 min |
| Review a document | 5–20 min (based on file size) |
| Pre-meeting prep | 15–30 min |
| Build a pricing model or ROI | 30–90 min |
| Redline a contract section | 30–60 min |
| Write a proposal section | 45–90 min |

---

## 6. Daily Brief Specification

### 6.1 Delivery

- **Format:** Email to `matthew.austin@hicleo.com` (and optionally rendered in the dashboard)
- **Timing:** Sent at 7:00 AM local time (before morning Focus block)
- **Subject line format:** `RevOps Brief — [Day, Date] | [N] Actions | [N] Meetings`

### 6.2 Brief Structure

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REVOPS DAILY BRIEF — Monday, June 15, 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 FOCUS BLOCK — QUICK WINS (< 10 min each)
[Listed in priority order. These are your morning sprint.]

  1. [Project Name] — [Action description] | Expected: X min
  2. [Project Name] — [Action description] | Expected: X min
  3. ...

⚡ PRIORITY ACTIONS TODAY (10–60 min each)
[Larger items that need scheduling today]

  1. [Project Name] — [Action description] | Expected: X min
  2. ...

📅 TODAY'S CALENDAR  [Date]
  [Time] — [Meeting Title]  ★ PREP NEEDED  (if applicable)
    Attendees: [names]
    Context: [1-line project tie-in]
  [Time] — [Meeting Title]
    ...

📋 WHAT'S WAITING ON OTHERS TODAY
[Projects where next step is not owned by Matt — no action needed, just visibility]

  • [Project Name] — Waiting on [Name] for [thing] (since [date])
  • ...

🔭 TOMORROW — [Date]
  Meetings: [count and titles]
  Actions coming due: [brief list]

📆 REST OF WEEK
  [Day]: [N meetings], [N actions]
  [Day]: [N meetings], [N actions]
  [Day]: [N meetings], [N actions]

⏰ SCHEDULE TIME FOR (Big blocks needed this week)
  • [Item]: Estimated [X hours] — suggest [Day AM/PM]
  • ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🆕 NEW THIS WEEK — [N new items added to registry]
  • [Project name] — [one-line reason added]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 6.3 Brief Logic Rules

- **Focus Block** = all actions estimated ≤ 10 min, sorted by priority (P1 first), capped at 8 items
- **Priority Actions** = actions estimated > 10 min, sorted by priority
- **Prep Needed flag** = any meeting within 6 hours that has no associated Drive doc opened by Matt in past 48h
- **Calendar Context** = system auto-links each calendar event to its matching project(s) in the registry
- **Waiting on Others** = projects where `next_step_owner ≠ Matt` and `next_step_due` is today or past
- **Big Block callouts** = any single action item estimated > 45 min triggers a "schedule time for" callout
- **New This Week** = items added to the registry in the past 7 days

---

## 7. Dashboard UI Specification

### 7.1 Technology Recommendation

**React single-page app** (Claude Code can generate and serve this locally, or host as a static site). The dashboard reads from and writes to Google Sheets via the Sheets API. No separate backend server needed — Claude Code handles the data sync script separately.

### 7.2 Views

#### View 1: Project Registry (Main Table)

Full table of all 78+ projects with all 20 columns. Default view on load.

**Columns shown by default (others toggleable):**

| Column | Width | Sortable | Filterable |
|---|---|---|---|
| Priority badge (P1/P2/P3/P4) | Narrow | ✓ | ✓ |
| Project Name | Medium | ✓ | Search |
| High-Level Bucket | Medium | ✓ | ✓ |
| Sub-Bucket | Medium | ✓ | ✓ |
| Status | Narrow | ✓ | ✓ |
| What Matt Needs to Do | Wide | — | — |
| Est. Time | Narrow | ✓ | — |
| Next Step | Wide | — | — |
| Next Step Owner | Medium | ✓ | ✓ |
| Next Step Due | Medium | ✓ | — |
| Last Signal | Medium | ✓ | — |
| Tags | Medium | — | ✓ |

**Filtering panel (left sidebar or top bar):**

- Filter by Bucket (multi-select)
- Filter by Status (multi-select)
- Filter by Priority (multi-select)
- Filter by Next Step Owner (multi-select — "Me" shortcut)
- Filter by Tag (multi-select, includes Recurring)
- Filter by "Has Action Today" (boolean toggle)
- Search box (searches Project Name + Summary + Notes)

**Row interactions:**

- Click row → opens **Project Detail Panel** (slide-in right panel, see View 2)
- Right-click or hover → quick actions: Change Status, Change Priority, Mark Next Step Done, Add Note
- Inline edit: Status, Priority, Next Step Owner, Next Step Due (click to edit in-place)
- Color coding by Priority: P1 = red left border, P2 = orange, P3 = neutral, P4 = gray

#### View 2: Project Detail Panel

Full detail view for a single project, open alongside the main table. Contains:

```
┌─────────────────────────────────────────┐
│  [BUCKET BADGE]  [STATUS BADGE]  [PRIORITY BADGE]
│
│  PROJECT NAME (editable)
│  Summary (editable text area)
│
│  ─── CURRENT ACTION ───
│  What Matt Needs to Do: [text]
│  Estimated Time: [X min]
│  [ Mark Done ]  [ Edit ]
│
│  ─── NEXT STEP ───
│  Next Step: [editable]
│  Owner: [dropdown]
│  Due: [date picker]
│
│  ─── PROJECT INFO ───
│  Owner: [name]
│  Key Partners: [comma list, editable]
│  Date Added: [date]
│  Last Signal: [date + summary]
│
│  ─── SIGNAL HISTORY ───
│  [Scrollable list of all matched signals,
│   newest first, with source icon and snippet]
│
│  ─── NOTES ───
│  [Free text, editable, timestamped entries]
│
└─────────────────────────────────────────┘
```

#### View 3: Today's Brief

The Daily Brief rendered as a formatted page within the dashboard (same content as email). Allows marking action items as done, which updates the registry.

#### View 4: Calendar View

A simple weekly view showing:
- All meetings for the current week
- Each meeting tagged to its matching project(s)
- Action items due on each day shown below that day's meetings
- Color coded by bucket

#### View 5: Kanban (optional, Phase 2)

Board view with columns = Status. Cards show Project Name, Priority, Next Step Owner, and Est. Time for today's action. Drag to move status.

### 7.3 Edit & Save Behavior

- All edits in the UI write back to Google Sheets immediately (optimistic update, with error toast if write fails)
- "Mark Next Step Done" → prompts Matt to enter what the new next step is → saves both
- Marking an action item as done → clears `what_matt_needs_to_do` and `estimated_time` for that project until next signal triggers a new one
- Changes are logged in `action_log` tab with timestamp

---

## 8. Claude Code Architecture & Implementation Plan

### 8.1 Project Structure

```
revops-command-center/
├── README.md
├── .env                        # API keys, Sheet IDs, email config
├── scripts/
│   ├── daily_sync.py           # Main daily job — pulls signals, updates registry
│   ├── signal_extractor.py     # Reads Gmail, Slack, Calendar, Drive, Zoom
│   ├── project_matcher.py      # Matches signals to registry rows
│   ├── action_generator.py     # Generates what_matt_needs_to_do entries
│   ├── brief_builder.py        # Assembles and sends Daily Brief email
│   └── sheets_client.py        # Google Sheets read/write wrapper
├── dashboard/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── ProjectTable.jsx
│   │   │   ├── ProjectDetail.jsx
│   │   │   ├── DailyBrief.jsx
│   │   │   ├── CalendarView.jsx
│   │   │   ├── FilterPanel.jsx
│   │   │   └── PriorityBadge.jsx
│   │   └── api/
│   │       └── sheetsApi.js    # Sheets API wrapper for UI
│   └── package.json
├── data/
│   └── project_registry_seed.csv   # The 78-row baseline audit table
└── config/
    └── project_config.json     # Keywords, time estimates, source mappings
```

### 8.2 Daily Sync Job

**Trigger:** Cron job at 6:30 AM local time (so brief is ready by 7:00 AM)

**Steps:**

```
1. Authenticate all MCP sources
2. Pull signals from all 5 sources (past 24h window)
3. Load current project registry from Google Sheets
4. Match each signal to project(s)
5. For each project with new signals:
   a. Update last_signal_date and last_signal_summary
   b. Generate new what_matt_needs_to_do (if action implied)
   c. Update estimated_time
   d. Auto-adjust priority if warranted
6. Flag unmatched signals as new project candidates
7. Write updated registry back to Sheets
8. Log all signals to signals_raw tab
9. Build Daily Brief
10. Send email
11. Log brief to daily_briefs tab
```

### 8.3 MCP Configuration

The system uses the same MCP connections already established in Claude.ai:

```json
{
  "mcp_servers": [
    { "name": "Gmail", "url": "https://gmailmcp.googleapis.com/mcp/v1" },
    { "name": "Google Calendar", "url": "https://calendarmcp.googleapis.com/mcp/v1" },
    { "name": "Google Drive", "url": "https://drivemcp.googleapis.com/mcp/v1" },
    { "name": "Slack", "url": "https://mcp.slack.com/mcp" },
    { "name": "Zoom for Claude", "url": "https://mcp.zoom.us/mcp/zoom/streamable" }
  ]
}
```

For the Google Sheets backend, use the Drive MCP to read/write the sheet file, or add the Sheets API directly via a service account.

### 8.4 Google Sheets as Backend — Implementation Detail

Options, in order of simplicity:

**Option A — Google Sheets API with service account (recommended):**
1. Create a Google Cloud service account
2. Share the spreadsheet with the service account email
3. Use `google-auth-library` + `googleapis` npm package or `gspread` Python library
4. Read/write via REST API calls in the sync script
5. Dashboard reads same sheet via same credentials

**Option B — Drive MCP read + local CSV write (simpler but less live):**
- Read sheet content via Drive MCP `read_file_content`
- Write updates as a new CSV and re-upload via Drive MCP `create_file`
- Less elegant; causes file replace rather than cell-level update

**Recommendation:** Option A for production, Option B as a fast prototype.

---

## 9. Baseline Data Seed

The 78-row audit table from the workload audit (June 14, 2026) is the starting dataset. It should be seeded into the `projects` tab of the Google Sheet with all columns from Section 4.

**Columns to be populated manually or semi-automatically at seed time:**

- `date_added` — to be researched from source signals (see Section 9.1)
- `status` — default all to `Active` at seed, Matt to review and adjust
- `priority` — system will auto-assign on first run; Matt can override
- `project_owner` — default to `Matt Austin` for all; Matt to update where ownership sits elsewhere
- `next_step`, `next_step_owner`, `next_step_due` — to be populated on first use or during initial review session

### 9.1 Date Added Research Notes

For the date-added column, here are the sourcing signals available per project category:

- **Gmail-sourced items** — exact date available from email timestamps in the original audit pull
- **Calendar-sourced items** — use event `created` date from Calendar API
- **Slack-sourced items** — approximate month derivable from context (most Slack-first items emerged March–June 2026)
- **Memory/prior context items** (Three Wire, MercerHTC, SLT tracker) — known to predate March 2026; flag as `~Q1 2026` or earlier

---

## 10. Configuration & Customization

All user-tunable settings live in `config/project_config.json`:

```json
{
  "user": {
    "name": "Matt Austin",
    "email": "matthew.austin@hicleo.com",
    "timezone": "America/New_York",
    "focus_block_start": "07:30",
    "focus_block_end": "09:30",
    "brief_delivery_time": "07:00"
  },
  "signal_windows": {
    "gmail_lookback_hours": 24,
    "slack_lookback_hours": 24,
    "zoom_lookback_hours": 48,
    "drive_lookback_hours": 24
  },
  "priority_overrides": {
    "always_p1_projects": ["Illumina 2027 Renewal", "Three Wire Systems Partner Contract Negotiation"],
    "always_p1_senders": ["alec.greenawalt@mercer.com", "johnny.anderson@hicleo.com"]
  },
  "time_estimates": {
    "short_email_reply": 3,
    "substantive_email": 20,
    "slack_reply": 2,
    "doc_review_short": 5,
    "doc_review_long": 20,
    "meeting_prep": 20,
    "pricing_model": 60,
    "contract_redline": 45,
    "proposal_section": 60
  },
  "brief_caps": {
    "max_focus_block_items": 8,
    "max_priority_actions": 5,
    "max_waiting_on_others": 6
  },
  "new_project_detection": {
    "enabled": true,
    "min_signal_confidence": 0.7,
    "commercial_keywords": ["renewal", "proposal", "pricing", "PEPM", "EMY", "ROI", "contract", "redline", "amendment", "reseller", "RFP", "deal desk"]
  }
}
```

---

## 11. Phased Build Plan

### Phase 1 — Core Registry + Manual Refresh (Week 1–2)

- [ ] Seed the 78-row project registry into Google Sheets with all 20 columns
- [ ] Build the React dashboard with Project Table view (read-only first)
- [ ] Add filtering, sorting, and search
- [ ] Add Project Detail panel with manual editing
- [ ] Set up Sheets API write-back for edits
- [ ] Manually populate `date_added`, `status`, `priority`, `next_step`, `project_owner` for top 20 P1/P2 items

**Exit criteria:** Matt can open the dashboard, see all 78 projects, filter to "P1 active with action today," click a row, and edit next steps.

### Phase 2 — Signal Engine + Daily Sync (Week 3–4)

- [ ] Build `signal_extractor.py` for Gmail + Calendar
- [ ] Build `project_matcher.py` with keyword + partner matching
- [ ] Build `action_generator.py` with time estimate logic
- [ ] Build `daily_sync.py` orchestrator
- [ ] Run first automated sync, review matching accuracy
- [ ] Tune keywords and matching thresholds
- [ ] Add Slack signal extraction
- [ ] Add Zoom summary extraction

**Exit criteria:** Each morning, the registry is auto-updated with matched signals and populated `what_matt_needs_to_do` entries for at least 80% of actionable items.

### Phase 3 — Daily Brief Email (Week 5)

- [ ] Build `brief_builder.py`
- [ ] Set up email delivery (Gmail API send, or SMTP)
- [ ] Set up cron/scheduler (local cron, or GitHub Actions, or a simple cloud function)
- [ ] Add Today's Brief view to dashboard
- [ ] Add "mark done" flow from brief → updates registry

**Exit criteria:** 7:00 AM email arrives every weekday, Matt reads it and can act on it without opening any other tool first.

### Phase 4 — Calendar View + New Project Detection (Week 6)

- [ ] Build Calendar View in dashboard
- [ ] Add new project candidate detection and triage flow
- [ ] Add Kanban status board (optional)
- [ ] Add Drive signal extraction
- [ ] Performance tuning and edge case handling

---

## 12. Key Design Principles

1. **Zero friction on action items.** The brief and dashboard should tell Matt exactly what to do, not make him figure it out. If a signal doesn't generate a clear action, don't surface it.

2. **Preserve human judgment on priority.** Auto-priority is a starting point. Matt's manual overrides are always respected and never overwritten by the system.

3. **The 3-minute rule.** Any action estimated at ≤ 3 minutes should be in the Focus Block, not buried. Quick wins protect larger blocks.

4. **Signal without noise.** The system should err on the side of surfacing one real thing per project per day rather than surfacing everything. If a project had 5 Slack messages today, summarize to one action item, not five.

5. **Matt is the source of truth for next steps.** The system can suggest, but Matt confirms next steps. The system never auto-sets a next step from a signal — it only populates `what_matt_needs_to_do` (the immediate action) automatically. `next_step` is always manually set or confirmed.

6. **Google Sheets stays human-readable.** Even if Matt never opens the dashboard, the Google Sheet should be clean enough to read and use directly. Column names are plain English, no IDs or codes.

---

## 13. Open Questions for Claude Code Session

The following questions are resolved or pending. Resolved items are marked ✅.

1. ✅ **Sheets API auth:** Using a Google Cloud service account. See Appendix A for full credentials details.

2. **Dashboard hosting:** Run locally only (Claude Code serves it), or deploy somewhere (Netlity, Vercel, GitHub Pages)? Local is fine for personal use.

3. **Email delivery:** Send via Gmail API (uses your own Gmail account, most natural) or a transactional service (SendGrid, Resend)? Gmail API recommended since you're already connected.

4. **Scheduler:** Run via local cron (works if your laptop is on), GitHub Actions (free, reliable, runs in cloud), or a lightweight cloud function? Recommend GitHub Actions for reliability.

5. **Phase 1 priority:** Do you want to do the full 78-row seed and manual data fill in the sheet first, or should Claude Code build the import script to do it programmatically from the CSV?

6. **Dashboard framework:** Full React app, or a simpler HTML/JS single file first? React gives more flexibility; a single HTML file is faster to prototype.

---

## Appendix A — Credentials & Authentication

### Google Service Account

**Project ID:** `revops-command-center-499414`

**Key file location (local machine):**
```
/Users/mattaustin/Documents/Rev-Ops-CommandCenter/revops-command-center-499414-7f64e03b383c.json
```

**✅ Security note:** This file is correctly stored in your local `Documents` folder, which is NOT inside your Google Drive sync path. This is the right place for it. Add the filename to `.gitignore` if the project is ever pushed to a Git repository — never commit a service account key to version control.

**How Claude Code should reference it:**

In the `.env` file at the project root:
```
GOOGLE_SERVICE_ACCOUNT_KEY_PATH=/Users/mattaustin/Documents/Rev-Ops-CommandCenter/revops-command-center-499414-7f64e03b383c.json
```

In Python scripts:
```python
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

KEY_PATH = os.getenv(
    "GOOGLE_SERVICE_ACCOUNT_KEY_PATH",
    "/Users/mattaustin/Documents/Rev-Ops-CommandCenter/revops-command-center-499414-7f64e03b383c.json"
)
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

credentials = service_account.Credentials.from_service_account_file(
    KEY_PATH, scopes=SCOPES
)
sheets_service = build("sheets", "v4", credentials=credentials)
drive_service = build("drive", "v3", credentials=credentials)
```

**Required setup before first run:**

1. Confirm the following APIs are enabled in the `revops-command-center-499414` Google Cloud project:
   - Google Sheets API
   - Google Drive API
   - Gmail API (for email delivery, if using Gmail API send)

2. Share the target Google Sheet with the service account's email address (found inside the JSON key file under `"client_email"`) with **Editor** access. Without this step, the script will authenticate successfully but fail when it tries to write to the sheet.

3. The Google Sheet to use as the project registry backend:
   - **Current sheet:** `https://docs.google.com/spreadsheets/d/1d3QJCXcTNwWOI3xIAqPJ4pvx0AhdyzKk3NpK6mvKVUQ`
   - **Sheet ID** (for API calls): `1d3QJCXcTNwWOI3xIAqPJ4pvx0AhdyzKk3NpK6mvKVUQ`

---

*This document is the complete specification for the RevOps Command Center. Hand it to Claude Code as the first message in a new session, and it has everything needed to begin Phase 1.*
