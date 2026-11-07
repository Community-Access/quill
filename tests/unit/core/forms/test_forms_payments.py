"""Payments in a form: the config block, its rules, and byte-stable BFL.

The configuration lives in ``extensions["payments"]`` and a payment field's
options in its ``props``, so a paid form needs no new BFL syntax: these tests
pin that a paid form reads, validates, writes canonically and round-trips
byte for byte, and that :func:`payments.semantic_errors` catches each way a
paid form can be wrong, at the path a builder can jump to.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.forms import model as M
from quill.core.forms import payments as P
from quill.core.forms.bfl_document import read_bfl, write_bfl
from quill.core.forms.bfl_read import read
from quill.core.forms.bfl_write import to_bfl

PAID_FORM = """bfl 1
form "Fundraiser"
  @extensions {"payments":{"providers":["stripe","paypal"],"currency":"usd",\
"mode":"donation","capture":"automatic","test_mode":true}}

payment #gift "Your gift"
  @amount "donation"
  @donation_min 5
  @donation_max 500
"""

ORDER_FORM = """bfl 1
form "Order"
  @extensions {"payments":{"providers":["stripe"],"currency":"usd",\
"mode":"payment","capture":"automatic","test_mode":true}}

product #shirt "T-shirt"
  + Small:10
  + Large:12

quantity #how_many "How many?"
  @min 1
  @max 10

total #order_total "Order total"

payment #pay "Payment"
  @amount "#order_total"
