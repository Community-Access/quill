"""**Song Details**: which release a song came from, what year, how long it runs.

Song History has recorded artist and title for a while, which makes it a list of
titles. This is what makes it a history you can *do something with* -- and the
distinction is not academic: "was that the album version?" and "what year is
this?" are the two questions people actually ask about a song they just heard,
and neither is answerable from a broadcast title.

MusicBrainz answers both, with no key and no account. The module that talks to it
(``core/radio/musicbrainz.py``) has existed and been called by nothing; this is
the command that calls it.

Three rules, and they are the reason this is opt-in rather than automatic:

* **Nothing happens until it is asked for.** No enrichment on record, none on
  refresh, none in the background. A history window that quietly issued a
  network request per row would be spending somebody's connection on curiosity
  they did not express.
* **It never blocks playback or the window.** MusicBrainz asks for one request
  per second and the module honours that itself; the call runs on the task
  manager and the window stays live while it waits.
* **It degrades to nothing.** No match, a timeout, a rate limit: the entry keeps
  exactly the artist and title it already had, and the listener is told plainly
  that nothing more is known. An enrichment that can fail loudly is worse than no
  enrichment.
"""

from __future__ import annotations

from typing import Any

NOT_FOUND = "MusicBrainz has nothing more about that song."
NO_SELECTION = "Select a song first."


def describe(song: Any, facts: Any) -> str:
    """One sentence: the song, plus whatever else is known about it."""
    detail = facts.spoken_detail if facts is not None else ""
    heard = song.display() if hasattr(song, "display") else str(song)
    return f"{heard}, {detail}." if detail else NOT_FOUND


def request(host: Any, song: Any, show: Any = None) -> None:
    """Look *song* up, speak what came back, and hand the text to *show*.

    ``host`` is the **frame**, which owns the task manager, Safe Mode and the
    announcement path; ``show`` is the dialog's own "put this in the detail box"
    callback. Injected that way round because the Song History window already
    takes its Background lookup as a callable, and one dialog with two injection
    styles would be a small mess for no gain.
    """
    from quill.core.radio import musicbrainz

    if song is None:
        host._announce(NO_SELECTION)
        return
    if getattr(host, "_safe_mode", False):
        host._announce("Song details are disabled in Safe Mode.")
        return
    task_manager = getattr(host, "_task_manager", None)
    if task_manager is None:
        host._announce("Song details are unavailable right now.")
        return

    host._announce(f"Looking up {song.display()}...")

    def _work(**_kwargs: Any) -> Any:
        return musicbrainz.lookup(song.artist, song.title, safe_mode=False)

    def _ok(_op: str, facts: object) -> None:
        host._wx.CallAfter(_arrived, host, song, facts, show)

    def _failed(_op: str, _error: BaseException) -> None:
        # Deliberately not the error text: a listener asking "what album is
        # this?" is not served by an HTTP message, and the honest answer to a
        # failed optional lookup is that we do not know.
        host._wx.CallAfter(host._announce, NOT_FOUND)

    task_manager.submit("radio-song-facts", _work, on_success=_ok, on_failure=_failed)


def _arrived(host: Any, song: Any, facts: Any, show: Any) -> None:
    said = describe(song, facts)
    if show is not None:
        show(said)
    host._announce(said)
