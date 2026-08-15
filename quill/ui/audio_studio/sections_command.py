"""**Copy Sections...**: the command that opens the section collector.

Kept out of ``apps/studio.py``, which is at its GATE-11 ceiling, and out of the
dialog, which should not have to know how Audio Studio finds the file that is
playing or how it plays a range.

The one interesting decision is the preview. There is no "play from here to
there" in the player, and adding a general one would mean a stop timer racing a
seek. Instead the preview seeks to the start and lets the listener stop when they
have heard enough -- announced as exactly that, because a preview that claimed to
stop at the end mark and did not would be worse than one that never promised to.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

NOTHING_PLAYING = (
    "Open or play an audio file first -- Copy Sections works on the file you are listening to."
)


def open_copy_sections(host: Any) -> None:
    """Open **Copy Sections...** for whatever Audio Studio currently has loaded."""
    source = _current_file(host)
    if source is None:
        host._announce(NOTHING_PLAYING)
        return

    from quill.ui.audio_studio.sections_dialog import CopySectionsDialog

    player = getattr(host, "_player", None)

    def _playhead() -> int:
        return int(player.playhead_ms()) if player is not None else 0

    def _play_range(start_ms: int, _end_ms: int) -> None:
        # Seek and play. Deliberately not a timed stop: a timer racing a seek
        # is the sort of thing that works on a fast machine and stutters on a
        # slow one, and a preview that stops in the wrong place is worse than
        # one that lets you stop it yourself.
        if player is None:
            return
        player.seek_to(int(start_ms))
        player.play()

    dialog = CopySectionsDialog(
        getattr(host, "frame", None),
        source=source,
        playhead_ms=_playhead,
        play_range=_play_range if player is not None else None,
        announce=host._announce,
        show_modal_dialog=getattr(host, "_show_modal_dialog", None),
    )
    dialog.show()


def _current_file(host: Any) -> Path | None:
    """The audio file Audio Studio is working on, or ``None``."""
    for attribute in ("_current_audio_path", "_current_book_path", "_loaded_path"):
        value = getattr(host, attribute, None)
        if value:
            path = Path(str(value))
            if path.exists():
                return path
    player = getattr(host, "_player", None)
    value = getattr(player, "source_path", None) if player is not None else None
    if value:
        path = Path(str(value))
        if path.exists():
            return path
    return None
