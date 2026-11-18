"""Which payment connection takes the money: by the payer's selection, or by rule.

A site's QAF plugin can hold several named connections per provider
("Stripe: Events", "Stripe: Donations", "Square: Downtown"). A form names
them by **reference**: the bare provider (``stripe``) for that provider's
default connection, or ``provider:slug`` (``stripe:events``) for a named one.
The provider is part of the reference on purpose, so QUILL can check
currencies and statement descriptors offline without asking the site which
provider a connection belongs to.

Two ways to choose, never both, in ``extensions["payments"]``:

- **By selection** -- ``"connections": ["stripe:events", "paypal"]``: the
  payer sees the choices, in that order, when there is more than one; the
  first is the default.
- **By rule** -- ``"rules": [{"when": {...}, "use": ref}, ...]`` and
  ``"otherwise": ref``: checked in order, the first that matches takes the
  payment, and ``otherwise`` always catches the rest, so a payment never has
  nowhere to go. At checkout the plugin also skips a rule whose connection is
  down and falls through to the next.

A rule's ``when`` is one of ``{"amount_over": "500"}``,
``{"amount_under": "10"}``, ``{"field": "fund", "equals": "building"}``,
``{"currency": "cad"}`` or ``{"from": "2026-12-01", "until": "2026-12-31"}``
(either end may be left out). Amounts are decimal strings, never floats.

:func:`parse_rules` and :func:`format_rules` turn the plain lines an author
types (``amount over 500: stripe:large-gifts``) into that JSON and back;
:func:`routing_errors` is what Check This Form and publishing report,
including rules that can never fire. Contract:
``docs/design/forms-payments-plugin-contract.md`` (version 2).

wx-free; strict-typed.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

__all__ = [
    "RULE_KINDS",
    "connection_provider",
    "describe_routing",
    "format_rules",
    "parse_rules",
    "referenced_connections",
    "routing_errors",
    "valid_reference",
]

#: The providers a reference may start with; kept in step with ``payments``.
_PROVIDERS = ("stripe", "paypal", "square")
_REFERENCE = re.compile(r"^(stripe|paypal|square)(?::([a-z0-9][a-z0-9-]{0,39}))?$")
#: The kinds of ``when`` a rule may have, as an author reads them.
RULE_KINDS = ("amount over", "amount under", "#field is", "currency is", "from/until", "otherwise")


def valid_reference(ref: Any) -> bool:
    """``stripe``, ``paypal``, ``square``, or one of them, a colon and a slug."""
    return isinstance(ref, str) and _REFERENCE.match(ref) is not None


def connection_provider(ref: str) -> str:
    """The provider a reference belongs to: ``"stripe:events"`` -> ``"stripe"``."""
    return ref.split(":", 1)[0]


def referenced_connections(raw: dict[str, Any]) -> list[str]:
    """Every connection the block can send money to, first mention first."""
    refs: list[Any] = []
    for ref in _list(raw.get("connections")):
        refs.append(ref)
    for rule in _list(raw.get("rules")):
        if isinstance(rule, dict):
            refs.append(rule.get("use"))
    refs.append(raw.get("otherwise"))
    out: list[str] = []
    for ref in refs:
        if valid_reference(ref) and ref not in out:
            out.append(ref)
    return out


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


# -- plain lines <-> JSON ---------------------------------------------------------------

_LINE = re.compile(r"^(?P<when>.+?)\s*:\s*(?P<use>[a-z0-9:-]+)\s*$")
_DATE = r"\d{4}-\d{2}-\d{2}"


def parse_rules(text: str) -> tuple[list[dict[str, Any]], str | None, list[str]]:
    """The author's lines as ``(rules, otherwise, problems)``.

    One rule a line, condition, a colon, then the connection::

        amount over 500: stripe:large-gifts
        #fund is building: square:building
        from 2026-12-01 until 2026-12-31: stripe:campaign
        otherwise: stripe:events

    Blank lines are skipped. Each line that does not read is a problem
    naming its line number, and nothing is guessed.
    """
    rules: list[dict[str, Any]] = []
    otherwise: str | None = None
    problems: list[str] = []
    for number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        match = _LINE.match(line)
        if match is None:
            problems.append(f"Line {number} needs a condition, a colon, then a connection.")
            continue
        when_text, use = match.group("when").strip(), match.group("use")
        when = _parse_when(when_text.lower() if not when_text.startswith("#") else when_text)
        if when_text.lower() == "otherwise":
            if otherwise is not None:
                problems.append(f"Line {number} is a second otherwise; a form has one.")
            otherwise = use
        elif when is None:
            problems.append(
                f'Line {number}: "{when_text}" is not a rule QUILL knows '
                "(amount over, amount under, #field is, currency is, from or until)."
            )
        else:
            rules.append({"when": when, "use": use})
    return rules, otherwise, problems


def _parse_when(text: str) -> dict[str, Any] | None:  # noqa: PLR0911 - one return per kind
    match = re.fullmatch(r"amount (over|under) ([0-9]+(?:\.[0-9]+)?)", text)
    if match:
        return {f"amount_{match.group(1)}": match.group(2)}
    match = re.fullmatch(r"#([A-Za-z0-9_-]+) is (.+)", text)
    if match:
        return {"field": match.group(1), "equals": match.group(2).strip()}
    match = re.fullmatch(r"currency is ([a-z]{3})", text)
    if match:
        return {"currency": match.group(1)}
    match = re.fullmatch(rf"(?:from ({_DATE}))?\s*(?:until ({_DATE}))?", text)
    if match and (match.group(1) or match.group(2)):
        window = {"from": match.group(1), "until": match.group(2)}
        return {k: v for k, v in window.items() if v}
    return None


def format_rules(raw: dict[str, Any]) -> str:
    """The block's rules as the lines :func:`parse_rules` reads, for editing."""
    lines = [
        f"{_when_text(rule.get('when'))}: {rule.get('use')}"
        for rule in _list(raw.get("rules"))
        if isinstance(rule, dict)
    ]
    if raw.get("otherwise"):
        lines.append(f"otherwise: {raw['otherwise']}")
    return "\n".join(lines)


