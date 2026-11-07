"""Typed models and strict response mapping for GitHub Projects v2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from quill.core.error_codes import CodedError


class GitHubProjectsError(CodedError):
    """A Projects v2 read or confirmed update could not be completed."""

    code = "QUILL-GITHUB-PROJECTS-ERROR"


@dataclass(frozen=True, slots=True)
class GitHubProject:
    node_id: str
    title: str
    number: int
    url: str
    description: str = ""
    closed: bool = False


@dataclass(frozen=True, slots=True)
class GitHubProjectField:
    node_id: str
    name: str
    kind: str
    options: tuple[tuple[str, str], ...] = ()
    iterations: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class GitHubIssueLink:
    node_id: str
    repository: str
    number: int
    title: str
    state: str
    url: str


@dataclass(frozen=True, slots=True)
class GitHubProjectItem:
    node_id: str
    content_id: str
    kind: str
    repository: str
    number: int
    title: str
    state: str
    url: str
    archived: bool
    values: tuple[tuple[str, str], ...] = ()
    blocked_by: tuple[GitHubIssueLink, ...] = ()
    blocking: tuple[GitHubIssueLink, ...] = ()
    sub_issues: tuple[GitHubIssueLink, ...] = ()
    sub_issue_total: int = 0
    sub_issue_completed: int = 0
    sub_issue_percent: float = 0.0
    selected_option_ids: tuple[tuple[str, tuple[str, ...]], ...] = ()

    @property
    def is_blocked(self) -> bool:
        return any(issue.state.casefold() != "closed" for issue in self.blocked_by)


@dataclass(frozen=True, slots=True)
class GitHubProjectBoard:
    project: GitHubProject
    fields: tuple[GitHubProjectField, ...]
    items: tuple[GitHubProjectItem, ...]
    complete: bool = True
    warning: str = ""

    @property
    def next_unblocked_work(self) -> tuple[GitHubProjectItem, ...]:
        """Open issue/PR rows without an open blocker, in stable board order."""
        return tuple(
            item
            for item in self.items
            if item.kind in {"issue", "pull_request"}
            and item.state.casefold() == "open"
            and not item.is_blocked
            and not item.archived
        )


def text(value: object) -> str:
    return value if isinstance(value, str) else ""


def connection(value: object, description: str) -> tuple[list[Any], dict[str, Any]]:
    if not isinstance(value, dict):
        raise ValueError(f"GitHub returned invalid {description} data.")
    nodes, page_info = value.get("nodes"), value.get("pageInfo")
    if not isinstance(nodes, list) or not isinstance(page_info, dict):
        raise ValueError(f"GitHub returned incomplete {description} pagination data.")
    if not isinstance(page_info.get("hasNextPage"), bool):
        raise ValueError(f"GitHub returned an invalid {description} page state.")
    return nodes, page_info


def project(node: dict[str, Any]) -> GitHubProject:
    node_id, title = node.get("id"), node.get("title")
    if not isinstance(node_id, str) or not node_id or not isinstance(title, str):
        raise ValueError("GitHub returned incomplete project details.")
    number = node.get("number")
    return GitHubProject(
        node_id,
        title,
        number if isinstance(number, int) and not isinstance(number, bool) else 0,
        text(node.get("url")),
    )


def project_fields(value: object) -> tuple[tuple[GitHubProjectField, ...], bool]:
    nodes, page = connection(value, "Project fields")
    fields: list[GitHubProjectField] = []
    for row in nodes:
        if not isinstance(row, dict):
            continue
        node_id, name, typename = row.get("id"), row.get("name"), row.get("__typename")
        if not isinstance(node_id, str) or not isinstance(name, str):
            continue
        kind = {
            "ProjectV2SingleSelectField": "single_select",
            "ProjectV2MultiSelectField": "multi_select",
            "ProjectV2Field": "field",
            "ProjectV2IterationField": "iteration",
        }.get(text(typename), "field")
        option_key = "multiSelectOptions" if kind == "multi_select" else "options"
        option_rows = row.get(option_key)
        options = (
            tuple(
                (text(option.get("id")), text(option.get("name")))
                for option in option_rows
                if isinstance(option, dict) and option.get("id") and option.get("name")
            )
            if isinstance(option_rows, list)
            else ()
        )
        configuration = row.get("configuration")
        iteration_connection = (
            configuration.get("iterations") if isinstance(configuration, dict) else None
        )
        iteration_rows = (
            iteration_connection.get("nodes") if isinstance(iteration_connection, dict) else None
        )
        iterations = (
            tuple(
                (text(iteration.get("id")), text(iteration.get("title")))
                for iteration in iteration_rows
                if isinstance(iteration, dict) and iteration.get("id") and iteration.get("title")
            )
            if isinstance(iteration_rows, list)
            else ()
        )
        fields.append(GitHubProjectField(node_id, name, kind, options, iterations))
    return tuple(fields), bool(page.get("hasNextPage"))


def issue_links(value: object, description: str) -> tuple[tuple[GitHubIssueLink, ...], bool]:
    nodes, page = connection(value, description)
    result: list[GitHubIssueLink] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        repo = node.get("repository")
        node_id, number, title = node.get("id"), node.get("number"), node.get("title")
        if not isinstance(repo, dict) or not isinstance(node_id, str) or not isinstance(title, str):
            continue
        if isinstance(number, bool) or not isinstance(number, int):
            continue
        result.append(
            GitHubIssueLink(
                node_id,
                text(repo.get("nameWithOwner")),
                number,
                title,
                text(node.get("state")),
                text(node.get("url")),
            )
        )
    return tuple(result), bool(page.get("hasNextPage"))


def project_item(row: dict[str, Any]) -> tuple[GitHubProjectItem | None, list[str]]:
    warnings: list[str] = []
    content = row.get("content")
    if not isinstance(content, dict):
        return None, ["Project item without readable content was skipped."]
    typename = text(content.get("__typename"))
    kind = {"Issue": "issue", "PullRequest": "pull_request", "DraftIssue": "draft"}.get(
        typename, "unsupported"
    )
    if kind == "unsupported":
        return None, ["Unsupported project item type was skipped."]
    node_id = text(row.get("id"))
    content_id = text(content.get("id"))
    if not node_id or not content_id:
        return None, ["Project item without stable IDs was skipped."]
    repository = content.get("repository")
    repository_name = text(repository.get("nameWithOwner")) if isinstance(repository, dict) else ""
    number = content.get("number")
    fields_value = row.get("fieldValues")
    field_nodes = fields_value.get("nodes") if isinstance(fields_value, dict) else None
    if not isinstance(field_nodes, list):
        warnings.append("Project item field values were unavailable.")
        field_nodes = []
    elif isinstance(fields_value, dict):
        page_info = fields_value.get("pageInfo")
        if not isinstance(page_info, dict) or not isinstance(page_info.get("hasNextPage"), bool):
            warnings.append("Project item field-value completeness is unavailable.")
        elif page_info["hasNextPage"]:
            warnings.append("Some project item field values were not loaded.")
    values: list[tuple[str, str]] = []
    selected_option_ids: list[tuple[str, tuple[str, ...]]] = []
    for value in field_nodes:
        if not isinstance(value, dict):
            continue
        field = value.get("field")
        if not isinstance(field, dict) or not isinstance(field.get("name"), str):
            continue
        key = {
            "ProjectV2ItemFieldTextValue": "text",
            "ProjectV2ItemFieldNumberValue": "number",
            "ProjectV2ItemFieldDateValue": "date",
            "ProjectV2ItemFieldSingleSelectValue": "name",
            "ProjectV2ItemFieldMultiSelectValue": "value",
            "ProjectV2ItemFieldIterationValue": "title",
        }.get(text(value.get("__typename")), "")
        if key and value.get(key) is not None:
            values.append((field["name"], str(value[key])))
        if text(value.get("__typename")) == "ProjectV2ItemFieldMultiSelectValue":
            options = value.get("options")
            if isinstance(options, list):
                selected = tuple(
                    text(option.get("id"))
                    for option in options
                    if isinstance(option, dict) and option.get("id")
                )
                selected_option_ids.append((field["name"], selected))
    blocked_by: tuple[GitHubIssueLink, ...] = ()
    blocking: tuple[GitHubIssueLink, ...] = ()
    sub_issues: tuple[GitHubIssueLink, ...] = ()
    total = completed = 0
    percent = 0.0
    if kind == "issue":
        blocked_by, more_blockers = issue_links(content.get("blockedBy"), "blocking issues")
        blocking, more_blocking = issue_links(content.get("blocking"), "blocked issues")
        sub_issues, more_sub_issues = issue_links(content.get("subIssues"), "sub-issues")
        if more_blockers or more_blocking or more_sub_issues:
            warnings.append("Some issue relationships exceed the 20-item display limit.")
        summary = content.get("subIssuesSummary")
        if isinstance(summary, dict):
            total = _nonnegative(summary.get("total"))
            completed = _nonnegative(summary.get("completed"))
            raw_percent = summary.get("percentCompleted")
            if isinstance(raw_percent, (int, float)) and not isinstance(raw_percent, bool):
                percent = float(raw_percent)
    return (
        GitHubProjectItem(
            node_id,
            content_id,
            kind,
            repository_name,
            number if isinstance(number, int) and not isinstance(number, bool) else 0,
            text(content.get("title")) or "Untitled project item",
            text(content.get("state")),
            text(content.get("url")),
            bool(row.get("isArchived", False)),
            tuple(values),
            blocked_by,
            blocking,
            sub_issues,
            total,
            completed,
            percent,
            tuple(selected_option_ids),
        ),
        warnings,
    )


def _nonnegative(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


__all__ = [
    "GitHubIssueLink",
    "GitHubProject",
    "GitHubProjectBoard",
    "GitHubProjectField",
    "GitHubProjectItem",
    "GitHubProjectsError",
    "connection",
    "issue_links",
    "project",
    "project_fields",
    "project_item",
    "text",
]
