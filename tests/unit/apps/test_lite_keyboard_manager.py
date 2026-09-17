"""The Keyboard Manager: what it says, and what it refuses.

The dialog is where a rebinding can go wrong in the ways nothing else can catch:
taking a key silently, refusing one without saying why, and assigning one wx will
accept and then never fire. Each of those is asserted here rather than left to a
person to notice, because all three are silent from the user's side -- the key
simply does nothing and no message is ever produced.
"""

from __future__ import annotations

import pytest
import wx

from quill.apps.lite_keymap_editor import (
    KeymapEditorDialog,
    binding_is_dispatchable,
    chord_from_event,
    row_text,
    sort_key,
)
from quill.core.lite.keymap import default_keymap


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.fixture()
def parent(wx_app):
    frame = wx.Frame(None)
    yield frame
    frame.Destroy()
    wx_app.Yield()


@pytest.fixture()
def manager(parent):
    said: list[str] = []
    dialog = KeymapEditorDialog(parent, keymap=default_keymap(), announce_cb=said.append)
    dialog.said = said  # type: ignore[attr-defined]
    yield dialog
    dialog.dialog.Destroy()


class _KeyEvent:
    """The four things chord_from_event asks a wx key event."""

    def __init__(self, code: int, *, ctrl=False, shift=False, alt=False) -> None:
        self._code, self._ctrl, self._shift, self._alt = code, ctrl, shift, alt

    def GetKeyCode(self) -> int:  # noqa: N802 - wx API shape
        return self._code

    def ControlDown(self) -> bool:  # noqa: N802
        return self._ctrl

    def ShiftDown(self) -> bool:  # noqa: N802
        return self._shift

    def AltDown(self) -> bool:  # noqa: N802
        return self._alt


# ---------------------------------------------------------------------------
# rows and ordering, which need no display


def test_a_row_leads_with_the_command() -> None:
    """The key is the answer to the row, not its name."""
    assert row_text("File > Save", "Ctrl+S") == "File > Save -- Ctrl+S"


def test_a_command_with_no_key_says_so_rather_than_trailing_off() -> None:
    assert row_text("File > Save", "") == "File > Save -- no key"


def test_rows_sort_by_menu_path() -> None:
    titles = ["Tools > Preferences", "Edit > Lines > Sort", "Edit > Copy"]
    assert sorted(titles, key=sort_key) == [
        "Edit > Copy",
        "Edit > Lines > Sort",
        "Tools > Preferences",
    ]


# ---------------------------------------------------------------------------
# recording a chord


def test_a_modifier_on_its_own_is_not_a_chord_yet() -> None:
    """Otherwise pressing Ctrl reports "Ctrl" before the key arrives."""
    assert chord_from_event(_KeyEvent(wx.WXK_CONTROL, ctrl=True)) == ""


def test_a_letter_with_modifiers_is_the_chord() -> None:
    assert chord_from_event(_KeyEvent(ord("K"), ctrl=True, shift=True)) == "Ctrl+Shift+K"


def test_a_function_key_keeps_its_name() -> None:
    assert chord_from_event(_KeyEvent(wx.WXK_F7)) == "F7"


def test_a_named_key_keeps_its_name() -> None:
    assert chord_from_event(_KeyEvent(wx.WXK_PAGEDOWN, ctrl=True)) == "Ctrl+PageDown"


# ---------------------------------------------------------------------------
# whether wx can actually fire it -- the check that cannot live in core


def test_a_real_chord_is_dispatchable() -> None:
    assert binding_is_dispatchable("Ctrl+Shift+S")


def test_a_chord_wx_refuses_is_not_dispatchable() -> None:
    """wx silently drops what it cannot parse, leaving the menu advertising it."""
    assert not binding_is_dispatchable("Ctrl+Shift+Plus")


def test_nothing_is_not_dispatchable() -> None:
    assert not binding_is_dispatchable("")