def _when_text(when: Any) -> str:
    when = when if isinstance(when, dict) else {}
    for side in ("over", "under"):
        if f"amount_{side}" in when:
            return f"amount {side} {when[f'amount_{side}']}"
    if "field" in when:
        return f"#{when['field']} is {when.get('equals', '')}"
    if "currency" in when:
        return f"currency is {when['currency']}"
    parts = [f"{k} {when[k]}" for k in ("from", "until") if when.get(k)]
    return " ".join(parts) or "?"


def describe_routing(raw: dict[str, Any]) -> list[str]:
    """Where the money goes, one sentence a row, for Verify Payment Setup."""
    if _list(raw.get("rules")) or raw.get("otherwise"):
        rows = [
            f"When {_when_text(rule.get('when'))}, {rule.get('use')} takes the payment."
            for rule in _list(raw.get("rules"))
            if isinstance(rule, dict)
        ]
        rows.append(f"Otherwise, {raw.get('otherwise') or 'nothing'} takes it.")
        return rows
    offered = [r for r in _list(raw.get("connections")) if valid_reference(r)]
    if len(offered) > 1:
        return [f"The payer chooses: {', '.join(offered)}; {offered[0]} is the default."]
    if offered:
        return [f"{offered[0]} takes every payment."]
    providers = [p for p in _list(raw.get("providers")) if p in _PROVIDERS]
    return [f"Each provider's default connection on the site: {', '.join(providers) or 'none'}."]


# -- what Check This Form reports --------------------------------------------------------


def routing_errors(model: dict[str, Any], raw: dict[str, Any], base: str) -> list[dict[str, str]]:
    """Connection and rule problems, including rules that can never fire."""
    errors: list[dict[str, str]] = []

    def err(path: str, message: str) -> None:
        errors.append({"path": path, "message": message})

    connections = raw.get("connections")
    if "connections" in raw:
        if not isinstance(connections, list) or not connections:
            err(f"{base}/connections", "connections must be a list naming at least one.")
        else:
            _reference_list_errors(connections, f"{base}/connections", err)
    has_rules = "rules" in raw or "otherwise" in raw
    if has_rules and "connections" in raw:
        err(
            f"{base}/rules",
            "Choose the connection by the payer's selection or by rule, not both: "
            "remove connections or remove the rules.",
        )
    if has_rules:
        _rule_errors(model, raw, base, err)
    return errors


