"""Whether a playlist item's audio is still there, said in words (FUX-13).

A multi-file DAISY book or a folder opened as a book keeps a playlist of file
paths. When one of those files has been moved or deleted since the book was
opened, Media Player used to load it anyway and write "Playing <title>" on the
status bar, which was false: nothing played. A LibriVox search result with no
audio read like every other result until Play said "That book has no playable
audio."

Both now say so where they are read: the status bar names the item, says its
audio file is missing and what to do, and the LibriVox row carries "no audio
to play". A failure is also said, once, because it answers a key the person
pressed or replaces the "Next: <title>" that auto-advance would have said; a
success stays on the status bar. Kept out of ``player.py`` under GATE-11, and
wx-free so the wording is tested without a window.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

#: The row suffix for a LibriVox result that has no recording yet.
NO_AUDIO = "no audio to play"


def is_remote(address: str) -> bool:
    """Whether *address* is a stream rather than a file on this computer."""
    return "://" in address and not address.lower().startswith("file:")


def payload_path(payload: tuple[Any, ...]) -> str:
    """The audio address a playlist payload plays, or "" for a seek."""
    kind = payload[0]
    if kind == "load":
        return str(payload[1])
    if kind == "track":
        return str(payload[1][0])
    return ""


def missing_sentence(title: str) -> str:
    """What the status bar and the player say for an item whose file is gone."""
    return f"{title}: audio file missing. If you moved the book, open it again from its new folder."


def play_payload(
    player: Any, payload: tuple[Any, ...], title: str, *, autoplay: bool
) -> tuple[bool, str]:
    """Load one playlist item; answer whether it loaded, and its status line.

    A local file that is no longer on disk is not handed to the player; a
    load the player refuses says "Could not play" rather than "Playing". The
    caller says a failure aloud, because the person pressed a key or was
    listening for the next track, and writes a success to the status bar only.
    """
    kind = payload[0]
    address = payload_path(payload)
    if address and not is_remote(address) and not Path(address).is_file():
        return False, missing_sentence(title)
    loaded: object = True
    if kind == "load":
        loaded = player.load(address, [], resume_ms=0, autoplay=autoplay)
    elif kind == "track":
        loaded = player.load(address, [], resume_ms=int(payload[1][1]), autoplay=autoplay)
    if loaded is False:
        return False, f"Could not play {title}."
    return True, ("Playing " if autoplay else "Loaded ") + title


def librivox_row(book: Any) -> str:
    """One LibriVox search result as it reads, with "no audio to play" when so."""
    label = f"{book.title} - {book.authors}" if book.authors else book.title
    return label if book.has_audio else f"{label}, {NO_AUDIO}"
