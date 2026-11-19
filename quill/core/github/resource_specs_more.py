"""More list-shaped settings for the resource engine (GitHub PRD sections 16 to 19).

The second sweep through the planned endpoints: lists that read as rows of
sentences, with Ctrl+N to add, Change and Delete where GitHub allows them.

* **Your account:** issue fields for your own repositories, the GitHub Apps you
  have installed (and which repositories each may reach), your public email
  addresses, the repositories you watch, and the gists you starred.
* **An organization:** its issue fields, invitations that failed, public
  members, installed apps, the repositories immutable releases are enforced
  on, the repositories allowed to run Actions and to use self-hosted runners,
  and its Dependabot alerts, secret scanning alerts, security advisories,
  recent events and custom property values across repositories.
* **A repository:** every issue comment, commit comments (change and delete),
  watchers, activity (pushes and merges), CODEOWNERS errors, rule insights,
  your notifications in it, and its custom property values.
Environments' own lists are in :mod:`quill.core.github.resource_specs_env_more`.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.access_matrix import property_rows
from quill.core.github.resource_engine import Field, ResourceSpec
from quill.core.github.sheet_fields import dig

__all__ = ["MORE_SPECS"]

_ORG_SETTINGS = "https://github.com/organizations/{target}/settings"
_REPO = "https://github.com/{target}"


def _day(raw: Mapping[str, Any], key: str = "updated_at") -> str:
    value = str(raw.get(key) or "")[:10]
    return f", {value}" if value else ""


def _repo_name(raw: Mapping[str, Any]) -> str:
    return f"{raw.get('full_name') or raw.get('name') or raw.get('id')}."


def _issue_field(raw: Mapping[str, Any]) -> str:
    kind = str(raw.get("data_type") or "text").replace("_", " ")
    options = [str(o.get("name")) for o in raw.get("options") or () if isinstance(o, Mapping)]
    choices = f": {', '.join(options)}" if options else ""
    about = f". {raw['description']}" if raw.get("description") else ""
    return f"{raw.get('name')}, {kind}{choices}{about}."


_ISSUE_FIELD_NEW = (
    Field("name", "The field's name, such as Priority:"),
    Field(
        "data_type",
        "What kind of value does it hold?",
        "choice",
        ("text", "number", "date", "single_select"),
    ),
    Field(
        "options", "For a single select, its choices, separated by commas:", "names", optional=True
    ),
    Field("description", "A description, or leave it empty:", optional=True),
)
_ISSUE_FIELD_EDIT = (
    Field("name", "Its name:"),
    Field("description", "Its description, or leave it empty:", optional=True),
    Field(
        "options", "For a single select, its choices, separated by commas:", "names", optional=True
    ),
)


def _repository_list(
    key: str, label: str, list_path: str, noun: str, help_: str, page: str
) -> ResourceSpec:
    """An organization setting that applies to chosen repositories: add one by name."""
    return ResourceSpec(
        key=key,
        label=label,
        scope="organization",
        parent="organization",
        noun=noun,
        list_path=list_path,
        items_key="repositories",
        id_field="id",
        id_param="{repository_id}",
        sentence=_repo_name,
        help=help_,
        page=page,
        create=(
            Field(
                "repository",
                "The repository, as owner/name or its name here:",
                "repository",
                is_id=True,
            ),
        ),
        create_method="PUT",
        create_path="{list}/{id}",
    )


def _reach(raw: Mapping[str, Any]) -> str:
    chosen = raw.get("repository_selection") == "all"
    return "all repositories" if chosen else "chosen repositories"


_RESULTS = {"pass": "Passed", "fail": "Blocked", "bypass": "Bypassed"}


def _event(raw: Mapping[str, Any]) -> str:
    who = dig(raw, "actor", "login") or "Someone"
    what = str(raw.get("type") or "").removesuffix("Event")
    where = dig(raw, "repo", "name") or "a repository"
    return f"{who}: {what} in {where}{_day(raw, 'created_at')}."


def _judged(raw: Mapping[str, Any]) -> str:
    result = _RESULTS.get(str(raw.get("result")), "Judged")
    ref = str(raw.get("ref") or "").removeprefix("refs/heads/")
    return (
        f"{result}: {raw.get('actor_name') or 'someone'} pushed to {ref}{_day(raw, 'pushed_at')}."
    )


def _alert(raw: Mapping[str, Any], what: str) -> str:
    where = dig(raw, "repository", "full_name") or "A repository"
    return f"{where}: {what}, {raw.get('state') or 'open'}{_day(raw, 'created_at')}."


MORE_SPECS: tuple[ResourceSpec, ...] = (
    # -- your account ------------------------------------------------------------------------
    ResourceSpec(
        key="my_issue_fields",
        label="My Issue Fields",
        scope="user",
        parent="people",
        noun="issue field",
        list_path="{base}/issue-fields",
        id_field="id",
        items_key="issue_fields",
        id_param="{issue_field_id}",
        sentence=_issue_field,
        help="My Issue Fields: values your own repositories' issues can carry. Ctrl+N adds one.",
        page="https://github.com/settings",
        create=_ISSUE_FIELD_NEW,
        edit=_ISSUE_FIELD_EDIT,
    ),
    ResourceSpec(
        key="my_installations",
        label="My Installed Apps",
        scope="user",
        parent="people",
        noun="installed app",
        list_path="{base}/installations",
        items_key="installations",
        id_field="id",
        id_param="{installation_id}",
        sentence=lambda raw: (
            f"{raw.get('app_slug') or 'An app'} on {dig(raw, 'account', 'login') or 'an account'}, "
            f"{_reach(raw)}."
        ),
        help=(
            "My Installed Apps: the GitHub Apps installed where you can manage them. "
            "Repositories... chooses which repositories an app may reach."
        ),
        page="https://github.com/settings/installations",
        delete=False,
        repositories="/repositories",
    ),
    ResourceSpec(
        key="my_public_emails",
        label="My Public Email Addresses",
        scope="user",
        parent="people",
        noun="public email address",
        list_path="{base}/public_emails",
        id_field="email",
        sentence=lambda raw: f"{raw.get('email')}{', primary' if raw.get('primary') else ''}.",
        help="My Public Email Addresses: the addresses anyone can see on your profile.",
        page="https://github.com/settings/emails",
        delete=False,
    ),
    ResourceSpec(
        key="my_watching",
        label="Repositories I Watch",
        scope="user",
        parent="people",
        noun="watched repository",
        list_path="{base}/subscriptions",
        id_field="full_name",
        sentence=_repo_name,
        help="Repositories I Watch: every repository you get notifications for.",
        page="https://github.com/watching",
        delete=False,
    ),
    ResourceSpec(
        key="my_starred_gists",
        label="Gists I Starred",
        scope="user",
        parent="gists",
        noun="starred gist",
        list_path="/gists/starred",
        id_field="id",
        sentence=lambda raw: (
            f"{raw.get('description') or ', '.join(raw.get('files') or {}) or 'A gist'} "
            f"by {dig(raw, 'owner', 'login') or 'someone'}."
        ),
        help="Gists I Starred: gists you starred, newest first.",
        page="https://gist.github.com/starred",
        delete=False,
    ),
    # -- an organization ---------------------------------------------------------------------
    ResourceSpec(
        key="org_issue_fields",
        label="Issue Fields",
        scope="organization",
        parent="organization",
        noun="issue field",
        list_path="{base}/issue-fields",
        id_field="id",
        items_key="issue_fields",
        id_param="{issue_field_id}",
        sentence=_issue_field,
        help=(
            "Issue Fields: values every repository's issues in this organization can carry, "
            "such as Priority or Due date. Ctrl+N adds one."
        ),
        page=f"{_ORG_SETTINGS}/issue-fields",
        create=(
            *_ISSUE_FIELD_NEW,
            Field(
                "visibility",
                "Who can see its values?",
                "choice",
                ("all", "organization_members_only"),
                optional=True,
            ),
        ),
        edit=_ISSUE_FIELD_EDIT,
    ),
    ResourceSpec(
        key="org_failed_invitations",
        label="Failed Invitations",
        scope="organization",
        parent="organization",
        noun="failed invitation",
        list_path="{base}/failed_invitations",
        id_field="id",
        sentence=lambda raw: (
            f"{raw.get('login') or raw.get('email') or 'Someone'}: "
            f"{raw.get('failed_reason') or 'the invitation failed'}{_day(raw, 'failed_at')}."
        ),
        help="Failed Invitations: invitations that expired or could not be delivered.",
        page=f"{_ORG_SETTINGS}/people",
        delete=False,
    ),
    ResourceSpec(
        key="org_public_members",
        label="Public Members",
        scope="organization",
        parent="organization",
        noun="public member",
        list_path="{base}/public_members",
        id_field="login",
        sentence=lambda raw: f"{raw.get('login')} shows membership publicly.",
        help="Public Members: members who show their membership on their profile.",
        page="https://github.com/orgs/{target}/people",
        delete=False,
    ),
    ResourceSpec(
        key="org_installations",
        label="Installed Apps",
        scope="organization",
        parent="organization",
        noun="installed app",
        list_path="{base}/installations",
        items_key="installations",
        id_field="id",
        sentence=lambda raw: f"{raw.get('app_slug') or 'An app'}, {_reach(raw)}.",
        help="Installed Apps: the GitHub Apps installed on this organization.",
        page=f"{_ORG_SETTINGS}/installations",
        delete=False,
    ),
    _repository_list(
        "org_immutable_release_repos",
        "Immutable Releases: Repositories",
        "{base}/settings/immutable-releases/repositories",
        "repository",
        "Immutable Releases: Repositories: where published releases cannot be changed, when "
        "the organization enforces it on chosen repositories. Ctrl+N adds one.",
        f"{_ORG_SETTINGS}/repository-defaults",
    ),
    _repository_list(
        "org_actions_repos",
        "Actions: Allowed Repositories",
        "{base}/actions/permissions/repositories",
        "repository",
        "Actions: Allowed Repositories: which repositories may run Actions, when the "
        "organization allows chosen repositories only. Ctrl+N adds one.",
        f"{_ORG_SETTINGS}/actions",
    ),
    _repository_list(
        "org_runner_repos",
        "Self-hosted Runners: Allowed Repositories",
        "{base}/actions/permissions/self-hosted-runners/repositories",
        "repository",
        "Self-hosted Runners: Allowed Repositories: which repositories may use the "
        "organization's self-hosted runners. Ctrl+N adds one.",
        f"{_ORG_SETTINGS}/actions",
    ),
    ResourceSpec(
        key="org_dependabot_alerts",
        label="Dependabot Alerts",
        scope="organization",
        parent="organization",
        noun="alert",
        list_path="{base}/dependabot/alerts",
        id_field="number",
        sentence=lambda raw: _alert(
            raw,
            f"{dig(raw, 'dependency', 'package', 'name') or 'a package'} "
            f"({dig(raw, 'security_advisory', 'severity') or 'unrated'})",
        ),
        help="Dependabot Alerts: every repository's vulnerable dependencies in one list.",
        page="https://github.com/orgs/{target}/security/alerts/dependabot",
        delete=False,
    ),
    ResourceSpec(
        key="org_secret_alerts",
        label="Secret Scanning Alerts",
        scope="organization",
        parent="organization",
        noun="alert",
        list_path="{base}/secret-scanning/alerts",
        id_field="number",
        sentence=lambda raw: _alert(raw, str(raw.get("secret_type_display_name") or "a secret")),
        help=(
            "Secret Scanning Alerts: secrets found in any repository. The secret itself is "
            "never shown here."
        ),
        page="https://github.com/orgs/{target}/security/alerts/secret-scanning",
        delete=False,
    ),
    ResourceSpec(
        key="org_advisories",
        label="Security Advisories",
        scope="organization",
        parent="organization",
        noun="advisory",
        list_path="{base}/security-advisories",
        id_field="ghsa_id",
        sentence=lambda raw: (
            f"{raw.get('ghsa_id')}: {raw.get('summary') or 'an advisory'}, "
            f"{raw.get('severity') or 'unrated'}, {raw.get('state') or 'draft'}."
        ),
        help="Security Advisories: the repository advisories across this organization.",
        page="https://github.com/orgs/{target}/security",
        delete=False,
    ),
    ResourceSpec(
        key="org_events",
        label="Recent Events",
        scope="organization",
        parent="organization",
        noun="event",
        list_path="{base}/events",
        id_field="id",
        sentence=_event,
        help="Recent Events: the organization's public activity, newest first.",
        page="https://github.com/{target}",
        delete=False,
    ),
    ResourceSpec(
        key="org_property_values",
        label="Custom Property Values",
        scope="organization",
        parent="organization",
        noun="repository's values",
        list_path="{base}/properties/values",
        id_field="repository_full_name",
        sentence=lambda raw: (
            f"{raw.get('repository_full_name')}: "
            + (
                "; ".join(
                    f"{p.get('property_name')} is {p.get('value')}"
                    for p in raw.get("properties") or ()
                    if isinstance(p, Mapping)
                )
                or "no values"
            )
            + "."
        ),
        help=(
            "Custom Property Values: every repository and every custom property, a row a "
            "repository, with unset properties said as not set. Change a repository's on its "
            "Properties, or several at once with Set Repositories' Custom Property... on the "
            "organization."
        ),
        page=f"{_ORG_SETTINGS}/custom-properties",
        delete=False,
        reader=property_rows,
    ),
    # -- a repository ------------------------------------------------------------------------
    ResourceSpec(
        key="repo_issue_comments",
        label="All Issue Comments",
        scope="repository",
        parent="activity",
        noun="comment",
        list_path="{base}/issues/comments",
        id_field="id",
        sentence=lambda raw: (
            f"{dig(raw, 'user', 'login') or 'Someone'} on "
            f"#{str(raw.get('issue_url') or '').rsplit('/', 1)[-1]}{_day(raw)}: "
            f"{' '.join(str(raw.get('body') or '').split())[:120]}"
        ),
        help="All Issue Comments: every comment on the repository's issues, newest changes last.",
        page=f"{_REPO}/issues",
        delete=False,
    ),
    ResourceSpec(
        key="commit_comments",
        label="Commit Comments",
        scope="repository",
        parent="code",
        noun="commit comment",
        list_path="{base}/comments",
        id_field="id",
        id_param="{comment_id}",
        sentence=lambda raw: (
            f"{dig(raw, 'user', 'login') or 'Someone'} on {str(raw.get('commit_id') or '')[:7]}"
            f"{' ' + str(raw['path']) if raw.get('path') else ''}{_day(raw)}: "
            f"{' '.join(str(raw.get('body') or '').split())[:120]}"
        ),
        help="Commit Comments: comments on the repository's commits. Change rewrites your own.",
        page=f"{_REPO}/commits",
        edit=(Field("body", "The comment:", "multiline"),),
    ),
    ResourceSpec(
        key="repo_watchers",
        label="Watchers",
        scope="repository",
        parent="people",
        noun="watcher",
        list_path="{base}/subscribers",
        id_field="login",
        sentence=lambda raw: f"{raw.get('login')} watches this repository.",
        help="Watchers: who gets notifications for this repository.",
        page=f"{_REPO}/watchers",
        delete=False,
    ),
    ResourceSpec(
        key="repo_push_activity",
        label="Push Activity",
        scope="repository",
        parent="activity",
        noun="push",
        list_path="{base}/activity",
        id_field="id",
        sentence=lambda raw: (
            f"{dig(raw, 'actor', 'login') or 'Someone'}: "
            f"{str(raw.get('activity_type') or 'push').replace('_', ' ')} to "
            f"{str(raw.get('ref') or '').removeprefix('refs/heads/')}{_day(raw, 'timestamp')}."
        ),
        help="Push Activity: pushes, force pushes, merges and branch changes, newest first.",
        page=f"{_REPO}/activity",
        delete=False,
    ),
    ResourceSpec(
        key="codeowners_errors",
        label="CODEOWNERS Problems",
        scope="repository",
        parent="settings",
        noun="CODEOWNERS problem",
        list_path="{base}/codeowners/errors",
        items_key="errors",
        id_field="line",
        sentence=lambda raw: (
            (
                f"Line {raw.get('line')}: {raw.get('message') or raw.get('kind') or 'a problem'}"
                f"{' (' + str(raw['suggestion']) + ')' if raw.get('suggestion') else ''}"
            ).rstrip(".")
            + "."
        ),
        help="CODEOWNERS Problems: lines in the CODEOWNERS file GitHub could not use.",
        page=f"{_REPO}/blob/HEAD/.github/CODEOWNERS",
        delete=False,
    ),
    ResourceSpec(
        key="repo_rule_insights",
        label="Rule Insights",
        scope="repository",
        parent="settings",
        noun="judged push",
        list_path="{base}/rulesets/rule-suites",
        id_field="id",
        sentence=_judged,
        help="Rule Insights: recent pushes the rulesets here passed, blocked or let through.",
        page=f"{_REPO}/rules/insights",
        delete=False,
    ),
    ResourceSpec(
        key="repo_my_notifications",
        label="My Notifications Here",
        scope="repository",
        parent="activity",
        noun="notification",
        list_path="{base}/notifications",
        id_field="id",
        sentence=lambda raw: (
            f"{dig(raw, 'subject', 'type') or 'Something'}: {dig(raw, 'subject', 'title') or ''}, "
            f"{str(raw.get('reason') or '').replace('_', ' ')}"
            f"{', unread' if raw.get('unread') else ''}."
        ),
        help="My Notifications Here: your notifications from this repository only.",
        page="https://github.com/notifications?query=repo%3A{target}",
        delete=False,
    ),
    ResourceSpec(
        key="repo_property_values",
        label="Custom Property Values",
        scope="repository",
        parent="settings",
        noun="custom property",
        list_path="{base}/properties/values",
        id_field="property_name",
        sentence=lambda raw: f"{raw.get('property_name')} is {raw.get('value') or 'not set'}.",
        help="Custom Property Values: the organization's custom properties, as set here.",
        page=f"{_REPO}/settings",
        delete=False,
    ),
)
