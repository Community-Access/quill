"""Start and Stop Watching for Changes in Quill Radio (codex.md decision 25).

**Start Watching for Changes** (Ctrl+F9, Video menu) watches the picture of the
video playing, taken on this computer the way Take a Snapshot takes it, without
captions. It looks every few seconds; when the picture changes, OCR on this
computer says how if it can (a new slide, a new caption on screen), and only
otherwise is the AI in use asked, at most once a minute and 30 times a watch.
**Stop Watching for Changes** (Ctrl+Shift+F9) ends it; so does hiding the
video, and so does closing Quill Radio. No sound and no video file ever leaves.

The timer, the worker and the words are the shared
:mod:`quill.ui.change_watch_controller`; the rules are
:mod:`quill.core.ai.change_watch`.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

__all__ = ["RadioWatchMixin"]

_NO_VIDEO = "There is no picture to watch. Show the video first."
_VIDEO_GONE = "Stopped watching: the video is no longer showing."


class RadioWatchMixin:
    """The two watch commands. Mixed in through ``RadioAiMixin``."""

    def cmd_radio_watch_start(self) -> None:
        """Start Watching for Changes (Ctrl+F9): the video picture, said and brailled."""
        from quill.ui.change_watch_controller import controller_for
        from quill.ui.radio import video_commands

        engine = video_commands._engine(self)

        def showing() -> bool:
            return engine is not None and getattr(self, "_video_window", None) is not None

        controller_for(self).request_start(
            subject="the video",
            grab=lambda: _grab(engine),
            refusal=lambda: "" if showing() else _NO_VIDEO,
            available=lambda: "" if showing() else _VIDEO_GONE,
            stop_key=self._radio_watch_stop_key(),
        )

    def cmd_radio_watch_stop(self) -> None:
        """Stop Watching for Changes (Ctrl+Shift+F9)."""
        from quill.ui.change_watch_controller import controller_for

        controller_for(self).stop()

    def _radio_watch_stop_key(self) -> str:
        try:
            return str(self._binding_for("radio.ai_watch_stop") or "")  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - no keymap names no key
            return ""


def _grab(engine: Any) -> bytes | None:
    """One frame of the video, through the snapshot path, not kept."""
    if engine is None:
        return None
    folder = Path(tempfile.mkdtemp(prefix="quill-radio-watch-"))
    try:
        shot = folder / "frame.png"
        if not engine.take_snapshot(str(shot)) or not shot.is_file():
            return None
        return shot.read_bytes()
    finally:
        shutil.rmtree(folder, ignore_errors=True)
