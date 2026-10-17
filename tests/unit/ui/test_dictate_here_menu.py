"""Edit > Dictate Here in Quill Radio and QUILL Cast (dict.md D-16).

The shared wiring (``quill/ui/support_menu.insert_edit_menu`` and
``quill/ui/dictate_here_ui.py``) on an in-memory menu bar, and Quill Radio's
real menu bar in a developer build, where QUILL Transcribe is offered. No
real window is driven: the command is called directly, with the request,
the owner lock and the launcher faked.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.app_keymaps import APP_KEYMAPS  # noqa: E402
from quill.ui import dictate_here_ui  # noqa: E402
from quill.ui.dictate_here_ui import COMMAND_ID, DictateHereMixin  # noqa: E402


@pytest.fixture
def wx_app() -> Any:
    app = wx.GetApp() or wx.App()
    yield app


class _Host(DictateHereMixin):
    """Just enough of an app frame for the Edit menu and the command."""

    def __init__(self, app_id: str) -> None:
        self.frame = wx.Frame(None)
        self._app_keymap_id = app_id
        self.keymap = dict(APP_KEYMAPS[app_id])
        self.said: list[str] = []
        self.kept: list[Any] = []

    def _announce(self, message: str, **_kw: Any) -> None:
        self.said.append(message)

    def _keep_menu_ids(self, *refs: Any) -> None:
        self.kept.extend(refs)

    def _menu_label(self, title: str, command_id: str) -> str:
        key = self.keymap.get(command_id)
        return f"{title}\t{key}" if key else title

    def undo_last_action(self) -> None: ...

    def open_undo_history(self) -> None: ...


def _edit_labels(host: _Host, *, released: bool, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    from quill.ui.support_menu import insert_edit_menu

    monkeypatch.setattr(dictate_here_ui, "dictate_here_available", lambda: released)
    bar = wx.MenuBar()
    bar.Append(wx.Menu(), "&Station")
    insert_edit_menu(host, bar, wx)
    return [item.GetItemLabel() for item in bar.GetMenu(1).GetMenuItems() if not item.IsSeparator()]


@pytest.mark.parametrize("app_id", ["cast", "radio"])
def test_the_edit_menu_shows_dictate_here_with_its_key(
    wx_app: Any, app_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = _Host(app_id)
    try:
        labels = _edit_labels(host, released=True, monkeypatch=monkeypatch)
        assert "&Dictate Here\tCtrl+F11" in labels
        # No other item in the menu claims the access letter.
        letters = [label.split("&", 1)[1][:1].lower() for label in labels if "&" in label]
        assert letters.count("d") == 1
    finally:
        host.frame.Destroy()


def test_no_item_where_transcribe_is_not_offered(
    wx_app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = _Host("radio")
    try:
        labels = _edit_labels(host, released=False, monkeypatch=monkeypatch)
        assert not any("Dictate Here" in label for label in labels)
    finally:
        host.frame.Destroy()


@pytest.mark.parametrize("app_id", ["cast", "radio"])
def test_ctrl_f11_is_the_key_in_both_apps_and_nothing_else_has_it(app_id: str) -> None:
    keys = APP_KEYMAPS[app_id]
    assert keys[COMMAND_ID] == "Ctrl+F11"
    assert [name for name, key in keys.items() if key == "Ctrl+F11"] == [COMMAND_ID]


@pytest.mark.parametrize("app_id", ["cast", "radio"])
def test_the_command_asks_transcribe_as_this_app(
    wx_app: Any, app_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core import dictation_owner

    monkeypatch.setattr(dictation_owner, "current_owner", lambda **_kw: "transcribe")
    host = _Host(app_id)
    try:
        host.dictate_here()
        assert [(r.command, r.sender) for r in dictation_owner.take_requests()] == [
            ("start", app_id)
        ]
        assert host.said == []  # QUILL Transcribe says "Dictation on" itself (GATE-13)
    finally:
        host.frame.Destroy()


def test_the_command_says_why_when_it_cannot(wx_app: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core import app_launcher, dictation_owner

    monkeypatch.setattr(dictation_owner, "current_owner", lambda **_kw: "")
    monkeypatch.setattr(app_launcher, "is_app_released", lambda _app: False)
    host = _Host("cast")
    try:
        host.dictate_here()
        assert host.said == [
            "Dictate Here needs QUILL Transcribe, which is not installed with this copy."
        ]
    finally:
        host.frame.Destroy()


def test_quill_radio_real_menu_bar_carries_it_once_in_a_developer_build(
    quill_data_dir: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real bar, where every other Radio key lives: Ctrl+F11 claimed once."""
    monkeypatch.setenv("QUILL_DEV_BUILD", "1")
    app = wx.App()
    from quill.apps.radio import RadioAppFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy

    frame = RadioAppFrame()
    try:
        bar = frame.frame.GetMenuBar()
        found: list[str] = []

        def walk(menu: Any, path: str) -> None:
            for item in menu.GetMenuItems():
                if item.GetSubMenu() is not None:
                    walk(item.GetSubMenu(), path)
                elif (
                    "\t" in item.GetItemLabel() and item.GetItemLabel().split("\t")[1] == "Ctrl+F11"
                ):
                    found.append(f"{path} > {item.GetItemLabel()}")

        for index in range(bar.GetMenuCount()):
            walk(bar.GetMenu(index), bar.GetMenuLabel(index))
        assert found == ["&Edit > &Dictate Here\tCtrl+F11"]
        assert frame.commands.get(COMMAND_ID) is not None
    finally:
        frame._radio_shutdown()
        set_transition_announcement_policy(None)
        del app


