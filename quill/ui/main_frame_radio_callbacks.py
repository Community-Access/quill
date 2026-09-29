"""The radio controller's three one-sentence callbacks into the host.

Sound Enhancements that could not start, an output device that could not be
used, and (2026-09-29, output_device_guard) a device the guard gave back whose
setting must follow. Each is a sentence or a save, nothing more; they left
``main_frame_radio.py`` when the third arrived and that module was at its
GATE-11 ceiling. Mixed into :class:`quill.ui.main_frame_radio.RadioMixin`,
which supplies ``_announce`` and ``_radio_history``.
"""

from __future__ import annotations

from typing import Any

from quill.core.paths import app_data_dir
from quill.core.radio import history as radio_history

__all__ = ["RadioCallbacksMixin"]


class RadioCallbacksMixin:
    """What the controller says through the host, and the one setting it saves."""

    _radio_history: Any

    def _announce(self, text: str, **kwargs: Any) -> None:  # provided by the host
        raise NotImplementedError

    def _on_radio_enhance_error(self, message: str) -> None:
        """Sound Enhancements couldn't start (ffmpeg missing, relay failed);
        playback still proceeds unenhanced, so this is an announcement, not a
        blocking dialog."""
        self._announce(f"Sound Enhancements: {message} Playing without it.")

    def _on_radio_output_device_error(self, message: str) -> None:
        """The chosen device could not be used; playback goes on, so a sentence (#1076)."""
        self._announce(message)

    def _on_radio_output_device_reverted(self, device: str) -> None:
        """output_device_guard gave a device back: save the setting it went back to."""
        self._radio_history.output_device = device
        radio_history.save_history(app_data_dir(), self._radio_history)
