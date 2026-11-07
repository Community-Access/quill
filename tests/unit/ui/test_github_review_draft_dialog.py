"""Review drafts restore by pull request and require stale-head confirmation."""

from __future__ import annotations

import pytest
import wx

from quill.core.github import local_drafts
from quill.core.github.local_drafts import GitHubIssueDraftStore
from quill.ui.github_review_draft_dialog import GitHubReviewDraftDialog
from tests.wx_session import shared_wx_app


@pytest.fixture(scope="module")
def wx_app():
    app = shared_wx_app()
    yield app
    app.Destroy()


def test_review_draft_recovers_and_requires_confirmation_after_head_changes(
    wx_app, tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(local_drafts, "app_data_dir", lambda: tmp_path)
    store = GitHubIssueDraftStore.load("review-account")
    store.save_review(
        "owner/repo",
        7,
        event="request changes",
        body="Please verify this change.",
        head_sha="oldhead",
    )
    frame = wx.Frame(None)
    dialog = GitHubReviewDraftDialog(
        frame,
        draft_store=store,
        repository="owner/repo",
        number=7,
        current_head_sha="newhead",
    )
    try:
        assert dialog._body.GetValue() == "Please verify this change."
        assert dialog._event.GetSelection() == 2
        assert dialog._stale
        assert dialog._stale_confirm.IsShown()
        assert "current HEAD is newhead" in dialog._notice.GetLabel()

        dialog._body.SetValue("Rechecked against the new diff.")
        dialog._save_local()
        assert store.get_review("owner/repo", 7).head_sha == "oldhead"
        dialog._submit(None)
        assert "Confirm that this draft" in dialog._status.GetLabel()
        assert dialog._result is None

        monkeypatch.setattr(wx.Dialog, "EndModal", lambda *_args: None)
        dialog._stale_confirm.SetValue(True)
        dialog._submit(None)
        assert dialog._result is not None
        assert dialog._result.event == "request changes"
        assert dialog._result.saved_head_sha == "newhead"
        assert store.get_review("owner/repo", 7).head_sha == "newhead"
    finally:
        dialog.dialog.Destroy()
        frame.Destroy()
