"""Shared payment authoring and site readiness commands for both editors.

The existing native field dialog supplies labels, modal handling and F1 help.
No provider secrets enter this process; WordPress owns verification and checkout.
"""

from __future__ import annotations

from typing import Any

from quill.core.forms import payment_routing as pr
from quill.core.forms import payment_site as ps
from quill.core.forms import payments as pay
from quill.core.wordpress.block_catalog import Field as Ask
from quill.ui import forms_doc as fd
from quill.ui import wordpress_block_dialogs as wbd
from quill.ui import wordpress_dialogs as dlg


class FormsPaymentsCommands:
    host: Any

    def _payment_document(self, command: str) -> Any:
        if not self._payments_on():
            self.host.announce("Turn on Form Payments in Features before using this command.")
            return None
        doc = self.document(command)  # type: ignore[attr-defined]
        if doc is not None and doc.errors:
            self.host.announce("Fix the form's source errors with Check This Form first.")
            return None
        return doc

    def _payments_on(self) -> bool:
        """Form Payments is switched on: QUILL's feature, or QUILL Lite's area."""
        editor = self.host.ai_editor()
        enabled = getattr(editor, "_feature_enabled", None)
        if callable(enabled):
            return bool(enabled("core.forms_payments"))
        app = getattr(editor, "app", None)
        area = getattr(app, "feature_enabled", None)
        return bool(area("forms_payments")) if callable(area) else False

    def cmd_payments_setup(self) -> None:
        doc = self._payment_document("Form Payments Setup")
        if doc is None:
            return
        config = pay.payment_config(doc.model) or pay.PaymentConfig()
        raw = pay.raw_payment_config(doc.model)
        raw = raw if isinstance(raw, dict) else {}
        offered = raw.get("connections") if isinstance(raw.get("connections"), list) else None
        answer = wbd.ask_fields(
            self.host.parent,
            self.host.show_modal,
            title="Form Payments Setup",
            purpose="Configure this form locally. Publish Form sends it to your site. "
            "Set provider credentials and webhooks in WordPress, then Verify Payment Setup.",
            fields=[
                Ask(
                    "pay_with",
                    "Pay &with:",
                    "text",
                    "Who takes the money, in the order the payer sees them, separated by "
                    "commas: stripe, paypal or square for that provider's main connection on "
                    "the site, or a named one such as stripe:events or square:downtown. "
                    "The payer chooses only when there is more than one.",
                    value=", ".join(offered or config.providers),
                ),
                Ask(
                    "rules",
                    "Choose by &rule:",
                    "multiline",
                    "Leave empty to let the payer choose. Otherwise one rule a line, checked in "
                    "order: amount over 500: stripe:large-gifts, #fund is building: "
                    "square:building, currency is cad: stripe:canada, from 2026-12-01 until "
                    "2026-12-31: stripe:campaign, and last otherwise: stripe:events, which "
                    "takes every payment no rule catches.",
                    value=pr.format_rules(raw),
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
                    "digits and spaces (20 with Square), with at least one letter.",
                    value=config.statement_descriptor,
                ),
            ],
            ok_label="Save in Form",
        )
        if answer is None:
            return
        from copy import deepcopy

        candidate = deepcopy(doc.model)
        routing = _routing(answer)
        if isinstance(routing, str):
            self.host.announce("Payment setup was not saved. " + routing)
            return
        selected = pay.PaymentConfig.from_dict({
            **answer,
            "providers": pay.effective_providers(routing) or routing.get("providers"),
            "currency": str(answer.get("currency", "usd")).strip().lower(),
        })
        _write(candidate, selected, routing)
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
        _write(doc.model, selected, routing)
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
        doc = self._payment_document("Verify Payment Setup")
        if doc is None:
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
            for row in state.get("connections", []):
                mode = {True: "test", False: "live"}.get(row["test_mode"], "mode not reported")
                works = row["configured"] and row["webhook_ready"]
                lines.append(
                    f"Connection {row['name']} ({row['id']}, {mode}): "
                    + ("works" if works else "not finished: check its keys and webhook")
                )
            raw = pay.raw_payment_config(doc.model)
            if isinstance(raw, dict):
                lines.append("This form:")
                lines += pr.describe_routing(raw)
            dlg.show_report(
                self.host.parent,
                self.host.show_modal,
                title=f"Payment Setup on {profile.name}",
                text="\n".join(lines),
                help_text="The site's reported readiness. Complete a sandbox checkout "
                "and verify its entry before enabling live payments.",
            )

        self.with_qaf("Verify Payment Setup", profile, "reading payment setup", ps.settings, done)  # type: ignore[attr-defined]


_ROUTING_KEYS = ("connections", "rules", "otherwise")


def _routing(answer: dict[str, Any]) -> dict[str, Any] | str:
    """The Pay With and Choose by Rule answers as block keys, or what is wrong."""
    names = [n.strip().lower() for n in str(answer.get("pay_with", "")).split(",") if n.strip()]
    rules_text = str(answer.get("rules", "")).strip()
    if rules_text:
        rules, otherwise, problems = pr.parse_rules(rules_text)
        if problems:
            return problems[0]
        return {"rules": rules, "otherwise": otherwise}
    if not names:
        return "Name at least one provider or connection in Pay With."
    if any(":" in n for n in names):
        return {"connections": names}
    return {"providers": names}


def _write(model: dict[str, Any], config: pay.PaymentConfig, routing: dict[str, Any]) -> None:
    pay.set_payment_config(model, config)
    block = model["extensions"][pay.EXTENSION_KEY]
    for key in _ROUTING_KEYS:
        block.pop(key, None)
    if "providers" in routing:  # what the author typed, so a mistake is reported, not dropped
        block["providers"] = routing["providers"]
    block.update({k: v for k, v in routing.items() if k in _ROUTING_KEYS})
