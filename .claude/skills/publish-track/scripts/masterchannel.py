#!/usr/bin/env python3
"""
WoP Publish Skill — Masterchannel API Integration
====================================================
Scaffold for automated AI mastering via Masterchannel's B2B REST API.

API Documentation: https://masterchannelai.readme.io
Integration Portal: https://integrate.masterchannel.ai

STATUS: SCAFFOLD — requires API partner signup and credentials.
The /publish skill falls back to manual mastering when credentials
are not configured.

SETUP (one-time):
    1. Sign up at integrate.masterchannel.ai as API partner
    2. Obtain CLIENT_ID and CLIENT_SECRET
    3. Set environment variables:
       export MASTERCHANNEL_CLIENT_ID="your_client_id"
       export MASTERCHANNEL_CLIENT_SECRET="your_client_secret"

USAGE:
    python masterchannel.py \
        --source pre-master.wav \
        --output-dir ./mastered/ \
        [--engine standard] \
        [--genre folk] \
        [--loudness -14]

API WORKFLOW:
    1. POST /token           → Authenticate, get bearer token
    2. POST /files           → Upload source WAV
    3. POST /jobs            → Create mastering job
    4. GET  /jobs/{id}       → Poll for completion
    5. GET  /streams/{id}    → Download mastered result

PRICING: Starts at $1.50/master. Previews are free.

DEPENDENCIES:
    pip install requests
"""

import argparse
import os
import sys
import time

try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False


# ── API CONFIGURATION ──────────────────────────────────────────────
API_BASE = "https://integrate.masterchannel.ai/api/v2"
TOKEN_ENDPOINT = f"{API_BASE}/token"
FILES_ENDPOINT = f"{API_BASE}/files"
JOBS_ENDPOINT = f"{API_BASE}/jobs"
STREAMS_ENDPOINT = f"{API_BASE}/streams"

# WoP mastering defaults
DEFAULT_ENGINE = "standard"   # NOT "wez_clarke" (his pop/R&B bias fights organic warmth)
DEFAULT_GENRE = "folk"        # Closest available; Americana not offered
DEFAULT_LOUDNESS = -14        # LUFS — Spotify/Apple standard


def get_credentials():
    """Read API credentials from environment."""
    client_id = os.environ.get("MASTERCHANNEL_CLIENT_ID")
    client_secret = os.environ.get("MASTERCHANNEL_CLIENT_SECRET")
    return client_id, client_secret


def authenticate(client_id, client_secret):
    """
    POST /token — Authenticate and receive bearer token.
    Returns token string or None on failure.
    """
    response = requests.post(TOKEN_ENDPOINT, json={
        "client_id": client_id,
        "client_secret": client_secret,
    })

    if response.status_code == 200:
        data = response.json()
        return data.get("access_token") or data.get("token")
    else:
        print(f"  ✗  Auth failed: {response.status_code} — {response.text}")
        return None


def upload_file(token, filepath):
    """
    POST /files — Upload source audio file.
    Returns file_id or None.
    """
    headers = {"Authorization": f"Bearer {token}"}
    filename = os.path.basename(filepath)

    with open(filepath, "rb") as f:
        response = requests.post(
            FILES_ENDPOINT,
            headers=headers,
            files={"file": (filename, f, "audio/wav")},
        )

    if response.status_code in (200, 201):
        data = response.json()
        file_id = data.get("id") or data.get("file_id")
        print(f"  ✓  Uploaded: {filename} → file_id={file_id}")
        return file_id
    else:
        print(f"  ✗  Upload failed: {response.status_code} — {response.text}")
        return None


def create_mastering_job(token, file_id, engine=DEFAULT_ENGINE,
                         genre=DEFAULT_GENRE, loudness=DEFAULT_LOUDNESS):
    """
    POST /jobs — Create a mastering job.
    Returns job_id or None.
    """
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "file_id": file_id,
        "engine": engine,
        "genre": genre,
        "target_loudness": loudness,
    }

    response = requests.post(JOBS_ENDPOINT, headers=headers, json=payload)

    if response.status_code in (200, 201):
        data = response.json()
        job_id = data.get("id") or data.get("job_id")
        print(f"  ✓  Mastering job created: job_id={job_id}")
        return job_id
    else:
        print(f"  ✗  Job creation failed: {response.status_code} — {response.text}")
        return None


