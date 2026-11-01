"""Fitting a drifted sound source to the picture in the mix (REC-022, mix half).

Every sound card has its own clock. Over a long recording a card that runs
fast delivers more samples than the minutes it covered, and its WAV slides
late against the picture and the other sources; one that runs slow slides
early. The capture side measures each source's sample count against the
session's monotonic length and writes the ratio into the segment's record
(``audio_timing[source_id]["drift_ratio"]``). This module decides, from that
measurement alone, whether the mix should stretch the source, and words the
correction for the verification report.

The measurement may be missing -- a recording made before it existed, or a
source that never delivered -- and is then treated as absent: no stretch,
nothing reported. A ratio outside a plausible band is a measurement fault,
not a clock, and is ignored the same way rather than wrecking the sound.

The lesson -- the sound card is the master clock, never the wall clock -- is
from Tony Gebhard's TG Drop Deck (https://github.com/tonygeb23/tg-drop-deck).
No code was copied.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

#: REC-022: a source off by more than this over its stretch is stretched.
DRIFT_LIMIT_SECONDS = 0.020
#: Real sound-card clocks are within a fraction of a percent; anything past
#: this is a broken measurement and is not applied.
PLAUSIBLE_RATIO = (0.98, 1.02)


@dataclass(frozen=True)
class DriftCorrection:
    """One source's stretch in one segment, and what the report says about it."""

    label: str
    segment: int
    ratio: float
    drift_ms: float
    seconds: float

    @property
    def tempo(self) -> float:
        """The ``atempo`` factor: a fast clock's file is played faster to fit."""
        return self.ratio

    def sentence(self) -> str:
        way = "fast" if self.drift_ms > 0 else "slow"
        return (
            f"{self.label}, segment {self.segment}: its clock ran {way}, "
            f"{abs(self.drift_ms):.0f} ms over {self.seconds:.0f} seconds; "
            f"stretched to fit (tempo {self.tempo:.6f})."
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.label,
            "segment": self.segment,
            "drift_ratio": self.ratio,
            "drift_ms": round(self.drift_ms, 3),
            "seconds": round(self.seconds, 3),
            "tempo": self.tempo,
        }


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def drift_correction(
    timing: Any, *, label: str, segment: int, duration: float
) -> DriftCorrection | None:
    """The stretch *timing* calls for, or ``None`` when the source fits as it is.

    *timing* is one source's entry from the segment record; anything that is
    not a mapping with a usable ``drift_ratio`` means "not measured".
    *duration* is the segment's length, used when the entry does not say how
    long a stretch it measured.
    """
    if not isinstance(timing, Mapping):
        return None
    ratio = _number(timing.get("drift_ratio"))
    if ratio is None or not PLAUSIBLE_RATIO[0] <= ratio <= PLAUSIBLE_RATIO[1]:
        return None
    seconds = _number(timing.get("monotonic_seconds")) or max(0.0, duration)
    drift_ms = _number(timing.get("drift_ms"))
    if drift_ms is None:
        drift_ms = (ratio - 1.0) * seconds * 1000.0
    if abs(drift_ms) <= DRIFT_LIMIT_SECONDS * 1000.0 or ratio == 1.0:
        return None
    return DriftCorrection(label, segment, ratio, drift_ms, seconds)


def segment_timing(segment: Any) -> Mapping[str, Any]:
    """A segment record's per-source timing, or an empty mapping when it has none."""
    timing = getattr(segment, "audio_timing", None)
    return timing if isinstance(timing, Mapping) else {}
