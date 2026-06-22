import csv
import json
from pathlib import Path

from cleantrace import output

USERNAME = "someone"
SOURCES = ["sherlock", "maigret"]
UNIQUE_URLS = ["https://github.com/someone", "https://reddit.com/user/someone"]
VERIFIED_URLS = ["https://reddit.com/user/someone"]


def test_write_txt(tmp_path: Path) -> None:
    path = output.write_results(tmp_path, USERNAME, SOURCES, UNIQUE_URLS, VERIFIED_URLS, "txt")

    assert path == tmp_path / "someone_clean.txt"
    content = path.read_text()
    assert "Found by: sherlock + maigret" in content
    assert "https://reddit.com/user/someone" in content
    assert "https://github.com/someone" not in content


def test_write_csv(tmp_path: Path) -> None:
    path = output.write_results(tmp_path, USERNAME, SOURCES, UNIQUE_URLS, VERIFIED_URLS, "csv")

    assert path == tmp_path / "someone_clean.csv"
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))

    assert rows[0] == {"url": "https://github.com/someone", "verified": "False"}
    assert rows[1] == {"url": "https://reddit.com/user/someone", "verified": "True"}


def test_write_json(tmp_path: Path) -> None:
    path = output.write_results(tmp_path, USERNAME, SOURCES, UNIQUE_URLS, VERIFIED_URLS, "json")

    assert path == tmp_path / "someone_clean.json"
    data = json.loads(path.read_text())
    assert data["username"] == USERNAME
    assert data["total_found"] == 2
    assert data["total_verified"] == 1
    results_by_url = {r["url"]: r["verified"] for r in data["results"]}
    assert results_by_url["https://reddit.com/user/someone"] is True
    assert results_by_url["https://github.com/someone"] is False


def test_write_report(tmp_path: Path) -> None:
    path = output.write_results(tmp_path, USERNAME, SOURCES, UNIQUE_URLS, VERIFIED_URLS, "report")

    assert path == tmp_path / "someone_clean.md"
    content = path.read_text()
    assert "## Verified results" in content
    assert "- https://reddit.com/user/someone" in content
    assert "## Unverified / false positives" in content
    assert "- https://github.com/someone" in content
