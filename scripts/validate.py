"""Check the catalog data against its rules.

    python scripts/validate.py              check the data; exit 1 on any error
    python scripts/validate.py --self-test  plant one fault per rule and confirm each is rejected

The rules cover the taxonomy, every resource record, the compact bookmark set and its limits, the
link-check ignore list, and the original links this collection began with. No network access.

The address rule is at least as strict as the rule of the TeamStarWolf project that builds a menu
from LINKS.md (the external address rule in tests/check_platform_nav.py of TeamStarWolf/intelligence-hub),
so an address that passes here cannot break that build.
"""
from __future__ import annotations

import copy
import csv
import ipaddress
import re
import sys
import unicodedata
import urllib.parse
from html.parser import HTMLParser

import catalog
from catalog import DATA, HTTP_ALLOWED, MAX_LIST

ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SINCE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")
LINK_RE = re.compile(r"^- \[([^\]\n]+)\]\((\S+)\)$")
MD_LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
DNS_LABEL = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
ENTITY_RE = re.compile(r"&#?[A-Za-z0-9]+;")
# A pair of underscores around a word or phrase, which Markdown reads as emphasis. An underscore inside a word is fine.
EMPHASIS_RE = re.compile(r"(?<![A-Za-z0-9])_+[^\s_]([^_]*[^\s_])?_+(?![A-Za-z0-9])")
MAX_WORDS = 25
MAX_ADDRESS = 512
STATUSES = {"active", "retired", "unverified"}
HOWS = {"script", "browser", "blocked"}
MAINTENANCE = {"archived", "maintenance-mode", "unmaintained", "dormant"}
REQUIRED = ("id", "name", "url", "publisher", "section", "kind", "cost", "checked")
KNOWN_FIELDS = set(REQUIRED) | {"domain", "description", "also_in", "formerly", "previously", "status",
                                "replaced_by", "maintenance", "notes"}
# Fields that are written into the generated pages.
RENDERED_FIELDS = ("name", "publisher", "description", "formerly")
TEAMSTARWOLF_HOSTS = {"teamstarwolf.com", "library.teamstarwolf.com", "teamstarwolf.github.io"}

# Words that describe a feeling instead of a property (the TeamStarWolf voice guide), plus "leading".
BANNED = [
    "comprehensive", "powerful", "cutting-edge", "state-of-the-art", "world-class", "best-in-class",
    "industry-leading", "enterprise-grade", "military-grade", "next-level", "game-changing", "game-changer",
    "revolutionary", "revolutionize", "groundbreaking", "unparalleled", "seamless", "effortless", "supercharge",
    "blazing-fast", "lightning-fast", "unbreakable", "hack-proof", "unhackable", "one-stop", "must-have",
    "battle-tested", "leverage", "empower", "leading", "robust", "ultimate",
]
BANNED_RE = re.compile(r"\b(" + "|".join(re.escape(w).replace(r"\-", r"[- ]") for w in BANNED) + r")", re.I)
TRACKING_RE = re.compile(r"[?&](utm_[a-z]+|fbclid|gclid|mc_cid|mc_eid|igshid|_hsenc|_hsmi|ref|ref_src|affiliate|aff_id|partner)=", re.I)
SHORTENERS = {"bit.ly", "t.co", "tinyurl.com", "goo.gl", "ow.ly", "buff.ly", "is.gd", "lnkd.in", "rebrand.ly", "cutt.ly", "t.ly", "shorturl.at"}
PRIVATE_RE = re.compile(r"([A-Za-z]:\\|/Users/|/home/[a-z]|[\w.+-]+@[\w-]+\.[a-z]{2,})")
# Characters that would end or reshape a Markdown link, a table cell, or an HTML attribute.
ADDRESS_FORBIDDEN = set('"<>|`()[]{}^\\')
# Characters that start Markdown or HTML markup inside a table cell or a link label.
MARKUP = set("[]<>`*\\")


