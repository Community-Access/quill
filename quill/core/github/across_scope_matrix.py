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

**The single-repository rule** (PRD 22.11; complete.md 1.3): a write across
repositories is complete only when the same write in one repository is.
Every supported cell whose operation is in :data:`WRITE_OPERATIONS` names in
:data:`SINGLE_REPOSITORY` the one-repository command or sheet field that does
the same thing, and the tests fail when that home does not exist or the live
run has no row for it. A write whose single-repository form is missing is a
"not yet" (:data:`HELD_BACK`), whatever the window can already do.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

__all__ = [
    "BY_NAME_KINDS",
    "CATEGORY_KINDS",
    "HELD_BACK",
    "OPERATIONS",
    "READ_OPERATIONS",
    "SCOPES",
    "SINGLE_REPOSITORY",
    "WRITE_OPERATIONS",
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
    "on_off",
)

#: Operations that only read. Every other operation writes to each repository.
READ_OPERATIONS = frozenset({"list", "variants", "missing_from", "find_uses", "compare"})
WRITE_OPERATIONS = frozenset(OPERATIONS) - READ_OPERATIONS

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

#: PRD 22.11's by-name table, plus the Fleet (22.12). Secrets and variables,
#: and deploy keys and autolinks, share a PRD row but not an API, so each is
#: its own kind here.
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
    "secrets",
    "variables",
    "webhooks",
    "deploy_keys",
    "autolinks",
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


_MISSING = "The repositories that answered and lack it."

