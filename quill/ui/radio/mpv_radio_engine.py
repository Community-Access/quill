"""libmpv playback engine for internet radio -- the output-device path (#1076).

``RadioPlayerController`` plays through ``WxMediaEngine`` (wx.media / WMP) by
default, and that backend has no audio-output-device API at all -- it always
plays to the system default device. This module is the opt-in alternative
that makes "route the radio to my second sound card" possible: libmpv
natively supports ``audio-device``, and it is already a first-class optional
component of the product (the Audio Studio / podcast engine, the Offline
Edition bundles it under ``{app}/tools/mpv``).

This is the "separately-scoped follow-up" the controller's own docstring
called for -- **not** a reuse of ``MpvAudioEngine``, whose ``_on_poll`` only
flips its "loaded" flag once ``duration`` reports a positive value, which a
live stream never does. Radio needs its own readiness logic:

- **Loaded** = the playback core actually started outputting audio
  (``core-idle`` goes false). No duration, no seek bar -- a live stream has
  neither.
- **Error** = mpv gave up and returned to idle (``idle-active`` goes true
  before the stream ever started); mpv's own ``network-timeout`` bounds the
  connect attempt so a dead URL fails in seconds, like the WMP backend does.
- **Finished** = ``eof-reached`` (with ``keep-open``) or a fall back to idle
  after playing -- for a live stream both mean the connection dropped, which
  is exactly what the controller's ``on_finished`` already expects.

The poll-tick decision is a pure function (:func:`next_poll_action`) so the
state machine is unit-testable without libmpv or a network.

Same contract as the other engines: all calls on the UI thread, callbacks on
the UI thread via a ``wx.Timer`` poll -- no mpv event thread ever touches
wx. Unlike ``MpvAudioEngine.close`` (which destroys the handle), ``close``
here is a soft stop and the handle stays reusable, because the radio
controller stop/play cycles one engine for the process's lifetime; the
handle is destroyed when the parent window is.

wx required (UI layer). No new network surface: the engine plays the same
station/relay URL the wx.media engine would (already inventoried); device
enumeration is local.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable

import wx

from quill.ui.audio.mpv_engine import _MpvClient, find_libmpv

_log = logging.getLogger(__name__)

_POLL_MS = 200
#: mpv's own bound on a stalled network connect/read; a dead URL errors out
#: in seconds instead of hanging "connecting..." forever.
_NETWORK_TIMEOUT_SECONDS = 15
#: The live-radio DVR buffer: mpv's demuxer cache keeps this much of the
#: stream behind (and ahead while paused), which is what makes pausing a
#: live show and rewinding it possible at all. 50 MiB is roughly 45
#: minutes of a typical 128 kbps stream.
_CACHE_MAX_BYTES = "50MiB"
_CACHE_BACK_BYTES = "50MiB"
#: Volume Boost headroom: mpv can amplify past 100 (with soft-clipping
#: protection well above this); the boost feature uses up to 150.
_VOLUME_MAX = "150"

#: What a poll tick should do next; returned by :func:`next_poll_action`.
ACTION_NONE = "none"
ACTION_LOADED = "loaded"
ACTION_ERROR = "error"
ACTION_FINISHED = "finished"


def next_poll_action(
    *,
    loaded: bool,
    idle_active: bool | None,
    core_idle: bool | None,
    eof_reached: bool | None,
) -> str:
    """The live-stream poll state machine (pure, unit-tested).

    Before *loaded*: a return to mpv's idle state means the load failed
    (mpv exhausted its network timeout or rejected the URL); the core
    leaving ``core-idle`` means audio is actually being output -- the
    stream is ready. After *loaded*: ``eof-reached`` or a fall back to
    idle both mean a live stream's connection dropped.

    ``None`` property reads (a query that failed) never drive a transition.
    """
    if not loaded:
        if idle_active is True:
            return ACTION_ERROR
        if core_idle is False:
            return ACTION_LOADED
        return ACTION_NONE
    if eof_reached is True or idle_active is True:
        return ACTION_FINISHED
    return ACTION_NONE


def parse_audio_device_list(raw: str) -> list[tuple[str, str]]:
    """``(name, description)`` pairs out of mpv's ``audio-device-list`` JSON.

    Pure and unit-tested; malformed input yields ``[]`` rather than raising.
    The *name* (e.g. ``wasapi/{guid}``) is the stable value to persist and
    hand back to ``audio-device``; the *description* is the human label
    ("Speakers (Realtek High Definition Audio)").

    mpv's list includes pseudo-entries that are not sound cards: ``auto``
    (what "System default" already means) and bare driver fallbacks with no
    device part (``openal``, ``sdl``). Both are dropped so the Preferences
    dropdown lists only real, pickable devices.
    """
    try:
        data = json.loads(raw)
    except ValueError:
        return []
    devices: list[tuple[str, str]] = []
    if not isinstance(data, list):
        return []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip()
        if not name or name == "auto" or "/" not in name:
            continue
        description = str(entry.get("description", "")).strip() or name
        devices.append((name, description))
    return devices


def list_audio_devices() -> list[tuple[str, str]]:
    """Enumerate output devices via a short-lived libmpv handle.

    ``[]`` when libmpv is not installed or enumeration fails -- callers
    (the Preferences dropdown) then show only "System default". Local
    only; never touches the network.
    """
    dll_path = find_libmpv()
    if dll_path is None:
        return []
    try:
        client = _MpvClient(dll_path)
    except Exception:  # noqa: BLE001 - a broken DLL must not break Preferences
        _log.exception("libmpv found but unusable for device enumeration")
        return []
    try:
        raw = client.get_str("audio-device-list")
    except Exception:  # noqa: BLE001
        _log.exception("audio-device-list query failed")
        return []
    finally:
        try:
            client.close()
        except Exception:  # noqa: BLE001
            pass
    return parse_audio_device_list(raw or "[]")


#: The always-first dropdown entry (device name ""): keeps radio on the
#: wx.media engine, byte-for-byte today's path.
SYSTEM_DEFAULT_DEVICE_LABEL = "System default"


def output_device_choices(
    devices: list[tuple[str, str]], current: str
) -> tuple[list[str], list[str], int]:
    """The Preferences dropdown model: labels, parallel device names, and
    the selected index (pure, unit-tested).

    "System default" is always first (name ""). A saved device that is not
    currently connected still appears -- marked, at the end -- so opening
    Preferences never silently resets the choice just because a USB sound
    card is unplugged today.
    """
    labels = [SYSTEM_DEFAULT_DEVICE_LABEL]
    names = [""]
    for name, description in devices:
        labels.append(description)
        names.append(name)
    current = current.strip()
    if current and current not in names:
        labels.append(f"{current} (not currently available)")
        names.append(current)
    return labels, names, names.index(current) if current in names else 0


def mpv_output_device_available() -> bool:
    """True when the opt-in device-selection path can work on this machine."""
    try:
        return find_libmpv() is not None
    except Exception:  # noqa: BLE001 - discovery must never block playback
        return False


class MpvRadioEngine:
    """The libmpv radio engine: live-stream readiness + ``audio-device``.

    Satisfies the parts of the ``AudioEngine`` protocol the radio controller
    uses (load/close/play/pause/is_playing/set_volume plus the loaded/
    finished/error callbacks); position/length/seek are best-effort no-ops a
    live stream has no use for.
    """

    def __init__(
        self,
        parent: wx.Window,
        *,
        on_loaded: Callable[[int], None],
        on_finished: Callable[[], None],
        on_error: Callable[[str], None],
        audio_device: str = "",
        on_buffering: Callable[[], None] | None = None,
    ) -> None:
        dll_path = find_libmpv()
        if dll_path is None:
            raise OSError("libmpv is not installed")
        self._mpv = _MpvClient(dll_path)
        self._mpv.set_str("network-timeout", str(_NETWORK_TIMEOUT_SECONDS))
        # Identify as Quill Radio (not the default "libmpv") in station logs
        # (quill-radio #6).
        from quill.core import http_client

        self._mpv.set_str("user-agent", http_client.user_agent())
        # The DVR buffer: a seekable demuxer cache large enough to pause a
        # live show or rewind it (see rewind_seconds / jump_to_live).
        self._mpv.set_str("cache", "yes")
        self._mpv.set_str("demuxer-max-bytes", _CACHE_MAX_BYTES)
        self._mpv.set_str("demuxer-max-back-bytes", _CACHE_BACK_BYTES)
        self._mpv.set_str("volume-max", _VOLUME_MAX)
        self._on_loaded = on_loaded
        self._on_finished = on_finished
        self._on_error = on_error
        #: Fired (UI thread) when a playing stream stalls and mpv pauses
        #: itself to rebuffer -- the host announces it instead of dead air.
        self._on_buffering = on_buffering
        self._loaded = False
        self._finish_fired = False
        self._buffering = False
        self._volume = 100
        self._current_url = ""
        self.set_audio_device(audio_device)
        self._timer = wx.Timer(parent)
        parent.Bind(wx.EVT_TIMER, self._on_poll, self._timer)
        parent.Bind(wx.EVT_WINDOW_DESTROY, self._on_parent_destroyed)

    # -- device -----------------------------------------------------------------

    def set_audio_device(self, name: str) -> None:
        """Route output to mpv device *name* ("" = system default).

        Runtime-settable: mpv switches a playing stream to the new device
        without a reload.
        """
        self._mpv.set_str("audio-device", name.strip() or "auto")

    # -- sound ------------------------------------------------------------------

    def set_filter_graph(self, graph: str) -> None:
        """Apply an ffmpeg filter graph (Sound Enhancements) natively via
        mpv's ``af`` -- no localhost relay, no second ffmpeg process, and it
        takes effect live on a playing stream without a reconnect. "" clears
        all filtering.
        """
        self._mpv.set_str("af", f"lavfi=[{graph}]" if graph else "")

    # -- live DVR (pause / rewind within the demuxer cache) ----------------------

    def behind_live_seconds(self) -> float | None:
        """How far behind the live edge playback currently is, or None when
        unknown (not loaded, or the stream exposes no usable timestamps)."""
        if not self._loaded:
            return None
        cache_end = self._mpv.get_double("demuxer-cache-time")
        position = self._mpv.get_double("time-pos")
        if cache_end is None or position is None:
            return None
        return max(0.0, cache_end - position)

    def seek_relative(self, seconds: float) -> bool:
        """Jump within the buffered live window (negative = rewind). mpv
        clamps to what the cache still holds. False when not loaded."""
        if not self._loaded:
            return False
        try:
            self._mpv.command("seek", f"{seconds:.3f}", "relative")
        except Exception:  # noqa: BLE001 - a failed seek must not crash playback
            _log.exception("mpv relative seek failed")
            return False
        return True

    def jump_to_live(self) -> bool:
        """Return to the live edge of the stream. False when not possible
        (the caller should reconnect instead -- always live)."""
        if not self._loaded:
            return False
        cache_end = self._mpv.get_double("demuxer-cache-time")
        if cache_end is None:
            return False
        try:
            self._mpv.command("seek", f"{max(0.0, cache_end - 1.0):.3f}", "absolute")
        except Exception:  # noqa: BLE001
            _log.exception("mpv jump-to-live seek failed")
            return False
        return True

    # -- now playing --------------------------------------------------------------

    def now_playing_title(self) -> str:
        """The stream's own ICY/HLS title via mpv's ``media-title`` -- the
        engine-native fallback when the out-of-band ICY side connection gets
        nothing (some hosts reject it; HLS has no ICY at all). "" when mpv
        only knows the URL (i.e. no real title)."""
        if not self._loaded:
            return ""
        title = (self._mpv.get_str("media-title") or "").strip()
        if not title or title == self._current_url:
            return ""
        return title

    # -- engine protocol ---------------------------------------------------------

    def load(self, path: str) -> bool:
        self._loaded = False
        self._finish_fired = False
        self._buffering = False
        self._current_url = path
        try:
            # Live radio starts playing as soon as it can -- no pause-then-
            # play handshake (that is the audiobook engine's shape). Volume
            # is applied before the URL so the first audible sample is
            # already at the user's level.
            self._mpv.set_str("volume", str(self._volume))
            self._mpv.set_str("pause", "no")
            self._mpv.command("loadfile", path, "replace")
        except Exception:  # noqa: BLE001 - a bad URL must not crash the app
            _log.exception("mpv loadfile failed")
            self._on_error("That stream could not be opened.")
            return False
        self._timer.Start(_POLL_MS)
        return True

    def close(self) -> None:
        """Soft stop: back to idle, handle kept for the next ``load``."""
        try:
            self._timer.Stop()
        except Exception:  # noqa: BLE001
            pass
        self._loaded = False
        try:
            self._mpv.command("stop")
        except Exception:  # noqa: BLE001 - never block a stop
            _log.exception("mpv stop failed")

    def play(self) -> None:
        if self._loaded:
            self._mpv.set_str("pause", "no")

    def pause(self) -> None:
        if self._loaded:
            self._mpv.set_str("pause", "yes")

    def stop(self) -> None:
        self.close()

    def seek(self, ms: int, *, resume: bool | None = None) -> None:
        """A live stream has no timeline; seeking is meaningless."""

    def position_ms(self) -> int:
        if not self._loaded:
            return 0
        value = self._mpv.get_double("time-pos")
        return int(value * 1000) if value is not None and value > 0 else 0

    def length_ms(self) -> int:
        return 0

    def is_playing(self) -> bool:
        if not self._loaded:
            return False
        return self._mpv.get_flag("pause") is False

    def set_volume(self, percent: int) -> None:
        # Up to 150, not 100: Volume Boost amplifies quiet streams past
        # unity (volume-max=150 was set at init; mpv soft-clips safely).
        self._volume = max(0, min(150, int(percent)))
        self._mpv.set_str("volume", str(self._volume))

    def set_rate(self, rate: float) -> None:
        """Live radio plays at broadcast speed."""

    # -- polling -----------------------------------------------------------------

    def _on_poll(self, _evt: wx.TimerEvent) -> None:
        try:
            action = next_poll_action(
                loaded=self._loaded,
                idle_active=self._mpv.get_flag("idle-active"),
                core_idle=self._mpv.get_flag("core-idle"),
                eof_reached=self._mpv.get_flag("eof-reached"),
            )
            if action == ACTION_LOADED:
                self._loaded = True
                self._on_loaded(0)
            elif action == ACTION_ERROR:
                self._timer.Stop()
                self._on_error("That stream could not be opened.")
            elif action == ACTION_FINISHED and not self._finish_fired:
                self._finish_fired = True
                self._timer.Stop()
                self._on_finished()
            elif action == ACTION_NONE and self._loaded:
                # Stall detection: mpv pauses itself to rebuffer when the
                # network hiccups; say so once per stall instead of dead air.
                stalled = self._mpv.get_flag("paused-for-cache") is True
                if stalled and not self._buffering and self._on_buffering is not None:
                    self._on_buffering()
                self._buffering = stalled
        except Exception:  # noqa: BLE001 - polling must never take the app down
            _log.exception("mpv radio poll failed")
            self._timer.Stop()

    def _on_parent_destroyed(self, evt: wx.WindowDestroyEvent) -> None:
        evt.Skip()
        try:
            self._timer.Stop()
        except Exception:  # noqa: BLE001
            pass
        self._mpv.close()
