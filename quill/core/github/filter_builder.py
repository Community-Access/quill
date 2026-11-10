"""The Filter Builder: every attribute, an operator, a value, written as GitHub's syntax (PRD 17.2).

One row per condition: attribute, operator, value. The builder lists every
attribute of the list's row type (:data:`ATTRIBUTES`, Appendix C's Filter
column for issues and pull requests), offers the operators that fit its type
(:data:`OPERATORS`), and fills the value from the repository: labels,
milestones, people, types, branches and teams, with "Me" for every person
field (GH-R-052). OK writes the query into the filter box, so people learn the
syntax by watching it appear:

- any of and none of become GitHub's comma and minus forms (``label:bug,ui``,
  ``-label:docs``);
- has none is ``no:label``, has any ``-no:label``, for every list attribute;
- dates take before, after, between and "in the last n days"; numbers more
  than, less than and between;
- Or between groups, which GitHub's issue search allows, writes ``OR`` and
  brackets (GH-R-054);
- sort and order are part of it: created, updated, comments, each reaction,
  interactions.

wx-free and strict-typed.
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Sequence
from dataclasses import dataclass

__all__ = [
    "ATTRIBUTES",
    "OPERATORS",
    "SORTS",
    "BuilderAttribute",
    "BuilderRow",
    "attribute",
    "describe_row",
    "render_query",
    "render_row",
    "rows_from_query",
]


@dataclass(frozen=True)
class BuilderAttribute:
    """One attribute of a row type: its qualifier, label, type and where values come from."""

    key: str
    label: str
    kind: str
    """``person``, ``list``, ``choice``, ``date``, ``number``, ``text`` or ``flag``."""
    source: str = ""
    """Where the value picker fills from: ``labels``, ``milestones``, ``people``..."""
    choices: tuple[str, ...] = ()
    local: bool = False


_PERSON, _LIST, _CHOICE, _DATE, _NUMBER, _TEXT = (
    "person",
    "list",
    "choice",
    "date",
    "number",
    "text",
)

#: Every attribute GitHub's issue and pull request search filters on (17.3).
ATTRIBUTES: tuple[BuilderAttribute, ...] = (
    BuilderAttribute(
        "is",
        "State",
        _CHOICE,
        choices=("open", "closed", "merged", "unmerged", "draft", "locked", "unlocked"),
    ),
    BuilderAttribute(
        "reason", "State reason", _CHOICE, choices=("completed", "not planned", "duplicate")
    ),
    BuilderAttribute("type", "Kind or issue type", _CHOICE, "types", ("issue", "pr")),
    BuilderAttribute("label", "Label", _LIST, "labels"),
    BuilderAttribute("milestone", "Milestone", _LIST, "milestones"),
    BuilderAttribute("assignee", "Assignee", _PERSON, "people"),
    BuilderAttribute("author", "Author", _PERSON, "people"),
    BuilderAttribute("mentions", "Mentions", _PERSON, "people"),
    BuilderAttribute("commenter", "Commenter", _PERSON, "people"),
    BuilderAttribute("involves", "Involves", _PERSON, "people"),
    BuilderAttribute("team", "Team mentioned", _LIST, "teams"),
    BuilderAttribute("project", "Project", _LIST, "projects"),
    BuilderAttribute("parent-issue", "Parent issue", _TEXT),
    BuilderAttribute(
        "has", "Has", _CHOICE, choices=("sub-issues", "parent-issue", "blocked-by", "blocking")
    ),
    BuilderAttribute("linked", "Linked", _CHOICE, choices=("pr", "issue")),
    BuilderAttribute("created", "Created", _DATE),
    BuilderAttribute("updated", "Updated", _DATE),
    BuilderAttribute("closed", "Closed", _DATE),
    BuilderAttribute("merged", "Merged", _DATE),
    BuilderAttribute("comments", "Comments", _NUMBER),
    BuilderAttribute("reactions", "Reactions", _NUMBER),
    BuilderAttribute("interactions", "Interactions", _NUMBER),
    BuilderAttribute("archived", "Repository archived", _CHOICE, choices=("true", "false")),
    BuilderAttribute("draft", "Draft", _CHOICE, choices=("true", "false")),
    BuilderAttribute(
        "review",
        "Review state",
        _CHOICE,
        choices=("none", "required", "approved", "changes_requested"),
    ),
    BuilderAttribute("review-requested", "Review requested from", _PERSON, "people"),
    BuilderAttribute("team-review-requested", "Review requested from team", _LIST, "teams"),
    BuilderAttribute("reviewed-by", "Reviewed by", _PERSON, "people"),
    BuilderAttribute("base", "Into branch", _LIST, "branches"),
    BuilderAttribute("head", "From branch", _LIST, "branches"),
    BuilderAttribute("status", "Checks", _CHOICE, choices=("success", "failure", "pending")),
    BuilderAttribute("language", "Language", _TEXT),
    BuilderAttribute("in", "Words in", _CHOICE, choices=("title", "body", "comments")),
    BuilderAttribute("conflicts", "Has conflicts", _CHOICE, choices=("true", "false"), local=True),
)
_BY_KEY = {item.key: item for item in ATTRIBUTES}

#: The operators each kind of attribute offers.
OPERATORS: dict[str, tuple[str, ...]] = {
    _PERSON: ("is", "is not", "any of", "none of", "has none", "has any"),
    _LIST: ("is", "is not", "any of", "none of", "has none", "has any"),
    _CHOICE: ("is", "is not"),
    _DATE: ("after", "before", "between", "in the last n days"),
    _NUMBER: ("more than", "less than", "between", "is"),
    _TEXT: ("is", "is not", "contains"),
}

#: Sort orders the builder offers: (words, GitHub's sort qualifier).
SORTS: tuple[tuple[str, str], ...] = (
    ("Newest", "sort:created-desc"),
    ("Oldest", "sort:created-asc"),
    ("Recently updated", "sort:updated-desc"),
    ("Least recently updated", "sort:updated-asc"),
    ("Most comments", "sort:comments-desc"),
    ("Fewest comments", "sort:comments-asc"),
    ("Most reactions", "sort:reactions-desc"),
    ("Most thumbs up", "sort:reactions-+1-desc"),
    ("Most hearts", "sort:reactions-heart-desc"),
    ("Most interactions", "sort:interactions-desc"),
)

_NO = {
    "label": "label",
    "milestone": "milestone",
    "assignee": "assignee",
    "project": "project",
    "type": "type",
    "team": "team",
}


def attribute(key: str) -> BuilderAttribute:
    return _BY_KEY[key]


@dataclass(frozen=True)
class BuilderRow:
    """One condition: attribute key, operator words, values (one or more), and its group."""

    key: str
    operator: str
    values: tuple[str, ...] = ()
    group: int = 0


def _value(text: str) -> str:
    word = "@me" if text in ("Me", "me") else text
    return f'"{word}"' if " " in word else word


def render_row(row: BuilderRow, *, today: _dt.date | None = None) -> str:
    """One condition as GitHub's syntax."""
    key, op, values = row.key, row.operator, [v for v in row.values if v]
    first = values[0] if values else ""
    if op == "has none":
        return f"no:{_NO.get(key, key)}"
    if op == "has any":
        return f"-no:{_NO.get(key, key)}"
    if op == "is":
        return f"{key}:{_value(first)}"
    if op == "is not":
        return f"-{key}:{_value(first)}"
    if op == "any of":
        return f"{key}:" + ",".join(_value(v) for v in values)
    if op == "none of":
        return " ".join(f"-{key}:{_value(v)}" for v in values)
    if op in ("after", "more than"):
        return f"{key}:>{first}"
    if op in ("before", "less than"):
        return f"{key}:<{first}"
    if op == "between":
        second = values[1] if len(values) > 1 else first
        return f"{key}:{first}..{second}"
    if op == "in the last n days":
        days = int(first or 0)
        since = (today or _dt.date.today()) - _dt.timedelta(days=days)
        return f"{key}:>={since.isoformat()}"
    if op == "contains":
        return (
            f"{_value(first)} in:{key}"
            if key in ("title", "body", "comments")
            else (f"{key}:{_value(first)}")
        )
    return f"{key}:{_value(first)}"


