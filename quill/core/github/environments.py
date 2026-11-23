"""A repository's deployment environments, as rows (GitHub PRD section 19).

Each row (kind ``environment``, keyed by the environment's name) opens the
Environment Properties sheet, and reaches its secrets and variables through
the resource engine's :data:`~quill.core.github.resource_specs_env.ENVIRONMENT_SPECS`.
:func:`create_environment` is New Environment (Ctrl+N in Environments): GitHub's
one call both makes and replaces an environment, so it reads first and never
replaces one that exists.
wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

from quill.core.error_codes import CodedError
from quill.core.github.explore_models import ExploreRow
from quill.core.github.rest_transport import GitHubRestError
from quill.core.github.workbench_api import GitHubApi

__all__ = [
    "MAX_WAIT_MINUTES",
    "EnvironmentRefused",
    "create_environment",
    "delete_environment",
    "environment_row",
    "fetch_environments",
]

#: GitHub's longest wait timer: 30 days, in minutes.
MAX_WAIT_MINUTES = 43200


class EnvironmentRefused(CodedError):
    code = "QUILL-GITHUB-ENVIRONMENT-REFUSED"


def _rules(raw: Mapping[str, Any]) -> str:
    kinds = []
    for rule in raw.get("protection_rules") or ():
        if not isinstance(rule, Mapping):
            continue
        kind = str(rule.get("type") or "")
        if kind == "required_reviewers":
            kinds.append("needs a reviewer")
        elif kind == "wait_timer":
            kinds.append(f"waits {rule.get('wait_timer')} minutes")
        elif kind == "branch_policy":
            kinds.append("only from chosen branches")
        elif kind:
            kinds.append(kind.replace("_", " "))
    return ", ".join(kinds) or "no protection rules"


def environment_row(raw: Mapping[str, Any], repo: str) -> ExploreRow:
    name = str(raw.get("name") or "")
    label = f"{name}: {_rules(raw)}."
    url = str(raw.get("html_url") or f"https://github.com/{repo}/settings/environments")
    return ExploreRow(label, f"{label}\n{url}", url, repo, "environment", name)


def fetch_environments(
    api: GitHubApi, repo: str, warnings: list[str] | None = None
) -> list[ExploreRow]:
    try:
        data = api.rest("GET", f"/repos/{repo}/environments", query={"per_page": "100"}).data
    except GitHubRestError as exc:
        if exc.status in (401, 403):
            raise EnvironmentRefused(
                "GitHub refused to list the environments. It needs admin access."
            ) from exc
        raise EnvironmentRefused(f"Could not list the environments: {exc}") from exc
    items = data.get("environments") if isinstance(data, Mapping) else []
    rows = [environment_row(raw, repo) for raw in items or () if isinstance(raw, Mapping)]
    if not rows and warnings is not None:
        warnings.append("No environments yet. A workflow job that names one makes it.")
    return rows


def delete_environment(api: GitHubApi, repo: str, name: str) -> str:
    try:
        api.rest("DELETE", f"/repos/{repo}/environments/{quote(name, safe='')}")
    except GitHubRestError as exc:
        if exc.status in (401, 403):
            raise EnvironmentRefused(
                "GitHub refused to delete the environment. It needs admin access."
            ) from exc
        raise EnvironmentRefused(f"Could not delete {name}: {exc}") from exc
    return f"Deleted the environment {name}, with its secrets and variables."


def create_environment(
    api: GitHubApi, repo: str, name: str, *, protected_only: bool = False, wait_minutes: int = 0
) -> str:
    """Make the environment *name* in *repo*; refuses, before sending, when it exists.

    Returns the sentence from GitHub's answer: which branches may deploy and the wait.
    """
    name = name.strip()
    if not name:
        raise EnvironmentRefused("An environment needs a name.")
    if not 0 <= wait_minutes <= MAX_WAIT_MINUTES:
        raise EnvironmentRefused(
            f"The wait is from 0 to {MAX_WAIT_MINUTES} minutes (30 days), not {wait_minutes}."
        )
    path = f"/repos/{repo}/environments/{quote(name, safe='')}"
    try:
        api.rest("GET", path)
    except GitHubRestError as exc:
        if exc.status != 404:
            raise EnvironmentRefused(
                f"GitHub did not say whether {repo} already has {name} ({exc})"
            ) from exc
    else:
        raise EnvironmentRefused(
            f"{repo} already has the environment {name}; its sheet (Alt+Enter) changes it."
        )
    policy = {"protected_branches": True, "custom_branch_policies": False}
    body: dict[str, object] = {"deployment_branch_policy": policy if protected_only else None}
    if wait_minutes:
        body["wait_timer"] = wait_minutes
    try:
        made = api.rest("PUT", path, body=body).data
    except GitHubRestError as exc:
        if exc.status in (401, 403):
            raise EnvironmentRefused(
                "GitHub refused it; an environment needs admin access, and on a private "
                "repository a paid plan."
            ) from exc
        raise EnvironmentRefused(str(exc)) from exc
    made = made if isinstance(made, Mapping) else {}
    answered = made.get("deployment_branch_policy")
    guarded = isinstance(answered, Mapping) and bool(answered.get("protected_branches"))
    wait = next(
        (
            int(rule.get("wait_timer") or 0)
            for rule in made.get("protection_rules") or ()
            if isinstance(rule, Mapping) and rule.get("type") == "wait_timer"
        ),
        0,
    )
    who = "only protected branches" if guarded else "any branch"
    after = f"a {wait} minute wait" if wait else "no wait"
    return f"Made the environment {name} in {repo}: {who} may deploy to it, with {after}."
