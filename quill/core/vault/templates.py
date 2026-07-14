"""Note templates with variables (Accessible Vault, Phase 6) — wx-free.

A tiny substitution pass, deliberately built on the same idea as the Snippet Gallery
rather than a second engine. Supported tokens:

- ``{{date}}`` / ``{{date:YYYY-MM-DD}}`` and ``{{time}}`` / ``{{time:HH-mm}}`` — the
  current date/time, in a friendly ``YYYY MM DD HH mm ss`` token format.
- ``{{title}}`` — the note title.
- ``{{prompt:Question}}`` — answered from ``answers`` (the UI speaks each question).
- ``{{cursor}}`` — removed; its position is returned so focus can land there, announced.
"""

from __future__ import annotations

import datetime as _dt
import re

_TOKEN_RE = re.compile(r"\{\{\s*(date|time|title|prompt|cursor)(?::([^}]*))?\s*\}\}")

_FORMAT_MAP = [
    ("YYYY", "%Y"),
    ("MM", "%m"),
    ("DD", "%d"),
    ("HH", "%H"),
    ("mm", "%M"),
    ("ss", "%S"),
]
_DEFAULT_DATE = "YYYY-MM-DD"
_DEFAULT_TIME = "HH:mm"


def _to_strftime(fmt: str) -> str:
    out = fmt
    for token, code in _FORMAT_MAP:
        out = out.replace(token, code)
    return out


def format_datetime(now: _dt.datetime, fmt: str) -> str:
    """Format ``now`` with a friendly YYYY/MM/DD/HH/mm/ss token string."""
    return now.strftime(_to_strftime(fmt))


def template_prompts(text: str) -> list[str]:
    """Every distinct ``{{prompt:Question}}`` question, in first-seen order."""
    seen: list[str] = []
    for match in _TOKEN_RE.finditer(text):
        if match.group(1) == "prompt":
            question = (match.group(2) or "").strip()
            if question and question not in seen:
                seen.append(question)
    return seen


def render_template(
    text: str,
    *,
    now: _dt.datetime,
    title: str = "",
    answers: dict[str, str] | None = None,
) -> tuple[str, int]:
    """Substitute template tokens; return ``(rendered_text, cursor_offset)``.

    ``cursor_offset`` is where ``{{cursor}}`` was (the marker removed), or ``-1`` when the
    template has none. Unanswered prompts and unknown formats degrade to sensible
    defaults rather than raising.
    """
    replies = answers or {}
    cursor_offset = -1
    out: list[str] = []
    pos = 0
    for match in _TOKEN_RE.finditer(text):
        out.append(text[pos : match.start()])
        kind, arg = match.group(1), match.group(2)
        if kind == "date":
            out.append(format_datetime(now, arg or _DEFAULT_DATE))
        elif kind == "time":
            out.append(format_datetime(now, arg or _DEFAULT_TIME))
        elif kind == "title":
            out.append(title)
        elif kind == "prompt":
            out.append(replies.get((arg or "").strip(), ""))
        elif kind == "cursor":
            cursor_offset = sum(len(p) for p in out)
        pos = match.end()
    out.append(text[pos:])
    return "".join(out), cursor_offset
