"""Publishing scheduler state machine (PRD 18.8, 18.12, 40).

Two pieces:

- Pure transition helpers -- valid state moves, retry backoff, and error
  classification -- with no store or clock, so the policy is unit-testable in
  isolation.
- A ``Scheduler`` that walks the store's due plans, publishes each through its
  account's adapter, and records the outcome, following the PRD's recovery
  rules: transient errors back off and retry with exponential backoff; a
  validation, permission, or privacy failure stops and asks the user (PRD
  18.12). One plan per account means a failure on one destination never
  duplicates or blocks the others (PRD 39.3).

Tiers (PRD 18.3): ``native`` scheduling is delegated to the network when the
capability registry says it is supported; ``local`` runs while the app is open
and is the P0 default; ``cloud`` is architected for but not enabled in P0.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from quill_social.adapters.base import AdapterError, NetworkAdapter, PublishRequest
from quill_social.model import (
    DeliveryAttempt,
    Draft,
    PublicationPlan,
    now_ms,
)

# Terminal states never transition further on their own.
TERMINAL_STATES = frozenset({"published", "cancelled", "archived"})

# Which transitions the scheduler itself may make (approvals/UI make others).
_ALLOWED: dict[str, frozenset[str]] = {
    "idea": frozenset({"draft", "cancelled"}),
    "draft": frozenset({"ready", "queued", "cancelled"}),
    "ready": frozenset({"approved", "changes_requested", "queued", "cancelled"}),
    "changes_requested": frozenset({"draft", "cancelled"}),
    "approved": frozenset({"queued", "scheduled", "cancelled"}),
    "queued": frozenset({"scheduled", "publishing", "failed", "cancelled", "paused"}),
    "scheduled": frozenset({"publishing", "queued", "failed", "cancelled", "paused"}),
    "publishing": frozenset({"published", "partial", "failed", "queued"}),
    "partial": frozenset({"publishing", "failed", "published", "paused"}),
    "failed": frozenset({"queued", "cancelled", "archived", "paused"}),
    "paused": frozenset({"queued", "scheduled", "cancelled"}),
    "published": frozenset({"archived"}),
    "cancelled": frozenset(),
    "archived": frozenset(),
}

MAX_RETRIES = 5
_BASE_BACKOFF_MS = 30_000  # 30s, doubling each retry
_MAX_BACKOFF_MS = 3_600_000  # cap at 1 hour


def can_transition(src: str, dst: str) -> bool:
    return dst in _ALLOWED.get(src, frozenset())


def backoff_ms(retry_count: int) -> int:
    """Exponential backoff for transient failures, capped (PRD 18.12)."""
    if retry_count <= 0:
        return _BASE_BACKOFF_MS
    return min(_MAX_BACKOFF_MS, _BASE_BACKOFF_MS * (2 ** retry_count))


def needs_review(error_kind: str) -> bool:
    """Validation, permission, and privacy failures require the user (PRD 18.12)."""
    return error_kind in ("validation", "permission", "privacy")


@dataclass
class StepResult:
    plan: PublicationPlan
    published: bool
    review_required: bool
    retry_scheduled: bool
    message: str


def process_plan(
    plan: PublicationPlan,
    adapter: NetworkAdapter,
    draft: Draft,
    *,
    now: int | None = None,
) -> StepResult:
    """Attempt one delivery of ``plan`` and return the updated plan + outcome.

    Pure with respect to storage: it mutates and returns the plan but does not
    persist it, so the state machine can be tested without a database.
    """
    at = now if now is not None else now_ms()
    request = PublishRequest(
        text=draft.text,
        visibility=draft.visibility,
        content_warning=draft.content_warning,
        lang=draft.lang,
        in_reply_to=draft.in_reply_to,
        quote_of=draft.quote_of,
        media=list(draft.media),
        idempotency_key=f"{plan.plan_id}",
    )
    plan.state = "publishing"
    try:
        published = adapter.publish(request)
    except AdapterError as exc:
        attempt = DeliveryAttempt(
            attempted_at=at, ok=False,
            error_kind=exc.kind, error_message=str(exc),
        )
        plan.attempts.append(attempt)
        plan.updated = at
        if needs_review(exc.kind) or plan.retry_count >= MAX_RETRIES:
            plan.state = "failed"
            plan.next_retry_at = None
            reason = (
                "needs review" if needs_review(exc.kind)
                else f"gave up after {MAX_RETRIES} retries"
            )
            return StepResult(plan, False, needs_review(exc.kind), False,
                              f"Failed: {exc} ({reason}).")
        # transient: schedule a backoff retry. retry_count already includes the
        # failure we just appended, so the first failure backs off by the base
        # delay (backoff_ms(0)).
        delay = exc.retry_after_ms or backoff_ms(plan.retry_count - 1)
        plan.next_retry_at = at + delay
        plan.state = "queued"
        return StepResult(plan, False, False, True,
                          f"Transient error; retry in {delay // 1000}s.")

    attempt = DeliveryAttempt(attempted_at=at, ok=True, published_id=published.remote_id)
    plan.attempts.append(attempt)
    plan.remote_id = published.remote_id
    plan.state = "published"
    plan.next_retry_at = None
    plan.updated = at
    return StepResult(plan, True, False, False, "Published.")


class Scheduler:
    """Local scheduler: publish due plans through their account adapters.

    Constructed with the store, an adapter resolver (account_id -> adapter), and
    an optional clock for deterministic tests.
    """

    def __init__(
        self,
        store,
        resolve_adapter: Callable[[str], NetworkAdapter],
        *,
        clock: Callable[[], int] = now_ms,
    ) -> None:
        self.store = store
        self.resolve_adapter = resolve_adapter
        self.clock = clock

    def run_due(self) -> list[StepResult]:
        """Process every plan whose scheduled time (and any backoff) has passed."""
        at = self.clock()
        results: list[StepResult] = []
        for plan in self.store.due_plans(now=at):
            draft = self.store.get_draft(plan.draft_id)
            if draft is None:
                plan.state = "failed"
                plan.updated = at
                self.store.put_plan(plan)
                results.append(StepResult(plan, False, True, False,
                                          "Draft missing; cannot publish."))
                continue
            adapter = self.resolve_adapter(plan.account_id)
            step = process_plan(plan, adapter, draft, now=at)
            self.store.put_plan(step.plan)
            results.append(step)
        return results
