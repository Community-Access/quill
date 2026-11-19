"""The date range, interval, money and comparison words of Shop Analytics (complete.md 2.3).

Split from :mod:`quill.core.wordpress.workbench_shop_analytics` (GATE-11). A
:class:`Period` is what the person chose for a site's reports: a range preset
(Today, Last 7 Days, Month to Date ... or Custom with two dates) and an
interval (day, week, month). It travels to the loader as plain strings
(:meth:`Period.as_params`), so the Workbench's loader signature does not
change. The previous period is the same number of days just before
(:func:`previous`), read from the same route, and :func:`compared` turns the
two totals into "up 12% on the 7 days before".

:class:`Money` says an amount the way the store's own settings do (currency
symbol and where it goes, the thousands and decimal separators, how many
decimals), read once a load from ``wc/v3/settings/general`` and
``wc/v3/data/currencies/current`` (:func:`read_money`). Wx-free.
"""

from __future__ import annotations

import html
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from quill.core.wordpress.api import WordPressApiError

__all__ = [
    "DEFAULT_RANGE",
    "INTERVALS",
    "RANGES",
    "Money",
    "Period",
    "compared",
    "days_words",
    "number",
    "parse_day",
    "previous",
    "read_money",
]

RANGES: tuple[tuple[str, str], ...] = (
    ("today", "Today"),
    ("yesterday", "Yesterday"),
    ("last_7_days", "Last 7 Days"),
    ("last_30_days", "Last 30 Days"),
    ("month_to_date", "Month to Date"),
    ("last_month", "Last Month"),
    ("this_year", "This Year"),
    ("last_year", "Last Year"),
    ("custom", "Custom..."),
)
"""The Date Range choices, in the order offered; Custom asks for two dates."""

DEFAULT_RANGE = "last_7_days"

INTERVALS: tuple[tuple[str, str], ...] = (("day", "Day"), ("week", "Week"), ("month", "Month"))
"""The Interval choices: one row per day, week or month in Revenue, Orders and Downloads."""

_RANGE_KEYS = frozenset(key for key, _label in RANGES)
_INTERVAL_KEYS = frozenset(key for key, _label in INTERVALS)


def parse_day(text: str) -> date | None:
    """``2026-11-03`` as a date, or None when it is not one."""
    try:
        return date.fromisoformat(text.strip())
    except ValueError:
        return None


def _day_words(day: date) -> str:
    return f"{day.day} {day.strftime('%B %Y')}"


@dataclass(frozen=True)
class Period:
    """A site's chosen range and interval; *start* and *end* only for Custom."""

    range: str = DEFAULT_RANGE
    interval: str = "day"
    start: date | None = None
    end: date | None = None

    def dates(self, today: date) -> tuple[date, date]:
        """The first and last day the range covers, both included."""
        if self.range == "custom" and self.start and self.end:
            return self.start, self.end
        if self.range == "today":
            return today, today
        if self.range == "yesterday":
            day = today - timedelta(days=1)
            return day, day
        if self.range == "last_30_days":
            return today - timedelta(days=29), today
        if self.range == "month_to_date":
            return today.replace(day=1), today
        if self.range == "last_month":
            last = today.replace(day=1) - timedelta(days=1)
            return last.replace(day=1), last
        if self.range == "this_year":
            return today.replace(month=1, day=1), today
        if self.range == "last_year":
            return date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)
        return today - timedelta(days=6), today

    def words(self, today: date) -> str:
        """How the range is said: ``last 7 days``, or ``1 November 2026 to 19 November 2026``."""
        if self.range == "custom" and self.start and self.end:
            if self.start == self.end:
                return _day_words(self.start)
            return f"{_day_words(self.start)} to {_day_words(self.end)}"
        label = dict(RANGES).get(self.range, "Last 7 Days")
        return label.lower()

    @property
    def label(self) -> str:
        """The range's name in the Date Range list (Custom shows its dates)."""
        if self.range == "custom" and self.start and self.end:
            return f"Custom: {self.start.isoformat()} to {self.end.isoformat()}"
        return dict(RANGES).get(self.range, "Last 7 Days")

    def as_params(self) -> dict[str, str]:
        """The period as the loader's query takes it (strings only)."""
        params = {"range": self.range, "interval": self.interval}
        if self.range == "custom" and self.start and self.end:
            params.update(start=self.start.isoformat(), end=self.end.isoformat())
        return params

    @classmethod
    def from_params(cls, query: Mapping[str, object]) -> Period:
        """A period from :meth:`as_params`; anything missing or unknown is the default."""
        chosen = str(query.get("range", "") or DEFAULT_RANGE)
        interval = str(query.get("interval", "") or "day")
        interval = interval if interval in _INTERVAL_KEYS else "day"
        if chosen == "custom":
            start = parse_day(str(query.get("start", "") or ""))
            end = parse_day(str(query.get("end", "") or ""))
            if start and end:
                return cls("custom", interval, min(start, end), max(start, end))
            chosen = DEFAULT_RANGE
        return cls(chosen if chosen in _RANGE_KEYS else DEFAULT_RANGE, interval)


