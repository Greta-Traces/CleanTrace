"""Writes CleanTrace results to disk in txt, csv, json, markdown, or report format."""

import csv
import json
from pathlib import Path

_EXTENSIONS = {"txt": "txt", "csv": "csv", "json": "json", "markdown": "md", "report": "md"}


def write_results(
    results_dir: Path,
    username: str,
    timestamp: str,
    sherlock_count: int | None,
    maigret_count: int | None,
    unique_urls: list[str],
    verified_urls: list[str],
    details: dict[str, dict],
    enabled: dict[str, bool],
    output_format: str,
) -> Path:
    ext = _EXTENSIONS[output_format]
    output_path = results_dir / f"{username}_{timestamp}.{ext}"

    if output_format in ("txt", "markdown"):
        _write_structured(
            output_path,
            username,
            timestamp,
            sherlock_count,
            maigret_count,
            unique_urls,
            verified_urls,
            details,
            enabled,
        )
    elif output_format == "csv":
        _write_csv(output_path, unique_urls, verified_urls, details)
    elif output_format == "json":
        _write_json(
            output_path,
            username,
            timestamp,
            sherlock_count,
            maigret_count,
            unique_urls,
            verified_urls,
            details,
            enabled,
        )
    elif output_format == "report":
        _write_report(
            output_path, username, sherlock_count, maigret_count, unique_urls, verified_urls
        )

    return output_path


def _sources(sherlock_count: int | None, maigret_count: int | None) -> list[str]:
    sources = []
    if sherlock_count is not None:
        sources.append("sherlock")
    if maigret_count is not None:
        sources.append("maigret")
    return sources


def _write_structured(
    path: Path,
    username: str,
    timestamp: str,
    sherlock_count: int | None,
    maigret_count: int | None,
    unique_urls: list[str],
    verified_urls: list[str],
    details: dict[str, dict],
    enabled: dict[str, bool],
) -> None:
    sherlock_text = str(sherlock_count) if sherlock_count is not None else "skipped"
    maigret_text = str(maigret_count) if maigret_count is not None else "skipped"

    lines = [
        f"--- CleanTrace report: {username} | {timestamp} ---",
        f"Sherlock: {sherlock_text} | Maigret: {maigret_text} | "
        f"Dedup: {len(unique_urls)} | Verified: {len(verified_urls)}",
        "",
        "[VERIFIED PROFILES]",
        "",
    ]

    exif_total = 0
    no_exif_total = 0

    for url in verified_urls:
        info = details.get(url, {})
        lines.append(f"URL: {url}")

        if enabled.get("fetch"):
            lines.append(f"Title: {info.get('title') or '(not found)'}")
            lines.append(f"Description: {info.get('description') or '(not found)'}")

        if enabled.get("wayback"):
            wayback_info = info.get("wayback")
            if wayback_info:
                lines.append(
                    f"Wayback oldest: {wayback_info['oldest']} | "
                    f"newest: {wayback_info['newest']} | snapshots: {wayback_info['count']}"
                )
            else:
                lines.append("Wayback: not found")

        if enabled.get("exif"):
            for image in info.get("images", []):
                if image["status"] == "exif":
                    exif_total += 1
                    lines.append(f"  [EXIF] {image['url']}")
                    meta = [
                        f"{label}: {image[key]}"
                        for label, key in (("GPS", "gps"), ("Device", "device"), ("Date", "date"))
                        if image.get(key)
                    ]
                    if meta:
                        lines.append(f"         {' | '.join(meta)}")
                    lines.append(f"         → Saved as {image['saved_path']}")
                elif image["status"] == "no_exif":
                    no_exif_total += 1
                    lines.append(f"  [NO EXIF] {image['url']}")
                    lines.append("            → Not saved, but may be worth manual review")

        lines.append("")

    if enabled.get("exif"):
        lines += [
            "---",
            "",
            "[IMAGE SUMMARY]",
            f"Images with EXIF saved: {exif_total}",
            f"Images without EXIF (logged, not saved): {no_exif_total}",
        ]

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_csv(
    path: Path, unique_urls: list[str], verified_urls: list[str], details: dict[str, dict]
) -> None:
    verified_set = set(verified_urls)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "url",
                "verified",
                "title",
                "description",
                "wayback_oldest",
                "wayback_newest",
                "wayback_snapshots",
                "images_with_exif",
                "images_without_exif",
            ]
        )
        for url in unique_urls:
            info = details.get(url, {})
            wayback_info = info.get("wayback") or {}
            images = info.get("images", [])
            writer.writerow(
                [
                    url,
                    url in verified_set,
                    info.get("title") or "",
                    info.get("description") or "",
                    wayback_info.get("oldest", ""),
                    wayback_info.get("newest", ""),
                    wayback_info.get("count", ""),
                    sum(1 for image in images if image["status"] == "exif"),
                    sum(1 for image in images if image["status"] == "no_exif"),
                ]
            )


def _write_json(
    path: Path,
    username: str,
    timestamp: str,
    sherlock_count: int | None,
    maigret_count: int | None,
    unique_urls: list[str],
    verified_urls: list[str],
    details: dict[str, dict],
    enabled: dict[str, bool],
) -> None:
    verified_set = set(verified_urls)
    exif_total = 0
    no_exif_total = 0
    results = []

    for url in unique_urls:
        info = details.get(url, {})
        images = info.get("images", [])
        exif_total += sum(1 for image in images if image["status"] == "exif")
        no_exif_total += sum(1 for image in images if image["status"] == "no_exif")
        results.append(
            {
                "url": url,
                "verified": url in verified_set,
                "title": info.get("title"),
                "description": info.get("description"),
                "wayback": info.get("wayback"),
                "images": images,
            }
        )

    data = {
        "username": username,
        "generated_at": timestamp,
        "sherlock_count": sherlock_count,
        "maigret_count": maigret_count,
        "total_found": len(unique_urls),
        "total_verified": len(verified_urls),
        "modules": enabled,
        "results": results,
        "image_summary": {"with_exif": exif_total, "without_exif": no_exif_total},
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _write_report(
    path: Path,
    username: str,
    sherlock_count: int | None,
    maigret_count: int | None,
    unique_urls: list[str],
    verified_urls: list[str],
) -> None:
    sources = _sources(sherlock_count, maigret_count)
    verified_set = set(verified_urls)
    lines = [
        f"# CleanTrace report: {username}",
        "",
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
