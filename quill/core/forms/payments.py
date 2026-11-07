"""Payments in a form: provider-neutral configuration and validation.

A form takes payment through the QAF WordPress plugin -- Stripe first, PayPal
second -- and QUILL's side of that is configuration, never money movement
(``docs/design/forms-payments-plugin-contract.md`` is the contract the plugin
keeps). The configuration lives in the model under
``extensions["payments"]``: the schema's ``extensions`` block is the one
place a program may keep data of its own, QAF stores and returns it
unchanged, and the schema itself -- byte-identical with QAF's, checked by the
conformance suite -- needs no change. A ``payment`` field's own options
(amount source, donation bounds) live in its ``props``, which BFL's
``@amount`` / ``@donation_min`` / ``@donation_max`` modifiers already read
and write, so a paid form round-trips byte for byte with no new syntax.

:func:`semantic_errors` holds the rules a schema cannot state; the model's
own :func:`quill.core.forms.model.semantic_errors` calls it, so Check This
Form and publishing both see them. No secret -- no Stripe key, no PayPal
secret -- ever belongs in this block; credentials stay on the WordPress site.

wx-free; strict-typed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

from quill.core.forms import model as M

__all__ = [
    "AMOUNT_DONATION",
    "AMOUNT_FIELD_TYPES",
    "CAPTURE_KINDS",
    "DEFAULT_PROVIDER",
    "EXTENSION_KEY",
    "ISO_4217_CURRENCIES",
    "PAYMENT_MODES",
    "PAYMENT_PROVIDERS",
    "STATEMENT_DESCRIPTOR_LIMIT",
    "STATEMENT_DESCRIPTOR_MINIMUM",
    "PaymentConfig",
    "PaymentProvider",
    "amount_sources",
    "clear_payment_config",
    "currency_decimals",
    "payment_config",
    "payment_fields",
    "semantic_errors",
    "set_payment_config",
]

PaymentProvider = Literal["stripe", "paypal"]

#: In the order a new form offers them: Stripe is the favored, first provider.
PAYMENT_PROVIDERS: tuple[PaymentProvider, ...] = ("stripe", "paypal")
DEFAULT_PROVIDER: PaymentProvider = "stripe"

#: What the form collects: a one-time payment, or a donation the giver sets.
PAYMENT_MODES: tuple[str, ...] = ("payment", "donation")

#: When the charge is taken: at submit, or held for review on the site.
CAPTURE_KINDS: tuple[str, ...] = ("automatic", "manual")

#: The model key: ``model["extensions"][EXTENSION_KEY]``.
EXTENSION_KEY = "payments"

#: A ``payment`` field's ``@amount`` for a giver-entered donation amount.
AMOUNT_DONATION = "donation"

#: Field types an ``@amount "#id"`` reference may name: each yields a number.
AMOUNT_FIELD_TYPES: tuple[str, ...] = ("total", "price", "calculation", "number", "currency")

#: Stripe's statement-descriptor ceiling, the stricter of the two providers'.
STATEMENT_DESCRIPTOR_LIMIT = 22
#: Stripe's floor for a full descriptor. The QAF plugin refuses a shorter
#: one when the form is published, so QUILL says so first.
STATEMENT_DESCRIPTOR_MINIMUM = 5
_STATEMENT_FORBIDDEN = frozenset("<>\\'\"*")

#: Currency identifiers understood by this client; provider support is checked on site.
ISO_4217_CURRENCIES: frozenset[str] = frozenset(
    """
    aed afn all amd ang aoa ars aud awg azn bam bbd bdt bgn bhd bif bmd bnd
    bob brl bsd btn bwp byn bzd cad cdf chf clp cny cop crc cup cve czk djf
    dkk dop dzd egp ern etb eur fjd fkp gbp gel ghs gip gmd gnf gtq gyd hkd
    hnl htg huf idr ils inr iqd irr isk jmd jod jpy kes kgs khr kmf kpw krw
    kwd kyd kzt lak lbp lkr lrd lsl lyd mad mdl mga mkd mmk mnt mop mru mur
    mvr mwk mxn myr mzn nad ngn nio nok npr nzd omr pab pen pgk php pkr pln
    pyg qar ron rsd rub rwf sar sbd scr sdg sek sgd shp sle sll sos srd ssp
    stn svc syp szl thb tjs tmt tnd top try ttd twd tzs uah ugx usd uyu uzs
    ves vnd vuv wst xaf xcd xof xpf yer zar zmw zwl
    """.split()
)


@dataclass(frozen=True, slots=True)
class PaymentConfig:
    """The provider-neutral payment configuration of one form.

    Authors start in test mode on purpose: nothing charges a real card until
    someone deliberately turns ``test_mode`` off.
    """

    providers: tuple[PaymentProvider, ...] = (DEFAULT_PROVIDER,)
    currency: str = "usd"
    mode: str = "payment"
    capture: str = "automatic"
    statement_descriptor: str = ""
    test_mode: bool = True

    def to_dict(self) -> dict[str, Any]:
        """The JSON block as it is stored, keys in one fixed order."""
        out: dict[str, Any] = {
            "providers": list(self.providers),
            "currency": self.currency,
            "mode": self.mode,
            "capture": self.capture,
            "test_mode": self.test_mode,
        }
        if self.statement_descriptor:
            out["statement_descriptor"] = self.statement_descriptor
        return out

    @classmethod
    def from_dict(cls, data: Any) -> PaymentConfig:
        """The stored block as a config; anything malformed takes its default.

        :func:`semantic_errors` is where malformed data is *reported*; this
        reader never fails, so a window can always show what is there.
        """
        raw = data if isinstance(data, dict) else {}
        providers = tuple(p for p in _as_list(raw.get("providers")) if p in PAYMENT_PROVIDERS) or (
            DEFAULT_PROVIDER,
        )
        currency = raw.get("currency")
        mode = raw.get("mode")
        capture = raw.get("capture")
        descriptor = raw.get("statement_descriptor")
        return cls(
            providers=providers,  # type: ignore[arg-type]
            currency=currency if isinstance(currency, str) else "usd",
            mode=mode if isinstance(mode, str) else "payment",
            capture=capture if isinstance(capture, str) else "automatic",
            statement_descriptor=descriptor if isinstance(descriptor, str) else "",
            test_mode=raw.get("test_mode") is not False,
        )


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def raw_payment_config(model: M.Model) -> Any:
    """``extensions["payments"]`` exactly as stored, or ``None``."""
    extensions = model.get("extensions")
    if not isinstance(extensions, dict):
        return None
    return extensions.get(EXTENSION_KEY)


def payment_config(model: M.Model) -> PaymentConfig | None:
    """The form's payment configuration, or ``None`` when it has none."""
    raw = raw_payment_config(model)
    return PaymentConfig.from_dict(raw) if isinstance(raw, dict) else None


