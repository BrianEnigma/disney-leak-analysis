#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

PAGE_SIZE = 1000


def basename(url_private: str) -> str:
    """Return just the filename portion of a url_private path."""
    return Path(url_private).name


def page_filename(page: int) -> str:
    """Return the output filename for the given 1-based page number."""
    return "index.html" if page == 1 else f"index-{page}.html"


def render_file_item(f: dict) -> str:
    """Render a single file entry as an HTML list item."""
    mimetype: str = f.get("mimetype", "")
    url_private: str = f.get("url_private", "")
    filename = basename(url_private)
    name: str = f.get("name", filename)

    if mimetype.startswith("image/"):
        inner = f'<img src="{html.escape(filename)}" alt="{html.escape(name)}">'
    elif mimetype.startswith("video/"):
        inner = (
            f'<video controls>'
            f'<source src="{html.escape(filename)}">'
            f'{html.escape(name)}'
            f'</video>'
        )
    else:
        inner = f'<a href="{html.escape(filename)}">{html.escape(name)}</a>'

    return f"      <li>{inner}</li>"


def render_attachment_item(att: dict) -> str:
    """Render a single attachment entry as an HTML list item."""
    from_url: str = att.get("from_url", "")
    fallback: str = att.get("fallback", from_url)
    return f'      <li><a href="{html.escape(from_url)}">{html.escape(fallback)}</a></li>'


def render_message(msg: dict) -> str:
    """Render a single message as an HTML list item, with optional sub-lists."""
    user: str = msg.get("user", "")
    text: str = msg.get("text", "")
    lines: list[str] = [f"  <li>{html.escape(user)}: {html.escape(text)}"]

    attachments: list[dict] | None = msg.get("attachments")
    if attachments:
        lines.append("    <ul>")
        for att in attachments:
            lines.append(render_attachment_item(att))
        lines.append("    </ul>")

    files: list[dict] | None = msg.get("files")
    if files:
        lines.append("    <ul>")
        for f in files:
            lines.append(render_file_item(f))
        lines.append("    </ul>")

    lines.append("  </li>")
    return "\n".join(lines)


def render_pagination(current_page: int, total_pages: int) -> str:
    """Render a pagination nav bar as an HTML string."""
    if total_pages <= 1:
        return ""

    parts: list[str] = ['<nav class="pagination">']

    if current_page > 1:
        parts.append(
            f'  <a href="{html.escape(page_filename(current_page - 1))}">&laquo; Prev</a>'
        )
    else:
        parts.append('  <span class="disabled">&laquo; Prev</span>')

    for p in range(1, total_pages + 1):
        fname = html.escape(page_filename(p))
        if p == current_page:
            parts.append(f'  <strong>{p}</strong>')
        else:
            parts.append(f'  <a href="{fname}">{p}</a>')

    if current_page < total_pages:
        parts.append(
            f'  <a href="{html.escape(page_filename(current_page + 1))}">Next &raquo;</a>'
        )
    else:
        parts.append('  <span class="disabled">Next &raquo;</span>')

    parts.append('</nav>')
    return "\n".join(parts)


def generate_page(
    name: str,
    messages: list[dict],
    current_page: int,
    total_pages: int,
) -> str:
    """Generate a single paginated HTML page."""
    pagination = render_pagination(current_page, total_pages)

    parts: list[str] = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        '  <meta charset="utf-8">',
        f"  <title>{html.escape(name)}</title>",
        "  <style>",
        "    img, video { max-width: 100vw; max-height: 50vh; }",
        "    .pagination { margin: 1em 0; display: flex; gap: 0.5em; align-items: center; flex-wrap: wrap; }",
        "    .pagination a, .pagination strong, .pagination .disabled",
        "      { padding: 0.25em 0.6em; border: 1px solid #aaa; border-radius: 3px; text-decoration: none; }",
        "    .pagination strong { background: #333; color: #fff; border-color: #333; }",
        "    .pagination .disabled { color: #aaa; border-color: #ddd; cursor: default; }",
        "  </style>",
        "</head>",
        "<body>",
        f"<h1>{html.escape(name)}</h1>",
    ]

    if pagination:
        parts.append(pagination)

    parts.append("<ul>")
    for msg in messages:
        parts.append(render_message(msg))
    parts.append("</ul>")

    if pagination:
        parts.append(pagination)

    parts += ["</body>", "</html>"]

    return "\n".join(parts) + "\n"


def generate_html(data: dict) -> str:
    """
    Generate a full HTML page from the parsed JSON data.
    Kept for single-page use (when total messages <= PAGE_SIZE).
    Returns the HTML string for page 1 (or the only page).
    """
    name: str = data.get("name", "")
    messages: list[dict] = data.get("messages") or []
    page_messages = messages[:PAGE_SIZE]
    total_pages = max(1, (len(messages) + PAGE_SIZE - 1) // PAGE_SIZE)
    return generate_page(name, page_messages, 1, total_pages)


def generate_all_pages(data: dict, out_dir: Path) -> list[Path]:
    """
    Generate all paginated HTML files into out_dir.
    Returns the list of files written.
    """
    name: str = data.get("name", "")
    messages: list[dict] = data.get("messages") or []
    total = len(messages)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    written: list[Path] = []
    for page in range(1, total_pages + 1):
        start = (page - 1) * PAGE_SIZE
        end = start + PAGE_SIZE
        page_msgs = messages[start:end]
        html_content = generate_page(name, page_msgs, page, total_pages)
        out_path = out_dir / page_filename(page)
        out_path.write_text(html_content, encoding="utf-8")
        written.append(out_path)

    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate paginated HTML pages from a Slack channel JSON export"
    )
    parser.add_argument("json_file", help="Path to the JSON file to process")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    json_path = Path(args.json_file)
    if not json_path.exists():
        print(f"{json_path}: file not found", file=sys.stderr)
        return 1

    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        print(f"{json_path}: invalid JSON: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"{json_path}: could not read file: {exc}", file=sys.stderr)
        return 1

    if not isinstance(data, dict):
        print(f"{json_path}: top-level JSON value must be an object", file=sys.stderr)
        return 1

    out_dir = json_path.parent
    written = generate_all_pages(data, out_dir)

    for p in written:
        print(f"Written to {p}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
