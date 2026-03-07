#!/usr/bin/env python3
"""
WoP Registry Server — Flask API on localhost:7430
Serves the registry GUI and provides SSE streaming for long-running commands.
"""

import json
import sys
import os
import time
import webbrowser
import threading
from pathlib import Path
from datetime import datetime

from flask import Flask, Response, jsonify, request, send_from_directory

# ─── Path setup ───────────────────────────────────────────────────────────────
TOOLS_DIR = Path(__file__).parent
sys.path.insert(0, str(TOOLS_DIR))

import wop_link_registry as registry_lib

app = Flask(__name__)
PORT = 7430
GUI_FILE = TOOLS_DIR / "wop_registry_gui.html"


# ─── CORS helper ──────────────────────────────────────────────────────────────
@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def serve_gui():
    """Serve the registry GUI HTML."""
    if GUI_FILE.exists():
        return send_from_directory(str(TOOLS_DIR), "wop_registry_gui.html")
    return "<h1>WoP Registry Server</h1><p>GUI not found at tools/wop_registry_gui.html</p>", 404


@app.route("/api/registry")
def api_registry():
    """Return current registry data."""
    data = registry_lib.get_registry_data()
    return jsonify(data)


@app.route("/api/stats")
def api_stats():
    """Return summary stats."""
    data = registry_lib.get_registry_data()
    return jsonify({
        "stats": data.get("stats", {}),
        "updated": data.get("updated"),
        "audio_base_url": data.get("audio_base_url", ""),
        "orphan_count": len(data.get("orphans", [])),
        "broken_ref_count": len(data.get("broken_refs", [])),
        "entry_count": len(data.get("entries", {})),
    })


@app.route("/api/run/<command>")
def api_run_stream(command):
    """SSE streaming endpoint for long-running commands."""
    params = dict(request.args)

    def generate():
        yield f"data: {json.dumps({'type': 'status', 'message': f'Starting {command}...'})}\n\n"
        try:
            for event in registry_lib.run_command_streaming(command, params):
                yield event
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'message': 'Command failed'})}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.route("/api/run/<command>", methods=["POST"])
def api_run_post(command):
    """POST endpoint for commands with body params (e.g. refactor with mapping)."""
    params = request.json or {}

    def generate():
        yield f"data: {json.dumps({'type': 'status', 'message': f'Starting {command}...'})}\n\n"
        try:
            for event in registry_lib.run_command_streaming(command, params):
                yield event
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'message': 'Command failed'})}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.route("/api/entry/<path:filename>")
def api_entry(filename):
    """Return detail for a single registry entry."""
    data = registry_lib.get_registry_data()
    entry = data.get("entries", {}).get(filename)
    if entry:
        return jsonify(entry)
    return jsonify({"error": "Not found"}), 404


@app.route("/api/r2config")
def api_r2config():
    """Return R2 config status (token redacted)."""
    config = registry_lib.load_r2_config()
    if not config:
        return jsonify({"configured": False})
    return jsonify({
        "configured": True,
        "account_id": config.get("account_id", ""),
        "bucket": config.get("default_bucket", ""),
        "prefix": config.get("default_prefix", ""),
        "cdn_hostname": config.get("cdn_hostname", ""),
        "has_token": bool(config.get("api_token"))
    })


@app.route("/api/health")
def api_health():
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


# ─── Launch ───────────────────────────────────────────────────────────────────

def open_browser():
    time.sleep(1.2)
    webbrowser.open(f"http://localhost:{PORT}")


if __name__ == "__main__":
    print(f"WoP Registry Server starting on http://localhost:{PORT}")
    print(f"GUI: {GUI_FILE}")
    print(f"Press Ctrl+C to stop.")

    t = threading.Thread(target=open_browser, daemon=True)
    t.start()

    app.run(host="127.0.0.1", port=PORT, debug=False, threaded=True)
