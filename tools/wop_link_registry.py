#!/usr/bin/env python3
"""
WoP Link Registry — Audio asset management CLI for Words of Plainness Ministry
Commands: audit, check, report, refactor, r2-audit, r2-check
"""

import os
import sys
import json
import re
import hashlib
import argparse
from pathlib import Path
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent
SRC_DIR = REPO_ROOT / "src"
ASSETS_AUDIO_DIR = SRC_DIR / "assets" / "audio"
DATA_DIR = SRC_DIR / "_data"
SITE_JSON = DATA_DIR / "site.json"
REGISTRY_FILE = Path(__file__).parent / "wop_registry.json"
R2_CONFIG_FILE = Path(__file__).parent / "wop_r2_config.json"
R2_REPORT_FILE = Path(__file__).parent / "wop_r2_report.json"

AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac", ".m4a"}

# Pattern: all audio src/href references in template files
AUDIO_REF_PATTERN = re.compile(
    r'''(?:src|href|data-src|audioSrc)\s*[=:]\s*["'`]([^"'`]*\.(?:mp3|wav|ogg|flac|m4a))[`"']''',
    re.IGNORECASE
)

# Template variable reference pattern — {{ site.audioBaseUrl }}/filename.mp3
TEMPLATE_VAR_PATTERN = re.compile(
    r'''\{\{[^}]*audioBaseUrl[^}]*\}\}/([^\s"'`<>]+\.(?:mp3|wav|ogg|flac|m4a))''',
    re.IGNORECASE
)

TEMPLATE_EXTENSIONS = {".njk", ".html", ".md", ".js", ".json", ".yaml", ".yml"}


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRY DATA MODEL
# ─────────────────────────────────────────────────────────────────────────────

def load_registry():
    if REGISTRY_FILE.exists():
        with open(REGISTRY_FILE) as f:
            return json.load(f)
    return {"version": 1, "updated": None, "entries": {}, "orphans": [], "broken_refs": []}


