"""Named, note-bearing bookmarks on any playable thing (``player.md`` 7.9/9.7).

Time-point bookmarks with an optional label and note, persisted as one atomic
JSON file keyed by an **anchor** -- and the anchor is the whole of list.md 4.3
and 4.5. This began as the Media Player's per-book store, keyed by a book's
resume key, and the key was always just an opaque string: what changed is that
:mod:`quill.core.bookmark_anchors` now says how *every* playable thing spells
one, so a station, a YouTube row, a recording and a podcast episode all live
here beside the books.

Two consequences worth naming, because they are the point:

* **One list window, not four.** A bookmark is a bookmark; where it points is
  a property of the row, not a reason for a separate feature.
* **A bookmark made in Quill Radio is in QUILL Cast's list.** Both apps build
  the identical anchor for the identical episode and read the same file in the
  shared data folder, so there is no sync, no merge and no protocol -- the same
  trick ``radio_listens`` and ``cross_app_resume`` already play with positions.

The label and the note are both optional, deliberately (4.2): a bare
timestamped bookmark -- "I was here" -- is the most common kind, and demanding
a sentence for it is demanding a sentence.

Pure ``quill.core``. The store path is injectable so it is unit-testable
without the real data directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quill.core.media.timecode import format_timecode
from quill.core.storage import read_json, write_json_atomic

#: ``list`` is also the name of this store's read method, and inside the class
#: body the method wins -- so the two annotations that need the builtin say so
#: through an alias rather than by renaming a public method.
_Anchors = list[str]
_Rows = list["tuple[str, MediaBookmark]"]


def _as_int(value: object, default: int = -1) -> int:
    if isinstance(value, (int, float, str)):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
    return default


@dataclass(frozen=True, slots=True)
class MediaBookmark:
    """One time-point bookmark on one anchored thing.

    ``label`` and ``note`` are both optional: a bare timestamp is a bookmark
    (4.2). ``title`` is what the anchored thing was *called* when the bookmark
    was made, carried on the row rather than resolved -- a shared list has to
    name a station Quill Radio knows and QUILL Cast does not, and a row that
    reads "Recording, 1:04:12" with no name is a row nobody can use.
    """

    position_ms: int
    label: str = ""
    note: str = ""
    title: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "position_ms": self.position_ms,
            "label": self.label,
            "note": self.note,
            "title": self.title,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> MediaBookmark:
        return cls(
            position_ms=max(0, _as_int(data.get("position_ms"), 0)),
            label=str(data.get("label", "") or ""),
            note=str(data.get("note", "") or ""),
            title=str(data.get("title", "") or ""),
        )


class BookmarkStore:
    """Bookmark persistence for every anchor, in one atomic JSON file.

    The parameter is still spelled ``book_key`` at every call site that only
    ever holds books, and means "anchor" everywhere -- renaming it across four
    modules would have been churn in exchange for nothing a reader gains that
    this sentence does not give them.
    """

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
        self,
        book_key: str,
        position_ms: int,
        *,
        label: str = "",
        note: str = "",
        title: str = "",
    ) -> MediaBookmark:
        """Add (or update the note/label of) a bookmark at ``position_ms``."""
        mark = MediaBookmark(
            position_ms=max(0, int(position_ms)), label=label, note=note, title=title
        )
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
        self.add(book_key, mark.position_ms, label=label, note=mark.note, title=mark.title)
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

    def anchors(self) -> _Anchors:
        """Every anchor that has at least one bookmark, in stored order."""
        return [key for key, rows in self._read().items() if rows]

    def all_bookmarks(self) -> _Rows:
        """``(anchor, bookmark)`` for everything, newest anchor last.

        The one read a shared list window needs, and the reason it is here
        rather than in the window: three surfaces would otherwise each write
        their own loop over the same file, and one of them would sort
        differently.
        """
        found: _Rows = []
        for anchor, rows in self._read().items():
            for row in rows:
                if isinstance(row, dict):
                    found.append((anchor, MediaBookmark.from_dict(row)))
        return sorted(found, key=lambda pair: (pair[0], pair[1].position_ms))

    def count(self) -> int:
        """How many bookmarks exist across every anchor."""
        return sum(len(rows) for rows in self._read().values() if isinstance(rows, list))

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
