"""The Repository sheet: all eighteen pages of Appendix C (GitHub PRD sections 15, 16.7, 18.3).

General, You, Fork, Features, Merging, Branches and Rules, Access, Actions,
Environments, Security, Pages, Webhooks, Deploy Keys, Autolinks, Secrets and
Variables, Templates, Insights and Danger Zone. Settings an admin may change
are editable fields; lists (collaborators, teams, hooks, keys) are read here
and changed from the Access page's buttons and their own sheets, each change
previewed in words (section 18.4). A page whose read needs a role you do not
have stays empty and says so instead of failing the whole sheet.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.github.permissions import WriteTier, repo_role
from quill.core.github.sheet_engine import Ident, Read, SheetDef, Write
from quill.core.github.sheet_fields import dig, ed, page, patch, ro, toggle, when
from quill.core.github.sheet_rows import (
    autolink_row,
    collaborator_row,
    hook_row,
    invitation_row,
    key_row,
    rows_of,
    team_row,
)
from quill.core.workbench.properties import FieldKind, SheetSpec, Value

__all__ = ["REPOSITORY", "VIEWER_REPO_QUERY", "WATCH_LEVELS", "repo_variables"]

_O, _V, _A, _D = (
    WriteTier.ORGANIZING,
    WriteTier.VISIBLE,
    WriteTier.ACCESS,
    WriteTier.DESTRUCTIVE,
)
_K = FieldKind
_REPO = "/repos/{repo}"
_ADMIN = "repo:admin"

WATCH_LEVELS: tuple[str, ...] = ("participating and mentions", "all activity", "ignore")

VIEWER_REPO_QUERY = (
    "query($owner:String!,$name:String!){repository(owner:$owner,name:$name){id "
    "viewerPermission viewerCanAdminister viewerCanUpdateTopics viewerCanSubscribe "
    "viewerCanCreateProjects viewerHasStarred viewerSubscription}}"
)


def repo_variables(ident: Ident) -> dict[str, object]:
    owner, _, name = ident["repo"].partition("/")
    return {"owner": owner, "name": name}


def _flag(data: Mapping[str, Any], key: str) -> bool:
    return bool(data.get(key))


def _security(data: Mapping[str, Any], key: str) -> bool:
    return bool(dig(data, "security_and_analysis", key, "status") == "enabled")


def _repo(data: Mapping[str, Any]) -> dict[str, Value]:
    found: dict[str, Value] = {
        "full_name": str(data.get("full_name") or ""),
        "name": str(data.get("name") or ""),
        "description": str(data.get("description") or ""),
        "homepage": str(data.get("homepage") or ""),
        "topics": tuple(str(t) for t in data.get("topics") or ()),
        "visibility": str(
            data.get("visibility") or ("private" if data.get("private") else "public")
        ),
        "default_branch": str(data.get("default_branch") or ""),
        "license": str(dig(data, "license", "name") or ""),
        "language": str(data.get("language") or ""),
        "created": when(data.get("created_at")),
        "pushed": when(data.get("pushed_at")),
        "updated": str(data.get("updated_at") or ""),
        "url": str(data.get("html_url") or ""),
        "fork": _flag(data, "fork"),
        "parent": str(dig(data, "parent", "full_name") or ""),
        "source": str(dig(data, "source", "full_name") or ""),
        "stars": int(data.get("stargazers_count") or 0),
        "forks": int(data.get("forks_count") or 0),
        "watchers": int(data.get("subscribers_count") or 0),
        "open_issues": int(data.get("open_issues_count") or 0),
        "size": f"{int(data.get('size') or 0)} KB",
        "your_access": repo_role(data.get("permissions")),
        "archived": _flag(data, "archived"),
        "secret_scanning": _security(data, "secret_scanning"),
        "push_protection": _security(data, "secret_scanning_push_protection"),
    }
    for key in (
        "is_template",
        "has_issues",
        "has_projects",
        "has_wiki",
        "has_discussions",
        "allow_merge_commit",
        "allow_squash_merge",
        "allow_rebase_merge",
        "allow_auto_merge",
        "allow_update_branch",
        "delete_branch_on_merge",
        "allow_forking",
        "web_commit_signoff_required",
    ):
        found[key] = _flag(data, key)
    for key in (
        "squash_merge_commit_title",
        "squash_merge_commit_message",
        "merge_commit_title",
        "merge_commit_message",
    ):
        found[key] = str(data.get(key) or "")
    return found


def _viewer(data: Mapping[str, Any]) -> dict[str, Value]:
    repo = dig(data, "repository") or {}
    found: dict[str, Value] = {k: bool(v) for k, v in repo.items() if k.startswith("viewerCan")}
    found["node_id"] = str(repo.get("id") or "")
    found["starred"] = bool(repo.get("viewerHasStarred"))
    role = repo_role(repo.get("viewerPermission"))
    if role:
        found["your_access"] = role
    return found


def _watch(data: Mapping[str, Any]) -> dict[str, Value]:
    if data.get("ignored"):
        return {"watch": "ignore"}
    return {"watch": "all activity" if data.get("subscribed") else "participating and mentions"}


def _actions(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "actions_enabled": bool(data.get("enabled")),
        "allowed_actions": str(data.get("allowed_actions") or "all"),
    }


def _workflow_permissions(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "token_permission": str(data.get("default_workflow_permissions") or "read"),
        "actions_approve_prs": bool(data.get("can_approve_pull_request_reviews")),
    }


def _pages(data: Mapping[str, Any]) -> dict[str, Value]:
    return {
        "pages_url": str(data.get("html_url") or ""),
        "pages_source": " ".join(
            str(dig(data, "source", part) or "") for part in ("branch", "path")
        ).strip(),
        "pages_cname": str(data.get("cname") or ""),
        "pages_https": bool(data.get("https_enforced")),
    }


def _limits(data: Mapping[str, Any]) -> dict[str, Value]:
    limit = str(data.get("limit") or "none")
    return {"interaction_limit": limit.replace("_", " ")}


def _community(data: Mapping[str, Any]) -> dict[str, Value]:
    return {"health": f"{int(data.get('health_percentage') or 0)} percent"}


def _enabled(key: str) -> Any:
    return lambda data: {key: bool(data.get("enabled", True))}


def _watch_encode(value: Value, _c: Mapping[str, object], _i: Ident) -> dict[str, object]:
    word = str(value or "")
    if word == "all activity":
        return {"subscribed": True, "ignored": False}
    if word == "ignore":
        return {"subscribed": False, "ignored": True}
    return {"__method": "DELETE"}


def _security_encode(key: str) -> Any:
    def encode(value: Value, _c: Mapping[str, object], _i: Ident) -> dict[str, object]:
        status = "enabled" if value else "disabled"
        return {"security_and_analysis": {key: {"status": status}}}

    return encode


def _allowed(value: Value, _c: Mapping[str, object], _i: Ident) -> dict[str, object]:
    return {"enabled": True, "allowed_actions": str(value or "all")}


def _limit_encode(value: Value, _c: Mapping[str, object], _i: Ident) -> dict[str, object]:
    word = str(value or "none").replace(" ", "_")
    if word == "none":
        return {"__method": "DELETE"}
    return {"limit": word, "expiry": "one_week"}


def _admin_patch(tier: WriteTier = _A, body_key: str = "", encode: Any = None) -> Write:
    return patch(_REPO, _ADMIN, tier, body_key, encode)


_FLAGS_FEATURES = ("has_issues", "has_projects", "has_wiki", "has_discussions")
_FLAGS_MERGING = (
    "allow_merge_commit",
    "allow_squash_merge",
    "allow_rebase_merge",
    "allow_auto_merge",
    "allow_update_branch",
    "delete_branch_on_merge",
)

_GENERAL = page(
    "general",
    "General",
    ed("name", "Name", help="Renaming moves the repository; GitHub redirects the old address."),
    ed("description", "Description"),
    ed("homepage", "Website"),
    ed("topics", "Topics", _K.LIST, "Comma-separated, lower case, such as accessibility, python."),
    ed("default_branch", "Default branch", help="The branch pull requests target by default."),
    ro("full_name", "Full name"),
    ro("language", "Language"),
    ro("license", "License"),
    ro("created", "Created", _K.DATE),
    ro("pushed", "Last push", _K.DATE),
    ro("url", "Address", _K.LINK, "Ctrl+C copies it."),
)
_YOU = page(
    "you",
    "You",
    ed("starred", "Starred", _K.CHECK, "Star it to keep it in your stars and show support."),
    ed(
        "watch",
        "Watch level",
        _K.CHOICE,
        "All activity, only when participating or mentioned, or ignore it.",
        choices=WATCH_LEVELS,
    ),
    ro(
        "custom_watch",
        "Custom watching",
        help="Watching only issues, pull requests, releases, "
        "discussions or security alerts is set on GitHub's page; GitHub has no API for it. "
        "Open on GitHub, Shift+Enter, goes there.",
    ),
    ro("your_access", "Your access", help="Your role, as GitHub reports it."),
)
_FORK = page(
    "fork",
    "Fork",
    ro("fork", "Is a fork", _K.CHECK),
    ro("parent", "Forked from"),
    ro("source", "Original repository"),
    ed("allow_forking", "Allow forking", _K.CHECK, "For an organization's private repositories."),
)
_FEATURES = page(
    "features",
    "Features",
    ed("has_issues", "Issues", _K.CHECK),
    ed("has_projects", "Projects", _K.CHECK),
    ed("has_wiki", "Wiki", _K.CHECK),
    ed("has_discussions", "Discussions", _K.CHECK),
    ed("web_commit_signoff_required", "Require sign-off on web commits", _K.CHECK),
)
_MERGING = page(
    "merging",
    "Merging",
    ed("allow_merge_commit", "Allow merge commits", _K.CHECK),
    ed("allow_squash_merge", "Allow squash merging", _K.CHECK),
    ed("allow_rebase_merge", "Allow rebase merging", _K.CHECK),
    ed("allow_auto_merge", "Allow auto-merge", _K.CHECK),
    ed("allow_update_branch", "Always suggest updating branches", _K.CHECK),
    ed("delete_branch_on_merge", "Delete head branches after merging", _K.CHECK),
    ed(
        "squash_merge_commit_title",
        "Squash commit title",
        _K.CHOICE,
        choices=("PR_TITLE", "COMMIT_OR_PR_TITLE"),
    ),
    ed(
        "squash_merge_commit_message",
        "Squash commit message",
        _K.CHOICE,
        choices=("PR_BODY", "COMMIT_MESSAGES", "BLANK"),
    ),
    ed(
        "merge_commit_title", "Merge commit title", _K.CHOICE, choices=("PR_TITLE", "MERGE_MESSAGE")
    ),
    ed(
        "merge_commit_message",
        "Merge commit message",
        _K.CHOICE,
        choices=("PR_BODY", "PR_TITLE", "BLANK"),
    ),
)
_RULES = page(
    "rules",
    "Branches and Rules",
    ro(
        "rulesets",
        "Rulesets",
        _K.TABLE,
        "Each ruleset; its own sheet edits every rule and reads it back as sentences.",
    ),
)
_ACCESS = page(
    "access",
    "Access",
    ro(
        "collaborators",
        "People",
        _K.TABLE,
        "Who has access, their role and where it comes "
        "from. Add, Change Role and Remove act on the selected row, each previewed first.",
    ),
    ro("teams", "Teams", _K.TABLE),
    ro("invitations", "Pending invitations", _K.TABLE),
    ed(
        "interaction_limit",
        "Interaction limit",
        _K.CHOICE,
        "Limit who may comment and open issues and pull requests, for a week.",
        choices=("none", "existing users", "contributors only", "collaborators only"),
    ),
)
_ACTIONS = page(
    "actions",
    "Actions",
    ed("actions_enabled", "Actions enabled", _K.CHECK),
    ed(
        "allowed_actions",
        "Allowed actions",
        _K.CHOICE,
        "All, only this owner's, or selected.",
        choices=("all", "local_only", "selected"),
    ),
    ed("token_permission", "Default GITHUB_TOKEN permission", _K.CHOICE, choices=("read", "write")),
    ed("actions_approve_prs", "Allow Actions to create and approve pull requests", _K.CHECK),
)
_SECURITY = page(
    "security",
    "Security",
    ed("vulnerability_alerts", "Dependabot alerts", _K.CHECK),
    ed("security_fixes", "Dependabot security updates", _K.CHECK),
    ed("private_reporting", "Private vulnerability reporting", _K.CHECK),
    ed("secret_scanning", "Secret scanning", _K.CHECK),
    ed("push_protection", "Push protection", _K.CHECK),
)
_PAGES = page(
    "pages",
    "Pages",
    ro("pages_url", "Site address", _K.LINK),
    ro("pages_source", "Source"),
    ed("pages_cname", "Custom domain"),
    ed("pages_https", "Enforce HTTPS", _K.CHECK),
)

REPOSITORY = SheetDef(
    "repository",
    SheetSpec(
        "repository",
        "Repository",
        (
            _GENERAL,
            _YOU,
            _FORK,
            _FEATURES,
            _MERGING,
            _RULES,
            _ACCESS,
            _ACTIONS,
            page("environments", "Environments", ro("environments", "Environments", _K.TABLE)),
            _SECURITY,
            _PAGES,
            page("webhooks", "Webhooks", ro("hooks", "Webhooks", _K.TABLE)),
            page("deploy_keys", "Deploy Keys", ro("deploy_keys", "Deploy keys", _K.TABLE)),
            page("autolinks", "Autolinks", ro("autolinks", "Autolinks", _K.TABLE)),
            page(
                "secrets",
                "Secrets and Variables",
                ro(
                    "secrets",
                    "Secrets",
                    _K.TABLE,
                    "Names only: GitHub never shows a secret's value, and neither does QUILL.",
                ),
                ro("variables", "Variables", _K.TABLE),
            ),
            page(
                "templates",
                "Templates",
                ed(
                    "is_template",
                    "Template repository",
                    _K.CHECK,
                    "Let people create new repositories from this one.",
                ),
            ),
            page(
                "insights",
                "Insights",
                ro("stars", "Stars", _K.NUMBER),
                ro("forks", "Forks", _K.NUMBER),
                ro("watchers", "Watchers", _K.NUMBER),
                ro("open_issues", "Open issues and pull requests", _K.NUMBER),
                ro("size", "Size"),
                ro("health", "Community health"),
            ),
            page(
                "danger",
                "Danger Zone",
                ed(
                    "visibility",
                    "Visibility",
                    _K.CHOICE,
                    "Making a private repository public "
                    "shows its code, issues, Actions logs and wiki to everyone; the preview "
                    "says so and asks you to type the name.",
                    choices=("public", "private", "internal"),
                ),
                ed(
                    "archived",
                    "Archived",
                    _K.CHECK,
                    "An archived repository is read-only for everyone until it is unarchived.",
                ),
            ),
        ),
    ),
    (
        Read(_REPO, _repo),
        Read(graphql=VIEWER_REPO_QUERY, variables=repo_variables, extract=_viewer, optional=True),
        Read(
            _REPO + "/subscription",
            _watch,
            optional=True,
            fallback={"watch": "participating and mentions"},
        ),
        Read(_REPO + "/collaborators", rows_of("collaborators", collaborator_row), optional=True),
        Read(_REPO + "/teams", rows_of("teams", team_row), optional=True),
        Read(_REPO + "/invitations", rows_of("invitations", invitation_row), optional=True),
        Read(
            _REPO + "/rulesets",
            rows_of(
                "rulesets",
                lambda r: f"{r.get('name', '')}, {r.get('enforcement', '')}, id {r.get('id', '')}",
            ),
            optional=True,
        ),
        Read(
            _REPO + "/environments",
            rows_of("environments", lambda r: str(r.get("name", ""))),
            optional=True,
        ),
        Read(_REPO + "/hooks", rows_of("hooks", hook_row), optional=True),
        Read(_REPO + "/keys", rows_of("deploy_keys", key_row), optional=True),
        Read(_REPO + "/autolinks", rows_of("autolinks", autolink_row), optional=True),
        Read(
            _REPO + "/actions/secrets",
            rows_of("secrets", lambda r: str(r.get("name", ""))),
            optional=True,
        ),
        Read(
            _REPO + "/actions/variables",
            rows_of("variables", lambda r: f"{r.get('name', '')} = {r.get('value', '')}"),
            optional=True,
        ),
        Read(_REPO + "/actions/permissions", _actions, optional=True),
        Read(_REPO + "/actions/permissions/workflow", _workflow_permissions, optional=True),
        Read(_REPO + "/pages", _pages, optional=True),
        Read(
            _REPO + "/interaction-limits",
            _limits,
            optional=True,
            fallback={"interaction_limit": "none"},
        ),
        Read(
            _REPO + "/vulnerability-alerts",
            _enabled("vulnerability_alerts"),
            optional=True,
            fallback={"vulnerability_alerts": False},
        ),
        Read(
            _REPO + "/automated-security-fixes",
            _enabled("security_fixes"),
            optional=True,
            fallback={"security_fixes": False},
        ),
        Read(
            _REPO + "/private-vulnerability-reporting",
            _enabled("private_reporting"),
            optional=True,
            fallback={"private_reporting": False},
        ),
        Read(_REPO + "/community/profile", _community, optional=True),
    ),
    {
        "name": _admin_patch(),
        "description": _admin_patch(_V),
        "homepage": _admin_patch(_V),
        "topics": Write(
            _REPO + "/topics", "viewer:viewerCanUpdateTopics", _V, "PUT", "put", "names"
        ),
        "default_branch": _admin_patch(),
        "allow_forking": _admin_patch(),
        "web_commit_signoff_required": _admin_patch(),
        "is_template": _admin_patch(),
        "archived": _admin_patch(),
        "visibility": _admin_patch(_D),
        **{key: _admin_patch() for key in _FLAGS_FEATURES},
        **{key: _admin_patch() for key in _FLAGS_MERGING},
        **{
            key: _admin_patch()
            for key in (
                "squash_merge_commit_title",
                "squash_merge_commit_message",
                "merge_commit_title",
                "merge_commit_message",
            )
        },
        "secret_scanning": _admin_patch(encode=_security_encode("secret_scanning")),
        "push_protection": _admin_patch(encode=_security_encode("secret_scanning_push_protection")),
        "starred": toggle("/user/starred/{repo}", "sign_in", _O),
        "watch": Write(_REPO + "/subscription", "sign_in", _O, "PUT", "put", encode=_watch_encode),
        "interaction_limit": Write(
            _REPO + "/interaction-limits", _ADMIN, _A, "PUT", "put", encode=_limit_encode
        ),
        "actions_enabled": patch(
            _REPO + "/actions/permissions", _ADMIN, _A, "enabled", method="PUT"
        ),
        "allowed_actions": patch(
            _REPO + "/actions/permissions", _ADMIN, _A, encode=_allowed, method="PUT"
        ),
        "token_permission": patch(
            _REPO + "/actions/permissions/workflow",
            _ADMIN,
            _A,
            "default_workflow_permissions",
            method="PUT",
        ),
        "actions_approve_prs": patch(
            _REPO + "/actions/permissions/workflow",
            _ADMIN,
            _A,
            "can_approve_pull_request_reviews",
            method="PUT",
        ),
        "vulnerability_alerts": toggle(_REPO + "/vulnerability-alerts", _ADMIN, _A),
        "security_fixes": toggle(_REPO + "/automated-security-fixes", _ADMIN, _A),
        "private_reporting": toggle(_REPO + "/private-vulnerability-reporting", _ADMIN, _A),
        "pages_cname": patch(_REPO + "/pages", _ADMIN, _A, "cname", method="PUT"),
        "pages_https": patch(_REPO + "/pages", _ADMIN, _A, "https_enforced", method="PUT"),
    },
    title=lambda ident: ident["repo"],
    url=lambda ident: f"https://github.com/{ident['repo']}",
    renames=("name", "repo"),
)

#: The repository's people in the access matrix's words (Phase 10 reads them).