def load_original() -> list[dict]:
    with open(DATA / "original-292.tsv", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def load_all() -> dict:
    return {
        "tax": catalog.load_taxonomy(),
        "records": catalog.load_resources(),
        "compact": catalog.load_compact(),
        "ignore": catalog.load_ignore(),
        "original": load_original(),
    }


# ---------------------------------------------------------------- addresses
def address_problem(url) -> str | None:
    """Why this address is not allowed, or None when it is fine."""
    if not isinstance(url, str) or not url:
        return "address is missing"
    if len(url) > MAX_ADDRESS:
        return f"address is longer than {MAX_ADDRESS} characters"
    for char in url:
        if ord(char) < 0x21 or ord(char) > 0x7e:
            return "address has whitespace, a control character, or a non-ASCII character"
    bad = sorted(set(url) & ADDRESS_FORBIDDEN)
    if bad:
        return f"address contains {' '.join(bad)}, which must be percent-encoded or removed"
    if not url.startswith("https://") and url not in HTTP_ALLOWED:
        return "address must be https"
    try:
        parts = urllib.parse.urlsplit(url)
        port = parts.port
    except ValueError:
        return "address has an invalid host or port"
    if "@" in parts.netloc:
        return "address carries credentials (an @ before the host)"
    if port is not None:
        return f"address has an explicit port ({port})"
    host = parts.hostname or ""
    if not host:
        return "address has no host"
    if parts.netloc.lower() != host:
        return "address has an empty port or other characters after the host"
    try:
        ipaddress.ip_address(host)
        return f"address host is an IP literal ({host})"
    except ValueError:
        pass
    if "." not in host:
        return f"address host is a single label ({host})"
    labels = host.split(".")
    last = labels[-1].lower()
    if last.isdigit() or last.startswith("0x"):
        return f"address host looks like an IP address ({host})"
    for label in labels:
        if not DNS_LABEL.fullmatch(label):
            return f"address host has an invalid DNS label ({host})"
        if label.lower().startswith("xn--"):
            return f"address host is punycode ({host})"
    for segment in parts.path.split("/"):
        if urllib.parse.unquote(segment).lower() in (".", ".."):
            return "address has a dot path segment"
    low = parts.path.lower()
    if "%2f" in low or "%5c" in low:
        return "address has an encoded slash or backslash in the path"
    if ENTITY_RE.search(url):
        return "address contains an HTML entity, which the generated Markdown would decode"
    if host in TEAMSTARWOLF_HOSTS or (host == "github.com" and (low + "/").startswith("/teamstarwolf/")):
        return "address is a TeamStarWolf property; the catalog lists outside resources"
    if host.removeprefix("www.") in SHORTENERS:
        return "address is a link shortener"
    if TRACKING_RE.search(url):
        return "address has a tracking or affiliate parameter"
    return None


def check_url(url, where: str) -> list[str]:
    problem = address_problem(url)
    return [f"{where}: {problem} ({str(url)[:80]!r})"] if problem else []


# ---------------------------------------------------------------- text
def text_problem(value: str, markup: bool = True, symbols: bool = True) -> str | None:
    """Why this text would break a generated page or the house style, or None when it is fine.

    markup: reject the characters that start Markdown or HTML markup. symbols: reject emoji, pictographs,
    and dashes other than the hyphen. Control characters and unusual spaces are always rejected.
    Letters of any script are allowed.
    """
    for char in value:
        cat = unicodedata.category(char)
        if cat in ("Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp") or (cat == "Zs" and char != " "):
            return f"contains a control character or a non-standard space (U+{ord(char):04X})"
        if markup and char in MARKUP:
            return f"contains {char!r}, which the generated Markdown or HTML would read as markup"
        if symbols and (cat in ("So", "Sk") or (cat == "Sm" and ord(char) > 0x7e) or ord(char) > 0xFFFF):
            return f"contains a symbol or emoji (U+{ord(char):04X})"
        if symbols and 0x2010 <= ord(char) <= 0x2015:
            return f"contains a dash that is not a hyphen (U+{ord(char):04X})"
    if markup:
        if ENTITY_RE.search(value):
            return "contains an HTML entity, which the generated Markdown would decode"
        if "://" in value or re.search(r"\bwww\.", value):
            return "contains an address, which the generated Markdown would turn into a link that no rule has checked"
        if "~~" in value or EMPHASIS_RE.search(value) or value.count("$") > 1:
            return "contains underscores, tildes, or dollar signs that the generated Markdown would read as markup"
    return None


def check_text(value, where: str, field: str, markup: bool = True, symbols: bool = True) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        return [f"{where}: {field} must be text without surrounding space"]
    problem = text_problem(value, markup, symbols)
    return [f"{where}: {field} {problem}"] if problem else []


def check_taxonomy(tax: dict) -> list[str]:
    errs = []
    for key in ("kinds", "costs", "groups", "domains"):
        ids = [x.get("id") for x in tax.get(key, [])]
        for i in ids:
            if not i or not ID_RE.match(i):
                errs.append(f"taxonomy {key}: bad id {i!r}")
        if len(ids) != len(set(ids)):
            errs.append(f"taxonomy {key}: duplicate id")
    for key in ("kinds", "costs"):
        for item in tax.get(key, []):
            for field in ("label", "means"):
                errs += check_text(item.get(field), f"taxonomy {key} {item.get('id')}", field)
    groups = {g["id"] for g in tax["groups"]}
    for group in tax["groups"]:
        for field in ("title", "note"):
            errs += check_text(group.get(field), f"taxonomy group {group.get('id')}", field)
    for dom in tax["domains"]:
        for field in ("title", "covers", "boundary", "group"):
            if not dom.get(field):
                errs.append(f"taxonomy domain {dom.get('id')}: missing {field}")
        for field in ("title", "covers", "boundary"):
            errs += check_text(dom.get(field), f"taxonomy domain {dom.get('id')}", field)
        if dom.get("group") not in groups:
            errs.append(f"taxonomy domain {dom.get('id')}: unknown group {dom.get('group')!r}")
        sids = [s.get("id") for s in dom.get("sections") or []]
        if len(sids) != len(set(sids)):
            errs.append(f"taxonomy domain {dom['id']}: duplicate section id")
        titles = [s.get("title") for s in dom.get("sections") or []]
        if len(titles) != len(set(titles)):
            errs.append(f"taxonomy domain {dom['id']}: duplicate section title")
        if len(sids) > MAX_LIST:
            errs.append(f"taxonomy domain {dom['id']}: more than {MAX_LIST} sections")
        for s in dom.get("sections") or []:
            if not s.get("id") or not ID_RE.match(s["id"]) or not s.get("title") or not s.get("question"):
                errs.append(f"taxonomy domain {dom['id']}: section needs id, title and question ({s})")
            for field in ("title", "question"):
                errs += check_text(s.get(field), f"taxonomy domain {dom['id']} section {s.get('id')}", field)
    sections = {(d["id"], s["id"]) for d in tax["domains"] for s in d.get("sections") or []}
    domains = {d["id"] for d in tax["domains"]}
    for row in tax.get("start_here", []):
        did, _, sid = row["to"].partition("/")
        if did not in domains or (sid and (did, sid) not in sections):
            errs.append(f"taxonomy start_here: unknown target {row['to']!r}")
        errs += check_text(row.get("want"), "taxonomy start_here", "want")
    return errs


def check_description(text, where: str) -> list[str]:
    errs = []
    if not isinstance(text, str) or not text.strip():
        return [f"{where}: description is missing"]
    n = catalog.word_count(text)
    if n > MAX_WORDS:
        errs.append(f"{where}: description has {n} words, the limit is {MAX_WORDS}")
    if not text.endswith("."):
        errs.append(f"{where}: description must end with a period")
    if re.search(r"[.!?]\s+[A-Z]", text.replace("U.S. ", "US ")):
        errs.append(f"{where}: description must be one sentence")
    m = BANNED_RE.search(text)
    if m:
        errs.append(f"{where}: description uses the word {m.group(1)!r}; name the property instead")
    return errs


def check_records(tax: dict, records: list[dict]) -> list[str]:
    errs = []
    kinds = {k["id"] for k in tax["kinds"]}
    costs = {c["id"] for c in tax["costs"]}
    sections = {(d["id"], s["id"]) for d in tax["domains"] for s in d.get("sections") or []}
    domains = {d["id"] for d in tax["domains"]}
    ids, addresses, names = {}, {}, {}
    for r in records:
        rid = r.get("id")
        where = f"{r.get('domain')}/{rid}"
        for field in REQUIRED:
            if r.get(field) in (None, "", []):
                errs.append(f"{where}: missing {field}")
        unknown = set(r) - KNOWN_FIELDS
        if unknown:
            errs.append(f"{where}: unknown field(s) {sorted(unknown)}")
        if not isinstance(rid, str) or not ID_RE.match(rid):
            errs.append(f"{where}: id must be a lower-case slug")
        if rid in ids:
            errs.append(f"{where}: duplicate id, also in {ids[rid]}")
        ids[rid] = where
        if r.get("domain") not in domains:
            errs.append(f"{where}: file name is not a domain in the taxonomy")
        elif (r["domain"], r.get("section")) not in sections:
            errs.append(f"{where}: unknown section {r.get('section')!r}")
        for ref in r.get("also_in") or []:
            did, _, sid = str(ref).partition("/")
            if (did, sid) not in sections:
                errs.append(f"{where}: also_in names an unknown section {ref!r}")
            if (did, sid) == (r.get("domain"), r.get("section")):
                errs.append(f"{where}: also_in repeats the record's own section")
        if r.get("kind") not in kinds:
            errs.append(f"{where}: unknown kind {r.get('kind')!r}")
        if r.get("cost") not in costs:
            errs.append(f"{where}: unknown cost {r.get('cost')!r}")
        status = r.get("status", "active")
        if status not in STATUSES:
            errs.append(f"{where}: unknown status {status!r}")
        errs += check_url(r.get("url"), where)
        previously = r.get("previously") or []
        if not isinstance(previously, list):
            errs.append(f"{where}: previously must be a list of addresses")
            previously = []
        for old in previously:
            errs += check_url(old, f"{where} previously")
        # One address belongs to one record, whether it is the current address or an earlier one.
        for address in dict.fromkeys([r.get("url")] + list(previously)):
            if isinstance(address, str):
                norm = catalog.normalize_url(address)
                if norm in addresses and addresses[norm] != where:
                    errs.append(f"{where}: duplicate address, also held by {addresses[norm]} ({address[:80]})")
                addresses[norm] = where
        if isinstance(r.get("name"), str):
            key = r["name"].casefold()
            if key in names:
                errs.append(f"{where}: duplicate name, also in {names[key]}")
            names[key] = where
        chk = r.get("checked") or {}
        if not isinstance(chk, dict) or not DATE_RE.match(str(chk.get("date", ""))):
            errs.append(f"{where}: checked.date must be YYYY-MM-DD")
        elif not isinstance(chk.get("status"), int) or not isinstance(chk.get("final"), str) or chk.get("how") not in HOWS:
            errs.append(f"{where}: checked needs status (a number), final (an address) and how ({', '.join(sorted(HOWS))})")
        if r.get("cost") == "unconfirmed" and chk.get("how") != "blocked":
            errs.append(f"{where}: cost may be unconfirmed only when the address could not be opened (checked.how: blocked)")
        maint = r.get("maintenance")
        if maint is not None:
            if not isinstance(maint, dict) or maint.get("state") not in MAINTENANCE or set(maint) - {"state", "since"}:
                errs.append(f"{where}: maintenance needs state ({', '.join(sorted(MAINTENANCE))}) and may carry since")
            elif maint.get("since") is not None and not SINCE_RE.match(str(maint["since"])):
                errs.append(f"{where}: maintenance.since must be YYYY, YYYY-MM or YYYY-MM-DD")
            elif maint["state"] == "dormant" and not maint.get("since"):
                errs.append(f"{where}: a dormant resource needs maintenance.since, the date of its last update")
        if status == "active":
            errs += check_description(r.get("description"), where)
            if chk.get("how") == "blocked" and not r.get("notes"):
                errs.append(f"{where}: a blocked address needs notes that name what was read instead")
        else:
            if not r.get("notes"):
                errs.append(f"{where}: a {status} record needs notes that say why")
        if r.get("replaced_by") and r["replaced_by"] not in {x.get("id") for x in records}:
            errs.append(f"{where}: replaced_by names an unknown record")
        for field in RENDERED_FIELDS:
            errs += check_text(r.get(field), where, field)
        # Notes stay in the data, so markup characters cannot break a page; the other text rules apply.
        errs += check_text(r.get("notes"), where, "notes", markup=False)
        for field in RENDERED_FIELDS + ("notes",):
            value = r.get(field)
            if isinstance(value, str) and PRIVATE_RE.search(value):
                errs.append(f"{where}: {field} contains a file path or an email address")
    return errs


def check_compact(records: list[dict], compact: dict, original: list[dict]) -> list[str]:
    errs = []
    by_id = {r["id"]: r for r in records}
    folders = compact.get("folders") or []
    if len(folders) > MAX_LIST:
        errs.append(f"compact: {len(folders)} folders, the limit is {MAX_LIST}")
    # Titles and labels of the compact set are frozen and carry emoji and arrows, so only markup and
    # control characters are rejected in them.
    errs += check_text(compact.get("title"), "compact", "title", symbols=False)
    for folder in folders:
        errs += check_text(folder.get("title"), "compact folder", "title", symbols=False)
        subs = folder.get("sections") or []
        if len(subs) > MAX_LIST:
            errs.append(f"compact {folder['title']!r}: {len(subs)} subsections, the limit is {MAX_LIST}")
        if not folder.get("links") and not subs:
            errs.append(f"compact {folder['title']!r}: empty folder")
        for sub in subs:
            errs += check_text(sub.get("title"), f"compact {folder['title']!r} subsection", "title", symbols=False)
    for ftitle, stitle, links in catalog.compact_lists(compact):
        where = f"compact {ftitle!r}" + (f" / {stitle!r}" if stitle else "")
        if len(links) > MAX_LIST:
            errs.append(f"{where}: {len(links)} links, the limit is {MAX_LIST}")
        if not links:
            errs.append(f"{where}: empty list")
        for link in links:
            rec = by_id.get(link.get("id"))
            if rec is None:
                errs.append(f"{where}: unknown resource id {link.get('id')!r}")
                continue
            if link.get("label") is None:
                errs.append(f"{where}: {link['id']} has no label")
            errs += check_text(link.get("label"), where, f"label of {link['id']}", symbols=False)
            if "url" in link:
                if link["url"] == rec["url"]:
                    errs.append(f"{where}: {link['id']} is pinned to the record's own address; remove the pin")
                errs += check_url(link["url"], f"{where} pin for {link['id']}")
    # every original link still maps to a record
    known = {}
    for r in records:
        for url in [r.get("url")] + list(r.get("previously") or []):
            known[url] = r["id"]
    for row in original:
        if row["address"] not in known:
            errs.append(f"original link not accounted for: {row['label']} ({row['address']})")
    return errs


def ignore_share(records: list[dict], compact: dict, ignore: dict) -> tuple[int, int]:
    """How many of the addresses the catalog publishes are covered by the ignore list, and how many there are."""
    addresses = catalog.published_addresses(records, compact)
    entries = [e for e in ignore.get("entries") or [] if isinstance(e.get("url"), str)]
    covered = [a for a in addresses if any(catalog.ignore_matches(e, a) for e in entries)]
    return len(covered), len(addresses)


def check_ignore(records: list[dict], compact: dict, ignore: dict) -> list[str]:
    errs = []
    limit = ignore.get("max_share_percent")
    if isinstance(limit, bool) or not isinstance(limit, (int, float)) or not 0 < limit <= 100:
        errs.append("link-check ignore list: max_share_percent must be a number above 0 and at most 100")
        limit = 100
    unknown = set(ignore) - {"max_share_percent", "entries"}
    if unknown:
        errs.append(f"link-check ignore list: unknown key(s) {sorted(unknown)}")
    addresses = set(catalog.published_addresses(records, compact))
    readme = catalog.ROOT / "README.md"
    cited = set(re.findall(r"\]\((https?://[^)\s]+)\)", readme.read_text(encoding="utf-8"))) if readme.exists() else set()
    seen = set()
    for item in ignore.get("entries") or []:
        if not isinstance(item.get("url"), str) or not item.get("reason") or not DATE_RE.match(str(item.get("opened", ""))):
            errs.append(f"link-check ignore list: each entry needs url, reason and opened ({item.get('url')})")
            continue
        url = item["url"]
        errs += check_url(url, "link-check ignore list")
        if set(item) - {"url", "match", "only", "reason", "opened"}:
            errs.append(f"link-check ignore list: {url}: unknown key(s) {sorted(set(item) - {'url', 'match', 'only', 'reason', 'opened'})}")
        if item.get("match") not in ("prefix", "exact"):
            errs.append(f"link-check ignore list: {url}: 'match' must say prefix or exact")
            continue
        if item["match"] == "prefix" and not url.endswith("/"):
            errs.append(f"link-check ignore list: {url}: a prefix entry must end with a slash, so that it cannot match another host or page")
        if item.get("only") not in (None, "ci"):
            errs.append(f"link-check ignore list: {url}: 'only' may be omitted or set to ci")
        if url in seen:
            errs.append(f"link-check ignore list: {url} is listed twice")
        seen.add(url)
        if not any(catalog.ignore_matches(item, a) for a in addresses | cited):
            errs.append(f"link-check ignore list: {url} matches no address in the catalog; remove it")
    covered, total = ignore_share(records, compact, ignore)
    if total and covered * 100 > limit * total:
        errs.append(f"link-check ignore list covers {covered} of {total} addresses ({covered * 100 / total:.1f}%), "
                    f"more than the {limit}% the data file allows; open the pages by hand or raise the limit on purpose")
    return errs


class _Bookmarks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.folders, self.links = 0, []

    def handle_starttag(self, tag, attrs):
        if tag == "h3":
            self.folders += 1
        if tag == "a":
            self.links.append(dict(attrs).get("href"))


def parse_bookmarks(text: str) -> tuple[int, list[str]]:
    p = _Bookmarks()
    p.feed(text)
    return p.folders, p.links


def check_internal_links(outputs: dict[str, str]) -> list[str]:
    """Every relative link in a generated Markdown page must reach a file, and its anchor a heading."""
    errs = []
    anchors = {}
    for rel, text in outputs.items():
        if rel.endswith(".md"):
            anchors[rel] = {catalog.slug(line.lstrip("#")) for line in text.split("\n") if line.startswith("#")}
    for rel, text in outputs.items():
        if not rel.endswith(".md"):
            continue
        base = rel.rsplit("/", 1)[0] + "/" if "/" in rel else ""
        for target in MD_LINK_RE.findall(text):
            if re.match(r"^[a-z]+:", target):
                continue
            path, _, anchor = target.partition("#")
            parts = []
            for seg in (base + path).split("/") if path else rel.split("/"):
                if seg == "..":
                    parts.pop()
                elif seg not in ("", "."):
                    parts.append(seg)
            dest = "/".join(parts)
            if dest in anchors:
                if anchor and anchor not in anchors[dest]:
                    errs.append(f"{rel}: link to {target} names a heading that {dest} does not have")
            elif not (catalog.ROOT / dest).exists():
                errs.append(f"{rel}: link to {target} reaches no file")
    return errs


def check_tables(outputs: dict[str, str]) -> list[str]:
    """Every row of a generated Markdown table must have as many cells as its header."""
    errs = []
    cell_end = re.compile(r"(?<!\\)\|")
    for rel, text in outputs.items():
        if not rel.endswith(".md"):
            continue
        width = None
        for i, line in enumerate(text.split("\n"), start=1):
            if not line.startswith("|"):
                width = None
                continue
            cells = len(cell_end.findall(line)) - 1
            if width is None:
                width = cells
            elif cells != width:
                errs.append(f"{rel} line {i}: table row has {cells} cells, its header has {width}")
    return errs


def check_generated(records: list[dict], compact: dict, outputs: dict[str, str]) -> list[str]:
    """Parse the generated files the way a consumer would and compare them with the data."""
    errs = []
    by_id = {r["id"]: r for r in records}
    expect = [catalog.compact_address(l, by_id) for _, _, links in catalog.compact_lists(compact) for l in links]
    n_folders = len(compact["folders"])
    n_subs = sum(len(f.get("sections") or []) for f in compact["folders"])

    lines = outputs["LINKS.md"].split("\n")
    seen, h2, h3 = [], 0, 0
    for i, line in enumerate(lines[1:], start=2):
        if line.startswith("## "):
            h2 += 1
        elif line.startswith("### "):
            h3 += 1
        elif line.startswith("- "):
            m = LINK_RE.match(line)
            if not m:
                errs.append(f"LINKS.md line {i}: not in the form '- [Label](address)' with nothing after it")
            else:
                seen.append(m.group(2))
        elif line.strip() and i > 3:
            errs.append(f"LINKS.md line {i}: unexpected text")
    if (h2, h3) != (n_folders, n_subs):
        errs.append(f"LINKS.md: {h2} folders and {h3} subsections, the data has {n_folders} and {n_subs}")
    if seen != expect:
        errs.append(f"LINKS.md: {len(seen)} links parsed, the data has {len(expect)} (or the order differs)")

    folders, links = parse_bookmarks(outputs["bookmarks.html"])
    if folders != 1 + n_folders + n_subs:
        errs.append(f"bookmarks.html: {folders} folders parsed, expected {1 + n_folders + n_subs}")
    if links != expect:
        errs.append(f"bookmarks.html: {len(links)} links parsed, the data has {len(expect)} (or the order differs)")

    errs += check_internal_links(outputs)
    errs += check_tables(outputs)

    active = [r for r in records if catalog.is_active(r)]
    _, full_links = parse_bookmarks(outputs["bookmarks-full.html"])
    if sorted(full_links) != sorted(r["url"] for r in active):
        errs.append(f"bookmarks-full.html: {len(full_links)} links parsed, the catalog shows {len(active)} resources")
    return errs


def collect(data: dict) -> list[str]:
    errs = check_taxonomy(data["tax"])
    errs += check_records(data["tax"], data["records"])
    errs += check_compact(data["records"], data["compact"], data["original"])
    errs += check_ignore(data["records"], data["compact"], data["ignore"])
    return errs


def report(data: dict) -> None:
    recs = data["records"]
    active = [r for r in recs if catalog.is_active(r)]
    print(f"records: {len(recs)} ({len(active)} shown, "
          f"{sum(1 for r in recs if r.get('status') == 'retired')} retired, "
          f"{sum(1 for r in recs if r.get('status') == 'unverified')} unverified)")
    for dom in data["tax"]["domains"]:
        n = sum(1 for r in active if r["domain"] == dom["id"])
        if n:
            print(f"  {dom['id']}: {n}")
    hows = {how: sum(1 for r in active if r["checked"]["how"] == how) for how in sorted(HOWS)}
    print(f"how the shown records were read: {hows['script']} by script, {hows['browser']} in a browser, "
          f"{hows['blocked']} from another page of the same publisher because the address refused every client")
    print(f"shown records that carry a maintenance state: {sum(1 for r in active if r.get('maintenance'))}")
    lists = list(catalog.compact_lists(data["compact"]))
    links = [l for _, _, ls in lists for l in ls]
    print(f"compact set: {len(links)} links in {len(lists)} lists, {len({l['id'] for l in links})} distinct resources, "
          f"{sum(1 for l in links if 'url' in l)} pinned to an earlier address; longest list {max(len(ls) for _, _, ls in lists)}")
    print(f"original links accounted for: {len(data['original'])}")
    covered, total = ignore_share(recs, data["compact"], data["ignore"])
    entries = data["ignore"].get("entries") or []
    print(f"link-check ignore list: {len(entries)} entries ({sum(1 for e in entries if e.get('only') == 'ci')} for the CI check only) "
          f"cover {covered} of {total} published addresses ({covered * 100 / total:.1f}%); the limit is {data['ignore'].get('max_share_percent')}%")


# ---------------------------------------------------------------- planted failures
BAD_ADDRESSES = [
    ("an http address", "http://example.org/", "must be https"),
    ("an address with no host", "https:///path", "no host"),
    ("a control character", "https://example.org/a\x07b", "control character"),
    ("a space", "https://example.org/a b", "whitespace"),
    ("a newline", "https://example.org/a\nb", "whitespace"),
    ("a double quote", 'https://example.org/a"b', "must be percent-encoded"),
    ("an angle bracket", "https://example.org/<b>", "must be percent-encoded"),
    ("a pipe", "https://example.org/a|b", "must be percent-encoded"),
    ("a parenthesis", "https://example.org/a_(b)", "must be percent-encoded"),
    ("a square bracket", "https://example.org/a[0]", "must be percent-encoded"),
    ("a backslash", "https://example.org\\path", "must be percent-encoded"),
    ("an IPv4 host", "https://192.0.2.7/", "IP literal"),
    ("an IPv6 host", "https://[2001:db8::1]/", "must be percent-encoded"),
    ("a shorthand IP host", "https://127.1/", "looks like an IP address"),
    ("a hex IP host", "https://0x7f.0.0.0x1/", "looks like an IP address"),
    ("an explicit port", "https://example.org:8443/", "explicit port"),
    ("a port that is not a number", "https://example.org:https/", "invalid host or port"),
    ("an empty port", "https://example.org:/", "empty port"),
    ("credentials", "https://user@example.org/", "credentials"),
    ("a punycode host", "https://xn--e1afmkfd.example/", "punycode"),
    ("a non-ASCII host", "https://ex\u00e4mple.org/", "non-ASCII"),
    ("a single-label host", "https://localhost/", "single label"),
    ("an invalid DNS label", "https://-bad-.example.org/", "invalid DNS label"),
    ("an encoded slash in the host", "https://example.org%2fevil.example/", "invalid DNS label"),
    ("a dot path segment", "https://example.org/a/../b", "dot path segment"),
    ("an encoded dot segment", "https://example.org/a/%2e%2e/b", "dot path segment"),
    ("an encoded slash in the path", "https://example.org/a%2fb", "encoded slash"),
    ("an encoded backslash in the path", "https://example.org/a%5Cb", "encoded slash"),
    ("620 characters", "https://example.org/" + "a" * 600, "longer than 512"),
    ("a tracking parameter", "https://example.org/page?utm_source=list", "tracking or affiliate"),
    ("a link shortener", "https://bit.ly/abc123", "link shortener"),
    ("a TeamStarWolf repository", "https://github.com/teamstarwolf/TeamStarWolf", "TeamStarWolf property"),
    ("a TeamStarWolf site", "https://library.teamstarwolf.com/", "TeamStarWolf property"),
    ("an HTML entity", "https://example.org/page?a=1&amp;b=2", "HTML entity"),
    ("an upper-case scheme", "HTTPS://example.org/", "must be https"),
    ("a host that ends with a dot", "https://example.org./", "invalid DNS label"),
    ("a javascript address", "javascript:alert(1)", "must be percent-encoded"),
    ("a data address", "data:text/html,hello", "must be https"),
]
BAD_TEXT = [
    ("a closing bracket", "Tool] name", "read as markup"),
    ("an opening bracket", "Tool [beta", "read as markup"),
    ("raw HTML", "A <b>bold</b> tool", "read as markup"),
    ("a backtick", "A `quoted` tool", "read as markup"),
    ("an asterisk", "A *starred* tool", "read as markup"),
    ("a backslash", "A back\\slash tool", "read as markup"),
    ("an HTML entity", "A tool &lt;for&gt; hosts", "HTML entity"),
    ("an address in the text", "A tool from https://example.org/ for hosts", "contains an address"),
    ("a www address in the text", "A tool from www.example.org for hosts", "contains an address"),
    ("underscore emphasis", "A _very_ good tool", "read as markup"),
    ("a strikethrough", "A ~~bad~~ good tool", "read as markup"),
    ("a pair of dollar signs", "Costs $5 or $10 a month", "read as markup"),
    ("a newline", "First line\nsecond line", "control character"),
    ("a tab", "First\tsecond", "control character"),
    ("an emoji", "A scanner \U0001F525 for hosts", "symbol or emoji"),
    ("a pictograph", "A scanner \u2705 for hosts", "symbol or emoji"),
    ("an arrow", "A scanner \u2192 for hosts", "symbol or emoji"),
    ("an en dash", "A scanner \u2013 for hosts", "dash that is not a hyphen"),
    ("an em dash", "A scanner \u2014 for hosts", "dash that is not a hyphen"),
    ("a non-breaking space", "A scanner\u00a0for hosts", "non-standard space"),
    ("a zero-width space", "A scan\u200bner for hosts", "control character"),
    ("a right-to-left override", "A scan\u202ener for hosts", "control character"),
]
LABEL_FAULTS = ("a closing bracket", "an opening bracket", "raw HTML", "a newline", "a non-breaking space",
                "a zero-width space", "a right-to-left override")


def self_test() -> int:
    base = load_all()
    clean = collect(base)
    if clean:
        print("self-test: the unmodified data must pass first")
        print("\n".join(clean[:20]))
        return 1

    def first_active(d):
        return next(r for r in d["records"] if catalog.is_active(r))

    def first_list(d):
        return next(links for _, _, links in catalog.compact_lists(d["compact"]))

    cases = []

    def case(label, expected):
        def wrap(fn):
            cases.append((label, fn, expected))
            return fn
        return wrap

    @case("a duplicate id", "duplicate id")
    def _(d):
        d["records"].append(dict(copy.deepcopy(first_active(d)), url="https://example.org/other", name="Other name"))

    @case("a duplicate address", "duplicate address")
    def _(d):
        r = first_active(d)
        d["records"].append(dict(copy.deepcopy(r), id="planted-copy", name="Planted copy", url=r["url"].rstrip("/")))

    @case("an address that another record keeps as an earlier address", "duplicate address")
    def _(d):
        a, b = [r for r in d["records"] if catalog.is_active(r)][:2]
        b["previously"] = list(b.get("previously") or []) + [a["url"]]

    @case("an earlier address shared by two records", "duplicate address")
    def _(d):
        a, b = [r for r in d["records"] if catalog.is_active(r)][:2]
        a["previously"] = list(a.get("previously") or []) + ["https://example.org/old"]
        b["previously"] = list(b.get("previously") or []) + ["https://example.org/old/"]

    @case("a duplicate name", "duplicate name")
    def _(d):
        a, b = [r for r in d["records"] if catalog.is_active(r)][:2]
        b["name"] = a["name"].upper()

    @case("a 30-word description", "description has 30 words")
    def _(d):
        first_active(d)["description"] = " ".join(["word"] * 30) + "."

    @case("a list of 17 in the compact set", "17 links, the limit is 16")
    def _(d):
        lst = first_list(d)
        while len(lst) < 17:
            lst.append(dict(lst[0]))

    @case("17 folders in the compact set", "17 folders, the limit is 16")
    def _(d):
        while len(d["compact"]["folders"]) < 17:
            d["compact"]["folders"].append(copy.deepcopy(d["compact"]["folders"][0]))

    @case("17 subsections in a compact folder", "17 subsections, the limit is 16")
    def _(d):
        folder = next(f for f in d["compact"]["folders"] if f.get("sections"))
        while len(folder["sections"]) < 17:
            folder["sections"].append(copy.deepcopy(folder["sections"][0]))

    @case("a selling adjective", "uses the word 'comprehensive'")
    def _(d):
        first_active(d)["description"] = "A comprehensive scanner for hosts."

    @case("an unknown section", "unknown section")
    def _(d):
        first_active(d)["section"] = "no-such-section"

    @case("a missing description", "description is missing")
    def _(d):
        first_active(d).pop("description")

    @case("two sentences", "must be one sentence")
    def _(d):
        first_active(d)["description"] = "A scanner for hosts. It also scans networks."

    @case("a pin equal to the record's address", "remove the pin")
    def _(d):
        lst = first_list(d)
        lst[0]["url"] = next(r for r in d["records"] if r["id"] == lst[0]["id"])["url"]

    @case("an original link with no record", "original link not accounted for")
    def _(d):
        gone = d["original"][0]["address"]
        for r in d["records"]:
            if r["url"] == gone:
                r["url"] = "https://example.org/moved"
            r["previously"] = [u for u in r.get("previously") or [] if u != gone]

    @case("an unknown kind", "unknown kind")
    def _(d):
        first_active(d)["kind"] = "gadget"

    @case("an unknown field", "unknown field")
    def _(d):
        first_active(d)["rating"] = 5

    @case("an unconfirmed cost on a readable address", "cost may be unconfirmed only")
    def _(d):
        next(r for r in d["records"] if catalog.is_active(r) and r["checked"]["how"] != "blocked")["cost"] = "unconfirmed"

    @case("an unknown id in the compact set", "unknown resource id")
    def _(d):
        first_list(d)[0]["id"] = "no-such-resource"

    @case("a retired record without notes", "needs notes that say why")
    def _(d):
        r = first_active(d)
        r["status"] = "retired"
        r.pop("notes", None)

    @case("a blocked address without notes", "needs notes that name what was read instead")
    def _(d):
        r = first_active(d)
        r["checked"]["how"] = "blocked"
        r.pop("notes", None)

    @case("a file path in notes", "file path or an email address")
    def _(d):
        first_active(d)["notes"] = "Copied from C:\\Users\\someone\\notes.txt"

    @case("an email address in the publisher", "file path or an email address")
    def _(d):
        first_active(d)["publisher"] = "someone@example.org"

    @case("an unknown maintenance state", "maintenance needs state")
    def _(d):
        first_active(d)["maintenance"] = {"state": "sleepy"}

    @case("a dormant resource with no date", "needs maintenance.since")
    def _(d):
        first_active(d)["maintenance"] = {"state": "dormant"}

    @case("a maintenance date that is not a date", "maintenance.since must be")
    def _(d):
        first_active(d)["maintenance"] = {"state": "archived", "since": "last spring"}

    @case("a stale ignore entry", "matches no address in the catalog")
    def _(d):
        d["ignore"]["entries"].append({"url": "https://nowhere.example/", "match": "prefix", "reason": "planted", "opened": "2026-01-01"})

    @case("an ignore entry that does not say prefix or exact", "must say prefix or exact")
    def _(d):
        d["ignore"]["entries"][0].pop("match")

    @case("an ignore prefix that could match another host", "must end with a slash")
    def _(d):
        entry = next(e for e in d["ignore"]["entries"] if e["match"] == "prefix")
        entry["url"] = entry["url"].rstrip("/")

    @case("an ignore entry without a reason", "needs url, reason and opened")
    def _(d):
        d["ignore"]["entries"][0].pop("reason")

    @case("an ignore list over its stated share", "more than the")
    def _(d):
        d["ignore"]["max_share_percent"] = 0.1

    @case("an ignore list with no stated share", "max_share_percent must be")
    def _(d):
        d["ignore"].pop("max_share_percent")

    for label, address, expected in BAD_ADDRESSES:
        def plant_url(d, address=address):
            first_active(d)["url"] = address
        cases.append((f"record address: {label}", plant_url, expected))

        def plant_previous(d, address=address):
            first_active(d)["previously"] = [address]
        cases.append((f"earlier address: {label}", plant_previous, expected))

        def plant_pin(d, address=address):
            first_list(d)[0]["url"] = address
        cases.append((f"compact pin: {label}", plant_pin, expected))

    for label, text, expected in BAD_TEXT:
        for field in RENDERED_FIELDS:
            def plant_text(d, text=text, field=field):
                first_active(d)[field] = text + ("." if field == "description" else "")
            cases.append((f"{field}: {label}", plant_text, expected))
        if label in LABEL_FAULTS:
            def plant_label(d, text=text):
                first_list(d)[0]["label"] = text
            cases.append((f"compact label: {label}", plant_label, expected))

    failed, groups = [], {}
    for label, plant, expected in cases:
        d = copy.deepcopy(base)
        plant(d)
        ok = any(expected in e for e in collect(d))
        group = label.split(":")[0] if ":" in label else "data rules"
        groups.setdefault(group, [0, 0])
        groups[group][0] += 1 if ok else 0
        groups[group][1] += 1
        print(f"  {'rejected' if ok else 'NOT REJECTED'}: {label}")
        if not ok:
            failed.append(label)

    # A row whose cell count differs from its header is caught in the generated pages.
    broken = {"domains/planted.md": "| A | B |\n|---|---|\n| one | two | three |\n"}
    table_ok = any("table row has 3 cells" in e for e in check_tables(broken))
    print(f"  {'rejected' if table_ok else 'NOT REJECTED'}: generated page: a table row with an extra cell")
    groups["generated page"] = [1 if table_ok else 0, 1]
    if not table_ok:
        failed.append("a table row with an extra cell")

    total = sum(n for _, n in groups.values())
    print("  by kind: " + "; ".join(f"{k} {a} of {n}" for k, (a, n) in groups.items()))
    print(f"self-test: {total - len(failed)} of {total} planted faults rejected; the unmodified data passes")
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    data = load_all()
    errs = collect(data)
    if not errs:
        # The generated files are parsed the way a consumer would read them.
        import build
        errs += check_generated(data["records"], data["compact"], build.Catalog().outputs())
    if errs:
        print("\n".join(errs))
        print(f"validate: {len(errs)} error(s)")
        return 1
    report(data)
    print("validate: no errors")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
