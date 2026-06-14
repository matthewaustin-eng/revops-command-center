#!/usr/bin/env python3
"""
Daily sync orchestrator.

Pipeline:
  1. Load projects from Google Sheets (skip P4 / Closed)
  2. Extract signals from Gmail (48h), Calendar (7d), Slack (48h)
  3. Match signals to projects
  4. For each matched project: call Claude Haiku to generate action
  5. Batch-write results to Sheets
  6. Append to action_log
  7. POST /api/sync to refresh Flask cache (local only)

Run locally:
    python3 scripts/daily_sync.py

Run in GitHub Actions:
    Triggered by .github/workflows/daily_sync.yml
    Env vars: GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_SHEET_ID,
              GOOGLE_OAUTH_CREDENTIALS, SLACK_TOKEN, ANTHROPIC_API_KEY
"""

import os
import sys
import json
import tempfile
import traceback
from datetime import datetime, timezone

# Add project root to path so imports resolve regardless of cwd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# --- early env check (printed before any imports that use credentials) ---
_SA_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
print(f"GOOGLE_SERVICE_ACCOUNT_JSON set: {bool(_SA_JSON)} (length: {len(_SA_JSON)})")
if not _SA_JSON:
    print("ERROR: GOOGLE_SERVICE_ACCOUNT_JSON secret is missing or empty.")
    print("  Go to: GitHub repo → Settings → Secrets → Actions")
    print("  Add secret named exactly: GOOGLE_SERVICE_ACCOUNT_JSON")
    sys.exit(1)


def _write_service_account_json():
    """
    In GitHub Actions, GOOGLE_SERVICE_ACCOUNT_JSON is a raw JSON string.
    sheets_client.py reads a file path, so write it to a temp file.
    Returns the temp file path, or None if the env var is not set.
    """
    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw:
        return None
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    tmp.write(raw)
    tmp.close()
    return tmp.name


def _cleanup_temp(path):
    if path:
        try:
            os.unlink(path)
        except Exception:
            pass


def _skip_project(project):
    priority = (project.get("priority") or "").upper().strip()
    status = (project.get("status") or "").lower().strip()
    if priority == "P4":
        return True
    if status in ("closed", "complete", "cancelled", "on hold"):
        return True
    return False


