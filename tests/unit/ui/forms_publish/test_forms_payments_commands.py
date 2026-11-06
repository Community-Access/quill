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
    setup(monkeypatch, {"providers": "paypal", "test_mode": False, "currency": "eur"})
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
