"""Staying inside Open-Meteo's free terms: a call budget and a back-off on 429.

Open-Meteo is free and keyless for non-commercial use at roughly 10,000 calls a
day, counted per address. Every Quill Weather request to any Open-Meteo host
goes through :func:`get_json` here, so the rules live in one place:

* **A daily budget.** One install should never need more than a few hundred
  calls a day, so the budget stops well short of the service's limit
  (:data:`DAILY_BUDGET`). Once it is spent, requests are refused locally with a
  plain sentence instead of being sent.
* **Back off on 429.** When the service says "too many requests", no further
  Open-Meteo request is sent until the back-off ends (the service's
  ``Retry-After`` when it gives one, else :data:`DEFAULT_BACKOFF_SECONDS`,
  doubling on repeats up to :data:`MAX_BACKOFF_SECONDS`).
* **Weighted calls.** A request for many places counts once per place, the way
  Open-Meteo counts it, so batching saves round trips without hiding cost.

Both refusals raise :class:`OpenMeteoBusy`, which is an ``OSError``: every
caller's existing ``HTTP_ERRORS`` handler already treats it as "could not
reach", which is exactly what it is -- never as "no data".

wx-free and strict-typed. The clock is injectable for tests.
"""

from __future__ import annotations

import threading
import time
import urllib.error
from collections.abc import Callable
from datetime import date
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.weather._http import http_json

#: Calls per local day this install will make, far under the ~10,000 limit.
DAILY_BUDGET = 2500
DEFAULT_BACKOFF_SECONDS = 15 * 60
MAX_BACKOFF_SECONDS = 6 * 60 * 60

#: The Open-Meteo hosts Quill Weather reaches. Anything else is refused here.
HOSTS = (
    "https://api.open-meteo.com/",
    "https://archive-api.open-meteo.com/",
    "https://air-quality-api.open-meteo.com/",
    "https://marine-api.open-meteo.com/",
)


class OpenMeteoBusy(CodedError, OSError):
    """Quill Weather is holding back from Open-Meteo (429 back-off or budget).

    Also an ``OSError``, so it travels through the same ``HTTP_ERRORS`` handlers
    as a dropped connection: "could not reach", never "no data". Its first
    argument is the plain sentence to say.
    """

    code = "QUILL-WEATHER-OPENMETEO-BUSY"


class _Gate:
    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self.clock = clock
        self._lock = threading.Lock()
        self.day: date | None = None
        self.used = 0
        self.backoff_until = 0.0
        self.backoff_seconds = 0.0

    def reset(self) -> None:
        with self._lock:
            self.day = None
            self.used = 0
            self.backoff_until = 0.0
            self.backoff_seconds = 0.0

    def take(self, weight: int) -> None:
        now = self.clock()
        with self._lock:
            today = date.fromtimestamp(now)
            if self.day != today:
                self.day, self.used = today, 0
            if now < self.backoff_until:
                minutes = max(1, round((self.backoff_until - now) / 60))
                raise OpenMeteoBusy(
                    "Open-Meteo asked Quill Weather to slow down. It will try again in "
                    f"about {minutes} minute{'s' if minutes != 1 else ''}."
                )
            if self.used + weight > DAILY_BUDGET:
                raise OpenMeteoBusy(
                    "Quill Weather has made as many Open-Meteo requests today as it "
                    "allows itself, to stay within the free service's fair-use limit. "
                    "Saved results still work; new ones resume tomorrow."
                )
            self.used += weight

    def throttled(self, retry_after: float | None) -> None:
        with self._lock:
            if retry_after and retry_after > 0:
                wait = min(float(retry_after), MAX_BACKOFF_SECONDS)
            else:
                doubled = self.backoff_seconds * 2 if self.backoff_seconds else 0
                wait = min(max(DEFAULT_BACKOFF_SECONDS, doubled), MAX_BACKOFF_SECONDS)
            self.backoff_seconds = wait
            self.backoff_until = self.clock() + wait

    def succeeded(self) -> None:
        with self._lock:
            self.backoff_seconds = 0.0


GATE = _Gate()


def _retry_after(error: urllib.error.HTTPError) -> float | None:
    raw = error.headers.get("Retry-After") if error.headers is not None else None
    try:
        return float(raw) if raw is not None else None
    except ValueError:
        return None


def get_json(url: str, *, weight: int = 1) -> Any:
    """One Open-Meteo GET through the budget and back-off. ``weight`` is how many
    calls Open-Meteo will count it as (one per place in a batched request)."""
    if not url.startswith(HOSTS):
        raise ValueError("Not an Open-Meteo address.")
    GATE.take(max(1, weight))
    try:
        data = http_json(url)
    except urllib.error.HTTPError as error:
        if error.code == 429:
            GATE.throttled(_retry_after(error))
        raise
    GATE.succeeded()
    return data
