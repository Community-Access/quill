"""Derive a suggested document title/filename from a document's first line.

Format-agnostic by design: it takes the first non-empty line of the text and
turns it into a clean, filename-safe title, lightly stripping the markup leaders
that show up across the formats QUILL edits (a Markdown ``#`` heading, a ``>``
quote, a ``-``/``*`` list bullet, or inline HTML tags). Used -- when the user
enables the option -- to pre-fill the name in Save-As / Export dialogs for an
untitled document.

Pure model code; no ``wx`` imports.
"""

from __future__ import annotations

import re

#: Characters that are invalid in a Windows filename, plus control characters.
_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
#: A simple inline HTML/XML tag, so ``<h1>Title</h1>`` yields ``Title``.
_HTML_TAG = re.compile(r"<[^>]+>")
#: Leading markup that precedes the human text on a heading/quote/list line.
_LEADING_MARKUP = re.compile(r"^[#>\*\-+=•·\s]+")
_WHITESPACE = re.compile(r"\s+")

#: Keep suggested filenames comfortably under filesystem limits.
DEFAULT_MAX_TITLE_LENGTH = 60


def suggested_title_from_text(text: str, *, max_length: int = DEFAULT_MAX_TITLE_LENGTH) -> str:
    """Return a filename-safe title from the first meaningful line, or ``""``.

    Returns ``""`` when the document is empty or has no usable first line, so the
    caller can fall back to its existing default.
    """
    for raw_line in text.splitlines():
        line = _HTML_TAG.sub(" ", raw_line)  # drop inline tags first
        line = _LEADING_MARKUP.sub("", line).strip()
        if not line:
            continue
        return _sanitize(line, max_length)
    return ""


def _sanitize(value: str, max_length: int) -> str:
    value = _INVALID_FILENAME_CHARS.sub("", value)
    value = _WHITESPACE.sub(" ", value).strip()
    # A leading/trailing dot or space is invalid (Windows) or surprising.
    value = value.strip(". ")
    if len(value) > max_length:
        value = value[:max_length].rstrip()
    return value


__all__ = ["DEFAULT_MAX_TITLE_LENGTH", "suggested_title_from_text"]
