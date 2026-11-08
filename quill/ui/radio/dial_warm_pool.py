"""Warm neighbours for dial tuning: up to two muted, connected mpv players.

The idea -- keep the stations either side of the one you are on connected, so
the next step is near instant -- comes from BlindRadio by serrebidev (MIT), whose
``tuner.rs`` and ``live.rs`` keep neighbours open. Quill Radio does it with mpv:
no BlindRadio code is copied.

**At most three players.** The controller's own engine plays the station; this
pool holds at most :data:`~quill.core.radio.dial_tuning.MAX_WARM` more. Engines
are made once and reused: a neighbour that stops being one is closed (a soft
stop) and its engine waits for the next, so a long session moving through
hundreds of stations makes two engines, not hundreds.

**A warm neighbour is muted, connected and never recorded.** Its volume is
zero, its Sound Enhancements graph empty, its time-shift buffer the small
in-memory one (it writes nothing to disk), and the recorder never sees it: a
recording is its own ffmpeg process on a station the listener chose.

**Promotion keeps every property the main player has.** When the dial settles
on a warm station, :func:`promote` hands that engine to the controller and the
controller's old engine comes back here, muted, still connected to the station
just left -- which is usually a neighbour of the new one. The promoted engine
takes the main player's output device, volume (with Volume Boost), Sound
Enhancements graph, the station's time-shift length (it applies from the next
load, which is what Enter does) and freshly reset song marks.

Everything runs on the UI thread, like every engine call.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from typing import Any

from quill.core.radio.dial_tuning import MAX_WARM, DialRow

_log = logging.getLogger(__name__)

__all__ = ["WarmPool", "can_promote", "promote"]

EngineFactory = Callable[..., Any]


def _default_factory(parent: Any, **callbacks: Any) -> Any:
    from quill.ui.radio.mpv_radio_engine import MpvRadioEngine

    # 0 minutes: the in-memory buffer. A neighbour must not write to disk, and a
    # disk buffer's first configure sweeps the cache folder the station uses.
    return MpvRadioEngine(parent, timeshift_minutes=0, **callbacks)


class _Slot:
    __slots__ = ("engine", "key", "ready")

    def __init__(self, engine: Any) -> None:
        self.engine = engine
        self.key = ""
        self.ready = False


class WarmPool:
    """The neighbours, by station key."""

    def __init__(self, parent: Any, *, factory: EngineFactory | None = None) -> None:
        self._parent = parent
        self._factory = factory or _default_factory
        self._slots: list[_Slot] = []

    # -- questions ----------------------------------------------------------

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(slot.key for slot in self._slots if slot.key)

    @property
    def engine_count(self) -> int:
        return len(self._slots)

    def is_ready(self, key: str) -> bool:
        slot = self._find(key)
        return slot is not None and slot.ready

    # -- keeping neighbours -------------------------------------------------

    def keep(self, rows: Sequence[DialRow], *, device: str = "") -> None:
        """Keep exactly *rows* connected; close every other slot."""
        wanted = [row for row in rows if row.station is not None][:MAX_WARM]
        wanted_keys = {row.key for row in wanted}
        for slot in self._slots:
            if slot.key and slot.key not in wanted_keys:
                self._release(slot)
        for row in wanted:
            if self._find(row.key) is not None:
                continue
            slot = self._free_slot()
            if slot is None:
                break
            self._connect(slot, row, device)

    def clear(self) -> None:
        """Let every neighbour go (the dial turned off, or focus left the list)."""
        for slot in self._slots:
            if slot.key:
                self._release(slot)

    def shutdown(self) -> None:
        """Destroy every engine; the app is closing."""
        for slot in self._slots:
            terminate = getattr(slot.engine, "terminate", None)
            if callable(terminate):
                try:
                    terminate()
                except Exception:  # noqa: BLE001 - never block app close
                    _log.exception("warm neighbour terminate failed")
        self._slots.clear()

    def take(self, key: str) -> Any:
        """Hand over the engine connected to *key*, or None. It leaves the pool."""
        slot = self._find(key)
        if slot is None:
            return None
        self._slots.remove(slot)
        return slot.engine

    def adopt(self, key: str, engine: Any, *, ready: bool) -> None:
        """Take back the controller's previous engine, still on station *key*.

        Kept only while there is room; otherwise it is closed and becomes the
        spare. The total never goes above the cap.
        """
        _mute(engine)
        slot = _Slot(engine)
        self._bind(slot)
        slot.key = key
        slot.ready = ready
        self._slots.append(slot)
        while len(self._slots) > MAX_WARM:
            # The idle spare goes first, then the oldest neighbour.
            spare = next((s for s in self._slots if not s.key), self._slots[0])
            self._release(spare)
            self._slots.remove(spare)
            terminate = getattr(spare.engine, "terminate", None)
            if callable(terminate):
                try:
                    terminate()
                except Exception:  # noqa: BLE001
                    _log.exception("spare neighbour terminate failed")

    # -- internals ----------------------------------------------------------

    def _find(self, key: str) -> _Slot | None:
        return next((slot for slot in self._slots if key and slot.key == key), None)

    def _free_slot(self) -> _Slot | None:
        idle = next((slot for slot in self._slots if not slot.key), None)
        if idle is not None:
            return idle
        if len(self._slots) >= MAX_WARM:
            return None
        try:
            slot = _Slot(None)
            slot.engine = self._factory(
                self._parent,
                on_loaded=lambda _ms, s=slot: self._loaded(s),
                on_finished=lambda s=slot: self._gone(s),
                on_error=lambda _message, s=slot: self._gone(s),
            )
        except Exception:  # noqa: BLE001 - no neighbour is a slower step, never a failure
            _log.exception("could not make a warm neighbour")
            return None
        self._slots.append(slot)
        return slot

    def _bind(self, slot: _Slot) -> None:
        """Point an engine's callbacks at this pool (an adopted one pointed elsewhere)."""
        engine = slot.engine
        engine._on_loaded = lambda _ms: self._loaded(slot)
        engine._on_finished = lambda: self._gone(slot)
        engine._on_error = lambda _message: self._gone(slot)
        engine._on_buffering = None

    def _connect(self, slot: _Slot, row: DialRow, device: str) -> None:
        engine = slot.engine
        station = row.station
        if station is None:
            return
        try:
            _mute(engine)
            engine.set_audio_device(device)
            if engine.load(station.stream_url):
                slot.key = row.key
                slot.ready = False
        except Exception:  # noqa: BLE001
            _log.exception("warm neighbour could not connect")
            self._release(slot)

    def _loaded(self, slot: _Slot) -> None:
        slot.ready = True
        # mpv's loaded callback is where the controller would unpause; a
        # neighbour stays muted and keeps reading so it is current when chosen.
        _mute(slot.engine)

    def _gone(self, slot: _Slot) -> None:
        """A neighbour that will not connect, or dropped, is simply let go."""
        if slot in self._slots:
            self._release(slot)

    def _release(self, slot: _Slot) -> None:
        slot.key = ""
        slot.ready = False
        try:
            slot.engine.close()
        except Exception:  # noqa: BLE001
            _log.exception("warm neighbour close failed")


