"""More tests an Episode Filter rule can ask, beyond the title and a minimum length.

A rule began (2026-08-28) with two questions: does the title fit a pattern, and
is the episode at least so many minutes long. Real feeds need more than that.
A show's sponsor reads are named only in the show notes; trailers are marked by
the publisher in ``itunes:episodeType`` rather than in the title; a guest you
would rather not hear is in the Podcasting 2.0 ``person`` tags; a back catalogue
re-published last week is old in every way except its date. Each of those is a
:class:`FilterCondition` -- one field, one test, one value -- and a rule holds as
many as it needs (``EpisodeFilterRule.conditions``).

Three rules carry over from the original criteria and are the point of this
module:

* **A missing fact never matches a numeric test.** A feed that does not say how
  long an episode is, or when it was published, or which season it belongs to,
  has not said "zero"; "at most 10 minutes" must not quietly catch every episode
  of a feed that omits ``itunes:duration``.
* **An unusable condition makes its whole rule unusable**, and an unusable rule
  never matches in either mode. A regular expression that does not compile is
  the obvious case; a number test with no number is the other.
* **Nothing here raises into a feed refresh.** Every matcher is total.

Text tests ``search`` rather than ``fullmatch``: "show notes contain sponsor" is
the natural sentence, and a regular expression can still anchor itself with
``^`` and ``$``. The title test on the rule itself keeps its whole-title shape,
because that is what every stored rule already means.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

# -- what a condition can look at -------------------------------------------

FIELD_TITLE = "title"
FIELD_NOTES = "notes"
FIELD_PEOPLE = "people"
FIELD_TYPE = "type"
FIELD_DURATION = "duration"
FIELD_AGE = "age"
FIELD_SEASON = "season"
FIELD_NUMBER = "number"

TEXT_FIELDS = (FIELD_TITLE, FIELD_NOTES, FIELD_PEOPLE)
NUMBER_FIELDS = (FIELD_DURATION, FIELD_AGE, FIELD_SEASON, FIELD_NUMBER)
FIELDS = (*TEXT_FIELDS, FIELD_TYPE, *NUMBER_FIELDS)

#: What each field is called, out loud and in the field chooser.
FIELD_LABELS: dict[str, str] = {
    FIELD_TITLE: "Title",
    FIELD_NOTES: "Show notes",
    FIELD_PEOPLE: "People on the episode",
    FIELD_TYPE: "Episode type",
    FIELD_DURATION: "Length in minutes",
    FIELD_AGE: "Age in days",
    FIELD_SEASON: "Season number",
    FIELD_NUMBER: "Episode number",
}

# -- the tests ----------------------------------------------------------------

OP_CONTAINS = "contains"
OP_NOT_CONTAINS = "not_contains"
OP_STARTS = "starts_with"
OP_ENDS = "ends_with"
OP_IS = "is"
OP_IS_NOT = "is_not"
OP_WILDCARD = "wildcard"
OP_REGEX = "regex"
OP_NOT_REGEX = "not_regex"
OP_AT_LEAST = "at_least"
OP_AT_MOST = "at_most"

TEXT_OPS = (
    OP_CONTAINS,
    OP_NOT_CONTAINS,
    OP_STARTS,
    OP_ENDS,
    OP_IS,
    OP_IS_NOT,
    OP_WILDCARD,
    OP_REGEX,
    OP_NOT_REGEX,
)
NUMBER_OPS = (OP_AT_LEAST, OP_AT_MOST, OP_IS, OP_IS_NOT)
TYPE_OPS = (OP_IS, OP_IS_NOT)

#: The test as a phrase that reads after the field: "Show notes contain ...".
OP_PHRASES: dict[str, str] = {
    OP_CONTAINS: "contains",
    OP_NOT_CONTAINS: "does not contain",
    OP_STARTS: "starts with",
    OP_ENDS: "ends with",
    OP_IS: "is",
    OP_IS_NOT: "is not",
    OP_WILDCARD: "fits the wildcard",
    OP_REGEX: "matches the regular expression",
    OP_NOT_REGEX: "does not match the regular expression",
    OP_AT_LEAST: "is at least",
    OP_AT_MOST: "is at most",
}

#: ``itunes:episodeType``'s three values, in the publisher's vocabulary.
EPISODE_TYPES = ("full", "trailer", "bonus")
EPISODE_TYPE_LABELS: dict[str, str] = {
    "full": "a full episode",
    "trailer": "a trailer",
    "bonus": "a bonus episode",
}


def ops_for(field: str) -> tuple[str, ...]:
    """The tests that make sense for *field*."""
    if field in NUMBER_FIELDS:
        return NUMBER_OPS
    if field == FIELD_TYPE:
        return TYPE_OPS
    return TEXT_OPS


def _parse_int(value: str) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True, slots=True)
class FilterCondition:
    """One test: a field of the episode, a comparison, and a value."""

    field: str = FIELD_NOTES
    op: str = OP_CONTAINS
    value: str = ""
    case_sensitive: bool = False

    @property
    def error(self) -> str:
        """Why this condition cannot decide anything, or ``""`` when it can."""
        if self.field not in FIELDS:
            return "it looks at something this version of Cast does not know"
        if self.op not in ops_for(self.field):
            return "its test does not apply to that field"
        if self.field in NUMBER_FIELDS:
            number = _parse_int(self.value)
            if number is None or number < 0:
                return "it needs a whole number of zero or more"
            return ""
        if self.field == FIELD_TYPE:
            return "" if self.value in EPISODE_TYPES else "it needs full, trailer or bonus"
        if not self.value.strip():
            return "it has nothing to look for"
        if self.op in (OP_REGEX, OP_NOT_REGEX):
            try:
                re.compile(self.value)
            except re.error as exc:
                return f"its regular expression cannot be read: {exc}"
        return ""

    @property
    def is_usable(self) -> bool:
        return not self.error

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {"field": self.field, "op": self.op, "value": self.value}
        if self.case_sensitive:
            data["case_sensitive"] = True
        return data

    @classmethod
    def from_dict(cls, data: object) -> FilterCondition | None:
        """One stored condition, or ``None`` when the entry is not a record.

        An unknown field or test is *kept*, not dropped -- it reads back as an
        unusable condition, which makes its rule match nothing. Dropping it would
        silently widen the rule into one the listener never wrote.
        """
        if not isinstance(data, dict):
            return None
        return cls(
            field=str(data.get("field", "") or ""),
            op=str(data.get("op", "") or ""),
            value=str(data.get("value", "") or ""),
            case_sensitive=bool(data.get("case_sensitive", False)),
        )


# -- reading an episode ---------------------------------------------------------


def _text_of(field: str, episode: Any) -> str:
    if field == FIELD_TITLE:
        return str(getattr(episode, "title", "") or "")
    if field == FIELD_NOTES:
        return str(getattr(episode, "description", "") or "")
    tags = getattr(episode, "tags", None)
    people = getattr(tags, "people", None) or []
    return "\n".join(str(getattr(person, "name", "") or "") for person in people)


def _number_of(field: str, episode: Any, now: datetime) -> int | None:
    """The episode's number for *field*, or ``None`` when the feed did not say."""
    if field == FIELD_DURATION:
        seconds = int(getattr(episode, "duration_seconds", 0) or 0)
        return seconds // 60 if seconds > 0 else None
    if field == FIELD_SEASON:
        season = int(getattr(episode, "season", 0) or 0)
        return season if season > 0 else None
    if field == FIELD_NUMBER:
        number = int(getattr(episode, "episode_number", 0) or 0)
        return number if number > 0 else None
    published = str(getattr(episode, "published", "") or "")
    if not published:
        return None
    try:
        moment = parsedate_to_datetime(published)
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return max(0, (now - moment).days)


