"""Billing and Usage (billing_usage.py): grouped sentences, a total, and honest refusals."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.github import billing_usage as bu
from quill.core.github.rest_transport import GitHubRestError

NOW = datetime(2026, 11, 13, tzinfo=UTC)


def _reply(answers: dict[str, Any]):
    asked: list[tuple[str, dict[str, str] | None]] = []

    def fake(_token, _method, path, *, query=None, **_kw):
        asked.append((path, query))
        answer = answers[path]
        if isinstance(answer, Exception):
            raise answer
        return SimpleNamespace(data=answer)

    return fake, asked


def test_usage_is_grouped_by_product_and_totalled(monkeypatch) -> None:
    items = [
        {
            "product": "actions",
            "sku": "linux",
            "quantity": 100,
            "unitType": "Minutes",
            "netAmount": 0,
            "grossAmount": 0.8,
        },
        {
            "product": "actions",
            "sku": "linux",
            "quantity": 20,
            "unitType": "Minutes",
            "netAmount": 0.16,
            "grossAmount": 0.16,
        },
        {
            "product": "packages",
            "sku": "storage",
            "quantity": 1.5,
            "unitType": "GigabyteHours",
            "netAmount": 0,
            "grossAmount": 0,
        },
    ]
    fake, asked = _reply({
        "/user": {"login": "octo"},
        "/users/octo/settings/billing/usage": {"usageItems": items},
    })
    monkeypatch.setattr(bu, "request_json", fake)
    rows = bu.fetch_billing_usage("tok", now=NOW)
    assert asked[1] == ("/users/octo/settings/billing/usage", {"year": "2026", "month": "11"})
    assert [r.label for r in rows] == [
        "Actions, Linux: 120 minutes, $0.16 after discounts",
        "Packages, Storage: 1.50 gigabytehours, $0.00 after discounts",
        "Total for November 2026: $0.16 after discounts",
    ]
    assert "Before discounts: $0.96" in rows[0].detail


@pytest.mark.parametrize("status", [401, 403, 404])
def test_a_token_without_plan_access_says_so_rather_than_showing_nothing(
    monkeypatch, status
) -> None:
    fake, _asked = _reply({
        "/user": {"login": "octo"},
        "/users/octo/settings/billing/usage": GitHubRestError("no", status=status),
    })
    monkeypatch.setattr(bu, "request_json", fake)
    (row,) = bu.fetch_billing_usage("tok", now=NOW)
    assert row.label == "GitHub did not share billing usage with this sign-in"
    assert "user scope" in row.detail and row.url == bu.BILLING_URL


def test_no_usage_is_said_not_left_empty(monkeypatch) -> None:
    fake, _asked = _reply({
        "/user": {"login": "octo"},
        "/users/octo/settings/billing/usage": {"usageItems": []},
    })
    monkeypatch.setattr(bu, "request_json", fake)
    (row,) = bu.fetch_billing_usage("tok", now=NOW)
    assert row.label == "No metered usage reported for November 2026"


def test_other_failures_are_raised_for_the_view_to_report(monkeypatch) -> None:
    fake, _asked = _reply({"/user": GitHubRestError("down", status=500)})
    monkeypatch.setattr(bu, "request_json", fake)
    with pytest.raises(GitHubRestError):
        bu.fetch_billing_usage("tok", now=NOW)
