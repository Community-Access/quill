"""One filter for every list: a query string, the attributes it can name, and local matching.

The filter box takes one string (GitHub PRD section 17.1). Plain words narrow
the loaded list on this device; qualifiers (``label:bug``, ``-label:docs``,
``created:>2026-01-01``) are what the provider's service is asked for. The
Filter Builder edits the same query as rows of attribute, operator and value,
and turns them back into the same string, so the four ways in can never
disagree.

The ``key:value`` qualifier syntax here is GitHub's, and the default; a
provider with another syntax (WordPress's REST parameters) supplies its own
:class:`QuerySyntax`.
"""

from __future__ import annotations

import shlex
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

__all__ = [
    "Attribute",
    "Condition",
    "Operator",
    "Query",
    "QualifierSyntax",
    "QuerySyntax",
    "describe",
    "matches_words",
    "parse",
    "render",
]


class Operator(StrEnum):
    IS = "is"
    IS_NOT = "is not"
    AFTER = "after"
    BEFORE = "before"
    AT_LEAST = "at least"
    AT_MOST = "at most"


@dataclass(frozen=True)
class Attribute:
    """Something a list can be filtered on, for the Filter Builder's first column."""

    key: str
    label: str
    operators: tuple[Operator, ...] = (Operator.IS, Operator.IS_NOT)
    values: tuple[str, ...] = ()
    help: str = ""


@dataclass(frozen=True)
class Condition:
    attribute: str
    operator: Operator
    value: str


@dataclass(frozen=True)
class Query:
    """A parsed filter: qualifier conditions and the plain words left over."""

    conditions: tuple[Condition, ...] = ()
    words: tuple[str, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not self.conditions and not self.words

    def with_condition(self, condition: Condition) -> Query:
        return Query((*self.conditions, condition), self.words)

    def without(self, attribute: str) -> Query:
        return Query(tuple(c for c in self.conditions if c.attribute != attribute), self.words)


class QuerySyntax(Protocol):
    def render(self, condition: Condition) -> str: ...

    def read(self, token: str) -> Condition | None: ...


@dataclass(frozen=True)
class QualifierSyntax:
    """GitHub's ``key:value`` qualifiers: ``-`` negates, ``>``/``<`` compare."""

    def render(self, condition: Condition) -> str:
        value = condition.value
        if any(ch.isspace() for ch in value):
            value = f'"{value}"'
        prefix = {
            Operator.IS: "",
            Operator.IS_NOT: "-",
        }.get(condition.operator, "")
        compare = {
            Operator.AFTER: ">",
            Operator.BEFORE: "<",
            Operator.AT_LEAST: ">=",
            Operator.AT_MOST: "<=",
        }.get(condition.operator, "")
        return f"{prefix}{condition.attribute}:{compare}{value}"

    def read(self, token: str) -> Condition | None:
        key, sep, value = token.partition(":")
        if not sep or not key or not value or key.startswith(("http", "https")):
            return None
        operator = Operator.IS
        if key.startswith("-"):
            key, operator = key[1:], Operator.IS_NOT
        for mark, compared in ((">=", Operator.AT_LEAST), ("<=", Operator.AT_MOST)):
            if value.startswith(mark):
                return Condition(key, compared, value[2:])
        if value.startswith(">"):
            return Condition(key, Operator.AFTER, value[1:])
        if value.startswith("<"):
            return Condition(key, Operator.BEFORE, value[1:])
        return Condition(key, operator, value) if key else None


def _tokens(text: str) -> list[str]:
    try:
        return shlex.split(text, posix=True)
    except ValueError:  # an unclosed quote: take the words as typed
        return text.split()


def parse(text: str, syntax: QuerySyntax | None = None) -> Query:
    """Split *text* into conditions the service understands and plain words."""
    reader = syntax or QualifierSyntax()
    conditions: list[Condition] = []
    words: list[str] = []
    for token in _tokens(text.strip()):
        condition = reader.read(token)
        if condition is None:
            words.append(token)
        else:
            conditions.append(condition)
    return Query(tuple(conditions), tuple(words))


def render(query: Query, syntax: QuerySyntax | None = None) -> str:
    """The one query string: conditions first, then the plain words."""
    writer = syntax or QualifierSyntax()
    parts = [writer.render(condition) for condition in query.conditions]
    parts.extend(f'"{word}"' if " " in word else word for word in query.words)
    return " ".join(parts)


def describe(query: Query, attributes: Sequence[Attribute] = ()) -> str:
    """The filter in words, for Alt+7 and the status bar: "label is bug, state is open"."""
    if query.is_empty:
        return "No filter"
    names = {attribute.key: attribute.label for attribute in attributes}
    parts = [
        f"{names.get(c.attribute, c.attribute)} {c.operator.value} {c.value}"
        for c in query.conditions
    ]
    if query.words:
        parts.append("containing " + " ".join(query.words))
    return ", ".join(parts)


def matches_words(text: str, words: Iterable[str]) -> bool:
    """Whether a row's text holds every plain word, ignoring case (local filtering)."""
    lowered = text.casefold()
    return all(word.casefold() in lowered for word in words)
