"""A Project's own care over GraphQL: drafts, fields, status, links, templates, copy, delete."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.github import project_admin as pa
from quill.core.github.project_models import GitHubProjectsError


class _GitHub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def __call__(self, _token: str, query: str, variables: dict[str, object]) -> dict[str, Any]:
        self.calls.append((query, dict(variables)))
        if "repository(owner" in query:
            return {"repository": {"id": "R_1"}}
        if "repositoryOwner" in query:
            return {"repositoryOwner": {"id": "O_1"}}
        operation = query.split("{", 1)[1].split("(", 1)[0].strip()
        return {
            operation: {
                "projectItem": {"id": "I_1"},
                "projectV2": {"url": "https://x/p/2"},
                "projectV2Field": {"name": "Size"},
            }
        }


def _inputs(github: _GitHub) -> list[dict[str, Any]]:
    return [v["input"] for _q, v in github.calls if "input" in v]


def test_draft_field_and_status_send_what_github_expects() -> None:
    github = _GitHub()
    assert pa.add_draft_issue("t", "P_1", " Fix it ", "Body", request=github) == "I_1"
    assert (
        pa.create_field("t", "P_1", "Size", "SINGLE_SELECT", ["S", " ", "M"], request=github)
        == "Size"
    )
    pa.post_status_update(
        "t", "P_1", "AT_RISK", "Slipping", target_date="2026-12-01", request=github
    )
    drafted, field, status = _inputs(github)
    assert drafted == {"projectId": "P_1", "title": "Fix it", "body": "Body"}
    assert [o["name"] for o in field["singleSelectOptions"]] == ["S", "M"]
    assert status == {
        "projectId": "P_1",
        "status": "AT_RISK",
        "body": "Slipping",
        "targetDate": "2026-12-01",
    }
    assert "AddProjectV2DraftIssueInput!" in github.calls[0][0]


def test_link_copy_template_and_delete_look_up_ids_first() -> None:
    github = _GitHub()
    pa.link_repository("t", "P_1", "o/r", request=github)
    pa.link_repository("t", "P_1", "o/r", link=False, request=github)
    pa.set_template("t", "P_1", True, request=github)
    assert (
        pa.copy_project("t", "P_1", "acme", "Copy", include_drafts=True, request=github)
        == "https://x/p/2"
    )
    pa.delete_project("t", "P_1", request=github)
    operations = [
        q.split("{", 1)[1].split("(", 1)[0].strip() for q, v in github.calls if "input" in v
    ]
    assert operations == [
        "linkProjectV2ToRepository",
        "unlinkProjectV2FromRepository",
        "markProjectV2AsTemplate",
        "copyProjectV2",
        "deleteProjectV2",
    ]
    assert _inputs(github)[0] == {"projectId": "P_1", "repositoryId": "R_1"}
    assert _inputs(github)[3]["ownerId"] == "O_1"


@pytest.mark.parametrize(
    "call",
    [
        lambda g: pa.add_draft_issue("t", "P", "  ", request=g),
        lambda g: pa.create_field("t", "P", "Size", "SINGLE_SELECT", [], request=g),
        lambda g: pa.create_field("t", "P", "X", "WRONG", request=g),
        lambda g: pa.post_status_update("t", "P", "FINE", "", request=g),
        lambda g: pa.copy_project("t", "P", "acme", " ", request=g),
        lambda g: pa.delete_project("", "P", request=g),
    ],
)
def test_bad_input_is_refused_before_anything_is_sent(call) -> None:
    github = _GitHub()
    with pytest.raises(GitHubProjectsError):
        call(github)
    assert not [v for _q, v in github.calls if "input" in v]


def test_a_reply_without_the_operation_is_not_reported_as_done() -> None:
    with pytest.raises(GitHubProjectsError, match="did not confirm"):
        pa.delete_project("t", "P", request=lambda *_a: {})
