"""Payment configuration on QAF, through the existing WordPress transport.

Provider credentials and checkout operations belong to the plugin. These
routes return only public configuration and readiness information.
"""

from __future__ import annotations

from typing import Any

from quill.core.forms.qaf_site import site_namespace
from quill.core.wordpress.api import WordPressApiError


class PaymentSiteError(WordPressApiError):
    """The site's payment capability is unavailable or its reply is invalid."""

    code = "QUILL-FORMS-PAYMENTS-SITE"


def settings(api: Any) -> dict[str, Any]:
    """Read the versioned payment capability; never treat a missing route as ready."""
    namespace = site_namespace(api)
    if namespace != "qaf/v1":
        raise PaymentSiteError("Update the site's QAF plugin to a version supporting payments.")
    try:
        raw = api.get(f"{namespace}/payments/settings")
    except WordPressApiError as exc:
        if exc.status == 404:
            raise PaymentSiteError(
                "The site's QAF plugin does not support payments yet. Update the plugin."
            ) from None
        raise
    if not isinstance(raw, dict) or raw.get("contract_version") != 1:
        raise PaymentSiteError("The site did not return a supported payment settings contract.")
    # Do not keep arbitrary server properties, especially accidental secret echoes.
    providers = raw.get("providers")
    return {
        "contract_version": 1,
        "test_mode": raw.get("test_mode"),
        "providers": {
            name: {
                "configured": entry.get("configured") is True,
                "webhook_ready": entry.get("webhook_ready") is True,
            }
            for name, entry in (providers.items() if isinstance(providers, dict) else [])
            if name in ("stripe", "paypal") and isinstance(entry, dict)
        },
    }


def require_ready(api: Any, model: dict[str, Any]) -> None:
    """Refuse publishing paid forms to old, unconfigured or wrong-mode plugins."""
    from quill.core.forms.payments import payment_config, payment_fields

    if not payment_fields(model):
        return
    config = payment_config(model)
    if config is None:
        raise PaymentSiteError("Set up this form's payments before publishing it.")
    state = settings(api)
    if state["test_mode"] is not config.test_mode:
        raise PaymentSiteError("The form and site must use the same payment test/live mode.")
    for provider in config.providers:
        entry = state["providers"].get(provider, {})
        if not entry.get("configured") or not entry.get("webhook_ready"):
            raise PaymentSiteError(
                f"Configure {provider} and verify its webhook in WordPress before publishing."
            )
