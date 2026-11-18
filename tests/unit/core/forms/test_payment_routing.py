"""Square, named payment connections, and choosing between them by rule.

complete.md Part 3 (Payments): Square as a third provider, more than one
connection per provider, chosen by the payer or by rule, with Check This Form
finding rules that can never fire and forms with nowhere to send a payment.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.forms import model as M
from quill.core.forms import payment_routing as R
from quill.core.forms import payment_site as ps
from quill.core.forms import payments as P
from quill.core.forms.bfl_read import read
from quill.core.forms.bfl_write import to_bfl


def form(block: dict[str, Any], *, amount: Any = "donation", extra: list[Any] | None = None):
    model = M.create("Paid")
    items = model["pages"][0]["items"]
    items.extend(extra or [])
    items.append({"id": "pay", "type": "payment", "label": "Pay", "props": {"amount": amount}})
    model["extensions"] = {
        "payments": {"currency": "usd", "mode": "payment", "test_mode": True, **block}
    }
    return model


def messages(model) -> list[str]:
    return [e["message"] for e in P.semantic_errors(model)]


FUND = {
    "id": "fund",
    "type": "radio",
    "label": "Fund",
    "choices": [
        {"value": "building", "label": "Building"},
        {"value": "general", "label": "General"},
    ],
}


# -- Square ---------------------------------------------------------------------------


def test_square_is_a_provider_with_its_own_currency_and_descriptor_limits() -> None:
    assert "square" in P.PAYMENT_PROVIDERS
    assert messages(form({"providers": ["square"]})) == []
    said = messages(form({"providers": ["square"], "currency": "mxn"}))
    assert any("Square does not take mxn" in m for m in said)
    said = messages(
        form({"providers": ["square"], "statement_descriptor": "Spring Gala Tickets 1"})
    )
    assert any("at most 20" in m for m in said)
    # Stripe alone keeps its own 22-character ceiling.
    assert (
        messages(form({"providers": ["stripe"], "statement_descriptor": "Spring Gala Tickets 1"}))
        == []
    )


def test_a_square_connection_brings_square_limits_with_it() -> None:
    said = messages(form({"connections": ["stripe", "square:downtown"], "currency": "mxn"}))
    assert any("Square does not take mxn" in m for m in said)


# -- connections, by selection ---------------------------------------------------------


def test_connections_by_selection_need_real_unique_references() -> None:
    assert messages(form({"connections": ["stripe:events", "paypal", "square:downtown"]})) == []
    said = messages(form({"connections": ["stripe:events", "stripe:events", "venmo"]}))
    assert any("listed twice" in m for m in said)
    assert any('"venmo" is not a connection' in m for m in said)
    assert P.effective_providers({"connections": ["square:a", "stripe:b", "square:c"]}) == [
        "square",
        "stripe",
    ]


def test_a_form_chooses_by_selection_or_by_rule_never_both() -> None:
    said = messages(form({"connections": ["stripe"], "rules": [], "otherwise": "paypal"}))
    assert any("not both" in m for m in said)


# -- rules -------------------------------------------------------------------------------


def test_rules_always_need_an_otherwise_so_a_payment_has_somewhere_to_go() -> None:
    rules = [{"when": {"amount_over": "500"}, "use": "stripe:large-gifts"}]
    assert any("need an otherwise" in m for m in messages(form({"rules": rules})))
    assert messages(form({"rules": rules, "otherwise": "stripe:events"})) == []


@pytest.mark.parametrize(
    ("rules", "extra", "amount", "reason"),
    [
        (
            [{"when": {"amount_over": "100"}, "use": "stripe"},
             {"when": {"amount_over": "500"}, "use": "square"}],
            [], "donation", "earlier amount over 100",
        ),
        (
            [{"when": {"field": "fund", "equals": "roof"}, "use": "square"}],
            [FUND], "donation", 'no choice "roof"',
        ),
        (
            [{"when": {"field": "nowhere", "equals": "x"}, "use": "square"}],
            [], "donation", "not in this form",
        ),
        ([{"when": {"currency": "cad"}, "use": "square"}], [], "donation", "takes usd only"),
        (
            [{"when": {"from": "2026-12-31", "until": "2026-12-01"}, "use": "square"}],
            [], "donation", "ends before it starts",
        ),
        ([{"when": {"amount_over": "500"}, "use": "square"}], [], 25, "always 25"),
        (
            [{"when": {"currency": "usd"}, "use": "square"},
             {"when": {"currency": "usd"}, "use": "stripe"}],
            [], "donation", "same condition",
        ),
    ],
)  # fmt: skip
def test_check_this_form_finds_rules_that_can_never_fire(rules, extra, amount, reason) -> None:
    said = messages(form({"rules": rules, "otherwise": "paypal"}, amount=amount, extra=extra))
    assert any("can never take a payment" in m and reason in m for m in said), said


def test_a_choice_rule_may_name_the_value_or_what_the_payer_reads() -> None:
    for equals in ("building", "Building"):
        rules = [{"when": {"field": "fund", "equals": equals}, "use": "square:building"}]
        assert messages(form({"rules": rules, "otherwise": "stripe"}, extra=[FUND])) == []


def test_plain_rule_lines_read_and_write_back() -> None:
    text = (
        "amount over 500: stripe:large-gifts\n"
        "#fund is building: square:building\n"
        "currency is usd: paypal\n"
        "from 2026-12-01 until 2026-12-31: stripe:campaign\n"
        "until 2027-01-15: stripe:late\n"
        "\n"
        "otherwise: stripe:events"
    )
    rules, otherwise, problems = R.parse_rules(text)
    assert problems == []
    assert otherwise == "stripe:events"
    assert rules[0] == {"when": {"amount_over": "500"}, "use": "stripe:large-gifts"}
    assert rules[1] == {"when": {"field": "fund", "equals": "building"}, "use": "square:building"}
    assert rules[3]["when"] == {"from": "2026-12-01", "until": "2026-12-31"}
    assert rules[4]["when"] == {"until": "2027-01-15"}
    again = R.format_rules({"rules": rules, "otherwise": otherwise})
    assert again == text.replace("\n\n", "\n")


def test_a_line_that_does_not_read_is_named_never_guessed() -> None:
    _rules, _other, problems = R.parse_rules(
        "amount about 5: stripe\nstripe\notherwise: a\notherwise: b"
    )
    assert problems[0].startswith('Line 1: "amount about 5"')
    assert problems[1].startswith("Line 2 needs a condition")
    assert problems[2].startswith("Line 4 is a second otherwise")


def test_where_the_money_goes_is_said_in_sentences() -> None:
    rules = [{"when": {"amount_over": "500"}, "use": "stripe:large-gifts"}]
    assert R.describe_routing({"rules": rules, "otherwise": "stripe:events"}) == [
        "When amount over 500, stripe:large-gifts takes the payment.",
        "Otherwise, stripe:events takes it.",
    ]
    assert R.describe_routing({"connections": ["stripe:events", "paypal"]}) == [
        "The payer chooses: stripe:events, paypal; stripe:events is the default."
    ]


def test_connections_and_rules_round_trip_through_bfl() -> None:
    model = form({
        "rules": [{"when": {"field": "fund", "equals": "building"}, "use": "square:building"}],
        "otherwise": "stripe",
    }, extra=[FUND])  # fmt: skip
    text = to_bfl(model)
    assert read(text).model["extensions"] == model["extensions"]
    assert to_bfl(read(text).model) == text


# -- the site, contract version 2 ----------------------------------------------------------


class Api:
    _quill_forms_namespace = "qaf/v1"

    def __init__(self, response):
        self.response = response

    def get(self, _route):
        return self.response


def site(*connections: dict[str, Any], version: int = 2) -> Api:
    return Api({
        "contract_version": version,
        "test_mode": True,
        "providers": {"stripe": {"configured": True, "webhook_ready": True}},
        "connections": list(connections),
    })


def conn(ref: str, **changes: Any) -> dict[str, Any]:
    return {"id": ref, "name": ref.title(), "test_mode": True, "configured": True,
            "webhook_ready": True, "secret_key": "sk_never_kept", **changes}  # fmt: skip


def test_settings_keep_each_connections_public_facts_and_drop_the_rest() -> None:
    state = ps.settings(site(conn("stripe:events"), {"id": "bad ref"}))
    assert state["connections"] == [{
        "id": "stripe:events", "name": "Stripe:Events", "provider": "stripe",
        "test_mode": True, "configured": True, "webhook_ready": True,
    }]  # fmt: skip


def test_publishing_checks_every_connection_a_form_can_reach() -> None:
    model = form({"rules": [{"when": {"amount_over": "500"}, "use": "stripe:large"}],
                  "otherwise": "square:downtown"})  # fmt: skip
    ps.require_ready(site(conn("stripe:large"), conn("square:downtown")), model)
    with pytest.raises(ps.PaymentSiteError, match="no payment connection called square:downtown"):
        ps.require_ready(site(conn("stripe:large")), model)
    with pytest.raises(ps.PaymentSiteError, match="never mixes test and live"):
        ps.require_ready(
            site(conn("stripe:large"), conn("square:downtown", test_mode=False)), model
        )
    with pytest.raises(ps.PaymentSiteError, match="Finish Square:Downtown"):
        ps.require_ready(
            site(conn("stripe:large"), conn("square:downtown", webhook_ready=False)), model
        )
    with pytest.raises(ps.PaymentSiteError, match="choose between payment connections"):
        ps.require_ready(site(version=1), model)


def test_a_square_form_needs_a_plugin_that_takes_square() -> None:
    with pytest.raises(ps.PaymentSiteError, match="take Square payments"):
        ps.require_ready(site(version=1), form({"providers": ["square"]}))


def test_the_sites_payments_page_lists_connections_and_never_a_key() -> None:
    text = ps.site_payments_text(
        site(conn("stripe:events"), conn("square:downtown", webhook_ready=False))
    )
    assert "Stripe:Events (stripe:events, test): works." in text
    assert "Square:Downtown (square:downtown, test): not finished" in text
    assert "sk_never_kept" not in text
    older = ps.site_payments_text(site(version=1))
    assert "Stripe (stripe, test): works." in older


def test_an_entry_says_which_connection_took_the_money() -> None:
    from quill.core.forms import qaf_site as qs
    from quill.core.forms import responses as rs

    entry = qs.response_from_payload({
        "id": 7,
        "payment": {"provider": "square", "status": "paid", "amount": "40.00", "currency": "USD",
                    "connection": "square:building", "connection_name": "Square: Building fund",
                    "access_token": "never kept"},
    })  # fmt: skip
    assert entry.payment["connection"] == "square:building"
    assert "access_token" not in entry.payment
    assert rs.spoken_payment(entry.payment)["provider"] == "Square: Building fund"
    header = rs.csv_text([entry], {}).splitlines()[0]
    assert header.endswith("Payment connection,Payment connection name")
