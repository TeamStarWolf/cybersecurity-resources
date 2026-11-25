"""Request every address in the catalog and report what answered.

    python scripts/check_links.py                    check every address; exit 1 if any fails
    python scripts/check_links.py --report out.json  also save status, final address, title and heading per address
    python scripts/check_links.py --pages            list the records whose page may not be the resource they name
    python scripts/check_links.py --wording          list the descriptions that repeat their page's own words;
                                                     exit 1 if any does. Add --only domain-id,domain-id to limit it
    python scripts/check_links.py --self-test        confirm the checker rejects a dead address, honors the ignore
                                                     list, flags a wrong page, and catches a copied description

Addresses checked: every shown resource and every link of the compact set (including pinned addresses).
An address on data/link-check-ignore.yaml is still requested and reported, but it cannot fail the run.

An address that answers 200 is not proof that it is the right page: a site can move a list and leave a hub,
or return an empty result for a filter. --pages compares each shown record's name with the page's title and
first heading, and looks for words such as "page not found" or "no results" in the page. It prints a list
for a person to read and never fails the run, because titles differ from names for honest reasons. It cannot
see a page that keeps its name while changing what it offers, and it cannot read a page that needs a browser.

A description has to be the catalog's own sentence. --wording takes what each page says about itself (its
meta descriptions, its title, its first heading, and its opening paragraphs) and finds the longest run of
consecutive words that the record's description shares with any of them. A run of five or more words is
reported, unless it is the resource's own name. It needs the network, so it is run by hand before a pull
request and by a weekly job, not on every push. It finds copied runs of words; it cannot find a sentence that
follows its source with one word in five changed, and it cannot read a page that needs a browser.

Standard library plus the curl command, which makes the requests.
"""
from __future__ import annotations

import concurrent.futures
import html
import json
import re
import shutil
import subprocess
import sys

