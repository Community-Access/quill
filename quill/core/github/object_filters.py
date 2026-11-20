"""Filter qualifiers for every Workbench list, checked here over the loaded rows (PRD 17, App. C).

Issues and pull requests send their qualifiers to GitHub's search
(:mod:`quill.core.github.filter_builder`), and a Search node sends the whole
filter box. Every other list -- branches, tags, commits, releases, runs,
workflows, and the Explore-loaded lists -- is read whole, so its qualifiers
are answered here, over the rows already loaded: ``name:release-*``,
``protected:true``, ``-conclusion:success``, ``created:>2026-01-01``,
``ahead:>=3``, ``no:repo``.

:data:`LOCAL` names, by the action table's row type, each qualifier a list
answers and the row attribute it reads. Appendix C's map
(:mod:`quill.core.github.appendix_c_rows`) is checked against this table, so
a qualifier the PRD promises is either answered, sent to GitHub's search, or
listed as not yet with its reason; and a qualifier here that names an
attribute the row does not have fails the gate.

wx-free and strict-typed.
"""

from __future__ import annotations

import fnmatch
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

from quill.core.workbench.filters import Condition, Operator

__all__ = [
    "EXPLORE_ROW_TYPES",
    "LOCAL",
    "ROW_CLASSES",
    "Qualifier",
    "filter_note",
    "filter_rows",
    "matches",
    "qualifiers_for",
    "value_of",
]

TEXT, WORDS, LIST, FLAG, NUMBER, DATE = "text", "words", "list", "flag", "number", "date"


@dataclass(frozen=True)
class Qualifier:
    """One ``key:value`` a list can be filtered on, and the row attribute it reads.

    *kind* decides how a value is compared: ``text`` is equal, ignoring case,
    or a pattern with ``*``; ``words`` contains; ``list`` holds one equal
    item; ``flag`` is true or false; ``number`` and ``date`` take ``>``,
    ``<``, ``>=``, ``<=`` and ``a..b``. *field* is an attribute of the row, or
    a name in :data:`_DERIVED` starting ``@``.
    """

    key: str
    label: str
    kind: str
    field: str


def _q(key: str, label: str, kind: str, field: str = "") -> Qualifier:
    return Qualifier(key, label, kind, field or key)


#: Each typed row class, by its row type ("module:Class"): the gate reads its fields.
ROW_CLASSES: dict[str, str] = {
    "branch": "quill.core.github.items_provider:GitHubBranch",
    "tag": "quill.core.github.items_provider:GitHubTag",
    "commit": "quill.core.github.items_provider:GitHubCommit",
    "release": "quill.core.github.items_provider:GitHubRelease",
    "release_asset": "quill.core.github.items_provider:GitHubReleaseAsset",
    "workflow": "quill.core.github.workflows:GitHubWorkflow",
    "run": "quill.core.github.workflow_models:GitHubWorkflowRun",
}
#: Every other list row is an Explore row.
EXPLORE_ROW = "quill.core.github.explore_models:ExploreRow"

_EXPLORE: tuple[Qualifier, ...] = (
    _q("name", "Name", TEXT, "@name"),
    _q("repo", "Repository", TEXT),
    _q("owner", "Owner", TEXT, "@owner"),
    _q("updated", "Updated", DATE, "updated_at"),
)

#: Row types whose rows are Explore rows (the Explore and local loaders').
EXPLORE_ROW_TYPES: frozenset[str] = frozenset({
    "repository", "person", "notification", "invitation", "runner", "package", "codespace",
    "environment", "deployment", "pages_site", "advisory", "key", "webhook", "deploy_key",
    "autolink", "sponsorship", "sponsor_tier", "wiki", "resource", "label", "gist",
    "discussion", "discussion_section", "discussion_category", "security_alert", "cache",
    "saved_search", "file", "folder", "milestone", "project", "organization", "team",
    "favorite", "template", "watch",
})  # fmt: skip

#: What each list answers here, by row type.
LOCAL: dict[str, tuple[Qualifier, ...]] = {
    "branch": (
        _q("name", "Name", TEXT),
        _q("protected", "Protected", FLAG),
        _q("ahead", "Commits ahead of the default branch", NUMBER),
        _q("behind", "Commits behind the default branch", NUMBER),
        _q("author", "Last commit's author", TEXT, "commit_author"),
        _q("committed", "Last commit's date", DATE, "commit_date"),
    ),
    "tag": (_q("name", "Name", TEXT), _q("sha", "Commit", TEXT, "commit_sha")),
    "commit": (
        _q("author", "Author", TEXT),
        _q("committed", "Date", DATE, "date"),
        _q("message", "Message", WORDS),
        _q("sha", "Commit", TEXT),
    ),
    "release": (
        _q("tag", "Tag", TEXT),
        _q("name", "Title", TEXT),
        _q("draft", "Draft", FLAG),
        _q("prerelease", "Pre-release", FLAG),
        _q("created", "Created", DATE, "created_at"),
    ),
    "release_asset": (
        _q("name", "Name", TEXT),
        _q("size", "Size in bytes", NUMBER, "size_bytes"),
        _q("downloads", "Downloads", NUMBER, "download_count"),
        _q("type", "Content type", TEXT, "content_type"),
        _q("updated", "Updated", DATE, "updated_at"),
    ),
    "workflow": (
        _q("name", "Name", TEXT),
        _q("path", "File", TEXT),
        _q("state", "State", TEXT),
    ),
    "run": (
        _q("workflow", "Workflow", TEXT, "name"),
        _q("branch", "Branch", TEXT),
        _q("event", "Event", TEXT),
        _q("status", "Status", TEXT),
        _q("conclusion", "Conclusion", TEXT),
        _q("created", "Created", DATE, "created_at"),
        _q("sha", "Head commit", TEXT, "head_sha"),
    ),
    **{row_type: _EXPLORE for row_type in EXPLORE_ROW_TYPES},
}

