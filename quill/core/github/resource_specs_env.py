"""An environment's secrets and variables, and the organization's that a repository may use.

``ENVIRONMENT_SPECS`` are the resource engine's descriptions for one
deployment environment; their target is ``owner/repo/environments/name``. They
are not tree nodes: an environment's row reaches them (Secrets...,
Variables...). ``REPO_ORG_SPECS`` are two read-only repository lists, the
organization's secrets and variables this repository may use, which
:mod:`quill.core.github.resource_specs` adds to ``RESOURCE_SPECS``. wx-free
and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

from quill.core.github.resource_engine import Field, ResourceSpec

__all__ = ["ENVIRONMENT_SPECS", "REPO_ORG_SPECS", "environment_spec", "environment_target"]


def _day(raw: Mapping[str, Any]) -> str:
    return str(raw.get("updated_at") or "")[:10]


def _secret(raw: Mapping[str, Any]) -> str:
    changed = _day(raw)
    return f"{raw.get('name')}" + (f", changed {changed}." if changed else ".")


def _variable(raw: Mapping[str, Any]) -> str:
    changed = _day(raw)
    return f"{raw.get('name')} is {raw.get('value')}" + (
        f", changed {changed}." if changed else "."
    )


def environment_target(repo: str, environment: str) -> str:
    """The engine's target for one environment of *repo*."""
    return f"{repo}/environments/{quote(environment, safe='')}"


_PAGE = "https://github.com/{target}"

ENVIRONMENT_SPECS: tuple[ResourceSpec, ...] = (
    ResourceSpec(
        key="environment_secrets",
        label="Environment Secrets",
        scope="environment",
        parent="",
        noun="secret",
        list_path="{base}/secrets",
        items_key="secrets",
        id_param="{secret_name}",
        sentence=_secret,
        help="Secrets a workflow job reads only when it deploys to this environment.",
        page=_PAGE,
        create=(
            Field("name", "The secret's name:", is_id=True),
            Field("value", "Its value:", "secret"),
        ),
        create_method="PUT",
        create_path="{list}/{id}",
        seal=True,
        edit=(Field("value", "The new value:", "secret"),),
        edit_method="PUT",
    ),
    ResourceSpec(
        key="environment_variables",
        label="Environment Variables",
        scope="environment",
        parent="",
        noun="variable",
        list_path="{base}/variables",
        items_key="variables",
        sentence=_variable,
        help="Values a workflow job reads only when it deploys to this environment.",
        page=_PAGE,
        create=(Field("name", "The variable's name:"), Field("value", "Its value:")),
        edit=(Field("value", "The new value:"),),
    ),
)


def environment_spec(key: str) -> ResourceSpec | None:
    from quill.core.github.resource_specs_env_more import MORE_ENVIRONMENT_SPECS

    every = (*ENVIRONMENT_SPECS, *MORE_ENVIRONMENT_SPECS)
    return next((spec for spec in every if spec.key == key), None)


REPO_ORG_SPECS: tuple[ResourceSpec, ...] = (
    ResourceSpec(
        key="repo_org_secrets",
        label="Organization Secrets Here",
        scope="repository",
        parent="settings",
        noun="organization secret",
        list_path="{base}/actions/organization-secrets",
        items_key="secrets",
        sentence=_secret,
        help=(
            "Organization Secrets Here: the organization's Actions secrets this repository "
            "may use. Change them in the organization."
        ),
        page="https://github.com/{target}/settings/secrets/actions",
        delete=False,
    ),
    ResourceSpec(
        key="repo_org_variables",
        label="Organization Variables Here",
        scope="repository",
        parent="settings",
        noun="organization variable",
        list_path="{base}/actions/organization-variables",
        items_key="variables",
        sentence=_variable,
        help=(
            "Organization Variables Here: the organization's Actions variables this "
            "repository may use. Change them in the organization."
        ),
        page="https://github.com/{target}/settings/variables/actions",
        delete=False,
    ),
)
