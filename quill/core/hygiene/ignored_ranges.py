"""Compute ignored text ranges (URLs, emails, code blocks, etc.)."""

from __future__ import annotations

import re

from quill.core.hygiene.findings import TextRange

# --- compiled patterns ---

_URL = re.compile(
    r"https?://[^\s<>\"\])]+"
    r"|ftp://[^\s<>\"\])]+"
    r"|www\.[a-zA-Z0-9][^\s<>\"\])]+",
    re.IGNORECASE,
)

_EMAIL = re.compile(
    r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b",
)

_MD_FENCED_CODE = re.compile(
    r"^(`{3,}|~{3,})[^\n]*\n.*?\n\1[ \t]*$",
    re.MULTILINE | re.DOTALL,
)

_MD_INLINE_CODE = re.compile(r"`[^`\n]+`")

_MD_FRONT_MATTER = re.compile(r"\A---[ \t]*\n.*?\n---[ \t]*\n", re.DOTALL)

_MD_LINK_URL = re.compile(r"\[(?:[^\]]*)\]\(([^)]+)\)")

_FILE_PATH = re.compile(
    r"(?:^|(?<=\s))"  # start of string or preceded by whitespace
    r"(?:[A-Za-z]:\\|/)[^\s]*"  # absolute path
    r"|"
    r"[a-zA-Z0-9_\-]+\.[a-zA-Z]{2,4}"  # relative path with extension (e.g. file.py)
    r"(?:/[a-zA-Z0-9_\-\.]+)*",
)

_DECIMAL_NUMBER = re.compile(r"\b\d+\.\d+\b")

_TIME_PATTERN = re.compile(r"\b\d{1,2}:\d{2}\b")


def compute_ignored_ranges(
    text: str,
    *,
    is_markdown: bool = False,
) -> list[TextRange]:
    """Return ranges that hygiene rules should not report findings inside."""
    ranges: list[TextRange] = []

    for m in _URL.finditer(text):
        ranges.append(TextRange(m.start(), m.end()))

    for m in _EMAIL.finditer(text):
        ranges.append(TextRange(m.start(), m.end()))

    for m in _DECIMAL_NUMBER.finditer(text):
        ranges.append(TextRange(m.start(), m.end()))

    for m in _TIME_PATTERN.finditer(text):
        ranges.append(TextRange(m.start(), m.end()))

    if is_markdown:
        for m in _MD_FENCED_CODE.finditer(text):
            ranges.append(TextRange(m.start(), m.end()))
        for m in _MD_INLINE_CODE.finditer(text):
            ranges.append(TextRange(m.start(), m.end()))
        front = _MD_FRONT_MATTER.match(text)
        if front:
            ranges.append(TextRange(0, front.end()))
        for m in _MD_LINK_URL.finditer(text):
            # Ignore only the URL part (group 1)
            ranges.append(TextRange(m.start(1), m.end(1)))

    return ranges
