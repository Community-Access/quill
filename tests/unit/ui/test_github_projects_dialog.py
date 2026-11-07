"""Readable project rows and safe issue-reference parsing."""

from __future__ import annotations

from quill.core.github.project_models import GitHubIssueLink, GitHubProjectItem
from quill.ui.github_projects_dialog import _item_detail, _item_label
from quill.ui.github_projects_dialog_actions import _parse_issue_reference


def test_project_item_label_and_details_explain_dependencies_and_progress() -> None:
    blocker = GitHubIssueLink(
        "node-blocker", "o/r", 1, "Build API", "OPEN", "https://github.com/o/r/issues/1"
    )
    child = GitHubIssueLink(
        "node-child", "o/r", 3, "Write tests", "CLOSED", "https://github.com/o/r/issues/3"
    )
    item = GitHubProjectItem(
        "item-2",
        "issue-2",
        "issue",
        "o/r",
        2,
        "Build interface",
        "OPEN",
        "https://github.com/o/r/issues/2",
        False,
        (("Status", "In progress"),),
        blocked_by=(blocker,),
        sub_issues=(child,),
        sub_issue_total=2,
        sub_issue_completed=1,
        sub_issue_percent=50,
    )

    assert "Blocked" in _item_label(item)
    detail = _item_detail(item)
    assert "Status: In progress" in detail
    assert "o/r#1: Build API" in detail
    assert "1 of 2 complete (50%)" in detail


def test_issue_relationship_reference_accepts_issue_urls_and_owner_repo_numbers() -> None:
    assert _parse_issue_reference("owner/repo#12") == ("owner/repo", 12)
    assert _parse_issue_reference("https://github.com/owner/repo/issues/12") == (
        "owner/repo",
        12,
    )
    assert _parse_issue_reference("https://github.com/owner/repo/pull/12") is None
    assert _parse_issue_reference("owner/repo#0") is None
