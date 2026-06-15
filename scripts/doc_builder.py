"""
Generate a project brief Google Doc from project data.
Uses the Project Brief Architect prompt with Claude Sonnet,
then creates a Google Doc in the user's Drive via OAuth credentials.
"""

import os
import re
from datetime import datetime

RECIPIENT = "matthew.austin@hicleo.com"

SYSTEM_PROMPT = """You are an elite Technical Product Manager and Executive Chief of Staff. Your core superpower is synthesizing chaotic, fragmented communication data into cohesive, highly strategic, and actionable Project Briefs. You read between the lines: identifying what stakeholders say they want versus what they actually need to solve the core business problem.

Phase 1: Ingestion & Analysis Framework
When data is provided, analyze across these vectors:
- The Data Trail: Identify patterns, commitments, and conflicts across the provided data. Note who said what, when, and whether it contradicts anyone else.
- Asks vs. Needs: Separate explicit feature/task requests ("Asks") from the root user or business problem ("Underlying Needs"). What someone asks for is rarely the whole story.
- Stakeholder Dynamics: Map who is driving, approving, contributing, and who needs to stay informed. Assess sentiment and anxieties from tone and communication patterns.

Phase 2: The Clarification Gatekeeper
Scan the source materials for critical gaps. If there are conflicting deadlines, unassigned high-priority action items, missing success metrics, undefined scope boundaries, or contradictory priorities — note them inline in the brief with [Insufficient data — clarify with team] rather than halting. Proceed directly to generating the brief.

Phase 3: Project Brief Output
Generate the brief using exactly this structure. Be professional, sharp, and scannable. Avoid corporate fluff. Use active verbs. An executive should be able to read this in under 2 minutes.

# {Project Name} — Project Brief

## Executive Summary
3 sentences maximum covering: current health status (On Track / At Risk / Blocked), core objective, and immediate critical path.

## Historical Context
How did this project come to be? Cite specific origins from the data. Include pivots, re-scoping events, or context that explains why the project looks the way it does.

## Key Objectives & Scope

**In-Scope:**
- Bulleted list of explicit deliverables

**Out-of-Scope:**
- Bulleted list of anything deprioritized or excluded

## Asks vs. Underlying Needs

| **Stakeholder / Source** | **The Explicit Ask** | **The Underlying Need** |
|---|---|---|
| [Name or role] | What they requested | The root problem they're actually trying to solve |

Include one row per distinct stakeholder or source. Be analytical.

## Stakeholder Map (DACI)

| **Role** | **Who** | **Notes** |
|---|---|---|
| **Driver** | Name + title | Steering day-to-day |
| **Approver** | Name + title | Final sign-off; note veto risks |
| **Contributors** | Names | Flag capacity risks |
| **Informed** | Names | Updates only |

If anyone's role is ambiguous, flag it.

## Timeline & Next Steps

**Milestones:**

| **Milestone** | **Target Date** | **Status** |
|---|---|---|
| [Name] | [Date] | On Track / At Risk / TBD |

**Action Item Registry:**

| **Action Item** | **Owner** | **Due Date** | **Source** |
|---|---|---|---|
| [Task] | [Name] | [Date] | [e.g. Sheets / Signal] |

Flag any unowned action items with 🚨 UNOWNED.

## Risks & Blockers

**Technical Risks:**
- 🔴/🟡/🟢 [Risk description]

**Timeline / Resource Risks:**
- 🔴/🟡/🟢 [Risk description]

**Alignment Risks:**
- 🔴/🟡/🟢 [Risk description]

## References

Sources used to generate this brief:
- [ ] 📧 Gmail
- [ ] 📅 Google Calendar
- [ ] 📁 Google Drive
- [ ] 💬 Slack
- [ ] 🎥 Zoom

Check the box for each source type present in the data provided.

---

Style Rules:
- Bold key terms, names, and statuses
- Use tables for DACI, milestones, action items, and asks/needs
- Use bullet points for scope and risks
- Never write a paragraph where a table or list will do
- Call out misalignments directly — don't soften them
- If you infer something not explicitly stated, mark it (inferred)
- If a field cannot be populated, write [Insufficient data — clarify with team]
- Voice: warm, direct, trusted advisor — no jargon, no filler
- Keep body paragraphs to 2–3 sentences max"""


