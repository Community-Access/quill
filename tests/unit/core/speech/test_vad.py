"""Tests for voice-activity end-of-turn detection (Hey QUILL refinement)."""

from __future__ import annotations

import struct

from quill.core.speech.vad import SilenceDetector, rms


def _pcm(amplitude: int, ms: int, sample_rate: int = 16000) -> bytes:
    n = sample_rate * ms // 1000
    return struct.pack(f"<{n}h", *([amplitude] * n))


# Most tests inject speech from the first chunk, so they disable the ambient
# calibration window (calibrate_ms=0) to exercise the core turn logic directly.
def _det(**kw) -> SilenceDetector:
    kw.setdefault("calibrate_ms", 0)
    return SilenceDetector(**kw)


def test_rms_of_silence_is_zero_and_loud_is_high() -> None:
    assert rms(_pcm(0, 100)) == 0.0
    assert rms(_pcm(8000, 100)) > 1000.0


def test_turn_ends_after_speech_then_silence() -> None:
    d = _det(sample_rate=16000, silence_ms=1000, min_speech_ms=200)
    assert d.feed(_pcm(6000, 400)) is False
    assert d.heard_speech is True
    assert d.feed(_pcm(0, 600)) is False
    assert d.feed(_pcm(0, 500)) is True


def test_silence_before_any_speech_never_ends_the_turn() -> None:
    d = _det(silence_ms=500, min_speech_ms=200)
    for _ in range(10):
        assert d.feed(_pcm(0, 300)) is False
    assert d.heard_speech is False


def test_brief_blip_below_min_speech_does_not_arm() -> None:
    d = _det(silence_ms=500, min_speech_ms=300)
    d.feed(_pcm(6000, 100))
    assert d.heard_speech is False
    assert d.feed(_pcm(0, 1000)) is False


def test_silence_run_resets_when_speech_resumes() -> None:
    d = _det(silence_ms=1000, min_speech_ms=200)
    d.feed(_pcm(6000, 300))
    d.feed(_pcm(0, 800))
    d.feed(_pcm(6000, 200))
    assert d.feed(_pcm(0, 800)) is False


def test_zero_silence_window_disables_detection() -> None:
    d = _det(silence_ms=0)
    for _ in range(20):
        assert d.feed(_pcm(0, 500)) is False


def test_reset_clears_state() -> None:
    d = _det(silence_ms=500, min_speech_ms=100)
    d.feed(_pcm(6000, 300))
    d.reset()
    assert d.heard_speech is False


# -- adaptive noise-floor calibration (real-hardware finding) ----------------


def test_calibration_raises_threshold_above_a_noisy_ambient_floor() -> None:
    # A noisy mic idling at RMS ~700 (a real USB headset) must not read its own
    # hiss as speech. Calibrate on 300 ms of that noise, then confirm quiet-ish
    # noise no longer counts as speech but real speech still does.
    d = SilenceDetector(silence_ms=800, min_speech_ms=200, calibrate_ms=300, speech_rms=500)
    d.feed(_pcm(700, 300))  # ambient calibration window
    assert d.threshold > 700  # threshold rose above the noise floor
    # Continued ambient noise is not speech, so the turn cannot end on it.
    for _ in range(10):
        assert d.feed(_pcm(700, 200)) is False
    assert d.heard_speech is False
    # Real speech (several thousand RMS) is clearly above the calibrated floor.
    d.feed(_pcm(6000, 400))
    assert d.heard_speech is True


def test_calibration_keeps_the_absolute_floor_in_a_quiet_room() -> None:
    # In a silent room the ambient floor is ~0, so the threshold stays at the
    # absolute speech_rms floor rather than collapsing to zero.
    d = SilenceDetector(silence_ms=800, min_speech_ms=200, calibrate_ms=300, speech_rms=500)
    d.feed(_pcm(0, 300))  # dead-quiet calibration
    assert d.threshold == 500
    d.feed(_pcm(6000, 300))
    assert d.heard_speech is True


def test_calibration_window_is_not_counted_as_speech() -> None:
    # Even loud audio during the calibration window is treated as ambient, so a
    # turn never ends purely because the leading audio was loud.
    d = SilenceDetector(silence_ms=400, min_speech_ms=100, calibrate_ms=300)
    assert d.feed(_pcm(6000, 300)) is False
    assert d.heard_speech is False


def test_speech_right_after_calibration_is_still_detected() -> None:
    # Regression (#796 review): if the user starts talking the moment the mic
    # opens, the calibration window is dominated by speech. With a min-based
    # floor plus a quiet inter-word chunk, the detector must still recognize
    # speech afterwards instead of setting an unreachable threshold.
    d = SilenceDetector(silence_ms=800, min_speech_ms=200, calibrate_ms=300, speech_rms=500)
    # Speaking immediately: one loud chunk and one quieter gap inside the window.
    d.feed(_pcm(6000, 150))
    d.feed(_pcm(300, 150))  # brief inter-word dip supplies the true floor
    assert d.threshold <= 1500, "calibration must not be dominated by leading speech"
    d.feed(_pcm(6000, 400))
    assert d.heard_speech is True


def test_contaminated_calibration_recovers_on_first_quiet_chunk() -> None:
    # Worst case: the entire calibration window is loud speech (floor ~6000,
    # threshold 15000). The first genuinely quiet chunk after calibration must
    # re-floor the detector so the rest of the turn works.
    d = SilenceDetector(silence_ms=800, min_speech_ms=200, calibrate_ms=300, speech_rms=500)
    d.feed(_pcm(6000, 300))  # calibration entirely dominated by speech
    assert d.threshold > 5000  # contaminated, as the regression described
    d.feed(_pcm(200, 200))  # first real pause lowers the floor again
    assert d.threshold == 500
    d.feed(_pcm(6000, 400))
    assert d.heard_speech is True