def _mute(engine: Any) -> None:
    try:
        engine.set_volume(0)
        engine.set_filter_graph("")
    except Exception:  # noqa: BLE001 - a neighbour that cannot be muted is closed by its owner
        _log.debug("could not mute a warm neighbour", exc_info=True)


#: ``ResolvedEnhancement`` field -> the controller attribute it sets, exactly as
#: ``RadioPlayerController._play_resolved_station`` copies them.
_ENHANCEMENT_FIELDS: tuple[tuple[str, str], ...] = (
    ("bass_db", "_eq_bass_db"),
    ("mid_db", "_eq_mid_db"),
    ("treble_db", "_eq_treble_db"),
    ("compressor_enabled", "_compressor_enabled"),
    ("channel_mode", "_channel_mode"),
    ("night_mode_enabled", "_night_mode_enabled"),
    ("optilab_enabled", "_optilab_enabled"),
    ("optilab_mode", "_optilab_mode"),
    ("optilab_input_db", "_optilab_input_db"),
    ("optilab_auto_adapt", "_optilab_auto_adapt"),
    ("optilab_exact_live", "_optilab_exact_live"),
)


def can_promote(controller: Any, station: Any) -> bool:
    """Whether a warm engine can take over from the controller's own.

    Only when the controller is playing through mpv with no relay in the way:
    a Windows Media, Spotify or exact-OptiLab play has nothing a muted mpv
    player can stand in for, so it takes the ordinary path.
    """
    try:
        if not controller._is_mpv_active():
            return False
        if controller._exact_live_spec() is not None:
            return False
        return not controller._is_spotify_station(station)
    except Exception:  # noqa: BLE001
        return False