"""


def paid_model(**config: Any) -> M.Model:
    model = M.create("Paid")
    model["pages"][0]["items"].append({
        "id": "pay",
        "type": "payment",
        "label": "Payment",
        "props": {"amount": 25},
    })
    P.set_payment_config(model, P.PaymentConfig(**config))
    return model


def paths(model: M.Model) -> list[str]:
    return [e["path"] for e in P.semantic_errors(model)]


# -- the config block --------------------------------------------------------------------


def test_config_round_trips_through_the_model() -> None:
    model = M.create("T")
    config = P.PaymentConfig(
        providers=("stripe", "paypal"),
        currency="eur",
        mode="donation",
        capture="manual",
        statement_descriptor="QUILL FORMS",
        test_mode=False,
    )
    P.set_payment_config(model, config)
    assert P.payment_config(model) == config
    assert model["extensions"][P.EXTENSION_KEY]["providers"] == ["stripe", "paypal"]
    P.clear_payment_config(model)
    assert P.payment_config(model) is None
    assert "extensions" not in model


def test_clear_keeps_another_programs_extensions() -> None:
    model = M.create("T")
    model["extensions"] = {"other": {"kept": True}}
    P.set_payment_config(model, P.PaymentConfig())
    P.clear_payment_config(model)
    assert model["extensions"] == {"other": {"kept": True}}


def test_from_dict_never_fails_and_defaults_sanely() -> None:
    assert P.PaymentConfig.from_dict(None) == P.PaymentConfig()
    assert P.PaymentConfig.from_dict({"providers": ["bitcoin"]}).providers == ("stripe",)
    read_back = P.PaymentConfig.from_dict({
        "providers": ["paypal", "stripe"],
        "currency": "gbp",
        "test_mode": False,
    })
    assert read_back.providers == ("paypal", "stripe")
    assert read_back.currency == "gbp"
    assert read_back.test_mode is False
    assert read_back.mode == "payment"


def test_defaults_favor_stripe_and_start_in_test_mode() -> None:
    config = P.PaymentConfig()
    assert config.providers == ("stripe",)
    assert config.test_mode is True
    assert config.to_dict() == {
        "providers": ["stripe"],
        "currency": "usd",
        "mode": "payment",
        "capture": "automatic",
        "test_mode": True,
    }
    assert "statement_descriptor" not in config.to_dict()


# -- the rules ---------------------------------------------------------------------------


def test_a_valid_paid_form_has_no_errors_and_passes_the_schema() -> None:
    model = paid_model()
    assert P.semantic_errors(model) == []
    assert M.validate(model) == []


def test_model_semantic_errors_carries_the_payment_rules() -> None:
    model = paid_model()
    del model["extensions"]
    assert any("/extensions/payments" == e["path"] for e in M.semantic_errors(model))
    assert any("/extensions/payments" == e["path"] for e in M.validate(model))


def test_a_payment_field_needs_a_providers_list() -> None:
    model = paid_model()
    P.clear_payment_config(model)
    assert paths(model) == ["/extensions/payments"]


def test_only_one_payment_field_per_form() -> None:
    model = paid_model()
    model["pages"][0]["items"].append({
        "id": "pay2",
        "type": "payment",
        "label": "Again",
        "props": {"amount": 1},
    })
    assert "/pages/0/items/1" in paths(model)


@pytest.mark.parametrize(
    ("block", "where"),
    [
        ({"providers": []}, "/extensions/payments/providers"),
        ({"providers": "stripe"}, "/extensions/payments/providers"),
        ({"providers": ["venmo"]}, "/extensions/payments/providers/0"),
        ({"providers": ["stripe", "stripe"]}, "/extensions/payments/providers/1"),
        ({"providers": ["stripe"], "currency": "zzz"}, "/extensions/payments/currency"),
        ({"providers": ["stripe"], "currency": 7}, "/extensions/payments/currency"),
        ({"providers": ["stripe"], "mode": "subscription"}, "/extensions/payments/mode"),
        ({"providers": ["stripe"], "capture": "later"}, "/extensions/payments/capture"),
        ({"providers": ["stripe"], "test_mode": "yes"}, "/extensions/payments/test_mode"),
        (
            {"providers": ["stripe"], "statement_descriptor": "X" * 23},
            "/extensions/payments/statement_descriptor",
        ),
        (
            {"providers": ["stripe"], "statement_descriptor": 'A "quoted" one'},
            "/extensions/payments/statement_descriptor",
        ),
    ],
)
def test_each_way_the_block_can_be_wrong(block: dict[str, Any], where: str) -> None:
    model = paid_model()
    model["extensions"][P.EXTENSION_KEY] = block
    assert where in paths(model)


def test_the_block_must_be_an_object() -> None:
    model = paid_model()
    model["extensions"][P.EXTENSION_KEY] = ["stripe"]
    assert "/extensions/payments" in paths(model)


def test_unknown_block_keys_are_kept_for_the_plugin() -> None:
    model = paid_model()
    model["extensions"][P.EXTENSION_KEY]["plugin_own_key"] = {"theirs": True}
    assert P.semantic_errors(model) == []


@pytest.mark.parametrize(
    ("props", "where"),
    [
        ({}, "/props/amount"),
        ({"amount": 0}, "/props/amount"),
        ({"amount": -5}, "/props/amount"),
        ({"amount": True}, "/props/amount"),
        ({"amount": "whatever"}, "/props/amount"),
        ({"amount": "#missing"}, "/props/amount"),
        ({"amount": "#name"}, "/props/amount"),
        ({"amount": 10, "donation_min": 5}, "/props/donation_min"),
        ({"amount": "donation", "donation_min": 0}, "/props/donation_min"),
        ({"amount": "donation", "donation_max": "big"}, "/props/donation_max"),
        ({"amount": "donation", "donation_min": 50, "donation_max": 5}, "/props/donation_min"),
    ],
)
def test_each_way_an_amount_can_be_wrong(props: dict[str, Any], where: str) -> None:
    model = paid_model()
    model["pages"][0]["items"][0]["props"] = props
    model["pages"][0]["items"].append({"id": "name", "type": "text", "label": "Name"})
    found = paths(model)
    assert f"/pages/0/items/0{where}" in found


@pytest.mark.parametrize(
    "props",
    [
        {"amount": 25},
        {"amount": 9.5},
        {"amount": "donation"},
        {"amount": "donation", "donation_min": 5, "donation_max": 500},
        {"amount": "#the_total"},
    ],
)
def test_each_way_an_amount_can_be_right(props: dict[str, Any]) -> None:
    model = paid_model()
    model["pages"][0]["items"][0]["props"] = props
    model["pages"][0]["items"].append({"id": "the_total", "type": "total", "label": "Total"})
    assert P.semantic_errors(model) == []


# -- BFL: no new syntax, byte-stable -----------------------------------------------------


@pytest.mark.parametrize("source", [PAID_FORM, ORDER_FORM])
def test_paid_forms_read_cleanly_validate_and_round_trip(source: str) -> None:
    result = read(source)
    assert result.errors == []
    assert result.warnings == []
    assert M.validate(result.model) == []
    canonical = to_bfl(result.model)
    again = read(canonical)
    assert M.same(again.model, result.model)
    assert to_bfl(again.model) == canonical
    doc = read_bfl(source)
    assert write_bfl(doc) == source


def test_the_bfl_modifiers_land_in_props_and_extensions() -> None:
    model = read(PAID_FORM).model
    config = P.payment_config(model)
    assert config is not None
    assert config.providers == ("stripe", "paypal")
    assert config.mode == "donation"
    [entry] = P.payment_fields(model)
    assert entry["item"]["props"] == {"amount": "donation", "donation_min": 5, "donation_max": 500}


def test_the_order_form_charges_its_total() -> None:
    model = read(ORDER_FORM).model
    [entry] = P.payment_fields(model)
    assert entry["item"]["props"]["amount"] == "#order_total"
    assert P.semantic_errors(model) == []
