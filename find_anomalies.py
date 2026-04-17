#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from config import INPUT_DATA_FOLDER

REQUIRED_KEYS = {"name", "messages", "channel_id"}
PROGRESS_STATE_FILE = Path(".find_anomalies_progress")


def describe_type(value: Any) -> str:
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "object"
    if value is None:
        return "null"
    return type(value).__name__


def check_json_file(path: Path) -> list[str]:
    errors: list[str] = []

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"]
    except OSError as exc:
        return [f"{path}: could not read file: {exc}"]

    if not isinstance(data, dict):
        return [f"{path}: top-level JSON value must be an object, got {describe_type(data)}"]

    missing_keys = REQUIRED_KEYS - data.keys()
    for key in sorted(missing_keys):
        errors.append(f"{path}: missing required top-level key '{key}'")

    if "name" in data and not isinstance(data["name"], str):
        errors.append(
            f"{path}: top-level key 'name' must be a string, got {describe_type(data['name'])}"
        )

    if "messages" in data and not isinstance(data["messages"], list):
        errors.append(
            f"{path}: top-level key 'messages' must be a list, got {describe_type(data['messages'])}"
        )

    if "channel_id" in data and not isinstance(data["channel_id"], str):
        errors.append(
            f"{path}: top-level key 'channel_id' must be a string, got {describe_type(data['channel_id'])}"
        )

    extra_keys = set(data.keys()) - REQUIRED_KEYS
    for key in sorted(extra_keys):
        errors.append(f"{path}: unexpected top-level key '{key}'")

    return errors


def print_progress(path: Path, current: int, total: int) -> None:
    percent = (current / total) * 100 if total else 100.0
    sys.stdout.write(f"\rChecking files: {current}/{total} ({percent:5.1f}%) {path.name}")
    sys.stdout.flush()


def load_resume_point() -> str | None:
    try:
        value = PROGRESS_STATE_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value or None


def save_resume_point(path: Path) -> None:
    PROGRESS_STATE_FILE.write_text(str(path), encoding="utf-8")


def clear_resume_point() -> None:
    try:
        PROGRESS_STATE_FILE.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


def main() -> int:
    input_folder = Path(INPUT_DATA_FOLDER)

    if not input_folder.exists():
        print(f"{input_folder}: input folder does not exist")
        return 1

    if not input_folder.is_dir():
        print(f"{input_folder}: input path is not a directory")
        return 1

    json_files = sorted(input_folder.rglob("*.json"))
    if not json_files:
        print(f"{input_folder}: no json files found")
        return 0

    resume_from = load_resume_point()
    start_index = 0
    if resume_from is not None:
        for index, path in enumerate(json_files):
            if str(path) == resume_from:
                start_index = index + 1
                break

    all_errors: list[str] = []
    total = len(json_files)

    if start_index >= total:
        clear_resume_point()
        print(f"Checked {len(json_files)} json file(s): no anomalies found")
        return 0

    try:
        for index, path in enumerate(json_files[start_index:], start=start_index + 1):
            print_progress(path, index, total)
            all_errors.extend(check_json_file(path))
            save_resume_point(path)
    except KeyboardInterrupt:
        sys.stdout.write("\n")
        sys.stdout.flush()
        print("Interrupted; progress saved for next run")
        return 130

    sys.stdout.write("\n")
    sys.stdout.flush()
    clear_resume_point()

    if all_errors:
        for error in all_errors:
            print(error)
        return 1

    print(f"Checked {len(json_files)} json file(s): no anomalies found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())