_DERIVED: dict[str, Callable[[object], object]] = {
    "@name": lambda row: getattr(row, "title", "") or getattr(row, "label", ""),
    "@owner": lambda row: str(getattr(row, "repo", "") or "").split("/", 1)[0],
}


def qualifiers_for(row_type: str) -> tuple[Qualifier, ...]:
    """What a list of *row_type* rows answers here (none for issues: GitHub's search does)."""
    return LOCAL.get(row_type, ())


def value_of(row: object, qualifier: Qualifier) -> object:
    derive = _DERIVED.get(qualifier.field)
    return derive(row) if derive is not None else getattr(row, qualifier.field, None)


def _empty(value: object) -> bool:
    return value is None or value == "" or (isinstance(value, (tuple, list)) and not value)


def _number(text: object) -> float | None:
    try:
        return float(str(text).strip())
    except ValueError:
        return None


def _compare_date(have: str, op: Operator, wanted: str) -> bool:
    """ISO dates compared as text, to the precision typed (``2026-11`` is the month)."""
    if not have:
        return False
    low, sep, high = wanted.partition("..")
    if sep and op is Operator.IS:
        return have[: len(low)] >= low and have[: len(high)] <= high
    part = have[: len(wanted)]
    return {
        Operator.AFTER: part > wanted,
        Operator.BEFORE: part < wanted,
        Operator.AT_LEAST: part >= wanted,
        Operator.AT_MOST: part <= wanted,
    }.get(op, part == wanted)


def _compare(kind: str, found: object, op: Operator, wanted: str) -> bool:
    if kind == NUMBER:
        have = _number(found)
        if have is None:
            return False
        low, sep, high = wanted.partition("..")
        if sep and op is Operator.IS:
            lo, hi = _number(low), _number(high)
            return lo is not None and hi is not None and lo <= have <= hi
        limit = _number(wanted)
        if limit is None:
            return False
        return {
            Operator.AFTER: have > limit,
            Operator.BEFORE: have < limit,
            Operator.AT_LEAST: have >= limit,
            Operator.AT_MOST: have <= limit,
        }.get(op, have == limit)
    if kind == DATE:
        return _compare_date(str(found or ""), op, wanted)
    if kind == FLAG:
        return bool(found) == (wanted.casefold() in ("true", "yes", "1"))
    items = found if isinstance(found, (tuple, list)) else (found,)
    want = wanted.casefold()
    for item in items:
        text = str(item or "").casefold()
        if kind == WORDS and want in text:
            return True
        if any(ch in want for ch in "*?[") and fnmatch.fnmatchcase(text, want):
            return True
        if text == want:
            return True
    return False


def matches(row: object, qualifiers: Sequence[Qualifier], conditions: Iterable[Condition]) -> bool:
    """Whether *row* meets every condition that names one of *qualifiers*."""
    by_key = {q.key: q for q in qualifiers}
    for condition in conditions:
        if condition.attribute == "no" and condition.value in by_key:
            hit = _empty(value_of(row, by_key[condition.value]))
            negated = condition.operator is Operator.IS_NOT
        elif condition.attribute in by_key:
            qualifier = by_key[condition.attribute]
            negated = condition.operator is Operator.IS_NOT
            op = Operator.IS if negated else condition.operator
            hit = _compare(qualifier.kind, value_of(row, qualifier), op, condition.value)
        else:
            continue
        if hit == negated:
            return False
    return True


def _known(condition: Condition, keys: set[str]) -> bool:
    return condition.attribute in keys or (condition.attribute == "no" and condition.value in keys)


def filter_rows(
    rows: Sequence[object],
    conditions: Sequence[Condition],
    row_type: Callable[[object], str],
    *,
    list_type: str = "",
) -> tuple[list[object], list[str]]:
    """The rows meeting the conditions, and the qualifiers no row here could answer.

    *list_type* is the node's own row type, so an empty list still knows its
    qualifiers.
    """
    if not conditions:
        return list(rows), []
    kept: list[object] = []
    answered: set[str] = {q.key for q in qualifiers_for(list_type)}
    for row in rows:
        qualifiers = qualifiers_for(row_type(row))
        answered |= {q.key for q in qualifiers}
        if matches(row, qualifiers, conditions):
            kept.append(row)
    unknown = [
        f"{c.attribute}:{c.value}" if c.attribute == "no" else c.attribute
        for c in conditions
        if not _known(c, answered)
    ]
    return kept, list(dict.fromkeys(unknown))


def filter_note(loaded: int, shown: int, unknown: Sequence[str], *, complete: bool) -> str:
    """The status line: how many rows the filter kept, and what it could not use here."""
    if complete:
        said = f"Filtered here: {shown} of all {loaded}."
    else:
        said = f"Filtered here: {shown} of {loaded} loaded. Load All to be sure."
    if unknown:
        said += " Not a filter for this list: " + ", ".join(unknown) + "."
    return said
