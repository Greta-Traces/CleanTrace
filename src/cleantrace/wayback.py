"""Queries the Wayback Machine CDX API for the snapshot history of a URL.

API reference: https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
"""

from datetime import datetime

import requests

from cleantrace.verifier import USER_AGENT

CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"


def is_reachable(timeout: int) -> bool:
    """Quick check whether the Wayback Machine can be reached at all.

    Any HTTP response (even an error status) means the network path works; only a
    connection failure or timeout means it's unreachable.
    """
    try:
        requests.get(CDX_ENDPOINT, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        return True
    except requests.RequestException:
        return False


def get_snapshots(url: str, timeout: int) -> dict | None:
    """Returns {'oldest': date, 'newest': date, 'count': int}, or None if no snapshots exist
    or the request failed."""
    params = {"url": url, "output": "json", "fl": "timestamp"}
    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.get(CDX_ENDPOINT, params=params, headers=headers, timeout=timeout)
        if response.status_code != 200:
            return None
        rows = response.json()
    except (requests.RequestException, ValueError):
        return None

    # The first row is the field header (["timestamp"]); no further rows means no snapshots.
    if len(rows) <= 1:
        return None

    timestamps = [row[0] for row in rows[1:]]
    return {
        "oldest": _format_timestamp(timestamps[0]),
        "newest": _format_timestamp(timestamps[-1]),
        "count": len(timestamps),
    }


def _format_timestamp(timestamp: str) -> str:
    """Wayback timestamps are 14-digit YYYYMMDDHHMMSS strings."""
    try:
        return datetime.strptime(timestamp[:8], "%Y%m%d").date().isoformat()
    except ValueError:
        return timestamp
