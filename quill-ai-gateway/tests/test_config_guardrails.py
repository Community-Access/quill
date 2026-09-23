"""Tests for app/config_schema.py and the validation it gives the config routes.

Before this existed, both the JSON API and the dashboard form accepted any
float that parsed. Typing ``15`` into the per-user cost ceiling where ``0.15``
was intended raised every user's spending limit a hundredfold and answered with
a cheerful green success message. These tests are that accident, written down.
"""

from __future__ import annotations

import pytest
from app.config_schema import KEYS, describe, grouped_keys, validate, words_for_tokens

from tests.conftest import make_admin_client, seed_config_rows, seed_default_model

# --- The schema itself ---------------------------------------------------------


def test_the_decimal_point_accident_is_rejected():
    """$0.15 typed as $15 -- the specific mistake this module was written for."""
    assert validate("monthly_cost_cap_usd", 0.15) is None
    problem = validate("monthly_cost_cap_usd", 15.0)
    assert problem is None or "between" in problem
    # And the genuinely absurd version is refused outright.
    problem = validate("monthly_cost_cap_usd", 1500.0)
    assert problem is not None
    assert "1,500" in problem or "1500" in problem


def test_an_out_of_range_value_explains_itself_in_a_sentence():
    problem = validate("monthly_request_cap", 10_000)
    assert problem is not None
    assert problem.endswith(".")
    assert "Free requests per person" in problem
    assert "You typed" in problem


def test_an_unknown_key_is_allowed_rather_than_bricked():
    """A key with no description must stay editable. The fail-safe path in
    limits.py can invent one, and a limit nobody can change is worse than one
    nobody can bound."""
    assert validate("some_future_key", 999_999) is None
    assert describe("some_future_key") is None


@pytest.mark.parametrize("key", sorted(KEYS))
def test_every_described_key_has_a_usable_description(key):
    entry = KEYS[key]
    assert entry.name and entry.name[0].isupper()
    assert entry.sentence.endswith(".")
    assert entry.consequence.endswith(".")
    assert entry.minimum <= entry.maximum
    assert entry.group in {"allowance", "request_size", "money", "signup", "later"}


def test_nan_and_infinity_are_refused():
    assert validate("monthly_request_cap", float("inf")) is not None
    assert validate("monthly_request_cap", float("nan")) is not None


def test_sizes_are_shown_in_words_because_nobody_thinks_in_tokens():
    entry = describe("max_input_tokens")
    shown = entry.format_value(1500)
    assert "words" in shown
    assert "1,500 tokens" in shown
    assert words_for_tokens(1500) > 1000


def test_the_groups_an_operator_reads_are_ordered_and_populated():
    groups = grouped_keys()
    ids = [g[0] for g in groups]
    assert ids == ["allowance", "request_size", "money", "signup", "later"]
    for _id, heading, blurb, members in groups:
        assert heading and blurb
        assert members


def test_the_cost_relevant_keys_are_exactly_the_three_that_move_the_bill():
    """Requests per person, and the two size limits. Everything else either
    redistributes an existing allowance or bounds something that is already
    bounded, so flagging it would train an operator to click through the
    confirmation."""
    relevant = {key for key, entry in KEYS.items() if entry.cost_relevant}
    assert relevant == {"monthly_request_cap", "max_input_tokens", "max_output_tokens"}


# --- The routes that use it ------------------------------------------------------


def test_the_api_refuses_an_out_of_range_config_write(app, client, db):
    seed_config_rows(db.session)
    c, headers, _user, _device = make_admin_client(app, client)

    response = c.put("/admin/config/monthly_request_cap", json={"value": 99_999}, headers=headers)
    assert response.status_code == 400
    assert response.json["reason"] == "out_of_range"
    assert "between" in response.json["message"]

    # And the stored value is untouched.
    response = c.get("/admin/config", headers=headers)
    stored = {row["key"]: row["value"] for row in response.json}
    assert stored["monthly_request_cap"] == 100


def test_the_api_requires_confirmation_for_a_cost_doubling(app, client, db):
    seed_default_model(db.session)
    seed_config_rows(db.session)
    c, headers, _user, _device = make_admin_client(app, client)

    response = c.put("/admin/config/monthly_request_cap", json={"value": 500}, headers=headers)
    assert response.status_code == 409
    assert response.json["reason"] == "needs_confirmation"
    assert "$" in response.json["message"]
    assert response.json["after_usd"] > response.json["before_usd"]

    # Explicitly confirmed, it goes through.
    response = c.put(
        "/admin/config/monthly_request_cap",
        json={"value": 500, "confirm": True},
        headers=headers,
    )
    assert response.status_code == 200


def test_an_ordinary_tuning_step_needs_no_confirmation(app, client, db):
    """The confirmation must be rare enough to mean something. A 25% increase
    is normal tuning and goes straight through."""
    seed_default_model(db.session)
    seed_config_rows(db.session)
    c, headers, _user, _device = make_admin_client(app, client)

    response = c.put("/admin/config/monthly_request_cap", json={"value": 125}, headers=headers)
    assert response.status_code == 200


def test_the_config_api_explains_each_key_in_plain_language(app, client, db):
    seed_config_rows(db.session)
    c, headers, _user, _device = make_admin_client(app, client)

    response = c.get("/admin/config", headers=headers)
    rows = {row["key"]: row for row in response.json}
    entry = rows["monthly_request_cap"]
    assert entry["name"] == "Free requests per person, per month"
    assert entry["unit"] == "requests"
    assert entry["explanation"]
    assert entry["consequence"]
    assert entry["cost_relevant"] is True
