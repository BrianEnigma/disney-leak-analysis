#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path

from config import OUTPUT_FOLDER
from htmlgen import generate_all_pages

CHECKPOINT_FILE = Path(".htmlgenall_progress")


def load_checkpoint() -> set[str]:
    """Return the set of folder paths already successfully processed."""
    try:
        text = CHECKPOINT_FILE.read_text(encoding="utf-8")
    except OSError:
        return set()
    return {line for line in text.splitlines() if line.strip()}


def save_checkpoint(folder: Path, done: set[str]) -> None:
    """Append a completed folder to the checkpoint file and the in-memory set."""
    done.add(str(folder))
    with CHECKPOINT_FILE.open("a", encoding="utf-8") as f:
        f.write(str(folder) + "\n")


def clear_checkpoint() -> None:
    try:
        CHECKPOINT_FILE.unlink()
    except FileNotFoundError:
        pass


def main() -> int:
    output_root = Path(OUTPUT_FOLDER)

    if not output_root.exists():
        print(f"{output_root}: output folder does not exist", file=sys.stderr)
        return 1

    folders = sorted(p for p in output_root.iterdir() if p.is_dir())

    if not folders:
        print("No folders found in output directory.", file=sys.stderr)
        return 0

    done = load_checkpoint()
    pending = [f for f in folders if str(f) not in done]
    total = len(folders)
    already_done = total - len(pending)

    failures: list[str] = []

    try:
        for i, folder in enumerate(pending, start=already_done + 1):
            index_json = folder / "index.json"
            print(f"[{i}/{total}] {folder.name}", file=sys.stderr)

            if not index_json.exists():
                msg = f"  skipped: no index.json in {folder}"
                print(msg, file=sys.stderr)
                failures.append(msg)
                save_checkpoint(folder, done)
                continue

            try:
                with index_json.open("r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                msg = f"  error reading {index_json}: {exc}"
                print(msg, file=sys.stderr)
                failures.append(msg)
                save_checkpoint(folder, done)
                continue

            if not isinstance(data, dict):
                msg = f"  error: {index_json} top-level value is not an object"
                print(msg, file=sys.stderr)
                failures.append(msg)
                save_checkpoint(folder, done)
                continue

            try:
                written = generate_all_pages(data, folder)
            except OSError as exc:
                msg = f"  error writing pages in {folder}: {exc}"
                print(msg, file=sys.stderr)
                failures.append(msg)
                save_checkpoint(folder, done)
                continue

            for out_path in written:
                print(f"  wrote {out_path}", file=sys.stderr)

            save_checkpoint(folder, done)

    except KeyboardInterrupt:
        print("\nInterrupted; progress saved for next run.", file=sys.stderr)
        return 130

    clear_checkpoint()

    if failures:
        print(f"\nCompleted with {len(failures)} failure(s):", file=sys.stderr)
        for msg in failures:
            print(msg, file=sys.stderr)
        return 1

    print(f"\nDone. Processed {total} folder(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
