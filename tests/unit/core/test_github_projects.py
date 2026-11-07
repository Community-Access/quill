"""Projects v2 parsing, bounded reads, and confirmed update contracts."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import projects
from quill.core.github.projects import (
    GitHubProjectsError,
    fetch_project,
    list_projects,
    update_issue_relationship,
    update_project_field,
)


def _connection(nodes: list[dict[str, Any]], *, next_page: bool = False, cursor: str = ""):
    return {
        "nodes": nodes,
        "pageInfo": {"hasNextPage": next_page, "endCursor": cursor},
    }


def _issue(
    number: int,
    title: str,
    *,
    blockers: list[dict[str, Any]] | None = None,
    sub_issues: list[dict[str, Any]] | None = None,
    state: str = "OPEN",
) -> dict[str, Any]:
    return {
        "id": f"issue-node-{number}",
        "number": number,
        "title": title,
        "state": state,
        "url": f"https://github.com/o/r/issues/{number}",
        "repository": {"nameWithOwner": "o/r"},
        "blockedBy": _connection(blockers or []),
        "blocking": _connection([]),
        "subIssues": _connection(sub_issues or []),
        "subIssuesSummary": {"total": len(sub_issues or []), "completed": 0, "percentCompleted": 0},
    }


def _board_page(*, issues: list[dict[str, Any]], next_page: bool = False) -> dict[str, Any]:
    project = {
        "id": "project-1",
        "title": "Release Plan",
        "number": 3,
        "url": "https://github.com/orgs/o/projects/3",
        "fields": _connection([
            {
                "__typename": "ProjectV2SingleSelectField",
                "id": "field-status",
                "name": "Status",
                "options": [{"id": "opt-progress", "name": "In progress"}],
            }
        ]),
        "items": _connection(
            [
                {
                    "id": f"item-{issue['number']}",
                    "type": "ISSUE",
                    "isArchived": False,
                    "content": {"__typename": "Issue", **issue},
                    "fieldValues": {
                        "pageInfo": {"hasNextPage": False},
                        "nodes": [
                            {
                                "__typename": "ProjectV2ItemFieldSingleSelectValue",
                                "name": "In progress",
                                "optionId": "opt-progress",
                                "field": {"id": "field-status", "name": "Status"},
                            }
                        ],
                    },
                }
                for issue in issues
            ],
            next_page=next_page,
            cursor="cursor-1" if next_page else "",
        ),
    }
    return {"node": project}


def test_fetch_project_maps_fields_dependencies_and_next_unblocked_work(monkeypatch) -> None:
    open_blocker = {
        "id": "issue-node-2",
        "number": 2,
        "title": "Build API",
        "state": "OPEN",
        "url": "https://github.com/o/r/issues/2",
        "repository": {"nameWithOwner": "o/r"},
    }
    closed_blocker = {**open_blocker, "id": "issue-node-4", "number": 4, "state": "CLOSED"}
    child = {**open_blocker, "id": "issue-node-3", "number": 3, "title": "Add tests"}
    payload = _board_page(
        issues=[
            _issue(1, "Docs", sub_issues=[child]),
            _issue(5, "UI", blockers=[open_blocker]),
            _issue(6, "Cleanup", blockers=[closed_blocker]),
        ]
    )
    monkeypatch.setattr(projects, "_request", lambda *_args: payload)

    board = fetch_project("secret", "project-1")

    assert board.complete
    assert board.fields[0].kind == "single_select"
    assert board.fields[0].options == (("opt-progress", "In progress"),)
    assert board.items[0].values == (("Status", "In progress"),)
    assert board.items[1].is_blocked
    assert [item.number for item in board.next_unblocked_work] == [1, 6]
    assert board.items[0].sub_issue_total == 1
    assert board.items[0].sub_issues[0].number == 3


def test_fetch_project_preserves_loaded_items_and_marks_later_page_failure(monkeypatch) -> None:
    calls = 0

    def request(_token, _query, variables):
        nonlocal calls
        calls += 1
        if calls == 1:
            payload = _board_page(issues=[_issue(1, "One")], next_page=True)
            return payload
        raise GitHubProjectsError("rate limit")

    monkeypatch.setattr(projects, "_request", request)

    board = fetch_project("secret", "project-1")

    assert len(board.items) == 1
    assert not board.complete
    assert "rate limit" in board.warning


def test_projects_list_distinguishes_exact_limit_from_more_pages(monkeypatch) -> None:
    def response(nodes, next_page=False):
        return {
            "repository": {"projectsV2": _connection(nodes, next_page=next_page, cursor="next")}
        }

    monkeypatch.setattr(
        projects,
        "_request",
        lambda *_args: response([
            {"id": "p1", "title": "One", "number": 1, "url": "https://github.com/o/p1"}
        ]),
    )
    exact = list_projects("secret", "o/r", limit=1)
    assert exact.complete

    monkeypatch.setattr(
        projects,
        "_request",
        lambda *_args: response([
            {"id": "p1", "title": "One", "number": 1, "url": "u1"},
            {"id": "p2", "title": "Two", "number": 2, "url": "u2"},
        ]),
    )
    truncated = list_projects("secret", "o/r", limit=1)
    assert len(truncated.items) == 1
    assert not truncated.complete
    assert "showing the first 1" in truncated.warning


def test_project_field_update_validates_option_and_confirms_server_result(monkeypatch) -> None:
    from quill.core.github.projects import GitHubProjectField

    calls = []

    def request(_token, query, variables):
        calls.append((query, variables))
        return {"updateProjectV2ItemFieldValue": {"projectV2Item": {"id": "item-1"}}}

    monkeypatch.setattr(projects, "_request", request)
    field = GitHubProjectField(
        "field-status", "Status", "single_select", (("opt-progress", "In progress"),)
    )
    update_project_field("secret", "project-1", "item-1", field, "opt-progress")
    assert calls[0][1]["value"] == {"singleSelectOptionId": "opt-progress"}

    with pytest.raises(GitHubProjectsError, match="available options"):
        update_project_field("secret", "project-1", "item-1", field, "unknown-option")


def test_multi_select_project_field_uses_only_available_option_ids(monkeypatch) -> None:
    from quill.core.github.projects import GitHubProjectField

    variables_seen = []

    def request(_token, _query, variables):
        variables_seen.append(variables)
        return {"updateProjectV2ItemFieldValue": {"projectV2Item": {"id": "item-1"}}}

    monkeypatch.setattr(projects, "_request", request)
    field = GitHubProjectField(
        "field-labels",
        "Labels",
        "multi_select",
        (("opt-a", "A"), ("opt-b", "B")),
    )
    update_project_field("secret", "project-1", "item-1", field, ("opt-a", "opt-b"))
    assert variables_seen[0]["value"] == {"multiSelectOptionIds": ["opt-a", "opt-b"]}
    with pytest.raises(GitHubProjectsError, match="available options"):
        update_project_field("secret", "project-1", "item-1", field, ("unknown",))


def test_issue_relationship_mutation_uses_issue_ids_and_confirms_result(monkeypatch) -> None:
    calls = []

    def request(_token, query, variables):
        calls.append((query, variables))
        return {"addBlockedBy": {"issue": {"id": "blocked"}, "blockingIssue": {"id": "blocker"}}}

    monkeypatch.setattr(projects, "_request", request)
    update_issue_relationship(
        "secret",
        relation="blocked_by",
        add=True,
        issue_id="blocked",
        related_issue_id="blocker",
    )

    assert "addBlockedBy" in calls[0][0]
    assert calls[0][1] == {"input": {"issueId": "blocked", "blockingIssueId": "blocker"}}
