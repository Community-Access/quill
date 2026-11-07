"""Accessible GitHub Projects v2 boards and issue relationships over GraphQL."""

from __future__ import annotations

from typing import Any

from quill.core.github.fetch_results import GitHubFetchResult
from quill.core.github.project_models import (
    GitHubIssueLink,
    GitHubProject,
    GitHubProjectBoard,
    GitHubProjectField,
    GitHubProjectItem,
    GitHubProjectsError,
)
from quill.core.github.project_models import (
    connection as _connection,
)
from quill.core.github.project_models import (
    project as _project,
)
from quill.core.github.project_models import (
    project_fields as _project_fields,
)
from quill.core.github.project_models import (
    project_item as _project_item,
)
from quill.core.github.project_models import (
    text as _string,
)
from quill.core.github.project_queries import _BOARD_QUERY, _ISSUE_QUERY, _PROJECTS_QUERY
from quill.core.github.project_transport import request_graphql


def _request(token: str, query: str, variables: dict[str, object]) -> dict[str, Any]:
    return request_graphql(token, query, variables)


def list_projects(
    token: str, repository: str, *, limit: int = 50
) -> GitHubFetchResult[GitHubProject]:
    """List repository Projects v2 boards, preserving rows if a later page fails."""
    parts = repository.strip().split("/", 1)
    if len(parts) != 2 or not all(parts):
        raise GitHubProjectsError("Enter a repository as owner/repo to list its Projects.")
    owner, repo = parts
    limit = max(1, min(limit, 200))
    rows: list[GitHubProject] = []
    warnings: list[str] = []
    after: str | None = None
    pages = 0
    while len(rows) < limit:
        pages += 1
        if pages > 4:
            warnings.append("Projects list exceeded the four-page safety limit.")
            break
        try:
            data = _request(token, _PROJECTS_QUERY, {"owner": owner, "repo": repo, "after": after})
            container = data.get("repository")
            if not isinstance(container, dict):
                raise GitHubProjectsError(
                    "This repository is unavailable or has no visible Projects."
                )
            nodes, page = _connection(container.get("projectsV2"), "Projects")
        except GitHubProjectsError as exc:
            if rows:
                warnings.append(str(exc))
                break
            raise
        except ValueError as exc:
            error = GitHubProjectsError(str(exc))
            if rows:
                warnings.append(str(error))
                break
            raise error from exc
        for node in nodes:
            if not isinstance(node, dict):
                warnings.append("GitHub returned an invalid project row; it was skipped.")
                continue
            node_id, title, number = node.get("id"), node.get("title"), node.get("number")
            if not isinstance(node_id, str) or not node_id or not isinstance(title, str):
                warnings.append("GitHub returned a project without an ID or title; it was skipped.")
                continue
            rows.append(
                GitHubProject(
                    node_id,
                    title,
                    int(number) if isinstance(number, int) and not isinstance(number, bool) else 0,
                    _string(node.get("url")),
                    _string(node.get("shortDescription")),
                    bool(node.get("closed", False)),
                )
            )
        if len(rows) >= limit:
            if len(rows) > limit or page["hasNextPage"]:
                warnings.append(f"Projects: showing the first {limit} boards; more may exist.")
            break
        if not page["hasNextPage"]:
            break
        cursor = page.get("endCursor")
        if not isinstance(cursor, str) or not cursor or cursor == after:
            warnings.append("GitHub returned an invalid Projects page cursor.")
            break
        after = cursor
    return GitHubFetchResult(
        tuple(rows[:limit]), complete=not warnings, warning="; ".join(warnings)
    )


