#!/usr/bin/env python3
"""
WoP Publish Skill — Catalog Update
====================================
Reads and writes the WoP_ISRC_Catalog.xlsx spreadsheet.
Adds new track rows, updates pipeline checkboxes, queries existing entries.

Called by the /publish skill pipeline at Step 9.

USAGE:
    # Add a new track row
    python catalog_update.py add \
        --catalog WoP_ISRC_Catalog.xlsx \
        --filename "04_2_When_God_Becomes_Real_Soul_Worship" \
        --title "When God Becomes Real" \
        --prefix "##" \
        --chapter 4 \
        --version 2 \
        --style "Soul Worship" \
        [--track-num 7] \
        [--notes "Alt arrangement for seekers"]

    # Update pipeline checkboxes for an existing row
    python catalog_update.py update \
        --catalog WoP_ISRC_Catalog.xlsx \
        --filename "04_2_When_God_Becomes_Real_Soul_Worship" \
        --archive-wav ✓ \
        --distro-wav ✓ \
        --web-mp3 ✓ \
        --website-live ✓ \
        --album-art "✓ Embedded"

    # List all tracks in catalog
    python catalog_update.py list \
        --catalog WoP_ISRC_Catalog.xlsx

    # Set ISRC after DistroKid assignment
    python catalog_update.py set-isrc \
        --catalog WoP_ISRC_Catalog.xlsx \
        --filename "04_2_When_God_Becomes_Real_Soul_Worship" \
        --isrc "USXX12600042"

DEPENDENCIES:
    pip install openpyxl
"""

import argparse
import os
import sys
from datetime import datetime

try:
    from openpyxl import Workbook, load_workbook
    OPENPYXL_OK = True
except ImportError:
    OPENPYXL_OK = False


# ── COLUMN MAP (matches WoP_ISRC_Catalog.xlsx "Track Catalog" sheet) ──
#    A=ISRC  B=Filename  C=Title  D=Prefix  E=Chapter  F=Version
#    G=Style  H=Artist  I=Album  J=Track#  K=Year  L=Genre
#    M=Composer  N=Copyright  O=Release Date  P=Album Art
#    Q=Archive WAV  R=Distro WAV  S=Web MP3  T=Website Live
#    U=DistroKid  V=Notes

DEFAULTS = {
    "artist": "Words of Plainness",
    "album": "Words of Plainness: Musical Testimonies",
    "year": "2026",
    "genre": "Christian / Sacred",
    "composer": "Aaron J Powner",
    "copyright": "© 2026 Aaron J Powner",
}


HEADERS = [
    "ISRC", "Filename", "Title", "Prefix", "Chapter", "Version",
    "Style", "Artist", "Album", "Track #", "Year", "Genre",
    "Composer", "Copyright", "Release Date", "Album Art",
    "Archive WAV", "Distro WAV", "Web MP3", "Website Live",
    "DistroKid", "Notes",
]