import catalog

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
CURL = shutil.which("curl") or "curl"
TIMEOUT = 30
RETRIES = 2
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
HIDDEN_RE = re.compile(r"<(script|style|noscript|template)\b.*?</\1\s*>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
META_RE = re.compile(r"<meta\b[^>]*>", re.I)
META_KEY_RE = re.compile(r"""(?:name|property)\s*=\s*["']?(?:description|og:description|twitter:description)["'\s>]""", re.I)
META_CONTENT_RE = re.compile(r"""content\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.I | re.S)
CHROME_RE = re.compile(r"<(nav|header|footer)\b.*?</\1\s*>", re.I | re.S)
PARA_RE = re.compile(r"<(p|li)\b[^>]*>(.*?)</\1\s*>", re.I | re.S)
WORD_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
# A description may not share this many consecutive words with its page's own summary.
MIN_RUN = 5
OPENING_PARAGRAPHS = 8
WRITE_OUT = r"\n%{http_code}\t%{url_effective}"
# Words a page uses when it answers 200 but has nothing at the address.
NOT_THERE = ("page not found", "404 not found", "no terms match", "no results found", "no matching results",
             "nothing found", "could not be found", "does not exist", "doesn't exist", "no longer available",
             "access denied", "login required")
SMALL_WORDS = {"the", "and", "for", "of", "a", "an", "to", "in", "on", "by", "with", "from", "at"}


def clean(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", fragment))).strip()


def read_page(body: bytes) -> dict:
    """The title, the first heading, any not-found wording, and what the page says about itself."""
    text = body[:600_000].decode("utf-8", "replace")
    title = TITLE_RE.search(text)
    visible = HIDDEN_RE.sub(" ", text)
    heading = H1_RE.search(visible)
    plain = clean(visible).lower()
    says = next((phrase for phrase in NOT_THERE if phrase in plain), "")
    sources = []
    for tag in META_RE.findall(text):
        content = META_CONTENT_RE.search(tag)
        if META_KEY_RE.search(tag) and content:
            sources.append(["meta", clean(content.group(1) or content.group(2) or "")[:800]])
    if title:
        sources.append(["title", clean(title.group(1))[:400]])
    if heading:
        sources.append(["heading", clean(heading.group(1))[:400]])
    paragraphs = [clean(m.group(2)) for m in PARA_RE.finditer(CHROME_RE.sub(" ", visible))]
    sources += [["opening", p[:800]] for p in paragraphs if len(p) >= 40][:OPENING_PARAGRAPHS]
    return {"title": clean(title.group(1))[:120] if title else "",
            "h1": clean(heading.group(1))[:120] if heading else "",
            "says": says,
            "sources": [s for s in sources if s[1]]}


def request(url: str) -> dict:
    """One address: status (0 when no HTTP answer), the final address after redirects, and what the page shows.

    curl makes the request: several sites in the catalog refuse the TLS fingerprint of Python's own client.
    It retries every kind of failure, because a reset connection is common when many requests run at once.
    """
    empty = {"title": "", "h1": "", "says": "", "sources": []}
    if not url.startswith(("https://", "http://")):
        return {"url": url, "status": 0, "final": url, "error": "not an http(s) address", **empty}
    cmd = [CURL, "--silent", "--show-error", "--location", "--compressed", "--max-time", str(TIMEOUT),
           "--retry", str(RETRIES), "--retry-all-errors", "--max-redirs", "10", "--user-agent", USER_AGENT]
    for name, value in HEADERS.items():
        cmd += ["--header", f"{name}: {value}"]
    cmd += ["--output", "-", "--write-out", WRITE_OUT, url]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT * (RETRIES + 2))
    except subprocess.TimeoutExpired:
        return {"url": url, "status": 0, "final": url, "error": "timed out", **empty}
    body, _, tail = proc.stdout.rpartition(b"\n")
    code, _, final = tail.decode("utf-8", "replace").partition("\t")
    status = int(code) if code.isdigit() else 0
    if 200 <= status < 300:
        error = ""
    elif status:
        error = f"HTTP {status}"
    else:
        error = re.sub(r"\s+", " ", proc.stderr.decode("utf-8", "replace")).strip()[:120] or "no answer"
    return {"url": url, "status": status, "final": final or url, "error": error, **read_page(body)}


def addresses() -> list[str]:
    return catalog.published_addresses(catalog.load_resources(), catalog.load_compact())


def is_ignored(url: str, ignore: list[dict]) -> bool:
    """On the ignore list for this checker. Entries marked "only: ci" apply to the CI check alone."""
    return any(catalog.ignore_matches(item, url) for item in ignore if item.get("only") != "ci")


def run(urls: list[str], ignore: list[dict], workers: int = 8) -> tuple[list[dict], list[dict], list[dict]]:
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        results = list(pool.map(request, urls))
    ok = [r for r in results if 200 <= r["status"] < 300]
    bad = [r for r in results if not 200 <= r["status"] < 300]
    ignored = [r for r in bad if is_ignored(r["url"], ignore)]
    failed = [r for r in bad if not is_ignored(r["url"], ignore)]
    return ok, ignored, failed


# ---------------------------------------------------------------- is it the right page?
def words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in SMALL_WORDS and len(w) > 1]


def name_share(name: str, page: dict) -> float:
    """The share of the words in a record's name that appear in the page's title or first heading."""
    wanted = list(dict.fromkeys(words(name)))
    seen = set(words(page["title"] + " " + page["h1"]))
    return sum(1 for w in wanted if w in seen) / len(wanted) if wanted else 1.0


def page_problem(name: str, page: dict) -> str | None:
    """Why this page may not be the resource the record names, or None. Only for a person to read."""
    if not 200 <= page["status"] < 300:
        return None  # the link check itself reports an address that does not answer
    if page["says"]:
        return f"the page text includes \"{page['says']}\""
    if not page["title"] and not page["h1"]:
        return "a script gets no title or heading from this page; read it in a browser"
    if name_share(name, page) < 0.5:
        return "fewer than half of the words in the record's name are in the page title or first heading"
    return None


def pages() -> int:
    records = [r for r in catalog.load_resources() if catalog.is_active(r)]
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        results = list(pool.map(lambda r: request(r["url"]), records))
    flagged = unread = 0
    for rec, page in zip(records, results):
        if not 200 <= page["status"] < 300:
            unread += 1
            continue
        why = page_problem(rec["name"], page)
        if why:
            flagged += 1
            print(f"READ  {rec['domain']}/{rec['id']}: {why}\n      name:    {rec['name']}\n"
                  f"      title:   {page['title']}\n      heading: {page['h1']}\n      address: {rec['url']}")
    print(f"check_links --pages: {len(records)} shown records requested; {flagged} to read by hand; "
          f"{unread} did not answer a script and need a browser. This list is for a person and does not fail the run.")
    return 0


# ---- is the description the catalog's own sentence?
def word_list(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def common_runs(a: list[str], b: list[str], least: int) -> list[list[str]]:
    """Every run of at least `least` consecutive words that two word lists share and that cannot be extended."""
    runs = []
    prev = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                ends_here = i == len(a) or j == len(b) or a[i] != b[j]
                if ends_here and cur[j] >= least:
                    runs.append(a[i - cur[j]:i])
        prev = cur
    return runs


def outside_names(run: list[str], names: list[list[str]]) -> int:
    """The longest stretch of a shared run that is not the resource's own name, former name, or publisher."""
    best, start = 0, 0
    for name in names:
        for i in range(len(run)):
            for j in range(len(name)):
                k = 0
                while i + k < len(run) and j + k < len(name) and run[i + k] == name[j + k]:
                    k += 1
                if k > best:
                    best, start = k, i
    if best < 2:
        return len(run)
    return max(outside_names(run[:start], names), outside_names(run[start + best:], names))


def wording_problem(rec: dict, page: dict) -> tuple[int, str, str] | None:
    """The longest run of MIN_RUN or more consecutive words that a description shares with what the page says
    about itself, as (length outside the resource's own name, the shared words, where), or None."""
    mine = word_list(rec.get("description") or "")
    names = [word_list(str(rec.get(key) or "")) for key in ("name", "formerly", "publisher")]
    worst = None
    for where, text in page.get("sources") or []:
        for run in common_runs(mine, word_list(text), MIN_RUN):
            length = outside_names(run, names)
            if length >= MIN_RUN and (worst is None or length > worst[0]):
                worst = (length, " ".join(run), where)
    return worst


def has_summary(page: dict) -> bool:
    """A script read something to compare: a meta description or an opening paragraph, not only a title."""
    return 200 <= page["status"] < 300 and any(where in ("meta", "opening") for where, _ in page.get("sources") or [])


def wording(argv: list[str]) -> int:
    only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else None
    records = [r for r in catalog.load_resources() if catalog.is_active(r) and (only is None or r["domain"] in only)]
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        results = list(pool.map(lambda r: request(r["url"]), records))
    rows, copied, unread = [], 0, []
    for rec, page in zip(records, results):
        readable = has_summary(page)
        found = wording_problem(rec, page) if readable else None
        rows.append({"id": rec["id"], "domain": rec["domain"], "readable": readable,
                     "run": found[0] if found else 0, "words": found[1] if found else "", "where": found[2] if found else ""})
        if not readable:
            unread.append(f"{rec['domain']}/{rec['id']}")
        elif found:
            copied += 1
            print(f"COPY  {rec['domain']}/{rec['id']}: {found[0]} words shared with the page's {found[2]}: \"{found[1]}\"")
    if "--report" in argv:
        with open(argv[argv.index("--report") + 1], "w", encoding="utf-8", newline="\n") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=1)
    if unread:
        print("A script got no summary text from these pages; read each in a browser:")
        for item in unread:
            print(f"  {item}")
    print(f"check_links --wording: {len(records)} shown records; {copied} share a run of {MIN_RUN} or more words "
          f"with their page's own summary; {len(unread)} gave a script no text to compare and need a browser")
    return 1 if copied else 0


def self_test() -> int:
    # The .invalid top-level domain never resolves (RFC 6761), so every request here fails.
    dead = "https://dead.invalid/"
    under_prefix = "https://skipped.invalid/page"
    exact = "https://exact.invalid/"
    beyond_exact = "https://exact.invalid/another-page"
    ci_only = "https://ci-only.invalid/"
    ignore = [
        {"url": "https://skipped.invalid/", "match": "prefix"},
        {"url": exact, "match": "exact"},
        {"url": ci_only, "match": "exact", "only": "ci"},
    ]
    ok, ignored, failed = run([dead, under_prefix, exact, beyond_exact, ci_only], ignore, workers=5)
    failed_urls, ignored_urls = {r["url"] for r in failed}, {r["url"] for r in ignored}
    problems = []
    if dead not in failed_urls:
        problems.append("a dead address was not reported as failed")
    if ignored_urls != {under_prefix, exact}:
        problems.append("the ignore list did not set aside exactly the prefix match and the exact match")
    if beyond_exact not in failed_urls:
        problems.append("an exact entry also covered a longer address")
    if ci_only not in failed_urls:
        problems.append("an entry marked only: ci was honored outside CI")
    if ok:
        problems.append("an address that cannot resolve was reported as answering")

    # Planted pages for the right-page check. No network.
    def page(markup: str) -> dict:
        return {"status": 200, **read_page(markup.encode("utf-8"))}

    name = "Example Agency Cybersecurity Advisories & Guidance"
    hub = page("<title>Press Room</title><h1>Engaging the Media &amp; Public</h1><p>News and statements.</p>")
    right = page("<title>Cybersecurity Advisories &amp; Guidance</title><h1>Example Agency <b>Advisories</b></h1>")
    empty_filter = page("<title>Example Blog</title><h1>Example Blog</h1><p>Sorry, no terms match your search!</p>")
    in_script = page("<title>Example Blog</title><h1>Example Blog</h1><script>var m = 'page not found';</script>")
    shell = page("<html><body><div id='app'></div></body></html>")
    planted = [
        ("a hub page where the list used to be", page_problem(name, hub) is not None),
        ("the right page", page_problem(name, right) is None),
        ("a filter that returns nothing", "no terms match" in (page_problem("Example Blog", empty_filter) or "")),
        ("not-found wording inside a script is not page text", page_problem("Example Blog", in_script) is None),
        ("a page with no title or heading", "browser" in (page_problem("Example Blog", shell) or "")),
    ]
    for label, passed in planted:
        if not passed:
            problems.append(f"right-page check got this wrong: {label}")

    # Planted pages for the wording check. No network.
    tagline = "a fast scanner for finding open ports on large networks"
    copied = {"name": "Example Scanner", "publisher": "Example Project", "description": "A fast scanner for finding open ports on large networks."}
    own = {"name": "Example Scanner", "publisher": "Example Project", "description": "Port scanner built for speed across big address ranges."}
    titled = {"name": "The Example Protocol Version Two Specification", "publisher": "Example Body",
              "description": "Defines the message formats of the Example Protocol Version Two Specification."}
    in_meta = page(f'<meta name="description" content="Example Scanner is {tagline} and hosts."><title>Example Scanner</title>')
    in_og = page(f"<meta content='Example Scanner: {tagline}.' property='og:description'><title>Example Scanner</title>")
    in_opening = page(f"<title>Example Scanner</title><main><p>Example Scanner is {tagline}, written in C.</p></main>")
    in_code = page(f'<title>Example Scanner</title><script>var d = "{tagline}";</script><p>Notes on how the project is built and released.</p>')
    in_menu = page(f"<title>Example Scanner</title><nav><p>{tagline}</p></nav><p>Notes on how the project is built and released.</p>")
    own_name = page('<meta name="description" content="The Example Protocol Version Two Specification is maintained by Example Body.">')
    title_only = page("<title>Example Scanner</title><div id='app'></div>")
    found = wording_problem(copied, in_meta)
    planted = [
        ("a description copied from the meta description", found is not None and found[0] == 10 and found[2] == "meta"),
        ("a description copied from a social-card description", wording_problem(copied, in_og) is not None),
        ("a description copied from the opening paragraph", (wording_problem(copied, in_opening) or (0, "", ""))[2] == "opening"),
        ("the catalog's own sentence", wording_problem(own, in_meta) is None),
        ("the same words inside a script are not page text", wording_problem(copied, in_code) is None),
        ("the same words inside the site menu are not the opening", wording_problem(copied, in_menu) is None),
        ("a run that is the resource's own name", wording_problem(titled, own_name) is None),
        ("a page with only a title counts as unread", not has_summary(title_only) and has_summary(in_meta)),
    ]
    for label, passed in planted:
        if not passed:
            problems.append(f"wording check got this wrong: {label}")

    for p in problems:
        print("self-test:", p)
    print("self-test:", "failed" if problems else
          "5 planted addresses: the dead one failed, the prefix and exact entries were set aside, "
          "and neither a longer address than an exact entry nor a CI-only entry was excused; "
          "5 planted pages: the hub, the empty filter and the page with no heading were flagged, "
          "the right page and wording inside a script were not; "
          "8 planted descriptions: copies of a meta description, a social-card description and an opening "
          "paragraph were caught, and the catalog's own sentence, words in a script or a menu, and the "
          "resource's own name were not")
    return 1 if problems else 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    if "--pages" in argv:
        return pages()
    if "--wording" in argv:
        return wording(argv)
    ignore = catalog.load_ignore()["entries"]
    urls = addresses()
    ok, ignored, failed = run(urls, ignore)
    if "--report" in argv:
        path = argv[argv.index("--report") + 1]
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            rows = [{k: v for k, v in r.items() if k != "sources"} for r in ok + ignored + failed]
            json.dump(sorted(rows, key=lambda r: r["url"]), fh, ensure_ascii=False, indent=1)
    for r in ignored:
        print(f"ignored  {r['error']}  {r['url']}")
    for r in failed:
        print(f"FAILED   {r['error']}  {r['url']}")
    answered = [i["url"] for i in ignore if i.get("only") != "ci" and not any(catalog.ignore_matches(i, r["url"]) for r in ignored)]
    for u in answered:
        print(f"note: {u} is on the ignore list but answered this time")
    print(f"check_links: {len(urls)} addresses requested; {len(ok)} answered 2xx; "
          f"{len(ignored)} did not and are on the ignore list; {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
