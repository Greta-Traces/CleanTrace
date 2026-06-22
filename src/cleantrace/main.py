"""CLI entrypoint for CleanTrace."""

import argparse
import sys
from pathlib import Path

from cleantrace import output, parser, runner, verifier

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
        help="Timeout in seconds per HTTP verification (default: 10).",
    )
    arg_parser.add_argument(
        "--skip-sherlock", action="store_true", help="Skip Sherlock."
    )
    arg_parser.add_argument(
        "--skip-maigret", action="store_true", help="Skip Maigret."
    )
    arg_parser.add_argument(
        "--format",
        choices=["txt", "csv", "json", "report"],
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
    sources = []

    if not args.skip_sherlock:
        print(f"[*] Running Sherlock for '{username}'...")
        try:
            sherlock_output = runner.run_sherlock(username, args.timeout)
            sherlock_urls = parser.parse_sherlock_output(sherlock_output)
            print(f"[+] Sherlock found {len(sherlock_urls)} results.")
            all_urls.extend(sherlock_urls)
            sources.append("sherlock")
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
            sources.append("maigret")
        except (runner.ToolNotFoundError, runner.ToolRunError) as exc:
            runner.print_tool_error("Maigret", exc)
            sys.exit(1)

    unique_urls = sorted(parser.deduplicate(all_urls), key=str.lower)
    print(f"[*] {len(unique_urls)} unique URLs after deduplication. Starting verification...")

    verified_urls = verifier.verify_urls(unique_urls, args.timeout)

    RESULTS_DIR.mkdir(exist_ok=True)
    output_path = output.write_results(
        RESULTS_DIR,
        username,
        sources,
        unique_urls,
        verified_urls,
        args.format,
    )

    header = (
        f"--- TraceClean results for: {username} ---\n"
        f"Found by: {' + '.join(sources)} | Verified: {len(verified_urls)} / {len(unique_urls)}\n"
    )
    print()
    print(header.strip())
    for url in verified_urls:
        print(url)

    print(f"\n[+] Results saved to {output_path}")


if __name__ == "__main__":
    main()
