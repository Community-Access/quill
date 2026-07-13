"""Tests for GitHubItemsDialog's Quick Filter (GHManage parity, Ctrl+Shift+F):
live local narrowing of the already-loaded list, no network request, no
keyboard-focus theft, and no per-keystroke screen-reader interruption.
"""

from __future__ import annotations

import pytest
import wx

from quill.core.github.items_provider import GitHubBranch, GitHubRepoForkInfo
from quill.ui.github_items_dialog import VIEW_BRANCHES, VIEW_ISSUES, GitHubItemsDialog


class _FakeProvider:
    def fetch_fork_info(self, repo: str) -> GitHubRepoForkInfo:
        return GitHubRepoForkInfo(is_fork=False)


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.fixture
def dlg(wx_app, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(wx, "CallAfter", lambda fn, *a, **k: fn(*a, **k))
    frame = wx.Frame(None)
    dialog = GitHubItemsDialog(frame, _FakeProvider(), initial_repo="owner/repo")
    dialog._repo = "owner/repo"
    statuses: list[tuple[str, bool]] = []
    announcements: list[str] = []

    def _record_status(message: str, *, announce: bool = True) -> None:
        statuses.append((message, announce))
        if announce:
            announcements.append(message)

    dialog._set_status = _record_status
    dialog._announce = lambda message: announcements.append(message)
    dialog._reload = lambda: None
    dialog.statuses = statuses
    dialog.announcements = announcements
    return dialog


_ROWS = [
    GitHubBranch(name="main", commit_sha="a" * 40, url="u"),
    GitHubBranch(name="feature-login", commit_sha="b" * 40, url="u"),
    GitHubBranch(name="release-1.0", commit_sha="c" * 40, url="u"),
]


def _seed(dlg) -> None:
    dlg._view = VIEW_BRANCHES
    dlg._unfiltered_rows = list(_ROWS)
    dlg._apply_quick_filter(move_focus=True)


def test_filter_narrows_rows_case_insensitively(dlg) -> None:
    _seed(dlg)
    dlg._quick_filter_ctrl.ChangeValue("FEATURE")
    dlg._on_quick_filter_changed(None)
    assert [r.name for r in dlg._rows] == ["feature-login"]
    assert dlg._unfiltered_rows == _ROWS  # the fetched set is untouched


def test_filter_matches_across_all_visible_columns(dlg) -> None:
    """Matches the rendered short commit sha column, not just the name."""
    _seed(dlg)
    dlg._quick_filter_ctrl.ChangeValue(("a" * 40)[:7])
    dlg._on_quick_filter_changed(None)
    assert [r.name for r in dlg._rows] == ["main"]


def test_clearing_filter_restores_full_list(dlg) -> None:
    _seed(dlg)
    dlg._quick_filter_ctrl.ChangeValue("main")
    dlg._on_quick_filter_changed(None)
    assert len(dlg._rows) == 1
    dlg._quick_filter_ctrl.ChangeValue("")
    dlg._on_quick_filter_changed(None)
    assert dlg._rows == _ROWS


def test_no_matches_clears_details_instead_of_crashing(dlg) -> None:
    _seed(dlg)
    dlg._quick_filter_ctrl.ChangeValue("no-such-branch")
    dlg._on_quick_filter_changed(None)
    assert dlg._rows == []


def test_keystroke_does_not_announce_but_updates_status_text(dlg) -> None:
    _seed(dlg)
    dlg.statuses.clear()
    dlg.announcements.clear()
    dlg._quick_filter_ctrl.ChangeValue("main")
    dlg._on_quick_filter_changed(None)
    message, announced = dlg.statuses[-1]
    assert "filter 'main': 1 Branches" in message
    assert announced is False
    assert dlg.announcements == []  # no screen-reader interruption per keystroke


def test_fetch_completing_does_announce(dlg) -> None:
    dlg._view = VIEW_BRANCHES
    dlg._on_rows_loaded(list(_ROWS), VIEW_BRANCHES)
    message, announced = dlg.statuses[-1]
    assert announced is True
    assert dlg.announcements  # a real load is still announced


def test_escape_clears_filter_when_box_has_focus(dlg) -> None:
    _seed(dlg)
    dlg._quick_filter_ctrl.ChangeValue("main")
    dlg._on_quick_filter_changed(None)
    dlg._quick_filter_ctrl.SetFocus()
    dlg._quick_filter_has_focus = lambda: True

    class _Esc:
        def GetKeyCode(self) -> int:
            return wx.WXK_ESCAPE

        def GetModifiers(self) -> int:
            return wx.MOD_NONE

        def Skip(self) -> None:
            pass

    dlg._on_char_hook(_Esc())
    assert dlg._quick_filter_query == ""
    assert dlg._quick_filter_ctrl.GetValue() == ""
    assert dlg._rows == _ROWS


def test_escape_is_a_no_op_when_filter_box_lacks_focus(dlg) -> None:
    _seed(dlg)
    dlg._quick_filter_ctrl.ChangeValue("main")
    dlg._on_quick_filter_changed(None)
    dlg._quick_filter_has_focus = lambda: False

    class _Esc:
        def GetKeyCode(self) -> int:
            return wx.WXK_ESCAPE

        def GetModifiers(self) -> int:
            return wx.MOD_NONE

        def Skip(self) -> None:
            pass

    dlg._on_char_hook(_Esc())
    assert dlg._quick_filter_query == "main"  # untouched


def test_ctrl_shift_f_focuses_the_quick_filter_box(dlg) -> None:
    class _Chord:
        def GetKeyCode(self) -> int:
            return ord("F")

        def GetModifiers(self) -> int:
            return wx.MOD_CONTROL | wx.MOD_SHIFT

        def Skip(self) -> None:
            pass

    dlg._on_char_hook(_Chord())
    assert wx.Window.FindFocus() is dlg._quick_filter_ctrl


def test_switching_view_resets_the_filter(dlg) -> None:
    _seed(dlg)
    dlg._quick_filter_ctrl.ChangeValue("main")
    dlg._on_quick_filter_changed(None)
    dlg._switch_view(VIEW_ISSUES)
    assert dlg._quick_filter_query == ""
    assert dlg._quick_filter_ctrl.GetValue() == ""


def test_loading_a_different_repo_resets_the_filter(dlg) -> None:
    _seed(dlg)
    dlg._quick_filter_ctrl.ChangeValue("main")
    dlg._on_quick_filter_changed(None)
    dlg._repo_ctrl.SetValue("other/repo")
    dlg._fetch_fork_info_async = lambda _repo: None
    dlg._on_load(None)
    assert dlg._quick_filter_query == ""
    assert dlg._quick_filter_ctrl.GetValue() == ""