def fetch_project(token: str, project_id: str, *, limit: int = 100) -> GitHubProjectBoard:
    """Load bounded project fields and items, including blocker/sub-issue links."""
    if not project_id.strip():
        raise GitHubProjectsError("Choose a Project before loading its board.")
    limit = max(1, min(limit, 1000))
    fields: tuple[GitHubProjectField, ...] = ()
    project: GitHubProject | None = None
    items: list[GitHubProjectItem] = []
    warnings: list[str] = []
    after: str | None = None
    pages = 0
    while len(items) < limit:
        pages += 1
        if pages > 10:
            warnings.append("Project board exceeded the ten-page safety limit.")
            break
        try:
            data = _request(token, _BOARD_QUERY, {"projectId": project_id, "after": after})
            node = data.get("node")
            if not isinstance(node, dict):
                raise GitHubProjectsError("This Project is unavailable to the signed-in account.")
            if project is None:
                project = _project(node)
                fields, more_fields = _project_fields(node.get("fields"))
                if more_fields:
                    warnings.append("Some project fields were not loaded.")
            page_nodes, page = _connection(node.get("items"), "Project items")
        except ValueError as exc:
            error = GitHubProjectsError(str(exc))
            if items:
                warnings.append(str(error))
                break
            raise error from exc
        except GitHubProjectsError as exc:
            if items:
                warnings.append(str(exc))
                break
            raise
        for row in page_nodes:
            if not isinstance(row, dict):
                warnings.append("GitHub returned an invalid project item; it was skipped.")
                continue
            try:
                item, row_warnings = _project_item(row)
            except ValueError as exc:
                warnings.append(str(exc))
                continue
            warnings.extend(row_warnings)
            if item is not None:
                items.append(item)
        if len(items) >= limit:
            if len(items) > limit or page["hasNextPage"]:
                warnings.append(f"Project board: showing the first {limit} items; more may exist.")
            break
        if not page["hasNextPage"]:
            break
        cursor = page.get("endCursor")
        if not isinstance(cursor, str) or not cursor or cursor == after:
            warnings.append("GitHub returned an invalid project-item page cursor.")
            break
        after = cursor
    if project is None:
        raise GitHubProjectsError("GitHub returned no project details.")
    return GitHubProjectBoard(
        project, fields, tuple(items[:limit]), not warnings, "; ".join(dict.fromkeys(warnings))
    )


def update_project_field(
    token: str,
    project_id: str,
    item_id: str,
    field: GitHubProjectField,
    value: str | tuple[str, ...],
) -> None:
    """Update one supported project field after the UI has confirmed the target."""
    if not project_id or not item_id or not field.node_id:
        raise GitHubProjectsError("This project item or field is missing its GitHub ID.")
    try:
        if field.kind == "single_select":
            if not isinstance(value, str):
                raise GitHubProjectsError("Choose one of the available options for this field.")
            if value not in {option_id for option_id, _label in field.options}:
                raise GitHubProjectsError("Choose one of the available options for this field.")
            field_value: dict[str, object] = {"singleSelectOptionId": value}
        elif field.kind == "multi_select":
            if not isinstance(value, tuple) or not set(value) <= {
                option_id for option_id, _label in field.options
            }:
                raise GitHubProjectsError("Choose from the available options for this field.")
            field_value = {"multiSelectOptionIds": list(value)}
        elif field.kind == "text":
            if not isinstance(value, str):
                raise GitHubProjectsError("Enter text for this project field.")
            field_value = {"text": value}
        elif field.kind == "number":
            if not isinstance(value, str):
                raise GitHubProjectsError("Enter a number for this project field.")
            field_value = {"number": float(value)}
        elif field.kind == "date":
            if not isinstance(value, str):
                raise GitHubProjectsError("Enter an ISO date for this project field.")
            field_value = {"date": value}
        elif field.kind == "iteration":
            if not isinstance(value, str):
                raise GitHubProjectsError("Choose an available iteration for this field.")
            if value not in {iteration_id for iteration_id, _label in field.iterations}:
                raise GitHubProjectsError("Choose an available iteration for this field.")
            field_value = {"iterationId": value}
        else:
            raise GitHubProjectsError(f"The {field.name!r} field type is read-only in QUILL.")
    except ValueError as exc:
        raise GitHubProjectsError("Enter a valid number for this project field.") from exc
    data = _request(
        token,
        "mutation($projectId:ID!, $itemId:ID!, $fieldId:ID!, $value:ProjectV2FieldValue!) { "
        "updateProjectV2ItemFieldValue(input:{projectId:$projectId,itemId:$itemId,"
        "fieldId:$fieldId,value:$value}) "
        "{ projectV2Item { id } } }",
        {
            "projectId": project_id,
            "itemId": item_id,
            "fieldId": field.node_id,
            "value": field_value,
        },
    )
    result = data.get("updateProjectV2ItemFieldValue")
    item = result.get("projectV2Item") if isinstance(result, dict) else None
    if not isinstance(item, dict) or item.get("id") != item_id:
        raise GitHubProjectsError("GitHub did not confirm the project field update.")


