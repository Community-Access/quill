"""The list-shaped settings the resource engine serves, one short description each.

Each :class:`~quill.core.github.resource_engine.ResourceSpec` becomes a node in
the GitHub Workbench's tree, rows that read as sentences, ``Ctrl+N`` to add one,
Change on a row where GitHub allows it, and Delete. The coverage table's rows
for each come from :meth:`ResourceSpec.endpoints`. Paths are checked against
GitHub's API description by the coverage gate. wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.resource_engine import Field, ResourceSpec
from quill.core.github.resource_specs_env import REPO_ORG_SPECS
from quill.core.github.resource_specs_more import MORE_SPECS
from quill.core.github.resource_specs_people import PEOPLE_SPECS
from quill.core.github.resource_specs_security import SECURITY_SPECS
from quill.core.github.resource_specs_user import USER_SPECS

__all__ = ["RESOURCE_SPECS", "spec_for"]


def _day(raw: Mapping[str, Any], key: str = "updated_at") -> str:
    value = str(raw.get(key) or "")[:10]
    return f", changed {value}" if value else ""


def _secret(raw: Mapping[str, Any]) -> str:
    shown = f", for {raw['visibility']} repositories" if raw.get("visibility") else ""
    return f"Secret {raw.get('name')}{shown}{_day(raw)}. Its value is never shown."


def _variable(raw: Mapping[str, Any]) -> str:
    shown = f", for {raw['visibility']} repositories" if raw.get("visibility") else ""
    return f"{raw.get('name')} is {raw.get('value')!s}{shown}{_day(raw)}."


def _login(raw: Mapping[str, Any]) -> str:
    return str(raw.get("login") or "someone")


_SECRET_NEW = (
    Field("name", "The secret's name, such as DEPLOY_TOKEN:", is_id=True),
    Field("value", "Its value. It is sealed before it leaves this computer:", kind="secret"),
)
_VISIBILITY = Field(
    "visibility",
    "Which of the organization's repositories may use it?",
    "choice",
    ("all", "private"),
)
_VARIABLE_NEW = (
    Field("name", "The variable's name, such as RELEASE_CHANNEL:"),
    Field("value", "Its value:"),
)


def _secrets(
    key: str, label: str, scope: str, parent: str, where: str, page: str, help_: str
) -> ResourceSpec:
    org = scope == "organization"
    return ResourceSpec(
        key=key,
        label=label,
        scope=scope,
        parent=parent,
        noun="secret",
        list_path=f"{{base}}/{where}/secrets",
        items_key="secrets",
        id_param="{secret_name}",
        sentence=_secret,
        help=help_,
        page=page,
        create=(*_SECRET_NEW, _VISIBILITY) if org else _SECRET_NEW,
        create_method="PUT",
        create_path="{list}/{id}",
        seal=True,
        repositories="/repositories" if scope != "repository" else "",
    )


def _variables(
    key: str, label: str, scope: str, parent: str, where: str, page: str, help_: str
) -> ResourceSpec:
    org = scope == "organization"
    return ResourceSpec(
        key=key,
        label=label,
        scope=scope,
        parent=parent,
        noun="variable",
        list_path=f"{{base}}/{where}/variables",
        items_key="variables",
        sentence=_variable,
        help=help_,
        page=page,
        create=(*_VARIABLE_NEW, _VISIBILITY) if org else _VARIABLE_NEW,
        edit=(Field("value", "The new value:"),),
        repositories="/repositories" if org else "",
    )


_REPO_SETTINGS = "https://github.com/{target}/settings"
_ORG_SETTINGS = "https://github.com/organizations/{target}/settings"

RESOURCE_SPECS: tuple[ResourceSpec, ...] = (
    # -- a repository --------------------------------------------------------------------
    _variables(
        "actions_variables",
        "Actions Variables",
        "repository",
        "settings",
        "actions",
        f"{_REPO_SETTINGS}/variables/actions",
        "Actions Variables: values workflows read as vars.NAME. Ctrl+N adds one.",
    ),
    _secrets(
        "actions_secrets",
        "Actions Secrets",
        "repository",
        "settings",
        "actions",
        f"{_REPO_SETTINGS}/secrets/actions",
        "Actions Secrets: values workflows read but nobody sees again. Ctrl+N adds one.",
    ),
    _secrets(
        "dependabot_secrets",
        "Dependabot Secrets",
        "repository",
        "settings",
        "dependabot",
        f"{_REPO_SETTINGS}/secrets/dependabot",
        "Dependabot Secrets: what Dependabot uses to reach private registries.",
    ),
    _secrets(
        "codespaces_secrets",
        "Codespaces Secrets",
        "repository",
        "settings",
        "codespaces",
        f"{_REPO_SETTINGS}/secrets/codespaces",
        "Codespaces Secrets: values given to every codespace of this repository.",
    ),
    _secrets(
        "agent_secrets",
        "Copilot Agent Secrets",
        "repository",
        "settings",
        "agents",
        f"{_REPO_SETTINGS}/copilot/coding_agent",
        "Copilot Agent Secrets: values the Copilot coding agent may use here.",
    ),
    _variables(
        "agent_variables",
        "Copilot Agent Variables",
        "repository",
        "settings",
        "agents",
        f"{_REPO_SETTINGS}/copilot/coding_agent",
        "Copilot Agent Variables: values the Copilot coding agent reads here.",
    ),
    ResourceSpec(
        key="artifacts",
        label="Artifacts",
        scope="repository",
        parent="actions",
        noun="artifact",
        list_path="{base}/actions/artifacts",
        items_key="artifacts",
        id_field="id",
        id_param="{artifact_id}",
        sentence=lambda raw: (
            f"{raw.get('name')}, {int(raw.get('size_in_bytes') or 0):,} bytes"
            + (", expired" if raw.get("expired") else "")
            + _day(raw, "created_at").replace("changed", "made")
            + "."
        ),
        help="Artifacts: files workflow runs kept, such as builds and test reports.",
        page="https://github.com/{target}/actions",
    ),
    ResourceSpec(
        key="repo_invitations",
        label="Invitations",
        scope="repository",
        parent="people",
        noun="invitation",
        list_path="{base}/invitations",
        id_field="id",
        id_param="{invitation_id}",
        sentence=lambda raw: (
            f"{_login(raw.get('invitee') or {})} is invited with {raw.get('permissions')} access"
            + _day(raw, "created_at").replace("changed", "since")
            + "."
        ),
        help="Invitations: people asked to join this repository who have not answered yet.",
        page=f"{_REPO_SETTINGS}/access",
        edit=(
            Field(
                "permissions",
                "The access to offer:",
                "choice",
                ("read", "triage", "write", "maintain", "admin"),
            ),
        ),
    ),
    ResourceSpec(
        key="repo_issue_types",
        label="Issue Types",
        scope="repository",
        parent="settings",
        noun="issue type",
        list_path="{base}/issue-types",
        id_field="id",
        sentence=lambda raw: f"{raw.get('name')}: {raw.get('description') or 'no description'}.",
        help="Issue Types: the kinds of issue this repository offers, set by its organization.",
        page="https://github.com/{target}/issues",
        delete=False,
    ),
    # -- an organization -----------------------------------------------------------------
    _variables(
        "org_actions_variables",
        "Actions Variables",
        "organization",
        "organization",
        "actions",
        f"{_ORG_SETTINGS}/variables/actions",
        "Actions Variables: values every chosen repository's workflows read.",
    ),
    _secrets(
        "org_actions_secrets",
        "Actions Secrets",
        "organization",
        "organization",
        "actions",
        f"{_ORG_SETTINGS}/secrets/actions",
        "Actions Secrets: values the organization's workflows read but nobody sees again.",
    ),
    _secrets(
        "org_dependabot_secrets",
        "Dependabot Secrets",
        "organization",
        "organization",
        "dependabot",
        f"{_ORG_SETTINGS}/secrets/dependabot",
        "Dependabot Secrets: what Dependabot uses across the organization.",
    ),
    _secrets(
        "org_codespaces_secrets",
        "Codespaces Secrets",
        "organization",
        "organization",
        "codespaces",
        f"{_ORG_SETTINGS}/secrets/codespaces",
        "Codespaces Secrets: values given to the organization's codespaces.",
    ),
    _secrets(
        "org_agent_secrets",
        "Copilot Agent Secrets",
        "organization",
        "organization",
        "agents",
        f"{_ORG_SETTINGS}/copilot",
        "Copilot Agent Secrets: values the coding agent may use in the organization.",
    ),
    _variables(
        "org_agent_variables",
        "Copilot Agent Variables",
        "organization",
        "organization",
        "agents",
        f"{_ORG_SETTINGS}/copilot",
        "Copilot Agent Variables: values the coding agent reads in the organization.",
    ),
    ResourceSpec(
        key="runner_groups",
        label="Runner Groups",
        scope="organization",
        parent="organization",
        noun="runner group",
        list_path="{base}/actions/runner-groups",
        items_key="runner_groups",
        id_field="id",
        id_param="{runner_group_id}",
        sentence=lambda raw: (
            f"{raw.get('name')}: for {raw.get('visibility')} repositories"
            + (", the default group" if raw.get("default") else "")
            + "."
        ),
        help="Runner Groups: which repositories may use which of the organization's runners.",
        page=f"{_ORG_SETTINGS}/actions/runner-groups",
        repositories="/repositories",
        create=(
            Field("name", "The group's name:"),
            Field(
                "visibility",
                "Which repositories may use it?",
                "choice",
                ("all", "private", "selected"),
            ),
        ),
        edit=(Field("name", "Its new name:"),),
    ),
    ResourceSpec(
        key="org_runners",
        label="Runners",
        scope="organization",
        parent="organization",
        noun="runner",
        list_path="{base}/actions/runners",
        items_key="runners",
        id_field="id",
        id_param="{runner_id}",
        sentence=lambda raw: (
            f"{raw.get('name')}: {raw.get('status')}"
            + (", busy" if raw.get("busy") else "")
            + f", {raw.get('os')}."
        ),
        help="Runners: the organization's own machines that run jobs.",
        page=f"{_ORG_SETTINGS}/actions/runners",
    ),
    ResourceSpec(
        key="hosted_runners",
        label="Larger Runners",
        scope="organization",
        parent="organization",
        noun="larger runner",
        list_path="{base}/actions/hosted-runners",
        items_key="runners",
        id_field="id",
        id_param="{hosted_runner_id}",
        sentence=lambda raw: (
            f"{raw.get('name')}: {raw.get('status')}, {raw.get('platform')}"
            + (
                f", {(raw.get('machine_size_details') or {}).get('cpu_cores')} cores"
                if raw.get("machine_size_details")
                else ""
            )
            + "."
        ),
        help="Larger Runners: GitHub's bigger machines the organization pays for.",
        page=f"{_ORG_SETTINGS}/actions/runners",
        edit=(Field("name", "Its new name:"),),
    ),
    ResourceSpec(
        key="org_members",
        label="Members",
        scope="organization",
        parent="organization",
        noun="member",
        list_path="{base}/members",
        id_field="login",
        id_param="{username}",
        sentence=lambda raw: f"{_login(raw)}.",
        help="Members: the organization's people. Ctrl+N invites someone; Delete removes them.",
        page="https://github.com/orgs/{target}/people",
        create=(
            Field("username", "Their GitHub username:", is_id=True),
            Field("role", "Their role:", "choice", ("member", "admin")),
        ),
        create_method="PUT",
        create_path="{base}/memberships/{id}",
    ),
    ResourceSpec(
        key="org_invitations",
        label="Invitations",
        scope="organization",
        parent="organization",
        noun="invitation",
        list_path="{base}/invitations",
        id_field="id",
        id_param="{invitation_id}",
        sentence=lambda raw: (
            f"{raw.get('login') or raw.get('email')} is invited as {raw.get('role')}"
            + _day(raw, "created_at").replace("changed", "since")
            + "."
        ),
        help="Invitations: people asked to join the organization who have not answered.",
        page="https://github.com/orgs/{target}/people/pending_invitations",
        create=(
            Field("email", "Their email address:"),
            Field("role", "Their role:", "choice", ("direct_member", "admin", "billing_manager")),
        ),
    ),
    ResourceSpec(
        key="org_blocks",
        label="Blocked People",
        scope="organization",
        parent="organization",
        noun="blocked person",
        list_path="{base}/blocks",
        id_field="login",
        id_param="{username}",
        sentence=lambda raw: f"{_login(raw)} is blocked.",
        help="Blocked People: who cannot take part in the organization's repositories.",
        page=f"{_ORG_SETTINGS}/blocked_users",
        create=(Field("username", "The username to block:", is_id=True),),
        create_method="PUT",
        create_path="{list}/{id}",
    ),
    ResourceSpec(
        key="outside_collaborators",
        label="Outside Collaborators",
        scope="organization",
        parent="organization",
        noun="outside collaborator",
        list_path="{base}/outside_collaborators",
        id_field="login",
        id_param="{username}",
        sentence=lambda raw: f"{_login(raw)}, not a member, with access to some repositories.",
        help="Outside Collaborators: people with access to repositories but not members.",
        page="https://github.com/orgs/{target}/outside-collaborators",
    ),
    ResourceSpec(
        key="security_managers",
        label="Security Managers",
        scope="organization",
        parent="organization",
        noun="security manager team",
        list_path="{base}/security-managers",
        id_field="slug",
        id_param="{team_slug}",
        item_path="{base}/security-managers/teams/{id}",
        sentence=lambda raw: f"The team {raw.get('name')} manages security alerts.",
        help="Security Managers: teams that see and manage every security alert.",
        page=f"{_ORG_SETTINGS}/security_analysis",
        create=(Field("team", "The team's short name (slug):", is_id=True),),
        create_method="PUT",
        create_path="{base}/security-managers/teams/{id}",
    ),
    ResourceSpec(
        key="custom_properties",
        label="Custom Properties",
        scope="organization",
        parent="organization",
        noun="custom property",
        list_path="{base}/properties/schema",
        id_field="property_name",
        id_param="{custom_property_name}",
        sentence=lambda raw: (
            f"{raw.get('property_name')}: {raw.get('value_type')}"
            + (", required" if raw.get("required") else "")
            + (f", default {raw['default_value']}" if raw.get("default_value") else "")
            + "."
        ),
        help="Custom Properties: labels the organization gives its repositories.",
        page=f"{_ORG_SETTINGS}/custom-properties",
        create=(
            Field("name", "The property's name:", is_id=True),
            Field(
                "value_type",
                "What kind of value?",
                "choice",
                ("string", "single_select", "multi_select", "true_false"),
            ),
            Field(
                "allowed_values",
                "For a select, its choices, separated by commas:",
                "list",
                optional=True,
            ),
            Field("description", "A description, or leave it empty:", optional=True),
        ),
        create_method="PUT",
        create_path="{list}/{id}",
    ),
    ResourceSpec(
        key="org_issue_types",
        label="Issue Types",
        scope="organization",
        parent="organization",
        noun="issue type",
        list_path="{base}/issue-types",
        id_field="id",
        id_param="{issue_type_id}",
        sentence=lambda raw: (
            f"{raw.get('name')}: {raw.get('description') or 'no description'}"
            + ("" if raw.get("is_enabled", True) else ", turned off")
            + "."
        ),
        help="Issue Types: the kinds of issue, such as Bug, the organization's repositories offer.",
        page=f"{_ORG_SETTINGS}/issue-types",
        create=(
            Field("name", "The type's name, such as Bug:"),
            Field("description", "A description, or leave it empty:", optional=True),
            Field("is_enabled", "Turn it on now?", "bool"),
        ),
        edit=(Field("name", "Its name:"), Field("is_enabled", "Turned on?", "bool")),
        edit_method="PUT",
    ),
    ResourceSpec(
        key="org_roles",
        label="Organization Roles",
        scope="organization",
        parent="organization",
        noun="organization role",
        list_path="{base}/organization-roles",
        items_key="roles",
        id_field="id",
        id_param="{role_id}",
        sentence=lambda raw: (
            f"{raw.get('name')}: {raw.get('description') or 'no description'}, "
            f"{len(raw.get('permissions') or ())} permissions."
        ),
        help="Organization Roles: the roles that can be given to people and teams.",
        page=f"{_ORG_SETTINGS}/roles",
        delete=False,
    ),
    # -- you -----------------------------------------------------------------------------
    _secrets(
        "my_codespaces_secrets",
        "My Codespaces Secrets",
        "user",
        "people",
        "codespaces",
        "https://github.com/settings/codespaces",
        "My Codespaces Secrets: values given to your own codespaces.",
    ),
    *SECURITY_SPECS,
    *REPO_ORG_SPECS,
    *USER_SPECS,
    *MORE_SPECS,
    *PEOPLE_SPECS,
)

_BY_KEY = {spec.key: spec for spec in RESOURCE_SPECS}


def spec_for(key: str) -> ResourceSpec | None:
    return _BY_KEY.get(key)
