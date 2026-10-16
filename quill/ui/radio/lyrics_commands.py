"""**Lyrics** in Quill Radio: the words of the song on the air, on request.

Song History has always shaped its clipboard text for "someone pasting into a
lyrics or store search" -- the app imagined the listener leaving to look the
words up somewhere else. This removes the trip: the song the station names is
looked up on LRCLIB (``core/lyrics/lrclib.py``) and its words open in a window
of their own (``ui/media/lyrics_window.py``), as plain text to arrow through.

Plain words only, never timed ones: a stream gives no position within a song,
so a caret following the words would be confidently in the wrong place.

The lookup key is the station's own now-playing title, parsed into artist and
title the same way the What's Playing announcement and Song History parse it
(``core/radio/now_playing.py``). A title with no artist in it is not looked up
-- a search by song name alone answers with somebody else's song as often as
not, and confidently wrong words are worse than none.

Three rules, the same as Song Details (``song_facts.py``):

* **Nothing happens until it is asked for** -- the Lyrics command, or the
  Lyrics button in Song History. No lookup as titles change, none in the
  background, none in Safe Mode.
* **It never blocks playback.** The lookup runs on the task manager.
* **It says plainly what it found**: the words, "no lyrics found", or that the
  song is an instrumental -- never an HTTP message. A listener asking "what are
  the words?" is not served by one.

The window says nothing when it opens: focus lands in the lyrics and the
screen reader reads the title and the text itself (GATE-13).
"""

from __future__ import annotations

from typing import Any

NOTHING_PLAYING = "Nothing is playing, so there is no song to look up."
NO_TITLE = "The station has not said what song is playing."
NO_ARTIST = "The station's title does not name an artist, so its lyrics cannot be looked up."
NO_SELECTION = "Select a song first."
SAFE_MODE = "Lyrics are disabled in Safe Mode."
UNAVAILABLE = "Lyrics are unavailable right now."


def not_found(title: str) -> str:
    return f"No lyrics found for {title}."


def instrumental(title: str) -> str:
    return f"{title} is an instrumental; it has no lyrics."


def lyrics_for_playing(host: Any) -> None:
    """The Lyrics command: look up the song the station is playing now."""
    from quill.core.radio.now_playing import parse_now_playing

    controller = getattr(host, "_radio_controller", None)
    state = getattr(controller, "state", None)
    if getattr(state, "station", None) is None:
        host._announce(NOTHING_PLAYING)
        return
    raw = str(getattr(host, "_radio_track_title", "") or "").strip()
    if not raw:
        host._announce(NO_TITLE)
        return
    now_playing = parse_now_playing(raw)
    request(host, now_playing.artist, now_playing.title)


def lyrics_for_song(host: Any, song: Any) -> None:
    """Song History's Lyrics button: look up a song heard earlier."""
    if song is None:
        host._announce(NO_SELECTION)
        return
    request(host, str(getattr(song, "artist", "") or ""), str(getattr(song, "title", "") or ""))


def request(host: Any, artist: str, title: str) -> None:
    """Look *title* by *artist* up and show the words, or say why not."""
    artist, title = artist.strip(), title.strip()
    if not title:
        host._announce(NO_TITLE)
        return
    if not artist:
        host._announce(NO_ARTIST)
        return
    if getattr(host, "_safe_mode", False):
        host._announce(SAFE_MODE)
        return
    task_manager = getattr(host, "_task_manager", None)
    if task_manager is None:
        host._announce(UNAVAILABLE)
        return

    song = f"{title} by {artist}"
    host._announce(f"Looking up lyrics for {song}...")

    def _work(**_kwargs: Any) -> Any:
        from quill.core.lyrics import lrclib

        return lrclib.search(artist, title)

    def _failed(_op: str, _error: BaseException) -> None:
        # Not the error text: the honest answer to a failed optional lookup is
        # that we do not know the words, and that is the sentence a miss gets.
        host._announce(not_found(title))

    # The task manager delivers both callbacks on the UI thread.
    task_manager.submit(
        "radio-lyrics",
        _work,
        on_success=lambda _op, lyrics: arrived(host, song, title, lyrics),
        on_failure=_failed,
    )


def arrived(host: Any, song: str, title: str, lyrics: Any) -> None:
    """Show what came back: the words, or one sentence saying why there are none."""
    if lyrics is None or not lyrics.text:
        host._announce(
            instrumental(title) if getattr(lyrics, "instrumental", False) else not_found(title)
        )
        return
    window = getattr(host, "_radio_lyrics_window", None)
    if window is not None:
        try:
            window.set_lyrics(song, lyrics)
            window.show()
            return
        except RuntimeError:  # the frame was destroyed under us
            host._radio_lyrics_window = None
    from quill.ui.media.lyrics_window import LyricsWindow

    window = LyricsWindow(
        getattr(host, "frame", None),
        song=song,
        lyrics=lyrics,
        announce=host._announce,
        on_closed=lambda: setattr(host, "_radio_lyrics_window", None),
    )
    host._radio_lyrics_window = window
    window.show()
