"""Nobody is charged for a request that did not happen.

The rate-limit counters are incremented by the gate *before* the size check,
before a model is resolved and before anything is sent. That ordering is
deliberate -- a limiter that reads before it writes can be raced past its own
cap -- and it means every failure path after the gate has already taken one of
the user's hundred requests.

They cannot see the counter move, so they have no way to notice and no way to
argue. Every message on those paths now says "nothing was used", and these
tests are what make that sentence true rather than merely reassuring.
"""

from __future__ import annotations

import pytest
from app.openai_client import Completion, OpenAICallError

from tests.conftest import (
    make_user_and_device,
    seed_config_rows,
    seed_default_model,
    seed_feature_flags,
)


@pytest.fixture()
def caller(app, db):
    seed_default_model(db.session)
    seed_config_rows(db.session)
    seed_feature_flags(db.session)
    user, device = make_user_and_device(db.session, token="user-token")
    return user, device, {"Authorization": "Bearer user-token"}


def _monthly_used(app, user):
    from app.limits import remaining_quota

    return remaining_quota(app, user).monthly_used


def test_a_successful_request_does_spend_one(app, client, caller, monkeypatch):
    user, _device, headers = caller
    monkeypatch.setattr(
        "app.routes.chat.complete",
        lambda *a, **k: Completion(text="a summary", tokens_in=100, tokens_out=20),
    )
    response = client.post(
        "/v1/chat", json={"feature": "summarize", "prompt": "some text"}, headers=headers
    )
    assert response.status_code == 200
    assert _monthly_used(app, user) == 1


def test_an_oversized_passage_costs_nothing(app, client, caller):
    """Refused before anything is sent, so it costs no money -- and now costs
    no allowance either."""
    user, _device, headers = caller
    huge = "word " * 20_000
    response = client.post(
        "/v1/chat", json={"feature": "summarize", "prompt": huge}, headers=headers
    )
    assert response.status_code == 422
    assert "Nothing was sent and nothing was used." in response.json["message"]
    assert _monthly_used(app, user) == 0


def test_too_many_excerpts_costs_nothing(app, client, caller):
    user, _device, headers = caller
    response = client.post(
        "/v1/chat",
        json={"feature": "document_qna", "prompt": "what?", "chunks": ["a", "b", "c", "d", "e"]},
        headers=headers,
    )
    assert response.status_code == 422
    assert _monthly_used(app, user) == 0


def test_an_upstream_outage_costs_nothing(app, client, caller, monkeypatch):
    """A provider having a bad afternoon must not quietly eat people's
    allowances -- they would come back tomorrow to find them gone."""
    user, _device, headers = caller

    def boom(*_args, **_kwargs):
        raise OpenAICallError("upstream exploded")

    monkeypatch.setattr("app.routes.chat.complete", boom)
    response = client.post(
        "/v1/chat", json={"feature": "summarize", "prompt": "some text"}, headers=headers
    )
    assert response.status_code == 502
    assert "Nothing was used." in response.json["message"]
    assert _monthly_used(app, user) == 0


def test_no_default_model_costs_nothing(app, client, caller, db):
    from app.models import GatewayModel

    user, _device, headers = caller
    db.session.query(GatewayModel).delete()
    db.session.commit()

    response = client.post(
        "/v1/chat", json={"feature": "summarize", "prompt": "some text"}, headers=headers
    )
    assert response.status_code == 503
    assert _monthly_used(app, user) == 0


def test_an_empty_answer_costs_the_user_nothing(app, client, caller, monkeypatch):
    """The worst of the lot: the model spent the whole output budget thinking
    and returned nothing. The user experiences that as a broken feature; being
    charged for it as well is what makes them stop using it rather than report
    it."""
    user, _device, headers = caller
    monkeypatch.setattr(
        "app.routes.chat.complete",
        lambda *a, **k: Completion(text="", tokens_in=100, tokens_out=500, reasoning_tokens=500),
    )
    response = client.post(
        "/v1/chat", json={"feature": "summarize", "prompt": "some text"}, headers=headers
    )
    assert response.status_code == 502
    assert "Nothing was used." in response.json["message"]
    assert _monthly_used(app, user) == 0


def test_an_empty_answer_is_still_recorded_as_real_money(app, client, caller, monkeypatch, db):
    """The provider billed *us* for those reasoning tokens even though the user
    got nothing, so the global budget has to see them. Only the user's own
    counters are given back."""
    from app.models import UsageEvent

    _user, _device, headers = caller
    monkeypatch.setattr(
        "app.routes.chat.complete",
        lambda *a, **k: Completion(text="", tokens_in=100, tokens_out=500, reasoning_tokens=500),
    )
    client.post("/v1/chat", json={"feature": "summarize", "prompt": "text"}, headers=headers)

    event = db.session.query(UsageEvent).one()
    assert event.status == "throttled"
    assert event.reasoning_tokens == 500
    assert float(event.estimated_cost_usd) > 0


def test_reasoning_tokens_are_recorded_on_a_normal_request(app, client, caller, monkeypatch, db):
    from app.models import UsageEvent

    _user, _device, headers = caller
    monkeypatch.setattr(
        "app.routes.chat.complete",
        lambda *a, **k: Completion(
            text="an answer", tokens_in=100, tokens_out=80, reasoning_tokens=30
        ),
    )
    client.post(
        "/v1/chat",
        json={"feature": "document_qna", "prompt": "q", "chunks": ["excerpt"]},
        headers=headers,
    )
    event = db.session.query(UsageEvent).one()
    assert event.reasoning_tokens == 30


def test_a_refund_never_drives_a_counter_negative(app, caller):
    """A counter below zero would hand out free requests -- the exact failure
    the whole module exists to prevent. Refunding twice is harmless."""
    from app.limits import refund_request, remaining_quota

    user, device, _headers = caller
    with app.app_context():
        refund_request(app, user, device, "summarize")
        refund_request(app, user, device, "summarize")
        quota = remaining_quota(app, user)
    assert quota.monthly_used >= 0
    assert quota.daily_used >= 0


def test_a_deferred_feature_says_it_was_never_built(app, client, caller):
    """Not "temporarily paused while we review unusual activity", which would
    send somebody to support over a feature that does not exist."""
    _user, _device, headers = caller
    response = client.post(
        "/v1/chat", json={"feature": "alt_text", "prompt": "a picture"}, headers=headers
    )
    assert response.status_code == 503
    assert "not a shipped feature" in response.json["message"]
