"""One test a rule asks: a field, a comparison and a value. Never raises.

This is Cast's Episode Filter condition (``quill.core.podcasts.filter_conditions``)
made field-agnostic. The **vocabulary is imported, not copied** -- the same test
ids, the same phrases, the same wildcard convention -- so "contains" means one
thing in a Cast filter and a Lineup rule, and a new test added there is one
place to add it here.

Cast's three rules carry over unchanged, because they are what make a rule
trustworthy:

* **A missing fact never matches a number test.** An episode whose feed did not
  say how long it is has not said "zero minutes".
* **An unusable condition makes its whole rule match nothing** -- a pattern that
  does not compile, a number test with no number, a field this build does not
  know. Matching nothing is visible; matching everything is a surprise.
* **Nothing raises.** A rule is evaluated during a refresh, in the background.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from quill.core.lineups.fields import LIST, NUMBER, TEXT, YESNO, Fact, ItemFacts, field_for
from quill.core.podcasts.filter_conditions import (
    NUMBER_OPS,
    OP_AT_LEAST,
    OP_AT_MOST,
    OP_CONTAINS,
    OP_ENDS,
    OP_IS,
    OP_IS_NOT,
    OP_NOT_CONTAINS,
    OP_NOT_REGEX,
    OP_PHRASES,
    OP_REGEX,
    OP_STARTS,
    OP_WILDCARD,
    TEXT_OPS,
)

YESNO_OPS: tuple[str, ...] = (OP_IS, OP_IS_NOT)
YES = "yes"
NO = "no"


def ops_for_type(field_type: str) -> tuple[str, ...]:
    """The tests that make sense for a field of *field_type*."""
    if field_type == NUMBER:
        return NUMBER_OPS
    if field_type == YESNO:
        return YESNO_OPS
    return TEXT_OPS


def ops_for(kind: str, field_id: str) -> tuple[str, ...]:
    """The tests offered for one field of one kind; empty for an unknown field."""
    found = field_for(kind, field_id)
    return ops_for_type(found.type) if found is not None else ()


def _parse_int(value: str) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True, slots=True)
class Condition:
    """One test on one field of an item."""

    field: str
    op: str = OP_CONTAINS
    value: str = ""
    case_sensitive: bool = False

    def error(self, kind: str) -> str:
        """Why this condition cannot decide anything for *kind*, or ``""``."""
        found = field_for(kind, self.field)
        if found is None:
            return "it looks at something this version does not know"
        if self.op not in ops_for_type(found.type):
            return "its test does not apply to that field"
        if found.type == NUMBER:
            number = _parse_int(self.value)
            if number is None or number < 0:
                unit = f" of {found.unit}" if found.unit else ""
                return f"it needs a whole number{unit}, zero or more"
            return ""
        if found.type == YESNO:
            return "" if self.value in (YES, NO) else "it needs yes or no"
        if not self.value.strip():
            return "it has nothing to look for"
        if self.op in (OP_REGEX, OP_NOT_REGEX):
            try:
                re.compile(self.value)
            except re.error as exc:
                return f"its regular expression cannot be read: {exc}"
        return ""

    def is_usable(self, kind: str) -> bool:
        return not self.error(kind)

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {"field": self.field, "op": self.op, "value": self.value}
        if self.case_sensitive:
            data["case_sensitive"] = True
        return data

    @classmethod
    def from_dict(cls, data: object) -> Condition | None:
        """A stored condition; an unknown field or test is kept (and unusable)."""
        if not isinstance(data, dict):
            return None
        return cls(
            field=str(data.get("field", "") or ""),
            op=str(data.get("op", "") or ""),
            value=str(data.get("value", "") or ""),
            case_sensitive=bool(data.get("case_sensitive", False)),
        )


def _wildcard(value: str) -> str:
    from quill.core.podcasts.models_filters import wildcard_to_regex

    return wildcard_to_regex(value)


def _one_text_matches(condition: Condition, text: str) -> bool:
    flags = 0 if condition.case_sensitive else re.IGNORECASE
    op, value = condition.op, condition.value
    if op in (OP_REGEX, OP_NOT_REGEX):
        try:
            found = re.search(value, text, flags) is not None
        except re.error:
            return False
        return found if op == OP_REGEX else not found
    if op == OP_WILDCARD:
        return re.fullmatch(_wildcard(value), text, flags | re.DOTALL) is not None
    haystack = text if condition.case_sensitive else text.casefold()
    needle = value if condition.case_sensitive else value.casefold()
    if op == OP_CONTAINS:
        return needle in haystack
    if op == OP_NOT_CONTAINS:
        return needle not in haystack
    if op == OP_STARTS:
        return haystack.startswith(needle)
    if op == OP_ENDS:
        return haystack.endswith(needle)
    if op == OP_IS:
        return haystack.strip() == needle.strip()
    return haystack.strip() != needle.strip()  # OP_IS_NOT


_NEGATIVE_TEXT_OPS = frozenset({OP_NOT_CONTAINS, OP_NOT_REGEX, OP_IS_NOT})


def _list_matches(condition: Condition, values: tuple[str, ...]) -> bool:
    """A list test is about any one entry; a negative test means "none of them"."""
    if condition.op in _NEGATIVE_TEXT_OPS:
        positive = {OP_NOT_CONTAINS: OP_CONTAINS, OP_NOT_REGEX: OP_REGEX, OP_IS_NOT: OP_IS}
        flipped = Condition(
            condition.field, positive[condition.op], condition.value, condition.case_sensitive
        )
        return not any(_one_text_matches(flipped, value) for value in values)
    return any(_one_text_matches(condition, value) for value in values)


def matches(condition: Condition, item: ItemFacts) -> bool:
    """Whether *item* passes *condition*. Total: never raises."""
    try:
        if not condition.is_usable(item.ref.kind):
            return False
        found = field_for(item.ref.kind, condition.field)
        if found is None:
            return False
        actual: Fact = item.fact(condition.field)
        if found.type == NUMBER:
            wanted = _parse_int(condition.value)
            if not isinstance(actual, int) or isinstance(actual, bool) or wanted is None:
                return False  # a missing fact never matches a number test
            if condition.op == OP_AT_LEAST:
                return actual >= wanted
            if condition.op == OP_AT_MOST:
                return actual <= wanted
            if condition.op == OP_IS:
                return actual == wanted
            return actual != wanted
        if found.type == YESNO:
            same = bool(actual) == (condition.value == YES)
            return same if condition.op == OP_IS else not same
        if found.type == LIST:
            values = tuple(str(v) for v in actual) if isinstance(actual, tuple) else ()
            return _list_matches(condition, values)
        if found.type == TEXT:
            return _one_text_matches(condition, "" if actual is None else str(actual))
    except Exception:  # noqa: BLE001 - a rule is evaluated in the background; never raise
        return False
    return False


def describe(condition: Condition, kind: str) -> str:
    """The test as a fragment of the rule's sentence: 'Folder is "News"'."""
    found = field_for(kind, condition.field)
    label = found.label if found is not None else (condition.field or "Unknown field")
    phrase = OP_PHRASES.get(condition.op, condition.op or "unknown test")
    if found is not None and found.type == YESNO:
        text = f"{label} {phrase} {condition.value or '?'}"
    elif found is not None and found.type == NUMBER:
        unit = found.unit or ""
        if unit.endswith("s") and str(condition.value).strip() == "1":
            unit = unit[:-1]  # "1 day", not "1 days"
        text = f"{label} {phrase} {condition.value}" + (f" {unit}" if unit else "")
    else:
        text = f'{label} {phrase} "{condition.value}"'
        if condition.case_sensitive:
            text += ", capitals matching"
    error = condition.error(kind)
    if error:
        text += f", which cannot be used: {error}"
    return text


__all__ = [
    "NO",
    "YES",
    "YESNO_OPS",
    "Condition",
    "describe",
    "matches",
    "ops_for",
    "ops_for_type",
]
