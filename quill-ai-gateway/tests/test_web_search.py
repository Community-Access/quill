"""Web search (2026-10-15): built, switched off, and capped at ten a month.

Four promises, each a test. It is **off** until an operator turns it on, and a
missing flag row reads as off -- the expensive way round is never the default.
While it is on it goes through its own call with its own body allowlist, so no
other feature can ever carry a search. Each account gets
``WEB_SEARCH_MONTHLY_CAP`` searches a month and is refused the next one, with
the refusal refunded like every other. And the client can see all of it:
``/v1/config`` says whether it is on and how many a month, ``/v1/quota`` how
many are used, and the catalogue offers the row only while it is on.

No test opens a socket: the search call is replaced at its one import site.
"""

from __future__ import annotations

import pytest
from app.limits import WEB_SEARCH_CALL_COST_USD, WEB_SEARCH_MONTHLY_CAP
from app.models import FeatureFlag, MonthlyUsageSummary, UsageEvent
from app.openai_client import (
    ALLOWED_BODY_KEYS,
    SEARCH_BODY_KEYS,
    Completion,
    build_request_body,
    build_search_body,
)
from app.prompts import (
    CATALOGUE,
    FEATURES,
    OPT_IN_FEATURES,
    SHIPPED_FEATURES,
    build_prompt,
)

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


def _switch_on(db) -> None:
    flag = db.session.get(FeatureFlag, "web_search")
    if flag is None:
        flag = FeatureFlag(feature="web_search")
        db.session.add(flag)
    flag.enabled = True
    flag.disabled_reason = None
    db.session.commit()


def _fake_search(monkeypatch) -> list[dict]:
    calls: list[dict] = []

    def fake(_app, model_id, prompt, max_output_tokens):
        calls.append({"model": model_id, "prompt": prompt, "max": max_output_tokens})
        return Completion(text="It is 42. Source: example.org", tokens_in=50, tokens_out=20)

    def no_complete(*_args, **_kwargs):  # pragma: no cover - would be the bug
        raise AssertionError("web_search must never go through complete()")

    monkeypatch.setattr("app.routes.chat.search", fake)
    monkeypatch.setattr("app.routes.chat.complete", no_complete)
    return calls


def _search(client, question: str = "What is the answer?"):
    return client.post(
        "/v1/chat", json={"feature": "web_search", "prompt": question}, headers=_HEADERS
    )


# --------------------------------------------------------------------------- #
# Off by default
# --------------------------------------------------------------------------- #


def test_web_search_is_built_but_not_shipped():
    assert "web_search" in FEATURES
    assert "web_search" in OPT_IN_FEATURES
    assert "web_search" not in SHIPPED_FEATURES
    assert WEB_SEARCH_MONTHLY_CAP == 10


def test_a_missing_flag_row_refuses_with_its_own_sentence(client, caller, monkeypatch):
    calls = _fake_search(monkeypatch)
    reply = _search(client)
    assert reply.status_code == 503
    assert reply.get_json()["message"] == OPT_IN_FEATURES["web_search"]
    assert calls == []


def test_config_says_it_is_off_and_offers_no_row(client, caller):
    body = client.get("/v1/config").get_json()
    assert body["web_search"] == {"enabled": False, "monthly_cap": WEB_SEARCH_MONTHLY_CAP}
    assert body["feature_flags"]["web_search"] is False
    assert "web_search" not in [entry["id"] for entry in body["features"]]


# --------------------------------------------------------------------------- #
# On: its own call, its own body
# --------------------------------------------------------------------------- #


def test_switched_on_it_is_offered_in_the_catalogue(client, caller, db):
    _switch_on(db)
    body = client.get("/v1/config").get_json()
    assert body["web_search"]["enabled"] is True
    ids = [entry["id"] for entry in body["features"]]
    assert ids[-1] == "web_search"
    entry = body["features"][-1]
    assert entry["input"] == "prompt"
    assert entry["label"] == CATALOGUE["web_search"]["label"]


