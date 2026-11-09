"""Build src/_data/livingTree.json for the /living-tree/ page (CODE-AOID2-110; inquirer resources added for step 163, CODE-AOID2-112).

Re-run this whenever the AOID2 source library grows. Nothing in the output is typed by hand:
every title, edition, rights class and link comes from the files below, and every link's status
comes from an ordinary HTTP GET made by this script.

Inputs (read only; none is ever edited):
  --inbox       the library inbox: INTAKE_LOG.csv, the *__MANIFEST.csv files and the newest
                CHECKLIST_CORRECTIONS_<date>.md
                (default C:/Users/aaron/Documents/wop-scratch/AOID2_Library_Inbox)
  --checklist   the checklist. Either the project CSV AOID2_Source_Checklist.csv (columns id, family,
                priority, status, text, source_url, alt_source, format_price, what_to_check), or a
                markdown export of its Docs mirror "AOID2 Source Library - Catalog and Acquisition
                Checklist". If omitted, AOID2_Source_Checklist.csv is looked for in the inbox and in
                the repo; there is no other default.
  --codex       Comparison_Principles_Codex.md; branch labels and status wording are checked against
                C4(d) and the build stops if any is missing.
  data-sources/living-tree/branches.json      rows, branches and their places on the picture
  data-sources/living-tree/institutions.csv   who publishes at each host, and what kind of host it is

Outputs:
  src/_data/livingTree.json                   what the page renders (no third-party link is in it)
  data-sources/living-tree/review.json        lists for Aaron's ruling: third-party copies, historic
                                              public copies, dead links, links that need a browser
                                              check, store links, and the checklist-to-id mapping

Link rule (ruled by Aaron, CODE-AOID2-110):
  * Every rendered link goes to the institution's own copy; a landing page beats a raw file where
    both are recorded.
  * FREE_THIRD_PARTY only: the text is listed as "No copy online from the church itself" and the
    third-party link goes to review.json only.
  * PUBLIC_DOMAIN: "Historic text, public copy", with the host named.
  * Sold or print-only: the church's own store page, "Available from <publisher>"; never a file
    that bypasses a sale.
  * Nothing from Aaron's library, R2 or the repo is ever linked.
  * Links are checked with a plain GET (urllib's own default headers). A 401/403/429 or any other
    refusal is recorded as "needs a browser check" and never worked around. A dead link is never
    replaced by a guess.

Inquirer resources (AOID2 step 163, CODE-AOID2-112; approved wording 2.8):
  --sources88   the CODE-AOID2-88 JSON (default C:/Users/aaron/Documents/wop-scratch/
                WoP_AOID2_CODE-AOID2-88_LivingTree_Sources_20261101.json); each branch's
                "inquirer_resources" entries, copied field for field (publisher, title, url)
  data-sources/living-tree/link_checks_<date>.json   the newest two-instrument check record: one
                WebFetch and one separate shell request per link (WebFetch cannot be run from here,
                so this script reads the record and never checks resource links itself)
  A resource is shown only if (a) the CODE-AOID2-88 verification field ("claim_verified") does not
  record it as unverified (UNVERIFIED_RE below), and (b) both instruments loaded it on the record
  (WebFetch OK or PARTIAL, shell 2xx). Anything else is withheld, never worked around, and listed
  with its reasons in review.json "resources.withheld". Chinese House Churches: none, by design.
  The page shows each as a link labelled "<publisher>, <title>", both as the JSON gives them.

Usage:
  python tools/build_living_tree.py --checklist <file> [--no-check]   (--no-check reuses the
  statuses already in src/_data/livingTree.json and review.json, for offline rebuilds)
  python tools/build_living_tree.py --resources-only   (re-applies the inquirer-resource rule to the
  livingTree.json and review.json already on disk and changes nothing else in them; used when the
  library inbox has moved on since the last full run and the adopted-text lists must stay as they are)
"""

import argparse
import concurrent.futures as cf
import csv
import datetime as dt
import glob
import json
import os
import re
import socket
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEF_INBOX = r"C:/Users/aaron/Documents/wop-scratch/AOID2_Library_Inbox"
DEF_CODEX = r"C:/Users/aaron/Documents/WoP/methodology/Comparison_Principles_Codex.md"
STRUCT = os.path.join(REPO, "data-sources", "living-tree", "branches.json")
HOSTS = os.path.join(REPO, "data-sources", "living-tree", "institutions.csv")
OUT = os.path.join(REPO, "src", "_data", "livingTree.json")
REVIEW = os.path.join(REPO, "data-sources", "living-tree", "review.json")
DEF_SOURCES88 = r"C:/Users/aaron/Documents/wop-scratch/WoP_AOID2_CODE-AOID2-88_LivingTree_Sources_20261101.json"
CHECKS_GLOB = os.path.join(REPO, "data-sources", "living-tree", "link_checks_*.json")

