"""
WoP R2 Banner Upload — /articles/ banner image set (boto3 / S3 API)

Uploads the optimized WebP banner variants to Cloudflare R2 under the
wop-media/web/banners/ prefix.

Why boto3 and not wrangler: `wrangler r2 object put` authenticates via the
Cloudflare account OAuth / API token, NOT the R2 S3 keys, and returns 403 for
this bucket. The reliable path is the S3-compatible endpoint
https://<account_id>.r2.cloudflarestorage.com signed with the
access_key_id / secret_access_key in tools/wop_r2_config.json.

Usage:
    python tools/wop_r2_upload_banners.py --source <folder> [--dry-run]

The source folder is the extracted `web/banners` directory from
wop-articles-banners-webp.zip. Keys are written as web/banners/<filename>,
matching the URLs baked into src/_data/banners.json.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import boto3
from botocore.config import Config

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "tools" / "wop_r2_config.json"

KEY_PREFIX = "web/banners"
CONTENT_TYPE = "image/webp"
CACHE_CONTROL = "public, max-age=31536000, immutable"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def make_client(cfg):
    return boto3.client(
        "s3",
        endpoint_url=f"https://{cfg['account_id']}.r2.cloudflarestorage.com",
        aws_access_key_id=cfg["access_key_id"],
        aws_secret_access_key=cfg["secret_access_key"],
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True,
                    help="Folder containing the *.webp banner variants")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = Path(args.source)
    if not src.is_dir():
        sys.exit(f"Source folder not found: {src}")

    files = sorted(p for p in src.iterdir() if p.suffix.lower() == ".webp")
    if not files:
        sys.exit(f"No .webp files found in: {src}")

    cfg = load_config()
    bucket = cfg["default_bucket"]
    cdn = cfg["cdn_hostname"]

    print(f"Bucket   : {bucket}")
    print(f"Key path : {KEY_PREFIX}/")
    print(f"CDN base : https://{cdn}/{KEY_PREFIX}/")
    print(f"Files    : {len(files)}"
          f"  ({sum(p.stat().st_size for p in files) / 1_048_576:.2f} MB)")
    if args.dry_run:
        print("MODE     : DRY RUN — nothing will be uploaded")
    print("=" * 70)

    client = None if args.dry_run else make_client(cfg)

    ok = 0
    failed = []
    for path in files:
        key = f"{KEY_PREFIX}/{path.name}"
        if args.dry_run:
            print(f"  [dry-run] {key}")
            continue
        try:
            with open(path, "rb") as fh:
                client.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=fh.read(),
                    ContentType=CONTENT_TYPE,
                    CacheControl=CACHE_CONTROL,
                )
            ok += 1
            print(f"  ok  {key}")
        except Exception as exc:  # noqa: BLE001
            failed.append((key, exc))
            print(f"  FAIL {key}: {exc}")

    print("=" * 70)
    if args.dry_run:
        print(f"DRY RUN complete — {len(files)} file(s) would be uploaded")
        return

    print(f"Uploaded {ok}/{len(files)}")
    if failed:
        print(f"FAILURES ({len(failed)}):")
        for key, exc in failed:
            print(f"  {key}: {exc}")
        sys.exit(1)

    # Verify every object landed, via the S3 API (authoritative; the CDN edge
    # filters plain fetches by User-Agent and can answer 403 to a healthy object).
    print("Verifying with head_object…")
    missing = []
    for path in files:
        key = f"{KEY_PREFIX}/{path.name}"
        try:
            head = client.head_object(Bucket=bucket, Key=key)
            if head["ContentLength"] != path.stat().st_size:
                missing.append(f"{key} (size mismatch)")
        except Exception as exc:  # noqa: BLE001
            missing.append(f"{key} ({exc})")
    if missing:
        print("VERIFY FAILED:")
        for m in missing:
            print(f"  {m}")
        sys.exit(1)
    print(f"ALL CLEAR — {len(files)} object(s) present with matching sizes.")


if __name__ == "__main__":
    main()