def resolve_issue_reference(token: str, repository: str, number: int) -> GitHubIssueLink:
    """Resolve one issue reference to its GraphQL node ID for relationship edits."""
    parts = repository.strip().split("/", 1)
    if len(parts) != 2 or not all(parts) or number <= 0:
        raise GitHubProjectsError("Enter a repository as owner/repo and a positive issue number.")
    data = _request(
        token,
        _ISSUE_QUERY,
        {"owner": parts[0], "repo": parts[1], "number": number},
    )
    repository_data = data.get("repository")
    issue = repository_data.get("issue") if isinstance(repository_data, dict) else None
    if not isinstance(issue, dict) or not isinstance(issue.get("id"), str):
        raise GitHubProjectsError(f"Could not read issue {repository}#{number}.")
    repository_value = issue.get("repository")
    if not isinstance(repository_value, dict):
        raise GitHubProjectsError(f"GitHub returned incomplete details for {repository}#{number}.")
    return GitHubIssueLink(
        _string(issue.get("id")),
        _string(repository_value.get("nameWithOwner")),
        number,
        _string(issue.get("title")),
        _string(issue.get("state")),
        _string(issue.get("url")),
    )


def update_issue_relationship(
    token: str,
    *,
    relation: str,
    add: bool,
    issue_id: str,
    related_issue_id: str,
) -> None:
    """Add or remove a blocker/sub-issue relationship after explicit confirmation."""
    if not issue_id or not related_issue_id or issue_id == related_issue_id:
        raise GitHubProjectsError("Choose two different GitHub issues for this relationship.")
    if relation == "blocked_by":
        operation = "addBlockedBy" if add else "removeBlockedBy"
        input_type = "AddBlockedByInput!" if add else "RemoveBlockedByInput!"
        input_data = {"issueId": issue_id, "blockingIssueId": related_issue_id}
        expected = "blockingIssue"
    elif relation == "sub_issue":
        operation = "addSubIssue" if add else "removeSubIssue"
        input_type = "AddSubIssueInput!" if add else "RemoveSubIssueInput!"
        input_data = {"issueId": issue_id, "subIssueId": related_issue_id}
        expected = "subIssue" if add else "issue"
    else:
        raise GitHubProjectsError("Choose either a blocker or a sub-issue relationship.")
    mutation = (
        f"mutation($input:{input_type}) {{ {operation}(input:$input) "
        "{ issue { id } "
        + ("blockingIssue { id } " if relation == "blocked_by" else "")
        + ("subIssue { id } " if relation == "sub_issue" and add else "")
        + "} }"
    )
    data = _request(token, mutation, {"input": input_data})
    result = data.get(operation)
    related = result.get(expected) if isinstance(result, dict) else None
    if not isinstance(result, dict) or not isinstance(result.get("issue"), dict):
        raise GitHubProjectsError("GitHub did not confirm the issue relationship change.")
    if add and (not isinstance(related, dict) or related.get("id") != related_issue_id):
        raise GitHubProjectsError("GitHub did not confirm the related issue.")


__all__ = [
    "GitHubIssueLink",
    "GitHubProject",
    "GitHubProjectBoard",
    "GitHubProjectField",
    "GitHubProjectItem",
    "GitHubProjectsError",
    "fetch_project",
    "list_projects",
    "resolve_issue_reference",
    "update_issue_relationship",
    "update_project_field",
]
