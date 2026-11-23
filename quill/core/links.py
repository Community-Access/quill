from __future__ import annotations

import re
from pathlib import Path


def infer_markup_kind(path: Path | None) -> str:
    if path is None:
        return "plain"
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown", ".mdx"}:
        return "markdown"
    if suffix in {".mobi", ".prc"}:
        return "markdown"  # a Kindle book opens as Markdown (quill.io.mobi_open)
    if suffix in {".html", ".htm", ".xhtml"}:
        return "html"
    if suffix in {".yaml", ".yml"}:
        return "yaml"
    return "plain"


def build_link_text(markup_kind: str, text: str, url: str) -> str:
    display = text.strip() or url
    if markup_kind == "markdown":
        return f"[{display}]({url})"
    if markup_kind == "html":
        return f'<a href="{url}">{display}</a>'
    return url if display == url else f"{display} ({url})"


def find_link_at_cursor(text: str, cursor: int) -> str | None:
    for pattern, group in (
        (r"\[[^\]]+\]\((https?://[^\s)]+)\)", 1),
        (r'href=["\']([^"\']+)["\']', 1),
        (r"(https?://[^\s<>\")]+)", 1),
    ):
        for match in re.finditer(pattern, text):
            if match.start() <= cursor <= match.end():
                return match.group(group)
    return None
