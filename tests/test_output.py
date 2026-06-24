import csv
import json
from pathlib import Path

from cleantrace import output

USERNAME = "someone"
TIMESTAMP = "20260101_120000"
UNIQUE_URLS = ["https://github.com/someone", "https://reddit.com/user/someone"]
VERIFIED_URLS = ["https://reddit.com/user/someone"]
NO_DETAILS: dict[str, dict] = {}
NO_MODULES = {"fetch": False, "wayback": False, "exif": False}


def test_write_txt(tmp_path: Path) -> None:
    path = output.write_results(
        tmp_path,
        USERNAME,
        TIMESTAMP,
        2,
        3,
        UNIQUE_URLS,
        VERIFIED_URLS,
        NO_DETAILS,
        NO_MODULES,
        "txt",
    )

    assert path == tmp_path / f"someone_{TIMESTAMP}.txt"
    content = path.read_text()
    assert "Sherlock: 2 | Maigret: 3 | Dedup: 2 | Verified: 1" in content
    assert "URL: https://reddit.com/user/someone" in content
    assert "URL: https://github.com/someone" not in content


def test_write_txt_skipped_source(tmp_path: Path) -> None:
    path = output.write_results(
        tmp_path,
        USERNAME,
        TIMESTAMP,
        None,
        3,
        UNIQUE_URLS,
        VERIFIED_URLS,
        NO_DETAILS,
        NO_MODULES,
        "txt",
    )

    assert "Sherlock: skipped | Maigret: 3" in path.read_text()


def test_write_txt_with_fetch_wayback_exif(tmp_path: Path) -> None:
    details = {
        "https://reddit.com/user/someone": {
            "title": "u/someone",
            "description": "Reddit profile",
            "wayback": {"oldest": "2019-03-12", "newest": "2024-11-01", "count": 47},
            "images": [
                {
                    "url": "https://reddit.com/avatar.jpg",
                    "status": "exif",
                    "gps": "52.3000N 4.9000E",
                    "device": "iPhone 12",
                    "date": "2023-07-14",
                    "saved_path": "results/someone_images/reddit_avatar.jpg",
                },
                {"url": "https://reddit.com/banner.jpg", "status": "no_exif"},
            ],
        }
    }
    enabled = {"fetch": True, "wayback": True, "exif": True}

    path = output.write_results(
        tmp_path, USERNAME, TIMESTAMP, 2, 3, UNIQUE_URLS, VERIFIED_URLS, details, enabled, "txt"
    )
    content = path.read_text()

    assert "Title: u/someone" in content
    assert "Description: Reddit profile" in content
    assert "Wayback oldest: 2019-03-12 | newest: 2024-11-01 | snapshots: 47" in content
    assert "[EXIF] https://reddit.com/avatar.jpg" in content
    assert "GPS: 52.3000N 4.9000E | Device: iPhone 12 | Date: 2023-07-14" in content
    assert "→ Saved as results/someone_images/reddit_avatar.jpg" in content
    assert "[NO EXIF] https://reddit.com/banner.jpg" in content
    assert "[IMAGE SUMMARY]" in content
    assert "Images with EXIF saved: 1" in content
    assert "Images without EXIF (logged, not saved): 1" in content


def test_write_markdown_same_content_as_txt(tmp_path: Path) -> None:
    path = output.write_results(
        tmp_path,
        USERNAME,
        TIMESTAMP,
        2,
        3,
        UNIQUE_URLS,
        VERIFIED_URLS,
        NO_DETAILS,
        NO_MODULES,
        "markdown",
    )

    assert path == tmp_path / f"someone_{TIMESTAMP}.md"
    assert "Sherlock: 2 | Maigret: 3" in path.read_text()


def test_write_csv(tmp_path: Path) -> None:
    path = output.write_results(
        tmp_path,
        USERNAME,
        TIMESTAMP,
        2,
        3,
        UNIQUE_URLS,
        VERIFIED_URLS,
        NO_DETAILS,
        NO_MODULES,
        "csv",
    )

    assert path == tmp_path / f"someone_{TIMESTAMP}.csv"
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))

    assert rows[0]["url"] == "https://github.com/someone"
    assert rows[0]["verified"] == "False"
    assert rows[1]["url"] == "https://reddit.com/user/someone"
    assert rows[1]["verified"] == "True"


def test_write_json(tmp_path: Path) -> None:
    path = output.write_results(
        tmp_path,
        USERNAME,
        TIMESTAMP,
        2,
        3,
        UNIQUE_URLS,
        VERIFIED_URLS,
        NO_DETAILS,
        NO_MODULES,
        "json",
    )

    assert path == tmp_path / f"someone_{TIMESTAMP}.json"
    data = json.loads(path.read_text())
    assert data["username"] == USERNAME
    assert data["sherlock_count"] == 2
    assert data["maigret_count"] == 3
    assert data["total_found"] == 2
    assert data["total_verified"] == 1
    results_by_url = {r["url"]: r["verified"] for r in data["results"]}
    assert results_by_url["https://reddit.com/user/someone"] is True
    assert results_by_url["https://github.com/someone"] is False
    assert data["image_summary"] == {"with_exif": 0, "without_exif": 0}


def test_write_report(tmp_path: Path) -> None:
    path = output.write_results(
        tmp_path,
        USERNAME,
        TIMESTAMP,
        2,
        3,
        UNIQUE_URLS,
        VERIFIED_URLS,
        NO_DETAILS,
        NO_MODULES,
        "report",
    )

    assert path == tmp_path / f"someone_{TIMESTAMP}.md"
    content = path.read_text()
    assert "## Verified results" in content
    assert "- https://reddit.com/user/someone" in content
    assert "## Unverified / false positives" in content
    assert "- https://github.com/someone" in content
