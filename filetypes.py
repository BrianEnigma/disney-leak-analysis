#!/usr/bin/env python3

from collections import Counter
from pathlib import Path

from config import OUTPUT_FOLDER

IGNORED_NAMES = {"index.json", "message-count.txt"}


def is_ignored(path: Path) -> bool:
    name = path.name
    if name in IGNORED_NAMES:
        return True
    # Ignore index*.html (e.g. index.html, index-2.html, etc.)
    if name.startswith("index") and name.endswith(".html"):
        return True
    return False


def count_extensions(directory: Path, counts: Counter, no_ext_files: list[Path]) -> None:
    """Count file extensions for immediate files in directory (non-recursive)."""
    for path in directory.iterdir():
        if path.is_file() and not is_ignored(path):
            ext = path.suffix.lower() if path.suffix else "(no ext)"
            if len(ext) > 16:
                ext = "(no ext)"
            counts[ext] += 1
            if ext == "(no ext)":
                no_ext_files.append(path)


def main() -> None:
    root = Path(OUTPUT_FOLDER)
    dirs = [root] + sorted(d for d in root.glob("*") if d.is_dir())
    total = len(dirs)
    counts: Counter = Counter()
    no_ext_files: list[Path] = []

    for i, directory in enumerate(dirs, start=1):
        count_extensions(directory, counts, no_ext_files)
        pct = i / total * 100
        print(f"\r{pct:5.1f}%  ({i}/{total} dirs)", end="", flush=True)

    print()  # newline after progress

    out_path = Path("filetypes.txt")
    with out_path.open("w", encoding="utf-8") as f:
        for ext, count in counts.most_common():
            f.write(f"{count:>6}  {ext}\n")

    print(f"Written to {out_path}")

    none_path = Path("filetypes-none.txt")
    with none_path.open("w", encoding="utf-8") as f:
        for p in sorted(no_ext_files):
            f.write(f"{p.relative_to(root)}\n")

    print(f"Written to {none_path}")


if __name__ == "__main__":
    main()
