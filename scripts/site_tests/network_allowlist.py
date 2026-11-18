"""Network allow-list for wordsofplainness.org pages (acceptance check 1 of the device-only journal).

Ruling SITE-JOURNAL-CHECK1-NETWORK, option 3 (Aaron, 17 Nov 2026):
  * Reader actions (write, edit, download, clear) must cause zero off-site requests,
    apart from loading the download libraries.
  * A page load may reach only the hosts below: Google Fonts, media.wordsofplainness.org,
    YouTube on pages that embed it, and cdnjs OpenSeadragon on the pages that use it.
    Any other host fails.

One reusable file so later runs check the same thing. Written for CODE-SITE-18 (SITE step 27).
Import it from any test:

    from network_allowlist import classify_page_load, classify_action, is_api_host
"""
from urllib.parse import urlparse

# The ministry's form API. No page load and no reader action may reach it; only a
# submitted contact, corrections or newsletter form does.
API_HOSTS = {"apowner.pythonanywhere.com"}

# Every page.
PAGE_LOAD_HOSTS = {
    "fonts.googleapis.com": "Google Fonts stylesheet",
    "fonts.gstatic.com": "Google Fonts files",
    "media.wordsofplainness.org": "media CDN (anthem audio, narration, images)",
}

# Only on pages that embed YouTube. Requests made from inside a YouTube iframe are
# YouTube's own and are counted under this heading, whatever host they go to.
YOUTUBE_HOSTS = {
    "www.youtube.com", "youtube.com", "m.youtube.com", "www.youtube-nocookie.com",
    "i.ytimg.com", "s.ytimg.com", "i9.ytimg.com", "yt3.ggpht.com",
}
YOUTUBE_FRAME_HOSTS = {"www.youtube.com", "www.youtube-nocookie.com", "youtube.com"}

# Only on the pages that use OpenSeadragon (the Living Tree, the Articles presentation).
OPENSEADRAGON_PREFIX = "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/"

# The download libraries, loaded only when the reader asks for that format
# (js/wop-reflections-panel.js). The Word writer is this site's own /js/wop-docx.js.
DOWNLOAD_LIBRARY_URLS = {
    "https://cdnjs.cloudflare.com/ajax/libs/pdfmake/0.2.20/pdfmake.min.js",
    "https://cdnjs.cloudflare.com/ajax/libs/pdfmake/0.2.20/vfs_fonts.min.js",
}


def host_of(url):
    return (urlparse(url).hostname or "").lower()


def is_api_host(url):
    return host_of(url) in API_HOSTS


def is_same_origin(url, site_origin):
    return url.startswith(site_origin) or url.startswith("data:") or url.startswith("blob:") or url.startswith("about:")


def classify_page_load(url, site_origin, frame_url="", page_embeds_youtube=False, page_uses_openseadragon=False):
    """Return (allowed: bool, reason: str) for a request seen while a page loads."""
    if is_same_origin(url, site_origin):
        return True, "site itself"
    host = host_of(url)
    if host in API_HOSTS:
        return False, "form API reached during page load"
    if host in PAGE_LOAD_HOSTS:
        return True, PAGE_LOAD_HOSTS[host]
    frame_host = host_of(frame_url) if frame_url else ""
    if page_embeds_youtube and (host in YOUTUBE_HOSTS or frame_host in YOUTUBE_FRAME_HOSTS):
        return True, "YouTube (page embeds YouTube)"
    if page_uses_openseadragon and url.startswith(OPENSEADRAGON_PREFIX):
        return True, "cdnjs OpenSeadragon (page uses it)"
    return False, "host not on the allow-list"


def classify_action(url, site_origin):
    """Return (allowed: bool, reason: str) for a request caused by a reader action
    (write, edit, download, clear)."""
    if is_same_origin(url, site_origin):
        return True, "site itself"
    if url.split("#")[0] in DOWNLOAD_LIBRARY_URLS:
        return True, "download library (loaded on request)"
    return False, "off-site request caused by a reader action"
