"""Playing a downloaded book: one chapter ends, the next begins.

A folder of forty files is not a book unless it plays like one. Quill Radio
could already play any single downloaded file; what it could not do was get to
chapter five without somebody going back to a list and choosing it -- which is
the difference between a book and forty recordings that happen to be adjacent.

So: when a chapter ends, the next one starts. That is the whole feature, and the
rules around it are what stop it being annoying.

* **Only inside the downloads folder.** A recording that ends is a recording
  that ended; auto-advancing something that merely happens to be a file would be
  Quill Radio deciding what somebody meant.
* **Only when it ended by itself.** Stopping deliberately, or choosing another
  station, must never start something new -- an app that plays a thing you did
  not ask for at the moment you asked it to stop is the most annoying kind.
* **The end of a book is an event.** "That was the last chapter of Middlemarch"
  rather than silence, which is indistinguishable from a fault.
* **Each chapter announces itself, briefly.** Position first: "4 of 40" is what
  somebody moving through a book is tracking, and the title second.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _announce(host: Any, message: str) -> None:
    announce = getattr(host, "_announce", None)
    if callable(announce) and message:
        announce(message)


def _books_root(host: Any) -> Path:
    from quill.core.paths import app_data_dir
    from quill.core.radio import download_prefs

    prefs = getattr(host, "_download_prefs", None) or download_prefs.load(app_data_dir())
    return download_prefs.resolved_root(prefs) / download_prefs.FOLDER_BOOKS


def local_path_of(station: Any) -> Path | None:
    """The file a station is, when it is one at all.

    A downloaded chapter is played as an ordinary station whose address is a
    path, so this is the test for "is this a file on this machine".
    """
    url = str(getattr(station, "stream_url", "") or "")
    if not url or url.lower().startswith(("http://", "https://")):
        return None
    path = Path(url)
    try:
        return path if path.is_file() else None
    except OSError:
        return None


def handle_finished(host: Any) -> bool:
    """A track ended. Start the next chapter if it was part of a book.

    Returns True when playback was handed on, so the caller stops rather than
    announcing an end that has not happened.
    """
    from quill.core.radio import downloaded_books

    state = getattr(host, "_state", None) or getattr(host, "state", None)
    station = getattr(state, "station", None)
    current = local_path_of(station)
    if current is None:
        return False

    book = downloaded_books.book_for(current, _books_root(host))
    if book is None:
        return False

    following = downloaded_books.next_chapter(book, current)
    if following is None:
        # The end of a book is worth saying. Silence at the end of a
        # fourteen-hour listen is indistinguishable from something breaking.
        _announce(host, f"That was the last chapter of {book.title}.")
        return False

    if not play_chapter(host, book, following):
        return False
    _announce(host, following.spoken())
    return True


def play_chapter(host: Any, book: Any, chapter: Any) -> bool:
    """Play one chapter through the ordinary station path.

    An ordinary station, deliberately: resume, Sound Enhancements, the Winamp
    keys and Continue Listening all already work on one, and a second playback
    path would have to earn every one of them again.
    """
    from quill.core.radio.models import RadioStation

    controller = getattr(host, "_radio_controller", None) or getattr(host, "_controller", None)
    if controller is None:
        return False
    station = RadioStation(
        name=f"{book.title} -- {chapter.title}",
        stream_url=str(chapter.path),
        source="Downloaded",
        is_recording=True,
    )
    try:
        controller.play_station(station)
    except Exception:  # noqa: BLE001 - reported by the caller, never raised at a listener
        return False
    return True


def play_book(host: Any, book: Any, *, start: int = 0) -> bool:
    """Start a book at a chapter -- the first by default."""
    chapter = book.chapter_at(start)
    if chapter is None:
        _announce(host, f"There is nothing in {book.title} to play.")
        return False
    if not play_chapter(host, book, chapter):
        return False
    _announce(host, f"{book.title}. {chapter.spoken()}.")
    return True
