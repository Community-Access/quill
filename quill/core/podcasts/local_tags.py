"""What a local audio file says about itself (ear.md R11).

Add Local Podcast named every episode from its **filename**, so a folder of
``track07.mp3`` became a show of episodes called "Track07" while the files
themselves carried a title, an artist and a duration all along. The filename is
the fallback, not the answer.

Read here, from tags: title, artist, album and duration. Nothing is written --
the listener's file is theirs, and Cast has no business editing it to make its own
list tidier.

**Optional by design.** ``mutagen`` is an extra (``pip install quill[mp3]``), so
every function answers with empty values when it is absent rather than raising:
a copy of Cast without it imports files exactly as before, named from filenames,
and nothing anywhere has to know why. The same is true of a file whose tags are
corrupt, which is common in exactly the archives people import.

Embedded **chapters** are not read here. Cast already reads ID3 chapter frames
through ``chapter_sources``' ``file`` tier, so an imported MP3's chapters arrive
by the route every other episode's do; adding a second reader would be a second
answer to one question.

wx-free, strict-typed. No network.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

__all__ = ["Tags", "read_tags"]


@dataclass(frozen=True, slots=True)
class Tags:
    """What a file said about itself. Every field may be empty or zero."""

    title: str = ""
    artist: str = ""
    album: str = ""
    duration_seconds: int = 0

    @property
    def is_empty(self) -> bool:
        return not (self.title or self.artist or self.album or self.duration_seconds)


def _first(value: object) -> str:
    """One string from whatever a tag library hands back.

    Tag values are lists more often than not, and an empty list is a tag that is
    present and says nothing -- which must read as absent, not as "[]".
    """
    if isinstance(value, (list, tuple)):
        return str(value[0]).strip() if value else ""
    return str(value or "").strip()


def read_tags(path: Path | str) -> Tags:
    """*path*'s own title, artist, album and duration. Never raises.

    A file that cannot be read, has no tags, or is not audio at all answers with
    an empty :class:`Tags`, which the caller treats exactly as it used to treat
    every file: name it from the filename.
    """
    try:
        import mutagen
    except Exception:  # noqa: BLE001 - the extra is not installed; that is fine
        return Tags()
    try:
        opened = mutagen.File(str(path), easy=True)
    except Exception:  # noqa: BLE001 - corrupt tags are common in old archives
        return Tags()
    if opened is None:
        return Tags()
    tags = getattr(opened, "tags", None) or {}
    info = getattr(opened, "info", None)
    seconds = 0
    length = getattr(info, "length", 0) or 0
    try:
        seconds = max(0, int(round(float(length))))
    except (TypeError, ValueError):
        seconds = 0
    return Tags(
        title=_first(tags.get("title") if hasattr(tags, "get") else ""),
        artist=_first(tags.get("artist") if hasattr(tags, "get") else ""),
        album=_first(tags.get("album") if hasattr(tags, "get") else ""),
        duration_seconds=seconds,
    )
