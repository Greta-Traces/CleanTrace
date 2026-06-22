"""Parses Sherlock txt output and Maigret JSON output into a deduplicated URL list."""

import json
import re
from pathlib import Path

_URL_PATTERN = re.compile(r"https?://\S+")


def parse_sherlock_output(path: Path) -> list[str]:
    """Sherlock --output writes one line per site, each containing the URL."""
    urls = []
    text = path.read_text(encoding="utf-8", errors="ignore")
    for line in text.splitlines():
        match = _URL_PATTERN.search(line)
        if match:
            urls.append(match.group(0).rstrip(".,)"))
    return urls


def parse_maigret_output(path: Path) -> list[str]:
    """Maigret --json simple writes a list of site-results with 'url_user'."""
    data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))

    urls = []
    items = data.values() if isinstance(data, dict) else data
    for entry in items:
        if not isinstance(entry, dict):
            continue
        status = entry.get("status", {})
        if isinstance(status, dict) and status.get("status") not in ("Claimed", None):
            continue
        url = entry.get("url_user") or entry.get("url")
        if url:
            urls.append(url)
    return urls


def deduplicate(urls: list[str]) -> list[str]:
    seen = set()
    unique = []
    for url in urls:
        normalized = url.strip().rstrip("/")
        if normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)
    return unique
