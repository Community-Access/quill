"""Filtering on every attribute: the Filter menu, Show Only and Hide, and Group By (PRD 17).

The list's filter is one query (section 17.1). Four ways write it, and every
one of them goes through here, so they stay in step (GH-R-050):

1. the filter box (the frame's own);
2. the Filter Builder (:mod:`quill.core.github.filter_builder`);
3. the Filter menu's toggles, :data:`TOGGLES`: each a checked row whose
   qualifier is in the query or not (:func:`toggle`, :func:`active`), named
   in the window title and status bar (:func:`toggle_words`);
4. Show Only and Hide on any cell (:func:`cell_choices`, :func:`show_only`),
   the fastest filter there is, which teaches the syntax as it goes.

Attributes GitHub's search does not index (a pull request's conflicts) are
filtered over the loaded rows (:func:`local_only`); :func:`local_status` is
the honest status line that says so. :func:`group_rows` is View > Group By:
the groups become tree nodes.

wx-free and strict-typed.
"""

from __future__ import annotations

import datetime as _dt
import shlex
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

__all__ = [
    "GROUP_FIELDS",
    "LOCAL_QUALIFIERS",
    "TOGGLES",
    "Toggle",
    "active",
    "clear_toggles",
    "cell_choices",
    "group_rows",
    "local_only",
    "local_status",
    "matches_local",
    "show_only",
    "toggle",
    "toggle_words",
]


@dataclass(frozen=True)
class Toggle:
    """One Filter menu row: its id, its label, and the qualifier it writes.

    A qualifier ending in ``:`` asks for a value (Assigned To...); ``{week}``
    is replaced by the date a week ago.
    """

    key: str
    label: str
    qualifier: str
    words: str
    local: bool = False


TOGGLES: tuple[Toggle, ...] = (
    Toggle("assigned_me", "Assigned to &Me", "assignee:@me", "assigned to me"),
    Toggle("assigned_to", "Assigned &To...", "assignee:", "assigned to {value}"),
    Toggle("opened_me", "&Opened by Me", "author:@me", "opened by me"),
    Toggle("opened_by", "Opened &By...", "author:", "opened by {value}"),
    Toggle("mentions_me", "Me&ntions Me", "mentions:@me", "mentions me"),
    Toggle(
        "review_me", "Review &Requested from Me", "review-requested:@me", "review requested from me"
    ),
    Toggle("reviewed_me", "Re&viewed by Me", "reviewed-by:@me", "reviewed by me"),
    Toggle("no_assignee", "No &Assignee", "no:assignee", "no assignee"),
    Toggle("no_milestone", "No M&ilestone", "no:milestone", "no milestone"),
    Toggle("no_label", "No &Label", "no:label", "no label"),
    Toggle("no_project", "No &Project", "no:project", "no project"),
    Toggle("no_type", "No T&ype", "no:type", "no type"),
    Toggle("drafts", "&Drafts", "draft:true", "drafts"),
    Toggle("conflicts", "Has &Conflicts", "conflicts:true", "has conflicts", local=True),
    Toggle("checks_failing", "Checks &Failing", "status:failure", "checks failing"),
    Toggle("updated_week", "&Updated This Week", "updated:>={week}", "updated this week"),
)
_BY_KEY = {t.key: t for t in TOGGLES}

#: Qualifiers GitHub's search cannot answer: filtered over the loaded rows.
LOCAL_QUALIFIERS: frozenset[str] = frozenset({"conflicts", "size", "duration", "downloads"})


def _tokens(text: str) -> list[str]:
    try:
        return shlex.split(text, posix=True)
    except ValueError:
        return text.split()


def _join(tokens: Sequence[str]) -> str:
    return " ".join(f'"{t}"' if " " in t and ":" not in t else _quote(t) for t in tokens)


def _quote(token: str) -> str:
    key, sep, value = token.partition(":")
    if sep and " " in value:
        return f'{key}:"{value}"'
    return token


def _week(today: _dt.date) -> str:
    return (today - _dt.timedelta(days=7)).isoformat()


def _matches(token: str, item: Toggle) -> bool:
    if item.qualifier.endswith(":"):
        return token.startswith(item.qualifier) and token != item.qualifier + "@me"
    if "{week}" in item.qualifier:
        return token.startswith("updated:>=")
    return token == item.qualifier


def active(text: str) -> dict[str, str]:
    """The toggles on in *text*, each with its value ("" for a fixed qualifier)."""
    found: dict[str, str] = {}
    for token in _tokens(text):
        for item in TOGGLES:
            if item.key not in found and _matches(token, item):
                found[item.key] = token.partition(":")[2] if item.qualifier.endswith(":") else ""
    return found


