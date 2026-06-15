#!/usr/bin/env python3
"""
RevOps Command Center — local server.
Serves dashboard.html and proxies all Google Sheets calls via the service account.

Usage:  python3 serve.py
Open:   http://localhost:8080
"""

import os
import sys
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, jsonify, request, send_file, abort
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scripts.sheets_client import (
    get_all_projects,
    update_project_fields,
    append_to_action_log,
    get_candidates,
    get_sa_credentials,
)
from scripts.doc_builder import create_brief_doc

app = Flask(__name__)
CORS(app)

DASHBOARD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.html")
PORT = int(os.getenv("PORT", 8080))

_cache = None
_cached_at = None

EDITABLE_FIELDS = {
    "status", "priority", "project_owner", "next_step", "next_step_owner",
    "next_step_due", "what_matt_needs_to_do", "estimated_time", "notes",
}


def load_cache():
    global _cache, _cached_at
    _cache = get_all_projects()
    _cached_at = datetime.now().isoformat()
    return _cache


def find_cached_project(row):
    if not _cache:
        return None
    for p in _cache:
        if p.get("_row") == row:
            return p
    return None


@app.route("/")
def index():
    return send_file(DASHBOARD)


@app.route("/api/projects")
def api_projects():
    if _cache is None:
        load_cache()
    return jsonify({"projects": _cache, "cached_at": _cached_at, "count": len(_cache)})


@app.route("/api/projects/<int:row>", methods=["PATCH"])
def api_update_project(row):
    body = request.get_json(silent=True) or {}
    updates = {k: v for k, v in body.items() if k in EDITABLE_FIELDS}
    if not updates:
        abort(400, "No editable fields in request body")

    updates["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    project_name = body.get("project_name", f"Row {row}")

    cached = find_cached_project(row)
    for field, new_val in updates.items():
        if field == "last_updated":
            continue
        append_to_action_log({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "project_name": project_name,
            "action_type": "field_update",
            "changed_field": field,
            "old_value": cached.get(field, "") if cached else "",
            "new_value": new_val,
            "source": "dashboard",
        })

    update_project_fields(row, updates)

    if cached:
        cached.update(updates)

    return jsonify({"ok": True, "row": row, "updated": list(updates.keys())})


@app.route("/api/projects/<int:row>/mark-done", methods=["POST"])
def api_mark_done(row):
    body = request.get_json(silent=True) or {}
    project_name = body.get("project_name", f"Row {row}")

    updates = {
        "what_matt_needs_to_do": "",
        "estimated_time": "",
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
    }
    for field in ("next_step", "next_step_owner", "next_step_due"):
        if body.get(field) is not None:
            updates[field] = body[field]

    append_to_action_log({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "project_name": project_name,
        "action_type": "mark_done",
        "changed_field": "what_matt_needs_to_do",
        "old_value": "cleared",
        "new_value": "",
        "source": "dashboard",
    })

    update_project_fields(row, updates)

    cached = find_cached_project(row)
    if cached:
        cached.update(updates)

    return jsonify({"ok": True})


@app.route("/api/projects/<int:row>/brief", methods=["POST"])
def api_generate_brief(row):
    cached = find_cached_project(row)
    if not cached:
        abort(404, "Project not found")
    try:
        creds = get_sa_credentials()
        result = create_brief_doc(cached, creds)
        return jsonify({"ok": True, **result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/candidates")
def api_candidates():
    try:
        candidates = get_candidates()
        return jsonify({"candidates": candidates, "count": len(candidates)})
    except Exception as e:
        return jsonify({"candidates": [], "count": 0, "error": str(e)})


@app.route("/api/sync", methods=["POST"])
def api_sync():
    projects = load_cache()
    return jsonify({"ok": True, "count": len(projects), "cached_at": _cached_at})


@app.route("/api/status")
def api_status():
    return jsonify({
        "ok": True,
        "loaded": _cache is not None,
        "count": len(_cache) if _cache else 0,
        "cached_at": _cached_at,
    })


if __name__ == "__main__":
    print(f"RevOps Command Center  →  http://localhost:{PORT}")
    print("Loading projects from Google Sheets…")
    try:
        load_cache()
        print(f"Loaded {len(_cache)} projects.\n")
    except Exception as e:
        print(f"Warning: could not pre-load — {e}\nProjects will load on first request.\n")
    app.run(host="0.0.0.0", port=PORT, debug=False)