def set_payment_config(model: M.Model, config: PaymentConfig) -> None:
    """Write *config* into the model (``extensions["payments"]``)."""
    extensions = model.get("extensions")
    if not isinstance(extensions, dict):
        extensions = {}
        model["extensions"] = extensions
    existing = extensions.get(EXTENSION_KEY)
    block = dict(existing) if isinstance(existing, dict) else {}
    block.pop("statement_descriptor", None)
    block.update(config.to_dict())
    extensions[EXTENSION_KEY] = block


def clear_payment_config(model: M.Model) -> None:
    """Remove the payment configuration; an emptied ``extensions`` goes too."""
    extensions = model.get("extensions")
    if isinstance(extensions, dict):
        extensions.pop(EXTENSION_KEY, None)
        if not extensions:
            del model["extensions"]


def payment_fields(model: M.Model) -> list[dict[str, Any]]:
    """Every ``payment`` field, as :func:`model.items` entries (item, path, page)."""
    return [e for e in M.items(model) if e["item"].get("type") == "payment"]


# -- the rules beyond the schema ---------------------------------------------------------


def semantic_errors(model: M.Model) -> list[dict[str, str]]:
    """What a schema cannot say about payments; empty when the form is fine.

    The same rules the QAF plugin applies before rendering a checkout
    (``docs/design/forms-payments-plugin-contract.md``): a ``payment`` field
    needs a resolvable amount source, one payment field per form, and a form
    that takes payment needs a providers list it can honour.
    """
    errors: list[dict[str, str]] = []

    def err(path: str, message: str) -> None:
        errors.append({"path": path, "message": message})

    raw = raw_payment_config(model)
    base = f"/extensions/{EXTENSION_KEY}"
    extensions = model.get("extensions")
    if isinstance(extensions, dict) and EXTENSION_KEY in extensions and not isinstance(raw, dict):
        err(base, "The payments block must be a JSON object.")
        raw = None
    if isinstance(raw, dict):
        _config_errors(raw, base, err)

    found = payment_fields(model)
    for entry in found[1:]:
        err(
            entry["path"],
            "Only one payment field is allowed per form; this is the second.",
        )
    if found and not (isinstance(raw, dict) and _as_list(raw.get("providers"))):
        err(
            base,
            "A form with a payment field needs a payments block naming at "
            "least one provider (Form Payments Setup writes one).",
        )
    by_id = {e["item"]["id"]: e["item"] for e in M.items(model) if "id" in e["item"]}
    currency = raw.get("currency") if isinstance(raw, dict) else None
    places = currency_decimals(currency if isinstance(currency, str) else "usd")
    for entry in found:
        _amount_errors(entry["item"], entry["path"], by_id, err)
        _precision_errors(entry["item"], entry["path"], places, err)
    return errors


