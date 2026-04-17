#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from config import OUTPUT_FOLDER

INPUT_FILE = Path("channel_names-sizes.txt")


def parse_input_line(line: str) -> tuple[str, str] | None:
    """Parse a single line from channel_names-sizes.txt."""
    line = line.strip()
    if not line:
        return None

    parts = line.split(maxsplit=1)
    if len(parts) != 2:
        return None

    size, folder_name = parts[0].strip(), parts[1].strip()
    if not size or not folder_name:
        return None

    return size, folder_name


def print_progress(path: Path, current: int, total: int) -> None:
    percent = (current / total) * 100 if total else 100.0
    sys.stdout.write(f"\rProcessing folders: {current}/{total} ({percent:5.1f}%) {path.name:30s}")
    sys.stdout.flush()


def count_messages(folder: Path) -> int:
    """Count messages using grep and wc, as instructed.

    Writes the result to message-count.txt in the folder for future runs.
    If message-count.txt already exists, reads from it instead of running grep.
    """
    cache_file = folder / "message-count.txt"

    if cache_file.exists():
        try:
            return int(cache_file.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            pass

    index_json = folder / "index.json"
    try:
        grep = subprocess.run(
            ["grep", '"type": "message",', str(index_json)],
            capture_output=True,
            text=True,
            check=False,
        )
        if grep.returncode not in (0, 1):
            return 0

        wc = subprocess.run(
            ["wc", "-l"],
            input=grep.stdout,
            capture_output=True,
            text=True,
            check=False,
        )
        if wc.returncode != 0:
            return 0

        count = int(wc.stdout.strip().split()[0])
    except (OSError, ValueError, IndexError):
        return 0

    try:
        cache_file.write_text(str(count) + "\n", encoding="utf-8")
    except OSError:
        pass

    return count


def count_attachments(folder: Path) -> int:
    """Count attachments as total files minus the index files and message-count.txt, never below zero."""
    try:
        total_files = sum(1 for p in folder.iterdir() if p.is_file())
    except OSError:
        return 0

    return max(0, total_files - 3)


def build_entry(folder_name: str, size: str, message_count: int, attachment_count: int) -> dict:
    """Build one JSON entry."""
    return {
        "folder": folder_name,
        "size": size,
        "message_count": message_count,
        "attachment_count": attachment_count,
    }


def main() -> int:
    if not INPUT_FILE.exists():
        print(f"{INPUT_FILE}: file not found")
        return 1

    output_root = Path(OUTPUT_FOLDER)
    output_root.mkdir(parents=True, exist_ok=True)

    entries: list[tuple[str, str]] = []
    for raw_line in INPUT_FILE.read_text(encoding="utf-8").splitlines():
        parsed = parse_input_line(raw_line)
        if parsed is not None:
            entries.append(parsed)

    if not entries:
        print(f"{INPUT_FILE}: no valid entries found")
        return 0

    rows: list[dict] = []
    total = len(entries)

    for current, (size, folder_name) in enumerate(entries, start=1):
        folder = output_root / folder_name
        print_progress(folder, current, total)
        message_count = count_messages(folder)
        attachment_count = count_attachments(folder)
        rows.append(build_entry(folder_name, size, message_count, attachment_count))
        #if current >= 200:
        #    break

    sys.stdout.write("\n")
    sys.stdout.flush()

    out_path = output_root / "index.json"
    out_path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print(f"Written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())