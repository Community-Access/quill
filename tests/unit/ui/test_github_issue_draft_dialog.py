"""Issue drafts restore locally without creating remote issues."""

from __future__ import annotations

import pytest
import wx

from quill.core.github import local_drafts
from quill.core.github.issue_templates import GitHubIssueTemplate
from quill.core.github.local_drafts import GitHubIssueDraftStore
from quill.ui.github_issue_draft_dialog import GitHubIssueDraftDialog
from tests.wx_session import shared_wx_app


@pytest.fixture(scope="module")
def wx_app():
    app = shared_wx_app()
    yield app
    app.Destroy()


def test_issue_dialog_recovers_edits_and_discards_local_draft(
    wx_app, tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(local_drafts, "app_data_dir", lambda: tmp_path)
    store = GitHubIssueDraftStore.load("account-token")
    store.save_issue(
        "owner/repo",
        title="Saved title",
        body="Saved body",
        labels=("bug",),
        assignees=("alice",),
    )
    frame = wx.Frame(None)
    template = GitHubIssueTemplate(
        name="Bug report",
        filename="bug.md",
        title="[Bug] ",
        body="Template body",
        labels=("question",),
    )
    dialog = GitHubIssueDraftDialog(
        frame,
        template,
        draft_store=store,
        repository="owner/repo",
    )
    try:
        assert dialog._title.GetValue() == "Saved title"
        assert dialog._body.GetValue() == "Saved body"
        assert dialog._labels.GetValue() == "bug"
        assert dialog._assignees.GetValue() == "alice"
        assert "Recovered a local draft" in dialog._draft_notice.GetLabel()

        dialog._body.SetValue("Edited saved body")
        dialog._save_local_draft()
        assert store.get_issue("owner/repo").body == "Edited saved body"

        dialog._discard_local_draft(None)
        assert store.get_issue("owner/repo") is None
        assert dialog._title.GetValue() == "[Bug] "
        assert dialog._body.GetValue() == "Template body"
        assert not dialog._discard_btn.IsEnabled()
        assert "Nothing has been submitted" in dialog._draft_notice.GetLabel()
    finally:
        dialog.dialog.Destroy()
        frame.Destroy()


def test_issue_dialog_labels_publish_as_explicit_create_only(wx_app) -> None:
    frame = wx.Frame(None)
    dialog = GitHubIssueDraftDialog(frame)
    try:
        dialog._on_create(None)
        assert dialog._result is None
        assert "Enter an issue title" in dialog._status.GetLabel()
        assert "not submitted" in dialog._draft_notice.GetLabel().casefold()
    finally:
        dialog.dialog.Destroy()
        frame.Destroy()
