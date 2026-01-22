#!/usr/bin/env python3
"""
Format timestamps JSON as JavaScript array for direct pasting into HTML.

Usage:
    python format-for-html.py chapter-01-timestamps.json

This will output JavaScript code you can paste directly into the HTML file.
"""

import json
import sys

def format_timestamps_for_js(timestamps):
    """Format timestamps as JavaScript array entries."""
    lines = []
    lines.append("const sentenceTimestamps = [")
    
    for ts in timestamps:
        idx = ts["index"]
        start = ts["start"]
        end = ts["end"]
        lines.append(f'    {{ index: {idx}, start: {start}, end: {end} }},')
    
    lines.append("];")
    return "\n".join(lines)

def main():
    if len(sys.argv) < 2:
        print("Usage: python format-for-html.py <timestamps.json>")
        print("\nThis formats the JSON for direct pasting into the HTML file.")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    with open(input_file, "r", encoding="utf-8") as f:
        timestamps = json.load(f)
    
    js_code = format_timestamps_for_js(timestamps)
    
    print("=" * 60)
    print("COPY THE FOLLOWING INTO YOUR HTML FILE")
    print("(Replace the existing sentenceTimestamps array around line 2162)")
    print("=" * 60)
    print()
    print(js_code)
    print()
    print("=" * 60)
    
    # Also save to file
    output_file = input_file.replace(".json", "-js.txt")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(js_code)
    
    print(f"\nAlso saved to: {output_file}")

if __name__ == "__main__":
    main()