_BY_NAME: Mapping[str, Mapping[str, Support]] = {
    "labels": {
        "list": _yes("across_variants", "Every label name in the set, with where it differs."),
        "variants": _yes("across_variants", "Each colour and description, with its repositories."),
        "missing_from": _yes("across_variants", _MISSING),
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
        "missing_from": _yes("across_variants", _MISSING),
        "make_same": _yes("across_make_same", "Due date and description take the winner's."),
        "copy_missing": _yes("across_add_missing", "Created where missing, with the winner."),
        "close": _yes("across_close_milestone", "Every open copy closed, after the preview."),
        "find_uses": _yes("across_find_uses", "One issue search over every repository in the set."),
        "rename": _yes(
            "across_rename_name", "Renamed everywhere; a clash is shown, and Undo puts it back."
        ),
        "merge": _yes(
            "across_move_open",
            "Each repository's open items move to another milestone of its own; one without "
            "that milestone is blocked, so no item is left without one.",
        ),
        "delete": _yes(
            "across_delete_name",
            "Deleted everywhere after a preview that starts on Cancel; its items stay, with no "
            "milestone.",
        ),
    },
    "topics": {
        "list": _yes("across_variants", "Every topic in the set and where it is."),
        "missing_from": _yes("across_variants", _MISSING),
        "copy_missing": _yes(
            "across_add_missing", "Added to the repositories you choose; their topics are kept."
        ),
        "delete": _yes("across_delete_name", "Removed everywhere; other topics are kept."),
    },
    "rules": {
        "list": _yes("across_variants", "Rulesets and default-branch protection, by name."),
        "variants": _yes("across_variants", "Enforcement, target and rule types, compared."),
        "missing_from": _yes("across_variants", _MISSING),
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
        "list": _yes("across_variants", "Tags by Name: every tag name and the commit it is on."),
        "variants": _yes("across_variants", "Each commit the name is on, with its repositories."),
        "missing_from": _yes("across_variants", _MISSING),
        "compare": _yes("across_variants", "What each copy points at, read side by side."),
        "copy_missing": _yes(
            "across_release_train",
            "A release train: the tag, or the tag and a draft or published release, made on "
            "each chosen repository's default branch; an existing tag is never moved.",
        ),
        "delete": _yes(
            "across_delete_name",
            "Deleted everywhere, after the preview; a tag with a release built on it is kept.",
        ),
    },
    "releases": {
        "list": _yes("load_across", "Releases is a category list (GX16), latest only or all."),
        "copy_missing": _yes(
            "across_release_train",
            "Release Train, on a Tags by Name row, makes the release in each repository that "
            "lacks the tag; a repository that has it is skipped.",
        ),
        "make_same": _yes(
            "across_draft_releases",
            "Draft Releases Together, on a Tags by Name row: one draft release per repository "
            "from notes written once; one that has a release or draft for the tag is skipped.",
        ),
    },
    "issue_types": {
        "list": _no(
            "Issue types are already organization-wide; the organization's Issue Types "
            "sheet lists them."
        ),
    },
    "branches": {
        "list": _yes("across_variants", "Branches by Name: default and protected in how many."),
        "variants": _yes("across_variants", "Default and protected, with the repositories each."),
        "missing_from": _yes(
            "across_variants",
            "The repositories that lack the branch; Rules and Branch Protection lists the "
            "unprotected default branches too.",
        ),
        "rename": _yes(
            "across_rename_name",
            "GitHub's rename in each: the preview says where it is the default, where its "
            "protection moves with it and how many open pull requests are retargeted.",
        ),
        "delete": _yes(
            "across_delete_merged",
            "Delete Where Merged: only where everything on it is in the default branch, or a "
            "merged pull request took its last commit; a default, protected or unmerged copy is "
            "kept.",
        ),
    },
    "environments": {
        "list": _yes("across_variants", "Environments by Name, with where they differ."),
        "variants": _yes("across_variants", "Wait timer, reviewers, self-review and branches."),
        "missing_from": _yes("across_variants", _MISSING),
        "make_same": _yes(
            "across_make_same",
            "The winner's wait timer, reviewers, self-review and branch rule; custom branch "
            "patterns and another owner's teams are not copied.",
        ),
        "copy_missing": _yes(
            "across_add_missing",
            "Made where missing, as the winner; custom branch patterns and another owner's "
            "teams are not copied.",
        ),
        "delete": _yes("across_delete_name", "Deleted everywhere, after the preview."),
        "promote_org": _no(
            "GitHub has no organization environments: each belongs to one repository."
        ),
    },
    "secrets": {
        "list": _yes("across_variants", "Secrets by Name; their values are never readable."),
        "missing_from": _yes("across_variants", _MISSING),
        "make_same": _yes(
            "across_set_secret",
            "One new value, typed once and sealed for each repository; no old value is read.",
        ),
        "copy_missing": _yes(
            "across_set_secret", "Set Secret Everywhere adds it where it is missing too."
        ),
        "delete": _yes("across_delete_name", "Deleted everywhere, after the preview."),
        "promote_org": _yes(
            "across_promote_org",
            "One organization secret for the set's repositories there, its value typed once; "
            "their own copies deleted only after it exists, because a repository's own wins.",
        ),
    },
    "variables": {
        "list": _yes("across_variants", "Variables by Name, with their values."),
        "variants": _yes("across_variants", "Each value, with the repositories that have it."),
        "missing_from": _yes("across_variants", _MISSING),
        "make_same": _yes("across_make_same", "Every copy takes the winning value."),
        "copy_missing": _yes("across_add_missing", "Created where missing, with the winner."),
        "delete": _yes("across_delete_name", "Deleted everywhere, after the preview."),
        "promote_org": _yes(
            "across_promote_org",
            "One organization variable for the set's repositories there; their own copies "
            "deleted only after it exists.",
        ),
    },
    "webhooks": {
        "list": _yes("across_variants", "Webhooks by address; their secrets are never readable."),
        "variants": _yes("across_variants", "Events, on or off, and content type."),
        "missing_from": _yes("across_variants", _MISSING),
        "make_same": _yes(
            "across_make_same", "The winner's events, state and content type; secrets are kept."
        ),
        "copy_missing": _yes(
            "across_add_missing", "Added where missing; a secret, if any, is typed once."
        ),
        "delete": _yes("across_delete_name", "Deleted everywhere, after the preview."),
        "on_off": _yes("across_hooks_on_off", "Turned on or off everywhere, after the preview."),
        "promote_org": _yes(
            "across_promote_org",
            "One organization webhook, which GitHub sends for every repository there (the "
            "preview says so); the copies there deleted only after it exists.",
        ),
    },
    "deploy_keys": {
        "list": _yes("across_variants", "Deploy keys by title, with fingerprint and access."),
        "variants": _yes("across_variants", "Each key and its access, with its repositories."),
        "missing_from": _yes("across_variants", _MISSING),
        "copy_missing": _no(
            "GitHub accepts a deploy key in one repository only, so one cannot be added to many."
        ),
        "delete": _yes("across_delete_name", "Removed everywhere, after the preview."),
        "promote_org": _no("GitHub has no organization deploy keys."),
    },
    "autolinks": {
        "list": _yes("across_variants", "Autolinks by prefix, with their addresses."),
        "variants": _yes("across_variants", "Each address and reference kind."),
        "missing_from": _yes("across_variants", _MISSING),
        "copy_missing": _yes("across_add_missing", "Added where missing, with the winner."),
        "make_same": _no(
            "GitHub cannot change an autolink, only delete and add one: Delete Everywhere, "
            "then Add to Missing."
        ),
        "delete": _yes("across_delete_name", "Deleted everywhere, after the preview."),
        "promote_org": _no("GitHub has no organization autolinks."),
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
        "make_same": _yes(
            "across_dismiss_alerts",
            "Dismiss Everywhere, on a Security Alerts row: every open copy of the advisory or "
            "code scanning rule, one reason and comment; Undo reopens each. Secret scanning "
            "alerts are each their own and are resolved one at a time.",
        ),
    },
    "packages_pages": {
        "list": _no(
            "Not yet: packages and Pages by name across a set. Each repository's Packages "
            "and GitHub Pages nodes, and its sheet's Pages page, do it one repository at a time."
        )
    },
}

