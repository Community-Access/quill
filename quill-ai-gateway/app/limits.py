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
from datetime import UTC, datetime, timedelta

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
    "review_daily_request_cap": 5,
    "max_input_tokens": 1500,
    "max_output_tokens": 500,
    "max_chunks_per_request": 3,
    "max_image_bytes": 3 * 1024 * 1024,
    "max_image_edge_px": 1600,
    "daily_image_cap": 0,
    "monthly_cost_cap_usd": 0.08,
    "global_monthly_budget_usd": 25.0,
    # Sign-up protection. The fail-safes here are deliberately *permissive
    # enough to work* rather than at the floor: a zero registration cap would
    # refuse every new user, and an unseeded database that silently did that
    # would look exactly like an outage.
    "new_account_hours": 48,
    "new_account_request_cap": 15,
    "registration_hourly_cap_per_ip": 5,
    "registration_daily_cap_per_ip": 20,
    "active_devices_cap_per_ip": 6,
    "network_monthly_request_cap": 600,
}

#: What ``flask seed-config`` writes into a fresh database.
#:
#: Deliberately **not** the same table as the fail-safes above, and the
#: difference is the point. A fail-safe is what a missing row falls back to, so
#: it must never be more permissive than intended -- the global budget cap's
#: fail-safe stays at the original $25 for that reason. A seed value is a
#: recommendation for a real deployment, and the recommended cap is $40: the
#: 500-user worst case at the shipped limits is $20 a month, and a cap only 25%
#: above the worst case is one that normal operation leans on rather than a
#: backstop that never fires.
SEED_DEFAULTS: dict[str, float] = {
    **_FAIL_SAFE_DEFAULTS,
    "global_monthly_budget_usd": 40.0,
}

