"""Verbosity token specs and the engine filter set (verbosity §12).

A *token* is a named value a verb can put into an announcement template, such as
``{line}`` or ``{word}``. A :class:`TokenSpec` declares a token's name, value
type, human description, an optional derive callable, and the filters it allows.

A *filter* transforms a token's value as it is rendered: ``${upper:word}``
upper-cases the word, ``${ordinal:line}`` turns ``3`` into ``3rd``. Only the
twelve engine-provided filters in :data:`FILTERS` exist — **custom filters are
not supported** (verbosity §12). That keeps templates and the future QUILL
Verbosity Pack (QVP) files data-only, with no code-execution surface.

Pure and wx-free.
"""

from __future__ import annotations

import enum
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

__all__ = [
    "TokenType",
    "NUMERIC_TYPES",
    "TokenSpec",
    "FilterSpec",
    "FILTERS",
    "get_filter",
    "filter_allowed_for_type",
    "apply_filter",
]


class TokenType(enum.Enum):
    """The value types a token may carry."""

    STR = "str"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    DATETIME = "datetime"
    DURATION = "duration"


#: Token types the numeric filters (``ordinal``, ``pad``) accept.
NUMERIC_TYPES = frozenset({TokenType.INT, TokenType.FLOAT})


@dataclass(frozen=True, slots=True)
class TokenSpec:
    """One named value a verb can expose to its announcement template.

    ``filters`` is the per-token allowlist (verbosity §13): only filters named
    here may be applied to this token. An empty tuple means the token accepts no
    filters at all.
    """

    name: str
    type: TokenType
    description: str = ""
    derive: Callable[[dict[str, Any]], Any] | None = None
    filters: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FilterSpec:
    """An engine filter: how it transforms a value and what it accepts.

    ``allowed_types`` empty means the filter accepts any token type. ``apply``
    receives the raw token value and the optional ``:arg:`` string and returns
    the rendered text.
    """

    name: str
    requires_arg: bool
    allowed_types: frozenset[TokenType]
    apply: Callable[[Any, str | None], str]


def _ordinal(value: Any, _arg: str | None) -> str:
    number = int(value)
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def _pad(value: Any, arg: str | None) -> str:
    width = int(arg) if arg is not None else 0
    return f"{int(value):0{width}d}"


def _pluralize(value: Any, _arg: str | None) -> str:
    word = str(value)
    if word.endswith(("s", "sh", "ch", "x", "z")):
        return f"{word}es"
    return f"{word}s"


def _singular(value: Any, _arg: str | None) -> str:
    word = str(value)
    if word.endswith("ies") and len(word) > 3:
        return f"{word[:-3]}y"
    if word.endswith("es") and word[:-2].endswith(("s", "sh", "ch", "x", "z")):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _duration_human(value: Any, _arg: str | None) -> str:
    total = int(value.total_seconds()) if isinstance(value, timedelta) else int(value)
    if total < 0:
        total = 0
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds or not parts:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    return " ".join(parts)


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    raise TypeError("expected a datetime value")


def _date_long(value: Any, _arg: str | None) -> str:
    moment = _as_datetime(value)
    return f"{moment.strftime('%A, %B')} {moment.day}, {moment.year}"


def _date_short(value: Any, _arg: str | None) -> str:
    return _as_datetime(value).strftime("%Y-%m-%d")


def _time(value: Any, _arg: str | None) -> str:
    moment = _as_datetime(value)
    return moment.strftime("%I:%M %p").lstrip("0")


def _truncate(value: Any, arg: str | None) -> str:
    limit = int(arg) if arg is not None else 0
    text = str(value)
    if limit <= 0 or len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return text[: limit - 3].rstrip() + "..."


#: The twelve engine-provided filters. No other filters exist.
FILTERS: dict[str, FilterSpec] = {
    "upper": FilterSpec("upper", False, frozenset(), lambda v, _a: str(v).upper()),
    "lower": FilterSpec("lower", False, frozenset(), lambda v, _a: str(v).lower()),
    "title": FilterSpec("title", False, frozenset(), lambda v, _a: str(v).title()),
    "ordinal": FilterSpec("ordinal", False, NUMERIC_TYPES, _ordinal),
    "pad": FilterSpec("pad", True, NUMERIC_TYPES, _pad),
    "pluralize": FilterSpec("pluralize", False, frozenset(), _pluralize),
    "singular": FilterSpec("singular", False, frozenset(), _singular),
    "duration_human": FilterSpec(
        "duration_human", False, frozenset({TokenType.DURATION}), _duration_human
    ),
    "date_long": FilterSpec("date_long", False, frozenset({TokenType.DATETIME}), _date_long),
    "date_short": FilterSpec("date_short", False, frozenset({TokenType.DATETIME}), _date_short),
    "time": FilterSpec("time", False, frozenset({TokenType.DATETIME}), _time),
    "truncate": FilterSpec("truncate", True, frozenset(), _truncate),
}


def get_filter(name: str) -> FilterSpec | None:
    """Return the :class:`FilterSpec` for ``name``, or ``None`` if unknown."""
    return FILTERS.get(name)


def filter_allowed_for_type(filter_spec: FilterSpec, token_type: TokenType) -> bool:
    """True if ``filter_spec`` may be applied to a token of ``token_type``."""
    if not filter_spec.allowed_types:
        return True
    return token_type in filter_spec.allowed_types


def apply_filter(name: str, value: Any, arg: str | None = None) -> str:
    """Apply the named engine filter to ``value`` and return the rendered text.

    Raises :class:`KeyError` for an unknown filter — callers that need a graceful
    error should validate the template first via :mod:`quill.core.verbosity.parser`.
    """
    spec = FILTERS[name]
    return spec.apply(value, arg)