def main():
    run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{run_ts}] Starting daily sync")

    # -----------------------------------------------------------------------
    # 1. Set up service account temp file for sheets_client
    # -----------------------------------------------------------------------
    sa_tmp = _write_service_account_json()
    if sa_tmp:
        os.environ["GOOGLE_SERVICE_ACCOUNT_KEY_FILE"] = sa_tmp
        print(f"  SA key written to temp file: {sa_tmp}")

    try:
        from scripts.sheets_client import get_all_projects, update_project_fields, append_to_action_log
    except ImportError:
        from sheets_client import get_all_projects, update_project_fields, append_to_action_log

    # -----------------------------------------------------------------------
    # 2. Load projects
    # -----------------------------------------------------------------------
    print("  Loading projects from Sheets...")
    all_projects = get_all_projects()
    active_projects = [p for p in all_projects if not _skip_project(p)]
    print(f"  {len(active_projects)} active projects (skipped {len(all_projects) - len(active_projects)} P4/Closed)")

    # -----------------------------------------------------------------------
    # 3. Extract signals
    # -----------------------------------------------------------------------
    print("  Extracting Gmail + Calendar signals...")
    try:
        from scripts.signal_extractor import get_google_credentials, GmailExtractor, CalendarExtractor, SlackExtractor
    except ImportError:
        from signal_extractor import get_google_credentials, GmailExtractor, CalendarExtractor, SlackExtractor

    all_signals = []

    try:
        creds = get_google_credentials()
        gmail_signals = GmailExtractor(creds).get_signals(days=2)
        print(f"    Gmail: {len(gmail_signals)} signals")
        all_signals.extend(gmail_signals)

        cal_signals = CalendarExtractor(creds).get_signals(days_ahead=7)
        print(f"    Calendar: {len(cal_signals)} signals")
        all_signals.extend(cal_signals)
    except Exception as e:
        print(f"  Warning: Gmail/Calendar extraction failed: {e}")
        traceback.print_exc()

    slack_token = os.getenv("SLACK_TOKEN", "")
    if slack_token:
        try:
            slack_signals = SlackExtractor(token=slack_token).get_signals(days=2)
            print(f"    Slack: {len(slack_signals)} signals")
            all_signals.extend(slack_signals)
        except Exception as e:
            print(f"  Warning: Slack extraction failed: {e}")
    else:
        print("    Slack: skipped (SLACK_TOKEN not set)")

    print(f"  Total signals: {len(all_signals)}")

    if not all_signals:
        print("  No signals found. Exiting early.")
        _cleanup_temp(sa_tmp)
        return

    # -----------------------------------------------------------------------
    # 4. Match signals to projects
    # -----------------------------------------------------------------------
    try:
        from scripts.project_matcher import ProjectMatcher
    except ImportError:
        from project_matcher import ProjectMatcher

    print("  Matching signals to projects...")
    matcher = ProjectMatcher(active_projects)
    project_signals = matcher.match_all(all_signals, min_score=2)
    print(f"  {len(project_signals)} projects with matched signals")

    # -----------------------------------------------------------------------
    # 5. Generate actions for matched projects
    # -----------------------------------------------------------------------
    try:
        from scripts.action_generator import generate_action
    except ImportError:
        from action_generator import generate_action

    updates = []

    for row, signals in sorted(project_signals.items()):
        project = next((p for p in active_projects if p["_row"] == row), None)
        if not project:
            continue

        # Skip if signal is older than last recorded signal (no change)
        latest_signal_date = max((s.get("date", "") for s in signals), default="")
        existing_signal_date = (project.get("last_signal_date") or "")
        if latest_signal_date and existing_signal_date and latest_signal_date <= existing_signal_date:
            print(f"  [{row}] {project['project_name']}: no new signals, skipping")
            continue

        print(f"  [{row}] {project['project_name']}: {len(signals)} signals → generating action...")
        result = generate_action(project, signals)

        if result is None:
            print(f"    API call failed, skipping")
            continue

        action = result.get("what_matt_needs_to_do", "").strip()
        if not action:
            print(f"    No actionable item returned, skipping")
            continue

        updates.append({
            "row": row,
            "project_name": project["project_name"],
            "fields": {
                "what_matt_needs_to_do": action,
                "estimated_time": result.get("estimated_time", ""),
                "last_signal_date": result.get("last_signal_date", "") or latest_signal_date,
                "last_signal_summary": result.get("last_signal_summary", ""),
                "last_updated": run_ts[:10],
            },
        })
        print(f"    → {action[:80]}{'...' if len(action) > 80 else ''}")

    # -----------------------------------------------------------------------
    # 6. Batch write to Sheets
    # -----------------------------------------------------------------------
    print(f"\n  Writing {len(updates)} updates to Sheets...")
    written = 0
    for u in updates:
        try:
            update_project_fields(u["row"], u["fields"])
            written += 1
        except Exception as e:
            print(f"    Error writing row {u['row']} ({u['project_name']}): {e}")

    print(f"  Done: {written}/{len(updates)} rows written")

    # -----------------------------------------------------------------------
    # 7. Append to action_log
    # -----------------------------------------------------------------------
    log_entry = {
        "timestamp": run_ts,
        "signals_found": len(all_signals),
        "projects_matched": len(project_signals),
        "actions_written": written,
        "projects_updated": [u["project_name"] for u in updates[:written]],
    }
    try:
        append_to_action_log(log_entry)
    except Exception as e:
        print(f"  Warning: action_log write failed: {e}")

    # -----------------------------------------------------------------------
    # 8. Refresh Flask cache (local only — skip in Actions)
    # -----------------------------------------------------------------------
    if not os.getenv("GITHUB_ACTIONS"):
        try:
            import urllib.request
            urllib.request.urlopen("http://localhost:8080/api/sync", timeout=5)
            print("  Flask cache refreshed")
        except Exception:
            pass

    _cleanup_temp(sa_tmp)
    print(f"\nSync complete: {written} projects updated from {len(all_signals)} signals")


if __name__ == "__main__":
    main()
