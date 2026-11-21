"""Looking after a Project itself: drafts, fields, status updates, copies, links.

:mod:`quill.core.github.projects` reads a board and edits its items; this
module changes the project: add a draft issue, add or delete a field, post a
status update, link it to a repository, mark it as a template, copy it, and
delete it. All GraphQL, through the same transport (one host, one token).
Each mutation's reply is checked before the change is reported. No ``wx``;
strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date
from typing import Any

from quill.core.github.project_models import GitHubProjectsError
from quill.core.github.project_transport import request_graphql

__all__ = [
    "FIELD_TYPES",
    "STATUS_CHOICES",
    "add_draft_issue",
    "copy_project",
    "create_field",
    "delete_field",
    "delete_project",
    "link_repository",
    "post_status_update",
    "set_template",
]

#: ``(GraphQL data type, what it is called in a list)`` for a new field.
FIELD_TYPES: tuple[tuple[str, str], ...] = (
    ("TEXT", "Text"),
    ("NUMBER", "Number"),
    ("DATE", "Date"),
    ("SINGLE_SELECT", "Single select (a list of choices)"),
)

#: ``(GraphQL status, words)`` for a status update.
STATUS_CHOICES: tuple[tuple[str, str], ...] = (
    ("ON_TRACK", "On track"),
    ("AT_RISK", "At risk"),
    ("OFF_TRACK", "Off track"),
    ("COMPLETE", "Complete"),
    ("INACTIVE", "Inactive"),
)

Request = Callable[[str, str, dict[str, object]], dict[str, Any]]


def _mutate(
    token: str, operation: str, input_data: dict[str, object], returns: str, request: Request
) -> dict[str, Any]:
    if not token:
        raise GitHubProjectsError("Sign in to GitHub to change a Project.")
    input_type = f"{operation[0].upper()}{operation[1:]}Input"
    query = f"mutation($input:{input_type}!) {{ {operation}(input:$input) {{ {returns} }} }}"
    data = request(token, query, {"input": input_data})
    result = data.get(operation) if isinstance(data, dict) else None
    if not isinstance(result, dict):
        raise GitHubProjectsError(
            "GitHub did not confirm the change. Refresh to see what it holds."
        )
    return result


def _node_id(
    token: str,
    query: str,
    variables: dict[str, object],
    path: Sequence[str],
    what: str,
    request: Request,
) -> str:
    data: Any = request(token, query, variables)
    for key in path:
        data = data.get(key) if isinstance(data, dict) else None
    if not isinstance(data, str) or not data:
        raise GitHubProjectsError(f"GitHub has no {what} by that name.")
    return data


def repository_id(token: str, repository: str, request: Request = request_graphql) -> str:
    owner, _sep, name = repository.strip().partition("/")
    if not owner or not name:
        raise GitHubProjectsError("Type the repository as owner/name.")
    return _node_id(
        token,
        "query($o:String!,$n:String!){ repository(owner:$o,name:$n){ id } }",
        {"o": owner, "n": name},
        ("repository", "id"),
        f"repository {repository}",
        request,
    )


def owner_id(token: str, login: str, request: Request = request_graphql) -> str:
    """The node id of a user or organization, for a copy's new owner."""
    return _node_id(
        token,
        "query($l:String!){ repositoryOwner(login:$l){ id } }",
        {"l": login.strip()},
        ("repositoryOwner", "id"),
        f"user or organization {login}",
        request,
    )


def add_draft_issue(
    token: str, project_id: str, title: str, body: str = "", request: Request = request_graphql
) -> str:
    """Add a draft issue to the project; returns the new item's id."""
    if not title.strip():
        raise GitHubProjectsError("A draft issue needs a title.")
    result = _mutate(
        token,
        "addProjectV2DraftIssue",
        {"projectId": project_id, "title": title.strip(), "body": body},
        "projectItem { id }",
        request,
    )
    return str((result.get("projectItem") or {}).get("id", ""))


