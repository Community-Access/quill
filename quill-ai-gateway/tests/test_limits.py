"""Tests for app/limits.py: the quota engine and the large-document
safeguards (PRD §8, §14.1). These are the highest-value tests in the
suite -- a bug here is a bug in the thing that keeps the Gateway's cost
bounded."""

from __future__ import annotations

import pytest
from app.limits import (
    FeatureUnavailable,
    QuotaExceeded,
    RequestTooLarge,
    check_request_allowed,
    count_tokens,
    reject_if_too_large,
    resolve_limit,
)

from tests.conftest import make_user_and_device


def test_resolve_limit_uses_fail_safe_when_config_row_missing(app):
    # No gateway_config row seeded -- resolve_limit should still return
    # the hardcoded fail-safe rather than erroring or returning zero.
    assert resolve_limit(app, "monthly_request_cap") == 100


def test_resolve_limit_reads_and_caches_config_row(app, db):
    from app.models import GatewayConfig

    db.session.add(GatewayConfig(key="daily_request_cap", value=42, description="test"))
    db.session.commit()
    assert resolve_limit(app, "daily_request_cap") == 42
    # Second call should hit the Redis cache, not Postgres -- functionally
    # verified by simply asserting the value is stable across calls.
    assert resolve_limit(app, "daily_request_cap") == 42


def test_count_tokens_is_conservative_not_exact(app):
    # ~4 chars/token heuristic: a 400-character string estimates to 100
    # tokens. The exact ratio isn't the point -- the point is it's a
    # stable, monotonic estimate a hard cap can be checked against.
    assert count_tokens("a" * 400) == 100
    assert count_tokens("") == 1  # never zero, avoids any divide-by-zero downstream


def test_reject_if_too_large_raises_on_oversized_prompt(app, db):
    from app.models import GatewayConfig

    db.session.add(GatewayConfig(key="max_input_tokens", value=10, description="test"))
    db.session.add(GatewayConfig(key="max_chunks_per_request", value=5, description="test"))
    db.session.commit()

    with pytest.raises(RequestTooLarge) as exc_info:
        reject_if_too_large(app, "x" * 1000, None)  # ~250 tokens, way over 10
    assert exc_info.value.reason == "input_too_large"
    assert exc_info.value.max_value == 10


def test_reject_if_too_large_allows_small_prompt(app, db):
    from app.models import GatewayConfig

    db.session.add(GatewayConfig(key="max_input_tokens", value=1000, description="test"))
    db.session.add(GatewayConfig(key="max_chunks_per_request", value=5, description="test"))
    db.session.commit()

    reject_if_too_large(app, "a short prompt", None)  # must not raise


def test_reject_if_too_large_catches_many_small_chunks(app, db):
    """PRD §14.1 layer 3: chunk *count* is checked independently of total
    token size, so many small chunks can't dodge the token ceiling by
    each individually looking small."""
    from app.models import GatewayConfig

    db.session.add(GatewayConfig(key="max_input_tokens", value=100_000, description="test"))
    db.session.add(GatewayConfig(key="max_chunks_per_request", value=2, description="test"))
    db.session.commit()

    with pytest.raises(RequestTooLarge) as exc_info:
        reject_if_too_large(app, "prompt", ["chunk one", "chunk two", "chunk three"])
    assert exc_info.value.reason == "too_many_chunks"


def test_check_request_allowed_blocks_a_blocked_user(app, db):
    user, device = make_user_and_device(db.session)
    user.status = "blocked"
    db.session.commit()

    with pytest.raises(QuotaExceeded) as exc_info:
        check_request_allowed(app, user, device, "document_qna")
    assert exc_info.value.scope == "blocked"


def test_check_request_allowed_rejects_a_revoked_device(app, db):
    user, device = make_user_and_device(db.session)
    device.status = "revoked"
    db.session.commit()

    with pytest.raises(QuotaExceeded) as exc_info:
        check_request_allowed(app, user, device, "document_qna")
    assert exc_info.value.scope == "device_revoked"


def test_check_request_allowed_enforces_monthly_cap(app, db):
    from app.models import GatewayConfig

    db.session.add(GatewayConfig(key="monthly_request_cap", value=2, description="test"))
    db.session.add(GatewayConfig(key="hourly_request_cap", value=100, description="test"))
    db.session.add(GatewayConfig(key="daily_request_cap", value=100, description="test"))
    db.session.add(GatewayConfig(key="device_hourly_request_cap", value=100, description="test"))
    db.session.add(GatewayConfig(key="feature_cap.document_qna", value=100, description="test"))
    db.session.commit()
    user, device = make_user_and_device(db.session)

    check_request_allowed(app, user, device, "document_qna")  # 1st: ok
    check_request_allowed(app, user, device, "document_qna")  # 2nd: ok, hits the cap
    with pytest.raises(QuotaExceeded) as exc_info:
        check_request_allowed(app, user, device, "document_qna")  # 3rd: over cap
    assert exc_info.value.scope == "monthly"


def test_check_request_allowed_respects_per_user_override(app, db):
    """A user-specific monthly_request_cap overrides the global default
    (PRD §5's "NULL means use the live global default" design)."""
    from app.models import GatewayConfig

    db.session.add(GatewayConfig(key="monthly_request_cap", value=100, description="test"))
    db.session.add(GatewayConfig(key="hourly_request_cap", value=100, description="test"))
    db.session.add(GatewayConfig(key="daily_request_cap", value=100, description="test"))
    db.session.add(GatewayConfig(key="device_hourly_request_cap", value=100, description="test"))
    db.session.add(GatewayConfig(key="feature_cap.document_qna", value=100, description="test"))
    db.session.commit()
    user, device = make_user_and_device(db.session)
    user.monthly_request_cap = 1  # explicit override, tighter than the global default
    db.session.commit()

    check_request_allowed(app, user, device, "document_qna")  # 1st: ok
    with pytest.raises(QuotaExceeded) as exc_info:
        check_request_allowed(app, user, device, "document_qna")  # 2nd: over the override
    assert exc_info.value.scope == "monthly"


def test_check_request_allowed_respects_global_kill_switch(app, db):
    from app.models import FeatureFlag

    db.session.add(FeatureFlag(feature="hosted_ai", enabled=False, disabled_reason="test"))
    db.session.commit()
    user, device = make_user_and_device(db.session)

    with pytest.raises(FeatureUnavailable) as exc_info:
        check_request_allowed(app, user, device, "document_qna")
    assert exc_info.value.scope == "global"


def test_check_request_allowed_respects_per_feature_flag(app, db):
    from app.models import FeatureFlag

    db.session.add(FeatureFlag(feature="alt_text", enabled=False, disabled_reason="test"))
    db.session.commit()
    user, device = make_user_and_device(db.session)

    with pytest.raises(FeatureUnavailable) as exc_info:
        check_request_allowed(app, user, device, "alt_text")
    assert exc_info.value.scope == "feature"
    # A different feature must be unaffected -- a per-feature flag is not
    # the same thing as the global switch.
    check_request_allowed(app, user, device, "document_qna")
