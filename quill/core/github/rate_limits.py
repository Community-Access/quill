"""GitHub API rate limits: what is left, when it resets, and when GitHub asked QUILL to wait.

Every reply from ``api.github.com`` carries ``X-RateLimit-Remaining``,
``X-RateLimit-Limit``, ``X-RateLimit-Reset`` and ``X-RateLimit-Resource``.
:class:`RateLimitTracker` keeps the latest of those per resource so the
workbench can say how much is left without asking, and so a poller can slow
down when little is left (:meth:`RateLimitTracker.slowed`).

A *secondary* rate limit is GitHub telling one client to back off for a while
(``Retry-After``, or a 403/429 whose message says "secondary rate limit"). It
is recorded once; until it passes, every request through
:func:`~quill.core.github.rest_transport.request_json` stops before the network
with the same plain sentence, "GitHub asked QUILL to wait 60 seconds.", so a
view that makes six calls reports one message rather than six failures.

The full readout (``GET /rate_limit`` plus GraphQL ``rateLimit``) is
:func:`fetch_rate_limit_report`. No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from quill.core.error_codes import CodedError

SECONDARY_DEFAULT_WAIT = 60
"""GitHub's documented minimum wait when a secondary limit names no ``Retry-After``."""

_RESOURCE_WORDS = {
    "core": "GitHub API",
    "graphql": "GraphQL",
    "search": "Search",
    "code_search": "Code search",
}


def _header(headers: object, name: str) -> str:
    if not headers:
        return ""
    getter = getattr(headers, "get", None)
    if not callable(getter):
        return ""
    for key in (name, name.casefold()):
        try:
            value = getter(key)
        except Exception:  # noqa: BLE001 - header containers vary by client
            value = None
        if value:
            return str(value)
    return ""


def _int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def wait_message(seconds: int) -> str:
    """The one sentence said for a secondary limit."""
    seconds = max(1, int(seconds))
    return f"GitHub asked QUILL to wait {seconds} second{'' if seconds == 1 else 's'}."


def is_wait_message(text: str) -> bool:
    return text.startswith("GitHub asked QUILL to wait ")


def secondary_wait_seconds(status: int | None, headers: object, message: str = "") -> int | None:
    """Seconds GitHub asked for, when this failure is a secondary limit; else ``None``.

    A primary limit (``X-RateLimit-Remaining: 0``) is not secondary: it lasts
    until the reset time, which :meth:`RateLimitTracker.observe` already holds.
    """
    if status not in (403, 429):
        return None
    lowered = message.casefold()
    retry_after = _header(headers, "Retry-After")
    if "secondary rate limit" in lowered or "abuse" in lowered:
        return max(1, _int(retry_after, SECONDARY_DEFAULT_WAIT))
    if _header(headers, "X-RateLimit-Remaining") == "0":
        return None
    if retry_after:
        return max(1, _int(retry_after, SECONDARY_DEFAULT_WAIT))
    if status == 429:
        return SECONDARY_DEFAULT_WAIT
    return None


@dataclass(frozen=True, slots=True)
class RateLimitBucket:
    """One resource's allowance: ``remaining`` of ``limit`` until ``reset_epoch``."""

    resource: str
    limit: int
    remaining: int
    reset_epoch: float

    @property
    def fraction_left(self) -> float:
        return self.remaining / self.limit if self.limit > 0 else 1.0

    def sentence(self, to_local: Callable[[float], datetime] | None = None) -> str:
        name = _RESOURCE_WORDS.get(self.resource, self.resource.replace("_", " ").capitalize())
        text = f"{name}: {self.remaining:,} of {self.limit:,} left"
        if self.reset_epoch > 0:
            text += f", resets at {format_clock(self.reset_epoch, to_local)}"
        return text


def format_clock(epoch: float, to_local: Callable[[float], datetime] | None = None) -> str:
    """``3:40 PM`` in local time (no leading zero, no seconds)."""
    moment = (to_local or datetime.fromtimestamp)(epoch)
    return moment.strftime("%I:%M %p").lstrip("0")


