# CleanTrace

CLI tool that combines Sherlock and Maigret to look up a username,
deduplicates the results, and live-verifies every found URL with an
HTTP request to filter out false positives (deleted or empty profile
pages that were incorrectly flagged as found).

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
| `--timeout SECONDS` | Timeout per HTTP verification request (default: 10) |
| `--skip-sherlock` | Skip Sherlock, use Maigret only |
| `--skip-maigret` | Skip Maigret, use Sherlock only |
| `--format {txt,csv,json,report}` | Output format (default: `txt`) |

## Output

Results are written to `results/{username}_clean.{ext}`, where `{ext}` depends
on `--format`:

- `txt` — plain list of verified URLs (original format)
- `csv` — `url,verified` for every found URL, including unverified ones
- `json` — structured result with metadata (sources, counts, timestamp)
- `report` — readable Markdown summary with verified and unverified sections

```
--- TraceClean results for: username ---
Found by: sherlock + maigret | Verified: 12 / 47
https://twitter.com/username
https://reddit.com/user/username
```

## Tests

```bash
uv run pytest
```