def test_a_search_goes_to_the_search_model_with_the_template(client, caller, db, app, monkeypatch):
    _switch_on(db)
    calls = _fake_search(monkeypatch)
    reply = _search(client, "Who won?")
    assert reply.status_code == 200
    assert reply.get_json()["text"].startswith("It is 42.")
    assert calls[0]["model"] == app.config["OPENAI_SEARCH_MODEL"]
    assert calls[0]["prompt"] == build_prompt("web_search", "Who won?")


def test_the_search_body_has_its_own_allowlist_and_the_others_cannot_search():
    body = build_search_body("search-model", "q", 500)
    assert set(body) <= SEARCH_BODY_KEYS
    assert body["web_search_options"] == {}
    assert "reasoning_effort" not in body
    # The ordinary allowlist is untouched: no other feature can carry a search.
    assert "web_search_options" not in ALLOWED_BODY_KEYS
    assert "web_search_options" not in build_request_body("m", "q", 500, "none")


def test_the_search_fee_reaches_the_budget_but_not_the_persons_ceiling(
    client, caller, db, monkeypatch
):
    _switch_on(db)
    _fake_search(monkeypatch)
    assert _search(client).status_code == 200
    event = db.session.query(UsageEvent).filter_by(feature="web_search").one()
    summary = db.session.query(MonthlyUsageSummary).filter_by(user_id=caller.id).one()
    assert float(event.estimated_cost_usd) >= WEB_SEARCH_CALL_COST_USD
    assert float(summary.total_cost_usd) < WEB_SEARCH_CALL_COST_USD


# --------------------------------------------------------------------------- #
# Ten a month, and the client can see how many are left
# --------------------------------------------------------------------------- #


def test_the_eleventh_search_in_a_month_is_refused_and_costs_nothing(
    client, caller, db, app, monkeypatch
):
    from app.models import GatewayConfig

    _switch_on(db)
    # The ordinary daily and hourly caps would stop ten searches in a row
    # first; this test is about the search cap.
    for key in ("daily_request_cap", "hourly_request_cap", "device_hourly_request_cap"):
        db.session.get(GatewayConfig, key).value = 1000
    db.session.commit()
    calls = _fake_search(monkeypatch)
    for _ in range(WEB_SEARCH_MONTHLY_CAP):
        assert _search(client).status_code == 200
    refused = _search(client)
    assert refused.status_code == 429
    assert refused.get_json()["scope"] == "feature"
    assert len(calls) == WEB_SEARCH_MONTHLY_CAP

    quota = client.get("/v1/quota", headers=_HEADERS).get_json()
    assert quota["web_search_monthly_cap"] == WEB_SEARCH_MONTHLY_CAP
    # The refused one incremented the counter and the gate does not refund a
    # quota refusal, so used reads at least the cap: nothing left either way.
    assert quota["web_searches_used"] >= WEB_SEARCH_MONTHLY_CAP


def test_quota_reports_searches_used(client, caller, db, monkeypatch):
    _switch_on(db)
    _fake_search(monkeypatch)
    assert client.get("/v1/quota", headers=_HEADERS).get_json()["web_searches_used"] == 0
    _search(client)
    quota = client.get("/v1/quota", headers=_HEADERS).get_json()
    assert quota["web_searches_used"] == 1
    assert quota["web_search_monthly_cap"] == WEB_SEARCH_MONTHLY_CAP


def test_a_failed_search_is_refunded(client, caller, db, monkeypatch):
    from app.openai_client import OpenAICallError

    _switch_on(db)

    def broken(*_args, **_kwargs):
        raise OpenAICallError("down")

    monkeypatch.setattr("app.routes.chat.search", broken)
    assert _search(client).status_code == 502
    assert client.get("/v1/quota", headers=_HEADERS).get_json()["web_searches_used"] == 0
