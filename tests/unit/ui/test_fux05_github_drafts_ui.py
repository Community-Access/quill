"""FUX-05 in GitHub Workbench: a recovered draft is said, and a created issue's draft goes.

The recovered-draft notice was a static line above the title field, so a
screen-reader user only learned a draft had come back by tabbing up to it; and
New Issue from the Workbench never cleared the draft after the issue was
created, so the next New Issue there offered it back as "not submitted".
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
import wx

from quill.core import settings_recovery
from quill.core.github import local_drafts
from quill.core.github.local_drafts import GitHubIssueDraftStore
from quill.ui.github_issue_draft_dialog import GitHubIssueDraftDialog
from quill.ui.github_review_draft_dialog import GitHubReviewDraftDialog
from quill.ui.github_workbench_items import GitHubWorkbenchItemsMixin


@pytest.fixture
def store(tmp_path, monkeypatch) -> GitHubIssueDraftStore:
    settings_recovery._forget()
    monkeypatch.setattr(local_drafts, "app_data_dir", lambda: tmp_path)
    return GitHubIssueDraftStore.load("account-token")


def _show_and_cancel(monkeypatch, module: str) -> None:
    monkeypatch.setattr(f"{module}.show_modal_dialog", lambda *_a, **_k: wx.ID_CANCEL)


def test_recovered_issue_draft_is_said_once_when_the_window_opens(
    wx_session_app, store, monkeypatch
) -> None:
    store.save_issue("owner/repo", title="Crash on save", body="Two words", labels=(), assignees=())
    said: list[str] = []
    monkeypatch.setattr(wx, "CallLater", lambda _ms, fn, *a: fn(*a))
    _show_and_cancel(monkeypatch, "quill.ui.github_issue_draft_dialog")
    frame = wx.Frame(None)
    try:
        GitHubIssueDraftDialog(
            frame, draft_store=store, repository="owner/repo", announce_cb=said.append
        ).show()
    finally:
        frame.Destroy()
    assert len(said) == 1
    assert said[0].startswith('Recovered your unsent issue for owner/repo, "Crash on save"')


def test_new_issue_window_without_a_draft_says_nothing(wx_session_app, store, monkeypatch) -> None:
    said: list[str] = []
    monkeypatch.setattr(wx, "CallLater", lambda _ms, fn, *a: fn(*a))
    _show_and_cancel(monkeypatch, "quill.ui.github_issue_draft_dialog")
    frame = wx.Frame(None)
    try:
        GitHubIssueDraftDialog(
            frame, draft_store=store, repository="owner/repo", announce_cb=said.append
        ).show()
    finally:
        frame.Destroy()
    assert said == []


def test_recovered_review_draft_is_said_once(wx_session_app, store, monkeypatch) -> None:
    store.save_review("owner/repo", 7, event="comment", body="Looks right", head_sha="h1")
    said: list[str] = []
    monkeypatch.setattr(wx, "CallLater", lambda _ms, fn, *a: fn(*a))
    _show_and_cancel(monkeypatch, "quill.ui.github_review_draft_dialog")
    frame = wx.Frame(None)
    try:
        GitHubReviewDraftDialog(
            frame,
            draft_store=store,
            repository="owner/repo",
            number=7,
            current_head_sha="h1",
            announce_cb=said.append,
        ).show()
    finally:
        frame.Destroy()
    assert len(said) == 1
    assert said[0].startswith("Recovered your unsent review of pull request #7: a comment")


def _workbench(said: list[str]) -> Any:
    def background(_label: str, work: Any, done: Any) -> None:
        done(work())

    return SimpleNamespace(
        _confirm=lambda *_a: True,
        _background=background,
        _say=said.append,
        frame=SimpleNamespace(reload=lambda: None),
        items=SimpleNamespace(create_issue=lambda *_a, **_k: SimpleNamespace(number=43)),
    )


def test_workbench_new_issue_clears_its_draft_once_created(store) -> None:
    store.save_issue("owner/repo", title="Crash", body="", labels=(), assignees=())
    said: list[str] = []
    GitHubWorkbenchItemsMixin._preview_and_create(
        _workbench(said), "owner/repo", "Crash", "", (), (), "preview", store
    )
    assert said == ["Created issue #43."]
    assert GitHubIssueDraftStore.load("account-token").get_issue("owner/repo") is None


def test_workbench_says_when_a_created_issue_draft_could_not_be_cleared(store) -> None:
    store.save_issue("owner/repo", title="Crash", body="", labels=(), assignees=())
    store.delete_issue = lambda _repository: False  # type: ignore[method-assign]
    said: list[str] = []
    GitHubWorkbenchItemsMixin._preview_and_create(
        _workbench(said), "owner/repo", "Crash", "", (), (), "preview", store
    )
    assert said == [
        "Created issue #43. The local draft could not be cleared; review it before creating again."
    ]
