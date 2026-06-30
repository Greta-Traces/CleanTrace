"""Fetches a page and extracts its title + meta description."""

import requests
from bs4 import BeautifulSoup

from cleantrace.verifier import USER_AGENT


def fetch_page(url: str, timeout: int) -> tuple[str | None, str | None, str | None]:
    """Returns (title, description, html).

    Any part is None if it could not be found.  A [TIMEOUT] message is printed
    and (None, None, None) returned if the request exceeds `timeout` seconds.
    """
    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code != 200:
            return None, None, None
    except requests.Timeout:
        print(f"  [TIMEOUT] {url} → skipped after {timeout}s")
        return None, None, None
    except requests.RequestException:
        return None, None, None

    soup = BeautifulSoup(response.text, "lxml")

    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip() or None

    description = None
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        description = meta["content"].strip() or None

    return title, description, response.text
