"""Runs Sherlock and Maigret as subprocesses and stores their output in temp files."""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


class ToolNotFoundError(Exception):
    pass


class ToolRunError(Exception):
    pass


def _require_binary(binary: str) -> None:
    if shutil.which(binary) is None:
        raise ToolNotFoundError(f"'{binary}' was not found in PATH. Is it installed?")


def run_sherlock(username: str, timeout: int) -> Path:
    """Runs sherlock and returns the path to the txt output file."""
    _require_binary("sherlock")

    output_file = Path(tempfile.gettempdir()) / f"cleantrace_sherlock_{username}.txt"
    cmd = [
        "sherlock",
        username,
        "--output",
        str(output_file),
        "--timeout",
        str(timeout),
        "--no-color",
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=timeout * 60, check=False)
    except subprocess.TimeoutExpired as exc:
        raise ToolRunError(f"Sherlock hit a timeout: {exc}") from exc
    except OSError as exc:
        raise ToolRunError(f"Sherlock could not be started: {exc}") from exc

    if not output_file.exists():
        raise ToolRunError("Sherlock stopped without writing an output file.")

    return output_file


def run_maigret(username: str, timeout: int) -> Path:
    """Runs maigret and returns the path to the JSON output file."""
    _require_binary("maigret")

    output_dir = Path(tempfile.gettempdir()) / f"cleantrace_maigret_{username}"
    output_dir.mkdir(exist_ok=True)
    cmd = [
        "maigret",
        username,
        "--json",
        "simple",
        "--folderoutput",
        str(output_dir),
        "--timeout",
        str(timeout),
        "--no-progressbar",
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=timeout * 60, check=False)
    except subprocess.TimeoutExpired as exc:
        raise ToolRunError(f"Maigret hit a timeout: {exc}") from exc
    except OSError as exc:
        raise ToolRunError(f"Maigret could not be started: {exc}") from exc

    json_files = list(output_dir.glob(f"report_{username}_simple.json"))
    if not json_files:
        raise ToolRunError("Maigret stopped without writing a JSON output file.")

    return json_files[0]


def print_tool_error(tool: str, exc: Exception) -> None:
    print(f"[!] Error while running {tool}: {exc}", file=sys.stderr)
