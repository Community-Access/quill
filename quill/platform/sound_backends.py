"""What a sound backend has to look like: the mandatory half and the optional one.

Split out of :mod:`quill.platform.sound_player` on 2026-09-10 (GATE-11), and
better placed here anyway: a protocol is an interface, and a caller that only
wants to type-check one should not have to import six hundred lines of BASS,
winsound and NSSound handling to do it.

The split into two is the substantive part. ``play_wav_blocking`` was briefly a
fourth method on the mandatory protocol, which made ``isinstance`` answer **no**
for ``_NullBackend``, ``_RecordingBackend`` and ``_NSSoundBackend`` -- three
shipped classes that are perfectly good backends and simply cannot tell when a
sound ended. A protocol that rejects the code it describes is worse than none,
so the optional capability gets a protocol of its own and
``SoundPlayer.play_and_wait`` keeps checking for the method before calling it.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = ["BlockingWavBackend", "WavBackend"]


@runtime_checkable
class WavBackend(Protocol):
    """Minimal interface a playback backend must satisfy."""

    def play_wav(self, wav: bytes) -> None:
        """Play *wav* bytes.  Must return promptly; never raises."""
        ...

    def set_volume(self, volume: float) -> None:
        """Set the master output volume in ``[0.0, 1.0]``.  Never raises;
        backends without a volume control silently ignore the call."""
        ...

    def shutdown(self, timeout: float = 2.0) -> None:
        """Release resources.  Called once at player teardown."""
        ...


@runtime_checkable
class BlockingWavBackend(Protocol):
    """The *optional* half: a backend that can say when a sound actually ended.

    Separate from :class:`WavBackend` because three shipped backends do not
    implement it and are still good backends; as a fourth mandatory method it
    made ``isinstance`` say no to all three.
    """

    def play_wav_blocking(self, wav: bytes, timeout: float) -> bool:
        """True when the sound genuinely ended, False when it cannot tell.

        ``SoundPlayer.play_and_wait`` checks for the method before calling, so a
        backend without it degrades to the timed fallback rather than failing.
        """
        ...