def poll_job(token, job_id, max_wait=600, interval=10):
    """
    GET /jobs/{id} — Poll until mastering completes.
    Returns job data dict or None on timeout/failure.
    """
    headers = {"Authorization": f"Bearer {token}"}
    elapsed = 0

    while elapsed < max_wait:
        response = requests.get(f"{JOBS_ENDPOINT}/{job_id}", headers=headers)

        if response.status_code == 200:
            data = response.json()
            status = data.get("status", "").lower()

            if status in ("completed", "done", "finished"):
                print(f"  ✓  Mastering complete (elapsed: {elapsed}s)")
                return data
            elif status in ("failed", "error"):
                print(f"  ✗  Mastering failed: {data}")
                return None
            else:
                print(f"  ⏳ Status: {status} ({elapsed}s elapsed)")
        else:
            print(f"  ⚠  Poll error: {response.status_code}")

        time.sleep(interval)
        elapsed += interval

    print(f"  ✗  Timed out after {max_wait}s")
    return None


def download_result(token, job_data, output_dir):
    """
    GET /streams/{id} — Download the mastered WAV.
    Returns output filepath or None.
    """
    headers = {"Authorization": f"Bearer {token}"}

    # Extract stream/result ID from job data
    stream_id = (job_data.get("result_id") or job_data.get("stream_id")
                 or job_data.get("id"))

    response = requests.get(
        f"{STREAMS_ENDPOINT}/{stream_id}",
        headers=headers,
        stream=True,
    )

    if response.status_code == 200:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "mastered_output.wav")

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"  ✓  Downloaded mastered file: {output_path} ({size_mb:.1f} MB)")
        return output_path
    else:
        print(f"  ✗  Download failed: {response.status_code} — {response.text}")
        return None


def master_track(source_path, output_dir, engine=DEFAULT_ENGINE,
                 genre=DEFAULT_GENRE, loudness=DEFAULT_LOUDNESS):
    """
    Full mastering pipeline: auth → upload → job → poll → download.
    Returns path to mastered WAV or None.
    """
    client_id, client_secret = get_credentials()

    if not client_id or not client_secret:
        print("  ⚠  Masterchannel API credentials not configured.")
        print("     Set MASTERCHANNEL_CLIENT_ID and MASTERCHANNEL_CLIENT_SECRET.")
        print("     Falling back to manual mastering.")
        return None

    print(f"\n{'═' * 60}")
    print(f"  Masterchannel AI Mastering")
    print(f"{'═' * 60}")
    print(f"  Source:   {source_path}")
    print(f"  Engine:   {engine}")
    print(f"  Genre:    {genre}")
    print(f"  Loudness: {loudness} LUFS")
    print(f"{'═' * 60}\n")

    # Step 1: Authenticate
    print("── Authenticating ──")
    token = authenticate(client_id, client_secret)
    if not token:
        return None

    # Step 2: Upload
    print("\n── Uploading Source ──")
    file_id = upload_file(token, source_path)
    if not file_id:
        return None

    # Step 3: Create job
    print("\n── Creating Mastering Job ──")
    job_id = create_mastering_job(token, file_id, engine, genre, loudness)
    if not job_id:
        return None

    # Step 4: Poll for completion
    print("\n── Waiting for Mastering ──")
    job_data = poll_job(token, job_id)
    if not job_data:
        return None

    # Step 5: Download result
    print("\n── Downloading Result ──")
    result_path = download_result(token, job_data, output_dir)
    return result_path


def main():
    parser = argparse.ArgumentParser(
        description="WoP Publish Skill — Masterchannel API Integration"
    )
    parser.add_argument("--source", required=True, help="Source WAV to master")
    parser.add_argument("--output-dir", default=".", help="Output directory")
    parser.add_argument("--engine", default=DEFAULT_ENGINE)
    parser.add_argument("--genre", default=DEFAULT_GENRE)
    parser.add_argument("--loudness", type=int, default=DEFAULT_LOUDNESS)
    parser.add_argument("--check", action="store_true",
                        help="Just check if credentials are configured")

    args = parser.parse_args()

    if not REQUESTS_OK:
        print("ERROR: requests not installed. Run: pip install requests")
        sys.exit(1)

    if args.check:
        cid, csec = get_credentials()
        if cid and csec:
            print("✓ Masterchannel API credentials configured")
            sys.exit(0)
        else:
            print("✗ Masterchannel API credentials NOT configured")
            print("  Set MASTERCHANNEL_CLIENT_ID and MASTERCHANNEL_CLIENT_SECRET")
            sys.exit(1)

    if not os.path.exists(args.source):
        print(f"ERROR: Source file not found: {args.source}")
        sys.exit(1)

    result = master_track(args.source, args.output_dir,
                          args.engine, args.genre, args.loudness)

    if result:
        print(f"\n✓ Mastered file ready: {result}")
        sys.exit(0)
    else:
        print("\n✗ Mastering did not complete. Use manual workflow.")
        sys.exit(1)


if __name__ == "__main__":
    main()
