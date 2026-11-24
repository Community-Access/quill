"""Try a small sample before a long job, and say honestly what it proved (FUX-11).

The moment: "I don't want to record an hour before finding the microphone was
wrong." Before a long job -- a narrated book, a batch of conversions, a long
transcription, a recording -- the person can make a small sample with exactly
the settings and engine the real job will use, hear or read it, and get an
estimate measured on this computer rather than guessed.

Each app makes its own sample with its own pipeline; what is shared is the
honesty around it, so every app says the same things in the same words:

- what the sample covered, and that it does not prove the rest
  (:func:`limits_sentence`);
- what the whole job should take and make, scaled from what the sample
  actually took and made (:func:`estimate_sentence`), never more precise than
  the measurement allows;
- whether the sample still describes the settings now chosen
  (:func:`fingerprint`, :meth:`SampleResult.is_current`,
  :func:`stale_sentence`). A sample is kept only for the configuration it
  tested; when a setting changes, the earlier evidence is labelled out of
  date rather than silently reused.

A sample never replaces the real result, never writes into the job's output
folder and never changes a setting: the callers keep it in a temporary folder
and remove it when the window closes.

wx-free and strict-typed.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

from quill.core.audio.media_probe import format_size
from quill.core.windows_dictation.file_models import spoken_length

__all__ = [
    "Estimate",
    "SampleResult",
    "estimate_sentence",
    "fingerprint",
    "limits_sentence",
    "scale",
    "stale_sentence",
    "wait_phrase",
]


def fingerprint(settings: Mapping[str, object]) -> str:
    """A stable digest of every setting that shapes the job's result.

    Two calls agree only when every value agrees; key order does not matter.
    Values that are not JSON (paths, tuples) are compared by their text.
    """
    text = json.dumps(dict(settings), sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class Estimate:
    """The whole job, scaled from one sample. ``None`` means "not known"."""

    seconds: float | None = None  # how long the job should take to run
    output_bytes: int | None = None  # how large the result should be
    output_seconds: float | None = None  # how long the resulting audio should play


@dataclass(frozen=True, slots=True)
class SampleResult:
    """One finished sample and what it measured.

    *sample_units* and *total_units* are in the same unit the job counts in:
    words for narration, seconds of audio for a conversion or transcription.
    """

    fingerprint: str
    covered: str  # "the first 120 words of chapter-1.docx"
    sample_units: float
    total_units: float
    elapsed_seconds: float
    output_bytes: int | None = None
    output_seconds: float | None = None

    def is_current(self, current_fingerprint: str) -> bool:
        """Whether this sample was made with the settings chosen now."""
        return self.fingerprint == current_fingerprint

    def estimate(self) -> Estimate:
        """The whole job scaled from this sample (see :func:`scale`)."""
        return scale(
            sample_units=self.sample_units,
            total_units=self.total_units,
            elapsed_seconds=self.elapsed_seconds,
            output_bytes=self.output_bytes,
            output_seconds=self.output_seconds,
        )


def scale(
    *,
    sample_units: float,
    total_units: float,
    elapsed_seconds: float,
    output_bytes: int | None = None,
    output_seconds: float | None = None,
) -> Estimate:
    """Scale what a sample took and made up to the whole job, linearly.

    Nothing is estimated from an empty sample or an empty job: a guess from
    no evidence is worse than saying it is not known.
    """
    if sample_units <= 0 or total_units <= 0:
        return Estimate()
    factor = total_units / sample_units
    return Estimate(
        seconds=max(0.0, elapsed_seconds) * factor,
        output_bytes=None if output_bytes is None else int(max(0, output_bytes) * factor),
        output_seconds=None if output_seconds is None else max(0.0, output_seconds) * factor,
    )


def wait_phrase(seconds: float) -> str:
    """``"under a minute"`` or ``"about 1 hour 5 minutes"``, for sentences."""
    return "under a minute" if seconds < 60 else f"about {spoken_length(seconds)}"


def estimate_sentence(result: SampleResult, *, job: str = "the whole job") -> str:
    """What the whole job should take and make, measured on this computer.

    Says only the figures the sample measured, and says that they are an
    estimate. *job* names the whole job ("all 12 documents").
    """
    took = f"The sample took {spoken_length(result.elapsed_seconds)} to make."
    est = result.estimate()
    if est.seconds is None:
        return f"{took} There is no estimate for {job}, because its length is not known."
    parts = [f"take {wait_phrase(est.seconds)}"]
    if est.output_seconds is not None:
        parts.append(f"play for about {spoken_length(est.output_seconds)}")
    if est.output_bytes is not None:
        parts.append(f"be about {format_size(est.output_bytes)}")
    said = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
    return f"{took} At that pace {job} should {said} on this computer. This is an estimate."


def limits_sentence(covered: str) -> str:
    """What the sample did and did not prove."""
    return (
        f"This sample checks {covered} only, with your current settings. It does "
        "not prove the rest: a later part can still fail or sound different."
    )


def stale_sentence() -> str:
    """Said in place of a result whose settings have since changed."""
    return (
        "Out of date: a setting changed after this sample was made, so it no "
        "longer shows what the job will do. Try a sample again to check."
    )
