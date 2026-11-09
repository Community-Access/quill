"""QUILL Lite reaches the last four GitHub features through the shared surfaces.

Lite opens the same ``GitHubItemsDialog`` (and, from it, the same Explore and
Review windows) that QUILL does, so a feature is in Lite exactly when it lives
on one of those. This pins that it stayed there, and that New Gist starts from
the Lite document the way it starts from QUILL's.
"""

from __future__ import annotations

import inspect

from quill.apps.lite_github_open import GitHubFileOpenMixin
from quill.apps.lite_shell_menu import ShellMenuMixin
from quill.apps.lite_window_tools import DocumentToolsMixin
from quill.ui.github_explore_dialog import GitHubExploreDialog
from quill.ui.github_items_dialog import GitHubItemsDialog
from quill.ui.github_pr_review_dialog import GitHubPullReviewDialog


def test_last_four_actions_live_on_the_shared_dialogs() -> None:
    for name in ("_assign_to_copilot", "_open_commit_comments", "_add_copilot_and_commit_actions"):
        assert callable(getattr(GitHubItemsDialog, name))
    for name in ("_new_gist", "_edit_gist", "_star_gist", "_delete_gist", "_add_gist_actions"):
        assert callable(getattr(GitHubExploreDialog, name))
    assert callable(GitHubPullReviewDialog._request_copilot_review)


def test_lite_passes_its_document_to_new_gist() -> None:
    # The row goes through the one opener every GitHub row shares (lite_github_workbench.py).
    assert "self.open_github_items()" in inspect.getsource(DocumentToolsMixin.cmd_github_workbench)
    source = inspect.getsource(DocumentToolsMixin.open_github_items)
    assert 'gist_source_cb=getattr(self, "_github_gist_source", None)' in source
    assert issubclass(ShellMenuMixin, GitHubFileOpenMixin)


class _Control:
    def __init__(self, value: str, selection: str = "") -> None:
        self._value, self._selection = value, selection

    def GetValue(self) -> str:  # noqa: N802 - wx API
        return self._value

    def GetStringSelection(self) -> str:  # noqa: N802 - wx API
        return self._selection


class _Window(GitHubFileOpenMixin):
    def __init__(self, control: object, path: object) -> None:
        self.control, self.path = control, path


def test_gist_source_prefers_the_selection_then_the_document() -> None:
    assert _Window(_Control("all", "part"), "C:/notes/todo.md")._github_gist_source() == (
        "todo.md",
        "part",
    )
    assert _Window(_Control("all"), None)._github_gist_source() == ("notes.md", "all")


def test_the_empty_window_starts_a_blank_gist() -> None:
    shell = _Window(object(), None)
    assert shell._github_gist_source() == ("notes.md", "")
