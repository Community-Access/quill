"""Silence trimming before batch transcription (the anti-hallucination pass).

Whisper-family decoders are language models at heart: fed silence, they decode
the *likeliest text anyway* — the phantom "thank you", the invented subtitle
credit. Dictation audio is mostly short utterances wrapped in silence, so this
failure lands exactly where QUILL's users dictate. The Handy project
(D:\\code\\handy) filters every recording through Silero VAD before Whisper for
this reason; this module gives QUILL the same pre-pass, in two tiers:

- **RMS tier (always available).** Pure stdlib: windowed root-mean-square
  energy locates where speech begins and ends; the WAV is trimmed to that span
  plus padding. It reuses the calibration of :mod:`quill.core.speech.vad`
  (the Hey-QUILL turn-taking detector) and needs no model, so *every* engine —
  whisper.cpp included, today — stops being fed long silent lead-ins/outs. A
  recording that contains no speech at all is reported as such, and the
  dictation flow turns that into its honest NO_SPEECH feedback instead of
  handing Whisper an invitation to invent.
- **Silero tier (when installed).** The Parakeet 3 model bundle ships
  sherpa-onnx's ``silero_vad.onnx`` (~0.6 MB); when sherpa-onnx and that file
  are present, the neural VAD refines the same decision. Strictly best-effort:
  any failure falls back to the RMS tier, and the RMS tier's answer is always
  safe because it only ever trims *quiet* audio.

The pass never rewrites speech — it only removes leading/trailing quiet and
answers "was there any speech at all?". Windows and thresholds are pure and
unit-tested; the wx shell calls :func:`trim_for_transcription` on the captured
WAV between recorder and engine.
"""

from __future__ import annotations

import shutil
import struct
import wave
from dataclasses import dataclass
from pathlib import Path

#: Analysis window. 30 ms is Silero's native hop and fine-grained enough that
#: padding, not window size, decides how much quiet survives around speech.
_WINDOW_MS = 30
#: Quiet kept on each side of detected speech, so plosives and soft onsets are
#: never clipped. Generous by design: the goal is removing *seconds* of
#: silence, not shaving milliseconds.
_PADDING_MS = 250
#: A window at or above this RMS (of 16-bit full scale) counts as speech.
#: Matches DEFAULT_SPEECH_RMS in quill.core.speech.vad — one calibration for
#: both "has the speaker stopped?" and "where did speech happen?".
_SPEECH_RMS = 500.0
#: Ignore trims that would remove less than this much audio: rewriting a WAV
#: to save a quarter second is churn, not signal.
_MIN_SAVINGS_MS = 400


@dataclass(frozen=True, slots=True)
class TrimResult:
    """What the pre-pass decided about one recording."""

    #: Path to feed the engine: the trimmed copy, or the original when no trim
    #: was worth making.
    path: Path
    #: True when no window reached the speech threshold — the honest
    #: "nothing was said" signal the dictation flow can act on *without*
    #: running (and paying for) a transcription that can only hallucinate.
    silent: bool
    #: Seconds removed (0.0 when the original was kept).
    trimmed_seconds: float


def _window_rms_values(frames: bytes, frame_count: int, window_frames: int) -> list[float]:
    """RMS per window over little-endian PCM-16 mono frames (pure)."""
    values: list[float] = []
    for start in range(0, frame_count, window_frames):
        chunk = frames[start * 2 : min(frame_count, start + window_frames) * 2]
        count = len(chunk) // 2
        if count == 0:
            break
        samples = struct.unpack(f"<{count}h", chunk[: count * 2])
        total = 0.0
        for sample in samples:
            total += float(sample) * float(sample)
        values.append((total / count) ** 0.5)
    return values


def speech_span(
    rms_values: list[float], *, threshold: float = _SPEECH_RMS
) -> tuple[int, int] | None:
    """First and last speech-window indices, or None when all quiet (pure)."""
    first = None
    last = None
    for index, value in enumerate(rms_values):
        if value >= threshold:
            if first is None:
                first = index
            last = index
    if first is None or last is None:
        return None
    return first, last