def previous(start: date, end: date) -> tuple[date, date]:
    """The same number of days just before *start*."""
    days = (end - start).days + 1
    return start - timedelta(days=days), start - timedelta(days=1)


def days_words(start: date, end: date) -> str:
    """``the day before`` / ``the 7 days before``: the previous period, said."""
    days = (end - start).days + 1
    return "the day before" if days == 1 else f"the {days} days before"


def compared(now: float, before: float, start: date, end: date) -> str:
    """``, up 12% on the 7 days before`` (or down, the same, or against none); "" for none."""
    then = days_words(start, end)
    if not before:
        return f", against none in {then}" if now else f", and none in {then} either"
    change = round((now - before) / abs(before) * 100)
    if change == 0:
        return f", the same as {then}"
    return f", {'up' if change > 0 else 'down'} {abs(change)}% on {then}"


def number(value: Any) -> float:
    """A report's figure as a number; anything unreadable is 0."""
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


@dataclass(frozen=True)
class Money:
    """How the store writes an amount (WooCommerce > Settings > General, Currency options)."""

    symbol: str = ""
    code: str = ""
    position: str = "left"
    thousands: str = ","
    decimal: str = "."
    decimals: int = 2

    def say(self, amount: Any, *, short: bool = False) -> str:
        """``$1,240.00``; *short* drops decimals that are all zero (``$1,240``), for speech."""
        value = number(amount)
        digits = max(0, self.decimals)
        text = f"{abs(value):,.{digits}f}"
        whole, _sep, cents = text.partition(".")
        whole = whole.replace(",", self.thousands)
        plain = not cents or (short and not cents.strip("0"))
        figure = whole if plain else whole + self.decimal + cents
        sign = "-" if value < 0 and round(abs(value), digits) else ""
        if not self.symbol:
            return f"{sign}{figure} {self.code}".strip()
        space = " " if self.position.endswith("_space") else ""
        if self.position.startswith("right"):
            return f"{sign}{figure}{space}{self.symbol}"
        return f"{sign}{self.symbol}{space}{figure}"


def read_money(api: Any) -> Money:
    """The store's currency settings; what cannot be read falls back to ``1,240.00 USD``."""
    settings: dict[str, str] = {}
    try:
        found = api.get("wc/v3/settings/general")
        for row in found if isinstance(found, list) else []:
            if isinstance(row, Mapping):
                settings[str(row.get("id", ""))] = str(row.get("value", "") or "")
    except WordPressApiError:
        pass
    symbol = code = ""
    try:
        current = api.get("wc/v3/data/currencies/current")
        if isinstance(current, Mapping):
            symbol = html.unescape(str(current.get("symbol", "") or ""))
            code = str(current.get("code", "") or "")
    except WordPressApiError:
        pass
    try:
        decimals = int(settings.get("woocommerce_price_num_decimals", "2") or 2)
    except ValueError:
        decimals = 2
    return Money(
        symbol=symbol,
        code=code or settings.get("woocommerce_currency", ""),
        position=settings.get("woocommerce_currency_pos", "") or "left",
        thousands=settings.get("woocommerce_price_thousand_sep", ","),
        decimal=settings.get("woocommerce_price_decimal_sep", "") or ".",
        decimals=decimals,
    )
