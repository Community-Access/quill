"""Cross-platform earcon playback for QUILL.

Backend selection (in priority order)
--------------------------------------
1. ``sound_lib`` (BASS from Un4seen via the accessibleapps/sound_lib package).
   Available on Windows, macOS, and Linux.  BASS mixes streams natively, so
   multiple earcons can play simultaneously with no queue or serialisation
   thread.  Install with ``pip install sound_lib``.  This is a *licensed*
   third-party engine (see the ``audio`` extra in ``pyproject.toml``), so it
   is deliberately never bundled by default on any platform's build.

2. ``winsound`` (Windows stdlib).  Falls back to this when sound_lib is
   absent.  Serialises playback via a daemon thread because winsound cannot
   mix.  Windows-only.

3. ``NSSound`` (AppKit, via ``pyobjc``).  macOS fallback for when sound_lib is
   absent -- macOS has no stdlib playback module equivalent to ``winsound``,
   so without this the macOS app fell straight through to :class:`_NullBackend`
   and every earcon, including the bundled default pack, was silent out of
   the box. ``pyobjc`` is already a dependency of the ``macos`` build extra
   (used for the Foundation Models bridge), so this adds no new dependency.

4. Silent no-op.  If no backend initialises, ``play()`` is a no-op and a
   one-time warning is logged.

Public API
----------
* :class:`SoundPlayer`    -- facade: cooldown, mute, disabled-event filtering,
                             per-event registration/unregistration, and
                             :meth:`SoundPlayer.set_volume` for the master
                             output level
* :data:`_detect_backend` -- called once at SoundPlayer construction
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Iterable
from typing import TYPE_CHECKING

# Imported under their old private names, so every use in this module and in
# tests/unit/platform/test_sound_player.py reads exactly as it did before the
# 2026-09-10 split.
from quill.platform.sound_backends import WavBackend as _WavBackend

if TYPE_CHECKING:
    from quill.core.sound_pack import SoundPack

logger = logging.getLogger(__name__)

_COOLDOWN_S: float = 0.08  # suppress repeated identical events within 80 ms

# winsound queue cap: winsound serialises (one sound at a time), so cap
# pending items to avoid pile-up.  sound_lib mixes natively and has no cap.
_WINSOUND_QUEUE_MAX: int = 2


# ---------------------------------------------------------------------------
# Backend: sound_lib (BASS) — cross-platform, native mixing
# ---------------------------------------------------------------------------


#: How many still-playing streams to hold references to. Earcons are tens of
#: milliseconds long, so more than a couple overlapping means something is
#: firing far too often -- and the cap is what stops a runaway from growing the
#: list without bound. Sixteen is generous enough never to clip a real one.
_MAX_LIVE_STREAMS = 16


class _SoundLibBackend:
    """BASS-backed earcon player via the ``sound_lib`` package.

    BASS supports simultaneous streams, so no queue or serialisation thread is
    needed. What *is* needed -- and was missing until 2026-09-10 -- is somewhere
    to keep each stream while it plays.

    **The bug this fixes made every earcon silent on this backend.**
    ``play_wav`` created a ``FileStream``, called ``play()``, and returned. The
    local name was then the only reference, so CPython freed the wrapper on the
    spot, ``FileStream.__del__`` freed the BASS handle, and the sound stopped
    before it had been heard -- reliably, on every event, for anybody whose
    machine had ``sound_lib`` installed. ``autofree=True`` looks like it covers
    this and does not: it tells *BASS* to reclaim the handle when playback ends,
    which says nothing about when *Python* reclaims the wrapper.

    It went unnoticed because the failure is silence, and silence is what a
    disabled earcon looks like too. Confirmed by ear, A/B: identical code with
    the stream held plays, with the stream dropped does not.

    So a stream lives in :attr:`_live` until it has finished, and each call
    prunes the ones that have. Cheap -- the list is empty most of the time --
    and it needs no timer and no thread.
    """

    def __init__(self) -> None:
        # Import deferred to keep the module importable without sound_lib.
        import threading

        from sound_lib.output import Output  # type: ignore[import-untyped]

        self._output = Output()
        self._live: list[object] = []
        self._live_lock = threading.Lock()
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
            # Held *before* play(), not after: between the two there is no
            # reference but the local, and that is the window the old code
            # died in.
            self._hold(stream)
            stream.play()
        except Exception:  # noqa: BLE001
            logger.warning("SoundPlayer (sound_lib): playback failed", exc_info=True)

    def play_wav_blocking(self, wav: bytes, timeout: float) -> bool:
        """Play *wav* and poll the stream until BASS says it has stopped.

        Asking the device rather than computing a duration from the header, and
        the difference is not academic: a custom goodbye somebody drops in could
        be any length, a device could be resampling, and a header says what the
        file *contains* rather than when the speaker stops. Reported as exactly
        that -- "shouldn't we have a better way of not cutting off the sound
        than timing delays?"

        *timeout* is still a hard ceiling, because this runs on the way out of
        the app and an exit that appears to hang is worse than one that clips.
        It is a backstop for a stream that never reports finishing, not the
        mechanism.
        """
        import time

        try:
            from sound_lib.stream import FileStream  # type: ignore[import-untyped]

            stream = FileStream(mem=True, file=wav, offset=0, length=len(wav), autofree=False)
            stream.play()
        except Exception:  # noqa: BLE001
            logger.warning("SoundPlayer (sound_lib): blocking playback failed", exc_info=True)
            return False
        deadline = time.monotonic() + max(0.0, timeout)
        try:
            while time.monotonic() < deadline:
                if not bool(stream.is_playing):
                    return True
                time.sleep(0.01)
            return True  # the ceiling is an answer too: it played for as long as allowed
        except Exception:  # noqa: BLE001 - a freed handle means it has finished
            return True
        finally:
            try:
                stream.free()
            except Exception:  # noqa: BLE001
                pass

    def _hold(self, stream: object) -> None:
        """Keep *stream* alive while it plays, and let go of the finished ones."""
        with self._live_lock:
            self._live = [held for held in self._live if _still_playing(held)]
            self._live.append(stream)
            if len(self._live) > _MAX_LIVE_STREAMS:
                # Only reachable if something is firing earcons faster than they
                # finish, which is a bug at the call site. Drop the oldest rather
                # than grow without bound.
                del self._live[:-_MAX_LIVE_STREAMS]

    def set_volume(self, volume: float) -> None:
        try:
            self._output.set_volume(volume)
        except Exception:  # noqa: BLE001
            pass

    def shutdown(self, timeout: float = 2.0) -> None:
        with self._live_lock:
            self._live.clear()
        try:
            self._output.free()
        except Exception:  # noqa: BLE001
            pass


def _still_playing(stream: object) -> bool:
    """Whether *stream* has more to say. Assumes yes when it cannot tell.

    Erring towards keeping a reference: holding one a moment too long costs a
    few bytes, and letting go a moment too early is the bug this whole class
    now exists to avoid.
    """
    try:
        return bool(getattr(stream, "is_playing", True))
    except Exception:  # noqa: BLE001 - a freed handle raises rather than answering
        return False


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

    def play_wav_blocking(self, wav: bytes, timeout: float) -> bool:
        """Play *wav* on the calling thread and return when it is done.

        ``PlaySound`` without ``SND_ASYNC`` blocks until the clip finishes,
        which is exactly the semantics wanted here -- so the backend that
        normally needs a serialising worker is the one that needs no extra
        machinery for this. *timeout* is unused: winsound offers no way to cut a
        synchronous play short, and the alternative would be a thread to abandon
        it in, which is more moving parts than an exit path should have.
        """
        del timeout
        try:
            self._winsound.PlaySound(wav, self._winsound.SND_MEMORY | self._winsound.SND_NODEFAULT)
        except Exception:  # noqa: BLE001
            logger.warning("SoundPlayer (winsound): blocking playback failed", exc_info=True)
            return False
        return True

    def set_volume(self, volume: float) -> None:
        # winsound has no per-stream volume control; ignored by design.
        pass

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
# Backend: NSSound (AppKit) — macOS fallback when sound_lib is absent
# ---------------------------------------------------------------------------


class _NSSoundBackend:
    """AppKit ``NSSound``-backed earcon player for macOS.

    macOS has no stdlib playback module equivalent to Windows' ``winsound``,
    so when the licensed ``sound_lib`` (BASS) extra is not installed -- the
    normal case for QUILL's macOS build, see the ``audio`` extra's docstring
    in ``pyproject.toml`` -- earcons would otherwise be silent. ``pyobjc`` is
    already a build/runtime dependency of the ``macos`` extra (used for the
    Foundation Models bridge), so selecting this backend adds no new
    dependency.

    ``NSSound`` plays asynchronously and must be kept alive until playback
    finishes or AppKit tears it down mid-sound. Rather than track completion
    with a delegate, a small bounded list of the most recently started sounds
    is retained -- earcons are short, so by the time the list wraps around,
    earlier entries have long finished playing.
    """

    _MAX_LIVE: int = 16

    def __init__(self) -> None:
        # Import deferred to keep the module importable without pyobjc.
        from AppKit import NSSound  # type: ignore[import-not-found]

        self._NSSound = NSSound
        self._live: list[object] = []
        self._volume: float = 1.0
        logger.debug("SoundPlayer: using NSSound (AppKit) backend")

    def play_wav(self, wav: bytes) -> None:
        try:
            from Foundation import NSData  # type: ignore[import-not-found]  # noqa: F401

            data = NSData.dataWithBytes_length_(wav, len(wav))
            sound = self._NSSound.alloc().initWithData_(data)
            if sound is None:
                return
            # Apply the current master volume to this sound. NSSound has no global
            # volume; each played sound must be set individually, so without this
            # the earcon volume slider had no effect on macOS.
            try:
                sound.setVolume_(self._volume)
            except Exception:  # noqa: BLE001
                pass
            sound.play()
            self._live.append(sound)
            if len(self._live) > self._MAX_LIVE:
                del self._live[: -self._MAX_LIVE]
        except Exception:  # noqa: BLE001
            logger.warning("SoundPlayer (NSSound): playback failed", exc_info=True)

    def set_volume(self, volume: float) -> None:
        try:
            self._volume = max(0.0, min(1.0, float(volume)))
        except (TypeError, ValueError):
            pass

    def shutdown(self, timeout: float = 2.0) -> None:
        self._live.clear()


# ---------------------------------------------------------------------------
# Backend: null — silent no-op
# ---------------------------------------------------------------------------


class _NullBackend:
    def play_wav(self, wav: bytes) -> None:
        pass

    def set_volume(self, volume: float) -> None:
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

    try:
        return _NSSoundBackend()
    except Exception:  # noqa: BLE001
        logger.debug("NSSound (AppKit) unavailable", exc_info=False)

    logger.warning(
        "SoundPlayer: no audio backend available; earcons will be silent. "
        "Install sound_lib for cross-platform audio: pip install sound_lib"
    )
    return _NullBackend()


# ---------------------------------------------------------------------------
# SoundPlayer — public facade
# ---------------------------------------------------------------------------


#: The longest an exit cue may hold the app open. Matched to
#: ``sound_scheme.MAX_SOUND_SECONDS``, which is the longest sound the Sound
#: Scheme window will *accept* -- so any goodbye a user is allowed to install
#: plays in full, and the ceiling only ever catches a stream that fails to
#: report finishing. Picking a smaller number here would mean the app refusing
#: to play a sound it had just told the user was fine.
MAX_BLOCKING_SECONDS = 10.0


def _wav_seconds(wav: bytes) -> float:
    """How long *wav* plays for, from its own header. 0.0 when unreadable.

    Zero rather than a guess: a caller waiting on this is holding a window open,
    and a header that cannot be parsed is not a reason to hold it open longer.
    """
    import io
    import wave

    try:
        with wave.open(io.BytesIO(wav), "rb") as handle:
            rate = handle.getframerate()
            return handle.getnframes() / rate if rate else 0.0
    except Exception:  # noqa: BLE001 - an unreadable header is not an error here
        return 0.0


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

    def unregister_event(self, event_id: str) -> None:
        """Remove a single event from the active pack.

        No-op when *event_id* is not present. Used by the indent tone overlay
        to drop its events when the overlay is cleared.
        """
        with self._lock:
            self._events.pop(event_id, None)
            self._cooldowns.pop(event_id, None)

    def unregister_events(self, event_ids: frozenset[str] | Iterable[str]) -> None:
        """Remove a batch of event IDs from the active pack."""
        with self._lock:
            for event_id in event_ids:
                self._events.pop(event_id, None)
                self._cooldowns.pop(event_id, None)

    def set_volume(self, volume: float) -> None:
        """Set the master playback volume on the active backend.

        *volume* is in the range ``[0.0, 1.0]`` and is passed through to the
        backend's volume control when one exists; backends without a volume
        control (winsound, null) silently ignore the call. Never raises.
        """
        try:
            clamped = max(0.0, min(1.0, float(volume)))
        except (TypeError, ValueError):
            return
        try:
            self._backend.set_volume(clamped)
        except Exception:  # noqa: BLE001
            pass

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

    def preview_wav(self, wav: bytes) -> None:
        """Play *wav* now, ignoring the pack, the disabled set and the cooldown.

        A preview has to bypass all three or it cannot do its job. The whole
        reason somebody opens the Sound Scheme window is to hear an event they
        have switched *off*, or one they are about to change, or the same one
        four times in a row while deciding -- and every one of those is
        something :meth:`play` is built to refuse. Mute is honoured, because
        mute means the user has said "not now" about the whole app.
        """
        with self._lock:
            if self._muted:
                return
        self._backend.play_wav(wav)

    def play_and_wait(self, event_id: str, timeout: float = MAX_BLOCKING_SECONDS) -> None:
        """Play *event_id* and do not return until it has finished.

        For exactly one situation: the cue that says the app is closing. Every
        other earcon must return instantly, because it is commenting on
        something the user is in the middle of. The goodbye is the opposite --
        the next thing that happens is the process ending, so an asynchronous
        play is a sound that gets cut off mid-note, which is what somebody
        actually reported hearing.

        Waited out by the clip's own length, read from its header, rather than
        by asking the backend: the two backends answer that question
        differently and one of them cannot answer it at all, while a WAV header
        is a WAV header. *timeout* is a hard ceiling, so a pack with a
        thirty-second goodbye cannot hold the window open -- an exit that seems
        to hang is worse than a cue that is clipped.
        """
        import time

        with self._lock:
            if self._muted:
                return
            if event_id in self._disabled:
                return
            wav = self._events.get(event_id)
        if wav is None:
            return
        # Ask the backend to tell us when it has finished. Only when it cannot
        # do we fall back to the clip's own header -- which is a good estimate
        # of a file and a poor one of a speaker.
        blocking = getattr(self._backend, "play_wav_blocking", None)
        if callable(blocking) and blocking(wav, timeout):
            return
        self._backend.play_wav(wav)
        time.sleep(min(timeout, max(0.0, _wav_seconds(wav))))

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