#: Currencies with no minor unit, and with three decimals, as Stripe and
#: PayPal count them; every other currency has two.
_ZERO_DECIMAL = frozenset("bif clp djf gnf jpy kmf krw mga pyg rwf ugx vnd vuv xaf xof xpf".split())
_THREE_DECIMAL = frozenset("bhd jod kwd omr tnd".split())


def amount_sources(model: M.Model) -> list[str]:
    """The fields an ``@amount "#id"`` may name, as an author hears them.

    ``['#order_total (Order total)', '#fee (Fee)']``, in the form's order, so
    Insert Payment Field can say which ids there are instead of leaving the
    author to remember them.
    """
    out: list[str] = []
    for entry in M.items(model):
        item = entry["item"]
        if item.get("type") in AMOUNT_FIELD_TYPES and isinstance(item.get("id"), str):
            label = item.get("label")
            out.append(
                f"#{item['id']} ({label})" if isinstance(label, str) and label else f"#{item['id']}"
            )
    return out


def currency_decimals(currency: str) -> int:
    """How many decimal places an amount in *currency* may have: 0, 2 or 3."""
    code = currency.lower()
    if code in _ZERO_DECIMAL:
        return 0
    return 3 if code in _THREE_DECIMAL else 2


def _decimal_places(value: float) -> int:
    from decimal import Decimal

    exponent = Decimal(repr(value)).normalize().as_tuple().exponent
    return -exponent if isinstance(exponent, int) and exponent < 0 else 0


def _precision_errors(item: dict[str, Any], path: str, places: int, err: Any) -> None:
    """A fixed amount or a bound with more decimals than the currency has.

    The plugin refuses these rather than rounding someone's price, so QUILL
    says so before publishing: 10.005 dollars, or 2000.5 yen.
    """
    props = item.get("props")
    if not isinstance(props, dict):
        return
    for key in ("amount", "donation_min", "donation_max"):
        value = props.get(key)
        if _positive_number(value) and _decimal_places(float(value)) > places:  # type: ignore[arg-type]
            unit = "whole amounts only" if places == 0 else f"at most {places} decimal places"
            err(f"{path}/props/{key}", f"This currency takes {unit}.")


