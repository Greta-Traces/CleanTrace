"""Verifies URLs with a live HTTP request to filter out false positives."""

import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def verify_url(url: str, timeout: int) -> bool:
    """Returns True if the URL responds with HTTP 200.

    Tries HEAD first (faster); falls back to GET for sites that block HEAD
    with 405 or 403.  A [TIMEOUT] message is printed and False returned if
    the request exceeds `timeout` seconds.
    """
    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
        if response.status_code == 200:
            return True
        if response.status_code in (405, 403):
            response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            return response.status_code == 200
        return False
    except requests.Timeout:
        print(f"  [TIMEOUT] {url} → skipped after {timeout}s")
        return False
    except requests.RequestException:
        return False


def verify_urls(urls: list[str], timeout: int) -> list[str]:
    verified = []
    for url in urls:
        if verify_url(url, timeout):
            verified.append(url)
    return verified
