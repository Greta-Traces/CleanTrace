from unittest.mock import Mock, patch

import requests

from cleantrace import wayback


def test_get_snapshots_found() -> None:
    response = Mock(status_code=200)
    response.json.return_value = [
        ["timestamp"],
        ["20190312000000"],
        ["20210605000000"],
        ["20241101000000"],
    ]
    with patch("cleantrace.wayback.requests.get", return_value=response):
        result = wayback.get_snapshots("https://example.com/someone", 10)

    assert result == {"oldest": "2019-03-12", "newest": "2024-11-01", "count": 3}


def test_get_snapshots_no_results() -> None:
    response = Mock(status_code=200)
    response.json.return_value = [["timestamp"]]
    with patch("cleantrace.wayback.requests.get", return_value=response):
        assert wayback.get_snapshots("https://example.com/someone", 10) is None


def test_get_snapshots_http_error() -> None:
    response = Mock(status_code=503)
    with patch("cleantrace.wayback.requests.get", return_value=response):
        assert wayback.get_snapshots("https://example.com/someone", 10) is None


def test_get_snapshots_request_exception() -> None:
    with patch("cleantrace.wayback.requests.get", side_effect=requests.RequestException):
        assert wayback.get_snapshots("https://example.com/someone", 10) is None
