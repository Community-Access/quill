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


#: The contract versions this client reads. Version 2 adds Square and named connections.
CONTRACT_VERSIONS = (1, 2)
_PROVIDERS = ("stripe", "paypal", "square")


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
    version = raw.get("contract_version") if isinstance(raw, dict) else None
    if version not in CONTRACT_VERSIONS or isinstance(version, bool):
        raise PaymentSiteError("The site did not return a supported payment settings contract.")
    # Do not keep arbitrary server properties, especially accidental secret echoes.
    providers = raw.get("providers")
    return {
        "contract_version": version,
        "test_mode": raw.get("test_mode"),
        "providers": {
            name: {
                "configured": entry.get("configured") is True,
                "webhook_ready": entry.get("webhook_ready") is True,
            }
            for name, entry in (providers.items() if isinstance(providers, dict) else [])
            if name in _PROVIDERS and isinstance(entry, dict)
        },
        "connections": _connections(raw.get("connections")) if version >= 2 else [],
    }


def _connections(raw: Any) -> list[dict[str, Any]]:
    """Each named connection's public facts; anything else in a row is dropped."""
    from quill.core.forms.payment_routing import connection_provider, valid_reference

    out: list[dict[str, Any]] = []
    for row in raw if isinstance(raw, list) else []:
        if not isinstance(row, dict) or not valid_reference(row.get("id")):
            continue
        ref = str(row["id"])
        name = row.get("name")
        out.append({
            "id": ref,
            "name": name if isinstance(name, str) and name else ref,
            "provider": connection_provider(ref),
            "test_mode": row.get("test_mode") if isinstance(row.get("test_mode"), bool) else None,
            "configured": row.get("configured") is True,
            "webhook_ready": row.get("webhook_ready") is True,
        })
    return out


def site_payments_text(api: Any) -> str:
    """The site's payment connections in sentences, for its Properties' Payments page.

    Names, providers, modes and whether each works -- never a key, which the
    route does not send and :func:`settings` would drop if it did.
    """
    try:
        state = settings(api)
    except WordPressApiError as exc:
        return str(getattr(exc, "plain", "") or exc)
    lines = [f"The site takes {'test' if state['test_mode'] else 'live'} payments."]
    rows = state["connections"] or [
        {"id": name, "name": name.title(), "test_mode": state["test_mode"], **entry}
        for name, entry in state["providers"].items()
    ]
    for row in rows:
        mode = {True: "test", False: "live"}.get(row["test_mode"], "mode not reported")
        works = row["configured"] and row["webhook_ready"]
        lines.append(
            f"{row['name']} ({row['id']}, {mode}): "
            + ("works." if works else "not finished: its keys or webhook need checking.")
        )
    if len(lines) == 1:
        lines.append("No payment connection is set up yet.")
    lines.append(
        "Connections are added, checked and removed on the site, in QAF Forms > Payments; "
        "a form names them in Form Payments Setup."
    )
    return "\n".join(lines)


def require_ready(api: Any, model: dict[str, Any]) -> None:
    """Refuse publishing paid forms to old, unconfigured or wrong-mode plugins."""
    from quill.core.forms.payment_routing import referenced_connections
    from quill.core.forms.payments import payment_config, payment_fields, raw_payment_config

    if not payment_fields(model):
        return
    config = payment_config(model)
    if config is None:
        raise PaymentSiteError("Set up this form's payments before publishing it.")
    state = settings(api)
    if state["test_mode"] is not config.test_mode:
        raise PaymentSiteError("The form and site must use the same payment test/live mode.")
    raw = raw_payment_config(model)
    refs = referenced_connections(raw) if isinstance(raw, dict) else []
    if not refs:
        for provider in config.providers:
            if provider == "square" and state["contract_version"] < 2:
                raise PaymentSiteError("Update the site's QAF plugin to take Square payments.")
            entry = state["providers"].get(provider, {})
            if not entry.get("configured") or not entry.get("webhook_ready"):
                raise PaymentSiteError(
                    f"Configure {provider} and verify its webhook in WordPress before publishing."
                )
        return
    if state["contract_version"] < 2:
        raise PaymentSiteError(
            "Update the site's QAF plugin to choose between payment connections."
        )
    on_site = {c["id"]: c for c in state["connections"]}
    for ref in refs:
        found = on_site.get(ref)
        if found is None:
            raise PaymentSiteError(f"The site has no payment connection called {ref}.")
        if found["test_mode"] is not config.test_mode:
            raise PaymentSiteError(
                f"{found['name']} is in {'test' if found['test_mode'] else 'live'} mode and this "
                f"form is in {'test' if config.test_mode else 'live'} mode. A form never mixes "
                "test and live connections."
            )
        if not found["configured"] or not found["webhook_ready"]:
            raise PaymentSiteError(
                f"Finish {found['name']} in WordPress (its keys and webhook) before publishing."
            )
