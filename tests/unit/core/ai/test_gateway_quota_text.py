"""The allowance in words, shared by AI Usage and both About windows."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from quill.core.ai.gateway_client import GatewayQuota
from quill.core.ai.gateway_quota_text import describe_quota, starter_ends

NOW = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)


def _starter(hours_left: float) -> GatewayQuota:
    return GatewayQuota(
        monthly_cap=15,
        daily_cap=20,
        starter_until=(NOW + timedelta(hours=hours_left)).isoformat(),
        standard_monthly_cap=100,
    )


def test_a_starter_allowance_is_explained_not_just_shown():
    """ "15 of 15 left" with no reason read as a mistake to somebody told 100
    (reported 2026-09-25). The server says when it ends; this says why."""
    text = describe_quota(_starter(30), now=NOW)
    assert "15 of 15 requests left" in text
    assert "connected recently" in text
    assert "becomes 100 a month on its own" in text
    assert "Get Help from Support" in text
    assert "Today\n15 left." in text


def test_an_ordinary_allowance_says_nothing_about_starting():
    quota = GatewayQuota(monthly_cap=100, monthly_used=10, daily_cap=20, daily_used=2)
    text = describe_quota(quota, now=NOW)
    assert "connected recently" not in text
    assert "90 of 100 requests left" in text


def test_a_starter_allowance_already_over_is_not_mentioned():
    assert starter_ends(_starter(-1), now=NOW) is None


def test_an_old_server_that_sends_no_end_time_is_fine():
    assert starter_ends(GatewayQuota(monthly_cap=15, daily_cap=20), now=NOW) is None


def test_the_end_is_read_from_the_servers_json():
    quota = GatewayQuota.from_json({
        "monthly_request_cap": 15,
        "starter_until": "2026-09-26T10:00:00+00:00",
        "standard_monthly_request_cap": 100,
    })
    assert quota.standard_monthly_cap == 100
    assert starter_ends(quota, now=NOW) is not None
