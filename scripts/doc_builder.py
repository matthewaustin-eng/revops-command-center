"""
Generate a project brief Google Doc from project data.
Calls Claude Haiku to draft the brief, then creates a Google Doc via Drive API.
The doc is shared with the user and the URL returned.
"""

import os
import re
from datetime import datetime

RECIPIENT = "matthew.austin@hicleo.com"


def generate_brief_text(project):
    """Call Claude to generate a structured project brief. Returns markdown string."""
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def v(key):
        val = project.get(key, "")
        return str(val).strip() if val else "—"

    prompt = f"""You are a RevOps project brief writer for Matt Austin, Director of Finance & Revenue Operations at Cleo.

Generate a structured project brief from the project data below. Be specific, direct, and concise. Use real details — no filler phrases like "this is an important project."

PROJECT DATA:
Name: {v('project_name')}
Bucket: {v('high_level_bucket')}
Priority: {v('priority')}
Status: {v('status')}
Owner: {v('project_owner')}
Summary: {v('summary')}
Key Partners / Stakeholders: {v('key_partners')}
Primary Source / System: {v('primary_source')}
Current Action Needed: {v('what_matt_needs_to_do')}
Estimated Time: {v('estimated_time')}
Next Step: {v('next_step')}
Next Step Owner: {v('next_step_owner')}
Next Step Due: {v('next_step_due')}
Last Signal Date: {v('last_signal_date')}
Last Signal Summary: {v('last_signal_summary')}
Notes: {v('notes')}
Tags: {v('tags')}

Write a brief with exactly these five section headers (use ## prefix):

## Overview
## Current Status
## Key Stakeholders
## Action Required
## Next Steps

Keep each section 2–4 sentences. Total 300–450 words. No introductory paragraph before the first section."""

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def _esc(s):
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _markdown_to_html(text):
    """Convert the brief markdown text to basic HTML."""
    lines = text.split("\n")
    html = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("## "):
            html.append(
                f'<h2 style="font-size:15px;font-weight:600;margin:22px 0 6px;'
                f'color:#111827;border-bottom:1px solid #e5e7eb;padding-bottom:4px;">'
                f"{_esc(s[3:])}</h2>"
            )
        elif s.startswith("# "):
            html.append(
                f'<h2 style="font-size:15px;font-weight:600;margin:22px 0 6px;color:#111827;">'
                f"{_esc(s[2:])}</h2>"
            )
        elif re.match(r"^\*\*\d+\.", s) or re.match(r"^\d+\. \*\*", s):
            # Numbered bold header like "**1. Overview**" or "1. **Overview**"
            label = re.sub(r"[\*\d\.]", "", s).strip()
            html.append(
                f'<h2 style="font-size:15px;font-weight:600;margin:22px 0 6px;color:#111827;">'
                f"{_esc(label)}</h2>"
            )
        else:
            # Paragraph — handle **bold** inline
            styled = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", _esc(s))
            html.append(f'<p style="margin:6px 0;line-height:1.65;font-size:14px;">{styled}</p>')
    return "\n".join(html)


def _build_html(project, brief_text, generated_at):
    """Wrap brief content in a clean HTML page for Drive import."""
    name = _esc(project.get("project_name", "Project"))
    priority = project.get("priority", "")
    status = _esc(project.get("status", ""))
    bucket = _esc(project.get("high_level_bucket", ""))
    owner = _esc(project.get("project_owner", ""))

    pri_color = {
        "P1": "#dc2626", "P2": "#d97706", "P3": "#2563eb", "P4": "#6b7280"
    }.get((priority or "")[:2], "#6b7280")
    pri_label = _esc(priority[:2] if priority else "")

    body_html = _markdown_to_html(brief_text)

    meta_chips = " &nbsp;·&nbsp; ".join(filter(None, [
        f'<span style="color:{pri_color};font-weight:700;">{pri_label}</span>' if pri_label else "",
        status,
        bucket,
        f"Owner: {owner}" if owner and owner != "—" else "",
    ]))

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8">
<style>
  body {{ font-family: Arial, sans-serif; color: #1f2937; }}
</style>
</head>
<body>
<h1 style="font-size:22px;margin-bottom:4px;color:#111827;">{name}</h1>
<p style="color:#6b7280;font-size:12px;margin:0 0 8px;">{meta_chips}</p>
<p style="color:#9ca3af;font-size:11px;margin:0 0 20px;">
  Project Brief &nbsp;·&nbsp; Generated {_esc(generated_at)}
</p>
<hr style="border:none;border-top:2px solid #e5e7eb;margin-bottom:24px;">
{body_html}
<hr style="border:none;border-top:1px solid #f3f4f6;margin:32px 0 16px;">
<p style="color:#d1d5db;font-size:10px;">RevOps Command Center &nbsp;·&nbsp; {_esc(generated_at)}</p>
</body>
</html>"""


def create_brief_doc(project, sa_credentials):
    """
    Generate a brief and create a Google Doc.
    Returns dict: {'url': str, 'title': str, 'doc_id': str}
    """
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaInMemoryUpload

    generated_at = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    date_slug = datetime.now().strftime("%Y-%m-%d %H:%M")

    brief_text = generate_brief_text(project)
    html = _build_html(project, brief_text, generated_at)

    project_name = project.get("project_name", "Project")
    title = f"{project_name} — Brief {date_slug}"

    drive = build("drive", "v3", credentials=sa_credentials, cache_discovery=False)

    media = MediaInMemoryUpload(html.encode("utf-8"), mimetype="text/html")
    file = drive.files().create(
        body={"name": title, "mimeType": "application/vnd.google-apps.document"},
        media_body=media,
        fields="id,webViewLink",
    ).execute()

    doc_id = file["id"]
    url = file.get("webViewLink", f"https://docs.google.com/document/d/{doc_id}/edit")

    # Share with Matt (non-fatal if it fails)
    try:
        drive.permissions().create(
            fileId=doc_id,
            body={"type": "user", "role": "writer", "emailAddress": RECIPIENT},
            fields="id",
            sendNotificationEmail=False,
        ).execute()
    except Exception:
        pass

    return {"url": url, "title": title, "doc_id": doc_id}
