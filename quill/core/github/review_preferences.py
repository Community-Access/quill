"""The GitHub workbench's own small reading preferences, shared by both editors.

Today that is one choice: whether a diff marks its lines with words ("Added
line", "Removed line") or symbols ("+", "-"). It lives beside the other
GitHub workbench files rather than in either editor's settings, because the
pull-request dialogs are the same code in QUILL and QUILL Lite and the choice
should follow the reader from one to the other.

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.github.diff_lines import LINE_MARK_STYLES, LINE_MARKS_WORDS
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

_FILENAME = "github_review_preferences.json"


def _path(path: Path | None) -> Path:
    return path if path is not None else app_data_dir() / _FILENAME


def load_line_marks(path: Path | None = None) -> str:
    """The saved line-mark style; words when nothing valid is saved."""
    raw = read_json(_path(path), default={})
    value = raw.get("diff_line_marks") if isinstance(raw, dict) else None
    return value if isinstance(value, str) and value in LINE_MARK_STYLES else LINE_MARKS_WORDS


def save_line_marks(style: str, path: Path | None = None) -> bool:
    """Remember *style*; False when it is not a known style or cannot be written."""
    if style not in LINE_MARK_STYLES:
        return False
    try:
        write_json_atomic(_path(path), {"diff_line_marks": style})
    except OSError:
        return False
    return True


__all__ = ["load_line_marks", "save_line_marks"]
