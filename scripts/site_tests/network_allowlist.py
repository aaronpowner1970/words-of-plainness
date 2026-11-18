"""Network allow-list for wordsofplainness.org pages (acceptance check 1 of the device-only journal).

Ruling SITE-JOURNAL-CHECK1-NETWORK, option 3 (Aaron, 17 Nov 2026):
  * Reader actions (write, edit, download, clear) must cause zero off-site requests,
    apart from loading the download libraries.
  * A page load may reach only the hosts below: Google Fonts, media.wordsofplainness.org,
    YouTube on pages that embed it, and cdnjs OpenSeadragon on the pages that use it.
    Any other host fails.

One reusable file so later runs check the same thing. Written for CODE-SITE-18 (SITE step 27).

Vercel Web Analytics (ruling SITE-PRIVACY-ANALYTICS-2, option 1; added by CODE-SITE-22, SITE step 33):
  * A page load may reach the site's own /_vercel/insights/ address, and only for the script
    (script.js) and the page view (view). Each page view must carry a page address with no
    query string and no fragment, and no event name or event data. Any other insights
    endpoint (event, identify, group, session) fails.
  * A reader action (write, edit, save, download, clear) may cause no request at all to
    /_vercel/insights/, even though it is on the site's own origin.
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

# Vercel Web Analytics, served from the site's own origin. Only these two endpoints may be
# reached, and only while a page loads; never because of a reader action.
ANALYTICS_PATH_PREFIX = "/_vercel/insights/"
ANALYTICS_ALLOWED_ENDPOINTS = {"script.js", "view"}

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


def is_analytics(url, site_origin):
    """True for a request to the site's own /_vercel/insights/ address."""
    return url.startswith(site_origin.rstrip("/") + ANALYTICS_PATH_PREFIX)


def analytics_payload_problems(post_data):
    """Problems with a page-view body sent to /_vercel/insights/view (empty list = fine).
    The page address ("o") and any referrer ("r") must carry no query string or fragment,
    and there may be no event name or event data ("en", "ed")."""
    import json
    if not post_data:
        return ["page view with no body"]
    try:
        body = json.loads(post_data)
    except ValueError:
        return ["page view body is not JSON"]
    problems = []
    for key in ("o", "r"):
        val = body.get(key)
        if isinstance(val, str) and ("?" in val or "#" in val):
            problems.append(f"{key}={val!r} carries a query string or fragment")
    for key in ("en", "ed"):
        if key in body:
            problems.append(f"custom event field {key!r} present")
    return problems


def classify_analytics(url, site_origin, post_data=None):
    """Return (allowed: bool, reason: str) for a page-load request to /_vercel/insights/."""
    path = urlparse(url).path
    endpoint = path[len(ANALYTICS_PATH_PREFIX):] if path.startswith(ANALYTICS_PATH_PREFIX) else path
    if endpoint not in ANALYTICS_ALLOWED_ENDPOINTS:
        return False, f"analytics endpoint not allowed: {endpoint}"
    if "?" in url or "#" in url:
        return False, "analytics request URL carries a query string or fragment"
    if endpoint == "view":
        problems = analytics_payload_problems(post_data)
        if problems:
            return False, "analytics page view: " + "; ".join(problems)
        return True, "Vercel Web Analytics page view"
    return True, "Vercel Web Analytics script"


def is_same_origin(url, site_origin):
    return url.startswith(site_origin) or url.startswith("data:") or url.startswith("blob:") or url.startswith("about:")


def classify_page_load(url, site_origin, frame_url="", page_embeds_youtube=False, page_uses_openseadragon=False,
                       post_data=None):
    """Return (allowed: bool, reason: str) for a request seen while a page loads."""
    if is_analytics(url, site_origin):
        return classify_analytics(url, site_origin, post_data)
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
    if is_analytics(url, site_origin):
        return False, "analytics request caused by a reader action"
    if is_same_origin(url, site_origin):
        return True, "site itself"
    if url.split("#")[0] in DOWNLOAD_LIBRARY_URLS:
        return True, "download library (loaded on request)"
    return False, "off-site request caused by a reader action"
