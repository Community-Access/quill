""" "What can I say here?" (command-key.md 11.1), wx-free.

The list is exactly the candidate list a request would get: this window's
commands that can run right now. Most used first, then by menu group, each with
its spoken name, one example and its key. A filter ("what can I say about
bookmarks") narrows by the words in titles, aliases, examples and groups.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from quill.core.command_catalogue.resolver import Candidate
from quill.core.command_catalogue.words import content_words, similar

__all__ = ["HelpRow", "count_line", "help_rows", "nothing_about_line"]


@dataclass(frozen=True, slots=True)
class HelpRow:
    """One row of the list: a group heading (no candidate) or a command."""

    label: str
    candidate: Candidate | None = None

    @property
    def is_heading(self) -> bool:
        return self.candidate is None


def _matches(candidate: Candidate, wanted: tuple[str, ...]) -> bool:
    spec = candidate.spec
    have = {word for phrase in (*spec.words(), spec.group) for word in content_words(phrase)}
    return all(any(similar(word, own) for own in have) for word in wanted)


def _label(candidate: Candidate) -> str:
    spec = candidate.spec
    parts = [spec.title]
    if spec.examples:
        parts.append(f"Say '{spec.examples[0]}'")
    if candidate.key:
        parts.append(candidate.key)
    return ". ".join(parts) + "."


def help_rows(
    candidates: Sequence[Candidate],
    *,
    help_filter: str = "",
    usage: Mapping[str, int] | None = None,
) -> tuple[HelpRow, ...]:
    """The list's rows, headings included. Empty when the filter matched nothing."""
    wanted = content_words(help_filter)
    chosen = [item for item in candidates if not wanted or _matches(item, wanted)]
    counts = usage or {}
    groups: dict[str, list[Candidate]] = {}
    for item in chosen:
        groups.setdefault(item.spec.group or "Other", []).append(item)

    def group_order(name: str) -> tuple[int, str]:
        return (-max(counts.get(item.spec.id, 0) for item in groups[name]), name)

    rows: list[HelpRow] = []
    for name in sorted(groups, key=group_order):
        members = sorted(
            groups[name], key=lambda item: (-counts.get(item.spec.id, 0), item.spec.title)
        )
        rows.append(HelpRow(f"{name}, {len(members)}"))
        rows.extend(HelpRow(_label(item), item) for item in members)
    return tuple(rows)


def count_line(rows: Sequence[HelpRow]) -> str:
    """The one thing the app says when the list opens: the count only it knows."""
    commands = sum(1 for row in rows if not row.is_heading)
    groups = sum(1 for row in rows if row.is_heading)
    things = "thing" if commands == 1 else "things"
    if groups <= 1:
        return f"{commands} {things} you can do here."
    return f"{commands} {things} you can do here, in {groups} groups."


def nothing_about_line(help_filter: str) -> str:
    return f"Nothing about {help_filter} here. Here is everything."