def save_registry(data):
    data["updated"] = datetime.now().isoformat()
    with open(REGISTRY_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_r2_config():
    if R2_CONFIG_FILE.exists():
        with open(R2_CONFIG_FILE) as f:
            return json.load(f)
    return None


def load_site_json():
    if SITE_JSON.exists():
        with open(SITE_JSON) as f:
            return json.load(f)
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# FILE DISCOVERY
# ─────────────────────────────────────────────────────────────────────────────

def find_audio_files(audio_dir=None):
    """Find all audio files in the assets/audio directory."""
    search_dir = audio_dir or ASSETS_AUDIO_DIR
    if not search_dir.exists():
        return {}
    files = {}
    for f in search_dir.rglob("*"):
        if f.suffix.lower() in AUDIO_EXTENSIONS:
            rel = str(f.relative_to(search_dir))
            stat = f.stat()
            files[rel] = {
                "path": str(f),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "checksum": None  # Lazy — computed on demand
            }
    return files


def find_template_files():
    """Find all template/source files that could reference audio."""
    if not SRC_DIR.exists():
        return []
    files = []
    for f in SRC_DIR.rglob("*"):
        if ".claude" in f.parts:
            continue
        if f.suffix.lower() in TEMPLATE_EXTENSIONS and f.is_file():
            files.append(f)
    return files


def extract_audio_refs(file_path):
    """Extract all audio filename references from a template file."""
    refs = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        # Direct refs
        for m in AUDIO_REF_PATTERN.finditer(content):
            url = m.group(1)
            filename = url.split("/")[-1]
            refs.append({
                "file": str(file_path.relative_to(REPO_ROOT)),
                "url": url,
                "filename": filename,
                "type": "direct",
                "line": content[:m.start()].count("\n") + 1
            })
        # Template variable refs
        for m in TEMPLATE_VAR_PATTERN.finditer(content):
            filename = m.group(1).split("?")[0]  # strip query strings
            refs.append({
                "file": str(file_path.relative_to(REPO_ROOT)),
                "url": f"{{{{site.audioBaseUrl}}}}/{filename}",
                "filename": filename,
                "type": "template_var",
                "line": content[:m.start()].count("\n") + 1
            })
    except Exception as e:
        print(f"  Warning: could not parse {file_path}: {e}", file=sys.stderr)
    return refs


# ─────────────────────────────────────────────────────────────────────────────
# COMMANDS
# ─────────────────────────────────────────────────────────────────────────────

def cmd_audit(args, stream=False):
    """Full audit: scan audio files, scan template refs, cross-reference."""
    emit = _make_emitter(stream)
    emit("status", "Starting full audio registry audit...")

    registry = load_registry()
    site = load_site_json()
    audio_base_url = site.get("audioBaseUrl", "/assets/audio")
    emit("info", f"audioBaseUrl: {audio_base_url}")

    # Step 1: Find audio files
    emit("status", "Scanning audio assets...")
    audio_files = find_audio_files()
    emit("info", f"Found {len(audio_files)} audio files in assets/audio/")

    # Step 2: Find all template refs
    emit("status", "Scanning template references...")
    template_files = find_template_files()
    all_refs = []
    for tf in template_files:
        refs = extract_audio_refs(tf)
        all_refs.extend(refs)
    emit("info", f"Found {len(all_refs)} audio references across {len(template_files)} template files")

    # Step 3: Cross-reference
    referenced_filenames = {r["filename"] for r in all_refs}
    audio_filenames = set(audio_files.keys())

    orphans = audio_filenames - referenced_filenames  # files not referenced
    broken = referenced_filenames - audio_filenames   # refs with no file

    # Build registry entries
    entries = {}
    for filename, meta in audio_files.items():
        refs_for_file = [r for r in all_refs if r["filename"] == filename]
        entries[filename] = {
            **meta,
            "referenced": filename in referenced_filenames,
            "ref_count": len(refs_for_file),
            "refs": refs_for_file,
            "r2_uploaded": False,
            "r2_url": None,
            "cdn_url": None,
        }

    registry["entries"] = entries
    registry["orphans"] = sorted(orphans)
    registry["broken_refs"] = sorted(broken)
    registry["audio_base_url"] = audio_base_url
    registry["stats"] = {
        "total_files": len(audio_files),
        "total_refs": len(all_refs),
        "orphan_count": len(orphans),
        "broken_ref_count": len(broken),
        "referenced_count": len(audio_filenames & referenced_filenames),
    }

    save_registry(registry)

    # Report
    emit("success", f"Audit complete.")
    emit("stat", f"Total audio files: {len(audio_files)}")
    emit("stat", f"Referenced: {len(audio_filenames & referenced_filenames)}")
    emit("stat", f"Orphaned (unreferenced): {len(orphans)}")
    emit("stat", f"Broken refs (no file): {len(broken)}")

    if orphans:
        emit("warn", "Orphaned files (exist but not referenced):")
        for o in sorted(orphans):
            emit("item", f"  {o}")

    if broken:
        emit("error", "Broken references (referenced but missing):")
        for b in sorted(broken):
            emit("item", f"  {b}")

    if not orphans and not broken:
        emit("success", "All audio files are referenced and all references resolve.")

    return registry


def cmd_check(args, stream=False):
    """Quick check against existing registry without full rescan."""
    emit = _make_emitter(stream)
    registry = load_registry()

    if not registry["entries"]:
        emit("warn", "Registry is empty. Run 'audit' first.")
        return registry

    audio_files = find_audio_files()
    current = set(audio_files.keys())
    registered = set(registry["entries"].keys())

    new_files = current - registered
    removed_files = registered - current

    emit("status", f"Quick check — {len(current)} files on disk, {len(registered)} in registry")

    if new_files:
        emit("warn", f"{len(new_files)} new file(s) not in registry (run audit):")
        for f in sorted(new_files):
            emit("item", f"  + {f}")

    if removed_files:
        emit("warn", f"{len(removed_files)} file(s) removed since last audit:")
        for f in sorted(removed_files):
            emit("item", f"  - {f}")

    if not new_files and not removed_files:
        emit("success", "Registry is current. No changes detected.")

    return registry


def cmd_report(args, stream=False):
    """Print a human-readable summary report."""
    emit = _make_emitter(stream)
    registry = load_registry()

    if not registry.get("entries"):
        emit("warn", "Registry is empty. Run 'audit' first.")
        return

    stats = registry.get("stats", {})
    emit("report", "═══════════════════════════════════")
    emit("report", "   WoP Audio Registry Report")
    emit("report", f"   {registry.get('updated', 'unknown')}")
    emit("report", "═══════════════════════════════════")
    emit("report", f"audioBaseUrl:  {registry.get('audio_base_url', '?')}")
    emit("report", f"Total files:   {stats.get('total_files', '?')}")
    emit("report", f"Total refs:    {stats.get('total_refs', '?')}")
    emit("report", f"Referenced:    {stats.get('referenced_count', '?')}")
    emit("report", f"Orphaned:      {stats.get('orphan_count', '?')}")
    emit("report", f"Broken refs:   {stats.get('broken_ref_count', '?')}")
    emit("report", "")

    # R2 status
    r2_uploaded = sum(1 for e in registry["entries"].values() if e.get("r2_uploaded"))
    emit("report", f"R2 uploaded:   {r2_uploaded}/{stats.get('total_files', '?')}")
    emit("report", "═══════════════════════════════════")

    for filename, entry in sorted(registry["entries"].items()):
        status = "[OK]" if entry.get("referenced") else "[!]"
        r2 = "R2:Y" if entry.get("r2_uploaded") else "R2:N"
        size_kb = entry.get("size", 0) // 1024
        emit("entry", f"{status} {r2}  {filename}  ({size_kb}KB, {entry.get('ref_count',0)} refs)")


def cmd_r2_audit(args, stream=False):
    """Audit R2 bucket — list what's uploaded vs what should be uploaded."""
    emit = _make_emitter(stream)
    r2_config = load_r2_config()

    if not r2_config:
        emit("error", "R2 config not found. Create tools/wop_r2_config.json first.")
        emit("info", "Required fields: access_key_id, secret_access_key, account_id, default_bucket, cdn_hostname")
        return

    bucket = args.bucket if hasattr(args, "bucket") and args.bucket else r2_config.get("default_bucket", "wop-media")
    prefix = args.prefix if hasattr(args, "prefix") and args.prefix else r2_config.get("default_prefix", "web")
    cdn_hostname = args.cdn if hasattr(args, "cdn") and args.cdn else r2_config.get("cdn_hostname", "")

    emit("status", f"Auditing R2 bucket: {bucket}/{prefix}/")
    emit("info", f"CDN hostname: {cdn_hostname}")

    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        emit("error", "boto3 not installed. Run: pip install boto3")
        return

    account_id = r2_config.get("account_id")
    access_key_id = r2_config.get("access_key_id")
    secret_access_key = r2_config.get("secret_access_key")
    endpoint = f"https://{account_id}.r2.cloudflarestorage.com"

    if not access_key_id or not secret_access_key:
        emit("error", "Missing access_key_id or secret_access_key in wop_r2_config.json")
        return

    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=Config(signature_version="s3v4"),
            region_name="auto"
        )

        # List objects in bucket/prefix
        paginator = s3.get_paginator("list_objects_v2")
        r2_objects = {}
        for page in paginator.paginate(Bucket=bucket, Prefix=f"{prefix}/"):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                filename = key[len(f"{prefix}/"):]
                if filename:
                    r2_objects[filename] = {
                        "key": key,
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"].isoformat(),
                        "etag": obj.get("ETag", "").strip('"')
                    }

        emit("success", f"R2 bucket has {len(r2_objects)} objects under {prefix}/")

        # Cross-reference with local registry
        registry = load_registry()
        local_files = set(registry["entries"].keys())
        r2_files = set(r2_objects.keys())

        not_uploaded = local_files - r2_files
        not_local = r2_files - local_files
        both = local_files & r2_files

        emit("stat", f"Local files:   {len(local_files)}")
        emit("stat", f"R2 objects:    {len(r2_files)}")
        emit("stat", f"Synced:        {len(both)}")
        emit("stat", f"Not uploaded:  {len(not_uploaded)}")
        emit("stat", f"R2-only:       {len(not_local)}")

        if not_uploaded:
            emit("warn", "Local files not yet on R2:")
            for f in sorted(not_uploaded):
                emit("item", f"  [X]{f}")

        if not_local:
            emit("warn", "R2 objects with no local file:")
            for f in sorted(not_local):
                emit("item", f"  ? {f}")

        if both:
            emit("success", f"Synced files ({len(both)}):")
            for f in sorted(both):
                cdn_url = f"https://{cdn_hostname}/{prefix}/{f}" if cdn_hostname else f"r2://{bucket}/{prefix}/{f}"
                emit("item", f"  [OK] {f} -> {cdn_url}")

        # Save R2 report
        report = {
            "generated": datetime.now().isoformat(),
            "bucket": bucket,
            "prefix": prefix,
            "cdn_hostname": cdn_hostname,
            "r2_objects": r2_objects,
            "not_uploaded": sorted(not_uploaded),
            "not_local": sorted(not_local),
            "synced": sorted(both)
        }
        with open(R2_REPORT_FILE, "w") as f:
            json.dump(report, f, indent=2)
        emit("info", f"R2 report saved to {R2_REPORT_FILE.name}")

        # Update registry with R2 status
        for filename in both:
            if filename in registry["entries"]:
                obj = r2_objects[filename]
                cdn_url = f"https://{cdn_hostname}/{prefix}/{filename}" if cdn_hostname else None
                registry["entries"][filename]["r2_uploaded"] = True
                registry["entries"][filename]["r2_url"] = f"r2://{bucket}/{prefix}/{filename}"
                registry["entries"][filename]["cdn_url"] = cdn_url
        save_registry(registry)

    except Exception as e:
        emit("error", f"R2 connection failed: {e}")
        emit("info", "Check access_key_id, secret_access_key, and account_id in wop_r2_config.json")


