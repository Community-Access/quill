"""Server-side quota, rate-limit, and large-document enforcement.

This module is the single place every one of PRD §8's tunable limits and
§14.1's large-document safeguards is actually checked. **Nothing in
app/routes/chat.py should compare a number to a limit directly** -- every
check goes through a function here, so the enforcement logic has exactly
one implementation to audit, test, and reason about.

Reading order for a newcomer:

1. :func:`resolve_limit` -- how a tunable number's *current* value is
   found (admin override > global config > hardcoded fail-safe).
2. :func:`check_request_allowed` -- the top-level gate every ``/v1/chat``
   request passes through, in the exact order PRD §8 specifies (cheapest
   check first).
3. :func:`count_tokens` / :func:`reject_if_too_large` -- the large-document
   safeguards from PRD §14.1, layers 2 and 3 (the client's own layer 1
   pre-check lives in the QUILL desktop client, not here -- this module is
   the *real* boundary that holds even if the client skips its own check).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import redis as redis_lib

from app.models import Device, GatewayConfig, MonthlyUsageSummary, User, UserFeatureCap, db

# --- Hardcoded fail-safes ----------------------------------------------------
# Used only if a gateway_config row is somehow missing (a fresh database
# that hasn't been seeded yet -- see migrations/002_seed_gateway_config.sql).
# These intentionally match the PRD §8/§23 initial-rollout defaults, not
# the more generous numbers this plan expects to grow into later -- a
# missing config row should never accidentally make the Gateway *more*
# permissive than intended.
_FAIL_SAFE_DEFAULTS: dict[str, float] = {
    "monthly_request_cap": 100,
    "daily_request_cap": 20,
    "hourly_request_cap": 8,
    "device_hourly_request_cap": 8,
    "max_input_tokens": 1500,
    "max_output_tokens": 500,
    "max_chunks_per_request": 3,
    "max_image_bytes": 3 * 1024 * 1024,
    "max_image_edge_px": 1600,
    "daily_image_cap": 5,
    "monthly_cost_cap_usd": 0.15,
    "global_monthly_budget_usd": 25.0,
}

# Per-feature monthly caps are a distinct family of config keys
# (feature_cap.<feature>) with their own fail-safes, since they're
# ceilings *within* the overall monthly total, not standalone limits.
_FEATURE_CAP_FAIL_SAFE_DEFAULTS: dict[str, float] = {
    "document_qna": 60,
    "summarize": 60,
    "rewrite": 60,
    "alt_text": 15,
    "chat": 60,
}

_CONFIG_CACHE_TTL_SECONDS = 30
"""How long a resolved gateway_config value is cached in Redis before the
next request re-reads Postgres. Short enough that an admin's config change
takes effect almost immediately; long enough that a busy Gateway isn't
hitting Postgres for a config read on every single request."""


class QuotaExceeded(Exception):
    """Raised by :func:`check_request_allowed`; carries the exact PRD §8
    response shape so ``app/routes/chat.py`` can serialize it directly."""

    def __init__(self, scope: str, message: str, reset_at: datetime | None = None) -> None:
        super().__init__(message)
        self.scope = scope
        self.message = message
        self.reset_at = reset_at


class RequestTooLarge(Exception):
    """Raised by :func:`reject_if_too_large`; the PRD §14.1 "input too
    large" response."""

    def __init__(self, reason: str, message: str, max_value: int, actual_value: int) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message
        self.max_value = max_value
        self.actual_value = actual_value


class FeatureUnavailable(Exception):
    """Raised when a feature flag (or the global ``hosted_ai`` switch) is off."""

    def __init__(self, scope: str, message: str) -> None:
        super().__init__(message)
        self.scope = scope
        self.message = message


def _redis(app) -> redis_lib.Redis:
    return app.extensions["gateway_redis"]


