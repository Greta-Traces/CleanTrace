"""CLI entrypoint for CleanTrace."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from cleantrace import delay as _delay
from cleantrace import exif_trace, fetcher, output, parser, runner, verifier, wayback


def parse_args() -> argparse.Namespace:
    arg_parser = argparse.ArgumentParser(
        prog="cleantrace",
        description=(
            "CleanTrace — OSINT username tool.\n"
            "Runs Sherlock + Maigret, deduplicates results, verifies each URL live,\n"
            "and optionally enriches profiles with page metadata, Wayback history,\n"
            "and image EXIF data."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    arg_parser.add_argument(
        "username",
        help="The username to investigate.",
    )

    # ── Network options ────────────────────────────────────────────────
    net = arg_parser.add_argument_group("network options")
    net.add_argument(
        "--timeout",
        type=int,
        default=10,
        metavar="INT",
        help=(
            "Seconds to wait for each HTTP response before giving up (default: 10). "
            "Timed-out URLs are logged as [TIMEOUT] and skipped."
        ),
    )
    net.add_argument(
        "--delay",
        type=float,
        default=1.0,
        metavar="FLOAT",
        help=(
            "Pause in seconds between outbound HTTP requests (default: 1.0). "
            "Slows down the scanner to reduce the chance of rate-limiting or IP bans."
        ),
    )
    net.add_argument(
        "--delay-random",
        action="store_true",
        help=(
            "Randomise the delay between 0.5× and 1.5× the --delay value. "
            "Breaks up predictable request timing, which helps avoid bot-detection."
        ),
    )

    # ── Source options ─────────────────────────────────────────────────
    src = arg_parser.add_argument_group("source options")
    src.add_argument(
        "--skip-sherlock",
        action="store_true",
        help="Skip the Sherlock step (useful if Sherlock is not installed).",
    )
    src.add_argument(
        "--skip-maigret",
        action="store_true",
        help="Skip the Maigret step (useful if Maigret is not installed).",
    )

    # ── Enrichment options ─────────────────────────────────────────────
    enrich = arg_parser.add_argument_group("enrichment options (applied to verified URLs only)")
    enrich.add_argument(
        "--fetch",
        action="store_true",
        help=(
            "FetchTrace: load each verified page and extract its <title> and meta description tag."
        ),
    )
    enrich.add_argument(
        "--wayback",
        action="store_true",
        help=(
            "WaybackTrace: query the Wayback Machine CDX API to find the oldest and "
            "newest archived snapshots and total snapshot count for each URL."
        ),
    )
    enrich.add_argument(
        "--exif",
        action="store_true",
        help=(
            "EXIFTrace: download every <img> on each page, extract embedded EXIF "
            "metadata (GPS coordinates, camera device, capture date), and save images "
            "that contain EXIF to the output directory."
        ),
    )

    # ── Output options ─────────────────────────────────────────────────
    out = arg_parser.add_argument_group("output options")
    out.add_argument(
        "--format",
        choices=["txt", "csv", "json", "markdown", "report"],
        default="txt",
        help="Output file format (default: txt).",
    )
    out.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results"),
        metavar="DIR",
        help=(
            "Directory where the report (and images, cache) are written "
            "(default: results/). Created automatically if it does not exist."
        ),
    )
    out.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Resume an interrupted run. Progress is saved to "
            "<output-dir>/<username>_cache.json after each URL. "
            "On restart, already-processed URLs are skipped. "
            "The cache is deleted automatically after a successful complete run."
        ),
    )

    return arg_parser.parse_args()


def main() -> None:
    args = parse_args()
    username = args.username
    output_dir: Path = args.output_dir

    if args.skip_sherlock and args.skip_maigret:
        print("[!] You cannot skip both Sherlock and Maigret.", file=sys.stderr)
        sys.exit(1)

    # ── Stage 1 + 2: OSINT collection ──────────────────────────────────
    all_urls: list[str] = []
    sherlock_count: int | None = None
    maigret_count: int | None = None

    stage = 1

    if not args.skip_sherlock:
        print(f"\n[*] Stage {stage} — Sherlock")
        print("    Sherlock is a username-search tool that checks 300+ social networks,")
        print(f"    forums, and platforms for the username '{username}'.")
        print("    It works by pattern-matching the username in known URL templates —")
        print("    some results may be false positives, which we filter out in Stage 4.")
        try:
            sherlock_output = runner.run_sherlock(username, args.timeout)
            sherlock_urls = parser.parse_sherlock_output(sherlock_output)
            print(f"    → {len(sherlock_urls)} candidate URLs found by Sherlock.")
            all_urls.extend(sherlock_urls)
            sherlock_count = len(sherlock_urls)
        except (runner.ToolNotFoundError, runner.ToolRunError) as exc:
            runner.print_tool_error("Sherlock", exc)
            sys.exit(1)
        stage += 1

    if not args.skip_maigret:
        print(f"\n[*] Stage {stage} — Maigret")
        print("    Maigret is an OSINT tool similar to Sherlock but with broader platform")
        print("    coverage and richer output (site categories, HTTP status per site).")
        print("    It complements Sherlock by finding accounts Sherlock may have missed.")
        try:
            maigret_output = runner.run_maigret(username, args.timeout)
            maigret_urls = parser.parse_maigret_output(maigret_output)
            print(f"    → {len(maigret_urls)} candidate URLs found by Maigret.")
            all_urls.extend(maigret_urls)
            maigret_count = len(maigret_urls)
        except (runner.ToolNotFoundError, runner.ToolRunError) as exc:
            runner.print_tool_error("Maigret", exc)
            sys.exit(1)
        stage += 1

    # ── Stage 3: Deduplication ─────────────────────────────────────────
    unique_urls = sorted(parser.deduplicate(all_urls), key=str.lower)
    print(f"\n[*] Stage {stage} — Deduplication")
    print("    Both tools' results are merged and sorted. URLs that appear in both")
    print("    Sherlock and Maigret are deduplicated, and trailing slashes are normalised.")
    print(f"    → {len(unique_urls)} unique URLs remain after deduplication.")
    stage += 1

    # ── Resume cache setup ─────────────────────────────────────────────
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_path = output_dir / f"{username}_cache.json"
    cache: dict = {}

    if args.resume and cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
            print(f"\n[*] Resuming from cache: {len(cache)}/{len(unique_urls)} already done.")
        except (json.JSONDecodeError, OSError):
            print("[!] Cache file is unreadable — starting fresh.", file=sys.stderr)
            cache = {}

    # ── Stage 4: Per-URL verification + enrichment ─────────────────────
    enabled = {"fetch": args.fetch, "wayback": args.wayback, "exif": args.exif}
    active = [k for k, v in enabled.items() if v]
    images_dir = output_dir / f"{username}_images"

    print(f"\n[*] Stage {stage} — Verification{' + ' + ', '.join(active) if active else ''}")
    print("    Every URL is now contacted live with a real HTTP request.")
    print("    URLs that return anything other than HTTP 200 are dropped as false positives.")
    if active:
        descriptions = {
            "fetch": "FetchTrace retrieves the page title and meta description.",
            "wayback": "WaybackTrace queries the Wayback Machine for archived snapshots.",
            "exif": "EXIFTrace downloads images and reads their embedded EXIF metadata.",
        }
        for key in active:
            print(f"    {descriptions[key]}")
    if args.delay:
        jitter = " (randomised ±50%)" if args.delay_random else ""
        print(
            f"    Delay: {args.delay}s{jitter} between requests — timeout: {args.timeout}s per request."
        )
    stage += 1

    wayback_reachable = True
    if enabled["wayback"]:
        wayback_reachable = wayback.is_reachable(args.timeout)
        if not wayback_reachable:
            print(
                "\n[!] Could not reach archive.org — WaybackTrace skipped for all URLs.",
                file=sys.stderr,
            )

    verified_urls: list[str] = []
    details: dict[str, dict] = {}
    width = len(str(len(unique_urls)))

    for i, url in enumerate(unique_urls, 1):
        prefix = f"  [{i:>{width}}/{len(unique_urls)}]"

        # Fast path: URL was already processed in a previous (interrupted) run.
        if url in cache:
            entry = cache[url]
            label = "[cache]" if entry["verified"] else "[cache-skip]"
            print(f"{prefix} {label} {url}")
            if entry["verified"]:
                verified_urls.append(url)
                details[url] = entry["info"]
            continue

        print(f"\n{prefix} {url}")

        # Verification: pause first, then send HEAD (or GET fallback).
        _delay.apply(args.delay, args.delay_random)
        is_live = verifier.verify_url(url, args.timeout)
        print(f"         Verify  : {'[OK] live' if is_live else '[--] not found — skipped'}")

        info: dict = {}
        if is_live:
            verified_urls.append(url)
            html: str | None = None

            if enabled["fetch"] or enabled["exif"]:
                _delay.apply(args.delay, args.delay_random)
                title, description, html = fetcher.fetch_page(url, args.timeout)
                info["title"] = title
                info["description"] = description
                title_display = f'"{title}"' if title else "(no title)"
                print(f"         Fetch   : {title_display}")

            if enabled["wayback"] and wayback_reachable:
                _delay.apply(args.delay, args.delay_random)
                wb = wayback.get_snapshots(url, args.timeout)
                info["wayback"] = wb
                if wb:
                    print(
                        f"         Wayback : {wb['count']} snapshots "
                        f"({wb['oldest']} → {wb['newest']})"
                    )
                else:
                    print("         Wayback : no snapshots found")

            if enabled["exif"] and html:
                _delay.apply(args.delay, args.delay_random)
                info["images"] = exif_trace.process_page_images(
                    url, html, images_dir, args.timeout, args.delay, args.delay_random
                )
                exif_count = sum(1 for img in info["images"] if img["status"] == "exif")
                no_exif_count = sum(1 for img in info["images"] if img["status"] == "no_exif")
                print(f"         EXIF    : {exif_count} with EXIF saved, {no_exif_count} without")

        details[url] = info

        # Persist progress so an interrupted run can be resumed.
        if args.resume:
            cache[url] = {"verified": is_live, "info": info}
            try:
                cache_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")
            except OSError as exc:
                print(f"[!] Could not write cache: {exc}", file=sys.stderr)

    # ── Stage 5: Write output ──────────────────────────────────────────
    print(f"\n[*] Stage {stage} — Writing results")
    print(f"    Saving report in '{args.format}' format to: {output_dir}/")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output.write_results(
        output_dir,
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
        print(f"    {url}")

    print(f"\n[+] Results saved to: {output_path}")

    # Clean up cache after a complete successful run.
    if args.resume and cache_path.exists():
        try:
            cache_path.unlink()
            print("[+] Cache removed — run completed successfully.")
        except OSError:
            pass


if __name__ == "__main__":
    main()
