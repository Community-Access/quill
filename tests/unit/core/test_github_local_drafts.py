"""Account-scoped local issue drafts never retain credentials or publish."""

from __future__ import annotations

import json

from quill.core.github import local_drafts
from quill.core.github.local_drafts import (
    GitHubIssueDraftData,
    GitHubIssueDraftStore,
)


def test_issue_draft_round_trips_by_account_without_saving_token(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(local_drafts, "app_data_dir", lambda: tmp_path)
    token = "ghp_private_test_token"
    store = GitHubIssueDraftStore.load(token)

    assert store.save_issue(
        "owner/repo",
        title="Bug report",
        body="Steps to reproduce",
        labels=("bug",),
        assignees=("alice",),
    )

    saved_text = (tmp_path / "github_local_drafts.json").read_text(encoding="utf-8")
    assert token not in saved_text
    assert GitHubIssueDraftStore.load(token).get_issue("owner/repo") == GitHubIssueDraftData(
        title="Bug report",
        body="Steps to reproduce",
        labels=("bug",),
        assignees=("alice",),
        updated_at=GitHubIssueDraftStore.load(token).get_issue("owner/repo").updated_at,
    )
    assert GitHubIssueDraftStore.load("another-token").get_issue("owner/repo") is None


def test_issue_draft_fields_and_repository_are_bounded(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(local_drafts, "app_data_dir", lambda: tmp_path)
    store = GitHubIssueDraftStore.load(None)

    assert not store.save_issue(
        "owner/repo/issues/3",
        title="Title",
        body="Body",
        labels=(),
        assignees=(),
    )
    assert store.save_issue(
        "owner/repo",
        title="T" * 300,
        body="B" * 60_000,
        labels=tuple(f"label-{index}" for index in range(25)),
        assignees=(" alice ",),
    )

    draft = store.get_issue("OWNER/REPO")
    assert draft is not None
    assert len(draft.title) == 256
    assert len(draft.body) == 50_000
    assert len(draft.labels) == 20
    assert draft.assignees == ("alice",)


def test_issue_draft_deletion_clears_only_that_repository(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(local_drafts, "app_data_dir", lambda: tmp_path)
    store = GitHubIssueDraftStore.load(None)
    for repository in ("owner/one", "owner/two"):
        store.save_issue(
            repository,
            title=repository,
            body="draft",
            labels=(),
            assignees=(),
        )

    assert store.delete_issue("owner/one")
    assert store.get_issue("owner/one") is None
    assert store.get_issue("owner/two").title == "owner/two"


def test_malformed_local_draft_data_degrades_to_no_draft(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(local_drafts, "app_data_dir", lambda: tmp_path)
    path = tmp_path / "github_local_drafts.json"
    path.write_text(
        json.dumps({"accounts": {"anonymous": {"issue_drafts": {"owner/repo": []}}}}),
        encoding="utf-8",
    )

    assert GitHubIssueDraftStore.load(None).get_issue("owner/repo") is None


def test_review_drafts_are_isolated_by_pull_request_and_head(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(local_drafts, "app_data_dir", lambda: tmp_path)
    token = "ghp_review_draft_secret"
    store = GitHubIssueDraftStore.load(token)
    assert store.save_review(
        "owner/repo",
        12,
        event="request changes",
        body="Please verify this commit.",
        head_sha="abc123",
    )
    assert store.save_review(
        "owner/repo",
        13,
        event="comment",
        body="Another pull request.",
        head_sha="def456",
    )

    saved_text = (tmp_path / "github_local_drafts.json").read_text(encoding="utf-8")
    assert token not in saved_text
    draft = GitHubIssueDraftStore.load(token).get_review("owner/repo", 12)
    assert draft is not None
    assert draft.event == "request changes"
    assert draft.body == "Please verify this commit."
    assert draft.head_sha == "abc123"
    assert GitHubIssueDraftStore.load("other-token").get_review("owner/repo", 12) is None

    assert store.delete_review("owner/repo", 12)
    assert store.get_review("owner/repo", 12) is None
    assert store.get_review("owner/repo", 13).body == "Another pull request."
