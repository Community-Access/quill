"""Optional optimal-time posting suggestions (PRD 18.11).

Given a caller's own historical post engagement, this ranks weekday/hour slots
by average engagement and returns a small set of suggestions. Per PRD 18.11 the
system "must explain the recommendation and avoid claiming certainty": every
suggestion carries a plain-language ``explanation`` and its ``sample_size``, and
small samples are called out honestly rather than presented as fact.

The function is pure and deterministic -- no randomness, no wall clock. Times
are integer milliseconds since the Unix epoch (UTC); weekday/hour bucketing is
done in a caller-supplied IANA time zone via :mod:`zoneinfo`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

# Below this many samples in a bucket, the suggestion is flagged low-confidence.
MIN_CONFIDENT_SAMPLES = 5

_WEEKDAY_NAMES = (
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
)


@dataclass
class Suggestion:
    """A suggested posting slot with an honest explanation (PRD 18.11)."""

    weekday: int  # 0=Monday .. 6=Sunday
    hour: int  # 0..23, local to the requested time zone
    score: float  # average engagement observed in this slot
    sample_size: int
    explanation: str

    @property
    def weekday_name(self) -> str:
        return _WEEKDAY_NAMES[self.weekday % 7]

    @property
    def confident(self) -> bool:
        return self.sample_size >= MIN_CONFIDENT_SAMPLES

    def to_dict(self) -> dict:
        return {
            "weekday": self.weekday,
            "weekday_name": self.weekday_name,
            "hour": self.hour,
            "score": self.score,
            "sample_size": self.sample_size,
            "confident": self.confident,
            "explanation": self.explanation,
        }


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("UTC")


def suggest(
    history: list[tuple[int, float]],
    tz: str = "UTC",
    *,
    top_n: int = 3,
) -> list[Suggestion]:
    """Rank weekday/hour slots by average engagement (PRD 18.11).

    ``history`` is a list of ``(timestamp_ms, engagement)`` for the caller's own
    past posts. Buckets are ranked by mean engagement, then by sample size, then
    chronologically for a stable order. Each returned ``Suggestion`` explains its
    basis and avoids claiming certainty; sparse buckets say so explicitly.

    Returns an empty list when there is no history to reason from.
    """
    if not history or top_n <= 0:
        return []

    zone = _zone(tz)
    totals: dict[tuple[int, int], float] = {}
    counts: dict[tuple[int, int], int] = {}
    for ts_ms, engagement in history:
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=zone)
        key = (dt.weekday(), dt.hour)
        totals[key] = totals.get(key, 0.0) + float(engagement)
        counts[key] = counts.get(key, 0) + 1

    total_samples = len(history)
    ranked = sorted(
        totals,
        key=lambda k: (-(totals[k] / counts[k]), -counts[k], k[0], k[1]),
    )

    out: list[Suggestion] = []
    for key in ranked[:top_n]:
        weekday, hour = key
        n = counts[key]
        avg = round(totals[key] / n, 2)
        out.append(
            Suggestion(
                weekday=weekday,
                hour=hour,
                score=avg,
                sample_size=n,
                explanation=_explain(weekday, hour, avg, n, total_samples),
            )
        )
    return out


def _explain(weekday: int, hour: int, avg: float, n: int, total: int) -> str:
    """Build a plain-language, non-committal explanation (PRD 18.11)."""
    name = _WEEKDAY_NAMES[weekday % 7]
    base = (
        f"Based on {n} of your past {total} posts on {name} around "
        f"{hour:02d}:00, average engagement was {avg}."
    )
    if n < MIN_CONFIDENT_SAMPLES:
        caution = (
            " This is based on very few posts, so treat it as a weak hint rather "
            "than a reliable pattern."
        )
    else:
        caution = (
            " This is a suggestion from your own history, not a guarantee of "
            "future results."
        )
    return base + caution
