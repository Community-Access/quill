"""Focus-free progress + ETA for long AI jobs (#1321).

Idea adopted from HomerScribe. A long batch job (bulk transcription, agent runs,
bulk OCR) should surface its progress in channels a screen-reader user can poll
on their own schedule, without anything stealing focus:

* the **window title** ("Transcribing 42 of 247 - QUILL"), readable via Alt+Tab
  at any moment (:meth:`ProgressReporter.title_text`), and
* a persistent **status line** the UI registers as a UIA live region
  (:meth:`ProgressReporter.status_text`).

This module is the pure state machine behind both: it counts completed units and
estimates time remaining. The estimate deliberately starts from the **second**
unit -- the first is warm-up-skewed (model load, cache miss) and would give a
wildly pessimistic ETA -- and the job warns up front when the whole run will
take hours. Timestamps are injected (monotonic seconds), so everything here is
deterministic and unit-tested; the UI passes ``time.monotonic()`` and drives the
two channels off the wx thread.
"""

from __future__ import annotations

#: A run projected to exceed this many seconds gets an up-front heads-up.
_HOURS_WARNING_SECONDS = 3600.0


def format_duration(seconds: float) -> str:
    """A rounded, spoken-friendly duration: "about 45 seconds", "3 minutes"."""
    seconds = max(0.0, seconds)
    if seconds < 90:
        n = max(1, round(seconds))
        return f"about {n} second{'s' if n != 1 else ''}"
    minutes = seconds / 60
    if minutes < 60:
        n = round(minutes)
        return f"about {n} minute{'s' if n != 1 else ''}"
    hours = int(seconds // 3600)
    rem_minutes = round((seconds - hours * 3600) / 60)
    if rem_minutes == 60:
        hours += 1
        rem_minutes = 0
    if rem_minutes == 0:
        return f"about {hours} hour{'s' if hours != 1 else ''}"
    return (
        f"about {hours} hour{'s' if hours != 1 else ''} "
        f"{rem_minutes} minute{'s' if rem_minutes != 1 else ''}"
    )


class ProgressReporter:
    """Counts completed units of a job and estimates the time remaining.

    Drive it by calling :meth:`start` once, then :meth:`advance` after each unit
    completes, passing a monotonic timestamp each time. Read :meth:`title_text` /
    :meth:`status_text` for the two focus-free channels.
    """

    def __init__(self, total: int, *, label: str = "Working", app_name: str = "QUILL") -> None:
        if total < 0:
            raise ValueError("total must be non-negative")
        self.total = total
        self.label = label
        self.app_name = app_name
        self.done = 0
        self._first_done_at: float | None = None
        self._last_at: float | None = None

    def start(self, now: float) -> None:
        """Mark the run's start (optional; only :meth:`advance` drives the ETA)."""
        self._last_at = now

    def advance(self, now: float, *, count: int = 1) -> None:
        """Record ``count`` completed unit(s) at time ``now`` (monotonic seconds)."""
        if count < 1:
            raise ValueError("count must be at least 1")
        self.done += count
        # The clock we measure the *warm* rate from is the moment the first unit
        # finished, so the warm-up-skewed first interval is excluded (#1321).
        if self._first_done_at is None:
            self._first_done_at = now
        self._last_at = now

    def is_complete(self) -> bool:
        return self.total > 0 and self.done >= self.total

    def _warm_rate(self) -> float | None:
        """Seconds per unit measured from the second unit onward, or None."""
        if self.done < 2 or self._first_done_at is None or self._last_at is None:
            return None
        elapsed = self._last_at - self._first_done_at
        units = self.done - 1
        if elapsed <= 0 or units <= 0:
            return None
        return elapsed / units

    def eta_seconds(self) -> float | None:
        """Estimated seconds remaining, or None until the second unit lands."""
        rate = self._warm_rate()
        if rate is None:
            return None
        return max(0.0, rate * (self.total - self.done))

    def total_estimate_seconds(self) -> float | None:
        """Estimated total run length once a warm rate is known, else None."""
        rate = self._warm_rate()
        if rate is None:
            return None
        return rate * self.total

    def title_text(self) -> str:
        """Window-title text: ``"Transcribing 42 of 247 - QUILL"``."""
        if self.is_complete():
            return f"{self.label} complete - {self.app_name}"
        return f"{self.label} {self.done} of {self.total} - {self.app_name}"

    def status_text(self) -> str:
        """Live-region status line, with the ETA once it is known."""
        if self.is_complete():
            return f"{self.label} complete: {self.total} of {self.total}."
        eta = self.eta_seconds()
        head = f"{self.label} {self.done} of {self.total}."
        if eta is None:
            return f"{head} Estimating time remaining."
        return f"{head} {format_duration(eta).capitalize()} remaining."

    def hours_warning(self, *, threshold_seconds: float = _HOURS_WARNING_SECONDS) -> str:
        """An up-front heads-up when the whole run will take hours, else ""."""
        estimate = self.total_estimate_seconds()
        if estimate is None or estimate < threshold_seconds:
            return ""
        return f"Heads up: this run will take {format_duration(estimate)}."
