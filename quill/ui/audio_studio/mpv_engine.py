"""libmpv playback backend for the Audio Studio player (optional, on demand).

The player's default backend is ``wx.media`` (WMP — zero new dependencies).
This module adds the ChapterForge-grade alternative the ``AudioEngine``
protocol was shaped for: **libmpv**, which brings gapless playback, exact
seeking, and wide format coverage — chapter navigation that feels instant on
8-hour books.

libmpv is *not* bundled. :func:`find_libmpv` looks for ``libmpv-2.dll`` in,
in order: the ``QUILL_LIBMPV`` environment override (a file or a folder),
the mpv engine pack folder (``<app data>/engine-packs/mpv`` — where the
on-demand assets-v1 download lands once that asset is hosted), and next to
the running executable. No DLL found simply means the player stays on the
wx.media backend; nothing else changes.

The binding is a deliberately small ctypes wrapper over the libmpv client
API — create, initialize, command, get/set property, destroy — with all
calls on the UI thread and a ``wx.Timer`` polling ``duration`` /
``eof-reached``, so no mpv event thread ever touches wx.
"""

from __future__ import annotations

import ctypes
import logging
import os
import sys
from collections.abc import Callable
from pathlib import Path

import wx

_log = logging.getLogger(__name__)

_DLL_NAMES = ("libmpv-2.dll", "mpv-2.dll", "libmpv.dll")
_POLL_MS = 200

# libmpv client API constants (client.h).
_MPV_FORMAT_FLAG = 3
_MPV_FORMAT_DOUBLE = 5


def mpv_pack_dir() -> Path:
    """Where the on-demand mpv component installs (assets-v1 flow)."""
    from quill.core.speech.engine_install import engine_packs_dir

    return engine_packs_dir() / "mpv"


def find_libmpv() -> Path | None:
    """The libmpv DLL to use, or None (= stay on the wx.media backend)."""
    override = os.environ.get("QUILL_LIBMPV", "").strip()
    candidates: list[Path] = []
    if override:
        path = Path(override)
        candidates += [path] if path.suffix else [path / name for name in _DLL_NAMES]
    try:
        pack = mpv_pack_dir()
        candidates += [pack / name for name in _DLL_NAMES]
    except Exception:  # noqa: BLE001 - no app data dir in odd harnesses
        pass
    exe_dir = Path(sys.executable).parent
    candidates += [exe_dir / name for name in _DLL_NAMES]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


class _MpvClient:
    """Minimal ctypes binding: exactly what the engine protocol needs."""

    def __init__(self, dll_path: Path) -> None:
        lib = ctypes.CDLL(str(dll_path))
        lib.mpv_create.restype = ctypes.c_void_p
        lib.mpv_create.argtypes = []
        lib.mpv_initialize.restype = ctypes.c_int
        lib.mpv_initialize.argtypes = [ctypes.c_void_p]
        lib.mpv_terminate_destroy.restype = None
        lib.mpv_terminate_destroy.argtypes = [ctypes.c_void_p]
        lib.mpv_command.restype = ctypes.c_int
        lib.mpv_command.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_char_p)]
        lib.mpv_set_option_string.restype = ctypes.c_int
        lib.mpv_set_option_string.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_char_p,
        ]
        lib.mpv_set_property_string.restype = ctypes.c_int
        lib.mpv_set_property_string.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_char_p,
        ]
        lib.mpv_get_property.restype = ctypes.c_int
        lib.mpv_get_property.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_void_p,
        ]
        self._lib = lib
        handle = lib.mpv_create()
        if not handle:
            raise OSError("mpv_create failed")
        self._handle = ctypes.c_void_p(handle)
        # Audio only, no window, no key bindings; keep-open so end-of-file is a
        # queryable state instead of an unload; idle so the core waits for us.
        for option, value in (
            ("vid", "no"),
            ("audio-display", "no"),
            ("terminal", "no"),
            ("input-default-bindings", "no"),
            ("osc", "no"),
            ("idle", "yes"),
            ("keep-open", "yes"),
        ):
            lib.mpv_set_option_string(self._handle, option.encode(), value.encode())
        if lib.mpv_initialize(self._handle) < 0:
            lib.mpv_terminate_destroy(self._handle)
            raise OSError("mpv_initialize failed")

    def close(self) -> None:
        if self._handle:
            self._lib.mpv_terminate_destroy(self._handle)
            self._handle = ctypes.c_void_p(None)

    def command(self, *args: str) -> None:
        encoded = [a.encode("utf-8") for a in args]
        array = (ctypes.c_char_p * (len(encoded) + 1))(*encoded, None)
        self._lib.mpv_command(self._handle, array)

    def set_str(self, name: str, value: str) -> None:
        self._lib.mpv_set_property_string(self._handle, name.encode(), value.encode())

    def get_double(self, name: str) -> float | None:
        out = ctypes.c_double(0.0)
        status = self._lib.mpv_get_property(
            self._handle, name.encode(), _MPV_FORMAT_DOUBLE, ctypes.byref(out)
        )
        return float(out.value) if status >= 0 else None

    def get_flag(self, name: str) -> bool | None:
        out = ctypes.c_int(0)
        status = self._lib.mpv_get_property(
            self._handle, name.encode(), _MPV_FORMAT_FLAG, ctypes.byref(out)
        )
        return bool(out.value) if status >= 0 else None