# ---------------------------------------------------------------------------
# the dialog


def test_it_opens_on_every_command(manager) -> None:
    assert manager.listbox.GetCount() == len(manager._handlers)
    assert manager.listbox.GetCount() > 100


def test_typing_narrows_the_list(manager) -> None:
    manager.search.SetValue("sort lines")
    manager._on_search()
    assert 0 < manager.listbox.GetCount() < len(manager._handlers)
    assert "Sort Lines" in manager.listbox.GetString(0)


def test_a_search_with_no_answer_says_so(manager) -> None:
    manager.search.SetValue("zzzz")
    manager._on_search()
    assert "No commands match" in manager.status.GetLabel()
    assert manager.said[-1] == manager.status.GetLabel()


def test_recording_a_taken_key_names_the_command_that_has_it(manager) -> None:
    manager.record.SetValue(True)
    manager._on_record_toggled()
    manager._record_chord(_KeyEvent(ord("S"), ctrl=True))
    assert "File > Save" in manager.status.GetLabel()


def test_recording_a_free_key_says_it_is_free(manager) -> None:
    """The letter is worked out, not assumed.

    This named Q outright, and the day a real command claimed Ctrl+Alt+Shift+Q
    (Back Up Settings, #1501) the test failed for a reason that had nothing to
    do with what it checks -- which is that an unclaimed chord reads as free.
    """
    import string

    from quill.core.lite.keymap import conflicting_handlers, default_keymap

    keymap = default_keymap()
    letter = next(
        candidate
        for candidate in string.ascii_uppercase
        if not conflicting_handlers(keymap, "cmd_new", f"Ctrl+Alt+Shift+{candidate}")
    )
    manager.record.SetValue(True)
    manager._on_record_toggled()
    manager._record_chord(_KeyEvent(ord(letter), ctrl=True, shift=True, alt=True))
    assert manager.status.GetLabel().endswith("is free.")


def test_recording_a_reserved_key_says_why_not(manager) -> None:
    manager.record.SetValue(True)
    manager._on_record_toggled()
    manager._record_chord(_KeyEvent(wx.WXK_INSERT))
    assert "NVDA" in manager.status.GetLabel()


def test_recording_ignores_a_bare_modifier(manager) -> None:
    manager.record.SetValue(True)
    manager._on_record_toggled()
    before = manager.status.GetLabel()
    manager._record_chord(_KeyEvent(wx.WXK_SHIFT, shift=True))
    assert manager.status.GetLabel() == before


# ---------------------------------------------------------------------------
# assigning


def _select(manager, handler: str) -> None:
    manager._refresh_list("", keep=handler)


def test_resetting_a_command_already_on_its_default_says_so(manager) -> None:
    _select(manager, "cmd_save")
    manager._reset_selected()
    assert "already on its default key" in manager.status.GetLabel()


def test_resetting_a_changed_command_puts_the_key_back(manager) -> None:
    manager._keymap["cmd_save"] = "Ctrl+Shift+Alt+W"
    _select(manager, "cmd_save")
    manager._reset_selected()
    assert manager._keymap["cmd_save"] == "Ctrl+S"
    assert "back to Ctrl+S" in manager.status.GetLabel()


def test_reset_everything_with_nothing_changed_refuses_quietly(manager) -> None:
    manager._reset_all()
    assert "Nothing to reset" in manager.status.GetLabel()


def test_the_dialog_never_edits_the_app_keymap_in_place(parent) -> None:
    """Escape out of a session of experimenting has to leave the keys alone."""
    live = default_keymap()
    dialog = KeymapEditorDialog(parent, keymap=live)
    try:
        dialog._keymap["cmd_save"] = "Ctrl+Shift+Alt+W"
        assert live["cmd_save"] == "Ctrl+S"
    finally:
        dialog.dialog.Destroy()