def _reference_list_errors(refs: list[Any], path: str, err: Any) -> None:
    seen: set[str] = set()
    for i, ref in enumerate(refs):
        if not valid_reference(ref):
            err(f"{path}/{i}", _bad_reference(ref))
        elif ref in seen:
            err(f"{path}/{i}", f'The connection "{ref}" is listed twice.')
        else:
            seen.add(ref)


def _bad_reference(ref: Any) -> str:
    return (
        f'"{ref}" is not a connection: use stripe, paypal or square, '
        "or one of them, a colon and the connection's short name (stripe:events)."
    )


def _rule_errors(model: dict[str, Any], raw: dict[str, Any], base: str, err: Any) -> None:
    rules = raw.get("rules", [])
    otherwise = raw.get("otherwise")
    if not valid_reference(otherwise):
        err(
            f"{base}/otherwise",
            "Rules need an otherwise: the connection that takes every payment no rule "
            "catches, so a payment never has nowhere to go."
            if otherwise is None
            else _bad_reference(otherwise),
        )
    if not isinstance(rules, list):
        err(f"{base}/rules", "rules must be a list.")
        return
    fields = _fields_by_id(model)
    currency = str(raw.get("currency") or "usd").lower()
    fixed = _fixed_amount(model)
    seen: list[dict[str, Any]] = []
    for i, rule in enumerate(rules):
        path = f"{base}/rules/{i}"
        if not isinstance(rule, dict) or not isinstance(rule.get("when"), dict):
            err(path, "Each rule needs a when and a use.")
            continue
        if not valid_reference(rule.get("use")):
            err(f"{path}/use", _bad_reference(rule.get("use")))
        when = rule["when"]
        reason = _never_fires(when, seen, fields, currency, fixed)
        if reason:
            err(f"{path}/when", f"This rule can never take a payment: {reason}.")
        seen.append(when)


def _fields_by_id(model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    from quill.core.forms import model as M

    return {e["item"]["id"]: e["item"] for e in M.items(model) if "id" in e["item"]}


def _fixed_amount(model: dict[str, Any]) -> Decimal | None:
    from quill.core.forms import model as M

    for entry in M.items(model):
        item = entry["item"]
        if item.get("type") == "payment":
            amount = (item.get("props") or {}).get("amount")
            if isinstance(amount, (int, float)) and not isinstance(amount, bool):
                return Decimal(str(amount))
    return None


def _decimal(value: Any) -> Decimal | None:
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        return None
    return number if number.is_finite() and number >= 0 else None


def _never_fires(  # noqa: C901, PLR0911, PLR0912 - one branch per kind of rule
    when: dict[str, Any],
    earlier: list[dict[str, Any]],
    fields: dict[str, dict[str, Any]],
    currency: str,
    fixed: Decimal | None,
) -> str:
    if when in earlier:
        return "an earlier rule has the same condition and always takes it first"
    for side in ("over", "under"):
        key = f"amount_{side}"
        if key in when:
            limit = _decimal(when[key])
            if limit is None:
                return f"{when[key]} is not an amount"
            if fixed is not None and not (fixed > limit if side == "over" else fixed < limit):
                return f"this form's amount is always {fixed}"
            for prior in earlier:
                other = _decimal(prior.get(key))
                if other is not None and (other <= limit if side == "over" else other >= limit):
                    return f"the earlier amount {side} {prior[key]} rule catches every such payment"
            return ""
    if "field" in when:
        field = fields.get(str(when["field"]))
        if field is None:
            return f"#{when['field']} is not in this form"
        choices = field.get("choices")
        if isinstance(choices, list) and choices:
            values = {str(c.get("value")) for c in choices if isinstance(c, dict)}
            labels = {str(c.get("label")) for c in choices if isinstance(c, dict)}
            if str(when.get("equals")) not in values | labels:
                return f'#{when["field"]} has no choice "{when.get("equals")}"'
        return ""
    if "currency" in when:
        if str(when["currency"]).lower() != currency:
            return f"this form takes {currency} only"
        return ""
    if "from" in when or "until" in when:
        try:
            start = date.fromisoformat(when["from"]) if when.get("from") else None
            end = date.fromisoformat(when["until"]) if when.get("until") else None
        except (TypeError, ValueError):
            return "a date is not a real day (write 2026-12-31)"
        if start and end and start > end:
            return "its window ends before it starts"
        return ""
    return "QUILL does not know this kind of rule"