def cmd_r2_check(args, stream=False):
    """Check R2 upload status from saved report."""
    emit = _make_emitter(stream)
    if not R2_REPORT_FILE.exists():
        emit("warn", "No R2 report found. Run 'r2-audit' first.")
        return
    with open(R2_REPORT_FILE) as f:
        report = json.load(f)
    emit("info", f"R2 report from: {report.get('generated', 'unknown')}")
    emit("stat", f"Synced: {len(report.get('synced', []))}")
    emit("stat", f"Not uploaded: {len(report.get('not_uploaded', []))}")
    emit("stat", f"R2-only: {len(report.get('not_local', []))}")


def cmd_refactor(args, stream=False):
    """
    Generate rename script and template update patches (dry run by default).
    This is Runbook Prompt 2 — generates but does not execute.
    """
    emit = _make_emitter(stream)
    emit("status", "Generating refactor plan (dry run)...")

    # Load rename mapping if provided
    mapping_file = getattr(args, "mapping", None)
    if not mapping_file or not Path(mapping_file).exists():
        emit("warn", "No rename mapping file provided. Use --mapping path/to/mapping.json")
        emit("info", "Mapping format: {\"old_filename.mp3\": \"new_filename.mp3\", ...}")
        return

    with open(mapping_file) as f:
        mapping = json.load(f)

    registry = load_registry()
    rename_ops = []
    ref_updates = []

    for old_name, new_name in mapping.items():
        if old_name not in registry["entries"]:
            emit("warn", f"  {old_name} — not in registry (skipping)")
            continue
        entry = registry["entries"][old_name]
        old_path = Path(entry["path"])
        new_path = old_path.parent / new_name

        rename_ops.append({"from": str(old_path), "to": str(new_path)})
        emit("item", f"  RENAME: {old_name} -> {new_name}")

        for ref in entry.get("refs", []):
            ref_updates.append({
                "file": ref["file"],
                "old_url": ref["url"],
                "new_url": ref["url"].replace(old_name, new_name),
                "line": ref["line"]
            })

    emit("stat", f"Rename operations: {len(rename_ops)}")
    emit("stat", f"Template ref updates: {len(ref_updates)}")

    if getattr(args, "execute", False):
        emit("status", "Executing renames...")
        for op in rename_ops:
            try:
                Path(op["from"]).rename(op["to"])
                emit("success", f"  [OK] {Path(op['from']).name} -> {Path(op['to']).name}")
            except Exception as e:
                emit("error", f"  [X]{op['from']}: {e}")
        emit("warn", "Template ref updates must be applied manually or via Claude Code.")
    else:
        emit("info", "Dry run complete. Use --execute to apply renames.")

    return {"rename_ops": rename_ops, "ref_updates": ref_updates}


