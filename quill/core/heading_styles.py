from __future__ import annotations

import html
import re
from dataclasses import dataclass

from quill.core.markdown_sections import (
    _HTML_HEADING_PATTERN,
    _MD_HEADING_PATTERN,
)

_ALLOWED_TEXT_ALIGN = {"left", "right", "center", "justify"}


@dataclass(frozen=True, slots=True)
class HeadingStyle:
    font_family: str | None = None
    font_size_pt: int | None = None
    text_align: str | None = None

    def declarations(self) -> list[str]:
        declarations: list[str] = []
        if self.font_family:
            declarations.append(f"font-family: {html.escape(self.font_family, quote=True)}")
        if self.font_size_pt is not None and self.font_size_pt > 0:
            declarations.append(f"font-size: {self.font_size_pt}pt")
        if self.text_align and self.text_align.lower() in _ALLOWED_TEXT_ALIGN:
            declarations.append(f"text-align: {self.text_align.lower()}")
        return declarations


def apply_heading_style(
    text: str,
    *,
    markup_kind: str,
    style: HeadingStyle,
    levels: set[int] | None = None,
) -> tuple[str, int]:
    if not style.declarations():
        return text, 0
    normalized_levels = {level for level in (levels or set(range(1, 7))) if 1 <= level <= 6}
    if not normalized_levels:
        return text, 0
    if markup_kind == "html":
        return _apply_html_heading_style(text, style, normalized_levels)
    if markup_kind == "markdown":
        return _apply_markdown_heading_style(text, style, normalized_levels)
    return text, 0


def _apply_markdown_heading_style(
    text: str,
    style: HeadingStyle,
    levels: set[int],
) -> tuple[str, int]:
    changed = 0
    style_text = "; ".join(style.declarations())

    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        marker = match.group("marker")
        level = len(marker)
        if level not in levels:
            return match.group(0)
        body = (match.group("title") or "").strip()
        changed += 1
        return f'<h{level} style="{style_text}">{body}</h{level}>'

    # Use the shared pattern from quill.core.markdown_sections (#359): the
    # old local regex required a space + body, so a heading like ``#NoSpace``
    # was silently skipped. The canonical pattern matches an optional title.
    updated = _MD_HEADING_PATTERN.sub(replace, text)
    return updated, changed


def _apply_html_heading_style(
    text: str,
    style: HeadingStyle,
    levels: set[int],
) -> tuple[str, int]:
    # The shared HTML pattern from quill.core.markdown_sections (#359).
    pattern = _HTML_HEADING_PATTERN
    changed = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        level = int(match.group("level"))
        if level not in levels:
            return match.group(0)
        attrs = match.group("attrs")
        body = match.group("body")
        merged_attrs = _merge_style_attr(attrs, style)
        changed += 1
        return f"<h{level}{merged_attrs}>{body}</h{level}>"

    updated = pattern.sub(replace, text)
    return updated, changed


def _merge_style_attr(attrs: str, style: HeadingStyle) -> str:
    declarations = style.declarations()
    if not declarations:
        return attrs
    style_match = re.search(
        r"""style\s*=\s*["'](?P<value>[^"']*)["']""", attrs, flags=re.IGNORECASE
    )
    declaration_map: dict[str, str] = {}
    if style_match is not None:
        existing = style_match.group("value")
        for chunk in existing.split(";"):
            statement = chunk.strip()
            if ":" not in statement:
                continue
            key, value = statement.split(":", 1)
            declaration_map[key.strip().lower()] = value.strip()
    for declaration in declarations:
        key, value = declaration.split(":", 1)
        declaration_map[key.strip().lower()] = value.strip()
    merged_style = "; ".join(f"{key}: {value}" for key, value in declaration_map.items())
    if style_match is not None:
        start, end = style_match.span()
        attrs = f'{attrs[:start]}style="{merged_style}"{attrs[end:]}'
        return attrs
    spacer = "" if not attrs or attrs.startswith(" ") else " "
    return f'{attrs}{spacer} style="{merged_style}"'
