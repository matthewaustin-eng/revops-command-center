"""
Generate what_matt_needs_to_do action items from matched signals using Claude Haiku.
"""

import json
import os
import anthropic

MODEL = "claude-haiku-4-5-20251001"

_SYSTEM = """You are a RevOps assistant generating specific, actionable work items for Matt Austin, Director of Finance & Revenue Operations at Cleo.

Given a project record and recent signals (emails, calendar events, Slack messages), return a JSON object with exactly these keys:
- what_matt_needs_to_do: 1-2 sentences. Specific action starting with a verb. Name the person or document involved. Never say just "check email" — say what to check and what to decide or respond.
- estimated_time: Realistic completion time (e.g. "10 min", "30 min", "1 hr").
- last_signal_date: YYYY-MM-DD of the most recent signal.
- last_signal_summary: 1 sentence describing what happened.

Rules:
- If a calendar event is in the signals, the action should be about attending or preparing for it.
- If an email from a key partner is in the signals, name them and the specific ask.
- If multiple signals, synthesize to the single highest-priority action.
- If signals are only automated notifications (Jira updates, Monday.com pings) with no clear action, set what_matt_needs_to_do to "".
- Output only the JSON object — no markdown, no explanation."""


def _format_signals(signals):
    lines = []
    for s in sorted(signals, key=lambda x: x.get('date', ''), reverse=True)[:5]:
        src = s['source'].upper()
        date = s.get('date', '')
        subject = s.get('subject', s.get('title', s.get('channel', '')))
        sender = s.get('sender', '') or ', '.join(s.get('attendees', []))
        content = s.get('content', '')[:400]
        lines.append(f"[{src} | {date}] {subject} — {sender}\n{content}")
    return '\n\n'.join(lines)


def generate_action(project, signals):
    """
    Call Claude Haiku to generate an action item for a project given its signals.
    Returns a dict with what_matt_needs_to_do, estimated_time, last_signal_date, last_signal_summary.
    Returns None if the API call fails or no action is warranted.
    """
    client = anthropic.Anthropic()

    user_msg = f"""Project: {project.get('project_name', '')}
Priority: {project.get('priority', '')}
Status: {project.get('status', '')}
Key Partners: {project.get('key_partners', '')}
Current next step: {project.get('next_step', '')}

Recent signals:
{_format_signals(signals)}"""

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=300,
            system=_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = response.content[0].text.strip()

        # Strip markdown code fences if present
        if text.startswith('```'):
            lines = text.split('\n')
            text = '\n'.join(lines[1:])
        text = text.rstrip('`').strip()

        result = json.loads(text)

        # Validate required keys
        for key in ('what_matt_needs_to_do', 'estimated_time', 'last_signal_date', 'last_signal_summary'):
            if key not in result:
                result[key] = ''

        return result

    except json.JSONDecodeError as e:
        print(f"    JSON parse error for {project.get('project_name', '')}: {e}")
        return None
    except Exception as e:
        print(f"    API error for {project.get('project_name', '')}: {e}")
        return None
