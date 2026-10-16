"""**Lyrics** in Quill Media Player: the timed words of the file that is playing.

The half of the lyrics feature that can follow the music. Quill Radio has no
position within a song, so it gets plain words; a file has a real playhead, so
here the LRCLIB answer's timed lines (``syncedLyrics``) mean what they say:
the Lyrics window shows the line being sung in **Current line** and, with
**Follow playback** on, keeps the cursor in the lyrics on it
(``quill/ui/media/lyrics_window.py``). Nothing is spoken as the lines change;
**Say Current Line** speaks it when asked.

The lookup key is the file's own tags -- artist, title, album and length -- so
LRCLIB's exact lookup finds the right recording rather than a live version.
A file with no tags falls back to an ``Artist - Title`` file name, and a name
that is not shaped like one is not guessed at.

Extracted from ``quill.apps.player``, which is at its GATE-11 ceiling. Same
rules as Radio's: only on request, never in Safe Mode, on the task manager, and
one plain sentence when there are no words.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = ["current_audio_path", "lookup_key", "open_lyrics"]

NOTHING_OPEN = "Open a song first."
NO_TAGS = "This file does not say its artist and title, so its lyrics cannot be looked up."
SAFE_MODE = "Lyrics are disabled in Safe Mode."
UNAVAILABLE = "Lyrics are unavailable right now."


def current_audio_path(frame: Any) -> Path | None:
    """The local file playing now: the current track of a multi-file book, else the book."""
    playlist = getattr(frame, "_playlist", None) or []
    index = getattr(frame, "_playlist_index", -1)
    if 0 <= index < len(playlist):
        payload = playlist[index][1]
        kind = payload[0] if payload else ""
        if kind == "track":
            return Path(str(payload[1][0]))
        if kind == "load" and "://" not in str(payload[1]):
            return Path(str(payload[1]))
    book = getattr(frame, "_book_path", None)
    return Path(book) if book is not None else None


def lookup_key(path: Path, length_ms: int = 0) -> tuple[str, str, str, float]:
    """``(artist, title, album, seconds)`` for *path*: its tags, else its name."""
    from quill.core.podcasts.local_tags import read_tags

    tags = read_tags(path)
    artist, title, album = tags.artist, tags.title, tags.album
    seconds = float(tags.duration_seconds or 0) or max(0, length_ms) / 1000
    if not (artist and title):
        stem_artist, sep, stem_title = path.stem.partition(" - ")
        if sep and stem_artist.strip() and stem_title.strip():
            artist, title = artist or stem_artist.strip(), title or stem_title.strip()
    return artist, title, album, seconds


def open_lyrics(frame: Any) -> None:
    """Playback > Lyrics: look the playing file's words up and show them."""
    path = current_audio_path(frame)
    if path is None:
        frame._announce(NOTHING_OPEN)
        return
    if getattr(frame, "_safe_mode", False):
        frame._announce(SAFE_MODE)
        return
    task_manager = getattr(frame, "_task_manager", None)
    if task_manager is None:
        frame._announce(UNAVAILABLE)
        return
    player = getattr(frame, "_player", None)
    length_ms = int(player.length_ms()) if player is not None else 0
    artist, title, album, seconds = lookup_key(path, length_ms)
    if not (artist and title):
        frame._announce(NO_TAGS)
        return
    song = f"{title} by {artist}"
    frame._announce(f"Looking up lyrics for {song}...")

    def _work(**_kwargs: Any) -> Any:
        from quill.core.lyrics import lrclib

        return lrclib.get_exact(artist, title, album, seconds)

    task_manager.submit(
        "player-lyrics",
        _work,
        on_success=lambda _op, lyrics: arrived(frame, song, title, lyrics),
        # Not the error text: a failed optional lookup means we do not know.
        on_failure=lambda _op, _error: frame._announce(f"No lyrics found for {title}."),
    )


def arrived(frame: Any, song: str, title: str, lyrics: Any) -> None:
    """Show the words, or say in one sentence why there are none."""
    if lyrics is None or not lyrics.text:
        if getattr(lyrics, "instrumental", False):
            frame._announce(f"{title} is an instrumental; it has no lyrics.")
        else:
            frame._announce(f"No lyrics found for {title}.")
        return
    player = getattr(frame, "_player", None)
    window = getattr(frame, "_lyrics_window", None)
    if window is not None:
        try:
            window.set_lyrics(song, lyrics)
            window.show()
            return
        except RuntimeError:  # the frame was destroyed under us
            frame._lyrics_window = None
    from quill.ui.media.lyrics_window import LyricsWindow

    window = LyricsWindow(
        frame.frame,
        song=song,
        lyrics=lyrics,
        position_ms=(lambda: int(player.playhead_ms())) if player is not None else (lambda: 0),
        announce=frame._announce,
        on_closed=lambda: setattr(frame, "_lyrics_window", None),
    )
    frame._lyrics_window = window
    window.show()
