"""Request every address in the catalog and report what answered.

    python scripts/check_links.py                    check every address; exit 1 if any fails
    python scripts/check_links.py --report out.json  also save status, final address and page title per address
    python scripts/check_links.py --self-test        confirm the checker rejects a dead address and honors the ignore list

Addresses checked: every shown resource and every link of the compact set (including pinned addresses).
An address on data/link-check-ignore.yaml is still requested and reported, but it cannot fail the run.
Standard library plus the curl command, which makes the requests.
"""
from __future__ import annotations

import concurrent.futures
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
TITLE_RE = re.compile(rb"<title[^>]*>(.*?)</title>", re.I | re.S)
WRITE_OUT = r"\n%{http_code}\t%{url_effective}"


def request(url: str) -> dict:
    """One address: status (0 when no HTTP answer), the final address after redirects, and the page title.

    curl makes the request: several sites in the catalog refuse the TLS fingerprint of Python's own client.
    """
    if not url.startswith(("https://", "http://")):
        return {"url": url, "status": 0, "final": url, "title": "", "error": "not an http(s) address"}
    cmd = [CURL, "--silent", "--show-error", "--location", "--compressed", "--max-time", str(TIMEOUT),
           "--retry", str(RETRIES), "--max-redirs", "10", "--user-agent", USER_AGENT]
    for name, value in HEADERS.items():
        cmd += ["--header", f"{name}: {value}"]
    cmd += ["--output", "-", "--write-out", WRITE_OUT, url]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT * (RETRIES + 2))
    except subprocess.TimeoutExpired:
        return {"url": url, "status": 0, "final": url, "title": "", "error": "timed out"}
    body, _, tail = proc.stdout.rpartition(b"\n")
    code, _, final = tail.decode("utf-8", "replace").partition("\t")
    status = int(code) if code.isdigit() else 0
    m = TITLE_RE.search(body[:400_000])
    title = re.sub(r"\s+", " ", m.group(1).decode("utf-8", "replace")).strip()[:120] if m else ""
    if 200 <= status < 300:
        error = ""
    elif status:
        error = f"HTTP {status}"
    else:
        error = re.sub(r"\s+", " ", proc.stderr.decode("utf-8", "replace")).strip()[:120] or "no answer"
    return {"url": url, "status": status, "final": final or url, "title": title, "error": error}


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
    for p in problems:
        print("self-test:", p)
    print("self-test:", "failed" if problems else
          "5 planted addresses: the dead one failed, the prefix and exact entries were set aside, "
          "and neither a longer address than an exact entry nor a CI-only entry was excused")
    return 1 if problems else 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    ignore = catalog.load_ignore()["entries"]
    urls = addresses()
    ok, ignored, failed = run(urls, ignore)
    if "--report" in argv:
        path = argv[argv.index("--report") + 1]
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(sorted(ok + ignored + failed, key=lambda r: r["url"]), fh, ensure_ascii=False, indent=1)
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