# Per-feature monthly caps are a distinct family of config keys
# (feature_cap.<feature>) with their own fail-safes, since they're ceilings
# *within* the overall monthly total, not standalone limits.
#
# The two deferred features (app/prompts.py's DEFERRED_FEATURES) get a cap of
# zero as well as a disabled flag. Belt and braces on purpose: a feature that is
# switched off in one place and uncapped in another is one flag flip away from
# being live and unlimited at the same time.
_FEATURE_CAP_FAIL_SAFE_DEFAULTS: dict[str, float] = {
    "summarize": 60,
    "rewrite": 60,
    "proofread": 60,
    "explain": 60,
    "document_qna": 60,
    "alt_text": 0,
    "chat": 0,
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


class RegistrationThrottled(Exception):
    """Raised when one internet address has started too many sign-ups.

    A distinct exception rather than a :class:`QuotaExceeded`, because it
    happens *before* any account exists -- there is no user to attribute it to
    and no allowance to report. The message must never read as a fault in the
    caller's computer: the person hitting it is usually an ordinary user behind
    a shared address, not the scripted abuse it is aimed at.
    """

    def __init__(self, message: str, retry_after_seconds: int) -> None:
        super().__init__(message)
        self.message = message
        self.retry_after_seconds = retry_after_seconds


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


def is_new_account(app, user: User, now: datetime | None = None) -> bool:
    """True while *user* is inside the new-account window.

    The window exists because anonymous registration is free to script: nothing
    stops somebody minting accounts, and each one used to arrive with a full
    monthly allowance. A ramp makes a throwaway account worth a fraction of a
    real one, which is what makes farming them uneconomic -- while a genuine
    new user, who is exploring rather than grinding, rarely reaches even the
    reduced number on their first day.
    """
    hours = resolve_limit(app, "new_account_hours")
    if hours <= 0:
        return False
    created = user.created_at
    if created is None:
        return False
    if created.tzinfo is None:  # SQLite hands back naive datetimes
        created = created.replace(tzinfo=UTC)
    return (now or datetime.now(UTC)) - created < timedelta(hours=hours)


def starter_allowance_ends_at(app, user: User, now: datetime | None = None) -> datetime | None:
    """When this user's new-account allowance gives way to the normal one.

    ``None`` when it does not apply: the account is past the window, or an
    admin has set this person's cap by hand (which always wins, see
    :func:`_effective_user_cap`). Reported by ``/v1/quota`` so the client can
    *explain* a smaller number rather than just show one -- "15 left" with no
    reason reads as a mistake to somebody who was told 100.
    """
    if user.monthly_request_cap is not None or not is_new_account(app, user, now):
        return None
    created = user.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return created + timedelta(hours=resolve_limit(app, "new_account_hours"))


def _effective_user_cap(app, user: User) -> int:
    """The monthly request cap that actually applies to *this* user.

    In order: an admin's explicit per-user override always wins, because it is
    the only value somebody deliberately typed for this person. Otherwise a
    brand-new account gets the ramp (:func:`is_new_account`), and everyone else
    gets the live global default.
    """
    normal = int(resolve_limit(app, "monthly_request_cap"))
    if user.monthly_request_cap is not None:
        return user.monthly_request_cap
    if is_new_account(app, user):
        # Never *more* than an established account would get. The two values are
        # independent dials, so an operator who lowers the monthly cap below the
        # ramp would otherwise hand new accounts a larger allowance than
        # everybody else -- turning the anti-farming measure into an incentive
        # to keep making fresh accounts. Caught by an existing monthly-cap test
        # that set the cap to 2 and watched a brand-new user sail past it.
        return min(int(resolve_limit(app, "new_account_request_cap")), normal)
    return normal


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
    """Refuse a switched-off feature, saying *why* it is off.

    The stored ``disabled_reason`` is used when there is one, which matters more
    than it looks: a feature that was never shipped and a feature paused for an
    hour are completely different facts, and telling somebody their request is
    "temporarily paused while we review unusual activity" when it is actually
    "this was never built" sends them to support for no reason. The deferred
    features (``app/prompts.py``'s ``DEFERRED_FEATURES``) are seeded with their
    own explanation for exactly this.
    """
    from app.models import FeatureFlag

    flag = db.session.get(FeatureFlag, feature)
    if flag is not None and not flag.enabled:
        reason = (flag.disabled_reason or "").strip()
        if reason:
            raise FeatureUnavailable("feature", reason)
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
        reduced_cap = int(resolve_limit(app, "review_daily_request_cap"))
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


# --- Undoing a charge for something that never happened -----------------------


def refund_request(
    app, user: User, device: Device, feature: str, now: datetime | None = None
) -> None:
    """Give back the counters :func:`check_request_allowed` took.

    The counters are incremented *up front*, before the size check, before the
    model is resolved and before anything is sent, because a rate limiter that
    reads before it writes can be raced past its own cap by two concurrent
    requests. That ordering is correct and it has a consequence: every failure
    path after the gate has already charged somebody for a request that was
    never made. An oversized selection, an upstream outage, a misconfigured
    model, a reply that spent its whole budget thinking -- all of them used to
    quietly cost the user one of their hundred.

    They cannot see the counter move, so they have no way to notice and no way
    to argue. That is precisely why this exists, and why every message on those
    paths is allowed to say "nothing was used": because it is now true.

    Decrements are floored at zero. Redis has no atomic "decrement but not below
    zero", and a counter driven negative by a double refund would hand out free
    requests -- the exact failure this whole module exists to prevent.
    """
    now = now or datetime.now(UTC)
    month_key = _month_key(now)
    client = _redis(app)

    keys = [
        f"ratelimit:{user.id}:hour:{now.strftime('%Y%m%d%H')}",
        f"ratelimit:device:{device.id}:hour:{now.strftime('%Y%m%d%H')}",
        f"ratelimit:{user.id}:day:{now.strftime('%Y%m%d')}",
        f"ratelimit:{user.id}:month:{month_key}",
        f"ratelimit:{user.id}:{feature}:month:{month_key}",
    ]
    if user.status == "review":
        keys.append(f"ratelimit:{user.id}:review_daily")

    for key in keys:
        try:
            if client.decr(key) < 0:
                client.set(key, 0, keepttl=True)
        except Exception:  # noqa: BLE001 - a failed refund must not fail the response
            app.logger.warning("Could not refund rate-limit key %s", key, exc_info=True)


# --- Sign-up protection ------------------------------------------------------


def check_registration_allowed(app, client_ip: str) -> None:
    """Gate on ``POST /v1/device/code`` before a sign-up flow may start.

    This is the hole every per-user quota in this module would otherwise leave
    open. Registration is anonymous and unauthenticated on purpose -- "no
    account, no password, no email" is the accessibility win the whole product
    rests on -- but it means an allowance is not a cost bound, it is a cost
    *quantum*: anyone who can script three HTTP requests can mint as many
    allowances as they like, and the only thing that would eventually stop them
    is the global budget cap switching hosted AI off for every legitimate user.

    Two fixed windows per address, both live-tunable. An empty or unknown
    address is *allowed* rather than refused: a proxy misconfiguration must not
    take sign-ups down, and the cost of the alternative is a wrong-looking
    outage nobody can diagnose from the client end.
    """
    ip = (client_ip or "").strip()
    if not ip:
        return

    now = datetime.now(UTC)
    client = _redis(app)

    hourly_cap = int(resolve_limit(app, "registration_hourly_cap_per_ip"))
    if hourly_cap > 0:
        key = f"reg:ip:{ip}:hour:{now.strftime('%Y%m%d%H')}"
        current = client.incr(key)
        if current == 1:
            client.expire(key, 3600)
        if current > hourly_cap:
            raise RegistrationThrottled(
                "Too many computers have connected from this network recently. "
                "Try again in an hour.",
                3600,
            )

    daily_cap = int(resolve_limit(app, "registration_daily_cap_per_ip"))
    if daily_cap > 0:
        key = f"reg:ip:{ip}:day:{now.strftime('%Y%m%d')}"
        current = client.incr(key)
        if current == 1:
            client.expire(key, 24 * 3600)
        if current > daily_cap:
            raise RegistrationThrottled(
                "Too many computers have connected from this network today. Try again tomorrow.",
                24 * 3600,
            )


def check_device_budget(app, client_ip: str) -> None:
    """Refuse a sign-up from an address that already has plenty of computers.

    The rate throttle above stops a *burst*. It does not stop somebody
    connecting one more machine every few days, and that matters here more than
    it would elsewhere, because of a design decision further up: confirming a
    device code creates a brand-new pseudonymous **user**, not another device on
    an existing account. Two computers are therefore two accounts with a full
    allowance each, and five are five.

    That is the right trade for the accessibility premise -- no account, no
    password, no email -- and it means the honest place to bound a *person* is
    the one thing their computers have in common. A standing cap on how many
    active devices one address holds is that bound.

    Set generously. This is aimed at one household quietly running six laptops
    through the free tier, not at an office, and the number is a live
    ``gateway_config`` row precisely because the first report of it catching a
    real workplace should be answerable in one edit rather than one release.
    """
    ip = (client_ip or "").strip()
    if not ip:
        return
    cap = int(resolve_limit(app, "active_devices_cap_per_ip"))
    if cap <= 0:
        return

    count = int(_redis(app).get(f"reg:devices:{ip}") or 0)
    if count >= cap:
        raise RegistrationThrottled(
            "There are already several computers connected to QUILL's free AI "
            "from this network. Sign one of them out first -- in QUILL Lite, "
            "Tools, AI, Usage -- and this one can connect.",
            24 * 3600,
        )


def note_device_registered(app, client_ip: str) -> None:
    """Count one more active device against this address.

    Kept in Redis with a long expiry rather than derived from the database on
    every sign-up: the address a device registered from is not stored on the
    device row, and adding it would put a piece of network metadata into a
    schema whose whole claim is that it holds no more about a person than it
    must.
    """
    ip = (client_ip or "").strip()
    if not ip:
        return
    client = _redis(app)
    key = f"reg:devices:{ip}"
    client.incr(key)
    client.expire(key, 400 * 24 * 3600)


def release_device_slot(app, client_ip: str) -> None:
    """Give a slot back when a device is signed out.

    Without this the cap is a lifetime total rather than a standing one, and
    somebody who dutifully signs out an old laptop before connecting a new one
    would be refused for doing exactly the right thing.
    """
    ip = (client_ip or "").strip()
    if not ip:
        return
    client = _redis(app)
    key = f"reg:devices:{ip}"
    try:
        if client.decr(key) < 0:
            client.set(key, 0, keepttl=True)
    except Exception:  # noqa: BLE001 - a lost slot must not fail a sign-out
        app.logger.warning("Could not release a device slot for %s", key, exc_info=True)


def check_network_budget(app, client_ip: str) -> None:
    """One shared monthly request ceiling for everybody behind one address.

    The measure that actually makes sponging uneconomic. Per-user caps cannot,
    because a user is free to mint: five computers are five accounts and five
    allowances. A ceiling counted per *network* is indifferent to how many
    accounts sit behind it.

    Deliberately several times a single person's allowance, so a genuinely
    shared address -- a family, a small office -- is never the one this catches.
    An unknown address is allowed rather than refused, for the same reason the
    sign-up throttle allows it: a proxy misconfiguration must not look like an
    outage.
    """
    ip = (client_ip or "").strip()
    if not ip:
        return
    cap = int(resolve_limit(app, "network_monthly_request_cap"))
    if cap <= 0:
        return

    month_key = _month_key()
    key = f"ratelimit:net:{ip}:month:{month_key}"
    client = _redis(app)
    current = client.incr(key)
    if current == 1:
        client.expire(key, 32 * 24 * 3600)
    if current > cap:
        raise QuotaExceeded(
            "network",
            "This network has used its share of QUILL's free AI for this month. "
            "It starts again on the 1st, or you can add your own API key to "
            "keep going now.",
            _month_reset_at(),
        )


def refund_network_request(app, client_ip: str) -> None:
    """Give back a network request that never happened.

    Counted up front like every other limit here, so it needs the same undo --
    see :func:`refund_request` for why the counters are taken before the work
    rather than after it.
    """
    ip = (client_ip or "").strip()
    if not ip:
        return
    key = f"ratelimit:net:{ip}:month:{_month_key()}"
    client = _redis(app)
    try:
        if client.decr(key) < 0:
            client.set(key, 0, keepttl=True)
    except Exception:  # noqa: BLE001 - a failed refund must not fail the response
        app.logger.warning("Could not refund network key %s", key, exc_info=True)


def note_registration_blocked(app) -> None:
    """Count one refused sign-up, for the console's safety-checks page."""
    key = f"reg:blocked:{datetime.now(UTC).strftime('%Y%m%d')}"
    client = _redis(app)
    if client.incr(key) == 1:
        client.expire(key, 3 * 24 * 3600)


def registrations_blocked_today(app) -> int:
    """How many sign-ups the throttle refused today.

    A protection with no visible effect is indistinguishable from one that is
    switched off, which is why this number is on the safety-checks page rather
    than only in a log.
    """
    value = _redis(app).get(f"reg:blocked:{datetime.now(UTC).strftime('%Y%m%d')}")
    return int(value) if value is not None else 0


# --- Giving somebody their allowance back ------------------------------------


def reset_user_usage(app, user: User, now: datetime | None = None) -> dict[str, float]:
    """Put *user* back to zero for the current month. Returns what was cleared.

    **Both halves, always.** The request counters live in Redis and the running
    cost total lives in Postgres, and they are checked by different fences: the
    counters by the monthly, daily and hourly caps, the cost total by the
    per-user cost ceiling. Clearing only the counters leaves the cost ceiling
    still refusing the person, so the reset looks like it silently did nothing;
    clearing only the total leaves them still out of requests. Either half on
    its own is a support ticket, which is why this is one function and not two
    buttons.

    The global spend counter is deliberately *not* touched. That money was
    really spent, and a per-user courtesy must never quietly edit the number the
    budget cap protects everybody with.
    """
    from app.prompts import FEATURES

    now = now or datetime.now(UTC)
    month_key = _month_key(now)
    client = _redis(app)

    keys = [
        f"ratelimit:{user.id}:month:{month_key}",
        f"ratelimit:{user.id}:day:{now.strftime('%Y%m%d')}",
        f"ratelimit:{user.id}:hour:{now.strftime('%Y%m%d%H')}",
        f"ratelimit:{user.id}:review_daily",
    ]
    keys.extend(f"ratelimit:{user.id}:{feature}:month:{month_key}" for feature in sorted(FEATURES))
    for device in list(user.devices):
        keys.append(f"ratelimit:device:{device.id}:hour:{now.strftime('%Y%m%d%H')}")

    counters_cleared = 0
    for key in keys:
        counters_cleared += int(client.delete(key) or 0)

    summary = db.session.get(MonthlyUsageSummary, {"user_id": user.id, "year_month": month_key})
    requests_cleared = 0
    cost_cleared = 0.0
    if summary is not None:
        requests_cleared = int(summary.request_count)
        cost_cleared = float(summary.total_cost_usd)
        summary.request_count = 0
        summary.total_cost_usd = 0
        db.session.commit()

    return {
        "counters_cleared": counters_cleared,
        "requests_cleared": requests_cleared,
        "cost_cleared_usd": cost_cleared,
    }


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
    reasoning_tokens: int = 0,
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
        reasoning_tokens=reasoning_tokens,
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
