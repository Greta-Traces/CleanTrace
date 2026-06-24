"""Queries the Wayback Machine CDX API for the snapshot history of a URL.

API reference: https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
"""

from datetime import datetime

import requests

CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"


def get_snapshots(url: str, timeout: int) -> dict | None:
    """Returns {'oldest': date, 'newest': date, 'count': int}, or None if no snapshots exist
    or the request failed."""
    params = {"url": url, "output": "json", "fl": "timestamp"}
    try:
        response = requests.get(CDX_ENDPOINT, params=params, timeout=timeout)
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