_W = "command:github.workbench."

#: (kind, write operation) -> the single-repository homes that do the same
#: write, in GATE-GITHUB-COVER's vocabulary (``command:<id>``, ``sheet:<kind>.<field>``).
SINGLE_REPOSITORY: Mapping[tuple[str, str], tuple[str, ...]] = {
    ("labels", "make_same"): ("sheet:label.colour", "sheet:label.description"),
    ("labels", "rename"): ("sheet:label.name",),
    ("labels", "merge"): (f"{_W}labels", f"{_W}delete_label"),
    ("labels", "copy_missing"): (f"{_W}labels",),
    ("labels", "delete"): (f"{_W}delete_label",),
    ("milestones", "make_same"): ("sheet:milestone.due", "sheet:milestone.description"),
    ("milestones", "copy_missing"): (f"{_W}milestone",),
    ("milestones", "close"): ("sheet:milestone.state",),
    ("milestones", "merge"): (f"{_W}milestone",),
    ("milestones", "rename"): ("sheet:milestone.title",),
    ("milestones", "delete"): (f"{_W}delete_milestone",),
    ("topics", "copy_missing"): ("sheet:repository.topics",),
    ("topics", "delete"): ("sheet:repository.topics",),
    ("rules", "make_same"): (
        "sheet:ruleset.approvals",
        "command:github.configure_branch_protection",
    ),
    ("rules", "promote_org"): (f"{_W}org_rulesets",),
    ("rules", "copy_missing"): (f"{_W}new_ruleset",),
    ("tags", "copy_missing"): (f"{_W}new_tag", "command:github.create_release"),
    ("tags", "delete"): (f"{_W}delete_tag",),
    ("releases", "copy_missing"): ("command:github.create_release",),
    ("releases", "make_same"): ("command:github.create_release",),
    ("branches", "rename"): ("sheet:branch.name",),
    ("branches", "delete"): (f"{_W}delete_branch",),
    ("environments", "make_same"): (
        "sheet:environment.wait_timer",
        "sheet:environment.reviewers",
        "sheet:environment.prevent_self_review",
        "sheet:environment.branches",
    ),
    ("environments", "delete"): (f"{_W}environment_delete",),
    ("environments", "copy_missing"): (f"{_W}new_environment",),
    ("secrets", "make_same"): ("sheet:secret.secret_value",),
    ("secrets", "copy_missing"): (f"{_W}resource_new",),
    ("secrets", "delete"): (f"{_W}resource_delete",),
    ("secrets", "promote_org"): (f"{_W}resource_new",),
    ("variables", "make_same"): ("sheet:variable.value",),
    ("variables", "copy_missing"): (f"{_W}resource_new",),
    ("variables", "delete"): (f"{_W}resource_delete",),
    ("variables", "promote_org"): (f"{_W}resource_new",),
    ("webhooks", "make_same"): (
        "sheet:webhook.events",
        "sheet:webhook.active",
        "sheet:webhook.content_type",
    ),
    ("webhooks", "copy_missing"): (f"{_W}new_webhook",),
    ("webhooks", "delete"): (f"{_W}delete_webhook",),
    ("webhooks", "on_off"): (f"{_W}webhook_on_off",),
    ("webhooks", "promote_org"): (f"{_W}new_webhook",),
    ("deploy_keys", "delete"): (f"{_W}delete_deploy_key",),
    ("autolinks", "copy_missing"): (f"{_W}new_autolink",),
    ("autolinks", "delete"): (f"{_W}delete_autolink",),
    ("alerts", "make_same"): (f"{_W}dismiss_alert", "sheet:security_alert.state"),
}

#: Writes the window can do but the single-repository rule does not count as
#: done yet, each with what is missing. May only shrink; empty since GH-R-151
#: (New Ruleset in one repository made ruleset Add to Missing count).
HELD_BACK: Mapping[tuple[str, str], str] = {}

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
        if (kind, op) in HELD_BACK:
            return _no(HELD_BACK[(kind, op)])
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
