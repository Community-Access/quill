"""Daily notes (Accessible Vault, Phase 6) — wx-free path math.

Maps a configured pattern like ``Journal/{{date:YYYY-MM-DD}}.md`` to a note's relative
path for a given day, and walks the calendar forward/back so "Open today's note" and
"Previous / Next daily note" are pure, testable computations (the UI does the file IO and
announces the date + whether it exists).
"""

from __future__ import annotations

import datetime as _dt
import re

from quill.core.vault.templates import format_datetime

DEFAULT_PATTERN = "Journal/{{date:YYYY-MM-DD}}.md"

_DATE_TOKEN_RE = re.compile(r"\{\{\s*date(?::([^}]*))?\s*\}\}")


def daily_note_relpath(pattern: str, day: _dt.date) -> str:
    """Resolve ``pattern`` to a vault-relative path for ``day`` (posix separators)."""
    noon = _dt.datetime(day.year, day.month, day.day, 12, 0, 0)

    def _sub(match: re.Match[str]) -> str:
        return format_datetime(noon, match.group(1) or "YYYY-MM-DD")

    rel = _DATE_TOKEN_RE.sub(_sub, pattern)
    return rel.replace("\\", "/")


def shift_daily(pattern: str, day: _dt.date, delta_days: int) -> tuple[str, _dt.date]:
    """The (relpath, date) ``delta_days`` from ``day`` — for Previous/Next daily note."""
    target = day + _dt.timedelta(days=delta_days)
    return daily_note_relpath(pattern, target), target