# ─────────────────────────────────────────────────────────────────────────────
# STREAMING EMITTER
# ─────────────────────────────────────────────────────────────────────────────

def _make_emitter(stream=False):
    """Returns an emit function. If stream=True, outputs SSE-compatible JSON lines."""
    if stream:
        def emit(event_type, message):
            data = json.dumps({"type": event_type, "message": message})
            print(f"data: {data}", flush=True)
    else:
        def emit(event_type, message):
            prefix = {
                "status": "->", "success": "[OK]", "warn": "[!]", "error": "[X]",
                "info": "[i]", "stat": "*", "item": " ", "report": "", "entry": "  "
            }.get(event_type, "-")
            print(f"{prefix} {message}")
    return emit


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRY HTTP API (for server integration)
# ─────────────────────────────────────────────────────────────────────────────

def get_registry_data():
    """Return current registry as dict for API responses."""
    return load_registry()


def run_command_streaming(command, params=None):
    """Run a command and yield SSE event lines."""
    import io
    import contextlib

    args = argparse.Namespace(**(params or {}))

    cmd_map = {
        "audit": cmd_audit,
        "check": cmd_check,
        "report": cmd_report,
        "r2-audit": cmd_r2_audit,
        "r2-check": cmd_r2_check,
        "refactor": cmd_refactor,
    }

    if command not in cmd_map:
        yield f"data: {json.dumps({'type': 'error', 'message': f'Unknown command: {command}'})}\n\n"
        return

    # Capture stdout as SSE stream
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        cmd_map[command](args, stream=True)
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

    for line in output.splitlines():
        if line.startswith("data:"):
            yield line + "\n\n"

    yield f"data: {json.dumps({'type': 'done', 'message': 'Command complete'})}\n\n"


