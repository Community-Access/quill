"""The Windows Media engine that can be pointed at a sound card.

Windows has two media stacks an app can play through. The classic one --
Windows Media Player's ActiveX control and DirectShow, which is what
``wx.media.MediaCtrl`` wraps in :class:`quill.ui.audio.audio_engine.WxMediaEngine`
-- plays on whatever device Windows assigns the process and offers no way to
choose another. The modern one, ``Windows.Media.Playback.MediaPlayer``
(Media Foundation underneath; the stack the Media Player app itself uses), has
an ``AudioDevice`` property that can be set before *and during* playback. It
is documented, it ships inside Windows 10 and 11, and the thin ``winrt-*``
projection wheels that reach it are the same family QUILL's Windows OCR
already uses (``quill/platform/windows/windows_ocr.py``).

So this is "Windows Media" for the QuillVille family from 3.0.5 on: the same
``AudioEngine`` protocol as the wx.media and libmpv backends, plus
:meth:`WinRtMediaEngine.set_audio_device` taking the same ``wasapi/{guid}``
names libmpv uses -- Windows' endpoint id carries the same GUID, so one saved
setting and one device list serve every engine. Jeff, 2026-09-29: "all of
this needs to be fixed across the quill family so that output devices work
across media types, windows media or mpv." Before this, choosing a device
under Windows Media could only send the listener to Windows' own Sound
settings page.

What it does not do, and mpv still does: play Ogg Vorbis and Opus streams on
every Windows build, keep a live-radio rewind buffer, boost volume past 100,
or run the sound-enhancement filter graph. It is the Windows engine, not the
primary one. Probed on 2026-09-29 (scratch ``winrt_probe*.py``): an HTTP MP3
stream reached PLAYING in about a second, a local MP3 opened with its
duration, seek and rate took effect, and the audio device switched live with
the position still advancing.

Threading: every MediaPlayer event arrives on a WinRT thread-pool thread and
is handed to the UI thread with ``wx.CallAfter``. The async device lookups
are waited on with a completion callback and an Event -- no asyncio loop, and
no thread of our own (GATE-40).
"""

from __future__ import annotations

import logging
import os
import re
import sys
import threading
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

__all__ = [
    "WinRtMediaEngine",
    "device_guid",
    "list_audio_devices",
    "winrt_media_available",
]

#: The Windows interface class every audio *render* endpoint id carries
#: (``KSCATEGORY_AUDIO`` render endpoints under ``SWD\MMDEVAPI``).
_RENDER_CLASS = "{e6327cad-dcec-4949-ae8a-991e976a79d2}"
#: An endpoint id looks like ``\\?\SWD#MMDEVAPI#{0.0.0.00000000}.{<guid>}#{<class>}``;
#: libmpv names the same device ``wasapi/{<guid>}``.
_ENDPOINT_GUID = re.compile(r"\{0\.0\.0\.00000000\}\.\{([0-9a-f-]{36})\}", re.IGNORECASE)
_MPV_NAME = re.compile(r"^wasapi/\{([0-9a-f-]{36})\}$", re.IGNORECASE)
#: MediaPlayer reports a live stream's duration as an enormous timedelta.
_LIVE_DURATION_DAYS = 3650
_ASYNC_TIMEOUT_SECONDS = 5.0
#: ``Windows.Media.Playback.MediaPlayerError``, in the listener's words.
_ERROR_REASONS = {
    0: "unknown",
    1: "aborted",
    2: "network error",
    3: "decoding error",
    4: "source not supported",
}


def winrt_media_available() -> bool:
    """Whether the Windows Media engine can be built on this machine."""
    if sys.platform != "win32":
        return False
    try:
        # Every namespace named here, including the two pywinrt reaches for
        # on its own (Foundation, Foundation.Collections): PyInstaller freezes
        # what an import statement names, and a missing one only shows at
        # the first call inside the built app.
        import winrt.windows.devices.enumeration  # noqa: F401
        import winrt.windows.foundation  # noqa: F401
        import winrt.windows.foundation.collections  # noqa: F401
        import winrt.windows.media.core  # noqa: F401
        import winrt.windows.media.devices  # noqa: F401
        import winrt.windows.media.playback  # noqa: F401
    except Exception:  # noqa: BLE001 - absent or broken projection is simply "no"
        return False
    return True


def device_guid(name: str) -> str:
    """The endpoint GUID in an mpv-style ``wasapi/{guid}`` device name, or ``""``."""
    match = _MPV_NAME.match((name or "").strip())
    return match.group(1).lower() if match else ""


