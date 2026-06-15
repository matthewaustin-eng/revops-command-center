"""
Build and send the daily RevOps brief email.

Pulls all active projects with what_matt_needs_to_do set, sorts by priority,
formats as HTML email, and sends via Gmail API using stored OAuth credentials.

Called from daily_sync.py after Sheets writes are complete.
"""

import os
import base64
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


RECIPIENT = "matthew.austin@hicleo.com"
SENDER = "matthew.austin@hicleo.com"

PRIORITY_ORDER = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
PRIORITY_COLOR = {
    "P1": "#dc2626",
    "P2": "#d97706",
    "P3": "#2563eb",
    "P4": "#6b7280",
}
STATUS_EMOJI = {
    "active": "🟢",
    "in progress": "🟢",
    "blocked": "🔴",
    "waiting": "🟡",
    "on hold": "⚪",
}


def _priority_sort_key(p):
    pri = (p.get("priority") or "P4").upper().strip()
    return PRIORITY_ORDER.get(pri, 9)


def _status_icon(status):
    s = (status or "").lower().strip()
    for key, icon in STATUS_EMOJI.items():
        if key in s:
            return icon
    return "🔵"


def _collect_action_items(projects):
    """Return projects that have a what_matt_needs_to_do, sorted by priority."""
    items = [
        p for p in projects
        if (p.get("what_matt_needs_to_do") or "").strip()
        and (p.get("priority") or "").upper() not in ("P4",)
        and (p.get("status") or "").lower() not in ("closed", "complete", "cancelled")
    ]
    items.sort(key=_priority_sort_key)
    return items


def _total_minutes(items):
    total = 0
    for item in items:
        t = (item.get("estimated_time") or "").lower().strip()
        if "hr" in t or "hour" in t:
            try:
                total += int("".join(c for c in t if c.isdigit())) * 60
            except ValueError:
                total += 60
        elif "min" in t:
            try:
                total += int("".join(c for c in t if c.isdigit()))
            except ValueError:
                total += 15
    return total


def _format_time(minutes):
    if minutes >= 60:
        h = minutes // 60
        m = minutes % 60
        return f"{h}h {m}m" if m else f"{h}h"
    return f"{minutes}m"