# CODE-AOID2-88 branch names that differ from the branch labels in branches.json.
BRANCH_88 = {"Catholic (including the Eastern Catholic churches)": "catholicism"}
# The CODE-AOID2-88 verification field records a page it could not confirm in these words.
UNVERIFIED_RE = re.compile(r"unverified|not verified|failed both instruments|content not read|content unread|shell 200 only", re.I)
# Branches that show no inquirer resource by design (approved wording 2.8).
NO_RESOURCES_BY_DESIGN = {"chinese-house-churches"}

# Family headings of the checklist (both forms) -> id prefix.
FAMILY_PREFIX = {
    "Catholicism": "CATH", "Eastern Orthodox": "EO", "Oriental Orthodox": "OO", "Church of the East": "COE",
    "Lutheran": "LUTH", "Anglican": "ANGL", "Reformed": "REF", "Methodist": "METH", "Baptist": "BAPT",
    "Pentecostal": "PENT", "Holiness": "HOLI", "Stone-Campbell": "SC", "Anabaptist": "ANAB",
    "Adventist": "ADV", "Latter-day Saints": "LDS", "Jehovah's Witnesses": "JW",
}

# The Docs mirror has no id column. Its rows follow the CSV's order inside each family, except that
# two Docs rows each stand for two CSV rows. Evidence: CHECKLIST_CORRECTIONS_20261108.md treats
# "CATH-07, CATH-08" together as the Order of Confirmation, and logs EO-11 (Social Concept) and EO-12
# (Statute), which the Docs mirror joins in one row. Every other id is the row's place in its family.
# The mapping is checked against the intake log on every run and written to review.json.
DOCS_SPLITS = {("CATH", 7): ["CATH-07", "CATH-08"], ("EO", 11): ["EO-11", "EO-12"]}

# Status wording, from Comparison Principles Codex C4(d). Each phrase is checked against the codex.
CODEX_PHRASES = {
    "family": "sixteen are families",
    "within": "Pentecostal, with the Charismatic branch counted within it",
    "movement": "counted within the families their churches belong to and never as families",
    "outside": "have no adopted texts the method can read",
    "lds": "alone and never grouped with churches that separated from it",
}
STATUS_LINE = {
    "family": "One of the sixteen families.",
    "within": "Counted within a family: Pentecostal, with the Charismatic branch counted within it.",
    "movement": "A movement, counted within the families its churches belong to and never as a family.",
    "outside": "Outside the count of sixteen: it has no adopted texts the method can read.",
    "lds": "One of the sixteen families: alone, and never grouped with churches that separated from it.",
}

FILE_EXT = re.compile(r"\.(pdf|epub|docx?|zip|txt)(\?|$)", re.I)
URL_RE = re.compile(r"https?://[^\s)<>\"]+")
SPACED_RE = re.compile(r"https?://[^\s()<>\"]+(?: [^()<>\"]+?)+\.(?:pdf|epub|html?)(?=\s*\(|\s*$)", re.I)
BARE_RE = re.compile(r"(?<![\w/.@-])((?:[a-z0-9-]+\.)+(?:org|com|net|edu|va|uk|ca|am|ru|se|info|church)(?:/[^\s)<>\"]*)?)", re.I)


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def norm_url(u):
    u = re.sub(r"\s+\(.*$", "", u.strip()).rstrip(".,;")
    if not re.match(r"https?://", u):
        u = "https://" + u
    p = urllib.parse.urlsplit(u)
    path = urllib.parse.quote(urllib.parse.unquote(p.path), safe="/%:@!$&'()*+,;=-._~")
    return urllib.parse.urlunsplit((p.scheme, p.netloc, path, p.query, p.fragment))


def host_of(u):
    h = urllib.parse.urlsplit(u).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def is_file(u):
    return bool(FILE_EXT.search(urllib.parse.urlsplit(u).path)) or "File.aspx" in u or "/download/" in u


def is_homepage(u):
    return urllib.parse.urlsplit(u).path in ("", "/")


