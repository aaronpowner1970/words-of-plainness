"""
WoP R2 DZI Upload — Deep Zoom tile pyramids (boto3 / S3 API)

Uploads a libvips/sharp `dzsave` output — <name>.dzi plus the whole
<name>_files/ level tree — to Cloudflare R2, preserving directory structure
under a caller-supplied key prefix.

Why boto3 and not wrangler: `wrangler r2 object put` authenticates via the
Cloudflare account OAuth / API token, NOT the R2 S3 keys, and returns 403 for
this bucket. The reliable path is the S3-compatible endpoint
https://<account_id>.r2.cloudflarestorage.com signed with the
access_key_id / secret_access_key in tools/wop_r2_config.json.

Usage:
    python tools/wop_r2_upload_dzi.py --source <dzi-output-folder> \
        --prefix web/aoid-slides/tree-of-christ [--dry-run]

The source folder is the directory holding tree.dzi and tree_files/. Keys are
written as <prefix>/tree.dzi and <prefix>/tree_files/<level>/<col>_<row>.webp.

Tile pyramids are NOT committed to the repo — R2 is their only home.
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import boto3
from botocore.config import Config

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "tools" / "wop_r2_config.json"

CACHE_CONTROL = "public, max-age=31536000, immutable"
CONTENT_TYPES = {
    ".dzi": "application/xml",
    ".xml": "application/xml",
    ".webp": "image/webp",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".png": "image/png",
}
MAX_WORKERS = 12


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
        config=Config(signature_version="s3v4", max_pool_connections=MAX_WORKERS * 2),
    )


def content_type_for(path: Path) -> str:
    return CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True,
                    help="Folder containing <name>.dzi and <name>_files/")
    ap.add_argument("--prefix", required=True,
                    help="R2 key prefix, e.g. web/aoid-slides/tree-of-christ")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = Path(args.source)
    if not src.is_dir():
        sys.exit(f"Source folder not found: {src}")

    prefix = args.prefix.strip("/")
    files = sorted(p for p in src.rglob("*") if p.is_file())
    if not files:
        sys.exit(f"No files found under: {src}")

    descriptors = [p for p in files if p.suffix.lower() == ".dzi"]
    if not descriptors:
        sys.exit(f"No .dzi descriptor found under: {src} — is this a dzsave output?")

    cfg = load_config()
    bucket = cfg["default_bucket"]
    cdn = cfg["cdn_hostname"]

    # (local path, key) pairs, structure-preserving.
    plan = [(p, f"{prefix}/{p.relative_to(src).as_posix()}") for p in files]
    total_bytes = sum(p.stat().st_size for p in files)

    print(f"Bucket   : {bucket}")
    print(f"Key path : {prefix}/")
    print(f"CDN base : https://{cdn}/{prefix}/")
    print(f"Files    : {len(plan)}  ({total_bytes / 1_048_576:.2f} MB)")
    for d in descriptors:
        print(f"Manifest : https://{cdn}/{prefix}/{d.relative_to(src).as_posix()}")
    if args.dry_run:
        print("MODE     : DRY RUN — nothing will be uploaded")
        print("=" * 70)
        for _, key in plan[:5]:
            print(f"  [dry-run] {key}")
        if len(plan) > 5:
            print(f"  [dry-run] … and {len(plan) - 5} more")
        print(f"DRY RUN complete — {len(plan)} file(s) would be uploaded")
        return

    print("=" * 70)
    client = make_client(cfg)

    def put(item):
        path, key = item
        try:
            with open(path, "rb") as fh:
                client.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=fh.read(),
                    ContentType=content_type_for(path),
                    CacheControl=CACHE_CONTROL,
                )
            return key, None
        except Exception as exc:  # noqa: BLE001
            return key, exc

    ok, failed = 0, []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for i, (key, exc) in enumerate(pool.map(put, plan), 1):
            if exc is None:
                ok += 1
                if i % 100 == 0 or i == len(plan):
                    print(f"  … {i}/{len(plan)}")
            else:
                failed.append((key, exc))
                print(f"  FAIL {key}: {exc}")

    print("=" * 70)
    print(f"Uploaded {ok}/{len(plan)}")
    if failed:
        print(f"FAILURES ({len(failed)}):")
        for key, exc in failed:
            print(f"  {key}: {exc}")
        sys.exit(1)

    # Verify every object landed, via the S3 API (authoritative; the CDN edge
    # filters plain fetches by User-Agent and can answer 403 to a healthy object).
    print("Verifying with head_object…")

    def check(item):
        path, key = item
        try:
            head = client.head_object(Bucket=bucket, Key=key)
            if head["ContentLength"] != path.stat().st_size:
                return f"{key} (size mismatch)"
            if head.get("ContentType") != content_type_for(path):
                return f"{key} (content-type {head.get('ContentType')})"
            return None
        except Exception as exc:  # noqa: BLE001
            return f"{key} ({exc})"

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        missing = [m for m in pool.map(check, plan) if m]

    if missing:
        print("VERIFY FAILED:")
        for m in missing:
            print(f"  {m}")
        sys.exit(1)
    print(f"ALL CLEAR — {len(plan)} object(s) present, sizes and content-types match.")


if __name__ == "__main__":
    main()
