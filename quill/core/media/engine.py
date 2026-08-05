"""The core-side playback engine protocol.

The controller (pure ``quill.core``, wx-free) depends on this protocol rather
than on the wx engines in ``quill/ui/audio/``. The existing ``WxMediaEngine`` and
``MpvAudioEngine`` already satisfy this shape structurally, so the UI passes one
straight in; tests pass a fake. Keeping the protocol here preserves the
core-cannot-import-ui boundary.

Method names mirror ``quill.ui.audio.audio_engine.AudioEngine`` exactly.
"""

from __future__ import annotations

from typing import Protocol


class PlaybackEngine(Protocol):
    """What :class:`~quill.core.media.controller.MediaController` needs from a backend."""

    def load(self, path: str) -> bool: ...

    def play(self) -> None: ...

    def pause(self) -> None: ...

    def stop(self) -> None: ...

    def seek(self, ms: int, *, resume: bool | None = None) -> None: ...

    def position_ms(self) -> int: ...

    def length_ms(self) -> int: ...

    def is_playing(self) -> bool: ...

    def set_volume(self, percent: int) -> None: ...

    def set_rate(self, rate: float) -> None: ...


__all__ = ["PlaybackEngine"]
