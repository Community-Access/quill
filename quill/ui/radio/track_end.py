"""What "this ended" actually means, which is three different things.

Playback reaching its end is one event with three quite different causes, and
answering them in the wrong order gets each of them wrong:

1. **A live stream ended** -- which almost always means the connection dropped,
   not that the broadcast stopped. Worth trying to get back before saying
   anything (``live_reconnect``).
2. **A chapter of a downloaded book ended** -- so the next chapter should start.
   Checked after the reconnect, because a live stream is never a book, and
   before the stop, because reaching the end of chapter four is not the end of
   anything (``book_playback``).
3. **A recording genuinely finished.** Only now is stopping the right answer.

Extracted from ``player_controller`` under GATE-11 when the book case arrived.
The order *is* the logic, which is why it reads better as a list than as three
branches buried in a controller.
"""

from __future__ import annotations

from typing import Any


def handle(controller: Any) -> None:
    """Decide what an end-of-playback means, and act on it."""
    from quill.ui.radio import book_playback, live_reconnect
    from quill.ui.radio.playback_state import RadioPlayerState

    controller._remember_resume_point()
    if live_reconnect.handle_finished(controller):
        return
    if book_playback.handle_finished(controller):
        return
    controller._set_state(RadioPlayerState.STOPPED, message="The stream ended or disconnected.")
