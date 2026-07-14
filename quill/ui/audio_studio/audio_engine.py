"""Audio playback engines for the Audio Studio player.

A tiny engine protocol with the default Windows implementation on
``wx.media.MediaCtrl`` (the WMP backend — no new native dependency). The
protocol mirrors ChapterForge's libmpv engine so an mpv backend can slot in
later (delivered on demand like ffmpeg) without touching the player panel:

- ``load`` begins async loading; ``on_loaded(length_ms)`` fires when ready.
- ``seek`` is absolute milliseconds and never changes the pause state unless
  ``resume`` says so.
- ``on_finished`` fires once when playback reaches the end.
- All calls happen on the UI thread; callbacks arrive on the UI thread.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Protocol

import wx

_log = logging.getLogger(__name__)


class AudioEngine(Protocol):
    """What the player panel needs from a playback backend."""

    def load(self, path: str) -> bool: ...

    def close(self) -> None: ...

    def play(self) -> None: ...

    def pause(self) -> None: ...

    def stop(self) -> None: ...

    def seek(self, ms: int, *, resume: bool | None = None) -> None: ...

    def position_ms(self) -> int: ...

    def length_ms(self) -> int: ...

    def is_playing(self) -> bool: ...

    def set_volume(self, percent: int) -> None: ...

    def set_rate(self, rate: float) -> None: ...


class WxMediaEngine:
    """The default engine: ``wx.media.MediaCtrl`` hidden inside the player panel.

    The control is created on *parent* (never shown — audio only). MP3 and
    M4B/M4A both play through the Windows Media Player backend.
    """

    def __init__(
        self,
        parent: wx.Window,
        *,
        on_loaded: Callable[[int], None],
        on_finished: Callable[[], None],
        on_error: Callable[[str], None],
    ) -> None:
        import wx.media

        self._on_loaded = on_loaded
        self._on_finished = on_finished
        self._on_error = on_error
        self._loaded = False
        self._pending_path = ""
        self._media = wx.media.MediaCtrl(parent, style=0, szBackend=wx.media.MEDIABACKEND_WMP10)
        if not self._media.GetHandle():  # pragma: no cover - backend fallback path
            self._media = wx.media.MediaCtrl(parent)
        self._media.Hide()
        parent.Bind(wx.media.EVT_MEDIA_LOADED, self._on_media_loaded, self._media)
        parent.Bind(wx.media.EVT_MEDIA_FINISHED, self._on_media_finished, self._media)

    # -- engine protocol -------------------------------------------------------

    def load(self, path: str) -> bool:
        self._loaded = False
        self._pending_path = path
        try:
            if not self._media.Load(path):
                self._on_error("This file could not be loaded for playback.")
                return False
        except Exception:  # noqa: BLE001 - backend quirks must not crash the studio
            _log.exception("MediaCtrl.Load failed")
            self._on_error("This file could not be loaded for playback.")
            return False
        return True

    def close(self) -> None:
        try:
            self._media.Stop()
        except Exception:  # noqa: BLE001
            pass
        self._loaded = False

    def play(self) -> None:
        if self._loaded:
            self._media.Play()

    def pause(self) -> None:
        if self._loaded:
            self._media.Pause()

    def stop(self) -> None:
        if self._loaded:
            self._media.Pause()
            self._media.Seek(0)

    def seek(self, ms: int, *, resume: bool | None = None) -> None:
        if not self._loaded:
            return
        was_playing = self.is_playing()
        self._media.Seek(max(0, int(ms)))
        should_play = was_playing if resume is None else resume
        if should_play:
            self._media.Play()
        else:
            self._media.Pause()

    def position_ms(self) -> int:
        try:
            return int(self._media.Tell()) if self._loaded else 0
        except Exception:  # noqa: BLE001
            return 0

    def length_ms(self) -> int:
        try:
            return int(self._media.Length()) if self._loaded else 0
        except Exception:  # noqa: BLE001
            return 0

    def is_playing(self) -> bool:
        import wx.media

        try:
            return bool(self._loaded and self._media.GetState() == wx.media.MEDIASTATE_PLAYING)
        except Exception:  # noqa: BLE001
            return False

    def set_volume(self, percent: int) -> None:
        try:
            self._media.SetVolume(max(0, min(100, int(percent))) / 100.0)
        except Exception:  # noqa: BLE001
            pass

    def set_rate(self, rate: float) -> None:
        """Playback speed (1.0 = normal); the WMP backend preserves pitch."""
        try:
            self._media.SetPlaybackRate(max(0.25, min(4.0, float(rate))))
        except Exception:  # noqa: BLE001
            pass

    # -- events ---------------------------------------------------------------

    def _on_media_loaded(self, _evt: wx.Event) -> None:
        self._loaded = True
        self._media.Pause()
        self._on_loaded(self.length_ms())

    def _on_media_finished(self, _evt: wx.Event) -> None:
        self._on_finished()


def preferred_backend() -> str:
    """``"mpv"`` when a libmpv DLL is present, else ``"wx"`` (the default)."""
    from quill.ui.audio_studio.mpv_engine import find_libmpv

    try:
        return "mpv" if find_libmpv() is not None else "wx"
    except Exception:  # noqa: BLE001 - discovery must never block playback
        return "wx"


def create_engine(
    parent: wx.Window,
    *,
    on_loaded: Callable[[int], None],
    on_finished: Callable[[], None],
    on_error: Callable[[str], None],
) -> AudioEngine | None:
    """The best available engine for this machine, or None with the error spoken.

    libmpv (gapless, exact seeking, wide format coverage) is preferred when its
    DLL is installed — the on-demand download, a ``QUILL_LIBMPV`` override, or
    a copy beside the executable. Any mpv failure falls back to wx.media so a
    broken DLL can never take playback away.
    """
    if preferred_backend() == "mpv":
        try:
            from quill.ui.audio_studio.mpv_engine import MpvAudioEngine

            return MpvAudioEngine(
                parent, on_loaded=on_loaded, on_finished=on_finished, on_error=on_error
            )
        except Exception:  # noqa: BLE001 - fall back to the zero-dependency backend
            _log.exception("libmpv found but unusable; falling back to wx.media")
    try:
        return WxMediaEngine(
            parent, on_loaded=on_loaded, on_finished=on_finished, on_error=on_error
        )
    except Exception:  # noqa: BLE001 - no media backend on this machine
        _log.exception("No audio playback backend available")
        on_error("Audio playback is not available on this computer.")
        return None
