#!/usr/bin/env python3
"""Detect changes on the official pages cited in countries.json.

Fetches every source URL, reduces it to visible text, and compares a hash with state/source_hashes.json.
Writes state/changes.json ({"changed": {CC: [urls]}, "failed": {url: error}}) and updates the hashes.
Exit code 0 always; the workflow decides what to do with the changes.
"""
import hashlib
import html
import json
import pathlib
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATASET = ROOT / "countries.json"
HASHES = ROOT / "state" / "source_hashes.json"
CHANGES = ROOT / "state" / "changes.json"
UA = "Mozilla/5.0 (compatible; PetRulesSourceWatch/1.0; +https://elysiumjet.com)"

# Volatile bits that change without the rules changing.
NOISE = [
    r"\b\d{1,2}:\d{2}(:\d{2})?\b",                       # times
    r"\b(19|20)\d{2}-\d{2}-\d{2}(t[\d:.+z-]+)?\b",       # ISO dates / timestamps
    r"(last (updated|modified|reviewed)|page updated|dernière mise à jour)[^.]{0,60}",
    r"\b(csrf|token|nonce|session)[^\s]{0,80}",
]


def visible_text(raw):
    raw = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|header)[^>]*>.*?</\1>", " ", raw)
    text = html.unescape(re.sub(r"(?s)<[^>]+>", " ", raw)).lower()
    for pattern in NOISE:
        text = re.sub(pattern, " ", text)
    return re.sub(r"\s+", " ", text).strip()


def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
        with urllib.request.urlopen(req, timeout=30) as res:
            body = res.read(3_000_000).decode(res.headers.get_content_charset() or "utf-8", "replace")
        return url, hashlib.sha256(visible_text(body).encode()).hexdigest(), None
    except Exception as exc:  # network errors are reported, not fatal
        return url, None, str(exc)[:200]


def main():
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    by_url = {}
    for entry in data["countries"]:
        for url in entry.get("sources") or []:
            if url.lower().endswith(".pdf"):
                continue  # PDFs are checked by the weekly research run instead
            by_url.setdefault(url, set()).add(entry["cc"])

    old = json.loads(HASHES.read_text(encoding="utf-8")) if HASHES.exists() else {}
    new, changed, failed = {}, {}, {}
    with ThreadPoolExecutor(max_workers=12) as pool:
        for url, digest, error in pool.map(fetch, sorted(by_url)):
            if error:
                failed[url] = error
                if url in old:
                    new[url] = old[url]
                continue
            new[url] = digest
            if url in old and old[url] != digest:
                for cc in by_url[url]:
                    changed.setdefault(cc, []).append(url)

    HASHES.write_text(json.dumps(new, indent=1, sort_keys=True), encoding="utf-8")
    CHANGES.write_text(json.dumps({"changed": changed, "failed": failed}, indent=1, sort_keys=True), encoding="utf-8")
    print(f"{len(by_url)} sources checked, {len(changed)} countries with changed pages, {len(failed)} fetch failures")
    for cc in sorted(changed):
        print(f"  {cc}: {', '.join(changed[cc])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
