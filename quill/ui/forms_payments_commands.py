"""Shared payment authoring and site readiness commands for both editors.

The existing native field dialog supplies labels, modal handling and F1 help.
No provider secrets enter this process; WordPress owns verification and checkout.
"""

from __future__ import annotations

from typing import Any

from quill.core.forms import payment_site as ps
from quill.core.forms import payments as pay
from quill.core.wordpress.block_catalog import Field as Ask
from quill.ui import forms_doc as fd
from quill.ui import wordpress_block_dialogs as wbd
from quill.ui import wordpress_dialogs as dlg


class FormsPaymentsCommands:
    host: Any

    def _payment_document(self, command: str) -> Any:
        editor = self.host.ai_editor()
        enabled = getattr(editor, "_feature_enabled", None)
        if callable(enabled) and not enabled("core.forms_payments"):
            self.host.announce("Turn on Form Payments in Features before using this command.")
            return None
        doc = self.document(command)  # type: ignore[attr-defined]
        if doc is not None and doc.errors:
            self.host.announce("Fix the form's source errors with Check This Form first.")
            return None
        return doc

    def cmd_payments_setup(self) -> None:
        doc = self._payment_document("Form Payments Setup")
        if doc is None:
            return
        config = pay.payment_config(doc.model) or pay.PaymentConfig()
        answer = wbd.ask_fields(
            self.host.parent,
            self.host.show_modal,
            title="Form Payments Setup",
            purpose="Configure this form locally. Publish Form sends it to your site. "
            "Set provider credentials and webhooks in WordPress, then Verify Payment Setup.",
            fields=[
                Ask(
                    "providers",
                    "&Providers:",
                    "choice",
                    "Checkout providers, in display order.",
                    value=",".join(config.providers),
                    choices=["Stripe", "Stripe, then PayPal", "PayPal", "PayPal, then Stripe"],
                    values=["stripe", "stripe,paypal", "paypal", "paypal,stripe"],
                ),
                Ask(
                    "currency",
                    "&Currency:",
                    "text",
                    "Three-letter currency, such as usd or eur. "
                    "The site must support it for every selected provider.",
                    value=config.currency,
                ),
                Ask(
                    "mode",
                    "&Mode:",
                    "choice",
                    "A fixed or calculated payment, or a donation.",
                    value=config.mode,
                    choices=["Payment", "Donation"],
                    values=["payment", "donation"],
                ),
                Ask(
                    "capture",
                    "C&apture:",
                    "choice",
                    "Take payment immediately, or authorize "
                    "funds for capture later in the provider dashboard.",
                    value=config.capture,
                    choices=["Automatic", "Manual"],
                    values=["automatic", "manual"],
                ),
                Ask(
                    "test_mode",
                    "&Test mode",
                    "check",
                    "Keep this on while testing. Turning it "
                    "off allows real charges after publishing to a live-configured site.",
                    value=config.test_mode,
                ),
                Ask(
                    "statement_descriptor",
                    "&Statement descriptor:",
                    "text",
                    "Optional text for the payer's card statement: 5 to 22 plain letters, "
                    "digits and spaces, with at least one letter.",
                    value=config.statement_descriptor,
                ),
            ],
            ok_label="Save in Form",
        )
        if answer is None:
            return
        from copy import deepcopy

        candidate = deepcopy(doc.model)
        selected = pay.PaymentConfig.from_dict({
            **answer,
            "providers": str(answer.get("providers", "stripe")).split(","),
            "currency": str(answer.get("currency", "usd")).strip().lower(),
        })
        pay.set_payment_config(candidate, selected)
        errors = pay.semantic_errors(candidate)
        if errors:
            self.host.announce("Payment setup was not saved. " + errors[0]["message"])
            return
        if not selected.test_mode and not dlg.confirm(
            self.host.parent,
            self.host.show_modal,
            title="Use Live Payments",
            message="After publishing, this form can charge real money on a live-configured "
            "site. Save live payment mode in this form?",
            yes_label="Use Live Mode",
        ):
            return
        pay.set_payment_config(doc.model, selected)
        self.apply(doc, "Payment settings saved in this form. Publish Form sends them to the site.")  # type: ignore[attr-defined]

    def cmd_insert_payment(self) -> None:
        doc = self._payment_document("Insert Payment Field")
        if doc is None:
            return
        if pay.payment_fields(doc.model):
            self.host.announce("This form already has its payment field. Edit that field's source.")
            return
        amount_help = (
            "A positive number, #id of an amount field, "
            "or donation for an amount the visitor chooses."
        )
        sources = pay.amount_sources(doc.model)
        if sources:
            amount_help += " Amount fields in this form: " + "; ".join(sources) + "."
        answer = wbd.ask_fields(
            self.host.parent,
            self.host.show_modal,
            title="Insert Payment Field",
            purpose="Add one checkout field. Defaults use Stripe in test mode; Form Payments "
            "Setup changes providers and currency. No card data is collected in QUILL.",
            fields=[
                Ask("label", "&Label:", "text", "What visitors hear at checkout.", value="Payment"),
                Ask(
                    "amount",
                    "&Amount:",
                    "text",
                    amount_help,
                    value="25",
                ),
                Ask("minimum", "Donation mi&nimum:", "text", "Optional positive donation minimum."),
                Ask("maximum", "Donation ma&ximum:", "text", "Optional positive donation maximum."),
            ],
            ok_label="Insert",
        )
        if answer is None:
            return
        from copy import deepcopy
        from dataclasses import replace

        amount = str(answer.get("amount", "")).strip()
        props: dict[str, Any] = {"amount": amount}
        try:
            if amount != "donation" and not amount.startswith("#"):
                props["amount"] = float(amount)
            for name, key in (("minimum", "donation_min"), ("maximum", "donation_max")):
                if str(answer.get(name, "")).strip():
                    props[key] = float(answer[name])
        except ValueError:
            self.host.announce(
                "Enter a positive amount, #field-id, or donation; bounds are numbers."
            )
            return
        candidate = deepcopy(doc.model)
        config = pay.payment_config(candidate) or pay.PaymentConfig()
        config = replace(config, mode="donation" if amount == "donation" else "payment")
        pay.set_payment_config(candidate, config)
        item = {
            "id": fd.new_id(candidate, "payment"),
            "type": "payment",
            "label": str(answer.get("label") or "Payment"),
            "props": props,
        }
        candidate["pages"][-1]["items"].append(item)
        errors = pay.semantic_errors(candidate)
        if errors:
            self.host.announce("Payment field was not inserted. " + errors[0]["message"])
            return
        pay.set_payment_config(doc.model, config)
        doc.model["pages"][-1]["items"].append(item)
        self.apply(doc, "Inserted payment field. Check Form Payments Setup before publishing.")  # type: ignore[attr-defined]

    def cmd_verify_payments(self) -> None:
        if self._payment_document("Verify Payment Setup") is None:
            return
        if self.offline_only("Verify Payment Setup"):  # type: ignore[attr-defined]
            return
        link = self.published().link_for(self.host.current_path())  # type: ignore[attr-defined]
        profile = self.choose_site("Verify Payment Setup", link.site_id if link else "")  # type: ignore[attr-defined]
        if profile is None or not dlg.confirm(
            self.host.parent,
            self.host.show_modal,
            title="Verify Payment Setup",
            message=f"Read payment configuration and webhook readiness from {profile.name} "
            f"({profile.site_url})? Credentials are managed in that site's WordPress dashboard.",
            yes_label="Read Setup",
        ):
            return

        def done(state: dict[str, Any]) -> None:
            lines = [
                "Test mode"
                if state["test_mode"] is True
                else "Live mode"
                if state["test_mode"] is False
                else "Mode not reported"
            ]
            for name in pay.PAYMENT_PROVIDERS:
                entry = state["providers"].get(name, {})
                lines.append(
                    f"{name}: "
                    + ("configured" if entry.get("configured") else "not configured")
                    + ", webhook "
                    + ("ready" if entry.get("webhook_ready") else "not ready")
                )
            dlg.show_report(
                self.host.parent,
                self.host.show_modal,
                title=f"Payment Setup on {profile.name}",
                text="\n".join(lines),
                help_text="The site's reported readiness. Complete a sandbox checkout "
                "and verify its entry before enabling live payments.",
            )

        self.with_qaf("Verify Payment Setup", profile, "reading payment setup", ps.settings, done)  # type: ignore[attr-defined]
