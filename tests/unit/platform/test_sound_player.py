"""Tests for :mod:`quill.platform.sound_player`.

Uses an injected ``_RecordingBackend`` so no audio hardware is touched and
no async behaviour needs to be waited on -- ``play_wav`` records synchronously.
"""

from __future__ import annotations

import time

from quill.core.sound_pack import SoundPack
from quill.platform.sound_player import (
    _COOLDOWN_S,
    SoundPlayer,
    _NullBackend,
    _WavBackend,
    _WinsoundBackend,
)

_WAV_A = b"WAV-A"
_WAV_B = b"WAV-B"


# ---------------------------------------------------------------------------
# Test backend
# ---------------------------------------------------------------------------


class _RecordingBackend:
    """Synchronous backend that records played bytes."""

    def __init__(self) -> None:
        self.played: list[bytes] = []
        self.shutdown_called: bool = False

    def play_wav(self, wav: bytes) -> None:
        self.played.append(wav)

    def shutdown(self, timeout: float = 2.0) -> None:
        self.shutdown_called = True


def _player(*event_ids: str, wav: bytes = _WAV_A) -> tuple[SoundPlayer, _RecordingBackend]:
    backend = _RecordingBackend()
    pack = SoundPack(
        name="Test",
        author="",
        description="",
        license="",
        events={eid: wav for eid in event_ids},
    )
    player = SoundPlayer(backend=backend)
    player.load_pack(pack)
    return player, backend


# ---------------------------------------------------------------------------
# _WavBackend protocol
# ---------------------------------------------------------------------------


def test_recording_backend_satisfies_protocol() -> None:
    assert isinstance(_RecordingBackend(), _WavBackend)


def test_null_backend_satisfies_protocol() -> None:
    assert isinstance(_NullBackend(), _WavBackend)


# ---------------------------------------------------------------------------
# Basic playback
# ---------------------------------------------------------------------------


def test_play_known_event() -> None:
    player, backend = _player("abbreviation_expanded", wav=_WAV_A)
    player.play("abbreviation_expanded")
    assert backend.played == [_WAV_A]


def test_play_unknown_event_is_silent() -> None:
    player, backend = _player("abbreviation_expanded")
    player.play("no_such_event")
    assert backend.played == []


def test_play_multiple_distinct_events() -> None:
    backend = _RecordingBackend()
    pack = SoundPack(
        name="T",
        author="",
        description="",
        license="",
        events={"abbreviation_expanded": _WAV_A, "document_saved": _WAV_B},
    )
    player = SoundPlayer(backend=backend)
    player.load_pack(pack)
    player.play("abbreviation_expanded")
    player.play("document_saved")
    assert set(backend.played) == {_WAV_A, _WAV_B}


def test_empty_pack_is_silent() -> None:
    backend = _RecordingBackend()
    player = SoundPlayer(backend=backend)
    player.load_pack(SoundPack(name="Empty", author="", description="", license=""))
    player.play("abbreviation_expanded")
    assert backend.played == []


# ---------------------------------------------------------------------------
# Mute
# ---------------------------------------------------------------------------


def test_muted_player_is_silent() -> None:
    player, backend = _player("abbreviation_expanded")
    player.set_muted(True)
    player.play("abbreviation_expanded")
    assert backend.played == []


def test_toggle_mute_flips_state() -> None:
    backend = _RecordingBackend()
    player = SoundPlayer(backend=backend)
    assert player.muted is False
    assert player.toggle_mute() is True
    assert player.muted is True
    assert player.toggle_mute() is False


def test_unmuting_restores_playback() -> None:
    player, backend = _player("abbreviation_expanded")
    player.set_muted(True)
    player.play("abbreviation_expanded")
    player.set_muted(False)
    player.play("abbreviation_expanded")
    assert len(backend.played) == 1


# ---------------------------------------------------------------------------
# Disabled events
# ---------------------------------------------------------------------------


def test_disabled_event_is_silent() -> None:
    backend = _RecordingBackend()
    pack = SoundPack(
        name="T",
        author="",
        description="",
        license="",
        events={"abbreviation_expanded": _WAV_A, "document_saved": _WAV_B},
    )
    player = SoundPlayer(backend=backend)
    player.load_pack(pack, disabled=frozenset({"abbreviation_expanded"}))
    player.play("abbreviation_expanded")
    player.play("document_saved")
    assert backend.played == [_WAV_B]


def test_set_disabled_updates_filter() -> None:
    backend = _RecordingBackend()
    pack = SoundPack(
        name="T",
        author="",
        description="",
        license="",
        events={"abbreviation_expanded": _WAV_A, "document_saved": _WAV_B},
    )
    player = SoundPlayer(backend=backend)
    player.load_pack(pack)
    player.set_disabled(frozenset({"document_saved"}))
    player.play("abbreviation_expanded")
    player.play("document_saved")
    assert backend.played == [_WAV_A]


# ---------------------------------------------------------------------------
# Cooldown
# ---------------------------------------------------------------------------


def test_rapid_duplicate_events_are_deduplicated() -> None:
    player, backend = _player("abbreviation_expanded")
    player.play("abbreviation_expanded")
    player.play("abbreviation_expanded")
    assert len(backend.played) == 1


