# CleanTrace

CLI tool that combines Sherlock and Maigret to look up a username,
deduplicates the results, and live-verifies every found URL with an
HTTP request to filter out false positives (deleted or empty profile
pages that were incorrectly flagged as found).

Optionally extends the pipeline with three more modules per verified URL:

- **FetchTrace** (`--fetch`) — fetches the page title + meta description
- **WaybackTrace** (`--wayback`) — checks the Wayback Machine CDX API for
  the oldest and newest snapshot
- **EXIFTrace** (`--exif`) — finds images on the page and extracts EXIF
  metadata. Images with EXIF data are saved to
  `results/{username}_images/`; images without EXIF are discarded
  immediately and only logged for manual review.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- [Sherlock](https://github.com/sherlock-project/sherlock) and
  [Maigret](https://github.com/soxoj/maigret) installed and available in
  your `PATH` (intended for use on Kali Linux)

## Installation

```bash
uv sync
```

## Usage

```bash
uv run cleantrace <username>
```

### Options

| Flag | Description |
|---|---|
| `--timeout SECONDS` | Timeout per HTTP request (default: 10) |
| `--skip-sherlock` | Skip Sherlock, use Maigret only |
| `--skip-maigret` | Skip Maigret, use Sherlock only |
| `--fetch` | Enable FetchTrace (page title + meta description) |
| `--wayback` | Enable WaybackTrace (oldest/newest Wayback snapshot) |
| `--exif` | Enable EXIFTrace (image discovery + EXIF extraction) |
| `--format {txt,csv,json,markdown,report}` | Output format (default: `txt`) |

## Output

Every run writes one structured document to
`results/{username}_{timestamp}.{ext}`, where `{ext}` depends on `--format`:

- `txt` / `markdown` — full structured report: verified profiles with their
  fetched title/description, Wayback snapshot range, and EXIF findings per
  image, followed by an image summary
- `csv` — one row per found URL with `verified`, `title`, `description`,
  Wayback fields, and EXIF image counts
- `json` — structured result with metadata, per-URL details (title,
  description, Wayback info, image list), and an image summary
- `report` — readable Markdown summary with verified/unverified URL lists
  only (no Fetch/Wayback/EXIF data)

```
--- CleanTrace report: username | 20260624_153012 ---
Sherlock: 12 | Maigret: 35 | Dedup: 47 | Verified: 12

[VERIFIED PROFILES]

URL: https://example.com/username
Title: username's profile
Description: ...
Wayback oldest: 2019-03-12 | newest: 2024-11-01 | snapshots: 47

  [EXIF] https://example.com/image.jpg
         GPS: 52.3000N 4.9000E | Device: iPhone 12 | Date: 2023-07-14
         → Saved as results/username_images/example_image.jpg

  [NO EXIF] https://example.com/banner.jpg
            → Not saved, but may be worth manual review

---

[IMAGE SUMMARY]
Images with EXIF saved: 1
Images without EXIF (logged, not saved): 1
```

EXIFTrace images with EXIF data are saved under
`results/{username}_images/`; images without EXIF are deleted immediately
and never written to disk.

## Tests

```bash
uv run pytest
```
