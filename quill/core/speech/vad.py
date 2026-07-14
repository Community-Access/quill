"""Voice-activity detection for conversation turns (Hey QUILL refinement).

Pure, wx-free, stdlib-only: decide when a spoken turn has *ended* by watching
the microphone's energy, so a conversation turn finishes when you stop talking
rather than after a fixed window (the ADP "silence window", WCAG 2.2.1). The UI
feeds successive PCM-16 mono chunks to :class:`SilenceDetector`; when speech has
been heard and then silence has persisted for the configured window, the
detector reports the turn is done and the UI stops the recording and
transcribes.

Energy is plain RMS over 16-bit samples — no numpy, no model. That is enough to
tell "someone is speaking" from "the room is quiet" for turn-taking; it is not
speech recognition and never leaves the machine.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

#: Default RMS threshold (0-32767) above which a chunk counts as speech. Tuned
#: for typical headset/laptop mics in a quiet-to-normal room.
DEFAULT_SPEECH_RMS = 500.0

#: A turn must contain at least this much speech before trailing silence can end
#: it, so a cough or a click cannot submit an empty turn.
DEFAULT_MIN_SPEECH_MS = 300


def rms(pcm16: bytes) -> float:
    """Root-mean-square amplitude of little-endian PCM-16 mono ``pcm16``."""
    count = len(pcm16) // 2
    if count == 0:
        return 0.0
    samples = struct.unpack(f"<{count}h", pcm16[: count * 2])
    total = 0.0
    for sample in samples:
        total += float(sample) * float(sample)
    return float((total / count) ** 0.5)


@dataclass(slots=True)
class SilenceDetector:
    """Streaming end-of-turn detector fed successive PCM-16 mono chunks.

    The speech threshold **calibrates to the room**: the first
    ``calibrate_ms`` of audio are treated as the ambient noise floor, and a
    chunk counts as speech only when it rises a clear margin above that floor
    (``speech_over_floor`` times it), never below ``speech_rms``. This keeps a
    noisy mic — a real-hardware pass found a USB headset idling at RMS ~700,
    above the old fixed 500 floor — from reading its own hiss as endless
    speech. Real speech runs several thousand RMS, so the margin is wide.

    Parameters
    ----------
    sample_rate:
        Frames per second of the incoming audio.
    silence_ms:
        Trailing quiet needed to end a turn once speech has been heard.
        ``0`` disables detection (:meth:`feed` never reports done).
    speech_rms:
        Absolute floor for the speech threshold (used when the room is quiet).
    min_speech_ms:
        Minimum total speech before trailing silence can end the turn.
    calibrate_ms:
        Leading audio measured as the ambient noise floor (0 disables
        calibration and uses ``speech_rms`` directly).
    speech_over_floor:
        A chunk is speech when its RMS exceeds ``ambient_floor`` times this.
    """

    sample_rate: int = 16000
    silence_ms: int = 2000
    speech_rms: float = DEFAULT_SPEECH_RMS
    min_speech_ms: int = DEFAULT_MIN_SPEECH_MS
    calibrate_ms: int = 300
    speech_over_floor: float = 2.5
    _speech_ms: float = field(default=0.0, repr=False)
    _silence_ms_run: float = field(default=0.0, repr=False)
    _heard_speech: bool = field(default=False, repr=False)
    _calibrated_ms: float = field(default=0.0, repr=False)
    _ambient: float = field(default=-1.0, repr=False)
    _threshold: float = field(default=0.0, repr=False)

    def __post_init__(self) -> None:
        self._threshold = self.speech_rms

    def reset(self) -> None:
        self._speech_ms = 0.0
        self._silence_ms_run = 0.0
        self._heard_speech = False
        self._calibrated_ms = 0.0
        self._ambient = -1.0
        self._threshold = self.speech_rms

    @property
    def heard_speech(self) -> bool:
        return self._heard_speech

    @property
    def threshold(self) -> float:
        """The current effective speech threshold (after any calibration)."""
        return self._threshold

    def _chunk_ms(self, pcm16: bytes) -> float:
        frames = len(pcm16) // 2
        return frames * 1000.0 / self.sample_rate if self.sample_rate else 0.0

    def feed(self, pcm16: bytes) -> bool:
        """Add one chunk; return True once the turn should end.

        A turn ends when at least ``min_speech_ms`` of speech has been heard and
        then ``silence_ms`` of trailing quiet has followed. With
        ``silence_ms == 0`` this always returns False (manual/timed submit).
        """
        if self.silence_ms <= 0:
            return False
        duration = self._chunk_ms(pcm16)
        level = rms(pcm16)

        # Calibrate the ambient floor from the leading audio, then set the
        # speech threshold above it (but never below the absolute floor). The
        # floor is the QUIETEST leading chunk, not the average: someone who
        # starts talking the instant the mic opens (or an earcon leaking in)
        # would otherwise inflate the floor so far that speech could never be
        # detected for the whole turn (#796 review).
        if self._calibrated_ms < self.calibrate_ms:
            self._ambient = level if self._ambient < 0 else min(self._ambient, level)
            self._calibrated_ms += duration
            if self._calibrated_ms >= self.calibrate_ms:
                self._threshold = max(self.speech_rms, self._ambient * self.speech_over_floor)
            # Leading audio is assumed ambient; do not count it as speech.
            return False

        # Keep re-flooring downward: if calibration was still contaminated by
        # speech, the first genuinely quiet chunk lowers the floor and the
        # detector recovers within the same turn.
        if 0 <= level < self._ambient:
            self._ambient = level
            self._threshold = max(self.speech_rms, self._ambient * self.speech_over_floor)

        if level >= self._threshold:
            self._speech_ms += duration
            self._silence_ms_run = 0.0
            if self._speech_ms >= self.min_speech_ms:
                self._heard_speech = True
        else:
            self._silence_ms_run += duration
        return self._heard_speech and self._silence_ms_run >= self.silence_ms


__all__ = [
    "DEFAULT_MIN_SPEECH_MS",
    "DEFAULT_SPEECH_RMS",
    "SilenceDetector",
    "rms",
]
