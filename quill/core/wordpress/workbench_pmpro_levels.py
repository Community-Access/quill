"""Make or change a Paid Memberships Pro membership level (complete.md 2.3, Memberships).

PMPro's REST route ``pmpro/v1/membership_level`` gets, makes, changes and
deletes a level (PMPro's REST API documentation: "Get, Update, Create, or
Delete a Membership Level Object"): a POST with no ``id`` makes one, a POST
with the level's ``id`` changes it, and the fields are the
``PMPro_Membership_Level`` object's. QUILL sends the price fields as plain
amounts and never anything about a member or a payment.

Changing a price changes it for new signups; PMPro does not change what
existing members pay, and the preview says so.

Three things the route does that its documentation does not say, all seen on
the test site (PMPro 3.9.2, 2026-11-20), and all read from its
``pmpro_rest_api_set_membership_level``:

- a ``POST`` *always* makes a new level, even with an ``id``; only ``PUT`` or
  ``PATCH`` changes one, so :func:`save_level` sends ``PUT`` for a change (a
  ``POST`` made a second level instead of saving the first);
- ``DELETE`` is turned off unless the site's ``pmpro_rest_api_methods`` filter
  adds it, so deleting a level (New Membership Level's Ctrl+Z) is refused with
  403 and :func:`delete_refused_words` says where to delete it instead;
- the recurring payment's period is never stored (``cycle_period`` is read and
  not set) and the expiry period is cast to a number, so :func:`not_saved` reads
  the level back and names what the site left out, rather than reporting a
  saved level that differs from the one previewed. Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from decimal import Decimal, InvalidOperation
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.wordpress.site import plain_text

__all__ = [
    "LEVEL_ROUTE",
    "PERIODS",
    "LevelSpec",
    "LevelValueError",
    "delete_refused_words",
    "level_body",
    "level_from",
    "level_preview",
    "money",
    "not_saved",
    "save_level",
    "unchanged",
]

LEVEL_ROUTE = "pmpro/v1/membership_level"
#: PMPro's own period words, in the order a chooser offers them.
PERIODS = ("Day", "Week", "Month", "Year")


class LevelValueError(CodedError, ValueError):
    """Something typed for a level that PMPro would not take, in one sentence."""

    code = "QUILL-WP-PMPRO-LEVEL"


def money(text: str, what: str) -> str:
    """An amount as PMPro stores it ("10.00"), or a sentence saying why not."""
    words = text.strip().lstrip("$").replace(",", "") or "0"
    try:
        value = Decimal(words)
    except InvalidOperation:
        raise LevelValueError(f"The {what}, {text.strip()}, is not an amount.") from None
    if value < 0 or value > Decimal(1_000_000):
        raise LevelValueError(f"The {what} is from 0 to 1000000.")
    return str(value.quantize(Decimal("0.01")))


@dataclass(frozen=True)
class LevelSpec:
    """A level's settings, as the person gave them."""

    name: str
    description: str = ""
    initial_payment: str = "0.00"
    billing_amount: str = "0.00"
    cycle_number: int = 1
    cycle_period: str = "Month"
    billing_limit: int = 0
    expiration_number: int = 0
    expiration_period: str = "Month"
    allow_signups: bool = True

    def billing_words(self) -> str:
        if Decimal(self.billing_amount) <= 0:
            return "no recurring payment"
        every = (
            f"every {self.cycle_period.lower()}"
            if self.cycle_number == 1
            else f"every {self.cycle_number} {self.cycle_period.lower()}s"
        )
        limit = f", {self.billing_limit} times" if self.billing_limit else ""
        return f"{self.billing_amount} {every}{limit}"

    def expiry_words(self) -> str:
        if not self.expiration_number:
            return "never expires"
        period = self.expiration_period.lower() + ("s" if self.expiration_number != 1 else "")
        return f"expires after {self.expiration_number} {period}"


def _whole(value: Any, low: int = 0, high: int = 10_000) -> int:
    try:
        number = int(str(value).strip() or 0)
    except ValueError:
        return low
    return min(max(number, low), high)


def level_from(raw: Mapping[str, Any]) -> LevelSpec:
    """A level as PMPro returns it, for Edit to start from."""
    period = str(raw.get("cycle_period") or "Month").title()
    expiry = str(raw.get("expiration_period") or "Month").title()
    return LevelSpec(
        name=plain_text(str(raw.get("name") or "")),
        description=str(raw.get("description") or ""),
        initial_payment=money(str(raw.get("initial_payment") or "0"), "initial payment"),
        billing_amount=money(str(raw.get("billing_amount") or "0"), "recurring payment"),
        cycle_number=_whole(raw.get("cycle_number"), 1) if raw.get("cycle_number") else 1,
        cycle_period=period if period in PERIODS else "Month",
        billing_limit=_whole(raw.get("billing_limit")),
        expiration_number=_whole(raw.get("expiration_number")),
        expiration_period=expiry if expiry in PERIODS else "Month",
        allow_signups=str(raw.get("allow_signups", "1")) not in ("0", "False", "false", ""),
    )


