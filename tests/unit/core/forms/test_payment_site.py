"""Plugin capability negotiation and payment metadata never move money."""

from __future__ import annotations

import csv
import io

import pytest

from quill.core.forms import payment_site as ps
from quill.core.forms import qaf_site as qs
from quill.core.forms import responses as rs
from quill.core.forms.payments import PaymentConfig, set_payment_config
from quill.core.wordpress.api import WordPressApiError


class Api:
    _quill_forms_namespace = "qaf/v1"

    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, route):
        self.calls.append(route)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def paid():
    model = {"pages": [{"items": [{"id": "pay", "type": "payment", "props": {"amount": 25}}]}]}
    set_payment_config(model, PaymentConfig())
    return model


def ready(**changes):
    return {
        "contract_version": 1,
        "test_mode": True,
        "providers": {"stripe": {"configured": True, "webhook_ready": True}},
        **changes,
    }


def test_ready_site_and_ordinary_form():
    api = Api(ready())
    ps.require_ready(api, {"pages": []})
    assert not api.calls
    ps.require_ready(api, paid())
    assert api.calls == ["qaf/v1/payments/settings"]


@pytest.mark.parametrize(
    "state",
    [
        None,
        {},
        {"contract_version": 2},
        ready(test_mode=False),
        ready(test_mode="true"),
        ready(providers={}),
        ready(providers={"stripe": {"configured": True}}),
    ],
)
def test_unready_or_malformed_site_blocks_publication(state):
    with pytest.raises(ps.PaymentSiteError):
        ps.require_ready(Api(state), paid())


def test_old_plugin_and_authentication_failures_are_distinct():
    with pytest.raises(ps.PaymentSiteError, match="does not support payments"):
        ps.settings(Api(WordPressApiError("missing", status=404)))
    with pytest.raises(WordPressApiError, match="unauthorized"):
        ps.settings(Api(WordPressApiError("unauthorized", status=401)))
    api = Api(ready())
    api._quill_forms_namespace = "baf/v1"
    with pytest.raises(ps.PaymentSiteError, match="Update"):
        ps.settings(api)
    assert api.calls == []


def test_settings_discard_unexpected_server_properties():
    state = ps.settings(
        Api(
            ready(
                secret_key="do not retain",
                providers={
                    "stripe": {"configured": True, "webhook_ready": True, "secret": "private"}
                },
            )
        )
    )
    assert "private" not in repr(state) and "secret" not in repr(state)


def test_payment_metadata_read_and_export_without_unknown_fields():
    row = qs.response_from_payload({
        "id": 1,
        "fields": {"name": "Ada"},
        "payment": {
            "provider": "stripe",
            "status": "paid",
            "amount": "25.00",
            "currency": "USD",
            "transaction_id": "pi_example",
            "receipt_url": "https://example.org/receipt",
            "secret": "hidden",
            "card_number": "hidden",
        },
    })
    assert "paid" in rs.row_text(row, {}, "Donation")
    assert "Payment transaction id: pi_example" in rs.one_at_a_time(row, {}, "Donation")
    output = list(csv.reader(io.StringIO(rs.csv_text([row], {"name": "Name"}))))
    assert output[1][output[0].index("Payment amount")] == "25.00"
    assert "hidden" not in str(output)
    assert "pi_example" not in repr(row)


def test_malformed_payment_metadata_is_ignored():
    assert qs.response_from_payload({"payment": []}).payment == {}
    assert qs.response_from_payload({"payment": {"status": {}, "amount": False}}).payment == {}