def test_same_event_allowed_after_cooldown() -> None:
    player, backend = _player("abbreviation_expanded")
    player.play("abbreviation_expanded")
    time.sleep(_COOLDOWN_S + 0.02)
    player.play("abbreviation_expanded")
    assert len(backend.played) == 2


def test_cooldown_is_per_event_id() -> None:
    backend = _RecordingBackend()
    pack = SoundPack(
        name="T",
        author="",
        description="",
        license="",
        events={"abbreviation_expanded": _WAV_A, "document_saved": _WAV_B},
    )
    player = SoundPlayer(backend=backend)
    player.load_pack(pack)
    player.play("abbreviation_expanded")
    player.play("document_saved")  # different id; cooldown does not apply
    assert len(backend.played) == 2


# ---------------------------------------------------------------------------
# load_pack resets cooldowns
# ---------------------------------------------------------------------------


def test_load_pack_resets_cooldown() -> None:
    player, backend = _player("abbreviation_expanded")
    player.play("abbreviation_expanded")
    player.load_pack(
        SoundPack(
            name="T2",
            author="",
            description="",
            license="",
            events={"abbreviation_expanded": _WAV_A},
        )
    )
    player.play("abbreviation_expanded")
    assert len(backend.played) == 2


# ---------------------------------------------------------------------------
# Shutdown forwarded to backend
# ---------------------------------------------------------------------------


def test_shutdown_calls_backend() -> None:
    backend = _RecordingBackend()
    player = SoundPlayer(backend=backend)
    player.shutdown()
    assert backend.shutdown_called is True


# ---------------------------------------------------------------------------
# _WinsoundBackend (integration: queue + thread, no audio hardware)
# ---------------------------------------------------------------------------


def test_winsound_backend_queue_drops_excess() -> None:
    """Posting more items than _WINSOUND_QUEUE_MAX while the worker is blocked
    should never raise and should play at most MAX+1 sounds total."""
    import threading

    from quill.platform.sound_player import _WINSOUND_QUEUE_MAX

    unblock = threading.Event()
    played: list[bytes] = []

    backend = _WinsoundBackend.__new__(_WinsoundBackend)
    # Replace internal winsound with a slow callable
    import queue as _queue

    backend._winsound = type(
        "_FakeWS",
        (),
        {  # type: ignore[attr-defined]
            "SND_MEMORY": 4,
            "SND_NODEFAULT": 2,
            "PlaySound": staticmethod(lambda data, flags: (unblock.wait(), played.append(data))),
        },
    )()
    backend._queue = _queue.Queue(maxsize=_WINSOUND_QUEUE_MAX)
    backend._thread = threading.Thread(target=backend._worker, daemon=True)
    backend._thread.start()

    for i in range(10):
        backend.play_wav(bytes([i]))

    unblock.set()
    backend.shutdown()

    assert len(played) <= _WINSOUND_QUEUE_MAX + 1


# ---------------------------------------------------------------------------
# #332 -- public set_volume / unregister_event(s) (was private _backend._output)
# ---------------------------------------------------------------------------


class _VolumeRecordingBackend(_RecordingBackend):
    """Recording backend that exposes a settable Output.volume for set_volume."""

    def __init__(self) -> None:
        super().__init__()
        self.volume: float | None = None
        outer = self

        class _Output:
            def set_volume(inner_self, v: float) -> None:  # noqa: N805
                outer.volume = v

        self._output = _Output()


def test_set_volume_clamps_and_forwards_to_backend() -> None:
    backend = _VolumeRecordingBackend()
    player = SoundPlayer(backend=backend)

    player.set_volume(0.5)
    assert backend.volume == 0.5

    # Values above 1.0 clamp down.
    player.set_volume(2.0)
    assert backend.volume == 1.0

    # Values below 0.0 clamp up.
    player.set_volume(-0.5)
    assert backend.volume == 0.0


def test_set_volume_is_silent_on_backends_without_output() -> None:
    backend = _RecordingBackend()  # no _output attr
    player = SoundPlayer(backend=backend)

    # Must not raise; the call is a no-op.
    player.set_volume(0.5)


def test_set_volume_ignores_non_numeric_argument() -> None:
    backend = _VolumeRecordingBackend()
    player = SoundPlayer(backend=backend)

    # Garbage in, no exception, no volume update.
    player.set_volume("nope")  # type: ignore[arg-type]
    assert backend.volume is None


def test_unregister_event_removes_a_single_event() -> None:
    player, _ = _player("alpha", "beta")
    assert "alpha" in player.loaded_event_ids()

    player.unregister_event("alpha")

    assert "alpha" not in player.loaded_event_ids()
    assert "beta" in player.loaded_event_ids()


def test_unregister_event_unknown_id_is_a_noop() -> None:
    player, _ = _player("alpha")
    player.unregister_event("does-not-exist")  # must not raise
    assert "alpha" in player.loaded_event_ids()


def test_unregister_events_removes_a_batch() -> None:
    player, _ = _player("a", "b", "c", "d")

    player.unregister_events(frozenset({"a", "c"}))

    remaining = player.loaded_event_ids()
    assert "a" not in remaining
    assert "c" not in remaining
    assert "b" in remaining
    assert "d" in remaining