def urls_in(text):
    """URLs written in a source_used cell, full or bare, in the order written. '...' marks an elided URL."""
    text = text.split("->")[0]  # "A -> B": A is the link the church gives; B is where it lands
    found = []
    for m in SPACED_RE.finditer(text):  # file URLs written with spaces in their names
        found.append((m.start(), m.group(0)))
    for m in URL_RE.finditer(text):
        if any(s <= m.start() < s + len(u) for s, u in found):
            continue
        found.append((m.start(), m.group(0)))
    spans = [(s, s + len(u)) for s, u in found]
    for m in BARE_RE.finditer(text):
        if any(a <= m.start() < b for a, b in spans):
            continue
        found.append((m.start(), m.group(1)))
    # A URL written before the first parenthesis is the source itself; URLs inside the parenthesis are
    # commentary (redirects, old links) and count only when nothing stands before it.
    cut = text.find("(")
    main = [(s, u) for s, u in found if cut < 0 or s < cut]
    out = []
    for _, u in sorted(main or found):
        if "..." in u or "\u2026" in u:
            continue
        out.append(norm_url(u))
    return out


# ---------------------------------------------------------------------------------------------
# Checklist
# ---------------------------------------------------------------------------------------------

def md_links(cell):
    return [
        (m.group(1), m.group(2), cell[m.end():m.end() + 14].lstrip().startswith("*(search)*"))
        for m in re.finditer(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", cell)
    ]


def load_checklist_docs(path):
    rows, fam, counters = [], None, {}
    in_list = False
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("## "):
            in_list = line.strip() == "## Acquisition checklist"
            continue
        if not in_list:
            continue
        if line.startswith("### "):
            name = line[4:].strip()
            fam = FAMILY_PREFIX.get(name)
            continue
        if not fam or not line.startswith("|") or line.startswith("| ---") or line.startswith("| Done"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 7:
            continue
        done, text, status, get, fmt, prio, note = cells[:7]
        n = counters.get(fam, 0) + 1
        place = len([r for r in rows if r["prefix"] == fam]) + 1
        ids = DOCS_SPLITS.get((fam, place)) or ["%s-%02d" % (fam, n)]
        counters[fam] = n + len(ids) - 1
        rows.append({
            "ids": ids, "prefix": fam, "title": text.replace("**", ""), "status": status, "done": done == "\u2713",
            "links": [{"label": lab, "url": norm_url(url), "search_only": so} for lab, url, so in md_links(get)],
            "format": fmt, "priority": prio, "note": note, "place": place,
        })
    return rows, "Docs mirror export (%s)" % os.path.basename(path)


def load_checklist_csv(path):
    rows = []
    for r in read_csv(path):
        links = []
        for k in ("source_url", "alt_source"):
            for u in urls_in(r.get(k, "") or ""):
                links.append({"label": host_of(u), "url": u, "search_only": False})
        rows.append({
            "ids": [r["id"]], "prefix": r["id"].split("-")[0], "title": r["text"], "status": r["status"],
            "done": False, "links": links, "format": r.get("format_price", ""), "priority": r.get("priority", ""),
            "note": r.get("what_to_check", ""), "place": None,
        })
    return rows, "AOID2_Source_Checklist.csv (%s)" % path


# ---------------------------------------------------------------------------------------------
# Corrections file: open / partial / closed / re-scoped flags and candidate additions
# ---------------------------------------------------------------------------------------------

def load_corrections(inbox):
    files = sorted(f for f in glob.glob(os.path.join(inbox, "CHECKLIST_CORRECTIONS_*.md")) if "backup" not in f)
    flags, additions = {}, []
    if not files:
        return flags, additions, None
    path = files[-1]
    for line in open(path, encoding="utf-8"):
        m = re.match(r"^\|\s*([A-Z]+-[A-Z0-9]+(?:\s*(?:,|to)\s*[A-Z]+-[A-Z0-9]+)*)\s*\|\s*(.+?)\s*\|\s*$", line)
        if m and m.group(1) != "Row":
            ids = re.findall(r"[A-Z]+-[A-Z0-9]+", m.group(1))
            if " to " in m.group(1) and len(ids) == 2:
                a, b = ids
                pre = a.split("-")[0]
                ids = ["%s-%02d" % (pre, i) for i in range(int(a.split("-")[1]), int(b.split("-")[1]) + 1)]
            text = m.group(2)
            for i in ids:
                f = flags.setdefault(i, {"open": False, "partial": False, "closed": False, "rescoped": False, "notes": []})
                f["notes"].append(text)
                low = text.lower()
                if "closed, not needed" in low:
                    f["closed"] = True
                if "re-scoped" in low:
                    f["rescoped"] = True
                if "partial" in low:
                    f["partial"] = True
                if re.search(r"stays? (partly )?open|re-scope open|stay open|purchase decision open|not yet published|no complete text", low):
                    f["open"] = True
        m = re.match(r"^- (.+?) - HELD as ([A-Z]+-[A-Z0-9]+)", line)
        if m:
            additions.append({"id": m.group(2), "title": re.sub(r"\s*\(.*$", "", m.group(1)).strip()})
    return flags, additions, path


# ---------------------------------------------------------------------------------------------
# Manifests
# ---------------------------------------------------------------------------------------------

def load_manifests(inbox):
    out = {}
    for p in glob.glob(os.path.join(inbox, "*__MANIFEST.csv")):
        name = os.path.basename(p)
        urls = []
        try:
            for r in read_csv(p):
                u = (r.get("source_url") or "").strip()
                if u.startswith("http"):
                    urls.append(norm_url(u))
        except Exception as e:  # a manifest that cannot be read is reported, not guessed at
            urls = []
            print("WARN manifest unreadable:", name, e, file=sys.stderr)
        out[name] = urls
    return out


def manifest_for(file_name, manifests):
    m = re.search(r"([A-Z]+-[A-Z0-9]+__[^ ]*?__MANIFEST\.csv|[A-Z]+-[A-Z0-9]+__MANIFEST\.csv)", file_name)
    if m and m.group(1) in manifests:
        return m.group(1)
    m = re.search(r"in ([A-Z]+-[A-Z0-9]+__\S*?)(?:__)?MANI", file_name)
    if m:
        stem = m.group(1).rstrip("_")
        for k in manifests:
            if k.startswith(stem):
                return k
    return None


def landing_of(urls, preferred=()):
    """The landing page of a set of saved pages: the page that is the parent of most of the others (the
    set's own index); failing that, a checklist link to a page on the same host; failing that, the
    shallowest page that is not an 'about' page; failing that, the first file."""
    pages = [u for u in urls if not is_file(u) and not re.search(r"/about(\.html?)?/?$", u)]
    if pages:
        def kids(u):
            base = u if u.endswith("/") else u + "/"
            return sum(1 for v in urls if v != u and v.startswith(base))
        best = max(pages, key=kids)
        if kids(best) > 0:
            return best
        hostset = {host_of(u) for u in urls}
        for c in preferred:
            if host_of(c) in hostset and not is_file(c) and not is_homepage(c):
                return c
        return sorted(pages, key=lambda u: (len(urllib.parse.urlsplit(u).path.strip("/").split("/")), urls.index(u)))[0]
    files = [u for u in urls if is_file(u)]
    return files[0] if files else (urls[0] if urls else None)


# ---------------------------------------------------------------------------------------------
# Hosts
# ---------------------------------------------------------------------------------------------

def load_hosts():
    hosts = {}
    for r in read_csv(HOSTS):
        hosts[r["host"].strip().lower()] = r
    return hosts


def host_info(u, hosts):
    """Longest match: host plus first path segment (for shared hosts such as s3 or Payhip), then the host,
    then each parent domain."""
    h = host_of(u)
    seg = urllib.parse.urlsplit(u).path.strip("/").split("/")[0]
    while h:
        if seg and (h + "/" + seg) in hosts:
            return hosts[h + "/" + seg]
        if h in hosts:
            return hosts[h]
        if "." not in h:
            break
        h = h.split(".", 1)[1]
    return None


# ---------------------------------------------------------------------------------------------
# Link checking: one plain GET per URL, urllib's own default headers, redirects followed.
# ---------------------------------------------------------------------------------------------

BLOCK_CODES = {401, 403, 405, 406, 409, 418, 429, 451, 503, 520, 521, 522, 523, 524, 525, 526}


def check(url):
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=25, context=ctx) as r:
            code = r.status
            final = r.geturl()
            r.read(1024)
        return {"code": code, "final": final if final != url else None, "result": "ok" if 200 <= code < 300 else "browser"}
    except urllib.error.HTTPError as e:
        code = e.code
        if code in (404, 410):
            res = "dead"
        else:
            res = "browser"
        return {"code": code, "final": None, "result": res}
    except urllib.error.URLError as e:
        reason = e.reason
        if isinstance(reason, socket.gaierror):
            return {"code": None, "final": None, "result": "dead", "error": "host name does not resolve"}
        return {"code": None, "final": None, "result": "browser", "error": str(reason)[:120]}
    except Exception as e:  # timeouts, resets, TLS failures
        return {"code": None, "final": None, "result": "browser", "error": (type(e).__name__ + ": " + str(e))[:120]}


STATUS_WORDS = {"ok": "answers", "browser": "needs a browser check", "dead": "dead"}


# ---------------------------------------------------------------------------------------------
# Inquirer resources (step 163)
# ---------------------------------------------------------------------------------------------

def build_resources(struct, sources88, checks_path):
    """Per-branch inquirer resources to show, and the review record of every resource (shown or withheld)."""
    src = json.load(open(sources88, encoding="utf-8"))
    checks = json.load(open(checks_path, encoding="utf-8"))
    links = checks["links"]
    slug_of = {b["label"]: b["slug"] for r in struct["rows"] for b in r["branches"]}
    slug_of.update(BRANCH_88)
    shown = {slug: [] for slug in slug_of.values()}
    record = {"from": os.path.basename(sources88), "checks": os.path.basename(checks_path),
              "checkedOn": checks.get("checkedOn"), "rule": "show only if (a) the CODE-AOID2-88 verification field "
              "does not record the page as unverified and (b) WebFetch (OK or PARTIAL) and the shell request (2xx) "
              "both loaded it", "shown": [], "withheld": [], "withheld_by_design": []}
    seen = set()
    for b in src["branches"]:
        slug = slug_of.get(b["branch"])
        if not slug:
            sys.exit("STOP: CODE-AOID2-88 branch not on the Tree: %s" % b["branch"])
        seen.add(slug)
        if slug in NO_RESOURCES_BY_DESIGN:
            if b["inquirer_resources"]:
                sys.exit("STOP: %s has inquirer resources, but shows none by design" % slug)
            record["withheld_by_design"].append({"slug": slug, "withheld_links": b.get("withheld_links", [])})
            continue
        for r in b["inquirer_resources"]:
            url = r["url"]
            chk = links.get(url)
            reasons = []
            if UNVERIFIED_RE.search(r.get("claim_verified", "")):
                reasons.append("(a) the CODE-AOID2-88 verification field does not confirm the page: " + r["claim_verified"])
            if chk is None:
                reasons.append("(b) not in the check record")
            else:
                wf, sh = chk["webfetch"], chk["shell"]
                if wf["result"] not in ("OK", "PARTIAL"):
                    reasons.append("(b) WebFetch: " + wf["detail"])
                if not (sh["code"] and 200 <= sh["code"] < 300):
                    reasons.append("(b) shell: " + ("HTTP %s" % sh["code"] if sh["code"] else (sh.get("error") or "no response")))
            entry = {"slug": slug, "publisher": r["publisher"], "title": r["title"], "url": url,
                     "claim_verified": r.get("claim_verified", ""), "check": chk}
            if reasons:
                entry["reasons"] = reasons
                record["withheld"].append(entry)
            else:
                record["shown"].append(entry)
                shown[slug].append({"label": r["publisher"] + ", " + r["title"], "url": url})
    missing = set(slug_of.values()) - seen
    if missing:
        sys.exit("STOP: branches missing from the CODE-AOID2-88 JSON: %s" % sorted(missing))
    return shown, record


def apply_resources(page_branches, review, shown, record):
    for b in page_branches:
        b["resources"] = shown[b["slug"]]
    review["resources"] = record


def latest_checks():
    files = sorted(glob.glob(CHECKS_GLOB))
    if not files:
        sys.exit("STOP: no data-sources/living-tree/link_checks_<date>.json")
    return files[-1]


# ---------------------------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inbox", default=DEF_INBOX)
    ap.add_argument("--checklist")
    ap.add_argument("--codex", default=DEF_CODEX)
    ap.add_argument("--no-check", action="store_true")
    ap.add_argument("--sources88", default=DEF_SOURCES88)
    ap.add_argument("--resources-only", action="store_true")
    a = ap.parse_args()

    if a.resources_only:
        # Re-apply the resource rule to the files on disk; every other key stays exactly as it is.
        struct = json.load(open(STRUCT, encoding="utf-8"))
        out = json.load(open(OUT, encoding="utf-8"))
        review = json.load(open(REVIEW, encoding="utf-8"))
        shown, record = build_resources(struct, a.sources88, latest_checks())
        apply_resources(out["branches"], review, shown, record)
        with open(OUT, "w", encoding="utf-8", newline="\n") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        with open(REVIEW, "w", encoding="utf-8", newline="\n") as f:
            json.dump(review, f, ensure_ascii=False, indent=1)
        print("resources shown:", len(record["shown"]), "| withheld:", len(record["withheld"]),
              "| none by design:", [w["slug"] for w in record["withheld_by_design"]])
        return

    # Codex: labels and status wording must stand in C4(d).
    codex = open(a.codex, encoding="utf-8").read()
    m = re.search(r"- \(d\) \*\*The sixteen families, and what stays outside\.\*\*(.+?)\n", codex)
    if not m:
        sys.exit("STOP: codex C4(d) not found in %s" % a.codex)
    c4d = m.group(1)
    struct = json.load(open(STRUCT, encoding="utf-8"))
    missing = []
    for row in struct["rows"]:
        for b in row["branches"]:
            if b["label"] not in c4d:
                missing.append(b["label"])
    for k, ph in CODEX_PHRASES.items():
        if ph not in c4d:
            missing.append("phrase: " + ph)
    if missing:
        sys.exit("STOP: not found in codex C4(d): %s" % missing)
    nb = sum(len(r["branches"]) for r in struct["rows"])
    if nb != 25:
        sys.exit("STOP: %d branches, codex says twenty-five" % nb)

    # Checklist.
    path = a.checklist
    if not path:
        for cand in (os.path.join(a.inbox, "AOID2_Source_Checklist.csv"), os.path.join(REPO, "AOID2_Source_Checklist.csv")):
            if os.path.exists(cand):
                path = cand
                break
    if not path:
        sys.exit("STOP: no checklist given and AOID2_Source_Checklist.csv not found in the inbox or repo")
    checklist, checklist_src = (load_checklist_csv(path) if path.lower().endswith(".csv") else load_checklist_docs(path))

    intake = read_csv(os.path.join(a.inbox, "INTAKE_LOG.csv"))
    if not intake or len(intake[0]) != 14:
        sys.exit("STOP: INTAKE_LOG.csv does not have 14 columns")
    manifests = load_manifests(a.inbox)
    flags, additions, corrections_path = load_corrections(a.inbox)
    hosts = load_hosts()

    by_id = {}
    for r in intake:
        by_id.setdefault(r["id"], []).append(r)

    # Candidate additions held under ids the checklist has no row for.
    listed = {i for row in checklist for i in row["ids"]}
    for add in additions:
        if add["id"] not in listed and add["id"] in by_id:
            checklist.append({"ids": [add["id"]], "prefix": add["id"].split("-")[0], "title": add["title"],
                              "status": "HELD", "done": True, "links": [], "format": "", "priority": "",
                              "note": "", "place": None, "addition": True})
            listed.add(add["id"])
    unlisted = sorted(set(by_id) - listed)

    review = {"checklist_source": checklist_src, "corrections_source": corrections_path,
              "mapping": [], "third_party": [], "historic": [], "store": [], "no_church_copy": [],
              "dead": [], "browser": [], "closed_rows": [], "unlisted_intake_ids": unlisted,
              "unknown_hosts": [], "landing_wanted": []}

    texts = []
    for row in checklist:
        ids = row["ids"]
        recs = [r for i in ids for r in by_id.get(i, [])]
        accepted = [r for r in recs if r["verdict"].upper().startswith("ACCEPT")]
        dead_recorded = [r for r in recs if r["verdict"].upper() in ("NOT_FOUND", "REJECT")]
        fl = {"open": False, "partial": False, "closed": False, "rescoped": False, "notes": []}
        for i in ids:
            f = flags.get(i)
            if f:
                for k in ("open", "partial", "closed", "rescoped"):
                    fl[k] = fl[k] or f[k]
                fl["notes"] += f["notes"]
        # Mapping evidence for the Docs mirror (ids are positional there): does the intake agree?
        ev = ""
        if accepted:
            hs = {host_of(l["url"]) for l in row["links"]}
            blob = " ".join(r["source_used"] + " " + r["file_name"] + " " + r["edition_or_year"] for r in accepted).lower()
            words = [w for w in re.findall(r"[a-z]{5,}", row["title"].lower())]
            hits = sum(1 for w in words if w in blob)
            hm = any(h and h.split(".")[-2] in blob for h in hs if "." in h)
            ev = "host match" if hm else ("%d of %d title words" % (hits, len(words)) if words else "no evidence")
        review["mapping"].append({"ids": ids, "title": row["title"], "intake_rows": len(recs), "evidence": ev})
        if fl["closed"] and not row.get("addition"):
            review["closed_rows"].append({"ids": ids, "title": row["title"], "note": fl["notes"][-1]})
            continue

        held_full = row["status"].upper().startswith("HAVE-FULL") or row["priority"].upper() == "HAVE-FULL"
        held = bool(accepted) or held_full
        copies = []

        def add_copy(url, kind, edition, origin, ids_=None, rights=None):
            if not url:
                return
            for c in copies:
                if c["url"] == url:
                    if edition and edition not in c["editions"]:
                        c["editions"].append(edition)
                    return
            info = host_info(url, hosts)
            if info is None:
                review["unknown_hosts"].append({"host": host_of(url), "url": url, "ids": ids})
            copies.append({"url": url, "kind": kind, "editions": [edition] if edition else [], "origin": origin,
                           "host": host_of(url), "institution": info["institution"] if info else host_of(url),
                           "church": (info.get("church") or "") if info else "",
                           "hostKind": info["kind"] if info else "unknown", "rights": rights})

        for r in accepted:
            rights = (r["rights_class"] or "").strip().upper()
            su = r["source_used"]
            cands = urls_in(su)
            if re.match(r"\s*checklist (source_url|alt_source)", su):
                which = 1 if "alt_source" in su[:30] else 0
                live = [l for l in row["links"]]
                if len(live) > which:
                    cands = [live[which]["url"]]
            mf = manifest_for(r["file_name"] + " " + su, manifests)
            murls = manifests.get(mf, []) if mf else []
            pool = [u for u in cands] + ([landing_of(murls, [l["url"] for l in row["links"]])] if murls else [])
            pool = [u for u in pool if u]
            if not pool:
                # nothing written in the log row: fall back to the checklist's own links for this text
                pool = [l["url"] for l in row["links"]]
            # landing page first, then a specific file, then a bare homepage
            pages = [u for u in pool if not is_file(u) and not is_homepage(u)]
            files = [u for u in pool if is_file(u)]
            homes = [u for u in pool if is_homepage(u)]
            if not pages and not files and homes:
                # the log names only a site: use the checklist's own link on that site, if it has one
                hs = {host_of(u) for u in homes}
                same = [l["url"] for l in row["links"] if host_of(l["url"]) in hs or any(host_of(l["url"]).endswith("." + h) for h in hs)]
                pages = [u for u in same if not is_file(u) and not is_homepage(u)]
                files = [u for u in same if is_file(u)]
            url = (pages or files or homes or [None])[0]
            if url and is_file(url):
                review["landing_wanted"].append({"ids": ids, "title": row["title"], "file_url": url})
            kind = {"FREE_OFFICIAL": "official", "PUBLIC_DOMAIN": "historic", "FREE_THIRD_PARTY": "third_party",
                    "PURCHASED": "store", "OWN": "official"}.get(rights, "official")
            info = host_info(url, hosts) if url else None
            if kind == "official" and info and info["kind"] == "third-party":
                kind = "third_party"
            add_copy(url, kind, r["edition_or_year"].strip(), "intake %s" % r["id"], rights=rights)

        extra_church = None
        if not accepted and row["status"].upper().startswith("NONE"):
            # "No authorised copy exists anywhere we can reach": nothing to link
            info = host_info(row["links"][0]["url"], hosts) if row["links"] else None
            extra_church = info.get("church") if info else None
        elif not accepted:
            st = row["status"].upper()
            for l in row["links"]:
                info = host_info(l["url"], hosts)
                hk = info["kind"] if info else "unknown"
                if "BUY" in st and not ("FREE" in st and hk == "church"):
                    kind = "store" if hk in ("church-store", "church") else "third_party_store"
                elif hk == "third-party" and "public domain" in row["note"].lower():
                    kind = "historic"
                elif hk == "third-party":
                    kind = "third_party"
                else:
                    kind = "official"
                add_copy(l["url"], kind, "", "checklist")
        elif fl["open"] and "BUY" in row["status"].upper():
            # held in part; the rest is sold: link the church's own store page for it
            for l in row["links"]:
                info = host_info(l["url"], hosts)
                if info and info["kind"] in ("church-store",):
                    add_copy(l["url"], "store", "", "checklist")

        # never link a recorded-dead URL
        dead_urls = set()
        for r in dead_recorded:
            for u in urls_in(r["source_used"]):
                dead_urls.add(u)
        copies = [c for c in copies if c["url"] not in dead_urls]

        if held_full and not accepted:
            state = "held"
        elif not held:
            state = "open"
        elif fl["open"] or fl["partial"]:
            state = "part"
        else:
            state = "held"

        texts.append({"ids": ids, "prefix": row["prefix"], "title": row["title"], "state": state,
                      "rescoped": fl["rescoped"], "copies": copies, "checklistStatus": row["status"],
                      "extraChurch": extra_church})

    # Link checks.
    urls = sorted({c["url"] for t in texts for c in t["copies"]})
    old, old_date = {}, None
    if a.no_check and os.path.exists(OUT):
        prev = json.load(open(OUT, encoding="utf-8"))
        old = prev.get("linkChecks", {})
        if os.path.exists(REVIEW):
            prev_review = json.load(open(REVIEW, encoding="utf-8"))
            old.update(prev_review.get("linkChecks", {}))
            old_date = prev_review.get("checkedOn")
    results = {}
    if a.no_check:
        results = {u: old.get(u, {"code": None, "result": "unchecked"}) for u in urls}
    else:
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            for u, res in zip(urls, ex.map(check, urls)):
                results[u] = res
    checked_at = dt.date.today().isoformat()

    # Compose the page data.
    labels = {"official": None, "historic": "Historic text, public copy", "store": "Available from"}
    page_branches = []
    counts = {"ok": 0, "browser": 0, "dead": 0, "unchecked": 0}
    seen_count = set()
    for row in struct["rows"]:
        for b in row["branches"]:
            kind = b["kind"]
            status_line = STATUS_LINE["lds" if b["slug"] == "latter-day-saints" else kind]
            fam_texts = [t for t in texts if b["prefix"] and t["prefix"] == b["prefix"]] if kind == "family" else []
            items, churches = [], []
            for t in fam_texts:
                if t.get("extraChurch") and t["extraChurch"] not in churches:
                    churches.append(t["extraChurch"])
                shown, hidden = [], []
                for c in t["copies"]:
                    res = results.get(c["url"], {"code": None, "result": "unchecked"})
                    entry = {"ids": t["ids"], "title": t["title"], "url": c["url"], "host": c["host"],
                             "institution": c["institution"], "code": res.get("code"), "result": res["result"],
                             "error": res.get("error"), "final": res.get("final"), "editions": c["editions"]}
                    if c["url"] not in seen_count:
                        seen_count.add(c["url"])
                        counts[res["result"]] = counts.get(res["result"], 0) + 1
                        if res["result"] == "dead":
                            review["dead"].append(entry)
                        elif res["result"] == "browser":
                            review["browser"].append(entry)
                    if c["kind"] in ("third_party", "third_party_store"):
                        review["third_party" if c["kind"] == "third_party" else "no_church_copy"].append(entry)
                        hidden.append(c)
                        continue
                    if c["kind"] == "historic":
                        review["historic"].append(entry)
                        label = "Historic text, public copy (%s)" % c["institution"]
                    elif c["kind"] == "store":
                        review["store"].append(entry)
                        label = "Available from %s" % c["institution"]
                    else:
                        label = c["institution"]
                    if c["kind"] in ("official", "store") and c["church"] and c["church"] not in churches:
                        churches.append(c["church"])
                    shown.append({"label": label, "kind": c["kind"],
                                  "url": None if res["result"] == "dead" else c["url"],
                                  "status": STATUS_WORDS.get(res["result"], "not checked"),
                                  "code": res.get("code"), "edition": "; ".join(c["editions"])})
                # "No copy online from the church itself" is for a text held only through a third party;
                # a historic public copy carries its own label instead.
                no_church = not any(s["kind"] in ("official", "store", "historic") for s in shown)
                if no_church and (hidden or t["state"] != "open"):
                    review["no_church_copy"].append({"ids": t["ids"], "title": t["title"]})
                items.append({"ids": t["ids"], "title": t["title"], "state": t["state"],
                              "moreToCome": t["state"] in ("open", "part"), "rescoped": t["rescoped"],
                              "noChurchCopy": no_church and bool(hidden or t["state"] != "open" or t["copies"]),
                              "copies": shown})
            page_branches.append({"slug": b["slug"], "label": b["label"], "row": row["label"], "kind": kind,
                                  "statusLine": status_line, "box": b["box"], "churches": churches, "texts": items,
                                  "familyOf": "Pentecostal" if kind == "within" else None})

    out = {
        "_generated": "by tools/build_living_tree.py on %s; do not edit by hand" % checked_at,
        "linksCheckedOn": old_date if a.no_check else checked_at,
        "image": struct["image"],
        "rows": [{"label": r["label"], "slugs": [b["slug"] for b in r["branches"]]} for r in struct["rows"]],
        "branches": page_branches,
        "counts": counts,
    }
    shown_res, res_record = build_resources(struct, a.sources88, latest_checks())
    apply_resources(out["branches"], review, shown_res, res_record)
    review["linkChecks"] = results
    review["counts"] = counts
    review["checkedOn"] = out["linksCheckedOn"]
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with open(REVIEW, "w", encoding="utf-8", newline="\n") as f:
        json.dump(review, f, ensure_ascii=False, indent=1)
    print("texts:", len(texts), "| links:", len(urls), "| counts:", counts)
    print("unknown hosts:", sorted({h["host"] for h in review["unknown_hosts"]}))
    print("unlisted intake ids:", unlisted)


if __name__ == "__main__":
    main()
