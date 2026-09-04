"""Tidying an episode title for reading, without renaming anything.

An accessibility feature that looks cosmetic and is not.

A great many podcasts prefix every episode title with the same thing:
``Ep. 412 -``, ``MyShow Presents:``, ``[Bonus]``. Read by eye, that is noise you
skip past. Read by ear it is the **first thing said on every row**, two hundred
times, and it destroys first-letter navigation entirely: arrowing to "S" in a
list where every row starts with "Ep." finds nothing, because the part of the
title that differs is never where the reader starts.

So: patterns removed **when a title is shown and spoken**. The feed's own title
is untouched, nothing is renamed, and Rename... (which really does rename) is a
different verb in a different place. Turning a rule off puts the words back.

Three kinds, because the three cover everything real feeds do and each one is
predictable in a way "a regular expression over the whole title" is not:

* **prefix** -- removed from the start, and only from the start.
* **suffix** -- removed from the end. ``| Sponsored by X`` lives here.
* **anywhere** -- the first occurrence, wherever it is. The escape hatch.

Wildcards are the same vocabulary Episode Filters uses (``*`` any text, ``?``
one character, everything else literal) with one deliberate difference: ``*`` is
**non-greedy** here. A greedy star in ``Ep. *: `` would eat a title containing a
second colon down to nothing, and a cleanup rule that can empty a title is a
cleanup rule that loses an episode.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from quill.core.podcasts.models_filters import wildcard_to_regex

KIND_PREFIX = "prefix"
KIND_SUFFIX = "suffix"
KIND_ANYWHERE = "anywhere"
KINDS: tuple[str, ...] = (KIND_PREFIX, KIND_SUFFIX, KIND_ANYWHERE)

KIND_LABELS: dict[str, str] = {
    KIND_PREFIX: "At the start",
    KIND_SUFFIX: "At the end",
    KIND_ANYWHERE: "Anywhere in the title",
}


@dataclass(frozen=True, slots=True)
class TitleRule:
    """One thing to take out of this podcast's episode titles."""

    pattern: str
    kind: str = KIND_PREFIX
    enabled: bool = True

    @property
    def is_usable(self) -> bool:
        return self.enabled and bool(self.pattern.strip())

    def to_dict(self) -> dict[str, object]:
        return {"pattern": self.pattern, "kind": self.kind, "enabled": self.enabled}

    @classmethod
    def from_dict(cls, data: object) -> TitleRule | None:
        if not isinstance(data, dict):
            return None
        pattern = str(data.get("pattern", "") or "")
        if not pattern.strip():
            return None
        kind = str(data.get("kind", KIND_PREFIX))
        return cls(
            pattern=pattern,
            kind=kind if kind in KINDS else KIND_PREFIX,
            enabled=bool(data.get("enabled", True)),
        )

    def describe(self) -> str:
        """The row, spoken: what is removed, then from where, then its state.

        The pattern first because it is what tells two rules apart, and the
        state last but never omitted -- a rules list where you cannot hear
        which rules are on is a list you have to open each row to read.
        """
        where = KIND_LABELS.get(self.kind, KIND_LABELS[KIND_PREFIX]).lower()
        state = "on" if self.enabled else "off"
        return f"Remove {self.pattern!r} {where}. Currently {state}."


def _source(rule: TitleRule) -> str:
    """The rule's pattern as an anchored, non-greedy regular expression."""
    body = wildcard_to_regex(rule.pattern).replace(".*", ".*?")
    if rule.kind == KIND_PREFIX:
        return f"^{body}"
    if rule.kind == KIND_SUFFIX:
        return f"{body}$"
    return body


def apply_rules(title: str, rules: tuple[TitleRule, ...] | list[TitleRule]) -> str:
    """*title* with every usable rule applied, in order.

    **Never returns an empty title.** A rule set that would remove everything
    leaves the title exactly as the feed published it: an episode whose row
    reads as nothing at all is worse than one that reads as noise, and it is
    the only failure mode this feature has.
    """
    cleaned = title
    for rule in rules:
        if not rule.is_usable:
            continue
        try:
            cleaned = re.sub(_source(rule), "", cleaned, count=1)
        except re.error:
            continue
    cleaned = " ".join(cleaned.split()).strip(" -:|,.–—")
    return cleaned or title


def preview(titles: list[str], rules: tuple[TitleRule, ...] | list[TitleRule]) -> list[str]:
    """``"before -> after"`` for each title a rule set would change.

    Only the ones that change: a preview that lists forty unchanged titles has
    buried the three that matter.
    """
    rows: list[str] = []
    for title in titles:
        cleaned = apply_rules(title, rules)
        if cleaned != title:
            rows.append(f"{title} -> {cleaned}")
    return rows


def preview_summary(titles: list[str], rules: tuple[TitleRule, ...] | list[TitleRule]) -> str:
    """What the preview says, counted."""
    if not titles:
        return "Nothing to preview: this podcast has no stored episodes yet."
    changed = len(preview(titles, rules))
    if not changed:
        return f"None of the {len(titles)} newest titles would change."
    return (
        f"{changed} of the {len(titles)} newest titles would change. "
        "The feed's own titles are not altered."
    )


def rules_from_stored(value: object) -> tuple[TitleRule, ...]:
    """Stored rules, made safe. Anything unreadable reads as no rules."""
    if not isinstance(value, (list, tuple)):
        return ()
    rules = [TitleRule.from_dict(entry) for entry in value]
    return tuple(rule for rule in rules if rule is not None)


def rules_to_stored(rules: tuple[TitleRule, ...] | list[TitleRule]) -> list[dict[str, object]]:
    return [rule.to_dict() for rule in rules]


__all__ = [
    "KINDS",
    "KIND_ANYWHERE",
    "KIND_LABELS",
    "KIND_PREFIX",
    "KIND_SUFFIX",
    "TitleRule",
    "apply_rules",
    "preview",
    "preview_summary",
    "rules_from_stored",
    "rules_to_stored",
]
