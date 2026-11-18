"""More settings on the Repository and Organization sheets (GitHub PRD sections 15 and 19).

Settings GitHub keeps one object each for, read with GET and saved with PUT or
PATCH: how long Actions keeps artifacts and logs, which outside contributors
need approval before their workflows run, which actions may run, whether
other repositories may use this one's workflows, immutable releases, code
scanning's default setup, and an organization's interaction limit. Split from
:mod:`quill.core.github.sheets_repo` and :mod:`quill.core.github.sheets_orgs`
to keep each under the size budget; :func:`with_more_settings` adds these pages
to the two sheets in :mod:`quill.core.github.sheet_catalog`.

Left out on purpose: the fork-pull-request rules for private repositories,
whose PUT needs every field at once while a sheet sends only the changed
ones. wx-free and strict-typed.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from typing import Any

from quill.core.github.permissions import WriteTier
from quill.core.github.sheet_engine import Ident, Read, SheetDef, Write
from quill.core.github.sheet_fields import dig, ed, page, patch, toggle
from quill.core.workbench.properties import FieldKind, PageSpec, SheetSpec, Value

__all__ = ["APPROVAL_POLICIES", "with_more_settings"]

_A = WriteTier.ACCESS
_K = FieldKind
_REPO = "/repos/{repo}"
_ORG = "/orgs/{org}"
_REPO_ADMIN = "repo:admin"
_ORG_OWNER = "org:owner"

#: GitHub's words for who needs approval, and the sheet's.
APPROVAL_POLICIES: dict[str, str] = {
    "first time contributors new to GitHub": "first_time_contributors_new_to_github",
    "first time contributors": "first_time_contributors",
    "all outside contributors": "all_external_contributors",
}
_POLICY_WORDS = {api: words for words, api in APPROVAL_POLICIES.items()}


def _days(data: Mapping[str, Any]) -> dict[str, Value]:
    return {"retention_days": int(data.get("days") or 0)}


def _approval(data: Mapping[str, Any]) -> dict[str, Value]:
    policy = str(data.get("approval_policy") or "")
    return {"fork_approval": _POLICY_WORDS.get(policy, policy.replace("_", " "))}


def _selected(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "github_owned_allowed": bool(data.get("github_owned_allowed")),
        "verified_allowed": bool(data.get("verified_allowed")),
        "patterns_allowed": [str(one) for one in data.get("patterns_allowed") or []],
    }


def _access(data: Mapping[str, Any]) -> dict[str, Value]:
    return {"workflow_access": str(data.get("access_level") or "none")}


def _immutable(data: Mapping[str, Any]) -> dict[str, Value]:
    return {"immutable_releases": bool(data.get("enabled"))}


def _scanning(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "scanning_setup": str(data.get("state") or "not-configured").replace("-", " "),
        "scanning_suite": str(data.get("query_suite") or "default"),
    }


def _org_workflow(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "org_token_permission": str(data.get("default_workflow_permissions") or "read"),
        "org_actions_approve_prs": bool(data.get("can_approve_pull_request_reviews")),
    }


def _org_runners(data: Mapping[str, Any]) -> dict[str, Value]:
    return {"self_hosted_repositories": str(data.get("enabled_repositories") or "all")}


def _org_immutable(data: Mapping[str, Any]) -> dict[str, Value]:
    return {"immutable_repositories": str(data.get("enforced_repositories") or "none")}


def _org_limit(data: Mapping[str, Any]) -> dict[str, Value]:
    limit = str(dig(data, "limit") or "none")
    return {"org_interaction_limit": limit.replace("_", " ")}


def _int(key: str) -> Any:
    def encode(value: Value, _c: Mapping[str, object], _i: Ident) -> dict[str, object]:
        return {key: int(str(value or 0))}

    return encode


def _policy(value: Value, _c: Mapping[str, object], _i: Ident) -> dict[str, object]:
    return {"approval_policy": APPROVAL_POLICIES.get(str(value), str(value))}


def _scan_state(value: Value, _c: Mapping[str, object], _i: Ident) -> dict[str, object]:
    return {"state": str(value).replace(" ", "-")}


def _org_limit_encode(value: Value, _c: Mapping[str, object], _i: Ident) -> dict[str, object]:
    word = str(value or "none").replace(" ", "_")
    if word == "none":
        return {"__method": "DELETE"}
    return {"limit": word, "expiry": "one_week"}


_RETENTION_HELP = "How many days Actions keeps artifacts and logs, up to the owner's maximum."
_APPROVAL_HELP = "Which outside contributors need approval before their workflows run."
_SELECTED_HELP = "Used when Allowed actions is set to selected."

REPOSITORY_PAGES = (
    page(
        "actions_rules",
        "Actions Rules",
        ed("retention_days", "Keep artifacts and logs for days", _K.NUMBER, _RETENTION_HELP),
        ed(
            "fork_approval",
            "Approval needed for workflows from",
            _K.CHOICE,
            _APPROVAL_HELP,
            choices=tuple(APPROVAL_POLICIES),
        ),
        ed("github_owned_allowed", "Allow actions made by GitHub", _K.CHECK, _SELECTED_HELP),
        ed("verified_allowed", "Allow actions from verified creators", _K.CHECK, _SELECTED_HELP),
        ed(
            "patterns_allowed",
            "Other allowed actions",
            _K.LIST,
            "Patterns such as octo-org/*, comma-separated. " + _SELECTED_HELP,
        ),
        ed(
            "workflow_access",
            "Workflows here may be used by",
            _K.CHOICE,
            "For a private repository: which other repositories may use its actions and "
            "reusable workflows.",
            choices=("none", "user", "organization"),
        ),
    ),
    page(
        "releases_scanning",
        "Releases and Scanning",
        ed(
            "immutable_releases",
            "Immutable releases",
            _K.CHECK,
            "A published release's tag and files can no longer be changed.",
        ),
        ed(
            "scanning_setup",
            "Code scanning default setup",
            _K.CHOICE,
            "Whether GitHub scans the code with CodeQL without a workflow of your own.",
            choices=("configured", "not configured"),
        ),
        ed(
            "scanning_suite",
            "Code scanning queries",
            _K.CHOICE,
            "The default queries, or the extended set that finds more.",
            choices=("default", "extended"),
        ),
    ),
)

REPOSITORY_READS = (
    Read(_REPO + "/actions/permissions/artifact-and-log-retention", _days, optional=True),
    Read(_REPO + "/actions/permissions/fork-pr-contributor-approval", _approval, optional=True),
    Read(_REPO + "/actions/permissions/selected-actions", _selected, optional=True),
    Read(_REPO + "/actions/permissions/access", _access, optional=True),
    Read(
        _REPO + "/immutable-releases",
        _immutable,
        optional=True,
        fallback={"immutable_releases": False},
    ),
    Read(_REPO + "/code-scanning/default-setup", _scanning, optional=True),
)


def _put(path: str, requirement: str, body_key: str = "", encode: Any = None) -> Write:
    return patch(path, requirement, _A, body_key, encode, method="PUT")


_SELECTED_REPO = _REPO + "/actions/permissions/selected-actions"
_SCAN = _REPO + "/code-scanning/default-setup"

REPOSITORY_WRITES: dict[str, Write] = {
    "retention_days": _put(
        _REPO + "/actions/permissions/artifact-and-log-retention", _REPO_ADMIN, encode=_int("days")
    ),
    "fork_approval": _put(
        _REPO + "/actions/permissions/fork-pr-contributor-approval", _REPO_ADMIN, encode=_policy
    ),
    "github_owned_allowed": _put(_SELECTED_REPO, _REPO_ADMIN),
    "verified_allowed": _put(_SELECTED_REPO, _REPO_ADMIN),
    "patterns_allowed": _put(_SELECTED_REPO, _REPO_ADMIN),
    "workflow_access": _put(_REPO + "/actions/permissions/access", _REPO_ADMIN, "access_level"),
    "immutable_releases": toggle(_REPO + "/immutable-releases", _REPO_ADMIN, _A),
    "scanning_setup": patch(_SCAN, _REPO_ADMIN, _A, encode=_scan_state),
    "scanning_suite": patch(_SCAN, _REPO_ADMIN, _A, "query_suite"),
}

ORGANIZATION_PAGES = (
    page(
        "actions_rules",
        "Actions Rules",
        ed(
            "org_retention_days",
            "Keep artifacts and logs for days",
            _K.NUMBER,
            "The organization's default; each repository may keep them for less.",
        ),
        ed(
            "org_fork_approval",
            "Approval needed for workflows from",
            _K.CHOICE,
            _APPROVAL_HELP,
            choices=tuple(APPROVAL_POLICIES),
        ),
        ed(
            "org_token_permission",
            "Workflow token permission",
            _K.CHOICE,
            "What the GITHUB_TOKEN may do by default, in every repository.",
            choices=("read", "write"),
        ),
        ed(
            "org_actions_approve_prs",
            "Allow Actions to create and approve pull requests",
            _K.CHECK,
        ),
        ed(
            "org_github_owned_allowed",
            "Allow actions made by GitHub",
            _K.CHECK,
            _SELECTED_HELP,
        ),
        ed(
            "org_verified_allowed",
            "Allow actions from verified creators",
            _K.CHECK,
            _SELECTED_HELP,
        ),
        ed(
            "org_patterns_allowed",
            "Other allowed actions",
            _K.LIST,
            "Patterns such as octo-org/*, comma-separated. " + _SELECTED_HELP,
        ),
        ed(
            "self_hosted_repositories",
            "Repositories that may use self-hosted runners",
            _K.CHOICE,
            choices=("all", "selected", "none"),
        ),
    ),
    page(
        "safety",
        "Safety",
        ed(
            "org_interaction_limit",
            "Interaction limit",
            _K.CHOICE,
            "Limit who may comment and open issues and pull requests in every public "
            "repository, for a week.",
            choices=("none", "existing users", "contributors only", "collaborators only"),
        ),
        ed(
            "immutable_repositories",
            "Immutable releases in",
            _K.CHOICE,
            "Which repositories must keep published releases unchanged.",
            choices=("none", "all", "selected"),
        ),
    ),
)


def _prefixed(extract: Any, prefix: str = "org_") -> Any:
    def read(data: Mapping[str, Any]) -> dict[str, Value]:
        return {prefix + key: value for key, value in extract(data).items()}

    return read


ORGANIZATION_READS = (
    Read(
        _ORG + "/actions/permissions/artifact-and-log-retention",
        _prefixed(_days),
        optional=True,
    ),
    Read(
        _ORG + "/actions/permissions/fork-pr-contributor-approval",
        _prefixed(_approval),
        optional=True,
    ),
    Read(_ORG + "/actions/permissions/workflow", _org_workflow, optional=True),
    Read(_ORG + "/actions/permissions/selected-actions", _prefixed(_selected), optional=True),
    Read(_ORG + "/actions/permissions/self-hosted-runners", _org_runners, optional=True),
    Read(
        _ORG + "/interaction-limits",
        _org_limit,
        optional=True,
        fallback={"org_interaction_limit": "none"},
    ),
    Read(_ORG + "/settings/immutable-releases", _org_immutable, optional=True),
)

_SELECTED_ORG = _ORG + "/actions/permissions/selected-actions"
_WORKFLOW_ORG = _ORG + "/actions/permissions/workflow"

ORGANIZATION_WRITES: dict[str, Write] = {
    "org_retention_days": _put(
        _ORG + "/actions/permissions/artifact-and-log-retention", _ORG_OWNER, encode=_int("days")
    ),
    "org_fork_approval": _put(
        _ORG + "/actions/permissions/fork-pr-contributor-approval", _ORG_OWNER, encode=_policy
    ),
    "org_token_permission": _put(_WORKFLOW_ORG, _ORG_OWNER, "default_workflow_permissions"),
    "org_actions_approve_prs": _put(_WORKFLOW_ORG, _ORG_OWNER, "can_approve_pull_request_reviews"),
    "org_github_owned_allowed": _put(_SELECTED_ORG, _ORG_OWNER, "github_owned_allowed"),
    "org_verified_allowed": _put(_SELECTED_ORG, _ORG_OWNER, "verified_allowed"),
    "org_patterns_allowed": _put(_SELECTED_ORG, _ORG_OWNER, "patterns_allowed"),
    "self_hosted_repositories": _put(
        _ORG + "/actions/permissions/self-hosted-runners", _ORG_OWNER, "enabled_repositories"
    ),
    "org_interaction_limit": Write(
        _ORG + "/interaction-limits", _ORG_OWNER, _A, "PUT", "put", encode=_org_limit_encode
    ),
    "immutable_repositories": _put(
        _ORG + "/settings/immutable-releases", _ORG_OWNER, "enforced_repositories"
    ),
}

#: The coverage rows each new field answers, as ``sheet:<kind>.<field>``.
_MORE = {
    "repository": (REPOSITORY_PAGES, REPOSITORY_READS, REPOSITORY_WRITES),
    "organization": (ORGANIZATION_PAGES, ORGANIZATION_READS, ORGANIZATION_WRITES),
}


def with_more_settings(sheet: SheetDef) -> SheetDef:
    """The Repository or Organization sheet with these pages added; any other, unchanged."""
    more = _MORE.get(sheet.kind)
    if more is None:
        return sheet
    pages, reads, writes = more
    spec: SheetSpec = dataclasses.replace(sheet.sheet, pages=(*sheet.sheet.pages, *pages))
    return dataclasses.replace(
        sheet, sheet=spec, reads=(*sheet.reads, *reads), writes={**sheet.writes, **writes}
    )


def extra_pages(kind: str) -> tuple[PageSpec, ...]:
    """The pages this module adds to one kind of sheet (for tests and the coverage rows)."""
    more = _MORE.get(kind)
    return more[0] if more else ()
