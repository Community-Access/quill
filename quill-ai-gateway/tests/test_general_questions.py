"""The sixth free feature: one general question, answered on its own.

What keeps it affordable where open-ended chat is not is its shape -- one
question in, one answer out, no history resent on every turn -- and a ceiling on
the answer of its own. These tests hold both halves: the feature is shipped
with no reasoning, and its answer ceiling reaches the provider for ``ask`` and
for nothing else.
"""

from __future__ import annotations

import pytest
from app.costing import CostModel
from app.openai_client import Completion
from app.prompts import (
    DEFERRED_FEATURES,
    REASONING_EFFORT,
    SHIPPED_FEATURES,
    TEMPLATES,
    build_prompt,
)

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
    _user, _device = make_user_and_device(db.session, token="user-token")
    return {"Authorization": "Bearer user-token"}


def _capture(monkeypatch) -> dict:
    seen: dict = {}

    def fake_complete(_app, model_id, prompt, max_output_tokens, effort):
        seen.update(prompt=prompt, max_output_tokens=max_output_tokens, effort=effort)
        return Completion(text="An answer.", tokens_in=40, tokens_out=12)

    monkeypatch.setattr("app.routes.chat.complete", fake_complete)
    return seen


def test_general_questions_are_shipped():
    assert "ask" in SHIPPED_FEATURES
    assert "ask" not in DEFERRED_FEATURES


def test_a_general_question_does_no_reasoning():
    """Reasoning bills as output and never reaches the answer; the question
    is answered, not researched."""
    assert REASONING_EFFORT["ask"] == "none"


def test_the_question_is_the_whole_message():
    built = build_prompt("ask", "What is a semicolon for?")
    assert built.endswith("What is a semicolon for?")
    assert "{prompt}" in TEMPLATES["ask"]


def test_a_general_question_gets_its_own_answer_ceiling(client, caller, monkeypatch):
    seen = _capture(monkeypatch)
    response = client.post(
        "/v1/chat", json={"feature": "ask", "prompt": "What is a semicolon for?"}, headers=caller
    )
    assert response.status_code == 200
    assert response.get_json()["text"] == "An answer."
    assert seen["max_output_tokens"] == 1000
    assert seen["effort"] == "none"


def test_other_features_keep_the_ordinary_ceiling(client, caller, monkeypatch):
    seen = _capture(monkeypatch)
    response = client.post(
        "/v1/chat", json={"feature": "summarize", "prompt": "Some text."}, headers=caller
    )
    assert response.status_code == 200
    assert seen["max_output_tokens"] == 500


def test_the_client_is_told_general_questions_are_on(client, caller):
    flags = client.get("/v1/config").get_json()["feature_flags"]
    assert flags["ask"] is True


def test_the_worst_case_costs_the_longer_answer():
    """A person may spend the whole allowance on general questions, so the
    projection prices every request at the longer of the two ceilings."""
    model = CostModel(
        model_id="m",
        model_label="M",
        input_per_million_usd=0.10,
        output_per_million_usd=0.50,
        max_input_tokens=3000,
        max_output_tokens=500,
        monthly_request_cap=100,
        max_ask_output_tokens=1000,
    )
    assert model.per_request_usd == pytest.approx(0.0008)
    assert model.per_person_month_usd == pytest.approx(0.08)


def test_the_per_person_fence_still_sits_above_the_reachable_worst_case():
    """The whole month at the longer answer -- every request a general
    question, a conversation turn or a long writing tool -- at the seeded
    sizes, must stay under the seeded per-person ceiling, or the fence cuts off
    people who did nothing wrong."""
    from app.limits import SEED_DEFAULTS

    per_input = 3000 / 1_000_000 * 0.10
    per_long_answer = SEED_DEFAULTS["max_ask_output_tokens"] / 1_000_000 * 0.50
    reachable = SEED_DEFAULTS["monthly_request_cap"] * (per_input + per_long_answer)
    assert reachable < SEED_DEFAULTS["monthly_cost_cap_usd"]
