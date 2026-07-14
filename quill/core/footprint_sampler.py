"""In-app peak-RSS and first-event timing sampler (Phase 0 — measurement).

The static ``scripts/footprint_report.py`` covers installed size, on-disk model
sizes, and machine context. The two deliverables it *can't* produce statically are
**per-engine peak RSS** and **cold-start / time-to-first-token** — those need a real
engine loaded and exercised inside the running app. This module is that in-app half,
kept **wx-free and headless-testable**: the UI runs ``work`` on the background task
pool and this module measures it.

- :func:`sample_peak_rss` polls a resident-set-size reader on a background thread
  while ``work`` runs and returns ``(result, peak_bytes)``.
- :func:`time_to_first` measures seconds from a start until ``work`` produces its
  first item (first token / first audio chunk).

Both degrade rather than crash: a missing/failing RSS reader yields ``-1`` and never
interferes with ``work``.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterable, Iterator

#: Default RSS polling interval (seconds). Small enough to catch a load spike,
#: coarse enough not to perturb the measured work.
DEFAULT_INTERVAL_S = 0.05


def default_rss_reader() -> Callable[[], int]:
    """Return a current-process RSS reader (bytes), or a reader that yields ``-1``.

    Uses ``psutil`` when present; otherwise every call returns ``-1`` ("unavailable")
    so callers record the gap instead of crashing on a machine without psutil.
    """
    try:
        import psutil  # type: ignore[import-untyped]

        process = psutil.Process()

        def _read() -> int:
            try:
                return int(process.memory_info().rss)
            except Exception:  # noqa: BLE001 - a transient read failure is not fatal
                return -1

        return _read
    except Exception:  # noqa: BLE001 - psutil absent: RSS is simply unavailable
        return lambda: -1


def sample_peak_rss[T](
    work: Callable[[], T],
    *,
    rss_reader: Callable[[], int] | None = None,
    interval_s: float = DEFAULT_INTERVAL_S,
) -> tuple[T, int]:
    """Run ``work`` while sampling RSS on a background thread; return ``(result, peak)``.

    ``peak`` is the largest RSS (bytes) seen across the run, or ``-1`` when no valid
    sample was taken (reader unavailable). The sampler thread is always joined before
    returning, and a failing reader never propagates into ``work``.
    """
    reader = rss_reader or default_rss_reader()
    peak = -1
    stop = threading.Event()

    def _poll() -> None:
        nonlocal peak
        while not stop.is_set():
            try:
                value = reader()
            except Exception:  # noqa: BLE001 - sampling must never break the measured work
                value = -1
            if value > peak:
                peak = value
            stop.wait(interval_s)

    sampler = threading.Thread(target=_poll, name="footprint-rss-sampler", daemon=True)
    # Take one sample up front so a very fast ``work`` still records a baseline.
    try:
        baseline = reader()
        if baseline > peak:
            peak = baseline
    except Exception:  # noqa: BLE001
        pass
    sampler.start()
    try:
        result = work()
    finally:
        stop.set()
        sampler.join()
    return result, peak


def time_to_first[T](
    stream: Callable[[], Iterable[T]],
    *,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[float, Iterator[T]]:
    """Measure seconds until the first item of ``stream()`` and return the rest.

    Returns ``(seconds_to_first, iterator)`` where the iterator still yields the first
    item (it is pushed back), so the caller can both time first-token/first-audio and
    then consume the whole stream. Raises ``StopIteration`` -> returns ``(-1.0, empty)``
    when the stream is empty.
    """
    start = clock()
    iterator = iter(stream())
    try:
        first = next(iterator)
    except StopIteration:
        return -1.0, iter(())
    elapsed = clock() - start

    def _rejoined() -> Iterator[T]:
        yield first
        yield from iterator

    return elapsed, _rejoined()
