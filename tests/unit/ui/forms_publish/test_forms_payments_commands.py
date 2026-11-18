"""Payment authoring, publication consent and test-mode refusal through real commands."""

from __future__ import annotations

import pytest

from quill.core.forms import model as M
from quill.core.forms import payments as P
from quill.core.forms import published as pub
from quill.ui import forms_doc as fd
from quill.ui.forms_commands import FormsCommands

QAF = "/wp-json/qaf/v1"


@pytest.fixture
def payments(fp, pub_host):
    commands = FormsCommands(pub_host)
    commands._data_dir = fp._data_dir
    commands._opener = fp._opener
    return commands


def setup(monkeypatch, answer):
    from quill.ui import wordpress_block_dialogs as dialogs

    monkeypatch.setattr(dialogs, "ask_fields", lambda *a, **kw: answer)


def add_payment(pub_host, *, test_mode=True):
    model = fd.read(pub_host.text).model
    P.set_payment_config(model, P.PaymentConfig(test_mode=test_mode))
    model["pages"][0]["items"].append({
        "id": "pay",
        "type": "payment",
        "label": "Fee",
        "props": {"amount": 25},
    })
    pub_host.text = fd.canonical(model)
    return model


def test_insert_payment_is_local_valid_and_one_undo(payments, pub_host, pub_site, monkeypatch):
    setup(monkeypatch, {"label": "Fee", "amount": "25"})
    payments.cmd_insert_payment()
    assert not pub_site.requests
    assert pub_host.replaced == 1
    model = fd.read(pub_host.text).model
    assert not M.validate(model)
    assert P.payment_config(model).test_mode
    assert P.payment_fields(model)[0]["item"]["props"]["amount"] == 25
    payments.cmd_insert_payment()
    assert pub_host.replaced == 1
    assert "already" in pub_host.said


@pytest.mark.parametrize("amount", ["0", "-2", "NaN", "inf", "#absent", "oops"])
def test_invalid_amount_never_changes_source(payments, pub_host, monkeypatch, amount):
    setup(monkeypatch, {"amount": amount})
    before = pub_host.text
    payments.cmd_insert_payment()
    assert pub_host.text == before
    assert pub_host.replaced == 0


def test_setup_cancel_and_live_confirmation(payments, pub_host, pub_dialogs, monkeypatch):
    setup(monkeypatch, None)
    payments.cmd_payments_setup()
    assert pub_host.replaced == 0
    setup(monkeypatch, {"pay_with": "paypal", "test_mode": False, "currency": "eur"})
    payments.cmd_payments_setup()
    assert pub_host.replaced == 0
    pub_dialogs.answer("confirm", True)
    payments.cmd_payments_setup()
    config = P.payment_config(fd.read(pub_host.text).model)
    assert not config.test_mode and config.providers == ("paypal",)


def test_verification_cancel_and_safe_mode_send_nothing(payments, pub_host, pub_site, pub_dialogs):
    payments.cmd_verify_payments()
    assert not pub_site.requests
    pub_host.ai._safe_mode = True
    pub_dialogs.answer("confirm", True)
    payments.cmd_verify_payments()
    assert not pub_site.requests
    assert "Safe Mode" in pub_host.said


def test_verify_reports_old_plugin(payments, pub_site, pub_dialogs, pub_host):
    pub_dialogs.answer("confirm", True)
    payments.cmd_verify_payments()
    assert "does not support payments" in pub_host.said
    assert pub_site.sent("GET", f"{QAF}/payments/settings")


@pytest.mark.parametrize("ready", [False, True])
def test_publish_requires_site_payment_capability(
    fp, pub_site, pub_dialogs, pub_host, make_form, ready
):
    model = add_payment(pub_host)
    if ready:
        pub_site.on(
            "GET",
            f"{QAF}/payments/settings",
            {
                "contract_version": 1,
                "test_mode": True,
                "providers": {"stripe": {"configured": True, "webhook_ready": True}},
            },
        )
    pub_site.on("POST", f"{QAF}/forms", make_form())
    pub_dialogs.answer("ask_choice", 0).answer("confirm", True)
    fp.cmd_publish_form()
    sent = pub_site.sent("POST", f"{QAF}/forms")
    assert bool(sent) is ready
    assert "test payments only" in pub_dialogs.asked("confirm")[0]["message"]
    if ready:
        assert pub_site.body(sent[0])["model"]["extensions"] == model["extensions"]


def test_published_live_form_never_opens_in_test_flow(
    fp, pub_site, pub_dialogs, pub_host, make_form
):
    remote = add_payment(pub_host, test_mode=False)
    fp.published().set_link(pub_host.path, pub.Link("radio", 12, "Fee", "now", "active"))
    pub_site.on("GET", f"{QAF}/forms/12", make_form(config={"form_model": remote}))
    pub_dialogs.answer("confirm", True)
    fp.cmd_test_on_site()
    assert not pub_host.browsed
    assert "not in payment test mode" in pub_host.said