class RateLimitTracker:
    """The latest allowance per resource, and any secondary-limit wait, thread-safe."""

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        wall: Callable[[], float] = time.time,
    ) -> None:
        self._clock = clock
        self._wall = wall
        self._lock = threading.Lock()
        self._buckets: dict[str, RateLimitBucket] = {}
        self._blocked_until = 0.0

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()
            self._blocked_until = 0.0

    def observe(self, headers: object) -> None:
        """Remember what one reply's ``X-RateLimit-*`` headers said."""
        limit = _int(_header(headers, "X-RateLimit-Limit"), -1)
        remaining = _int(_header(headers, "X-RateLimit-Remaining"), -1)
        if limit <= 0 or remaining < 0:
            return
        resource = _header(headers, "X-RateLimit-Resource") or "core"
        bucket = RateLimitBucket(
            resource, limit, remaining, float(_int(_header(headers, "X-RateLimit-Reset")))
        )
        with self._lock:
            self._buckets[resource] = bucket

    def observe_secondary(self, seconds: int) -> None:
        with self._lock:
            self._blocked_until = max(self._blocked_until, self._clock() + max(1, seconds))

    def wait_seconds(self) -> int:
        """Seconds left of a secondary-limit wait; 0 when requests may go."""
        with self._lock:
            remaining = self._blocked_until - self._clock()
        return max(0, int(remaining + 0.999))

    def bucket(self, resource: str = "core") -> RateLimitBucket | None:
        with self._lock:
            return self._buckets.get(resource)

    def slowed(self, interval_seconds: int, resource: str = "core") -> int:
        """Stretch a poll interval when the allowance runs low.

        Under a quarter left doubles it, under a tenth quadruples it, and none
        left waits for the reset. A secondary-limit wait is never shortened.
        """
        interval = max(0, int(interval_seconds))
        wait = self.wait_seconds()
        bucket = self.bucket(resource)
        if bucket is not None:
            if bucket.remaining <= 0:
                interval = max(interval, int(bucket.reset_epoch - self._wall()) + 1)
            elif bucket.fraction_left < 0.10:
                interval *= 4
            elif bucket.fraction_left < 0.25:
                interval *= 2
        return max(interval, wait)

    def is_low(self, resource: str = "core") -> bool:
        bucket = self.bucket(resource)
        return bucket is not None and bucket.fraction_left < 0.25


RATE_LIMITS = RateLimitTracker()
"""The process-wide tracker every workbench request reports into."""


class GitHubRateLimitError(CodedError):
    """The rate-limit readout could not be read."""

    code = "QUILL-GITHUB-RATELIMIT-READ-FAILED"


@dataclass(frozen=True, slots=True)
class RateLimitReport:
    """What ``GET /rate_limit`` and GraphQL ``rateLimit`` said, as sentences."""

    buckets: tuple[RateLimitBucket, ...]
    notes: tuple[str, ...] = ()

    def sentence(self, to_local: Callable[[float], datetime] | None = None) -> str:
        parts = [bucket.sentence(to_local) + "." for bucket in self.buckets]
        return " ".join(parts + list(self.notes)) or "GitHub did not report a rate limit."


def parse_rest_rate_limit(data: object) -> list[RateLimitBucket]:
    """``GET /rate_limit``: core first, then search, then anything else reported."""
    resources = data.get("resources") if isinstance(data, dict) else None
    if not isinstance(resources, dict):
        return []
    out: list[RateLimitBucket] = []
    for name in ("core", "search", "code_search"):
        row = resources.get(name)
        if isinstance(row, dict) and _int(row.get("limit")) > 0:
            out.append(
                RateLimitBucket(
                    name,
                    _int(row.get("limit")),
                    _int(row.get("remaining")),
                    float(_int(row.get("reset"))),
                )
            )
    return out


def parse_graphql_rate_limit(data: object) -> RateLimitBucket | None:
    """``{ rateLimit { limit remaining resetAt } }`` (``resetAt`` is ISO 8601 UTC)."""
    node = data.get("rateLimit") if isinstance(data, dict) else None
    if not isinstance(node, dict) or _int(node.get("limit")) <= 0:
        return None
    reset = 0.0
    raw = node.get("resetAt")
    if isinstance(raw, str) and raw:
        try:
            reset = datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
        except ValueError:
            reset = 0.0
    return RateLimitBucket("graphql", _int(node.get("limit")), _int(node.get("remaining")), reset)


def fetch_rate_limit_report(token: str | None, *, request: Any = None) -> RateLimitReport:
    """Read the REST and GraphQL allowances. ``/rate_limit`` itself costs nothing.

    GraphQL needs a signed-in account; without one, or when it fails, the
    report says so in a note instead of leaving the line out silently.
    """
    from quill.core.github.rest_transport import GitHubRestError, request_json

    send = request or request_json
    notes: list[str] = []
    try:
        buckets = parse_rest_rate_limit(send(token, "GET", "/rate_limit").data)
    except GitHubRestError as exc:
        from quill.core.github.rest_transport import rest_failure_message

        raise GitHubRateLimitError(rest_failure_message("read the rate limit", exc)) from exc
    if token:
        try:
            reply = send(
                token,
                "POST",
                "/graphql",
                body={"query": "query { rateLimit { limit remaining resetAt } }"},
            )
            payload = reply.data if isinstance(reply.data, dict) else {}
            graphql = parse_graphql_rate_limit(payload.get("data"))
        except GitHubRestError:
            graphql = None
        if graphql is not None:
            buckets.insert(1 if buckets else 0, graphql)
        else:
            notes.append("GraphQL's allowance could not be read.")
    else:
        notes.append("Sign in to see the GraphQL allowance.")
    wait = RATE_LIMITS.wait_seconds() if request is None else 0
    if wait:
        notes.append(wait_message(wait))
    return RateLimitReport(tuple(buckets), tuple(notes))


__all__ = [
    "RATE_LIMITS",
    "SECONDARY_DEFAULT_WAIT",
    "GitHubRateLimitError",
    "RateLimitBucket",
    "RateLimitReport",
    "RateLimitTracker",
    "fetch_rate_limit_report",
    "format_clock",
    "is_wait_message",
    "parse_graphql_rate_limit",
    "parse_rest_rate_limit",
    "secondary_wait_seconds",
    "wait_message",
]
