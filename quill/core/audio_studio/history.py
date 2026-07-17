"""Recently played audiobooks, persisted as atomic JSON (Phase 2 port-in).

Backs the standalone Studio's Recently Played submenu and its optional
resume-on-launch behavior: a "what did I recently play" log, most recent
first, capped, de-duplicated by book path. Mirrors
``quill/core/podcasts/history.py`` (and ``quill/core/radio/history.py``),
swapping the episode identity for a book path plus a resume position
(``position_ms`` / ``chapter``) so the host can jump back to where playback
stopped. wx-free, strict-typed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.storage import write_json_atomic

_FILE_NAME = "audio_studio_history.json"
_MAX_ENTRIES = 15


@dataclass(slots=True)
class PlayedBook:
    """One recently played book, with a resume position."""

    path: str
    title: str
    position_ms: int = 0
    chapter: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "title": self.title,
            "position_ms": self.position_ms,
            "chapter": self.chapter,
        }

    @staticmethod
    def from_dict(data: object) -> PlayedBook | None:
        if not isinstance(data, dict):
            return None
        path = str(data.get("path", ""))
        if not path:
            return None
        return PlayedBook(
            path=path,
            title=str(data.get("title", "")),
            position_ms=int(data.get("position_ms", 0) or 0),
            chapter=int(data.get("chapter", 0) or 0),
        )


@dataclass(slots=True)
class AudioStudioHistory:
    """Recently played books plus the resume-on-launch preference."""

    books: list[PlayedBook] = field(default_factory=list)
    #: On by default -- the Studio's common case is "pick up where I left off".
    resume_on_launch: bool = True

    def record(
        self, path: str, *, title: str, position_ms: int = 0, chapter: int = 0
    ) -> None:
        """Note that this book just started/continued playing; moves to front."""
        if not path:
            return
        self.books = [b for b in self.books if b.path != path]
        self.books.insert(
            0,
            PlayedBook(
                path=path,
                title=title,
                position_ms=position_ms,
                chapter=chapter,
            ),
        )
        del self.books[_MAX_ENTRIES:]

    @property
    def last_played(self) -> PlayedBook | None:
        return self.books[0] if self.books else None


def _store_path(data_dir: Path) -> Path:
    return data_dir / _FILE_NAME


def load_history(data_dir: Path) -> AudioStudioHistory:
    """Read history (an absent or broken file reads as empty, resume on)."""
    history = AudioStudioHistory()
    try:
        raw = json.loads(_store_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return history
    if isinstance(raw, dict):
        history.resume_on_launch = bool(raw.get("resume_on_launch", True))
        entries = raw.get("books")
        for entry in entries if isinstance(entries, list) else []:
            played = PlayedBook.from_dict(entry)
            if played is not None:
                history.books.append(played)
        del history.books[_MAX_ENTRIES:]
    return history


def save_history(data_dir: Path, history: AudioStudioHistory) -> None:
    """Persist history atomically (temp file + ``os.replace``)."""
    write_json_atomic(
        _store_path(data_dir),
        {
            "resume_on_launch": history.resume_on_launch,
            "books": [b.to_dict() for b in history.books],
        },
    )