@pytest.mark.parametrize(
    ("safe", "shown", "owner", "active", "starts"),
    [
        (False, False, True, False, True),  # in the tray, ready: start
        (False, True, True, False, False),  # its window is in front: the field is ours
        (True, False, True, False, False),  # Safe Mode
        (False, False, False, False, False),  # Inkwell owns Dictate Anywhere
        (False, False, True, True, False),  # already dictating
    ],
)
def test_transcribe_started_by_dictate_here(
    safe: bool, shown: bool, owner: bool, active: bool, starts: bool
) -> None:
    from types import SimpleNamespace

    from quill.apps.transcribe_dictation import TranscribeDictationMixin

    started: list[bool] = []
    host = SimpleNamespace(
        _safe_mode=safe,
        frame=SimpleNamespace(IsShown=lambda: shown),
        _own_dictate_anywhere=lambda: owner,
        dictation_active=lambda: active,
        start_dictation=lambda: started.append(True),
    )
    TranscribeDictationMixin.dictate_here_at_launch(host)  # type: ignore[arg-type]
    assert started == ([True] if starts else [])


def _key(field: Any, code: int, *, ctrl: bool = True) -> Any:
    event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(code)
    event.SetControlDown(ctrl)
    event.SetEventObject(field)
    return event


def test_the_key_works_in_a_dialogs_search_box_and_only_there(
    wx_app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Add Podcast and Search Stations are modal dialogs, where the main
    window's menu accelerator is never consulted."""
    from quill.ui.dictate_here_ui import key_matches

    assert key_matches("Ctrl+F11", wx.WXK_F11, wx.MOD_CONTROL)
    assert not key_matches("Ctrl+F11", wx.WXK_F11, wx.MOD_NONE)
    assert not key_matches("", wx.WXK_F11, wx.MOD_CONTROL)

    host = _Host("cast")
    asked: list[bool] = []
    monkeypatch.setattr(host, "dictate_here", lambda: asked.append(True))
    dialog = wx.Dialog(host.frame)
    search = wx.TextCtrl(dialog)
    button = wx.Button(dialog)
    main_field = wx.TextCtrl(host.frame)
    try:
        assert host._dictate_here_key_in_dialog(_key(search, wx.WXK_F11)) is True
        assert asked == [True]
        # The main window has the menu accelerator: never twice.
        assert host._dictate_here_key_in_dialog(_key(main_field, wx.WXK_F11)) is False
        # Not a text field, or not the key: typing goes on untouched.
        assert host._dictate_here_key_in_dialog(_key(button, wx.WXK_F11)) is False
        assert host._dictate_here_key_in_dialog(_key(search, wx.WXK_F11, ctrl=False)) is False
        # Rebound: the new key, not the old one.
        host.keymap[COMMAND_ID] = "Alt+Shift+D"
        assert host._dictate_here_key_in_dialog(_key(search, wx.WXK_F11)) is False
        assert asked == [True]
    finally:
        dialog.Destroy()
        host.frame.Destroy()


def test_the_filter_is_installed_once_and_removed_with_the_frame(
    wx_app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(dictate_here_ui, "dictate_here_available", lambda: True)
    host = _Host("radio")
    registered: list[str] = []
    host.commands = type(
        "Commands", (), {"try_register": lambda _s, cid, *_a, **_k: registered.append(cid)}
    )()
    host._register_dictate_here_command()
    first = host._dictate_here_filter
    host._install_dictate_here_filter()
    assert host._dictate_here_filter is first and registered == [COMMAND_ID]
    host.frame.Destroy()
    wx_app.Yield()
    if host._dictate_here_filter is not None:  # destroy is deferred on some builds
        host._remove_dictate_here_filter()
    assert host._dictate_here_filter is None
