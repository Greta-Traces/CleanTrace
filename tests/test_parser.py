import json
from pathlib import Path

from cleantrace import parser


def test_parse_sherlock_output(tmp_path: Path) -> None:
    content = (
        "[*] Checking username someone on:\n"
        "[+] Reddit: https://reddit.com/user/someone\n"
        "[+] Twitter: https://twitter.com/someone\n"
        "[-] GitHub: Not Found!\n"
    )
    path = tmp_path / "sherlock.txt"
    path.write_text(content)

    urls = parser.parse_sherlock_output(path)

    assert urls == ["https://reddit.com/user/someone", "https://twitter.com/someone"]


def test_parse_maigret_output(tmp_path: Path) -> None:
    data = {
        "Reddit": {"status": {"status": "Claimed"}, "url_user": "https://reddit.com/user/someone"},
        "Github": {"status": {"status": "Available"}, "url_user": "https://github.com/someone"},
    }
    path = tmp_path / "maigret.json"
    path.write_text(json.dumps(data))

    urls = parser.parse_maigret_output(path)

    assert urls == ["https://reddit.com/user/someone"]


def test_deduplicate() -> None:
    urls = [
        "https://reddit.com/user/someone/",
        "https://reddit.com/user/someone",
        "https://twitter.com/someone",
    ]

    assert parser.deduplicate(urls) == [
        "https://reddit.com/user/someone",
        "https://twitter.com/someone",
    ]