def create_field(
    token: str,
    project_id: str,
    name: str,
    data_type: str,
    options: Sequence[str] = (),
    request: Request = request_graphql,
) -> str:
    """Add a field; a single select needs at least one choice. Returns the field's name."""
    if data_type not in {code for code, _w in FIELD_TYPES}:
        raise GitHubProjectsError("Choose Text, Number, Date or Single select.")
    if not name.strip():
        raise GitHubProjectsError("A field needs a name.")
    input_data: dict[str, object] = {
        "projectId": project_id,
        "dataType": data_type,
        "name": name.strip(),
    }
    if data_type == "SINGLE_SELECT":
        choices = [o.strip() for o in options if o.strip()]
        if not choices:
            raise GitHubProjectsError("A single select field needs at least one choice.")
        input_data["singleSelectOptions"] = [
            {"name": choice, "color": "GRAY", "description": ""} for choice in choices
        ]
    result = _mutate(
        token,
        "createProjectV2Field",
        input_data,
        "projectV2Field { ... on ProjectV2FieldCommon { name } }",
        request,
    )
    return str((result.get("projectV2Field") or {}).get("name", name.strip()))


def delete_field(token: str, field_id: str, request: Request = request_graphql) -> None:
    _mutate(
        token,
        "deleteProjectV2Field",
        {"fieldId": field_id},
        "projectV2Field { ... on ProjectV2FieldCommon { name } }",
        request,
    )


def post_status_update(
    token: str,
    project_id: str,
    status: str,
    body: str,
    *,
    start_date: str = "",
    target_date: str = "",
    request: Request = request_graphql,
) -> None:
    """Post a status update ("On track", with a note and optional dates, YYYY-MM-DD)."""
    if status not in {code for code, _w in STATUS_CHOICES}:
        raise GitHubProjectsError("Choose On track, At risk, Off track, Complete or Inactive.")
    for typed, what in ((start_date, "start"), (target_date, "target")):
        _check_date(typed, what)
    input_data: dict[str, object] = {"projectId": project_id, "status": status, "body": body}
    if start_date:
        input_data["startDate"] = start_date
    if target_date:
        input_data["targetDate"] = target_date
    _mutate(token, "createProjectV2StatusUpdate", input_data, "statusUpdate { id }", request)


def _check_date(typed: str, what: str) -> None:
    """Refuse a date GitHub would refuse, before anything is sent."""
    if not typed:
        return
    try:
        valid = len(typed) == 10 and bool(date.fromisoformat(typed))
    except ValueError:
        valid = False
    if not valid:
        raise GitHubProjectsError(f"Type the {what} date as year-month-day, like 2026-12-01.")


def link_repository(
    token: str,
    project_id: str,
    repository: str,
    *,
    link: bool = True,
    request: Request = request_graphql,
) -> None:
    """Link the project to a repository (it then shows in the repository's Projects), or unlink."""
    repo_id = repository_id(token, repository, request)
    operation = "linkProjectV2ToRepository" if link else "unlinkProjectV2FromRepository"
    _mutate(
        token,
        operation,
        {"projectId": project_id, "repositoryId": repo_id},
        "repository { name }",
        request,
    )


def set_template(
    token: str, project_id: str, template: bool, request: Request = request_graphql
) -> None:
    """Mark or unmark as a template; GitHub allows templates only in an organization."""
    operation = "markProjectV2AsTemplate" if template else "unmarkProjectV2AsTemplate"
    _mutate(token, operation, {"projectId": project_id}, "projectV2 { id }", request)


def copy_project(
    token: str,
    project_id: str,
    owner_login: str,
    title: str,
    *,
    include_drafts: bool = False,
    request: Request = request_graphql,
) -> str:
    """Copy the project's fields and views (not its items) to *owner_login*; returns its address."""
    if not title.strip():
        raise GitHubProjectsError("The copy needs a title.")
    result = _mutate(
        token,
        "copyProjectV2",
        {
            "projectId": project_id,
            "ownerId": owner_id(token, owner_login, request),
            "title": title.strip(),
            "includeDraftIssues": include_drafts,
        },
        "projectV2 { url }",
        request,
    )
    return str((result.get("projectV2") or {}).get("url", ""))


def delete_project(token: str, project_id: str, request: Request = request_graphql) -> None:
    """Delete the project for good. Its issues and pull requests are not touched."""
    _mutate(token, "deleteProjectV2", {"projectId": project_id}, "projectV2 { id }", request)