def toggle(text: str, key: str, value: str = "", *, today: _dt.date | None = None) -> str:
    """*text* with the toggle *key* turned on (with *value*) or, when it is on, off."""
    item = _BY_KEY[key]
    tokens = _tokens(text)
    if any(_matches(t, item) for t in tokens):
        return _join([t for t in tokens if not _matches(t, item)])
    qualifier = item.qualifier.replace("{week}", _week(today or _dt.date.today()))
    if qualifier.endswith(":"):
        if not value:
            return _join(tokens)
        qualifier += value
    return _join([*tokens, qualifier])


def clear_toggles(text: str) -> str:
    """Clear These Filters: every toggle off, anything else typed kept."""
    return _join([t for t in _tokens(text) if not any(_matches(t, item) for item in TOGGLES)])


def toggle_words(text: str) -> str:
    """What is on, for the title and status bar: "assigned to me, no milestone"."""
    on = active(text)
    return ", ".join(_BY_KEY[key].words.replace("{value}", value) for key, value in on.items())


# ---------------------------------------------------------------------------
# Show Only and Hide on a cell (17.1, way 4)
# ---------------------------------------------------------------------------


def _value_token(key: str, value: str) -> str:
    return f'{key}:"{value}"' if " " in value else f"{key}:{value}"


def cell_choices(row: Mapping[str, object]) -> list[tuple[str, str]]:
    """Each value in a row as (qualifier, words): ("label:bug", "label bug")."""
    found: list[tuple[str, str]] = []
    for key, attribute in (
        ("labels", "label"),
        ("assignees", "assignee"),
        ("author", "author"),
        ("milestone", "milestone"),
        ("state", "state"),
        ("issue_type", "type"),
        ("repo", "repo"),
        ("base", "base"),
        ("head", "head"),
    ):
        value = row.get(key)
        values = value if isinstance(value, tuple) else (value,) if value else ()
        for item in values:
            text = str(item)
            if text:
                found.append((_value_token(attribute, text), f"{attribute} {text}"))
    return found


def show_only(text: str, qualifier: str, *, hide: bool = False) -> str:
    """*text* narrowed to *qualifier* (Show Only) or with it excluded (Hide)."""
    token = f"-{qualifier}" if hide else qualifier
    opposite = qualifier if hide else f"-{qualifier}"
    tokens = [t for t in _tokens(text) if _quote(t) not in (opposite, token)]
    return " ".join([*(_quote(t) for t in tokens), token])


# ---------------------------------------------------------------------------
# Local filtering (17.3)
# ---------------------------------------------------------------------------


def local_only(text: str) -> tuple[str, list[tuple[str, str, bool]]]:
    """Split *text* into what GitHub is asked and what is checked here.

    Returns the server query and the local conditions as (key, value, negated).
    """
    server: list[str] = []
    local: list[tuple[str, str, bool]] = []
    for token in _tokens(text):
        negated = token.startswith("-")
        key, sep, value = token.lstrip("-").partition(":")
        if sep and key in LOCAL_QUALIFIERS:
            local.append((key, value, negated))
        else:
            server.append(token)
    return _join(server), local


def matches_local(
    values: Mapping[str, object], conditions: Sequence[tuple[str, str, bool]]
) -> bool:
    """Whether a row's values satisfy the local conditions."""
    for key, value, negated in conditions:
        found = values.get(key)
        if key == "conflicts":
            hit = (str(found) == "dirty") == (value.lower() in ("true", "yes"))
        elif value.startswith((">", "<")):
            try:
                number = float(str(found or 0).split()[0])
                limit = float(value.lstrip("<>="))
            except ValueError:
                hit = False
            else:
                hit = number >= limit if value.startswith(">") else number <= limit
        else:
            hit = str(found).casefold() == value.casefold()
        if hit == negated:
            return False
    return True


def local_status(loaded: int, shown: int, *, complete: bool) -> str:
    """The honest status line for a local filter (17.3)."""
    if complete:
        return f"Filtered locally: {shown} of all {loaded}."
    return f"Filtered locally: {shown} of {loaded} loaded. Load All to be sure."


# ---------------------------------------------------------------------------
# Group By (17.4)
# ---------------------------------------------------------------------------

GROUP_FIELDS: tuple[tuple[str, str], ...] = (
    ("label", "Label"),
    ("milestone", "Milestone"),
    ("assignee", "Assignee"),
    ("author", "Author"),
    ("type", "Type"),
    ("state", "State"),
    ("repository", "Repository"),
    ("review", "Review State"),
)


def group_rows[T](
    rows: Sequence[T], field: str, values: Callable[[T], Sequence[str]]
) -> list[tuple[str, list[T]]]:
    """The groups for View > Group By: (name, rows), names sorted, "None" last.

    A row with several values (two labels) is in each of their groups, as
    GitHub's own grouping does.
    """
    groups: dict[str, list[T]] = {}
    for row in rows:
        found = [v for v in values(row) if v] or ["None"]
        for name in found:
            groups.setdefault(name, []).append(row)
    names = sorted((n for n in groups if n != "None"), key=str.casefold)
    if "None" in groups:
        names.append("None")
    return [(f"{name}", groups[name]) for name in names]
