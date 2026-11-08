"""QUILL Lite's GitHub rows: the Workbench, workbench mode's views, the switch and Clone.

Every handler is called here (GATE-LITE-COVER counts a call, by AST), against a
small host made of the real mixin, with the dialogs and the network replaced.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.apps.lite_github_workbench import GitHubWorkbenchLiteMixin
from quill.apps.lite_window_tools import DocumentToolsMixin
from quill.core.github import workbench_menu


class _Host(GitHubWorkbenchLiteMixin):
    def __init__(self, *, safe_mode: bool = False, path: Path | None = Path("notes.md")) -> None:
        self.app = SimpleNamespace(safe_mode=safe_mode)
        self.path = path
        self.said: list[str] = []
        self.rebuilt = 0

    def _announce(self, message: str) -> None:
        self.said.append(message)

    def _open_github_file_reference(self, _url: str) -> None:
        pass

    def _github_workbench_as_guest(self, _retry: object) -> bool:
        return True

    def rebuild_workbench_menus(self) -> None:
        self.rebuilt += 1


@pytest.fixture
def opened(monkeypatch):
    """Patch the gates and both windows; return the log of what opened, on which view."""
    calls: list[object] = []

    class _Provider:
        def __init__(self, *, token=None) -> None:
            calls.append(("provider", token))

        def close(self) -> None:
            calls.append("closed")

    class _Items:
        def __init__(self, _parent, _provider, *, initial_repo="", initial_view="", **_kw):
            calls.append(("items", initial_repo, initial_view))

        def show(self) -> None:
            pass

    class _Explore:
        def __init__(self, _parent, _provider, *, initial_view=None, **_kw) -> None:
            calls.append(("explore", initial_view))

        def show(self) -> None:
            pass

    monkeypatch.setattr("quill.core.github.github_provider.require_pygithub", lambda: None)
    monkeypatch.setattr("quill.core.github.consent.load_github_consent_complete", lambda: True)
    monkeypatch.setattr("quill.core.github.token_store.load_github_token", lambda: "secret")
    monkeypatch.setattr("quill.core.github.local_repo.detect_github_repo", lambda _p: "owner/repo")
    monkeypatch.setattr("quill.core.github.items_provider.GitHubItemsProvider", _Provider)
    monkeypatch.setattr("quill.ui.github_items_dialog.GitHubItemsDialog", _Items)
    monkeypatch.setattr("quill.ui.github_explore_dialog.GitHubExploreDialog", _Explore)
    return calls


def test_lite_github_workbench_uses_shared_viewer_and_closes_provider(opened) -> None:
    DocumentToolsMixin.cmd_github_workbench(_Host())
    assert opened == [("provider", "secret"), ("items", "owner/repo", ""), "closed"]


def test_lite_github_workbench_refuses_safe_mode_before_network(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "quill.core.github.github_provider.require_pygithub",
        lambda: calls.append("dependency check"),
    )
    monkeypatch.setattr(
        "quill.apps.lite_github_workbench.show_message_box",
        lambda *_args: calls.append("message"),
    )
    _Host(safe_mode=True).cmd_github_workbench()
    assert calls == ["message"]


@pytest.mark.parametrize(
    ("press", "expected"),
    [
        (lambda h: h.cmd_github_inbox(), ("explore", "attention")),
        (lambda h: h.cmd_github_my_work(), ("explore", "my_work")),
        (lambda h: h.cmd_github_notifications(), ("explore", "notifications")),
        (lambda h: h.cmd_github_explore(), ("explore", None)),
        (lambda h: h.cmd_github_issues(), ("items", "owner/repo", "issues")),
        (lambda h: h.cmd_github_actions_runs(), ("items", "owner/repo", "runs")),
        (lambda h: h.cmd_github_releases(), ("items", "owner/repo", "releases")),
    ],
)
def test_each_github_menu_row_opens_its_view_through_the_one_gate(opened, press, expected) -> None:
    host = _Host()
    press(host)
    assert opened == [("provider", "secret"), expected, "closed"]
    assert host.said == []  # the window's title says it (GATE-13)


def test_the_switch_flips_the_mode_says_one_sentence_and_rebuilds() -> None:
    host = _Host()
    host.cmd_toggle_github_workbench()
    assert host._github_workbench_mode is True
    assert host.said == [workbench_menu.ANNOUNCE_ON]
    host.cmd_toggle_github_workbench()
    assert host._github_workbench_mode is False
    assert host.said == [workbench_menu.ANNOUNCE_ON, workbench_menu.ANNOUNCE_OFF]
    assert host.rebuilt == 2


def test_clone_hands_the_shared_flow_this_windows_repository_and_voice(monkeypatch) -> None:
    seen: dict[str, object] = {}
    monkeypatch.setattr("quill.core.github.local_repo.detect_github_repo", lambda _p: "o/r")
    monkeypatch.setattr("quill.ui.github_clone.start_clone", lambda host: seen.update(host=host))
    host = _Host()
    host.cmd_github_clone()
    clone_host = seen["host"]
    assert clone_host.initial_repo == "o/r"
    assert clone_host.parent is host
    clone_host.announce("Cloned o/r.")
    assert host.said == ["Cloned o/r."]


def test_after_a_clone_quill_lite_offers_a_file_and_not_now_opens_nothing(monkeypatch) -> None:
    import wx

    opened: list[Path] = []
    host = _Host()
    host.app.open_path = opened.append
    monkeypatch.setattr(
        "quill.apps.lite_github_workbench.show_message_box", lambda *_a, **_k: wx.NO
    )
    host._after_github_clone(Path("C:/clones/r"))
    assert opened == []


def test_a_document_window_in_workbench_mode_has_the_github_menu_after_tools(
    wx_session_app,
) -> None:
    """The shipped ``_build_menus`` on a real frame: GitHub after Tools, File's
    rows gone into it, the View mark set, and back again."""
    import wx

    from quill.apps.lite_window_menus import DocumentMenuMixin
    from quill.core.lite.keymap import default_keymap

    class _App:
        keymap = default_keymap()
        frames: list[object] = []
        settings = SimpleNamespace(
            theme="light", word_wrap=True, show_status_bar=True, recent_files=[]
        )

        def feature_enabled(self, _area: str) -> bool:
            return True

    class _Frame(wx.Frame, DocumentMenuMixin, GitHubWorkbenchLiteMixin):
        def __init__(self) -> None:
            super().__init__(None)
            self.app = _App()
            self.path = None
            self.said: list[str] = []
            self._selection_anchor = None
            self._build_menus()

        def _announce(self, message: str) -> None:
            self.said.append(message)

        def extend_selection_active(self) -> bool:
            return False

        def sound_is_quiet(self) -> bool:
            return False

        def run_unless_read_only(self, handler: str) -> None:
            getattr(self, handler)()

    frame = _Frame()
    try:
        assert frame.GetMenuBar().FindMenu("GitHub") == wx.NOT_FOUND
        frame.cmd_toggle_github_workbench()
        bar = frame.GetMenuBar()
        titles = [bar.GetMenuLabel(i) for i in range(bar.GetMenuCount())]
        assert titles.index("&GitHub") == titles.index("&Tools") + 1
        file_menu = bar.GetMenu(bar.FindMenu("File"))
        assert all("GitHub Workbench" not in i.GetItemLabel() for i in file_menu.GetMenuItems())
        assert frame._check_items["cmd_toggle_github_workbench"].IsChecked()
        leave = frame._menu_items["cmd_toggle_github_workbench"]
        assert leave.GetItemLabel().startswith("Lea&ve Workbench Mode")
        frame.GetEventHandler().ProcessEvent(wx.CommandEvent(wx.wxEVT_MENU, leave.GetId()))
        bar = frame.GetMenuBar()
        assert bar.FindMenu("GitHub") == wx.NOT_FOUND
        assert not frame._check_items["cmd_toggle_github_workbench"].IsChecked()
        assert frame.said == [workbench_menu.ANNOUNCE_ON, workbench_menu.ANNOUNCE_OFF]
    finally:
        frame.Destroy()
