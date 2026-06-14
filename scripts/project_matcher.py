"""
Match extracted signals to projects using keyword + partner scoring.
Returns a dict mapping row_number → list of matched signals.
"""

import re
from collections import defaultdict

STOP_WORDS = {
    'the', 'and', 'for', 'with', 'from', 'this', 'that', 'will', 'have',
    'been', 'are', 'all', 'its', 'our', 'your', 'their', 'strategy',
    'review', 'update', 'meeting', 'sync', 'call', 'team', 'weekly',
    'daily', 'monthly', 'plan', 'work', 'room', 'desk',
}

def _tokenize(text):
    tokens = re.split(r'[\s/&+\-—,;.()]+', (text or '').lower())
    return [t for t in tokens if len(t) >= 4 and t not in STOP_WORDS]

def _partner_identifiers(key_partners):
    ids = []
    for part in re.split(r'[,;]+', (key_partners or '')):
        part = part.strip().lower()
        if not part:
            continue
        if '@' in part:
            ids.append(part)
            domain = part.split('@')[-1]
            if domain not in {'hicleo.com', 'gmail.com', 'googlemail.com'}:
                ids.append(domain)
        else:
            ids.extend(w for w in part.split() if len(w) >= 4)
    return ids

def _signal_text(signal):
    parts = [
        signal.get('subject', ''),
        signal.get('title', ''),
        signal.get('content', ''),
        signal.get('sender', ''),
        signal.get('channel', ''),
        ' '.join(signal.get('attendees', [])),
    ]
    return ' '.join(parts).lower()


class ProjectMatcher:
    def __init__(self, projects):
        self.projects = projects
        self._meta = {}
        for p in projects:
            row = p['_row']
            # Build keyword set from project_name — prefer multi-word proper nouns
            name = p.get('project_name', '')
            primary_source = p.get('primary_source', '')
            kws = set(_tokenize(name)) | set(_tokenize(primary_source))
            # Also add the full project name words ≥ 5 chars as high-value tokens
            long_kws = {t for t in kws if len(t) >= 5}
            partners = _partner_identifiers(p.get('key_partners', ''))
            self._meta[row] = {
                'keywords': kws,
                'long_keywords': long_kws,
                'partners': partners,
                'project': p,
            }

    def _score(self, signal, meta):
        text = _signal_text(signal)
        score = 0
        # Long keyword match: higher weight (more specific)
        for kw in meta['long_keywords']:
            if kw in text:
                score += 2
        # Short keyword match
        for kw in meta['keywords'] - meta['long_keywords']:
            if kw in text:
                score += 1
        # Partner match: highest weight
        for pid in meta['partners']:
            if pid in text:
                score += 3
        return score

    def match_all(self, signals, min_score=2):
        """
        Returns dict: row → [signal, ...] for the best-matching project per signal.
        Only includes signals where the top-match score >= min_score.
        """
        project_signals = defaultdict(list)

        for signal in signals:
            scored = [
                (row, self._score(signal, meta), meta['project'])
                for row, meta in self._meta.items()
            ]
            scored = [(r, s, p) for r, s, p in scored if s >= min_score]
            if not scored:
                continue
            scored.sort(key=lambda x: -x[1])
            top_row, top_score, top_project = scored[0]

            # Reject if second-best is within 1 point (ambiguous match)
            if len(scored) >= 2 and scored[1][1] >= top_score - 1:
                continue

            project_signals[top_row].append({
                **signal,
                '_match_score': top_score,
                '_matched_project': top_project['project_name'],
            })

        return dict(project_signals)