def test_a_test_mode_payment_form_opens_with_the_test_card_said(
    fp, pub_site, pub_dialogs, pub_host, make_form
):
    remote = add_payment(pub_host, test_mode=True)
    fp.published().set_link(pub_host.path, pub.Link("radio", 12, "Fee", "now", "active"))
    pub_site.on("GET", f"{QAF}/forms/12", make_form(config={"form_model": remote}))
    pub_site.on(
        "GET",
        f"{QAF}/payments/settings",
        {
            "contract_version": 1,
            "test_mode": True,
            "providers": {"stripe": {"configured": True, "webhook_ready": True}},
        },
    )
    page = {
        "id": 5,
        "link": "https://radio.example/fee/",
        "status": "publish",
        "title": {"raw": "Fee"},
        "content": {"raw": '<!-- wp:qaf/form {"formId":12} /-->'},
    }
    pub_site.on("GET", "/wp-json/wp/v2/pages", [page])
    pub_site.on("GET", "/wp-json/wp/v2/posts", [])
    pub_dialogs.answer("confirm", True)
    fp.cmd_test_on_site()
    assert pub_host.browsed == ["https://radio.example/fee/"]
    assert "4242 4242 4242 4242" in pub_host.said
    assert "Never a real card" in pub_host.said
    assert "PayPal" not in pub_host.said, "the form offers Stripe only"


def test_insert_payment_names_the_forms_amount_fields(payments, pub_host, monkeypatch):
    from quill.ui import wordpress_block_dialogs as dialogs

    model = fd.read(pub_host.text).model
    model["pages"][0]["items"].append({
        "id": "order_total",
        "type": "total",
        "label": "Order total",
    })
    pub_host.text = fd.canonical(model)
    seen = {}

    def ask(*args, **kwargs):
        seen.update({f.key: f.help for f in kwargs["fields"]})
        return {"label": "Pay", "amount": "#order_total"}

    monkeypatch.setattr(dialogs, "ask_fields", ask)
    payments.cmd_insert_payment()
    assert "#order_total (Order total)" in seen["amount"]
    [entry] = P.payment_fields(fd.read(pub_host.text).model)
    assert entry["item"]["props"]["amount"] == "#order_total"


@pytest.mark.parametrize("amount", ["10.005", "0.001"])
def test_an_amount_finer_than_cents_is_refused_before_the_site_sees_it(
    payments, pub_host, monkeypatch, amount
):
    setup(monkeypatch, {"amount": amount})
    before = pub_host.text
    payments.cmd_insert_payment()
    assert pub_host.text == before
    assert "decimal places" in pub_host.said


def test_setup_saves_rules_and_connections_and_refuses_a_rule_it_cannot_read(
    payments, pub_host, monkeypatch
):
    """complete.md Payments: choosing the connection by rule, and by selection."""
    add_payment(pub_host)
    rules = "amount under 50: stripe:small\notherwise: square:downtown"
    setup(monkeypatch, {"pay_with": "stripe", "rules": rules, "test_mode": True, "currency": "usd"})
    payments.cmd_payments_setup()
    block = fd.read(pub_host.text).model["extensions"]["payments"]
    assert block["rules"] == [{"when": {"amount_under": "50"}, "use": "stripe:small"}]
    assert block["otherwise"] == "square:downtown"
    assert block["providers"] == ["stripe", "square"] and "connections" not in block

    choose = {
        "pay_with": "stripe:events, paypal",
        "rules": "",
        "test_mode": True,
        "currency": "usd",
    }
    setup(monkeypatch, choose)
    payments.cmd_payments_setup()
    block = fd.read(pub_host.text).model["extensions"]["payments"]
    assert block["connections"] == ["stripe:events", "paypal"]
    assert "rules" not in block and "otherwise" not in block

    before = pub_host.text
    setup(monkeypatch, {**choose, "rules": "amount about 5: stripe"})
    payments.cmd_payments_setup()
    assert pub_host.text == before
    assert 'Line 1: "amount about 5"' in pub_host.said


def test_verify_lists_each_connection_and_where_this_form_sends_money(
    payments, pub_site, pub_dialogs, pub_host
):
    model = add_payment(pub_host)
    model["extensions"]["payments"].update({"connections": ["stripe:events", "square:downtown"]})
    pub_host.text = fd.canonical(model)
    pub_site.on(
        "GET",
        f"{QAF}/payments/settings",
        {
            "contract_version": 2,
            "test_mode": True,
            "providers": {"stripe": {"configured": True, "webhook_ready": True}},
            "connections": [
                {"id": "stripe:events", "name": "Stripe: Events", "test_mode": True,
                 "configured": True, "webhook_ready": True},
                {"id": "square:downtown", "name": "Square: Downtown", "test_mode": True,
                 "configured": True, "webhook_ready": False},
            ],
        },
    )  # fmt: skip
    pub_dialogs.answer("confirm", True)
    payments.cmd_verify_payments()
    text = pub_dialogs.reports[-1]["text"]
    assert "Connection Stripe: Events (stripe:events, test): works" in text
    assert "Connection Square: Downtown (square:downtown, test): not finished" in text
    assert "The payer chooses: stripe:events, square:downtown" in text