def resolve_limit(app, key: str) -> float:
    """The current value of a tunable limit: Redis cache -> Postgres
    ``gateway_config`` -> hardcoded fail-safe, in that order.

    This is the function that makes every number in PRD §8 a live,
    admin-tunable dial instead of a constant: change the row in
    ``gateway_config`` (via the admin console, ``PUT /admin/config/{key}``)
    and the *next* request that calls this function sees the new value,
    with at most :data:`_CONFIG_CACHE_TTL_SECONDS` of staleness from the
    Redis cache.
    """
    cache_key = f"gwcfg:{key}"
    cached = _redis(app).get(cache_key)
    if cached is not None:
        return float(cached)

    row = db.session.get(GatewayConfig, key)
    value = float(row.value) if row is not None else _FAIL_SAFE_DEFAULTS.get(key, 0.0)
    _redis(app).set(cache_key, str(value), ex=_CONFIG_CACHE_TTL_SECONDS)
    return value


def resolve_feature_cap(app, feature: str) -> float:
    """The current per-feature monthly cap (a sub-ceiling within the
    overall monthly total -- see PRD §8's per-feature-cap row)."""
    cache_key = f"gwcfg:feature_cap.{feature}"
    cached = _redis(app).get(cache_key)
    if cached is not None:
        return float(cached)

    row = db.session.get(GatewayConfig, f"feature_cap.{feature}")
    value = (
        float(row.value) if row is not None else _FEATURE_CAP_FAIL_SAFE_DEFAULTS.get(feature, 60.0)
    )
    _redis(app).set(cache_key, str(value), ex=_CONFIG_CACHE_TTL_SECONDS)
    return value


def _effective_user_cap(app, user: User) -> int:
    """The monthly request cap that actually applies to *this* user: their
    own override if an admin set one, else the live global default."""
    if user.monthly_request_cap is not None:
        return user.monthly_request_cap
    return int(resolve_limit(app, "monthly_request_cap"))


def _effective_feature_cap(app, user_id: str, feature: str) -> int:
    override = db.session.get(UserFeatureCap, {"user_id": user_id, "feature": feature})
    if override is not None:
        return override.monthly_cap
    return int(resolve_feature_cap(app, feature))


