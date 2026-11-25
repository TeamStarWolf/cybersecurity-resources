"""Check the catalog data against its rules.

    python scripts/validate.py              check the data; exit 1 on any error
    python scripts/validate.py --self-test  plant one fault per rule and confirm each is rejected

The rules cover the taxonomy, every resource record, the compact bookmark set and its limits, the
link-check ignore list, and the original links this collection began with. No network access.
"""
from __future__ import annotations

import copy
import csv
import re
import sys
from html.parser import HTMLParser

import catalog
from catalog import DATA, HTTP_ALLOWED, MAX_LIST

ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LINK_RE = re.compile(r"^- \[([^\]\n]+)\]\((\S+)\)$")
MAX_WORDS = 25
STATUSES = {"active", "retired", "unverified"}
HOWS = {"script", "browser", "blocked"}
REQUIRED = ("id", "name", "url", "publisher", "section", "kind", "cost", "checked")
KNOWN_FIELDS = set(REQUIRED) | {"domain", "description", "also_in", "formerly", "previously", "status", "replaced_by", "notes"}

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
EM_DASH = "\u2014"


def load_original() -> list[dict]:
    with open(DATA / "original-292.tsv", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def load_all() -> dict:
    return {
        "tax": catalog.load_taxonomy(),
        "records": catalog.load_resources(),
        "compact": catalog.load_compact(),
        "ignore": catalog.read_yaml(DATA / "link-check-ignore.yaml") or [],
        "original": load_original(),
    }


def check_url(url, where: str) -> list[str]:
    errs = []
    if not isinstance(url, str) or not url or re.search(r"\s", url):
        return [f"{where}: address is missing or contains whitespace"]
    if not url.startswith("https://") and url not in HTTP_ALLOWED:
        errs.append(f"{where}: address must be https ({url})")
    m = re.match(r"^https?://([^/?#]+)", url)
    host = m.group(1).lower() if m else ""
    if "@" in host:
        errs.append(f"{where}: address carries credentials ({url})")
    if host.removeprefix("www.") in SHORTENERS:
        errs.append(f"{where}: link shortener ({url})")
    if TRACKING_RE.search(url):
        errs.append(f"{where}: tracking or affiliate parameter ({url})")
    return errs


def check_taxonomy(tax: dict) -> list[str]:
    errs = []
    for key in ("kinds", "costs", "groups", "domains"):
        ids = [x.get("id") for x in tax.get(key, [])]
        for i in ids:
            if not i or not ID_RE.match(i):
                errs.append(f"taxonomy {key}: bad id {i!r}")
        if len(ids) != len(set(ids)):
            errs.append(f"taxonomy {key}: duplicate id")
    groups = {g["id"] for g in tax["groups"]}
    for dom in tax["domains"]:
        for field in ("title", "covers", "boundary", "group"):
            if not dom.get(field):
                errs.append(f"taxonomy domain {dom.get('id')}: missing {field}")
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
    sections = {(d["id"], s["id"]) for d in tax["domains"] for s in d.get("sections") or []}
    domains = {d["id"] for d in tax["domains"]}
    for row in tax.get("start_here", []):
        did, _, sid = row["to"].partition("/")
        if did not in domains or (sid and (did, sid) not in sections):
            errs.append(f"taxonomy start_here: unknown target {row['to']!r}")
    return errs


def check_description(text, where: str) -> list[str]:
    errs = []
    if not isinstance(text, str) or not text.strip():
        return [f"{where}: description is missing"]
    if "\n" in text or text != text.strip():
        errs.append(f"{where}: description must be one line without surrounding space")
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
    if EM_DASH in text:
        errs.append(f"{where}: description contains an em dash")
    return errs


def check_records(tax: dict, records: list[dict]) -> list[str]:
    errs = []
    kinds = {k["id"] for k in tax["kinds"]}
    costs = {c["id"] for c in tax["costs"]}
    sections = {(d["id"], s["id"]) for d in tax["domains"] for s in d.get("sections") or []}
    domains = {d["id"] for d in tax["domains"]}
    ids, urls, names = {}, {}, {}
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
        for old in r.get("previously") or []:
            if not isinstance(old, str) or not re.match(r"^https?://\S+$", old):
                errs.append(f"{where}: previously must list addresses")
        if isinstance(r.get("url"), str):
            norm = catalog.normalize_url(r["url"])
            if norm in urls:
                errs.append(f"{where}: duplicate address, also in {urls[norm]}")
            urls[norm] = where
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
        if status == "active":
            errs += check_description(r.get("description"), where)
            if chk.get("how") == "blocked" and not r.get("notes"):
                errs.append(f"{where}: a blocked address needs notes that name what was read instead")
        else:
            if not r.get("notes"):
                errs.append(f"{where}: a {status} record needs notes that say why")
        if r.get("replaced_by") and r["replaced_by"] not in {x.get("id") for x in records}:
            errs.append(f"{where}: replaced_by names an unknown record")
        for field in ("name", "publisher", "description", "notes", "formerly"):
            value = r.get(field)
            if isinstance(value, str):
                if EM_DASH in value:
                    errs.append(f"{where}: {field} contains an em dash")
                if PRIVATE_RE.search(value):
                    errs.append(f"{where}: {field} contains a file path or an email address")
    return errs


def check_compact(records: list[dict], compact: dict, original: list[dict]) -> list[str]:
    errs = []
    by_id = {r["id"]: r for r in records}
    folders = compact.get("folders") or []
    if len(folders) > MAX_LIST:
        errs.append(f"compact: {len(folders)} folders, the limit is {MAX_LIST}")
    for folder in folders:
        subs = folder.get("sections") or []
        if len(subs) > MAX_LIST:
            errs.append(f"compact {folder['title']!r}: {len(subs)} subsections, the limit is {MAX_LIST}")
        if not folder.get("links") and not subs:
            errs.append(f"compact {folder['title']!r}: empty folder")
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
            label = link.get("label")
            if not isinstance(label, str) or not label.strip() or re.search(r"[\]\[\n]", label):
                errs.append(f"{where}: bad label {label!r}")
            if "url" in link:
                if link["url"] == rec["url"]:
                    errs.append(f"{where}: {link['id']} is pinned to the record's own address; remove the pin")
                errs += check_url(link["url"], f"{where} pin for {link['id']}")
            errs += check_url(catalog.compact_address(link, by_id), f"{where} {link['id']}")
    # every original link still maps to a record
    known = {}
    for r in records:
        for url in [r.get("url")] + list(r.get("previously") or []):
            known[url] = r["id"]
    for row in original:
        if row["address"] not in known:
            errs.append(f"original link not accounted for: {row['label']} ({row['address']})")
    return errs


def check_ignore(records: list[dict], compact: dict, ignore: list[dict]) -> list[str]:
    errs = []
    by_id = {r["id"]: r for r in records}
    addresses = {r["url"] for r in records if isinstance(r.get("url"), str)}
    for _, _, links in catalog.compact_lists(compact):
        addresses |= {catalog.compact_address(l, by_id) for l in links if l.get("id") in by_id}
    for item in ignore:
        if not item.get("url") or not item.get("reason") or not DATE_RE.match(str(item.get("opened", ""))):
            errs.append(f"link-check ignore list: each entry needs url, reason and opened ({item.get('url')})")
            continue
        if not any(a.startswith(item["url"]) for a in addresses):
            errs.append(f"link-check ignore list: {item['url']} matches no address in the catalog; remove it")
    return errs


class _Bookmarks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.folders, self.links, self._in_h3 = 0, [], False

    def handle_starttag(self, tag, attrs):
        if tag == "h3":
            self.folders += 1
        if tag == "a":
            self.links.append(dict(attrs).get("href"))


def parse_bookmarks(text: str) -> tuple[int, list[str]]:
    p = _Bookmarks()
    p.feed(text)
    return p.folders, p.links


def check_generated(records: list[dict], compact: dict, outputs: dict[str, str]) -> list[str]:
    """Parse the generated compact files the way a consumer would and compare them with the data."""
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

    active = [r for r in records if catalog.is_active(r)]
    _, full_links = parse_bookmarks(outputs["bookmarks-full.html"])
    if sorted(full_links) != sorted(r["url"] for r in active):
        errs.append(f"bookmarks-full.html: {len(full_links)} links parsed, the catalog shows {len(active)} resources")
    return errs


MD_LINK_RE = re.compile(r"\]\(([^)\s]+)\)")


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
    lists = list(catalog.compact_lists(data["compact"]))
    links = [l for _, _, ls in lists for l in ls]
    print(f"compact set: {len(links)} links in {len(lists)} lists, {len({l['id'] for l in links})} distinct resources, "
          f"{sum(1 for l in links if 'url' in l)} pinned to an earlier address; longest list {max(len(ls) for _, _, ls in lists)}")
    print(f"original links accounted for: {len(data['original'])}")


# ---------------------------------------------------------------- planted failures
def self_test() -> int:
    base = load_all()
    clean = collect(base)
    if clean:
        print("self-test: the unmodified data must pass first")
        print("\n".join(clean[:20]))
        return 1

    def first_active(d):
        return next(r for r in d["records"] if catalog.is_active(r))

    def plant_dup_id(d):
        d["records"].append(dict(copy.deepcopy(first_active(d)), url="https://example.org/other", name="Other name"))

    def plant_dup_url(d):
        r = first_active(d)
        d["records"].append(dict(copy.deepcopy(r), id="planted-copy", name="Planted copy", url=r["url"].rstrip("/")))

    def plant_long(d):
        first_active(d)["description"] = " ".join(["word"] * 30) + "."

    def plant_http(d):
        first_active(d)["url"] = "http://example.org/"

    def plant_17(d):
        lst = next(links for _, _, links in catalog.compact_lists(d["compact"]))
        while len(lst) < 17:
            lst.append(dict(lst[0]))

    def plant_17_folders(d):
        while len(d["compact"]["folders"]) < 17:
            d["compact"]["folders"].append(copy.deepcopy(d["compact"]["folders"][0]))

    def plant_banned(d):
        first_active(d)["description"] = "A comprehensive scanner for hosts."

    def plant_section(d):
        first_active(d)["section"] = "no-such-section"

    def plant_no_description(d):
        first_active(d).pop("description")

    def plant_tracking(d):
        first_active(d)["url"] = "https://example.org/page?utm_source=list"

    def plant_shortener(d):
        first_active(d)["url"] = "https://bit.ly/abc123"

    def plant_em_dash(d):
        first_active(d)["description"] = "A scanner \u2014 for hosts."

    def plant_two_sentences(d):
        first_active(d)["description"] = "A scanner for hosts. It also scans networks."

    def plant_pin(d):
        lst = next(links for _, _, links in catalog.compact_lists(d["compact"]))
        rec = next(r for r in d["records"] if r["id"] == lst[0]["id"])
        lst[0]["url"] = rec["url"]

    def plant_lost_original(d):
        gone = d["original"][0]["address"]
        for r in d["records"]:
            if r["url"] == gone:
                r["url"] = "https://example.org/moved"
            r["previously"] = [u for u in r.get("previously") or [] if u != gone]

    def plant_kind(d):
        first_active(d)["kind"] = "gadget"

    def plant_unconfirmed(d):
        r = next(r for r in d["records"] if catalog.is_active(r) and r["checked"]["how"] != "blocked")
        r["cost"] = "unconfirmed"

    def plant_stale_ignore(d):
        d["ignore"].append({"url": "https://nowhere.example/", "reason": "planted", "opened": "2026-01-01"})

    def plant_unknown_id(d):
        next(links for _, _, links in catalog.compact_lists(d["compact"]))[0]["id"] = "no-such-resource"

    def plant_retired_without_notes(d):
        r = first_active(d)
        r["status"] = "retired"
        r.pop("notes", None)

    def plant_private(d):
        first_active(d)["notes"] = "Copied from C:\\Users\\someone\\notes.txt"

    cases = [
        ("a duplicate id", plant_dup_id, "duplicate id"),
        ("a duplicate address", plant_dup_url, "duplicate address"),
        ("a 30-word description", plant_long, "description has 30 words"),
        ("an http address", plant_http, "address must be https"),
        ("a list of 17 in the compact set", plant_17, "17 links, the limit is 16"),
        ("17 folders in the compact set", plant_17_folders, "17 folders, the limit is 16"),
        ("a selling adjective", plant_banned, "uses the word 'comprehensive'"),
        ("an unknown section", plant_section, "unknown section"),
        ("a missing description", plant_no_description, "description is missing"),
        ("a tracking parameter", plant_tracking, "tracking or affiliate parameter"),
        ("a link shortener", plant_shortener, "link shortener"),
        ("an em dash", plant_em_dash, "contains an em dash"),
        ("two sentences", plant_two_sentences, "must be one sentence"),
        ("a pin equal to the record's address", plant_pin, "remove the pin"),
        ("an original link with no record", plant_lost_original, "original link not accounted for"),
        ("an unknown kind", plant_kind, "unknown kind"),
        ("an unconfirmed cost on a readable address", plant_unconfirmed, "cost may be unconfirmed only"),
        ("a stale ignore entry", plant_stale_ignore, "matches no address in the catalog"),
        ("an unknown id in the compact set", plant_unknown_id, "unknown resource id"),
        ("a retired record without notes", plant_retired_without_notes, "needs notes that say why"),
        ("a file path in notes", plant_private, "file path or an email address"),
    ]
    failed = 0
    for label, plant, expected in cases:
        d = copy.deepcopy(base)
        plant(d)
        errs = collect(d)
        ok = any(expected in e for e in errs)
        print(f"  {'rejected' if ok else 'NOT REJECTED'}: {label}")
        failed += 0 if ok else 1
    print(f"self-test: {len(cases) - failed} of {len(cases)} planted faults rejected; the unmodified data passes")
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    data = load_all()
    errs = collect(data)
    if not errs:
        # The generated compact files are parsed the way a consumer would read them.
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
