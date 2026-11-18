"""An environment's deployment branch and tag policies, and its custom protection rules.

Reached from an environment's row (Branch Policies..., Protection Rules...),
like its secrets and variables; the target is ``owner/repo/environments/name``.
Adding a protection rule offers the GitHub Apps that can guard deployments
(:func:`protection_apps`) rather than asking for an app's number. wx-free and
strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.resource_engine import Field, ResourceSpec
from quill.core.github.sheet_fields import dig

__all__ = ["MORE_ENVIRONMENT_SPECS", "protection_apps"]

_REPO = "https://github.com/{target}"


def _policy(raw: Mapping[str, Any]) -> str:
    kind = "Tags" if raw.get("type") == "tag" else "Branches"
    return f"{kind} matching {raw.get('name')} may deploy."


def protection_apps(api: Any, target: str) -> list[tuple[str, str]]:
    """``(app id, its name)`` for each GitHub App that can guard deployments to *target*."""
    from quill.core.github.resource_engine import ResourceError
    from quill.core.github.rest_transport import GitHubRestError

    path = f"/repos/{target}/deployment_protection_rules/apps"
    try:
        data = api.rest("GET", path).data
    except GitHubRestError as exc:
        raise ResourceError(f"Could not list the apps that can protect deployments: {exc}") from exc
    found = (
        data.get("available_custom_deployment_protection_rule_integrations", [])
        if isinstance(data, Mapping)
        else []
    )
    return [
        (str(app.get("id")), str(app.get("slug") or app.get("id")))
        for app in found
        if isinstance(app, Mapping) and app.get("id") is not None
    ]


MORE_ENVIRONMENT_SPECS: tuple[ResourceSpec, ...] = (
    ResourceSpec(
        key="environment_branch_policies",
        label="Environment Branch and Tag Policies",
        scope="environment",
        parent="",
        noun="branch or tag policy",
        list_path="{base}/deployment-branch-policies",
        items_key="branch_policies",
        id_field="id",
        id_param="{branch_policy_id}",
        sentence=_policy,
        help=(
            "Which branches and tags may deploy to this environment, when it allows chosen "
            "ones only. Names can use wildcards, such as release/*."
        ),
        page=_REPO,
        create=(
            Field("name", "The branch or tag name, wildcards allowed, such as release/*:"),
            Field("type", "Is it a branch or a tag?", "choice", ("branch", "tag")),
        ),
        edit=(Field("name", "The new name pattern:"),),
        edit_method="PUT",
    ),
    ResourceSpec(
        key="environment_protection_rules",
        label="Environment Custom Protection Rules",
        scope="environment",
        parent="",
        noun="protection rule",
        list_path="{base}/deployment_protection_rules",
        items_key="custom_deployment_protection_rules",
        id_field="id",
        id_param="{protection_rule_id}",
        sentence=lambda raw: (
            f"{dig(raw, 'app', 'slug') or 'An app'} must approve each deployment"
            f"{'' if raw.get('enabled', True) else ' (turned off)'}."
        ),
        help=(
            "Custom protection rules: GitHub Apps that must approve a deployment to this "
            "environment. Ctrl+N lists the apps you can add."
        ),
        page=_REPO,
        create=(Field("integration_id", "The app to add:", "number"),),
        extra=(
            "GET /repos/{owner}/{repo}/environments/{environment_name}"
            "/deployment_protection_rules/apps",
        ),
    ),
)