def _month_key(now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    return now.strftime("%Y-%m")


def _month_reset_at(now: datetime | None = None) -> datetime:
    now = now or datetime.now(UTC)
    if now.month == 12:
        return now.replace(
            year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
    return now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)


# --- Sliding-window / fixed-window Redis rate limiting -----------------------


def _increment_and_check(
    app,
    redis_key: str,
    ttl_seconds: int,
    cap: int,
    scope: str,
    message: str,
    reset_at: datetime | None = None,
) -> None:
    """Atomically increment a Redis counter and raise :class:`QuotaExceeded`
    if it now exceeds *cap*. A single ``INCR`` + conditional ``EXPIRE`` is
    used rather than a read-then-write pair, so concurrent requests from
    the same user/device can never race past the cap (the classic
    check-then-act bug a naive rate limiter gets wrong)."""
    client = _redis(app)
    current = client.incr(redis_key)
    if current == 1:
        client.expire(redis_key, ttl_seconds)
    if current > cap:
        raise QuotaExceeded(scope, message, reset_at)


def check_feature_flags(app) -> None:
    """PRD §8's first check, before any per-user logic: is hosted AI on at
    all? Raises :class:`FeatureUnavailable` if the global kill switch (or
    the specific feature, checked separately in :func:`check_request_allowed`)
    is off."""
    from app.models import FeatureFlag

    global_flag = db.session.get(FeatureFlag, "hosted_ai")
    if global_flag is not None and not global_flag.enabled:
        raise FeatureUnavailable(
            "global",
            "Hosted AI is paused for everyone right now while we look into "
            "something — check quillforall.org/status, or use your own "
            "API key in the meantime.",
        )


def check_feature_enabled(app, feature: str) -> None:
    from app.models import FeatureFlag

    flag = db.session.get(FeatureFlag, feature)
    if flag is not None and not flag.enabled:
        raise FeatureUnavailable(
            "feature",
            f"{feature.replace('_', ' ').title()} is temporarily paused while "
            "we review unusual activity — other features are still "
            "available.",
        )


def check_request_allowed(app, user: User, device: Device, feature: str) -> None:
    """The full PRD §8 gate, in the exact specified order: cheapest signal
    first (Redis counters), falling through to anything needing Postgres
    only when necessary. Raises :class:`FeatureUnavailable` or
    :class:`QuotaExceeded` on the first failing check; raises nothing (a
    plain return) when the request may proceed.

    This function does **not** check request size -- see
    :func:`reject_if_too_large`, called separately once the prompt is in
    hand, since token counting requires the actual text.
    """
    # 1. Global kill switch, before anything user-specific.
    check_feature_flags(app)
    check_feature_enabled(app, feature)

    # 2. User/device status -- a blocked user is rejected before any
    #    counter is even incremented, so a blocked user's retries don't
    #    pollute rate-limit windows meant for legitimate traffic.
    if not user.effective_status_allows_requests():
        raise QuotaExceeded(
            "blocked",
            "This account has been paused. Contact support if you believe this is a mistake.",
        )
    if device.status != "active":
        raise QuotaExceeded(
            "device_revoked",
            "This device's access has been revoked. Register it again from "
            "QUILL's AI Hub, or use a different device.",
        )
    if user.status == "review":
        # Reduced, not zero -- PRD §9's "review mode" is a soft throttle,
        # never a silent hard block, so a legitimate user under review
        # barely notices while determined abuse gets uneconomical.
        reduced_cap = 5
        _increment_and_check(
            app,
            f"ratelimit:{user.id}:review_daily",
            24 * 3600,
            reduced_cap,
            "review",
            "Your account is under a routine review; a reduced daily limit "
            "applies until it's cleared. Contact support if this is "
            "unexpected.",
        )

    now = datetime.now(UTC)
    reset_at = _month_reset_at(now)

    # 3. Hourly (per-user and per-device), cheapest Redis checks.
    hourly_cap = int(resolve_limit(app, "hourly_request_cap"))
    _increment_and_check(
        app,
        f"ratelimit:{user.id}:hour:{now.strftime('%Y%m%d%H')}",
        3600,
        hourly_cap,
        "hourly",
        "You've reached this hour's request limit. It resets at the top of the next hour.",
    )
    device_hourly_cap = int(resolve_limit(app, "device_hourly_request_cap"))
    _increment_and_check(
        app,
        f"ratelimit:device:{device.id}:hour:{now.strftime('%Y%m%d%H')}",
        3600,
        device_hourly_cap,
        "hourly",
        "This device has reached this hour's request limit.",
    )

    # 4. Daily.
    daily_cap = int(resolve_limit(app, "daily_request_cap"))
    _increment_and_check(
        app,
        f"ratelimit:{user.id}:day:{now.strftime('%Y%m%d')}",
        24 * 3600,
        daily_cap,
        "daily",
        "You've reached today's free limit. It resets at midnight, or add your own API key to keep "
        "going now.",
    )

    # 5. Monthly (per-user and per-feature) -- the primary defense (PRD §8.1).
    monthly_cap = _effective_user_cap(app, user)
    month_key = _month_key(now)
    _increment_and_check(
        app,
        f"ratelimit:{user.id}:month:{month_key}",
        32 * 24 * 3600,
        monthly_cap,
        "monthly",
        "You've used your free QUILL AI allowance for this month. It resets "
        "on the 1st, or you can add your own API key to continue right away.",
        reset_at,
    )
    feature_cap = _effective_feature_cap(app, user.id, feature)
    _increment_and_check(
        app,
        f"ratelimit:{user.id}:{feature}:month:{month_key}",
        32 * 24 * 3600,
        feature_cap,
        "feature",
        f"You've used this month's free allowance for {feature.replace('_', ' ')}. "
        "Other features may still be available, or add your own API key.",
        reset_at,
    )

    # 6. Cost ceiling -- only worth a Postgres read once we're close to it,
    #    per PRD §8's "cheap early-exit skip below that" note.
    summary = db.session.get(MonthlyUsageSummary, {"user_id": user.id, "year_month": month_key})
    cost_cap = (
        float(user.monthly_cost_cap_usd)
        if user.monthly_cost_cap_usd is not None
        else resolve_limit(app, "monthly_cost_cap_usd")
    )
    if summary is not None and float(summary.total_cost_usd) >= cost_cap * 0.9:
        if float(summary.total_cost_usd) >= cost_cap:
            raise QuotaExceeded(
                "monthly_cost",
                "You've reached this month's free-tier cost ceiling. It "
                "resets on the 1st, or add your own API key to continue.",
                reset_at,
            )

    # 7. Global budget cap -- the backstop, not the everyday control
    #    (PRD §13's "governing principle"). Checked last since it's the
    #    least likely to actually trip in normal operation.
    global_cap = resolve_limit(app, "global_monthly_budget_usd")
    global_spend_key = f"gwspend:{month_key}"
    cached_spend = _redis(app).get(global_spend_key)
    if cached_spend is not None and float(cached_spend) >= global_cap:
        raise FeatureUnavailable(
            "global",
            "Hosted AI is paused for everyone right now while we review "
            "unusual activity — check quillforall.org/status, or use "
            "your own API key in the meantime.",
        )


# --- Large-document safeguards (PRD §14.1) -----------------------------------


def count_tokens(text: str) -> int:
    """A conservative token estimate: ~4 characters per token, the same
    rule of thumb OpenAI's own docs use for English text. This is
    deliberately an overestimate-leaning heuristic (using a real
    tokenizer like ``tiktoken`` is a straightforward upgrade -- see
    ``requirements.txt``'s comment on this -- but even the simple
    heuristic is sufficient to enforce a hard ceiling safely, since being
    conservative only ever rejects a request early, never lets an
    oversized one through)."""
    return max(1, len(text) // 4)


def reject_if_too_large(app, prompt: str, chunks: list[str] | None) -> None:
    """PRD §14.1, layers 2 and 3: the real, server-side size boundary.

    Raises :class:`RequestTooLarge` if the combined prompt + chunks exceed
    ``max_input_tokens``, or if more chunks are supplied than
    ``max_chunks_per_request`` allows -- checked independently of the
    token-count check, so many small chunks can't route around the token
    ceiling (PRD §14.1's third layer).

    Called *before* any OpenAI call is attempted, so a rejected request
    never costs anything.
    """
    chunks = chunks or []
    max_chunks = int(resolve_limit(app, "max_chunks_per_request"))
    if len(chunks) > max_chunks:
        raise RequestTooLarge(
            "too_many_chunks",
            "This request references more document excerpts than the free "
            "tier allows — try a more specific question, or switch to "
            "your own API key for full documents.",
            max_chunks,
            len(chunks),
        )

    combined_text = prompt + "".join(chunks)
    max_tokens = int(resolve_limit(app, "max_input_tokens"))
    counted = count_tokens(combined_text)
    if counted > max_tokens:
        raise RequestTooLarge(
            "input_too_large",
            "This selection is too large for the free tier — try a "
            "shorter passage, or switch to your own API key for full "
            "documents.",
            max_tokens,
            counted,
        )


@dataclass(slots=True)
class RemainingQuota:
    """The shape ``GET /v1/quota`` and every successful ``/v1/chat``
    response return -- purely informational, never itself an enforcement
    point (PRD §8: the client never enforces anything, it only displays)."""

    monthly_cap: int
    monthly_used: int
    daily_cap: int
    daily_used: int
    hourly_cap: int
    hourly_used: int
    reset_at: datetime


def remaining_quota(app, user: User) -> RemainingQuota:
    """Read-only snapshot of a user's current usage vs. their live limits,
    for display purposes only (see :class:`RemainingQuota`'s docstring)."""
    now = datetime.now(UTC)
    client = _redis(app)
    monthly_cap = _effective_user_cap(app, user)
    daily_cap = int(resolve_limit(app, "daily_request_cap"))
    hourly_cap = int(resolve_limit(app, "hourly_request_cap"))

    def _get_int(key: str) -> int:
        value = client.get(key)
        return int(value) if value is not None else 0

    return RemainingQuota(
        monthly_cap=monthly_cap,
        monthly_used=_get_int(f"ratelimit:{user.id}:month:{_month_key(now)}"),
        daily_cap=daily_cap,
        daily_used=_get_int(f"ratelimit:{user.id}:day:{now.strftime('%Y%m%d')}"),
        hourly_cap=hourly_cap,
        hourly_used=_get_int(f"ratelimit:{user.id}:hour:{now.strftime('%Y%m%d%H')}"),
        reset_at=_month_reset_at(now),
    )


def record_usage(
    app,
    user: User,
    device: Device,
    feature: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    estimated_cost_usd: float,
    status: str,
    abuse_flag: str | None = None,
) -> None:
    """Write one :class:`~app.models.UsageEvent` and update the running
    monthly aggregate + the global spend counter, all in one transaction.

    This is the *only* place a request's outcome is durably recorded; if
    this call doesn't happen (e.g. the process crashes between the OpenAI
    call and here), the Redis rate-limit counters incremented in
    :func:`check_request_allowed` still hold the line for that user until
    the next reconciliation job runs (see ``app/cli.py``'s
    ``reconcile-usage`` command) -- a crash can undercount Postgres
    aggregates temporarily, but can never let a user exceed their Redis-
    enforced ceiling.
    """
    from app.models import UsageEvent

    now = datetime.now(UTC)
    month_key = _month_key(now)

    event = UsageEvent(
        user_id=user.id,
        device_id=device.id,
        feature=feature,
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        estimated_cost_usd=estimated_cost_usd,
        status=status,
        abuse_flag=abuse_flag,
    )
    db.session.add(event)

    summary = db.session.get(MonthlyUsageSummary, {"user_id": user.id, "year_month": month_key})
    if summary is None:
        summary = MonthlyUsageSummary(
            user_id=user.id, year_month=month_key, request_count=0, total_cost_usd=0
        )
        db.session.add(summary)
    summary.request_count += 1
    summary.total_cost_usd = float(summary.total_cost_usd) + estimated_cost_usd

    db.session.commit()

    # Update the cached global-spend counter used by the budget-cap check
    # in check_request_allowed; a short TTL keeps it self-healing even if
    # this increment is ever missed for some reason.
    spend_key = f"gwspend:{month_key}"
    client = _redis(app)
    client.incrbyfloat(spend_key, estimated_cost_usd)
    client.expire(spend_key, 40 * 24 * 3600)

    device.last_seen_at = now
    db.session.commit()

    _maybe_alert_on_budget_threshold(app, month_key)


_ALERTED_THRESHOLDS_KEY = "gwalerted:{month}"


def _maybe_alert_on_budget_threshold(app, month_key: str) -> None:
    """PRD §13's 50/75/90/100% alerting, fired at most once per threshold
    per month (tracked in a small Redis set so a burst of requests
    crossing 75% doesn't send fifty Slack messages)."""
    from app.alerts import send_alert

    client = _redis(app)
    spend = float(client.get(f"gwspend:{month_key}") or 0.0)
    cap = resolve_limit(app, "global_monthly_budget_usd")
    if cap <= 0:
        return
    fraction = spend / cap
    alerted_key = _ALERTED_THRESHOLDS_KEY.format(month=month_key)

    for threshold in (1.0, 0.9, 0.75, 0.5):
        if fraction < threshold:
            continue
        member = str(threshold)
        if client.sismember(alerted_key, member):
            break  # already alerted at this threshold (or higher) this month
        client.sadd(alerted_key, member)
        client.expire(alerted_key, 40 * 24 * 3600)
        send_alert(
            app,
            f"QUILL AI Gateway: hosted AI spend has reached {int(threshold * 100)}% "
            f"of this month's ${cap:.2f} budget cap (${spend:.2f} spent).",
        )
        if threshold >= 1.0:
            _auto_pause_hosted_ai(app)
        break


def _auto_pause_hosted_ai(app) -> None:
    """PRD §13: crossing 100% of the global budget cap auto-pauses hosted
    AI for everyone, pending admin review -- it does not wait for a human
    to notice the alert first."""
    from app.models import FeatureFlag

    flag = db.session.get(FeatureFlag, "hosted_ai")
    if flag is None:
        flag = FeatureFlag(
            feature="hosted_ai", enabled=False, disabled_reason="Global monthly budget cap reached."
        )
        db.session.add(flag)
    else:
        flag.enabled = False
        flag.disabled_reason = "Global monthly budget cap reached."
    db.session.commit()
