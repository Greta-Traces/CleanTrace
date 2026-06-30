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
  `{output-dir}/{username}_images/`; images without EXIF are discarded
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
uv run cleantrace <username> [options]
```

### Full example — all flags

```bash
uv run cleantrace janedoe \
  --fetch \
  --wayback \
  --exif \
  --format markdown \
  --delay 1.5 \
  --delay-random \
  --timeout 10 \
  --output-dir ~/results \
  --resume
```

### Options

**Network**

| Flag | Default | Description |
|---|---|---|
| `--timeout INT` | `10` | Seconds to wait per HTTP request before giving up. Timed-out URLs are logged as `[TIMEOUT]` and skipped. |
| `--delay FLOAT` | `1.0` | Pause in seconds between every outbound request. Reduces the chance of rate-limiting or IP bans. |
| `--delay-random` | off | Randomise the delay between 0.5× and 1.5× the `--delay` value. Breaks up predictable request patterns. |

**Sources**

| Flag | Description |
|---|---|
| `--skip-sherlock` | Skip Sherlock, use Maigret only |
| `--skip-maigret` | Skip Maigret, use Sherlock only |

**Enrichment** (applied to verified URLs only)

| Flag | Description |
|---|---|
| `--fetch` | FetchTrace — retrieve each page's `<title>` and meta description |
| `--wayback` | WaybackTrace — look up the oldest/newest Wayback Machine snapshot and snapshot count |
| `--exif` | EXIFTrace — download images and extract embedded EXIF metadata (GPS, device, date) |

**Output**

| Flag | Default | Description |
|---|---|---|
| `--format` | `txt` | Output format: `txt`, `csv`, `json`, `markdown`, `report` |
| `--output-dir DIR` | `results/` | Directory where the report, images, and cache are written. Created automatically if it does not exist. |
| `--resume` | off | Resume an interrupted run. Progress is saved to `{output-dir}/{username}_cache.json` after each URL. Already-processed URLs are skipped on restart. The cache is deleted after a successful complete run. |

## Output

Every run writes one structured document to
`{output-dir}/{username}_{timestamp}.{ext}`, where `{ext}` depends on `--format`:

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
`{output-dir}/{username}_images/`; images without EXIF are deleted
immediately and never written to disk.

## Robustness

- **Rate limiting** — `--delay` and `--delay-random` insert a configurable
  pause between every outbound request so the scanner does not hammer targets
  with rapid-fire requests.
- **Timeout handling** — every request (verify, fetch, Wayback, image
  download) is individually wrapped with a timeout. A slow site prints
  `[TIMEOUT] https://... → skipped after Xs` and the run continues normally.
- **Resume** — `--resume` saves progress after each URL. If the run is
  interrupted (Ctrl+C, network drop, power loss), restart with the same
  command and `--resume` to pick up exactly where it stopped.

## Notes for Kali / VPN users

The Wayback Machine (`archive.org`) blocks some VPN exit nodes. If
WaybackTrace returns no results for any URL, try switching your exit node
before assuming a code bug.
