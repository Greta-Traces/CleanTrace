"""CLI entrypoint for CleanTrace."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from cleantrace import exif_trace, fetcher, output, parser, runner, verifier, wayback

RESULTS_DIR = Path("results")


def parse_args() -> argparse.Namespace:
    arg_parser = argparse.ArgumentParser(
        prog="cleantrace",
        description="Combines Sherlock + Maigret results and verifies each URL.",
    )
    arg_parser.add_argument("username", help="The username to look up.")
    arg_parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Timeout in seconds per HTTP request (default: 10).",
    )
    arg_parser.add_argument("--skip-sherlock", action="store_true", help="Skip Sherlock.")
    arg_parser.add_argument("--skip-maigret", action="store_true", help="Skip Maigret.")
    arg_parser.add_argument(
        "--fetch", action="store_true", help="Fetch page title + meta description (FetchTrace)."
    )
    arg_parser.add_argument(
        "--wayback",
        action="store_true",
        help="Check the Wayback Machine for oldest/newest snapshots (WaybackTrace).",
    )
    arg_parser.add_argument(
        "--exif",
        action="store_true",
        help="Find images per page and extract EXIF metadata (EXIFTrace).",
    )
    arg_parser.add_argument(
        "--format",
        choices=["txt", "csv", "json", "markdown", "report"],
        default="txt",
        help="Output format (default: txt).",
    )
    return arg_parser.parse_args()


def main() -> None:
    args = parse_args()
    username = args.username

    if args.skip_sherlock and args.skip_maigret:
        print("[!] You cannot skip both Sherlock and Maigret.", file=sys.stderr)
        sys.exit(1)

    all_urls: list[str] = []
    sherlock_count: int | None = None
    maigret_count: int | None = None

    if not args.skip_sherlock:
        print(f"[*] Running Sherlock for '{username}'...")
        try:
            sherlock_output = runner.run_sherlock(username, args.timeout)
            sherlock_urls = parser.parse_sherlock_output(sherlock_output)
            print(f"[+] Sherlock found {len(sherlock_urls)} results.")
            all_urls.extend(sherlock_urls)
            sherlock_count = len(sherlock_urls)
        except (runner.ToolNotFoundError, runner.ToolRunError) as exc:
            runner.print_tool_error("Sherlock", exc)
            sys.exit(1)

    if not args.skip_maigret:
        print(f"[*] Running Maigret for '{username}'...")
        try:
            maigret_output = runner.run_maigret(username, args.timeout)
            maigret_urls = parser.parse_maigret_output(maigret_output)
            print(f"[+] Maigret found {len(maigret_urls)} results.")
            all_urls.extend(maigret_urls)
            maigret_count = len(maigret_urls)
        except (runner.ToolNotFoundError, runner.ToolRunError) as exc:
            runner.print_tool_error("Maigret", exc)
            sys.exit(1)

    unique_urls = sorted(parser.deduplicate(all_urls), key=str.lower)
    print(f"[*] {len(unique_urls)} unique URLs after deduplication. Starting verification...")

    verified_urls = verifier.verify_urls(unique_urls, args.timeout)

    enabled = {"fetch": args.fetch, "wayback": args.wayback, "exif": args.exif}
    images_dir = RESULTS_DIR / f"{username}_images"
    details = _gather_details(verified_urls, enabled, images_dir, args.timeout)

    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output.write_results(
        RESULTS_DIR,
        username,
        timestamp,
        sherlock_count,
        maigret_count,
        unique_urls,
        verified_urls,
        details,
        enabled,
        args.format,
    )

    print(f"\n[*] Verified: {len(verified_urls)} / {len(unique_urls)}")
    for url in verified_urls:
        print(url)

    print(f"\n[+] Results saved to {output_path}")


def _gather_details(
    verified_urls: list[str], enabled: dict[str, bool], images_dir: Path, timeout: int
) -> dict[str, dict]:
    """Runs FetchTrace, WaybackTrace and EXIFTrace for every verified URL."""
    details: dict[str, dict] = {}

    for url in verified_urls:
        info: dict = {}
        html = None

        if enabled["fetch"] or enabled["exif"]:
            print(f"[*] Fetching {url}...")
            title, description, html = fetcher.fetch_page(url, timeout)
            info["title"] = title
            info["description"] = description

        if enabled["wayback"]:
            print(f"[*] Checking Wayback Machine for {url}...")
            info["wayback"] = wayback.get_snapshots(url, timeout)

        if enabled["exif"] and html:
            print(f"[*] Scanning images on {url}...")
            info["images"] = exif_trace.process_page_images(url, html, images_dir, timeout)

        details[url] = info

    return details


if __name__ == "__main__":
    main()