def trim_for_transcription(wav_path: Path, out_dir: Path) -> TrimResult:
    """Trim leading/trailing silence from *wav_path* into *out_dir*.

    Only 16-bit mono WAVs (the dictation capture format) are analysed; anything
    else passes through untouched — this pre-pass must never be the reason a
    transcription fails. The Silero refinement rides on the same decision shape
    and is attempted only when its runtime and model happen to be installed.
    """
    try:
        with wave.open(str(wav_path), "rb") as wf:
            channels = wf.getnchannels()
            width = wf.getsampwidth()
            rate = wf.getframerate()
            frame_count = wf.getnframes()
            if channels != 1 or width != 2 or rate <= 0 or frame_count == 0:
                return TrimResult(path=wav_path, silent=frame_count == 0, trimmed_seconds=0.0)
            frames = wf.readframes(frame_count)
    except Exception:  # noqa: BLE001 - unreadable audio: hand it on unchanged
        return TrimResult(path=wav_path, silent=False, trimmed_seconds=0.0)

    window_frames = max(1, (rate * _WINDOW_MS) // 1000)
    rms_values = _window_rms_values(frames, frame_count, window_frames)
    span = speech_span(rms_values)
    # Silero refinement: same decision, a model instead of an energy gate. It
    # may only *narrow* the RMS span (neural "that hum was not speech"), never
    # widen it — RMS marks everything loud, so anything outside its span is
    # genuinely quiet and safe to drop regardless of what a model thinks.
    if span is not None:
        neural = _silero_span(frames, frame_count, rate, window_frames)
        if neural is not None:
            span = (max(span[0], neural[0]), min(span[1], neural[1]))
            if span[0] > span[1]:
                span = neural
    if span is None:
        return TrimResult(path=wav_path, silent=True, trimmed_seconds=0.0)

    padding_windows = max(1, _PADDING_MS // _WINDOW_MS)
    first = max(0, span[0] - padding_windows)
    last = min(len(rms_values) - 1, span[1] + padding_windows)
    start_frame = first * window_frames
    end_frame = min(frame_count, (last + 1) * window_frames)
    removed_frames = start_frame + (frame_count - end_frame)
    if (removed_frames * 1000) // rate < _MIN_SAVINGS_MS:
        return TrimResult(path=wav_path, silent=False, trimmed_seconds=0.0)

    out_dir.mkdir(parents=True, exist_ok=True)
    trimmed_path = out_dir / (wav_path.stem + ".trimmed.wav")
    try:
        with wave.open(str(trimmed_path), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(rate)
            out.writeframes(frames[start_frame * 2 : end_frame * 2])
    except Exception:  # noqa: BLE001 - failing to write the trim keeps the original
        shutil.rmtree(trimmed_path, ignore_errors=True)
        return TrimResult(path=wav_path, silent=False, trimmed_seconds=0.0)
    return TrimResult(
        path=trimmed_path,
        silent=False,
        trimmed_seconds=removed_frames / float(rate),
    )


def _silero_span(
    frames: bytes, frame_count: int, rate: int, window_frames: int
) -> tuple[int, int] | None:
    """Speech span as window indices per Silero VAD, or None when unavailable.

    Best-effort by contract: no sherpa-onnx, no model file, an API mismatch, or
    any runtime error simply returns None and the RMS tier's answer stands.
    """
    model = silero_model_path()
    if model is None:
        return None
    try:
        import numpy as np  # type: ignore[import]
        import sherpa_onnx  # type: ignore[import-not-found,import-untyped]

        config = sherpa_onnx.VadModelConfig()
        config.silero_vad.model = str(model)
        config.sample_rate = rate
        detector = sherpa_onnx.VoiceActivityDetector(
            config, buffer_size_in_seconds=max(1.0, frame_count / float(rate))
        )
        samples = np.frombuffer(frames[: frame_count * 2], dtype=np.int16)
        detector.accept_waveform(samples.astype(np.float32) / 32768.0)
        detector.flush()
        first_frame: int | None = None
        last_frame: int | None = None
        while not detector.empty():
            segment = detector.front
            start = int(segment.start)
            end = start + len(segment.samples)
            first_frame = start if first_frame is None else min(first_frame, start)
            last_frame = end if last_frame is None else max(last_frame, end)
            detector.pop()
        if first_frame is None or last_frame is None:
            return None
        return (first_frame // window_frames, max(0, (last_frame - 1)) // window_frames)
    except Exception:  # noqa: BLE001 - the RMS tier is the answer of record
        return None


def silero_model_path() -> Path | None:
    """The installed ``silero_vad.onnx``, if any Parakeet/Nemotron bundle has one.

    The Parakeet 3 mirror zip ships it; resolution is by inspection rather than
    registration so a hand-installed bundle counts too.
    """
    from quill.core.speech import models

    root = models.models_root()
    for provider_dir in ("parakeet", "nemotron"):
        base = root / provider_dir
        if not base.is_dir():
            continue
        for found in sorted(base.rglob("silero_vad.onnx")):
            if found.is_file():
                return found
    return None