def _build_html(items, run_date):
    total_min = _total_minutes(items)
    p1_count = sum(1 for p in items if (p.get("priority") or "").upper() == "P1")
    p2_count = sum(1 for p in items if (p.get("priority") or "").upper() == "P2")

    rows_html = ""
    for p in items:
        pri = (p.get("priority") or "P4").upper().strip()
        pri_color = PRIORITY_COLOR.get(pri, "#6b7280")
        status = p.get("status") or ""
        icon = _status_icon(status)
        name = p.get("project_name", "")
        action = p.get("what_matt_needs_to_do", "")
        est = p.get("estimated_time") or ""
        signal_summary = p.get("last_signal_summary") or ""
        signal_date = p.get("last_signal_date") or ""

        rows_html += f"""
        <tr style="border-bottom: 1px solid #e5e7eb;">
          <td style="padding: 14px 8px; vertical-align: top; white-space: nowrap;">
            <span style="display:inline-block; background:{pri_color}; color:#fff;
                         border-radius:4px; padding:2px 7px; font-size:11px;
                         font-weight:700; letter-spacing:0.5px;">{pri}</span>
          </td>
          <td style="padding: 14px 8px; vertical-align: top;">
            <div style="font-weight:600; font-size:13px; color:#111827; margin-bottom:4px;">
              {icon} {name}
            </div>
            <div style="font-size:13px; color:#374151; line-height:1.5;">
              {action}
            </div>
            {f'<div style="font-size:11px; color:#9ca3af; margin-top:4px;">Signal ({signal_date}): {signal_summary}</div>' if signal_summary else ''}
          </td>
          <td style="padding: 14px 8px; vertical-align: top; white-space: nowrap;
                     font-size:12px; color:#6b7280; text-align:right;">
            {est}
          </td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0; padding:0; background:#f9fafb; font-family: -apple-system, BlinkMacSystemFont,
             'Segoe UI', sans-serif;">
  <div style="max-width:680px; margin:32px auto; background:#fff; border-radius:8px;
              border: 1px solid #e5e7eb; overflow:hidden;">

    <!-- Header -->
    <div style="background:#111827; padding:20px 28px;">
      <div style="font-size:20px; font-weight:700; color:#fff;">
        RevOps Brief &mdash; {run_date}
      </div>
      <div style="font-size:13px; color:#9ca3af; margin-top:4px;">
        {len(items)} actions &nbsp;·&nbsp; ~{_format_time(total_min)} estimated
        &nbsp;·&nbsp; {p1_count} P1 &nbsp;·&nbsp; {p2_count} P2
      </div>
    </div>

    <!-- Actions table -->
    <div style="padding: 0 28px 24px;">
      <table style="width:100%; border-collapse:collapse;">
        <thead>
          <tr style="border-bottom: 2px solid #e5e7eb;">
            <th style="padding:12px 8px; text-align:left; font-size:11px;
                       color:#6b7280; font-weight:600; text-transform:uppercase;
                       letter-spacing:0.5px; white-space:nowrap;">PRI</th>
            <th style="padding:12px 8px; text-align:left; font-size:11px;
                       color:#6b7280; font-weight:600; text-transform:uppercase;
                       letter-spacing:0.5px;">Project &amp; Action</th>
            <th style="padding:12px 8px; text-align:right; font-size:11px;
                       color:#6b7280; font-weight:600; text-transform:uppercase;
                       letter-spacing:0.5px;">Est.</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </div>

    <!-- Footer -->
    <div style="background:#f9fafb; border-top:1px solid #e5e7eb; padding:14px 28px;
                font-size:12px; color:#9ca3af;">
      Auto-generated by RevOps Command Center &nbsp;·&nbsp;
      <a href="http://localhost:8080" style="color:#6b7280;">Open Dashboard</a>
    </div>
  </div>
</body>
</html>"""
    return html


def _build_plain(items, run_date):
    total_min = _total_minutes(items)
    lines = [
        f"RevOps Brief — {run_date}",
        f"{len(items)} actions | ~{_format_time(total_min)} estimated",
        "",
    ]
    for p in items:
        pri = (p.get("priority") or "").upper()
        name = p.get("project_name", "")
        action = p.get("what_matt_needs_to_do", "")
        est = p.get("estimated_time") or ""
        lines.append(f"[{pri}] {name} ({est})")
        lines.append(f"  → {action}")
        lines.append("")
    lines.append("Open dashboard: http://localhost:8080")
    return "\n".join(lines)


def send_brief(projects, google_credentials, run_date=None):
    """
    Build and send the daily brief email.
    projects: list of project dicts (from get_all_projects())
    google_credentials: Credentials object from get_google_credentials()
    run_date: string like "Mon Jun 16" (defaults to today)
    """
    from googleapiclient.discovery import build

    items = _collect_action_items(projects)
    if not items:
        print("  Brief: no actionable items to send, skipping email")
        return 0

    if run_date is None:
        run_date = datetime.now(timezone.utc).strftime("%a %b %-d")

    html_body = _build_html(items, run_date)
    plain_body = _build_plain(items, run_date)
    subject = f"RevOps Brief — {run_date} | {len(items)} actions"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SENDER
    msg["To"] = RECIPIENT
    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    service = build("gmail", "v1", credentials=google_credentials, cache_discovery=False)
    service.users().messages().send(
        userId="me",
        body={"raw": raw},
    ).execute()

    print(f"  Brief sent: {len(items)} items, ~{_format_time(_total_minutes(items))} estimated")
    return len(items)