def generate_brief_text(project):
    """Call Claude Sonnet with the Project Brief Architect prompt."""
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def v(key):
        val = project.get(key, "")
        return str(val).strip() if val else "—"

    user_message = f"""Here is the project data from the RevOps Command Center for **{v('project_name')}**:

**Project Metadata**
- Name: {v('project_name')}
- Bucket / Category: {v('high_level_bucket')}
- Priority: {v('priority')}
- Status: {v('status')}
- Project Owner: {v('project_owner')}
- Date Added: {v('date_added')}
- Tags: {v('tags')}

**Summary**
{v('summary')}

**Key Partners / Stakeholders**
{v('key_partners')}

**Primary Source / System of Record**
{v('primary_source')}

**Current Action Needed (AI-detected from signal analysis)**
{v('what_matt_needs_to_do')}
Estimated time: {v('estimated_time')}

**Next Step**
{v('next_step')}
Next step owner: {v('next_step_owner')}
Next step due: {v('next_step_due')}

**Last Signal (auto-detected)**
Date: {v('last_signal_date')}
Summary: {v('last_signal_summary')}

**Notes**
{v('notes')}

Generate the Project Brief now using the structure in your instructions."""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    return msg.content[0].text


# ── HTML conversion ────────────────────────────────────────────────────────