def promote(controller: Any, pool: WarmPool, key: str, station: Any, *, old_key: str) -> bool:
    """Swap the warm engine for *key* into *controller*. True when it did.

    The steps are the controller's own ``_play_resolved_station`` with the load
    taken out, because the load is what the warm engine already did.
    """
    if not can_promote(controller, station) or not pool.is_ready(key):
        return False
    engine = pool.take(key)
    if engine is None:
        return False
    from quill.ui.radio import engine_selection, live_reconnect
    from quill.ui.radio.playback_state import RadioPlayerState

    old = controller._mpv_engine
    old_ready = bool(getattr(old, "_loaded", False))
    if controller._before_play is not None:
        try:
            controller._before_play()
        except Exception:  # noqa: BLE001 - a sibling-stop must never block play
            pass
    if controller._resolve_enhancement is not None:
        resolved = controller._resolve_enhancement(station)
        for field, attribute in _ENHANCEMENT_FIELDS:
            setattr(controller, attribute, getattr(resolved, field))
    controller._remember_resume_point()
    controller._play_token += 1
    controller._playback_url_override = ""
    controller._youtube_stream = None
    controller._state.station = station
    controller._pending_resume_ms = 0
    if controller._resolve_volume is not None:
        memorized = controller._resolve_volume(station)
        if memorized >= 0:
            controller._state.volume_percent = max(0, min(100, int(memorized)))
            controller._state.muted = controller._state.volume_percent == 0
    controller._fallback_attempted = False
    controller._device_rescued = False
    controller._selected_audio_track = None
    live_reconnect.reset(controller)
    # The swap. The old engine keeps its connection and goes back to the pool.
    engine._on_loaded = controller._on_loaded
    engine._on_finished = controller._on_finished
    engine._on_error = controller._on_error
    engine._on_buffering = controller._handle_buffering
    controller._mpv_engine = engine
    controller._engine = engine
    try:
        engine.set_audio_device(controller._output_device)
        engine_selection.prepare_station(controller, engine)
        extras = getattr(engine, "live_extras", None)
        if extras is not None:
            extras.on_load()  # song marks start again for this station
            extras.marks.station_name = str(getattr(station, "name", "") or "")
        engine.set_filter_graph(controller._current_filter_graph())
        engine.set_volume(controller._effective_volume())
    except Exception:  # noqa: BLE001 - a property that will not apply is logged, not fatal
        _log.exception("could not carry a property onto the promoted engine")
    if old is not None and old is not engine:
        pool.adopt(old_key, old, ready=old_ready)
    controller._set_state(RadioPlayerState.CONNECTING, message="")
    controller._declare_source_shape()
    if bool(getattr(engine, "_loaded", False)):
        controller._on_loaded(0)
    return True
