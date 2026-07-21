"""Offline resilience: the outbox, reconnection revalidation, and breakers (PRD 32).

When the app is offline or a service is failing, composed posts wait in an
outbox instead of being lost (PRD 32.2). Each :class:`OutboxItem` records enough
to revalidate itself when connectivity returns: the account and network, when it
was created, its privacy, any thread dependency, whether its media is ready, its
send mode, an optional expiration, and the last validation status.

On reconnection (PRD 32.2, 39.7) the outbox is revalidated in order:

- capability limits are re-checked and changed limits warned about,
- reply references are refreshed,
- expired timing is flagged -- a post whose intended time has passed must NOT be
  silently published; it is held for the user (PRD 39.7),
- order is preserved.

Service failures are contained with a :class:`CircuitBreaker` (closed / open /
half-open) and an exponential ``backoff`` helper (PRD 32.3). This module is
wx-free; all time comes through a ``now`` parameter defaulting to
``model.now_ms``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from quill_social.capabilities import Capabilities
from quill_social.model import new_id, now_ms

_DOC_KIND = "outbox"

# Send modes an outbox item can carry (PRD 32.2).
SEND_MODES = ("immediate", "scheduled", "hold")

# Validation statuses (PRD 32.2, 39.7).
VALIDATION_STATUSES = ("pending", "valid", "warn", "invalid", "expired")


@dataclass
class OutboxItem:
    """A post held for delivery while offline or during a service failure (PRD 32.2)."""

    outbox_id: str = field(default_factory=lambda: new_id("outbox"))
    account_id: str = ""
    network: str = "mock"
    text: str = ""
    created: int = field(default_factory=now_ms)
    privacy: str = "public"
    thread_dependency: str = ""  # local id of the item/plan this must follow
    reply_to_remote_id: str = ""  # remote id of the parent, refreshed on reconnect
    media_ready: bool = True
    send_mode: str = "immediate"
    expiration: int | None = None  # intended time; must not auto-publish once past
    validation_status: str = "pending"

    def to_dict(self) -> dict:
        return {
            "outbox_id": self.outbox_id,
            "account_id": self.account_id,
            "network": self.network,
            "text": self.text,
            "created": self.created,
            "privacy": self.privacy,
            "thread_dependency": self.thread_dependency,
            "reply_to_remote_id": self.reply_to_remote_id,
            "media_ready": self.media_ready,
            "send_mode": self.send_mode,
            "expiration": self.expiration,
            "validation_status": self.validation_status,
        }

    @classmethod
    def from_dict(cls, d: dict) -> OutboxItem:
        return cls(
            outbox_id=d.get("outbox_id") or new_id("outbox"),
            account_id=d.get("account_id", ""),
            network=d.get("network", "mock"),
            text=d.get("text", ""),
            created=int(d.get("created", 0) or 0),
            privacy=d.get("privacy", "public"),
            thread_dependency=d.get("thread_dependency", ""),
            reply_to_remote_id=d.get("reply_to_remote_id", ""),
            media_ready=bool(d.get("media_ready", True)),
            send_mode=d.get("send_mode", "immediate"),
            expiration=d.get("expiration"),
            validation_status=d.get("validation_status", "pending"),
        )


class Outbox:
    """Durable queue of outbox items, persisted via the document store (PRD 32.2)."""

    def __init__(self, store) -> None:
        self.store = store

    def enqueue(self, item: OutboxItem) -> OutboxItem:
        self.store.put_document(
            _DOC_KIND, item.outbox_id, item.to_dict(), ordinal=item.created
        )
        return item

    def list(self) -> list[OutboxItem]:
        """All queued items, in stable creation order (order preserved, PRD 32.2)."""
        return [OutboxItem.from_dict(d) for d in self.store.list_documents(_DOC_KIND)]

    def get(self, outbox_id: str) -> OutboxItem | None:
        d = self.store.get_document(_DOC_KIND, outbox_id)
        return OutboxItem.from_dict(d) if d else None

    def remove(self, outbox_id: str) -> None:
        self.store.delete_document(_DOC_KIND, outbox_id)


@dataclass
class RevalidationResult:
    """The outcome of revalidating one outbox item on reconnect (PRD 32.2)."""

    item: OutboxItem
    warnings: list[str] = field(default_factory=list)
    expired: bool = False
    needs_review: bool = False


def on_reconnect(
    items: list[OutboxItem],
    caps_lookup: Callable[[OutboxItem], Capabilities],
    *,
    now: int | None = None,
) -> list[RevalidationResult]:
    """Revalidate outbox items when connectivity returns (PRD 32.2, 39.7).

    ``caps_lookup`` maps an item to the network's *current* capabilities so
    changed limits can be detected. Order is preserved: results come back in the
    same order as ``items``.
    """
    at = now if now is not None else now_ms()
    results: list[RevalidationResult] = []
    for item in items:
        res = RevalidationResult(item=item)

        # Expired timing: a post whose intended time has passed must never be
        # published silently -- hold it for the user (PRD 39.7).
        if item.expiration is not None and at > item.expiration:
            res.expired = True
            res.needs_review = True
            res.warnings.append(
                "intended time has passed; held for review instead of publishing"
            )
            item.validation_status = "expired"

        # Capability revalidation: warn if the current character limit no longer
        # fits the queued text (PRD 32.2, "warn about changed limits").
        caps = caps_lookup(item)
        if caps is not None and len(item.text) > caps.char_limit:
            res.needs_review = True
            res.warnings.append(
                f"character limit changed: text is {len(item.text)} but the network "
                f"now allows {caps.char_limit}"
            )
            if item.validation_status != "expired":
                item.validation_status = "warn"

        # Privacy revalidation: a visibility the network no longer allows.
        if caps is not None and not caps.allows_visibility(item.privacy):
            res.needs_review = True
            res.warnings.append(
                f"privacy '{item.privacy}' is not allowed on {item.network} anymore"
            )
            if item.validation_status not in ("expired", "warn"):
                item.validation_status = "warn"

        # Reply references: a queued reply must re-resolve its parent's remote id
        # before publishing (PRD 32.2, "refresh reply references").
        if item.thread_dependency and not item.reply_to_remote_id:
            res.warnings.append(
                "reply reference must be refreshed before this item can publish"
            )

        # Media readiness (PRD 32.2).
        if not item.media_ready:
            res.needs_review = True
            res.warnings.append("attached media is not yet uploaded/ready")

        if not res.warnings and item.validation_status not in ("expired",):
            item.validation_status = "valid"
        results.append(res)
    return results


# -- service failure containment (PRD 32.3) -----------------------------------

_BASE_BACKOFF_MS = 30_000  # 30s, doubling each attempt
_MAX_BACKOFF_MS = 3_600_000  # cap at 1 hour


def backoff(attempt: int, *, base_ms: int = _BASE_BACKOFF_MS, cap_ms: int = _MAX_BACKOFF_MS) -> int:
    """Exponential backoff for a retry ``attempt`` (0-based), capped (PRD 32.3)."""
    if attempt <= 0:
        return base_ms
    return min(cap_ms, base_ms * (2 ** attempt))


@dataclass
class CircuitBreaker:
    """A per-service circuit breaker (PRD 32.3).

    Starts ``closed`` (calls allowed). After ``failure_threshold`` consecutive
    failures it trips ``open`` (calls blocked). After ``cooldown_ms`` it moves to
    ``half_open`` to allow a single trial call; a success closes it, a failure
    re-opens it. All time comes through ``now`` for deterministic tests.
    """

    service: str = ""
    failure_threshold: int = 5
    cooldown_ms: int = 60_000
    state: str = "closed"  # closed | open | half_open
    failures: int = 0
    opened_at: int | None = None

    def allow(self, *, now: int | None = None) -> bool:
        """Whether a call may proceed, transitioning open -> half_open on cooldown."""
        at = now if now is not None else now_ms()
        if self.state == "open":
            if self.opened_at is not None and at - self.opened_at >= self.cooldown_ms:
                self.state = "half_open"
                return True
            return False
        # closed or half_open both permit a call (half_open permits the trial).
        return True

    def record_success(self, *, now: int | None = None) -> None:
        self.failures = 0
        self.opened_at = None
        self.state = "closed"

    def record_failure(self, *, now: int | None = None) -> None:
        at = now if now is not None else now_ms()
        if self.state == "half_open":
            # The trial failed: re-open and restart the cooldown.
            self.state = "open"
            self.opened_at = at
            return
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.state = "open"
            self.opened_at = at