def _wait(operation: Any, timeout: float = _ASYNC_TIMEOUT_SECONDS) -> Any:
    """Block on a WinRT async operation with its completion callback."""
    done = threading.Event()
    operation.completed = lambda _sender, _status: done.set()
    if not done.wait(timeout):
        raise TimeoutError("the Windows device query did not complete")
    return operation.get_results()


#: GUID -> DeviceInformation, from the last enumeration; set_audio_device
#: needs the object, not the id, and the lookup is async.
_known_devices: dict[str, Any] = {}


def _find_audio_endpoints() -> Any:
    """Windows' audio render endpoints, asking for only those where we can.

    pywinrt does not take the overloads positionally -- ``find_all_async(x)``
    raises "Invalid parameter count" whether *x* is a ``DeviceClass`` or an AQS
    string -- which is why this used to sweep every device on the machine and
    filter in Python. It names its overloads instead, and the named one is not
    a small win: on a developer's machine the unfiltered sweep returned 4,048
    devices in 2.4 seconds, and ``find_all_async_device_class`` returns the 2
    real sound cards in 8 milliseconds. That sweep ran every time a Preferences
    window was opened, and it is what made opening one take two seconds.

    The unfiltered sweep stays as the fallback, because the named overload is a
    pywinrt spelling rather than a WinRT guarantee: a build that does not have
    it gets a slow answer instead of no answer.
    """
    from winrt.windows.devices.enumeration import DeviceClass, DeviceInformation

    by_class = getattr(DeviceInformation, "find_all_async_device_class", None)
    if callable(by_class):
        try:
            return _wait(by_class(DeviceClass.AUDIO_RENDER))
        except TimeoutError:
            raise
        except Exception:  # noqa: BLE001 - an unusable overload is not a failure
            _log.debug("find_all_async_device_class unavailable; sweeping", exc_info=True)
    return _wait(DeviceInformation.find_all_async())


def _enumerate() -> list[Any]:
    """Every enabled audio render endpoint, freshest first in ``_known_devices``."""
    found = []
    for device in _find_audio_endpoints():
        try:
            if _RENDER_CLASS not in device.id.lower() or not device.is_enabled:
                continue
        except Exception:  # noqa: BLE001 - one odd device must not hide the rest
            continue
        match = _ENDPOINT_GUID.search(device.id)
        if match is None:
            continue
        _known_devices[match.group(1).lower()] = device
        found.append(device)
    return found


def list_audio_devices() -> list[tuple[str, str]]:
    """``[(name, description)]`` of the sound cards Windows offers, in libmpv's
    ``wasapi/{guid}`` naming. ``[]`` when the engine is unavailable or the query
    fails -- the callers then show only "System default". Local only."""
    if not winrt_media_available():
        return []
    try:
        devices = _enumerate()
    except Exception:  # noqa: BLE001 - a failed enumeration must not break Preferences
        _log.exception("Windows audio device enumeration failed")
        return []
    rows = []
    for device in devices:
        match = _ENDPOINT_GUID.search(device.id)
        assert match is not None  # _enumerate kept only matching ids
        rows.append((f"wasapi/{{{match.group(1).lower()}}}", str(device.name)))
    return rows


def _dispatch(work: Callable[[], None]) -> None:
    """Run *work* on the UI thread; directly when no wx app is running."""
    try:
        import wx

        if wx.GetApp() is not None:
            wx.CallAfter(work)
            return
    except Exception:  # noqa: BLE001 - no wx at all: run inline
        pass
    work()


def _looks_like_local_path(source: str) -> bool:
    return bool(re.match(r"^[a-zA-Z]:[\\/]", source)) or source.startswith("\\\\")