def _text_matches(condition: FilterCondition, text: str) -> bool:
    flags = 0 if condition.case_sensitive else re.IGNORECASE
    op, value = condition.op, condition.value
    if op in (OP_REGEX, OP_NOT_REGEX):
        try:
            found = re.search(value, text, flags) is not None
        except re.error:
            return False
        return found if op == OP_REGEX else not found
    if op == OP_WILDCARD:
        # Imported here: models_filters imports this module for the rule's
        # ``conditions`` field, so a top-level import would be a cycle.
        from quill.core.podcasts.models_filters import wildcard_to_regex

        # Whole-text, like the rule's own title wildcard: one wildcard
        # convention, whichever box it was typed in.
        return re.fullmatch(wildcard_to_regex(value), text, flags | re.DOTALL) is not None
    haystack = text if condition.case_sensitive else text.casefold()
    needle = value if condition.case_sensitive else value.casefold()
    if condition.field == FIELD_PEOPLE and op in (OP_IS, OP_IS_NOT, OP_STARTS, OP_ENDS):
        # A person test is about any one person, not the joined list.
        names = [name for name in haystack.split("\n") if name]
        hit = any(
            (name == needle)
            if op in (OP_IS, OP_IS_NOT)
            else (name.startswith(needle) if op == OP_STARTS else name.endswith(needle))
            for name in names
        )
        return (not hit) if op == OP_IS_NOT else hit
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