def _config_errors(raw: dict[str, Any], base: str, err: Any) -> None:  # noqa: C901 - one rule per block, as the model's own checker
    providers = raw.get("providers")
    if "providers" in raw:
        if not isinstance(providers, list) or not providers:
            err(f"{base}/providers", "providers must be a list naming at least one provider.")
        else:
            seen: set[str] = set()
            for i, p in enumerate(providers):
                if p not in PAYMENT_PROVIDERS:
                    known = ", ".join(PAYMENT_PROVIDERS)
                    err(f"{base}/providers/{i}", f'"{p}" is not a payment provider ({known}).')
                elif p in seen:
                    err(f"{base}/providers/{i}", f'The provider "{p}" is listed twice.')
                else:
                    seen.add(str(p))
    currency = raw.get("currency")
    if "currency" in raw and (
        not isinstance(currency, str) or currency.lower() not in ISO_4217_CURRENCIES
    ):
        err(f"{base}/currency", f'"{currency}" is not an ISO 4217 currency code (such as "usd").')
    mode = raw.get("mode")
    if "mode" in raw and mode not in PAYMENT_MODES:
        err(f"{base}/mode", f"mode must be one of: {', '.join(PAYMENT_MODES)}.")
    capture = raw.get("capture")
    if "capture" in raw and capture not in CAPTURE_KINDS:
        err(f"{base}/capture", f"capture must be one of: {', '.join(CAPTURE_KINDS)}.")
    descriptor = raw.get("statement_descriptor")
    if descriptor is not None:
        if not isinstance(descriptor, str):
            err(f"{base}/statement_descriptor", "The statement descriptor must be text.")
        elif len(descriptor) > STATEMENT_DESCRIPTOR_LIMIT:
            err(
                f"{base}/statement_descriptor",
                f"The statement descriptor is over {STATEMENT_DESCRIPTOR_LIMIT} characters.",
            )
        elif descriptor and len(descriptor) < STATEMENT_DESCRIPTOR_MINIMUM:
            err(
                f"{base}/statement_descriptor",
                f"The statement descriptor needs at least {STATEMENT_DESCRIPTOR_MINIMUM} "
                "characters, or leave it empty.",
            )
        elif any(c in _STATEMENT_FORBIDDEN for c in descriptor):
            err(
                f"{base}/statement_descriptor",
                "The statement descriptor cannot contain <, >, \\, ', \" or *.",
            )
        elif descriptor and not all(" " <= c <= "~" for c in descriptor):
            err(
                f"{base}/statement_descriptor",
                "The statement descriptor uses plain letters, digits and spaces only, "
                "as card statements print them.",
            )
        elif descriptor and not any(c.isascii() and c.isalpha() for c in descriptor):
            err(
                f"{base}/statement_descriptor",
                "The statement descriptor needs at least one letter.",
            )
    test_mode = raw.get("test_mode")
    if "test_mode" in raw and not isinstance(test_mode, bool):
        err(f"{base}/test_mode", "test_mode must be true or false.")


def _positive_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return value > 0 and (isinstance(value, int) or math.isfinite(value))


def _amount_errors(
    item: dict[str, Any], path: str, by_id: dict[str, dict[str, Any]], err: Any
) -> None:
    raw_props = item.get("props")
    props: dict[str, Any] = raw_props if isinstance(raw_props, dict) else {}
    amount = (props or {}).get("amount")
    donation = amount == AMOUNT_DONATION
    for key in ("donation_min", "donation_max"):
        if key in (props or {}):
            if not donation:
                err(f"{path}/props/{key}", f'@{key} only applies with @amount "{AMOUNT_DONATION}".')
            elif not _positive_number(props[key]):
                err(f"{path}/props/{key}", f"@{key} must be a number greater than zero.")
    if (
        donation
        and _positive_number((props or {}).get("donation_min"))
        and _positive_number((props or {}).get("donation_max"))
        and props["donation_min"] > props["donation_max"]
    ):
        err(f"{path}/props/donation_min", "The smallest donation is larger than the largest.")
    if amount is None:
        err(
            f"{path}/props/amount",
            'A payment field needs @amount: a fixed number, "#id" of a total '
            f'or price field, or "{AMOUNT_DONATION}".',
        )
        return
    if _positive_number(amount):
        return
    if not isinstance(amount, str):
        err(f"{path}/props/amount", "@amount must be a number greater than zero, or text.")
        return
    if donation:
        return
    if amount.startswith("#"):
        ref = amount[1:]
        target = by_id.get(ref)
        if target is None:
            err(f"{path}/props/amount", f"@amount names #{ref}, which is not in this form.")
        elif target.get("type") not in AMOUNT_FIELD_TYPES:
            kinds = ", ".join(AMOUNT_FIELD_TYPES)
            err(
                f"{path}/props/amount",
                f"@amount names #{ref}, which is not an amount field ({kinds}).",
            )
        return
    err(
        f"{path}/props/amount",
        f'@amount must be a number greater than zero, "#id", or "{AMOUNT_DONATION}".',
    )