class WinRtMediaEngine:
    """``Windows.Media.Playback.MediaPlayer`` behind the family's engine protocol.

    Callbacks (``on_loaded(length_ms)``, ``on_finished()``, ``on_error(message)``
    and the optional ``on_buffering(active)``) arrive on the UI thread. A
    ``load`` that is superseded by another before it opens is dropped: each
    load carries a generation number and stale events are ignored.
    """

    def __init__(
        self,
        parent: Any,
        *,
        on_loaded: Callable[[int], None],
        on_finished: Callable[[], None],
        on_error: Callable[[str], None],
        audio_device: str = "",
        on_buffering: Callable[[bool], None] | None = None,
    ) -> None:
        if not winrt_media_available():
            raise OSError("the Windows Media engine is not available")
        from winrt.windows.media.playback import MediaPlayer

        self._parent = parent
        self._on_loaded = on_loaded
        self._on_finished = on_finished
        self._on_error = on_error
        self._on_buffering = on_buffering
        self._player = MediaPlayer()
        # The system media transport controls would otherwise take the
        # keyboard's media keys away from the app's own handling.
        try:
            self._player.command_manager.is_enabled = False
        except Exception:  # noqa: BLE001 - not every build exposes it
            pass
        self._player.auto_play = False
        self._session = self._player.playback_session
        self._generation = 0
        self._loaded = False
        self._finish_fired = False
        self._bounded = False
        self._device = ""
        self._volume = 100
        self._player.add_media_opened(self._media_opened)
        self._player.add_media_failed(self._media_failed)
        self._player.add_media_ended(self._media_ended)
        self._session.add_buffering_started(lambda _s, _a: self._buffering(True))
        self._session.add_buffering_ended(lambda _s, _a: self._buffering(False))
        self.set_audio_device(audio_device)

    # -- device -----------------------------------------------------------------

    def set_audio_device(self, name: str) -> None:
        """Route output to *name* (libmpv's ``wasapi/{guid}``; ``""`` = the device
        Windows gives this app). Takes effect live on a playing stream. A name
        Windows does not offer is logged and leaves the previous device."""
        name = (name or "").strip()
        if not name:
            try:
                self._player.audio_device = None
            except Exception:  # noqa: BLE001
                _log.exception("Windows Media could not return to the default device")
                return
            self._device = ""
            return
        guid = device_guid(name)
        device = _known_devices.get(guid) if guid else None
        if device is None and guid:
            try:
                _enumerate()
            except Exception:  # noqa: BLE001
                _log.exception("Windows audio device enumeration failed")
            device = _known_devices.get(guid)
        if device is None:
            _log.warning("Windows Media has no device named %r; keeping the previous one", name)
            return
        try:
            self._player.audio_device = device
        except Exception:  # noqa: BLE001 - a refused device keeps the previous one
            _log.exception("Windows Media refused audio device %r", name)
            return
        self._device = name
        _log.info("Windows Media output device: %s (%s)", device.name, name)

    @property
    def audio_device(self) -> str:
        return self._device

    # -- engine protocol -------------------------------------------------------

    def load(self, path: str) -> bool:
        from winrt.windows.foundation import Uri
        from winrt.windows.media.core import MediaSource

        self._generation += 1
        self._loaded = False
        self._finish_fired = False
        source = path.strip()
        try:
            if _looks_like_local_path(source) or os.path.exists(source):
                uri = Uri(Path(source).resolve().as_uri())
            else:
                uri = Uri(source)
            self._player.source = MediaSource.create_from_uri(uri)
        except Exception as exc:  # noqa: BLE001 - a bad address is a load failure, not a crash
            _log.warning("Windows Media could not take %r: %s", source, exc)
            self._on_error("Windows Media could not open this address.")
            return False
        return True

    def close(self) -> None:
        self._generation += 1
        self._loaded = False
        try:
            self._player.pause()
            self._player.source = None
        except Exception:  # noqa: BLE001
            pass

    def terminate(self) -> None:
        """Release the player itself (process exit)."""
        self.close()
        try:
            self._player.close()
        except Exception:  # noqa: BLE001
            pass

    def play(self) -> None:
        if self._loaded:
            self._player.play()

    def pause(self) -> None:
        if self._loaded:
            self._player.pause()

    def stop(self) -> None:
        if self._loaded:
            self._player.pause()
            self._seek_to(0)

    def set_bounded(self, bounded: bool) -> None:
        """Whether what is loaded is a finished recording rather than a live
        broadcast (the controller knows once the source resolves)."""
        self._bounded = bool(bounded)

    def is_bounded(self) -> bool:
        return self._bounded

    def seek(self, ms: int, *, resume: bool | None = None) -> None:
        if not self._loaded:
            return
        was_playing = self.is_playing()
        self._seek_to(max(0, int(ms)))
        should_play = was_playing if resume is None else resume
        if should_play:
            self._player.play()
        else:
            self._player.pause()

    def _seek_to(self, ms: int) -> None:
        try:
            if self._session.can_seek:
                self._session.position = timedelta(milliseconds=ms)
        except Exception:  # noqa: BLE001 - a live stream that will not seek stays put
            _log.debug("Windows Media seek refused", exc_info=True)

    def position_ms(self) -> int:
        if not self._loaded:
            return 0
        try:
            return int(self._session.position.total_seconds() * 1000)
        except Exception:  # noqa: BLE001
            return 0

    def length_ms(self) -> int:
        """The duration, or 0 for a live stream (which Windows reports as years)."""
        if not self._loaded:
            return 0
        try:
            duration = self._session.natural_duration
        except Exception:  # noqa: BLE001
            return 0
        if duration is None or duration.days >= _LIVE_DURATION_DAYS or duration.days < 0:
            return 0
        return int(duration.total_seconds() * 1000)

    def is_playing(self) -> bool:
        from winrt.windows.media.playback import MediaPlaybackState

        if not self._loaded:
            return False
        try:
            return self._session.playback_state in (
                MediaPlaybackState.PLAYING,
                MediaPlaybackState.BUFFERING,
            )
        except Exception:  # noqa: BLE001
            return False

    def set_volume(self, percent: int) -> None:
        """0-100. Volume Boost sends up to 150; Windows Media stops at 100."""
        self._volume = max(0, min(100, int(percent)))
        try:
            self._player.volume = self._volume / 100.0
        except Exception:  # noqa: BLE001
            pass

    def set_rate(self, rate: float) -> None:
        """Playback speed (1.0 = normal); Media Foundation keeps the pitch."""
        try:
            self._session.playback_rate = max(0.25, min(4.0, float(rate)))
        except Exception:  # noqa: BLE001
            pass

    # -- what this engine can actually do ---------------------------------
    #
    # The classic wx.media control could answer none of these, so callers
    # guessed. A transport button that is enabled and does nothing is the
    # silent failure: a listener presses it, hears nothing, and has no way to
    # tell "not supported here" from "broken". Asked of the source, a button
    # can be correctly disabled instead, which the screen reader announces.

    def can_seek(self) -> bool:
        """Whether the thing playing can be moved through at all.

        False for live radio, which has no position to seek to.
        """
        try:
            return bool(self._session.can_seek)
        except Exception:  # noqa: BLE001 - unknown means do not promise
            return False

    def can_pause(self) -> bool:
        """Whether pause is real here, rather than a stop wearing its name."""
        try:
            return bool(self._session.can_pause)
        except Exception:  # noqa: BLE001 - unknown means do not promise
            return False

    def buffering_progress(self) -> float:
        """How full the buffer is, 0.0-1.0; 1.0 when it is not buffering.

        The buffering callback is a boolean -- started, ended -- which can say
        "buffering" for twenty seconds without saying whether anything is
        happening. This is the number behind it.
        """
        try:
            return max(0.0, min(1.0, float(self._session.buffering_progress)))
        except Exception:  # noqa: BLE001 - unknown reads as ready
            return 1.0

    def set_real_time(self, enabled: bool) -> None:
        """Ask Media Foundation to favour latency over buffering.

        For live radio, where being thirty seconds behind is worse than an
        occasional rebuffer, and where there is nothing to seek back to anyway.
        Ignored by builds that do not offer it.
        """
        try:
            self._player.real_time_playback = bool(enabled)
        except Exception:  # noqa: BLE001 - a hint, never a requirement
            pass

    def media_transport_controls(self) -> Any:
        """Windows' own now-playing card for this player, or None.

        Display only -- :mod:`quill.ui.audio.now_playing` claims no buttons,
        because the apps own the media keys themselves through RegisterHotKey
        and the command manager is disabled above for exactly that reason.
        """
        try:
            return self._player.system_media_transport_controls
        except Exception:  # noqa: BLE001 - no card is not a failure
            return None

    # -- events (WinRT threads -> UI thread) ------------------------------------

    def _media_opened(self, _sender: Any, _args: Any) -> None:
        generation = self._generation

        def deliver() -> None:
            if generation != self._generation:
                return
            self._loaded = True
            self._on_loaded(self.length_ms())

        _dispatch(deliver)

    def _media_failed(self, _sender: Any, args: Any) -> None:
        generation = self._generation
        try:
            reason = _ERROR_REASONS.get(int(args.error), "unknown")
            detail = str(args.error_message or "").strip()
        except Exception:  # noqa: BLE001
            reason, detail = "unknown", ""
        message = f"Windows Media could not play this stream ({reason})."
        if detail:
            message = f"{message[:-1]}: {detail})."
        _log.warning("Windows Media load failed: %s", message)

        def deliver() -> None:
            if generation != self._generation:
                return
            self._loaded = False
            self._on_error(message)

        _dispatch(deliver)

    def _media_ended(self, _sender: Any, _args: Any) -> None:
        generation = self._generation

        def deliver() -> None:
            if generation != self._generation or self._finish_fired:
                return
            self._finish_fired = True
            self._on_finished()

        _dispatch(deliver)

    def _buffering(self, active: bool) -> None:
        if self._on_buffering is None:
            return
        generation = self._generation

        def deliver() -> None:
            if generation == self._generation and self._loaded and self._on_buffering:
                self._on_buffering(active)

        _dispatch(deliver)
