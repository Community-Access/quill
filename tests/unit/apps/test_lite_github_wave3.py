"""QUILL Lite reaches every Wave 3 GitHub feature through the shared surfaces.

Lite opens the same ``GitHubItemsDialog`` and Explore QUILL does, so a Wave 3
feature is in Lite exactly when it lives on a shared surface. Lite also hands
the viewer an open-file callback, so Repository Files' Open in Editor works in
both editors rather than only in QUILL.
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest

from quill.apps import lite_github_open
from quill.apps.lite_window_tools import DocumentToolsMixin
from quill.core.github.items_provider import GitHubItemsProvider
from quill.ui.github_explore_dialog import GitHubExploreDialog
from quill.ui.github_items_dialog import GitHubItemsDialog
from tests.wx_session import patch_call_after


def test_wave3_actions_live_on_the_shared_dialogs() -> None:
    for name in (
        "_open_repo_files",
        "_open_milestones",
        "_batch_set_milestone",
        "_batch_add_assignees",
    ):
        assert callable(getattr(GitHubItemsDialog, name))
    for name in (
        "_dismiss_alert",
        "_reopen_alert",
        "_open_discussion_thread",
        "_new_discussion",
    ):
        assert callable(getattr(GitHubExploreDialog, name))


def test_wave3_provider_operations_are_on_the_shared_provider() -> None:
    for name in (
        "fetch_repo_folder",
        "fetch_repo_file_text",
        "fetch_readme",
        "fetch_file_history",
        "fetch_blame",
        "fetch_milestones",
        "create_milestone",
        "update_milestone",
        "assign_milestone",
        "add_assignees",
        "fetch_discussion_thread",
        "reply_to_discussion",
        "set_discussion_answer",
        "create_discussion",
        "set_security_alert_state",
        "fetch_closed_security_alerts",
    ):
        assert callable(getattr(GitHubItemsProvider, name))


def test_lite_gives_the_workbench_an_open_file_callback() -> None:
    source = inspect.getsource(DocumentToolsMixin.cmd_github_workbench)
    assert "open_file_reference_cb=self._open_github_file_reference" in source


class _Frame(lite_github_open.GitHubFileOpenMixin):
    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.opened: list[str] = []
        control = SimpleNamespace(SetValue=self.opened.append, SetInsertionPoint=lambda _pos: None)
        window = SimpleNamespace(control=control, _announce=self.spoken.append)
        self.app = SimpleNamespace(new_window=lambda _mode: window)

    def _announce(self, message: str) -> None:
        self.spoken.append(message)


def test_lite_opens_a_github_file_as_a_new_untitled_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Provider:
        def __init__(self, token=None) -> None:
            pass

        def fetch_repo_file_text(self, repo: str, path: str, ref: str) -> str:
            assert (repo, path, ref) == ("o/r", "docs/a.md", "main")
            return "# A"

        def close(self) -> None:
            pass

    class _Thread:
        def __init__(self, target=None, daemon=None) -> None:
            self._target = target

        def start(self) -> None:
            self._target()

    monkeypatch.setattr("quill.core.github.items_provider.GitHubItemsProvider", _Provider)
    monkeypatch.setattr("quill.core.github.token_store.load_github_token", lambda: "")
    monkeypatch.setattr(lite_github_open.threading, "Thread", _Thread)
    patch_call_after(monkeypatch)
    frame = _Frame()
    frame._open_github_file_reference("https://github.com/o/r/blob/main/docs/a.md")
    assert frame.opened == ["# A"]
    assert frame.spoken[-1].startswith("a.md from GitHub, opened as a new untitled document.")


def test_lite_refuses_a_link_that_is_not_a_file() -> None:
    frame = _Frame()
    frame._open_github_file_reference("https://github.com/o/r/issues/3")
    assert frame.opened == []
    assert frame.spoken == ["That link is not a GitHub file."]