def _esc(s):
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline(text):
    """Handle inline markdown within already-escaped text."""
    # Escape first, then apply inline formatting
    text = _esc(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    return text


def _html_table(lines):
    """Convert a block of markdown table lines to an HTML table."""
    header_cells = None
    data_rows = []

    for line in lines:
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        # Skip separator rows (only dashes, colons, spaces)
        if all(re.match(r'^[-:\s]+$', c or '-') for c in cells):
            continue
        if header_cells is None:
            header_cells = cells
        else:
            data_rows.append(cells)

    if not header_cells:
        return ''

    th = ('background:#f9fafb;font-weight:600;text-align:left;'
          'padding:8px 10px;border:1px solid #e5e7eb;font-size:13px;')
    td = 'padding:8px 10px;border:1px solid #e5e7eb;font-size:13px;vertical-align:top;'

    html = '<table style="border-collapse:collapse;width:100%;margin:12px 0;">'
    html += '<tr>' + ''.join(f'<th style="{th}">{_inline(c)}</th>' for c in header_cells) + '</tr>'
    for row in data_rows:
        # Pad short rows
        while len(row) < len(header_cells):
            row.append('')
        html += '<tr>' + ''.join(f'<td style="{td}">{_inline(c)}</td>' for c in row) + '</tr>'
    html += '</table>'
    return html


def _markdown_to_html(text):
    """Convert the brief markdown to HTML, handling tables, checkboxes, lists, headers."""
    lines = text.split('\n')
    blocks = []
    i = 0

    HEADER_SIZES  = {1: '22px', 2: '17px', 3: '14px', 4: '13px'}
    HEADER_WEIGHT = {1: '700',  2: '600',  3: '600',  4: '600'}
    HEADER_MARGIN = {1: '28px 0 8px', 2: '22px 0 6px', 3: '16px 0 4px', 4: '12px 0 4px'}
    HEADER_COLOR  = {1: '#111827', 2: '#1f2937', 3: '#374151', 4: '#374151'}

    while i < len(lines):
        raw = lines[i]
        s = raw.strip()

        if not s:
            i += 1
            continue

        # Table block
        if s.startswith('|'):
            tbl = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                tbl.append(lines[i].strip())
                i += 1
            blocks.append(_html_table(tbl))
            continue

        # Headers (#, ##, ###, ####)
        m = re.match(r'^(#{1,4})\s+(.*)', s)
        if m:
            lvl = len(m.group(1))
            content = _inline(m.group(2))
            border = ' border-bottom:2px solid #e5e7eb;padding-bottom:4px;' if lvl <= 2 else ''
            blocks.append(
                f'<h{lvl} style="font-size:{HEADER_SIZES[lvl]};font-weight:{HEADER_WEIGHT[lvl]};'
                f'margin:{HEADER_MARGIN[lvl]};color:{HEADER_COLOR[lvl]};{border}">'
                f'{content}</h{lvl}>'
            )
            i += 1
            continue

        # Checkbox list items
        if re.match(r'^- \[[ xX]\]', s):
            items = []
            while i < len(lines) and re.match(r'^- \[[ xX]\]', lines[i].strip()):
                ls = lines[i].strip()
                checked = ls[3].lower() == 'x'
                content = _inline(ls[6:].strip())
                items.append((checked, content))
                i += 1
            html = '<ul style="list-style:none;padding:0;margin:6px 0;">'
            for checked, content in items:
                mark = '☑' if checked else '☐'
                color = '#16a34a' if checked else '#6b7280'
                html += (f'<li style="margin:4px 0;font-size:13px;">'
                         f'<span style="color:{color};margin-right:6px;">{mark}</span>{content}</li>')
            html += '</ul>'
            blocks.append(html)
            continue

        # Bullet list
        if re.match(r'^[-*•]\s', s):
            items = []
            while i < len(lines) and re.match(r'^[-*•]\s', lines[i].strip()):
                content = _inline(re.sub(r'^[-*•]\s+', '', lines[i].strip()))
                items.append(content)
                i += 1
            html = '<ul style="margin:6px 0;padding-left:22px;">'
            for item in items:
                html += f'<li style="margin:3px 0;line-height:1.55;font-size:13px;">{item}</li>'
            html += '</ul>'
            blocks.append(html)
            continue

        # Numbered list
        if re.match(r'^\d+\.\s', s):
            items = []
            while i < len(lines) and re.match(r'^\d+\.\s', lines[i].strip()):
                content = _inline(re.sub(r'^\d+\.\s+', '', lines[i].strip()))
                items.append(content)
                i += 1
            html = '<ol style="margin:6px 0;padding-left:22px;">'
            for item in items:
                html += f'<li style="margin:3px 0;line-height:1.55;font-size:13px;">{item}</li>'
            html += '</ol>'
            blocks.append(html)
            continue

        # Horizontal rule
        if re.match(r'^[-*_]{3,}$', s):
            blocks.append('<hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0;">')
            i += 1
            continue

        # Paragraph — collect consecutive non-special lines
        para = []
        while i < len(lines):
            ls = lines[i].strip()
            if not ls:
                break
            if (ls.startswith('|') or re.match(r'^#{1,4}\s', ls) or
                    re.match(r'^[-*•]\s', ls) or re.match(r'^\d+\.\s', ls) or
                    re.match(r'^- \[[ xX]\]', ls) or re.match(r'^[-*_]{3,}$', ls)):
                break
            para.append(ls)
            i += 1
        if para:
            blocks.append(
                f'<p style="margin:6px 0;line-height:1.65;font-size:14px;">'
                f'{_inline(" ".join(para))}</p>'
            )
        continue

    return '\n'.join(blocks)


def _build_html(project, brief_text, generated_at):
    """Wrap the brief in a clean branded HTML page for Drive import."""
    name = _esc(project.get("project_name", "Project"))
    priority = project.get("priority", "")
    status = _esc(project.get("status", ""))
    bucket = _esc(project.get("high_level_bucket", ""))
    owner = _esc(project.get("project_owner", ""))

    pri_color = {"P1": "#dc2626", "P2": "#d97706", "P3": "#2563eb", "P4": "#6b7280"}.get(
        (priority or "")[:2], "#6b7280"
    )
    pri_label = _esc((priority or "")[:2])

    chips = " &nbsp;·&nbsp; ".join(filter(None, [
        f'<span style="color:{pri_color};font-weight:700;">{pri_label}</span>' if pri_label else "",
        status, bucket,
        f"Owner: {owner}" if owner and owner != "—" else "",
    ]))

    body = _markdown_to_html(brief_text)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: Arial, sans-serif; color: #1f2937; max-width: 860px; margin: 0 auto; }}
  table {{ page-break-inside: avoid; }}
</style>
</head>
<body>
<p style="color:#9ca3af;font-size:11px;margin:0 0 4px;">Project Brief &nbsp;·&nbsp; Generated {_esc(generated_at)}</p>
<p style="color:#6b7280;font-size:12px;margin:0 0 20px;">{chips}</p>
<hr style="border:none;border-top:2px solid #e5e7eb;margin-bottom:24px;">
{body}
<hr style="border:none;border-top:1px solid #f3f4f6;margin:36px 0 16px;">
<p style="color:#d1d5db;font-size:10px;">RevOps Command Center &nbsp;·&nbsp; {_esc(generated_at)}</p>
</body>
</html>"""


# ── Main entry point ───────────────────────────────────────────────────────

def create_brief_doc(project, oauth_credentials):
    """
    Generate a brief and create a Google Doc in the user's Drive.
    Returns dict: {'url': str, 'title': str, 'doc_id': str}
    """
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaInMemoryUpload

    generated_at = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    date_slug = datetime.now().strftime("%Y-%m-%d %H:%M")

    brief_text = generate_brief_text(project)
    html = _build_html(project, brief_text, generated_at)

    title = f"{project.get('project_name', 'Project')} — Brief {date_slug}"

    drive = build("drive", "v3", credentials=oauth_credentials, cache_discovery=False)
    media = MediaInMemoryUpload(html.encode("utf-8"), mimetype="text/html")
    file = drive.files().create(
        body={"name": title, "mimeType": "application/vnd.google-apps.document"},
        media_body=media,
        fields="id,webViewLink",
    ).execute()

    doc_id = file["id"]
    url = file.get("webViewLink", f"https://docs.google.com/document/d/{doc_id}/edit")

    return {"url": url, "title": title, "doc_id": doc_id}
