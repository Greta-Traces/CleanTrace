"""Writes CleanTrace results to disk in txt, csv, json, or report format."""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

_EXTENSIONS = {"txt": "txt", "csv": "csv", "json": "json", "report": "md"}


def write_results(
    results_dir: Path,
    username: str,
    sources: list[str],
    unique_urls: list[str],
    verified_urls: list[str],
    output_format: str,
) -> Path:
    ext = _EXTENSIONS[output_format]
    output_path = results_dir / f"{username}_clean.{ext}"

    if output_format == "txt":
        _write_txt(output_path, username, sources, unique_urls, verified_urls)
    elif output_format == "csv":
        _write_csv(output_path, unique_urls, verified_urls)
    elif output_format == "json":
        _write_json(output_path, username, sources, unique_urls, verified_urls)
    elif output_format == "report":
        _write_report(output_path, username, sources, unique_urls, verified_urls)

    return output_path


def _write_txt(
    path: Path,
    username: str,
    sources: list[str],
    unique_urls: list[str],
    verified_urls: list[str],
) -> None:
    header = (
        f"--- TraceClean results for: {username} ---\n"
        f"Found by: {' + '.join(sources)} | Verified: {len(verified_urls)} / {len(unique_urls)}\n"
    )
    with path.open("w", encoding="utf-8") as f:
        f.write(header)
        for url in verified_urls:
            f.write(url + "\n")


def _write_csv(path: Path, unique_urls: list[str], verified_urls: list[str]) -> None:
    verified_set = set(verified_urls)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["url", "verified"])
        for url in unique_urls:
            writer.writerow([url, url in verified_set])


def _write_json(
    path: Path,
    username: str,
    sources: list[str],
    unique_urls: list[str],
    verified_urls: list[str],
) -> None:
    verified_set = set(verified_urls)
    data = {
        "username": username,
        "sources": sources,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_found": len(unique_urls),
        "total_verified": len(verified_urls),
        "results": [
            {"url": url, "verified": url in verified_set} for url in unique_urls
        ],
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _write_report(
    path: Path,
    username: str,
    sources: list[str],
    unique_urls: list[str],
    verified_urls: list[str],
) -> None:
    verified_set = set(verified_urls)
    lines = [
        f"# CleanTrace report: {username}",
        "",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        f"- Sources: {' + '.join(sources)}",
        f"- Found: {len(unique_urls)} | Verified: {len(verified_urls)}",
        "",
        "## Verified results",
        "",
    ]
    for url in verified_urls:
        lines.append(f"- {url}")

    unverified = [url for url in unique_urls if url not in verified_set]
    if unverified:
        lines += ["", "## Unverified / false positives", ""]
        for url in unverified:
            lines.append(f"- {url}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