class MpvAudioEngine:
    """The libmpv implementation of the player's ``AudioEngine`` protocol.

    Same contract as ``WxMediaEngine``: all calls on the UI thread, callbacks
    on the UI thread (driven by a polling timer, never an mpv event thread).
    """

    def __init__(
        self,
        parent: wx.Window,
        *,
        on_loaded: Callable[[int], None],
        on_finished: Callable[[], None],
        on_error: Callable[[str], None],
        dll_path: Path | None = None,
    ) -> None:
        path = dll_path or find_libmpv()
        if path is None:
            raise OSError("libmpv is not installed")
        self._mpv = _MpvClient(path)
        self._on_loaded = on_loaded
        self._on_finished = on_finished
        self._on_error = on_error
        self._loaded = False
        self._eof_fired = False
        self._length_ms = 0
        self._timer = wx.Timer(parent)
        parent.Bind(wx.EVT_TIMER, self._on_poll, self._timer)
        parent.Bind(wx.EVT_WINDOW_DESTROY, self._on_parent_destroyed)

    # -- engine protocol -------------------------------------------------------

    def load(self, path: str) -> bool:
        self._loaded = False
        self._eof_fired = False
        self._length_ms = 0
        try:
            self._mpv.set_str("pause", "yes")
            self._mpv.command("loadfile", path, "replace")
        except Exception:  # noqa: BLE001 - a bad file must not crash the studio
            _log.exception("mpv loadfile failed")
            self._on_error("This file could not be loaded for playback.")
            return False
        self._timer.Start(_POLL_MS)
        return True

    def close(self) -> None:
        try:
            self._timer.Stop()
        except Exception:  # noqa: BLE001
            pass
        self._loaded = False
        self._mpv.close()

    def play(self) -> None:
        if self._loaded:
            self._mpv.set_str("pause", "no")

    def pause(self) -> None:
        if self._loaded:
            self._mpv.set_str("pause", "yes")

    def stop(self) -> None:
        if self._loaded:
            self._mpv.set_str("pause", "yes")
            self.seek(0, resume=False)

    def seek(self, ms: int, *, resume: bool | None = None) -> None:
        if not self._loaded:
            return
        was_playing = self.is_playing()
        self._eof_fired = False
        self._mpv.command("seek", f"{max(0, int(ms)) / 1000.0:.3f}", "absolute+exact")
        should_play = was_playing if resume is None else resume
        self._mpv.set_str("pause", "no" if should_play else "yes")

    def position_ms(self) -> int:
        if not self._loaded:
            return 0
        value = self._mpv.get_double("time-pos")
        return int(value * 1000) if value is not None and value > 0 else 0

    def length_ms(self) -> int:
        return self._length_ms if self._loaded else 0

    def is_playing(self) -> bool:
        if not self._loaded:
            return False
        paused = self._mpv.get_flag("pause")
        return paused is False

    def set_volume(self, percent: int) -> None:
        self._mpv.set_str("volume", str(max(0, min(100, int(percent)))))

    def set_rate(self, rate: float) -> None:
        """Playback speed (1.0 = normal); mpv's scaletempo keeps the pitch."""
        self._mpv.set_str("speed", f"{max(0.25, min(4.0, float(rate))):.2f}")

    # -- polling ---------------------------------------------------------------

    def _on_poll(self, _evt: wx.TimerEvent) -> None:
        try:
            if not self._loaded:
                duration = self._mpv.get_double("duration")
                if duration is not None and duration > 0:
                    self._loaded = True
                    self._length_ms = int(duration * 1000)
                    self._mpv.set_str("pause", "yes")
                    self._on_loaded(self._length_ms)
                return
            if not self._eof_fired and self._mpv.get_flag("eof-reached"):
                self._eof_fired = True
                self._on_finished()
        except Exception:  # noqa: BLE001 - polling must never take the app down
            _log.exception("mpv poll failed")
            self._timer.Stop()

    def _on_parent_destroyed(self, evt: wx.WindowDestroyEvent) -> None:
        evt.Skip()
        self.close()