# ─────────────────────────────────────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="WoP Link Registry — Audio asset management for Words of Plainness"
    )
    subparsers = parser.add_subparsers(dest="command")

    # audit
    subparsers.add_parser("audit", help="Full audit: scan files + template refs + cross-reference")

    # check
    subparsers.add_parser("check", help="Quick check against existing registry")

    # report
    subparsers.add_parser("report", help="Human-readable summary report")

    # r2-audit
    r2_audit_p = subparsers.add_parser("r2-audit", help="Audit R2 bucket upload status")
    r2_audit_p.add_argument("--bucket", help="R2 bucket name (default: from config)")
    r2_audit_p.add_argument("--prefix", help="R2 prefix (default: web)")
    r2_audit_p.add_argument("--cdn", help="CDN hostname (default: from config)")

    # r2-check
    subparsers.add_parser("r2-check", help="Check R2 status from saved report")

    # refactor
    refactor_p = subparsers.add_parser("refactor", help="Generate rename plan (dry run)")
    refactor_p.add_argument("--mapping", help="Path to JSON rename mapping file")
    refactor_p.add_argument("--execute", action="store_true", help="Execute renames (not dry run)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmd_map = {
        "audit": cmd_audit,
        "check": cmd_check,
        "report": cmd_report,
        "r2-audit": cmd_r2_audit,
        "r2-check": cmd_r2_check,
        "refactor": cmd_refactor,
    }

    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
