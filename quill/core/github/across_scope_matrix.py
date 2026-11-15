"""Every kind x scope x operation across repositories, classified (PRD 22.11, GH-E).

PRD 22.11: "Every kind in the table, over every scope, with every operation
the kind allows, is one row of the action table, so the coverage of
combinations is tested like everything else." :func:`matrix` is that table.
Each cell is a :class:`Support`: supported, with the Workbench verb that does
it (``_do_<verb>`` on the provider, or ``load_across`` or ``load_fleet`` for a
list), or not,
with the reason in words a person could be read. A cell is never blank;
``tests/unit/core/test_github_across_scope_matrix.py`` checks that, checks the
decided cells, and checks that every verb named here is a real command.

Read-only category lists (GX16) are their own family, apart from by-name
writes, because the PRD counts them separately: a list that reads across
repositories is not yet a batch that writes to them.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

__all__ = [
    "BY_NAME_KINDS",
    "CATEGORY_KINDS",
    "OPERATIONS",
    "SCOPES",
    "Support",
    "classify",
    "matrix",
]

#: The scopes of PRD 22.11: a hand-made set, a filter-made set, one
#: organization, your own repositories, and every repository you may read.
SCOPES = ("repository_set", "filter_set", "organization", "own_repositories", "every_permitted")

OPERATIONS = (
    "list",
    "variants",
    "missing_from",
    "make_same",
    "rename",
    "merge",
    "copy_missing",
    "delete",
    "close",
    "find_uses",
    "compare",
    "promote_org",
)

#: GX16's category lists.
CATEGORY_KINDS = (
    "issues",
    "releases",
    "runs",
    "commits",
    "tags",
    "milestones",
    "discussions",
    "alerts",
)

#: PRD 22.11's by-name table, plus the Fleet (22.12).
BY_NAME_KINDS = (
    "labels",
    "milestones",
    "tags",
    "releases",
    "topics",
    "issue_types",
    "branches",
    "rules",
    "environments",
    "secrets_variables",
    "webhooks",
    "deploy_keys_autolinks",
    "workflows",
    "templates",
    "dependabot_codeowners",
    "people",
    "teams",
    "settings",
    "personal_lists",
    "alerts",
    "packages_pages",
    "fleet",
)


@dataclass(frozen=True)
class Support:
    """One cell: whether it is supported, the verb that does it, and why."""

    supported: bool
    reason: str
    verb: str = ""


def _yes(verb: str, reason: str) -> Support:
    return Support(True, reason, verb)


def _no(reason: str) -> Support:
    return Support(False, reason)


_LATER = "Not yet: {what}. The single-repository {single} comes first (GATE-GITHUB-COVER)."


def _later(what: str, single: str) -> Support:
    return _no(_LATER.format(what=what, single=single))


_BY_NAME: Mapping[str, Mapping[str, Support]] = {
    "labels": {
        "list": _yes("across_variants", "Every label name in the set, with where it differs."),
        "variants": _yes("across_variants", "Each colour and description, with its repositories."),
        "missing_from": _yes("across_variants", "The repositories that answered and lack it."),
        "make_same": _yes("across_make_same", "Choose the winning variant; preview, then results."),
        "rename": _yes("across_rename_name", "Renamed everywhere; a clash is shown, not merged."),
        "merge": _yes("across_merge_label", "Items relabelled, then the old label is deleted."),
        "copy_missing": _yes("across_add_missing", "Created where missing, with the winner."),
        "delete": _yes("across_delete_name", "Deleted everywhere, after the preview."),
        "promote_org": _no(
            "GitHub's API has no organization labels: default labels for new repositories are "
            "set on github.com only, so a label cannot be promoted."
        ),
        "find_uses": _yes("across_find_uses", "One issue search over every repository in the set."),
    },
    "milestones": {
        "list": _yes("across_variants", "Every milestone title in the set, with its progress."),
        "variants": _yes("across_variants", "Each due date, description and state."),
        "missing_from": _yes("across_variants", "The repositories that answered and lack it."),
        "make_same": _yes("across_make_same", "Due date and description take the winner's."),
        "copy_missing": _yes("across_add_missing", "Created where missing, with the winner."),
        "close": _yes("across_close_milestone", "Every open copy closed, after the preview."),
        "find_uses": _yes("across_find_uses", "One issue search over every repository in the set."),
        "rename": _later("renaming a milestone everywhere", "milestone sheet's title"),
        "merge": _yes(
            "across_move_open",
            "Each repository's open items move to another milestone of its own; one without "
            "that milestone is blocked, so no item is left without one.",
        ),
        "delete": _later("deleting a milestone everywhere", "milestone deletion"),
    },
    "topics": {
        "list": _yes("across_variants", "Every topic in the set and where it is."),
        "missing_from": _yes("across_variants", "The repositories that answered and lack it."),
        "copy_missing": _yes(
            "across_add_missing", "Added to the repositories you choose; their topics are kept."
        ),
        "delete": _yes("across_delete_name", "Removed everywhere; other topics are kept."),
    },
    "rules": {
        "list": _yes("across_variants", "Rulesets and default-branch protection, by name."),
        "variants": _yes("across_variants", "Enforcement, target and rule types, compared."),
        "missing_from": _yes("across_variants", "The repositories that answered and lack it."),
        "compare": _yes("across_variants", "Read side by side; nothing is changed."),
        "make_same": _yes(
            "across_make_same",
            "Rulesets and default-branch protection take the winner's; who may push is never "
            "copied, and protection is never removed this way.",
        ),
        "copy_missing": _yes(
            "across_add_missing", "A ruleset is created where it is missing (not protection)."
        ),
        "promote_org": _yes(
            "across_promote_org",
            "One organization ruleset for the set's repositories in that organization, then "
            "their copies deleted, only after it was created.",
        ),
    },
    "fleet": {
        "list": _yes(
            "load_fleet",
            "Each repository's revision, checks, pull requests, "
            "latest release and alerts, with when it was read.",
        ),
        "compare": _yes("load_fleet", "One line per repository, read row by row."),
    },
    "tags": {
        "list": _yes("load_across", "Tags is a category list (GX16), every tag by repository."),
        "compare": _later("comparing what each tag points at by name", "tag comparison"),
        "copy_missing": _later("creating one tag in many repositories (a release train)", "tag"),
        "delete": _later("deleting a tag everywhere", "tag deletion"),
    },
    "releases": {
        "list": _yes("load_across", "Releases is a category list (GX16), latest only or all."),
        "copy_missing": _later("release trains", "Create Release command"),
        "make_same": _later("editing notes together", "release sheet"),
    },
    "issue_types": {
        "list": _no(
            "Issue types are already organization-wide; the organization's Issue Types "
            "sheet lists them."
        ),
    },
    "branches": {
        "list": _yes("load_fleet", "Each repository's default branch is on its Fleet line."),
        "missing_from": _yes(
            "across_variants",
            "Rules and Branch Protection lists each default branch's protection, so the "
            "unprotected ones read as protected no.",
        ),
        "rename": _later("renaming a branch everywhere", "Rename Branch command"),
        "delete": _later("deleting merged branches of one name", "Delete Branch"),
    },
    "environments": {"make_same": _later("aligning environments", "environment sheet")},
    "secrets_variables": {
        "make_same": _later("setting a secret everywhere", "write-only secret field"),
        "delete": _later("deleting a secret everywhere", "secret deletion"),
        "promote_org": _later("promoting to an organization secret", "organization secret"),
    },
    "webhooks": {"make_same": _later("changing a webhook everywhere", "webhook sheet")},
    "deploy_keys_autolinks": {
        "copy_missing": _later("adding a deploy key or autolink to many", "deploy key sheet")
    },
    "workflows": {"compare": _later("comparing workflow files", "file comparison")},
    "templates": {"compare": _later("comparing community files", "template catalogue")},
    "dependabot_codeowners": {"make_same": _later("aligning configuration", "CODEOWNERS editor")},
    "people": {"list": _later("the access matrix from a person's side", "Access Review")},
    "teams": {
        "list": _no("Teams are already organization-wide; Organizations > Teams lists them.")
    },
    "settings": {"make_same": _later("making a setting the same", "repository sheet batch")},
    "personal_lists": {
        "list": _no(
            "Saved replies, favorites, watch levels and stars are yours, not a repository's: "
            "Repositories > Favorites, Saved Searches and Watches already list them across "
            "everything."
        ),
    },
    "alerts": {
        "list": _yes("load_across", "Security Alerts is a category list (GX16)."),
        "make_same": _later("dismissing an alert everywhere", "Dismiss Alert batch"),
    },
    "packages_pages": {"list": _later("packages and Pages by name", "Packages node")},
}

_SCOPE_NOTES = {
    "repository_set": "",
    "filter_set": " Over a filter-made set, the filter is resolved each time it is used.",
    "organization": " An organization is a filter-made set, org:name.",
    "own_repositories": " Your own repositories are a filter-made set, user:your-login.",
    "every_permitted": (
        " Every repository you can reach is a set of its own: the 200 most recently pushed, "
        "and the Items cell says when GitHub lists more."
    ),
}


def classify(family: str, kind: str, scope: str, op: str) -> Support:
    """The cell for *family* (``category`` or ``by_name``), *kind*, *scope* and *op*."""
    if scope not in SCOPES or op not in OPERATIONS:
        raise ValueError(f"Unknown scope or operation {scope!r} {op!r}.")
    if family == "category":
        if kind not in CATEGORY_KINDS:
            raise ValueError(f"Unknown category {kind!r}.")
        if op != "list":
            return _no(
                "A category list is read only; act on an item by opening it in its own "
                "repository, or by name under Across Repositories."
            )
        cell = _yes("load_across", "Every repository in the set, each answering for itself.")
    else:
        if kind not in _BY_NAME:
            raise ValueError(f"Unknown kind {kind!r}.")
        found = _BY_NAME[kind].get(op)
        if found is None:
            return _no("Not something this kind can do (the PRD 22.11 table).")
        cell = found
    if not cell.supported:
        return cell
    if scope == "every_permitted" and cell.verb == "across_promote_org":
        return _no("Promote to Organization works over one organization's repositories.")
    return Support(True, cell.reason + _SCOPE_NOTES[scope], cell.verb)


def matrix() -> dict[tuple[str, str, str, str], Support]:
    """Every cell: (family, kind, scope, op) -> :class:`Support`."""
    cells: dict[tuple[str, str, str, str], Support] = {}
    for family, kinds in (("category", CATEGORY_KINDS), ("by_name", BY_NAME_KINDS)):
        for kind in kinds:
            for scope in SCOPES:
                for op in OPERATIONS:
                    cells[(family, kind, scope, op)] = classify(family, kind, scope, op)
    return cells
