from unittest.mock import Mock, patch

import requests

from cleantrace import fetcher

HTML = """
<html>
  <head>
    <title>  Someone's Profile  </title>
    <meta name="description" content="A short bio.">
  </head>
</html>
"""


def test_fetch_page_found() -> None:
    response = Mock(status_code=200, text=HTML)
    with patch("cleantrace.fetcher.requests.get", return_value=response):
        title, description, html = fetcher.fetch_page("https://example.com/someone", 10)

    assert title == "Someone's Profile"
    assert description == "A short bio."
    assert html == HTML


def test_fetch_page_no_meta() -> None:
    response = Mock(status_code=200, text="<html><head></head></html>")
    with patch("cleantrace.fetcher.requests.get", return_value=response):
        title, description, _ = fetcher.fetch_page("https://example.com/someone", 10)

    assert title is None
    assert description is None


def test_fetch_page_http_error() -> None:
    response = Mock(status_code=404, text="")
    with patch("cleantrace.fetcher.requests.get", return_value=response):
        assert fetcher.fetch_page("https://example.com/someone", 10) == (None, None, None)


def test_fetch_page_request_exception() -> None:
    with patch("cleantrace.fetcher.requests.get", side_effect=requests.RequestException):
        assert fetcher.fetch_page("https://example.com/someone", 10) == (None, None, None)