def condition_matches(
    condition: FilterCondition, episode: Any, *, now: datetime | None = None
) -> bool:
    """Whether *episode* passes *condition*. Total: never raises."""
    if not condition.is_usable:
        return False
    if condition.field == FIELD_TYPE:
        # The iTunes default: an item that does not say is a full episode.
        kind = str(getattr(episode, "episode_type", "") or "").strip().lower() or "full"
        same = kind == condition.value
        return same if condition.op == OP_IS else not same
    if condition.field in NUMBER_FIELDS:
        actual = _number_of(condition.field, episode, now or datetime.now(UTC))
        wanted = _parse_int(condition.value)
        if actual is None or wanted is None:
            return False  # a missing fact never matches a numeric test
        if condition.op == OP_AT_LEAST:
            return actual >= wanted
        if condition.op == OP_AT_MOST:
            return actual <= wanted
        if condition.op == OP_IS:
            return actual == wanted
        return actual != wanted
    return _text_matches(condition, _text_of(condition.field, episode))


# -- saying it --------------------------------------------------------------------


def describe_condition(condition: FilterCondition) -> str:
    """One test as a sentence fragment: "Show notes contain 'sponsor'"."""
    field = FIELD_LABELS.get(condition.field, condition.field or "Unknown field")
    phrase = OP_PHRASES.get(condition.op, condition.op or "unknown test")
    if condition.field == FIELD_TYPE:
        value = EPISODE_TYPE_LABELS.get(condition.value, condition.value)
        text = f"{field} {phrase} {value}"
    elif condition.field in NUMBER_FIELDS:
        text = f"{field} {phrase} {condition.value}"
    else:
        text = f'{field} {phrase} "{condition.value}"'
        if condition.case_sensitive:
            text += ", capitals matching"
    error = condition.error
    if error:
        text += f" -- not usable: {error}"
    return text


__all__ = [
    "EPISODE_TYPES",
    "EPISODE_TYPE_LABELS",
    "FIELDS",
    "FIELD_AGE",
    "FIELD_DURATION",
    "FIELD_LABELS",
    "FIELD_NOTES",
    "FIELD_NUMBER",
    "FIELD_PEOPLE",
    "FIELD_SEASON",
    "FIELD_TITLE",
    "FIELD_TYPE",
    "NUMBER_FIELDS",
    "NUMBER_OPS",
    "OP_AT_LEAST",
    "OP_AT_MOST",
    "OP_CONTAINS",
    "OP_ENDS",
    "OP_IS",
    "OP_IS_NOT",
    "OP_NOT_CONTAINS",
    "OP_NOT_REGEX",
    "OP_PHRASES",
    "OP_REGEX",
    "OP_STARTS",
    "OP_WILDCARD",
    "TEXT_FIELDS",
    "TEXT_OPS",
    "TYPE_OPS",
    "FilterCondition",
    "condition_matches",
    "describe_condition",
    "ops_for",
]
