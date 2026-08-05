"""Named, note-bearing media bookmarks (``player.md`` Sections 7.9 / 9.7).

Per-book time-point bookmarks with an optional label and note, persisted as one
atomic JSON file keyed by the book's resume key. Pure ``quill.core`` -- the UI
lists them (Enter jumps), adds them (one key), and can send one into the open
document. The store path is injectable so it is unit-testable without the real
data directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quill.core.media.timecode import format_timecode
from quill.core.storage import read_json, write_json_atomic


def _as_int(value: object, default: int = -1) -> int:
    if isinstance(value, (int, float, str)):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
    return default


@dataclass(frozen=True, slots=True)
class MediaBookmark:
    """One time-point bookmark within a book."""

    position_ms: int
    label: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, object]:
        return {"position_ms": self.position_ms, "label": self.label, "note": self.note}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> MediaBookmark:
        return cls(
            position_ms=max(0, _as_int(data.get("position_ms"), 0)),
            label=str(data.get("label", "") or ""),
            note=str(data.get("note", "") or ""),
        )


class BookmarkStore:
    """Per-book bookmark persistence in one atomic JSON file."""

    def __init__(self, path: Path | str | None = None) -> None:
        self._path = Path(path) if path is not None else self._default_path()

    @staticmethod
    def _default_path() -> Path:
        from quill.core.paths import app_data_dir

        return app_data_dir() / "media_bookmarks.json"

    def _read(self) -> dict[str, list[dict[str, object]]]:
        data = read_json(self._path, default={})
        return data if isinstance(data, dict) else {}

    def _write(self, data: dict[str, list[dict[str, object]]]) -> None:
        write_json_atomic(self._path, data)

    def list(self, book_key: str) -> list[MediaBookmark]:
        """Return the book's bookmarks, sorted by position."""
        rows = self._read().get(book_key, [])
        marks = [MediaBookmark.from_dict(row) for row in rows if isinstance(row, dict)]
        return sorted(marks, key=lambda m: m.position_ms)

    def add(
        self, book_key: str, position_ms: int, *, label: str = "", note: str = ""
    ) -> MediaBookmark:
        """Add (or update the note/label of) a bookmark at ``position_ms``."""
        mark = MediaBookmark(position_ms=max(0, int(position_ms)), label=label, note=note)
        data = self._read()
        rows = [row for row in data.get(book_key, []) if isinstance(row, dict)]
        rows = [row for row in rows if _as_int(row.get("position_ms")) != mark.position_ms]
        rows.append(mark.to_dict())
        data[book_key] = rows
        self._write(data)
        return mark

    def remove(self, book_key: str, position_ms: int) -> bool:
        """Remove the bookmark at ``position_ms``. Returns True when one existed."""
        data = self._read()
        rows = [row for row in data.get(book_key, []) if isinstance(row, dict)]
        kept = [row for row in rows if _as_int(row.get("position_ms")) != int(position_ms)]
        if len(kept) == len(rows):
            return False
        if kept:
            data[book_key] = kept
        else:
            data.pop(book_key, None)
        self._write(data)
        return True

    def rename(self, book_key: str, position_ms: int, label: str) -> bool:
        """Set the label of the bookmark at ``position_ms``. Returns True on success."""
        existing = {m.position_ms: m for m in self.list(book_key)}
        mark = existing.get(int(position_ms))
        if mark is None:
            return False
        self.add(book_key, mark.position_ms, label=label, note=mark.note)
        return True

    def clear(self, book_key: str) -> int:
        """Remove all bookmarks for a book. Returns how many were removed."""
        data = self._read()
        rows = data.get(book_key)
        if not rows:
            return 0
        data.pop(book_key, None)
        self._write(data)
        return len(rows)

    # -- sync (QuilleSync local half) ---------------------------------------

    def export_bundle(self) -> dict[str, object]:
        """A portable bundle of every book's bookmarks, for cross-device sync."""
        return {"version": 1, "kind": "quill-media-bookmarks", "books": self._read()}

    def merge_bundle(self, bundle: dict[str, object]) -> int:
        """Merge an imported bundle in (union by position). Returns how many were added."""
        books = bundle.get("books")
        if not isinstance(books, dict):
            return 0
        data = self._read()
        added = 0
        for book_key, rows in books.items():
            if not isinstance(rows, list):
                continue
            current = [row for row in data.get(book_key, []) if isinstance(row, dict)]
            seen = {_as_int(row.get("position_ms")) for row in current}
            for row in rows:
                if not isinstance(row, dict):
                    continue
                pos = _as_int(row.get("position_ms"))
                if pos < 0 or pos in seen:
                    continue
                current.append(MediaBookmark.from_dict(row).to_dict())
                seen.add(pos)
                added += 1
            if current:
                data[book_key] = current
        if added:
            self._write(data)
        return added


def format_bookmark_line(position_ms: int, *, note: str = "", title: str = "") -> str:
    """A one-line, paste-ready bookmark, e.g. ``[1:23:45] note — Title``."""
    stamp = f"[{format_timecode(max(0, int(position_ms)), always_hours=True)}]"
    parts = [stamp]
    if note.strip():
        parts.append(note.strip())
    line = " ".join(parts)
    if title.strip():
        line = f"{line} — {title.strip()}"
    return line


def bookmarks_to_markdown(title: str, marks: list[MediaBookmark]) -> str:
    """Render a book's bookmarks as a Markdown list (for Export Bookmarks)."""
    heading = f"# Bookmarks — {title.strip()}" if title.strip() else "# Bookmarks"
    lines = [heading, ""]
    for mark in sorted(marks, key=lambda m: m.position_ms):
        stamp = format_timecode(max(0, mark.position_ms), always_hours=True)
        note = (mark.note or mark.label).strip()
        lines.append(f"- **{stamp}**{f' — {note}' if note else ''}")
    return "\n".join(lines) + "\n"


__all__ = [
    "BookmarkStore",
    "MediaBookmark",
    "bookmarks_to_markdown",
    "format_bookmark_line",
]
