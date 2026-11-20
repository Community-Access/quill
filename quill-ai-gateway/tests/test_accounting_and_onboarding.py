"""Hosted-AI accounting and onboarding, made trustworthy (2026-11-20).

Every test here reproduces a defect the gateway review in the repository's
``plan.md`` found ("Hosted AI gateway review"), and failed before the fix:

* Nightly reconciliation rebuilt a person's monthly cost from the *full* event
  cost, search fee included, so a $0.001 search became $0.031 overnight.
* Two confirmations of one device code both succeeded: two accounts and two
  devices were created and counted, and only one token was ever delivered.
* A Redis restart or eviction wiped the global spend and the monthly counters,
  which reopened the budget cap and gave everybody a fresh month.
* Signing a computer out gave its place back to whichever network the person
  happened to be on, not the one it was counted against.
* A provider reply that was HTTP 200 but not the expected JSON escaped the
  error-and-refund path.
* The admin's "Reduced quota" status reduced nothing.
* The Switches page said "five features" over a list of eighteen.

No test opens a socket: the provider calls are replaced where they are made.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import requests
from app.auth import (
    confirm_device_code,
    hash_token,
    poll_device_token,
    start_device_flow,
)
from app.limits import WEB_SEARCH_CALL_COST_USD, _month_key
from app.models import (
    Device,
    FeatureFlag,
    GatewayConfig,
    MonthlyUsageSummary,
    UsageEvent,
    User,
)
from app.openai_client import Completion

from tests.conftest import (
    make_user_and_device,
    seed_config_rows,
    seed_default_model,
    seed_feature_flags,
)

_HEADERS = {"Authorization": "Bearer user-token"}


@pytest.fixture()
def caller(app, db):
    seed_default_model(db.session)
    seed_config_rows(db.session)
    seed_feature_flags(db.session)
    user, _device = make_user_and_device(db.session, token="user-token")
    return user


def _answer(monkeypatch, text: str = "Done.") -> None:
    monkeypatch.setattr(
        "app.routes.chat.complete",
        lambda *_a, **_k: Completion(text=text, tokens_in=1000, tokens_out=200),
    )


def _summarize(client, headers=_HEADERS):
    return client.post(
        "/v1/chat", json={"feature": "summarize", "prompt": "Some text."}, headers=headers
    )


# --------------------------------------------------------------------------- #
# 1. Reconciliation keeps the person's cost and the global cost apart
# --------------------------------------------------------------------------- #


def _switch_search_on(db) -> None:
    flag = db.session.get(FeatureFlag, "web_search") or FeatureFlag(feature="web_search")
    flag.enabled = True
    flag.disabled_reason = None
    db.session.add(flag)
    db.session.commit()


def test_reconciliation_after_a_search_keeps_the_persons_cost(app, client, caller, db, monkeypatch):
    """The review's probe: $0.001 before the nightly job, $0.031 after it.

    A search's per-search charge reaches the usage event and the global budget,
    and deliberately not the person's own cost ceiling. The nightly
    ``reconcile-usage`` job rebuilt the person's total from the full event cost,
    so it quietly moved the fee onto them -- enough, after three searches, to
    shut every other feature off for the month.
    """
    _switch_search_on(db)
    monkeypatch.setattr(
        "app.routes.chat.search",
        lambda *_a, **_k: Completion(
            text="Answer. Source: example.org", tokens_in=5000, tokens_out=1000
        ),
    )
    reply = client.post(
        "/v1/chat", json={"feature": "web_search", "prompt": "q?"}, headers=_HEADERS
    )
    assert reply.status_code == 200

    month = _month_key()
    summary = db.session.get(MonthlyUsageSummary, {"user_id": caller.id, "year_month": month})
    before = float(summary.total_cost_usd)
    token_cost = 5000 / 1e6 * 0.10 + 1000 / 1e6 * 0.50
    assert before == pytest.approx(token_cost)

    event = db.session.query(UsageEvent).one()
    # The durable record carries both figures: what was spent, and what of it
    # counts against this person.
    assert float(event.estimated_cost_usd) == pytest.approx(token_cost + WEB_SEARCH_CALL_COST_USD)
    assert float(event.user_cost_usd) == pytest.approx(token_cost)

    result = app.test_cli_runner().invoke(args=["reconcile-usage"])
    assert result.exit_code == 0, result.output

    db.session.expire_all()
    summary = db.session.get(MonthlyUsageSummary, {"user_id": caller.id, "year_month": month})
    assert float(summary.total_cost_usd) == pytest.approx(before)
    assert summary.request_count == 1


def test_reconciliation_counts_an_event_from_before_the_split_at_its_full_cost(app, caller, db):
    """A row written before ``user_cost_usd`` existed has no person's share
    recorded; migration 010 back-fills it, and reconciliation treats a row it
    did not reach as the whole cost rather than as nothing."""
    _user, device = caller, db.session.query(Device).one()
    db.session.add(
        UsageEvent(
            user_id=caller.id,
            device_id=device.id,
            feature="summarize",
            model="gpt-5-nano",
            tokens_in=10,
            tokens_out=10,
            estimated_cost_usd=0.002,
            user_cost_usd=None,
            status="allowed",
        )
    )
    db.session.commit()

    assert app.test_cli_runner().invoke(args=["reconcile-usage"]).exit_code == 0
    summary = db.session.get(
        MonthlyUsageSummary, {"user_id": caller.id, "year_month": _month_key()}
    )
    assert float(summary.total_cost_usd) == pytest.approx(0.002)


def test_reconciliation_restores_a_lost_global_spend_figure(app, client, caller, db, monkeypatch):
    _answer(monkeypatch)
    assert _summarize(client).status_code == 200
    event_cost = float(db.session.query(UsageEvent).one().estimated_cost_usd)

    redis = app.extensions["gateway_redis"]
    redis.delete(f"gwspend:{_month_key()}")

    assert app.test_cli_runner().invoke(args=["reconcile-usage"]).exit_code == 0
    assert float(redis.get(f"gwspend:{_month_key()}")) == pytest.approx(event_cost)


# --------------------------------------------------------------------------- #
# 2. A device code is confirmed once, atomically
# --------------------------------------------------------------------------- #


def test_two_confirmations_of_one_code_create_one_device(app, db, monkeypatch):
    """The review's deterministic interleaving: the second confirmation runs
    while the first is between reading the pending grant and writing it back.

    Before the fix both returned success, two users and two devices were
    created and counted against the network, and only one token was ever
    delivered -- the other device was an orphan nobody could sign out.
    """
    import app.auth as auth_module

    with app.app_context():
        result = start_device_flow(app)
        code = result["user_code"]

        real_token = auth_module._generate_opaque_token
        outcomes: list[bool] = []
        started: list[bool] = []

        def interleave() -> str:
            if not started:  # only the outer confirmation triggers the inner one
                started.append(True)
                outcomes.append(confirm_device_code(app, code))
            return real_token()

        monkeypatch.setattr(auth_module, "_generate_opaque_token", interleave)
        outcomes.append(confirm_device_code(app, code))
        monkeypatch.setattr(auth_module, "_generate_opaque_token", real_token)

        assert sorted(outcomes) == [False, True]
        assert db.session.query(Device).count() == 1
        assert db.session.query(User).count() == 1

        status, body = poll_device_token(app, result["device_code"])
        assert status == 200
        device = db.session.query(Device).one()
        assert body["device_id"] == device.id
        assert hash_token(body["token"]) == device.token_hash


def test_a_poll_racing_a_confirmation_cannot_lose_the_token(app, db, monkeypatch):
    """A poll used to read the whole grant, stamp ``last_poll_at`` on it and
    write the whole grant back. A confirmation landing between the read and the
    write was overwritten by the stale ``pending`` copy: the device existed and
    its token was gone for good."""
    import app.auth as auth_module

    with app.app_context():
        result = start_device_flow(app)
        real_seconds_left = auth_module._seconds_left
        fired: list[bool] = []
        started: list[bool] = []

        def confirm_mid_poll(grant, now):
            if not started:
                started.append(True)
                fired.append(confirm_device_code(app, result["user_code"]))
            return real_seconds_left(grant, now)

        monkeypatch.setattr(auth_module, "_seconds_left", confirm_mid_poll)
        first = poll_device_token(app, result["device_code"])
        monkeypatch.setattr(auth_module, "_seconds_left", real_seconds_left)
        assert fired == [True]
        assert first[0] in (200, 428)
        if first[0] == 428:
            app.extensions["gateway_redis"].delete(f"devpoll:{result['device_code']}")
            first = poll_device_token(app, result["device_code"])
        assert first[0] == 200
        assert hash_token(first[1]["token"]) == db.session.query(Device).one().token_hash


def test_a_confirmation_that_fails_part_way_can_be_retried(app, db, monkeypatch):
    """The claim is taken before any row is written. If writing the rows fails,
    the claim is given back, so the person's retry works rather than being told
    their perfectly good code is not recognised."""
    with app.app_context():
        result = start_device_flow(app)

        real_commit = db.session.commit
        calls = {"n": 0}

        def fail_once():
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("database went away")
            return real_commit()

        monkeypatch.setattr(db.session, "commit", fail_once)
        with pytest.raises(RuntimeError):
            confirm_device_code(app, result["user_code"])
        monkeypatch.setattr(db.session, "commit", real_commit)
        db.session.rollback()

        assert confirm_device_code(app, result["user_code"]) is True
        assert db.session.query(Device).count() == 1


# --------------------------------------------------------------------------- #
# 3. What survives Redis losing its data
# --------------------------------------------------------------------------- #


def test_the_budget_cap_still_holds_after_redis_loses_the_spend(
    app, client, caller, db, monkeypatch
):
    """The global spend lived only in Redis. Losing it -- a restart with no
    persistence, or an eviction -- read as "nothing spent this month", and the
    budget cap stopped protecting anything until the month turned over."""
    _answer(monkeypatch)
    db.session.get(GatewayConfig, "global_monthly_budget_usd").value = 1.0
    device = db.session.query(Device).one()
    db.session.add(
        UsageEvent(
            user_id=caller.id,
            device_id=device.id,
            feature="summarize",
            model="gpt-5-nano",
            tokens_in=1,
            tokens_out=1,
            estimated_cost_usd=1.5,
            user_cost_usd=0.0,
            status="allowed",
        )
    )
    db.session.commit()
    app.extensions["gateway_redis"].flushall()

    reply = _summarize(client)
    assert reply.status_code == 503
    assert reply.get_json()["scope"] == "global"


def test_a_lost_monthly_counter_is_rebuilt_from_the_summary(app, client, caller, db, monkeypatch):
    """The month's request count is the primary allowance. Redis losing it
    handed the person a fresh month; it is now rebuilt from the durable summary
    the first time it is missed."""
    _answer(monkeypatch)
    caller.monthly_request_cap = 3
    db.session.add(
        MonthlyUsageSummary(
            user_id=caller.id, year_month=_month_key(), request_count=3, total_cost_usd=0
        )
    )
    db.session.commit()

    reply = _summarize(client)
    assert reply.status_code == 429
    assert reply.get_json()["scope"] == "monthly"


def test_a_reset_is_not_undone_by_the_rebuild(app, client, caller, db, monkeypatch):
    """Resetting somebody's month clears the summary in the same breath as the
    counters, so the rebuild finds nothing to restore."""
    from app.limits import reset_user_usage

    _answer(monkeypatch)
    caller.monthly_request_cap = 3
    db.session.commit()
    for _ in range(3):
        assert _summarize(client).status_code == 200
    assert _summarize(client).status_code == 429

    reset_user_usage(app, caller)
    assert _summarize(client).status_code == 200


def test_production_redis_keeps_its_data_and_never_evicts():
    """Which state must survive is decided in the compose file, and this pins
    it: an append-only file on a named volume, and no eviction policy that may
    throw a quota counter or the spend figure away to make room."""
    import re
    from pathlib import Path

    text = (Path(__file__).resolve().parents[1] / "docker-compose.prod.yml").read_text("utf-8")
    # The redis service block: from "  redis:" to the next service at the same indent.
    block = re.search(r"^  redis:\n(.*?)(?=^  \w[\w-]*:\n)", text, re.S | re.M).group(1)
    lines = [line for line in block.splitlines() if not line.strip().startswith("#")]
    command = " ".join(
        line for line in lines if "redis-server" in line or line.strip().startswith("--")
    )
    assert "--appendonly yes" in command
    assert "--maxmemory-policy noeviction" in command
    assert "allkeys" not in command
    mount = re.search(r"-\s*([\w-]+):/data\b", "\n".join(lines))
    assert mount, "redis must keep /data on a named volume"
    top_level_volumes = text.split("\nvolumes:\n", 1)[1]
    assert re.search(rf"^  {re.escape(mount.group(1))}:", top_level_volumes, re.M)


# --------------------------------------------------------------------------- #
# 4. Dollar ceilings are estimates, and say so
# --------------------------------------------------------------------------- #


def test_the_money_limits_do_not_claim_to_be_exact():
    from app.config_schema import describe

    for key in ("monthly_cost_cap_usd", "global_monthly_budget_usd"):
        entry = describe(key)
        text = f"{entry.sentence} {entry.consequence}"
        assert "whatever happens" not in text
        assert "in flight" in text or "already being answered" in text


# --------------------------------------------------------------------------- #
# 6. The smaller gaps
# --------------------------------------------------------------------------- #


def test_signing_out_gives_the_place_back_to_the_network_it_was_counted_against(
    app, client, caller, db
):
    """Counted against the address that registered; released against whatever
    address the person signs out from. A laptop connected at home and signed
    out at a library left the home slot taken for 400 days, and handed the
    library one it never had."""
    home, library = "203.0.113.50", "198.51.100.77"
    redis = app.extensions["gateway_redis"]

    code = client.post("/v1/device/code", headers={"X-Forwarded-For": home}).get_json()
    confirmed = client.post(
        "/connect", data={"code": code["user_code"]}, headers={"X-Forwarded-For": home}
    )
    assert confirmed.status_code == 200
    assert redis.get(f"reg:devices:{home}") == "1"

    token = client.post("/v1/device/token", json={"device_code": code["device_code"]}).get_json()
    signed_out = client.delete(
        f"/v1/devices/{token['device_id']}",
        headers={"Authorization": f"Bearer {token['token']}", "X-Forwarded-For": library},
    )
    assert signed_out.status_code == 204
    assert redis.get(f"reg:devices:{home}") == "0"
    assert redis.get(f"reg:devices:{library}") is None


def test_a_device_counts_against_the_network_that_was_checked(app, client, caller):
    """The cap is checked against the computer's address when the code is
    minted. Counting it against the address the confirmation page was opened
    from -- often a phone on mobile data -- let a household walk round it."""
    home, phone = "203.0.113.51", "192.0.2.80"
    redis = app.extensions["gateway_redis"]
    code = client.post("/v1/device/code", headers={"X-Forwarded-For": home}).get_json()
    client.post("/connect", data={"code": code["user_code"]}, headers={"X-Forwarded-For": phone})
    assert redis.get(f"reg:devices:{home}") == "1"
    assert redis.get(f"reg:devices:{phone}") is None


class _Reply:
    def __init__(self, payload=None, *, broken_json: bool = False) -> None:
        self.status_code = 200
        self._payload = payload
        self._broken = broken_json

    def raise_for_status(self) -> None:
        return None

    def json(self):
        if self._broken:
            raise requests.exceptions.JSONDecodeError("Expecting value", "<html>", 0)
        return self._payload


@pytest.mark.parametrize(
    "reply",
    [
        _Reply(broken_json=True),
        _Reply({
            "choices": [{"message": {"content": "hi"}}],
            "usage": {"prompt_tokens": "lots", "completion_tokens": 1},
        }),
        _Reply({
            "choices": [{"message": {"content": ["not", "text"]}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }),
    ],
    ids=["not-json", "non-numeric-usage", "non-text-content"],
)
def test_a_malformed_ok_reply_is_an_error_and_is_refunded(app, client, caller, monkeypatch, reply):
    monkeypatch.setattr("app.openai_client.requests.post", lambda *_a, **_k: reply)

    answer = _summarize(client)
    assert answer.status_code == 502
    assert "Nothing was used" in answer.get_json()["message"]
    assert client.get("/v1/quota", headers=_HEADERS).get_json()["monthly_requests_used"] == 0


def test_reduced_quota_actually_reduces_the_monthly_allowance(app, client, caller, db, monkeypatch):
    """The console offered "Reduced quota" and nothing read it: a reduced
    person kept the full hundred."""
    _answer(monkeypatch)
    caller.created_at = datetime.now(UTC) - timedelta(days=30)  # past the starter allowance
    caller.status = "reduced"
    row = db.session.get(GatewayConfig, "reduced_monthly_request_cap")
    if row is None:
        db.session.add(GatewayConfig(key="reduced_monthly_request_cap", value=2, description="x"))
    else:
        row.value = 2
    db.session.commit()

    assert _summarize(client).status_code == 200
    assert _summarize(client).status_code == 200
    refused = _summarize(client)
    assert refused.status_code == 429
    assert refused.get_json()["scope"] == "monthly"


def test_an_admins_own_number_still_beats_reduced(app, caller, db):
    from app.limits import _effective_user_cap

    caller.created_at = datetime.now(UTC) - timedelta(days=30)
    caller.status = "reduced"
    caller.monthly_request_cap = 70
    db.session.commit()
    assert _effective_user_cap(app, caller) == 70


def test_the_switches_page_counts_its_own_features(app, client, db):
    from app.prompts import OPT_IN_FEATURES, SHIPPED_FEATURES
    from tests.test_dashboard_pages import _admin_session_client

    seed_default_model(db.session)
    seed_config_rows(db.session)
    seed_feature_flags(db.session)
    c, _user, _device = _admin_session_client(app, client)
    html = c.get("/dashboard/feature-flags").get_data(as_text=True)
    assert "The five features" not in html
    assert f"The {len(SHIPPED_FEATURES) + len(OPT_IN_FEATURES)} features" in html


def test_the_limits_page_states_the_tolerated_overshoot(app, client, db):
    from tests.test_dashboard_pages import _admin_session_client

    seed_default_model(db.session)
    seed_config_rows(db.session)
    seed_feature_flags(db.session)
    c, _user, _device = _admin_session_client(app, client)
    html = c.get("/dashboard/config").get_data(as_text=True)
    assert "not exact" in html
    assert "in flight" in html
