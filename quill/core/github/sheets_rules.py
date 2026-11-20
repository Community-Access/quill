"""The Ruleset sheets, a repository's and an organization's, and classic protection (18.3.1).

A ruleset is the most combinations GitHub offers, so its sheet is laid out
for them: General, Target (branches or tags), **Repositories** (an
organization ruleset's include and exclude names, or the property it
chooses by), Bypass (the roles that may bypass it, as a check list, and every
actor GitHub lists, teams and apps too), Rules (each rule on or off, the
pull request and status check settings, and **every rule with every setting
GitHub sent**, in words, so a rule type QUILL has no box for is still read),
the plain-words Summary, and History.

GitHub replaces a ruleset whole, so a save goes through
:func:`quill.core.github.rulesets.ruleset_body`, and the organization's
ruleset is saved to the organization's path. Classic branch protection keeps
every list GitHub holds (who may push, dismiss reviews or skip the pull
request) through :mod:`quill.core.github.branch_protection`, and signed
commits go to their own endpoint.

wx-free and strict-typed.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from quill.core.github import branch_protection as protection
from quill.core.github.permissions import WriteTier
from quill.core.github.rulesets import (
    BYPASS_ROLES,
    MERGE_METHODS,
    RULES,
    classic_as_rules,
    ruleset_body,
    ruleset_values,
    summary,
)
from quill.core.github.sheet_engine import Ident, Read, SheetDef, Write
from quill.core.github.sheet_fields import ed, page, ro
from quill.core.workbench.properties import FieldKind, PageSpec, SheetSpec, Value

__all__ = ["BRANCH_PROTECTION", "ORG_RULESET", "RULESET"]

_A, _D = WriteTier.ACCESS, WriteTier.DESTRUCTIVE
_K = FieldKind
_RULE_WORDS = tuple(words for _key, words in RULES)


def _ruleset(data: Mapping[str, Any]) -> dict[str, Value]:
    return {k: v for k, v in ruleset_values(data).items() if isinstance(v, (str, int, bool, tuple))}


def _compose(where: str) -> Any:
    def compose(
        ident: Ident, edits: Mapping[str, Value]
    ) -> list[tuple[str, str, dict[str, object]]]:
        raw = json.loads(ident.get("raw_json") or "{}")
        owner = ident["repo"] if where == "repos" else ident["org"]
        body = ruleset_body(raw, dict(edits))
        return [("PUT", f"/{where}/{owner}/rulesets/{ident['id']}", body)]

    return compose


_RULES_PAGE = page(
    "rules",
    "Rules",
    ed(
        "rules",
        "Rules",
        _K.CHECKLIST,
        "Each rule GitHub offers, checked when it is on.",
        choices=_RULE_WORDS,
    ),
    ed("approvals", "Approvals needed", _K.NUMBER, "For Require a pull request."),
    ed("dismiss_stale", "Dismiss stale approvals on new pushes", _K.CHECK),
    ed("code_owners", "Require a code owner's review", _K.CHECK),
    ed("last_push", "Require approval of the most recent push", _K.CHECK),
    ed("resolve_threads", "Require conversations to be resolved", _K.CHECK),
    ed("merge_methods", "Allowed merge methods", _K.CHECKLIST, choices=MERGE_METHODS),
    ed("status_checks", "Required status checks", _K.LIST, "Check names, comma-separated."),
    ed("strict", "Branch must be up to date", _K.CHECK),
    ro(
        "rule_details",
        "Every rule and its settings",
        _K.MULTILINE,
        "Each rule GitHub sent, with every setting it carries, a line a rule: patterns, "
        "paths, file sizes, workflows and code scanning tools included.",
    ),
)

_BYPASS_PAGE = page(
    "bypass",
    "Bypass",
    ed(
        "bypass_roles",
        "Roles that may bypass",
        _K.CHECKLIST,
        "Checked roles may push past the rules. Teams and apps that may bypass are kept "
        "as they are; they are listed below.",
        choices=tuple(name for name, _kind, _id in BYPASS_ROLES),
    ),
    ro(
        "bypass",
        "Everyone who may bypass",
        _K.TABLE,
        "Roles, teams and apps that may bypass it, always or for pull requests.",
    ),
)

_EDITABLE = (
    "name",
    "enforcement",
    "include",
    "exclude",
    "bypass_roles",
    "rules",
    "approvals",
    "dismiss_stale",
    "code_owners",
    "last_push",
    "resolve_threads",
    "merge_methods",
    "status_checks",
    "strict",
)


def _pages(organization: bool) -> tuple[PageSpec, ...]:
    general = page(
        "general",
        "General",
        ed("name", "Name"),
        ed(
            "enforcement",
            "Enforcement",
            _K.CHOICE,
            "Active blocks; evaluate only reports what it would block; disabled does nothing.",
            choices=("active", "evaluate", "disabled"),
        ),
        ro("target", "Applies to", help="Branches, tags, or every push."),
    )
    target = page(
        "target",
        "Target",
        ed(
            "include",
            "Include",
            _K.LIST,
            "Branch or tag patterns; ~DEFAULT_BRANCH is the default branch and ~ALL is "
            "all of them.",
        ),
        ed("exclude", "Exclude", _K.LIST),
    )
    repositories = page(
        "repositories",
        "Repositories",
        ro("repositories", "Covers", help="Which of the organization's repositories, in words."),
        ed(
            "repo_include",
            "Repository names to include",
            _K.LIST,
            "Names or patterns, comma-separated; ~ALL is every repository. Changing these "
            "chooses repositories by name, in place of a property.",
        ),
        ed("repo_exclude", "Repository names to exclude", _K.LIST),
        ed(
            "repo_protected",
            "Stop repositories being renamed out of it",
            _K.CHECK,
            "A repository the ruleset covers by name cannot be renamed so it no longer matches.",
        ),
    )
    summary_page = page(
        "summary",
        "Summary",
        ro("summary", "In plain words", _K.MULTILINE, "The whole ruleset as sentences."),
    )
    history = page(
        "history",
        "History",
        ro(
            "history_note",
            "History and insights",
            help="Ruleset History on the ruleset's row lists every version; Rule Insights "
            "lists the pushes the rules passed, blocked or let through.",
        ),
    )
    middle = (repositories,) if organization else ()
    return (general, target, *middle, _BYPASS_PAGE, _RULES_PAGE, summary_page, history)


RULESET = SheetDef(
    "ruleset",
    SheetSpec("ruleset", "Ruleset", _pages(False)),
    (Read("/repos/{repo}/rulesets/{id}", _ruleset),),
    {
        key: Write("/repos/{repo}/rulesets/{id}", "repo:admin", _A, "PUT", "put")
        for key in _EDITABLE
    },
    title=lambda ident: f"Ruleset {ident.get('name') or ident['id']}",
    url=lambda ident: f"https://github.com/{ident['repo']}/rules/{ident['id']}",
    compose=_compose("repos"),
    adopt=("raw_json",),
)

ORG_RULESET = SheetDef(
    "org_ruleset",
    SheetSpec("org_ruleset", "Organization Ruleset", _pages(True)),
    (Read("/orgs/{org}/rulesets/{id}", _ruleset),),
    {
        key: Write("/orgs/{org}/rulesets/{id}", "org:owner", _A, "PUT", "put")
        for key in (*_EDITABLE, "repo_include", "repo_exclude", "repo_protected")
    },
    title=lambda ident: f"Ruleset {ident.get('name') or ident['id']}",
    url=lambda ident: (
        f"https://github.com/organizations/{ident['org']}/settings/rules/{ident['id']}"
    ),
    compose=_compose("orgs"),
    adopt=("raw_json",),
)


# ---------------------------------------------------------------------------
# Classic branch protection
# ---------------------------------------------------------------------------


def _protection(data: Mapping[str, Any]) -> dict[str, Value]:
    found = protection.values(data)
    return {k: v for k, v in found.items() if isinstance(v, (str, int, bool, tuple))}


def _protection_summary(data: Mapping[str, Any]) -> dict[str, Value]:
    return {"summary": summary(classic_as_rules(data, "this branch"))}


def _compose_protection(
    ident: Ident, edits: Mapping[str, Value]
) -> list[tuple[str, str, dict[str, object]]]:
    raw = json.loads(ident.get("raw_json") or "{}")
    return protection.requests(ident["repo"], ident["branch"], raw, dict(edits))


_PROTECTION_KEYS = (
    "approvals",
    "dismiss_stale",
    "code_owners",
    "last_push",
    "status_checks",
    "strict",
    "signatures",
    *(key for key, _api, _words in protection.FLAGS),
)

BRANCH_PROTECTION = SheetDef(
    "branch_protection",
    SheetSpec(
        "branch_protection",
        "Branch Protection",
        (
            page(
                "general",
                "General",
                ed(
                    "approvals",
                    "Approvals needed",
                    _K.NUMBER,
                    "0 turns off Require a pull request.",
                ),
                ed("dismiss_stale", "Dismiss stale approvals on new pushes", _K.CHECK),
                ed("code_owners", "Require a code owner's review", _K.CHECK),
                ed("last_push", "Require approval of the most recent push", _K.CHECK),
                ed("status_checks", "Required status checks", _K.LIST),
                ed("strict", "Branch must be up to date", _K.CHECK),
                ed("signatures", "Require signed commits", _K.CHECK),
                *(ed(key, words, _K.CHECK) for key, _api, words in protection.FLAGS),
            ),
            page(
                "who",
                "Who",
                ro(
                    "push_restrictions",
                    "Who may push",
                    help="People, teams and apps; kept as they are on save.",
                ),
                ro("dismissers", "Who may dismiss reviews", help="Kept on save."),
                ro("pr_bypass", "Who may skip the pull request", help="Kept on save."),
            ),
            page("summary", "Summary", ro("summary", "In plain words", _K.MULTILINE)),
        ),
    ),
    (
        Read("/repos/{repo}/branches/{branch}/protection", _protection),
        Read("/repos/{repo}/branches/{branch}/protection", _protection_summary),
    ),
    {
        key: Write(
            "/repos/{repo}/branches/{branch}/protection",
            "repo:admin",
            _D if key in ("allow_force_pushes", "allow_deletions", "lock_branch") else _A,
            "PUT",
            "put",
        )
        for key in _PROTECTION_KEYS
    },
    title=lambda ident: f"Protection of {ident['branch']}",
    url=lambda ident: f"https://github.com/{ident['repo']}/settings/branches",
    compose=_compose_protection,
    adopt=("raw_json",),
)
