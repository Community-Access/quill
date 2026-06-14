"""Cross-platform earcon playback for QUILL.

Backend selection (in priority order)
--------------------------------------
1. ``sound_lib`` (BASS from Un4seen via the accessibleapps/sound_lib package).
   Available on Windows, macOS, and Linux.  BASS mixes streams natively, so
   multiple earcons can play simultaneously with no queue or serialisation
   thread.  Install with ``pip install sound_lib``.

2. ``winsound`` (Windows stdlib).  Falls back to this when sound_lib is absent.
   Serialises playback via a daemon thread because winsound cannot mix.

3. Silent no-op.  If neither backend initialises, ``play()`` is a no-op and a
   one-time warning is logged.

Public API
----------
* :class:`SoundPlayer`    -- facade: cooldown, mute, disabled-event filtering
* :data:`_detect_backend` -- called once at SoundPlayer construction
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from quill.core.sound_pack import SoundPack

logger = logging.getLogger(__name__)

_COOLDOWN_S: float = 0.08  # suppress repeated identical events within 80 ms

# winsound queue cap: winsound serialises (one sound at a time), so cap
# pending items to avoid pile-up.  sound_lib mixes natively and has no cap.
_WINSOUND_QUEUE_MAX: int = 2


# ---------------------------------------------------------------------------
# Backend protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class _WavBackend(Protocol):
    """Minimal interface a playback backend must satisfy."""

    def play_wav(self, wav: bytes) -> None:
        """Play *wav* bytes.  Must return promptly; never raises."""
        ...

    def shutdown(self, timeout: float = 2.0) -> None:
        """Release resources.  Called once at player teardown."""
        ...


# ---------------------------------------------------------------------------
# Backend: sound_lib (BASS) — cross-platform, native mixing
# ---------------------------------------------------------------------------


class _SoundLibBackend:
    """BASS-backed earcon player via the ``sound_lib`` package.

    BASS supports simultaneous streams — no queue or serialisation thread
    is needed.  Each ``play_wav()`` call creates a short-lived BASS stream
    with ``autofree=True`` so BASS disposes of it automatically when done.
    """

    def __init__(self) -> None:
        # Import deferred to keep the module importable without sound_lib.
        from sound_lib.output import Output  # type: ignore[import-untyped]

        self._output = Output()
        logger.debug("SoundPlayer: using sound_lib (BASS) backend")

    def play_wav(self, wav: bytes) -> None:
        try:
            from sound_lib.stream import FileStream  # type: ignore[import-untyped]

            stream = FileStream(
                mem=True,
                file=wav,
                offset=0,
                length=len(wav),
                autofree=True,
            )
            stream.play()
        except Exception:  # noqa: BLE001
            logger.warning("SoundPlayer (sound_lib): playback failed", exc_info=True)

    def shutdown(self, timeout: float = 2.0) -> None:
        try:
            self._output.free()
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# Backend: winsound — Windows stdlib, serialising thread
# ---------------------------------------------------------------------------


class _WinsoundBackend:
    """``winsound``-backed earcon player for Windows.

    ``winsound`` cannot mix, so playback is serialised through a single
    daemon thread with a bounded queue.  Excess requests are dropped
    rather than stacked.
    """

    def __init__(self) -> None:
        import winsound as _ws  # imported here so the module stays importable elsewhere

        self._winsound = _ws
        self._queue: queue.Queue[bytes | None] = queue.Queue(maxsize=_WINSOUND_QUEUE_MAX)
        self._thread = threading.Thread(
            target=self._worker,
            name="QuillSoundPlayer-winsound",
            daemon=True,
        )
        self._thread.start()
        logger.debug("SoundPlayer: using winsound backend")

    def play_wav(self, wav: bytes) -> None:
        try:
            self._queue.put_nowait(wav)
        except queue.Full:
            pass  # player busy; drop this earcon

    def shutdown(self, timeout: float = 2.0) -> None:
        try:
            self._queue.put(None, timeout=timeout)
        except queue.Full:
            pass
        self._thread.join(timeout=timeout)

    def _worker(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                return
            try:
                self._winsound.PlaySound(
                    item,
                    self._winsound.SND_MEMORY | self._winsound.SND_NODEFAULT,
                )
            except Exception:  # noqa: BLE001
                logger.warning("SoundPlayer (winsound): playback failed", exc_info=True)


# ---------------------------------------------------------------------------
# Backend: null — silent no-op
# ---------------------------------------------------------------------------


class _NullBackend:
    def play_wav(self, wav: bytes) -> None:
        pass

    def shutdown(self, timeout: float = 2.0) -> None:
        pass


# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------


def _detect_backend() -> _WavBackend:
    """Return the best available playback backend."""

    try:
        return _SoundLibBackend()
    except Exception:  # noqa: BLE001
        logger.debug("sound_lib unavailable; trying winsound", exc_info=False)

    try:
        return _WinsoundBackend()
    except Exception:  # noqa: BLE001
        logger.debug("winsound unavailable", exc_info=False)

    logger.warning(
        "SoundPlayer: no audio backend available; earcons will be silent. "
        "Install sound_lib for cross-platform audio: pip install sound_lib"
    )
    return _NullBackend()


# ---------------------------------------------------------------------------
# SoundPlayer — public facade
# ---------------------------------------------------------------------------


class SoundPlayer:
    """Fire-and-forget earcon player.

    Owns cooldown, mute, and disabled-event logic.  Delegates actual
    playback to the injected (or auto-detected) backend.

    Lifecycle::

        player = SoundPlayer()
        player.load_pack(pack, disabled=frozenset())
        player.play("abbreviation_expanded")   # returns immediately
        player.shutdown()                      # waits for backend teardown
    """

    def __init__(self, backend: _WavBackend | None = None) -> None:
        self._backend: _WavBackend = backend if backend is not None else _detect_backend()
        self._lock = threading.Lock()
        self._muted: bool = False
        self._events: dict[str, bytes] = {}
        self._disabled: frozenset[str] = frozenset()
        self._cooldowns: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def load_pack(
        self,
        pack: SoundPack,
        disabled: frozenset[str] = frozenset(),
    ) -> None:
        """Replace the active pack and clear cooldowns."""
        with self._lock:
            self._events = dict(pack.events)
            self._disabled = disabled
            self._cooldowns.clear()
        logger.debug(
            "SoundPlayer: loaded pack '%s' (%d event(s), %d disabled)",
            pack.name,
            len(pack.events),
            len(disabled),
        )

    def register_event(self, event_id: str, wav: bytes) -> None:
        """Add or replace a single event's WAV bytes (used by Quillin sound packs)."""
        with self._lock:
            self._events[event_id] = wav

    def set_disabled(self, disabled: frozenset[str]) -> None:
        with self._lock:
            self._disabled = disabled

    def set_muted(self, muted: bool) -> None:
        with self._lock:
            self._muted = muted

    def toggle_mute(self) -> bool:
        """Flip mute and return the new state (True == muted)."""
        with self._lock:
            self._muted = not self._muted
            return self._muted

    @property
    def muted(self) -> bool:
        with self._lock:
            return self._muted

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    def play(self, event_id: str) -> None:
        """Post an earcon for *event_id*.  Returns immediately; never raises."""
        with self._lock:
            if self._muted:
                return
            if event_id in self._disabled:
                return
            wav = self._events.get(event_id)
            if wav is None:
                return
            now = time.monotonic()
            if now - self._cooldowns.get(event_id, 0.0) < _COOLDOWN_S:
                return
            self._cooldowns[event_id] = now

        self._backend.play_wav(wav)

    def loaded_event_ids(self) -> frozenset[str]:
        """Return the set of event IDs currently loaded in the player."""
        with self._lock:
            return frozenset(self._events.keys())

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def shutdown(self, timeout: float = 2.0) -> None:
        """Shut down the backend.  Blocks up to *timeout* seconds."""
        self._backend.shutdown(timeout=timeout)
