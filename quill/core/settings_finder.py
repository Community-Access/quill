"""Find a setting by what it is called, wherever it lives (qc.md X-01, 7.7).

The family's Preferences search began by walking a window's *built* controls.
That answers "where in this window", and nothing else: a page a dialog builds
only when it is first shown, a setting kept in the main window rather than in
Preferences, and a whole settings dialog nobody has opened yet were all
invisible to it, because none of them had controls to walk.

This module is the other half: a **declarative** index. Each app writes down
its settings as :class:`SettingEntry` rows -- the exact visible label, the
place it lives (as a phrase a person can follow), the words people use for it
-- and the search reads those, not the widgets. A window that has not been
built yet is still in the index, because the index never needed the window.

Matching is the one rule the native search already uses (every word of the
query must occur somewhere in what describes the setting, ignoring case), and
a stable ranking on top of it so the setting *called* what you typed comes
before the one that only mentions it in its help.

Never a value: labels, places, descriptions and aliases only. No ``wx``.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol

__all__ = [
    "SettingEntry",
    "match_rank",
    "moved_to",
    "registry_entries",
    "result_label",
    "search_entries",
]


@dataclass(frozen=True, slots=True)
class SettingEntry:
    """One setting, described for searching rather than for drawing.

    ``area`` is where it lives, written to follow the word "in" -- "the Editing
    page of Settings", "the main window's Advanced Options" -- because it is
    both shown beside a result and spoken after the search moves you there.
    ``area`` is empty for a setting in the very window being searched.
    """

    key: str
    label: str
    area: str = ""
    description: str = ""
    aliases: tuple[str, ...] = ()

    def searchable_text(self) -> str:
        """Everything a query may match: never a value."""
        return " ".join((self.label, " ".join(self.aliases), self.description, self.area))


def _words(query: str) -> list[str]:
    return query.casefold().split()


def match_rank(label: str, text: str, query: str) -> int | None:
    """How well *query* matches, lower is better; ``None`` is no match.

    0 -- the label *is* the query; 1 -- the label starts with it; 2 -- every
    word is in the label; 3 -- every word is somewhere in *text* (aliases,
    help, place). An empty query matches nothing: a search box that lists
    every setting before anything is typed is a list nobody asked for.
    """
    words = _words(query)
    if not words:
        return None
    haystack = f"{label} {text}".casefold()
    if not all(word in haystack for word in words):
        return None
    name = label.casefold().replace("&", "").strip()
    phrase = " ".join(words)
    if name.rstrip(":. ") == phrase:
        return 0
    if name.startswith(phrase):
        return 1
    if all(word in name for word in words):
        return 2
    return 3


def search_entries(entries: Iterable[SettingEntry], query: str) -> list[SettingEntry]:
    """The entries matching *query*, best first; ties keep declaration order."""
    ranked: list[tuple[int, int, SettingEntry]] = []
    for position, entry in enumerate(entries):
        rank = match_rank(entry.label, entry.searchable_text(), query)
        if rank is not None:
            ranked.append((rank, position, entry))
    ranked.sort(key=lambda item: (item[0], item[1]))
    return [entry for _rank, _position, entry in ranked]


def result_label(entry: SettingEntry) -> str:
    """How a result reads in the list: the label, then where it lives."""
    return f"{entry.label}, in {entry.area}" if entry.area else entry.label


def moved_to(entry: SettingEntry) -> str:
    """What to say after the search has carried focus somewhere else.

    Only the place. The screen reader says the window title and the focused
    control's name, role and value on its own (GATE-13); the one thing it has
    no way to know is which *part* of a window the setting was found in.
    """
    return f"Moved to {entry.area}." if entry.area else ""


class _Group(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def title(self) -> str: ...


class _Spec(Protocol):
    @property
    def key(self) -> str: ...

    @property
    def label(self) -> str: ...

    @property
    def group(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def keywords(self) -> tuple[str, ...]: ...


def registry_entries(
    groups: Sequence[_Group], specs: Iterable[_Spec], *, area: str = "the {title} page"
) -> list[SettingEntry]:
    """QUILL's settings registry as index rows.

    *area* is formatted with the group's ``title``: "the {title} page" inside
    the Settings dialog, "the {title} page of Settings" from the Preferences
    hub, which has not opened that dialog yet.
    """
    titles = {group.id: group.title for group in groups}
    return [
        SettingEntry(
            key=spec.key,
            label=spec.label,
            area=area.format(title=titles.get(spec.group, spec.group)),
            description=spec.description,
            aliases=tuple(spec.keywords),
        )
        for spec in specs
    ]
