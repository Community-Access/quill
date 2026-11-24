"""What the queue should take, scaled from the preview's own encode (FUX-11).

**Preview with Your Settings** encodes a few seconds with the batch's real
command before it plays them. That encode is a measurement: how long these
settings take on this computer, and how large they make the sound. Scaled to
the queue's length it is an honest estimate of the whole batch, said with the
preview's limits (:mod:`quill.core.rehearsal`).

Some settings make the preview a poor measure, and then no estimate is given
rather than a wrong one: a video format (the preview encodes the sound only),
copying the sound without re-encoding (the preview re-encodes it), and the
Original preview (no settings at all).

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Sequence

from quill.core.audio.convert import ConversionSpec
from quill.core.audio.formats import VIDEO_OUTPUT_FORMATS
from quill.core.rehearsal import SampleResult, estimate_sentence, fingerprint, limits_sentence

__all__ = ["estimable", "queue_estimate"]


def estimable(spec: ConversionSpec) -> str:
    """``""`` when a preview measures *spec* fairly, else why it does not."""
    if spec.fmt.strip().lower() in VIDEO_OUTPUT_FORMATS or spec.copy_video:
        return "A video's picture is not part of the preview, so there is no estimate."
    if spec.start_s or spec.end_s:
        return "The batch keeps only part of each file, so there is no estimate."
    if spec.copy_audio:
        return "The preview re-encodes sound that the batch copies, so there is no estimate."
    return ""


def queue_estimate(
    *,
    source_name: str,
    spec: ConversionSpec,
    clip_seconds: float,
    encode_seconds: float,
    encoded_bytes: int,
    durations: Sequence[float],
) -> str:
    """One status line: the preview's measurement, the queue's estimate, the limits."""
    why_not = estimable(spec)
    if why_not:
        return why_not
    total = sum(max(0.0, d) for d in durations)
    count = len(durations)
    result = SampleResult(
        fingerprint=fingerprint({"spec": repr(spec)}),
        covered=f"{round(clip_seconds)} seconds of {source_name}",
        sample_units=clip_seconds,
        total_units=total,
        elapsed_seconds=encode_seconds,
        output_bytes=encoded_bytes,
    )
    whole = "the one file in the queue" if count == 1 else f"the {count} files in the queue"
    return (
        f"{estimate_sentence(result, job=f'converting {whole}')} {limits_sentence(result.covered)}"
    )
