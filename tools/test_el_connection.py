"""
Quick connectivity test for ElevenLabs REST API.
Calls the /v1/voices endpoint — lightweight, no audio generated.
Run this before the full chunk regeneration script.

Usage:
    python tools\test_el_connection.py
"""

import getpass
import urllib.request
import urllib.error
import json

print("Testing ElevenLabs REST API connectivity...")
print("(Uses urllib from Python standard library — no third-party packages)")

api_key = getpass.getpass("Enter your ElevenLabs API key (hidden): ").strip()

req = urllib.request.Request(
    "https://api.elevenlabs.io/v1/voices",
    headers={"xi-api-key": api_key},
    method="GET"
)

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        voices = data.get("voices", [])
        print(f"\nSUCCESS — Connected to ElevenLabs API.")
        print(f"  {len(voices)} voices found in your account.")
        # Find Aaron's voice and Jonathan's
        for v in voices:
            if v["voice_id"] in ("As8zJaZyH4MAgaQ93FMc", "PIGsltMj3gFMR34aFDI3"):
                print(f"  Found: {v['name']} ({v['voice_id']})")
        print("\nReady to proceed with chunk regeneration.")

except urllib.error.HTTPError as e:
    print(f"\nHTTP ERROR {e.code}: {e.reason}")
    print("Check your API key and try again.")

except urllib.error.URLError as e:
    print(f"\nCONNECTION ERROR: {e.reason}")
    print("\nThe ElevenLabs API is not reachable from Python on this machine.")
    print("This is likely a Windows Firewall rule blocking outbound HTTPS.")
    print("\nTo fix:")
    print("  1. Open Windows Security")
    print("  2. Firewall & network protection")
    print("  3. Advanced settings")
    print("  4. Outbound rules -> New Rule")
    print("  5. Program -> Browse to your Python executable")
    print("     (likely: C:\\Python313\\python.exe or")
    print("      C:\\Users\\aaron\\AppData\\Local\\Programs\\Python\\Python313\\python.exe)")
    print("  6. Allow the connection")
    print("  7. Apply to all profiles (Domain, Private, Public)")
    print("  8. Name it: Python ElevenLabs API")
    print("\nAlternatively, run this command to find your Python path:")
    print("  where python")

except Exception as e:
    print(f"\nUNEXPECTED ERROR: {type(e).__name__}: {e}")