def level_body(spec: LevelSpec, level_id: int = 0) -> dict[str, Any]:
    """The POST body: every field, with ``id`` only when changing a level."""
    if not spec.name.strip():
        raise LevelValueError("A level needs a name.")
    if spec.cycle_period not in PERIODS or spec.expiration_period not in PERIODS:
        raise LevelValueError("A period is a day, week, month or year.")
    body: dict[str, Any] = {
        "name": " ".join(spec.name.split()),
        "description": spec.description,
        "initial_payment": spec.initial_payment,
        "billing_amount": spec.billing_amount,
        "cycle_number": spec.cycle_number if Decimal(spec.billing_amount) > 0 else 0,
        "cycle_period": spec.cycle_period,
        "billing_limit": spec.billing_limit,
        "trial_amount": "0.00",
        "trial_limit": 0,
        "expiration_number": spec.expiration_number,
        "expiration_period": spec.expiration_period,
        "allow_signups": 1 if spec.allow_signups else 0,
    }
    if level_id:
        body["id"] = int(level_id)
    return body


def level_preview(spec: LevelSpec, site: str, old: LevelSpec | None = None) -> list[str]:
    """The level in words; for a change, only what changes, old and new."""
    now = {
        "Name": spec.name,
        "Initial payment": spec.initial_payment,
        "Recurring payment": spec.billing_words(),
        "Expiry": spec.expiry_words(),
        "New signups": "allowed" if spec.allow_signups else "not allowed",
        "Description": spec.description or "(none)",
    }
    if old is None:
        lines = [f"A new membership level on {site}:"]
        lines += [f"{key}: {value}." for key, value in now.items()]
        return lines
    before = {
        "Name": old.name,
        "Initial payment": old.initial_payment,
        "Recurring payment": old.billing_words(),
        "Expiry": old.expiry_words(),
        "New signups": "allowed" if old.allow_signups else "not allowed",
        "Description": old.description or "(none)",
    }
    lines = [f"Membership level {old.name} on {site}:"]
    lines += [
        f"{key}: {before[key]} becomes {value}."
        for key, value in now.items()
        if before[key] != value
    ]
    if any(before[k] != now[k] for k in ("Initial payment", "Recurring payment")):
        lines.append("New prices are for new signups; PMPro does not change what members pay now.")
    return lines


def unchanged(spec: LevelSpec, old: LevelSpec) -> bool:
    return all(getattr(spec, f.name) == getattr(old, f.name) for f in fields(LevelSpec))


def save_level(api: Any, body: Mapping[str, Any]) -> Any:
    """Make a level (``POST``, no ``id``) or change one (``PUT``, with its ``id``).

    PMPro's route makes a new level for every ``POST``, ``id`` or not.
    """
    method = "PUT" if body.get("id") else "POST"
    return api.request(method, LEVEL_ROUTE, json_body=dict(body)).payload


def delete_refused_words(name: str, site: str) -> str:
    """Why a level could not be deleted through REST, and where to delete it."""
    return (
        f"{site} would not delete the membership level {name}: Paid Memberships Pro turns "
        "deleting off in its REST API unless the site allows it (the pmpro_rest_api_methods "
        "filter). Delete it under Memberships > Settings > Levels in wp-admin."
    )


_CHECKED = (
    ("name", "Name"),
    ("initial_payment", "Initial payment"),
    ("billing_amount", "Recurring payment"),
    ("cycle_number", "Billing every"),
    ("cycle_period", "Billing period"),
    ("billing_limit", "Billing limit"),
    ("expiration_number", "Expiry"),
    ("expiration_period", "Expiry period"),
    ("allow_signups", "New signups"),
)


def _same(key: str, sent: Any, stored: Any) -> bool:
    if key in ("initial_payment", "billing_amount"):
        try:
            return Decimal(str(sent or 0)) == Decimal(str(stored or 0))
        except InvalidOperation:
            return False
    if key in ("cycle_period", "expiration_period"):
        return str(sent or "").casefold() == str(stored or "").casefold()
    if key == "name":
        return " ".join(str(sent).split()) == " ".join(plain_text(str(stored or "")).split())
    return str(_whole(sent, -1)) == str(_whole(stored, -1))


def not_saved(body: Mapping[str, Any], stored: Mapping[str, Any]) -> list[str]:
    """What the site did not keep of *body*, read back as *stored*, by name.

    A period only matters where its number does: no recurring payment, no period.
    A field the answer leaves out entirely is not judged: only one it gives back
    different from what was sent.
    """
    missed: list[str] = []
    for key, label in _CHECKED:
        if key not in body or key not in stored:
            continue
        if key == "cycle_period" and not _whole(body.get("cycle_number")):
            continue
        if key == "expiration_period" and not _whole(body.get("expiration_number")):
            continue
        if not _same(key, body[key], stored.get(key)):
            missed.append(label)
    return missed
