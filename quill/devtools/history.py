"""Console command history — persistent JSONL log in app_data_dir/console/."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.stability.redaction import redact_source_tokens

_HISTORY_FILE = "console/history.jsonl"
_MAX_ENTRIES = 500


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    timestamp: str
    language: str  # "python" | "typescript"
    source: str
    success: bool


def _history_path() -> Path:
    return app_data_dir() / _HISTORY_FILE


def add_entry(language: str, source: str, success: bool) -> None:
    """Append one history entry to the JSONL log."""
    path = _history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "language": language,
        "source": redact_source_tokens(source),
        "success": success,
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    _trim(path)


def load(max_entries: int = 200, *, language: str | None = None) -> list[HistoryEntry]:
    """Return the most recent *max_entries* history entries (oldest first).

    Pass *language* (``"python"`` or ``"typescript"``) to filter to one
    language only.
    """
    path = _history_path()
    if not path.exists():
        return []
    entries: list[HistoryEntry] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            lang = str(obj.get("language", "python"))
            if language is not None and lang != language:
                continue
            entries.append(
                HistoryEntry(
                    timestamp=str(obj.get("timestamp", "")),
                    language=lang,
                    source=str(obj.get("source", "")),
                    success=bool(obj.get("success", True)),
                )
            )
        except (json.JSONDecodeError, KeyError):
            continue
    return entries[-max_entries:]


def clear() -> None:
    """Delete the entire history log."""
    path = _history_path()
    if path.exists():
        path.unlink()


def _trim(path: Path) -> None:
    """Keep only the last _MAX_ENTRIES lines (atomic write)."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    if len(lines) <= _MAX_ENTRIES:
        return
    trimmed = "\n".join(lines[-_MAX_ENTRIES:]) + "\n"
    temp = path.with_suffix(".tmp")
    try:
        temp.write_text(trimmed, encoding="utf-8")
        os.replace(temp, path)
    except OSError:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
