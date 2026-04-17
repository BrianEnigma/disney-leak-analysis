#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import sys
import zipfile
from pathlib import Path

from config import INPUT_DATA_FOLDER, OUTPUT_FOLDER

PROGRESS_STATE_FILE = Path(".expand_progress")


def print_progress(current: int, total: int, name: str) -> None:
    percent = (current / total) * 100 if total else 100.0
    sys.stdout.write(f"\rProcessing files: {current}/{total} ({percent:5.1f}%) - {name}")
    sys.stdout.flush()


def load_json_name(path: Path) -> str:
    """
    Parse the json name from the file by loading the whole thing into an object model.
    :param path: path to the file
    :return: the name field
    """
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level JSON value must be an object")

    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"{path}: top-level 'name' must be a non-empty string")

    return name


def load_json_name_alt(path: Path) -> str:
    """
    Parse the json name from the file by reading the first two lines of the file
    and manually parsing the `  "name": "channel-name",` string.
    This is a speed-up hack, but it works for the data format we have.
    :param path: path to the file
    :return: the name field
    """
    with path.open("r", encoding="utf-8") as f:
        first_two_lines = [next(f, ""), next(f, "")]

    if len(first_two_lines) < 2 or not first_two_lines[1]:
        raise ValueError(f"{path}: file must contain at least two lines")

    line = first_two_lines[1].strip()

    prefix = '"name":'
    if prefix not in line:
        raise ValueError(f"{path}: second line does not contain a 'name' field")

    _, value_part = line.split(prefix, 1)
    value_part = value_part.strip().rstrip(",")

    if not (value_part.startswith('"') and value_part.endswith('"')):
        raise ValueError(f"{path}: malformed 'name' field")

    name = value_part[1:-1]
    if not name.strip():
        raise ValueError(f"{path}: top-level 'name' must be a non-empty string")

    return name


def extract_zip_stripping_single_root(archive: zipfile.ZipFile, destination_folder: Path) -> None:
    members = [info for info in archive.infolist() if info.filename and not info.is_dir()]
    if not members:
        return

    root_names = {
        Path(info.filename).parts[0]
        for info in members
        if len(Path(info.filename).parts) > 1
    }

    strip_prefix = root_names.pop() if len(root_names) == 1 else None

    for info in members:
        member_path = Path(info.filename)

        if strip_prefix and member_path.parts and member_path.parts[0] == strip_prefix:
            member_path = Path(*member_path.parts[1:])

        if not member_path.parts:
            continue

        target_path = destination_folder / member_path
        target_path.parent.mkdir(parents=True, exist_ok=True)

        with archive.open(info, "r") as src, target_path.open("wb") as dst:
            shutil.copyfileobj(src, dst)


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


def process_json_file(json_path: Path, output_root: Path) -> None:
    folder_name = load_json_name_alt(json_path)
    destination_folder = output_root / folder_name
    destination_folder.mkdir(parents=True, exist_ok=True)

    shutil.copy2(json_path, destination_folder / "index.json")

    zip_path = json_path.with_suffix(".zip")
    if zip_path.exists():
        with zipfile.ZipFile(zip_path, "r") as archive:
            extract_zip_stripping_single_root(archive, destination_folder)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Expand json files into output folders")
    parser.add_argument(
        "limit",
        nargs="?",
        type=int,
        help="Maximum number of json files to process",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_folder = Path(INPUT_DATA_FOLDER)
    output_folder = Path(OUTPUT_FOLDER)

    if not input_folder.exists():
        print(f"{input_folder}: input folder does not exist")
        return 1

    if not input_folder.is_dir():
        print(f"{input_folder}: input path is not a directory")
        return 1

    output_folder.mkdir(parents=True, exist_ok=True)

    json_files = sorted(input_folder.rglob("*.json"))
    if args.limit is not None:
        json_files = json_files[: max(args.limit, 0)]

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

    if start_index >= len(json_files):
        clear_resume_point()
        print(f"Processed {len(json_files)} json file(s)")
        return 0

    total = len(json_files)
    failures: list[str] = []

    try:
        for index, json_path in enumerate(json_files[start_index:], start=start_index + 1):
            print_progress(index, total, json_path.name)
            try:
                process_json_file(json_path, output_folder)
            except Exception as exc:
                failures.append(f"{json_path}: {exc}")
            finally:
                save_resume_point(json_path)
    except KeyboardInterrupt:
        sys.stdout.write("\n")
        sys.stdout.flush()
        print("Interrupted; progress saved for next run")
        return 130

    sys.stdout.write("\n")
    sys.stdout.flush()
    clear_resume_point()

    if failures:
        for failure in failures:
            print(failure)
        return 1

    print(f"Processed {total} json file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