def test_assigning_with_nothing_selected_asks_rather_than_failing(manager) -> None:
    manager.listbox.SetSelection(wx.NOT_FOUND)
    manager._assign_selected()
    assert "Move to a command in the list first." in manager.status.GetLabel()


def test_a_chord_wx_will_not_fire_is_refused_at_assign_time(manager, monkeypatch) -> None:
    """The one failure that looks like success.

    ``wx.AcceleratorEntry`` silently drops what it cannot parse, so a chord that
    normalises cleanly and that wx refuses used to be *assigned* -- the menu then
    advertised a key that did nothing and nothing said so. The check existed and
    ran only from the Audit button, which is to say after the damage (bad.md H2).
    """
    import quill.apps.lite_keymap_editor as editor

    monkeypatch.setattr(editor, "ask_for_chord", lambda *_a, **_k: "Ctrl+Shift+Plus")
    monkeypatch.setattr(editor, "show_message_box", lambda *_a, **_k: None)
    monkeypatch.setattr(editor.keymap_mod, "describe_binding_problem", lambda _c: "")
    before = manager._keymap.get("cmd_save")

    _select(manager, "cmd_save")
    manager._assign_selected()

    assert manager._keymap.get("cmd_save") == before
    assert "will not send" in manager.status.GetLabel()


def test_every_status_message_is_also_announced(manager) -> None:
    """A label change on an unfocused control is what a reader does not say."""
    manager._say("Something happened.")
    assert manager.status.GetLabel() == "Something happened."
    assert manager.said[-1] == "Something happened."


# ---------------------------------------------------------------------------
# what a cleared binding does to the menu


def test_a_cleared_binding_leaves_no_trailing_tab_in_the_label(wx_app) -> None:
    """Moving a taken key frees the command that had it, and it has to survive.

    A label ending in a bare tab is a menu item advertising an accelerator that
    is not there -- the regression class PRD 8.14's binding/label gate names,
    and one the command table alone could never produce because every row in it
    ships a key.
    """
    from quill.apps.lite_window_menus import DocumentMenuMixin
    from quill.core.lite.keymap import default_keymap

    keymap = default_keymap()
    keymap["cmd_save"] = ""

    class _App:
        def __init__(self) -> None:
            self.keymap = keymap
            self.frames: list[object] = []
            self.settings = _Settings()

        def feature_enabled(self, _area: str) -> bool:
            return True

    class _Settings:
        theme = "light"
        word_wrap = True
        show_status_bar = True
        recent_files: list[str] = []

    class _Frame(wx.Frame, DocumentMenuMixin):
        def __init__(self) -> None:
            super().__init__(None)
            self.app = _App()
            self._selection_anchor = None
            self._extend_selection_mode = False
            self._build_menus()

        def extend_selection_active(self) -> bool:
            """Read by _sync_check_items for the Extend Selection Mode mark.

            The mode is invisible -- no selection on screen while it is on --
            so the menu's check mark is one of the two places its state can be
            seen at all.
            """
            return False

        def sound_is_quiet(self) -> bool:
            """Read by _sync_check_items for the Quiet Mode mark.

            Quiet mode is shared with QUILL and deliberately not cached on the
            frame, so the mark asks for it every time the menu is built -- which
            makes it something a stub frame has to answer.
            """
            return False

    frame = _Frame()
    try:
        labels: list[str] = []

        def walk(menu) -> None:
            for item in menu.GetMenuItems():
                if item.IsSeparator():
                    continue
                labels.append(item.GetItemLabel())
                sub = item.GetSubMenu()
                if sub is not None:
                    walk(sub)

        bar = frame.GetMenuBar()
        for index in range(bar.GetMenuCount()):
            walk(bar.GetMenu(index))

        assert labels
        trailing = [label for label in labels if label.endswith("\t")]
        assert trailing == [], trailing
        saves = [label for label in labels if label.startswith("&Save")]
        assert saves and all("\t" not in label for label in saves), saves
    finally:
        frame.Destroy()
        wx_app.Yield()