def render_query(
    rows: Sequence[BuilderRow], sort: str = "", *, today: _dt.date | None = None
) -> str:
    """Every condition, groups joined by OR (in brackets when there are several)."""
    groups: dict[int, list[str]] = {}
    for row in rows:
        groups.setdefault(row.group, []).append(render_row(row, today=today))
    parts = [" ".join(found) for _g, found in sorted(groups.items())]
    if len(parts) > 1:
        text = " OR ".join(f"({part})" for part in parts)
    else:
        text = parts[0] if parts else ""
    return f"{text} {sort}".strip()


def describe_row(row: BuilderRow) -> str:
    """The row as the builder's list reads it: "Label is any of bug, ui"."""
    label = _BY_KEY[row.key].label if row.key in _BY_KEY else row.key
    values = ", ".join("Me" if v == "@me" else v for v in row.values)
    group = f" (group {row.group + 1})" if row.group else ""
    return f"{label} {row.operator} {values}".strip() + group


def rows_from_query(text: str) -> list[BuilderRow]:
    """What the builder can read back from a typed query (the rest stays as typed)."""
    import shlex

    try:
        tokens = shlex.split(text)
    except ValueError:
        tokens = text.split()
    rows: list[BuilderRow] = []
    for token in tokens:
        negated = token.startswith("-")
        key, sep, value = token.lstrip("-").partition(":")
        if not sep:
            continue
        if key == "no":
            rows.append(BuilderRow(value, "has any" if negated else "has none"))
        elif key in _BY_KEY:
            if value.startswith(">="):
                rows.append(BuilderRow(key, "after", (value[2:],)))
            elif value.startswith(">"):
                op = "more than" if _BY_KEY[key].kind == _NUMBER else "after"
                rows.append(BuilderRow(key, op, (value[1:],)))
            elif value.startswith("<"):
                op = "less than" if _BY_KEY[key].kind == _NUMBER else "before"
                rows.append(BuilderRow(key, op, (value[1:],)))
            elif ".." in value:
                rows.append(BuilderRow(key, "between", tuple(value.split("..", 1))))
            elif "," in value and not negated:
                rows.append(BuilderRow(key, "any of", tuple(value.split(","))))
            else:
                rows.append(BuilderRow(key, "is not" if negated else "is", (value,)))
    return rows
