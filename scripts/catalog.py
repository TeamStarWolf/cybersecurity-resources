"""Load the catalog data: the taxonomy, the resource records, and the compact bookmark set.

Shared by build.py, validate.py and check_links.py. Nothing here writes a file.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# The one address in the catalog that is served over http only (its https address does not answer).
HTTP_ALLOWED = {"http://flaws.cloud/"}

# Limits that the consumer of LINKS.md enforces.
MAX_LIST = 16


def read_yaml(path: Path):
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_taxonomy(data: Path = DATA) -> dict:
    return read_yaml(data / "taxonomy.yaml")


def load_resources(data: Path = DATA) -> list[dict]:
    """Every record, in file order, with its domain taken from the file name."""
    out = []
    for path in sorted((data / "resources").glob("*.yaml")):
        for rec in read_yaml(path) or []:
            rec = dict(rec)
            rec["domain"] = path.stem
            out.append(rec)
    return out


def load_compact(data: Path = DATA) -> dict:
    return read_yaml(data / "compact.yaml")


def load_ignore(data: Path = DATA) -> dict:
    """The link-check ignore list: the largest share of the catalog it may cover, and its entries."""
    loaded = read_yaml(data / "link-check-ignore.yaml")
    if not isinstance(loaded, dict) or not isinstance(loaded.get("entries"), list):
        raise SystemExit("data/link-check-ignore.yaml must be a mapping with max_share_percent and entries")
    return loaded


def ignore_matches(item: dict, address: str) -> bool:
    """An entry names one address (match: exact) or every address that starts with it (match: prefix)."""
    if item.get("match") == "exact":
        return address == item["url"]
    return address.startswith(item["url"])


def published_addresses(records: list[dict], compact: dict) -> list[str]:
    """Every address the catalog publishes, once each: shown resources, then the compact set with its pins."""
    by_id = {r["id"]: r for r in records}
    out = [r["url"] for r in records if is_active(r) and isinstance(r.get("url"), str)]
    for _, _, links in compact_lists(compact):
        out += [compact_address(link, by_id) for link in links if link.get("id") in by_id]
    return list(dict.fromkeys(out))


def is_active(rec: dict) -> bool:
    """Active records are rendered on the domain pages. Retired and unverified ones are kept in the data only."""
    return rec.get("status", "active") == "active"


def compact_lists(compact: dict):
    """Yield (folder title, subsection title or None, links) for every list in the compact set."""
    for folder in compact["folders"]:
        if folder.get("links"):
            yield folder["title"], None, folder["links"]
        for sub in folder.get("sections") or []:
            yield folder["title"], sub["title"], sub["links"]


def compact_address(link: dict, by_id: dict) -> str:
    """A compact link uses its pinned address if it has one, otherwise the resource's current address."""
    return link.get("url") or by_id[link["id"]]["url"]


def slug(heading: str) -> str:
    """The anchor GitHub gives a Markdown heading."""
    text = heading.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def normalize_url(url: str) -> str:
    """Form used to spot the same address written two ways."""
    m = re.match(r"^(https?)://([^/]+)(.*)$", url)
    if not m:
        return url
    scheme, host, rest = m.groups()
    if rest in ("", "/"):
        rest = ""
    return f"https://{host.lower()}{rest.rstrip('/') if '?' not in rest and '#' not in rest else rest}"


def word_count(text: str) -> int:
    return len(text.split())