def create_new_catalog(path):
    """Bootstrap a new WoP_ISRC_Catalog.xlsx with headers."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Track Catalog"
    for col_idx, header in enumerate(HEADERS, 1):
        ws.cell(row=1, column=col_idx, value=header)

    # Summary sheet
    summary = wb.create_sheet("Summary")
    summary["A1"] = "Metric"
    summary["B1"] = "Value"
    summary["A2"] = "Last Updated"
    summary["B2"] = datetime.now().strftime("%Y-%m-%d")
    summary["A3"] = "Total Tracks"
    summary["B3"] = 0

    os.makedirs(os.path.dirname(path), exist_ok=True)
    wb.save(path)
    wb.close()


def find_row_by_filename(ws, filename):
    """Find row number matching a filename in column B."""
    for row in range(2, ws.max_row + 1):
        val = ws[f"B{row}"].value
        if val and str(val).strip() == filename:
            return row
    return None


def find_next_empty_row(ws):
    """Find the first empty row (no title in column C)."""
    for row in range(2, ws.max_row + 2):
        if not ws[f"C{row}"].value:
            return row
    return ws.max_row + 1


def cmd_add(args):
    """Add a new track row to the catalog."""
    wb = load_workbook(args.catalog)
    ws = wb["Track Catalog"]

    # Check for duplicates
    existing = find_row_by_filename(ws, args.filename)
    if existing:
        print(f"  WARNING: Track already exists at row {existing}: {args.filename}")
        print(f"      Use 'update' command to modify existing entries.")
        wb.close()
        return 1

    row = find_next_empty_row(ws)

    # Write all columns
    ws[f"A{row}"] = ""  # ISRC — blank until DistroKid assigns
    ws[f"B{row}"] = args.filename
    ws[f"C{row}"] = args.title
    ws[f"D{row}"] = args.prefix
    ws[f"E{row}"] = args.chapter if args.chapter else ""
    ws[f"F{row}"] = args.version
    ws[f"G{row}"] = args.style
    ws[f"H{row}"] = DEFAULTS["artist"]
    ws[f"I{row}"] = args.album if args.album else DEFAULTS["album"]
    ws[f"J{row}"] = args.track_num if args.track_num else ""
    ws[f"K{row}"] = DEFAULTS["year"]
    ws[f"L{row}"] = DEFAULTS["genre"]
    ws[f"M{row}"] = DEFAULTS["composer"]
    ws[f"N{row}"] = DEFAULTS["copyright"]
    ws[f"O{row}"] = ""  # Release date — set during DistroKid upload
    ws[f"P{row}"] = "Pending"  # Album art
    ws[f"Q{row}"] = "--"  # Archive WAV
    ws[f"R{row}"] = "--"  # Distro WAV
    ws[f"S{row}"] = "--"  # Web MP3
    ws[f"T{row}"] = "--"  # Website Live
    ws[f"U{row}"] = "--"  # DistroKid
    ws[f"V{row}"] = args.notes if args.notes else ""

    # Update Summary sheet total
    try:
        summary_ws = wb["Summary"]
        # Count non-empty title cells (data rows)
        count = sum(1 for r in range(2, ws.max_row + 1) if ws[f"C{r}"].value)
        summary_ws["B3"] = count
    except Exception:
        pass

    wb.save(args.catalog)
    wb.close()

    print(f"  [OK] Added to catalog at row {row}: {args.title}")
    print(f"      Filename: {args.filename}")
    return 0


def cmd_update(args):
    """Update pipeline checkboxes for an existing track."""
    wb = load_workbook(args.catalog)
    ws = wb["Track Catalog"]

    row = find_row_by_filename(ws, args.filename)
    if not row:
        print(f"  [FAIL] Track not found: {args.filename}")
        wb.close()
        return 1

    updates = {}
    if args.album_art:
        updates["P"] = args.album_art
    if args.archive_wav:
        updates["Q"] = args.archive_wav
    if args.distro_wav:
        updates["R"] = args.distro_wav
    if args.web_mp3:
        updates["S"] = args.web_mp3
    if args.website_live:
        updates["T"] = args.website_live
    if args.distrokid:
        updates["U"] = args.distrokid

    for col, val in updates.items():
        ws[f"{col}{row}"] = val

    wb.save(args.catalog)
    wb.close()

    print(f"  [OK] Updated row {row}: {args.filename}")
    for col, val in updates.items():
        print(f"      Column {col}: {val}")
    return 0


def cmd_set_isrc(args):
    """Set ISRC code for a track (after DistroKid assignment)."""
    wb = load_workbook(args.catalog)
    ws = wb["Track Catalog"]

    row = find_row_by_filename(ws, args.filename)
    if not row:
        print(f"  [FAIL] Track not found: {args.filename}")
        wb.close()
        return 1

    ws[f"A{row}"] = args.isrc
    wb.save(args.catalog)
    wb.close()

    print(f"  [OK] ISRC set for row {row}: {args.isrc}")
    return 0


def cmd_list(args):
    """List all tracks in catalog."""
    wb = load_workbook(args.catalog, data_only=True)
    ws = wb["Track Catalog"]

    print(f"\n{'=' * 80}")
    print(f"  WoP ISRC Catalog -- Track Listing")
    print(f"{'=' * 80}")
    print(f"  {'#':>3}  {'Title':<35} {'Style':<25} {'Pipeline'}")
    print(f"  {'-' * 3}  {'-' * 35} {'-' * 25} {'-' * 15}")

    count = 0
    for row in range(2, ws.max_row + 1):
        title = ws[f"C{row}"].value
        if not title:
            continue
        count += 1

        style = ws[f"G{row}"].value or "--"
        archive = ws[f"Q{row}"].value or "--"
        distro = ws[f"R{row}"].value or "--"
        web = ws[f"S{row}"].value or "--"
        live = ws[f"T{row}"].value or "--"
        dk = ws[f"U{row}"].value or "--"

        pipeline = f"A:{archive} D:{distro} W:{web} L:{live} DK:{dk}"
        print(f"  {count:>3}  {str(title):<35} {str(style):<25} {pipeline}")

    print(f"\n  Total: {count} tracks")
    print(f"{'=' * 80}\n")

    wb.close()
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="WoP Publish Skill — Catalog Update"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── add ──
    p_add = sub.add_parser("add", help="Add new track to catalog")
    p_add.add_argument("--catalog", required=True)
    p_add.add_argument("--filename", required=True)
    p_add.add_argument("--title", required=True)
    p_add.add_argument("--prefix", default="##")
    p_add.add_argument("--chapter", type=int, default=0)
    p_add.add_argument("--version", type=int, default=1)
    p_add.add_argument("--style", default="")
    p_add.add_argument("--album", default="")
    p_add.add_argument("--track-num", type=int, default=0)
    p_add.add_argument("--notes", default="")

    # ── update ──
    p_up = sub.add_parser("update", help="Update pipeline checkboxes")
    p_up.add_argument("--catalog", required=True)
    p_up.add_argument("--filename", required=True)
    p_up.add_argument("--album-art", default=None)
    p_up.add_argument("--archive-wav", default=None)
    p_up.add_argument("--distro-wav", default=None)
    p_up.add_argument("--web-mp3", default=None)
    p_up.add_argument("--website-live", default=None)
    p_up.add_argument("--distrokid", default=None)

    # ── set-isrc ──
    p_isrc = sub.add_parser("set-isrc", help="Set ISRC code")
    p_isrc.add_argument("--catalog", required=True)
    p_isrc.add_argument("--filename", required=True)
    p_isrc.add_argument("--isrc", required=True)

    # ── list ──
    p_list = sub.add_parser("list", help="List all catalog tracks")
    p_list.add_argument("--catalog", required=True)

    args = parser.parse_args()

    if not OPENPYXL_OK:
        print("ERROR: openpyxl not installed. Run: pip install openpyxl")
        sys.exit(1)

    if not os.path.exists(args.catalog):
        create_new_catalog(args.catalog)
        print(f"  [NEW] Created catalog: {args.catalog}")

    if args.command == "add":
        return cmd_add(args)
    elif args.command == "update":
        return cmd_update(args)
    elif args.command == "set-isrc":
        return cmd_set_isrc(args)
    elif args.command == "list":
        return cmd_list(args)


if __name__ == "__main__":
    sys.exit(main())
