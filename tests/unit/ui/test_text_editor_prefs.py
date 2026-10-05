"""Preferences > Windows and your files, in QUILL and in QUILL Lite.

The group is :mod:`quill.ui.text_editor_prefs`, built into both editors'
Preferences: a status line, Make <app> My Text Editor..., and Open <app>
instead of Notepad. None of it is stored -- Windows' registry is the truth --
so these tests fake the registry and the administrator prompt exactly as the
command tests do, and check that the checkbox shows the truth when the window
opens, that OK runs the same confirmation and prompt as the menu, that the box
goes back to the truth when nothing changed, and that the outcome is said once.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core import windows_editor as editor  # noqa: E402
from quill.ui import text_editor_commands as shared  # noqa: E402
from quill.ui.main_frame_text_editor import TextEditorMixin  # noqa: E402
from quill.ui.preferences_search import _targets, find_settings  # noqa: E402
from quill.ui.text_editor_prefs import notepad_status  # noqa: E402

QUILL_EXE = r"C:\Program Files\QUILL for All\quill.exe"
QUILL_ARGV = [QUILL_EXE, "-m", "quill"]
QUILL_VALUE = f'"{QUILL_EXE}" -m quill --notepad'
LITE_EXE = r"C:\Program Files\QUILL Lite\QuillLite.exe"
LITE_VALUE = f'"{LITE_EXE}" --notepad'


@pytest.fixture
def app():
    current = wx.GetApp()
    if current is not None:
        try:
            current.GetAppName()
            return current
        except Exception:  # noqa: BLE001 - a dead App is no App
            pass
    return wx.App()


@pytest.fixture(autouse=True)
def help_provider(app):
    """SetHelpText stores nothing without one, which the app installs at startup."""
    wx.HelpProvider.Set(wx.SimpleHelpProvider())


class FakeReader:
    def __init__(self, keys: dict[str, dict[str, object]] | None = None) -> None:
        self.keys = keys or {}

    def value(self, path: str, name: str) -> object | None:
        return self.keys.get(path, {}).get(name)

    def subkeys(self, path: str) -> list[str]:
        prefix = path + "\\"
        return sorted({k[len(prefix) :].split("\\")[0] for k in self.keys if k.startswith(prefix)})


class FakeSystem:
    DONE = "done"
    DECLINED = "declined"
    FAILED = "failed"

    def __init__(self, reader: FakeReader, value: str, *, outcome: str = "done") -> None:
        self.reader = reader
        self.value = value
        self.outcome = outcome
        self.elevated: list[str] = []
        self.opened: list[str] = []
        self.written: dict[tuple[str, str], str] = {}

    def CurrentUserWriter(self) -> object:  # noqa: N802 - the class it stands in for
        fake = self

        class _Writer:
            def set_value(self, path: str, name: str, data: str, kind: str) -> None:
                fake.written[(path, name)] = data

        return _Writer()

    def MachineReader(self) -> FakeReader:  # noqa: N802 - the class it stands in for
        return self.reader

    def notify_association_change(self) -> None:
        pass

    def open_settings(self, uri: str) -> bool:
        self.opened.append(uri)
        return True

    def windows_build(self) -> int:
        return 19045  # no Windows 11 alias step, so one question per change

    def system32(self) -> Path:
        return Path(r"C:\Windows\System32")

    def run_elevated(self, executable: str, parameters: str) -> str:
        self.elevated.append(parameters)
        if self.outcome != self.DONE:
            return self.outcome
        turning_on = " add " in parameters
        for key in editor.notepad_keys(self.reader):
            entry = self.reader.keys.setdefault(key, {})
            if turning_on:
                entry["Debugger"] = self.value
            elif entry.get("Debugger") == self.value:
                del entry["Debugger"]
        return self.DONE


class QuillHost(TextEditorMixin):
    """What QUILL's MainFrame supplies: a frame, an announcer, a way back."""

    def __init__(self, frame: Any) -> None:
        self.frame = frame
        self.announcements: list[str] = []
        self.refocused = 0

    def _announce(self, message: str, **_kwargs: Any) -> None:
        self.announcements.append(message)

    def _return_focus_to_editor(self) -> None:
        self.refocused += 1


@pytest.fixture
def boxes(monkeypatch):
    """Message boxes answered in order; records (caption, parent)."""
    state = SimpleNamespace(replies=[], asked=[])

    def fake_box(message, caption, style, parent=None, **_kw):
        state.asked.append((caption, parent, message))
        return state.replies.pop(0)

    monkeypatch.setattr(shared, "show_message_box", fake_box)
    monkeypatch.setattr(shared, "launcher", lambda _p: (QUILL_ARGV, f"{QUILL_EXE},0"))
    return state


def _quill(app, monkeypatch, reader: FakeReader, **kwargs: Any):
    fake = FakeSystem(reader, QUILL_VALUE, **kwargs)
    monkeypatch.setattr(shared, "system", fake)
    frame = wx.Frame(None)
    dialog = wx.Dialog(frame, title="Settings")
    sizer = wx.BoxSizer(wx.VERTICAL)
    host = QuillHost(frame)
    changed: list[bool] = []
    group = host._add_text_editor_prefs(dialog, dialog, sizer, lambda: changed.append(True))
    return SimpleNamespace(
        fake=fake, frame=frame, dialog=dialog, host=host, group=group, changed=changed
    )


@pytest.fixture
def cleanup():
    windows: list[Any] = []
    yield windows
    for window in windows:
        window.Destroy()


# -- the status line ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("debugger", "sentence"),
    [
        (None, "Nothing opens in place of Notepad. Notepad opens as usual."),
        (QUILL_VALUE, "QUILL opens in place of Notepad."),
        (LITE_VALUE, "QUILL Lite opens in place of Notepad."),
        (
            r'"C:\npp\notepad++.exe" -notepadStyleCmdline -z',
            "Another program opens in place of Notepad: notepad++.exe.",
        ),
    ],
)
def test_the_status_line_names_who_opens_in_place_of_notepad(debugger, sentence) -> None:
    keys = {editor.IFEO_KEY: {"Debugger": debugger}} if debugger else {}
    state = editor.read_notepad_state(editor.QUILL, FakeReader(keys))
    assert notepad_status(editor.QUILL, state) == sentence


# -- QUILL: Settings > General ---------------------------------------------------------


def test_the_group_shows_the_truth_and_is_findable(app, monkeypatch, cleanup) -> None:
    built = _quill(app, monkeypatch, FakeReader({editor.IFEO_KEY: {"Debugger": LITE_VALUE}}))
    cleanup.append(built.frame)
    group = built.group
    assert group.heading.GetLabel() == "Windows and your files"
    assert group.status.GetLabel() == "QUILL Lite opens in place of Notepad."
    assert group.make_button.GetLabel() == "Make QUILL My Te&xt Editor..."
    assert group.notepad_check.GetLabel() == "&Open QUILL instead of Notepad"
    assert group.notepad_check.GetValue() is False
    for control in (group.heading, group.status, group.make_button, group.notepad_check):
        assert control.GetHelpText().strip(), control.GetLabel()
    targets = _targets(built.dialog)
    assert "Open QUILL instead of Notepad" in [t.label for t in find_settings(targets, "notepad")]
    assert "Make QUILL My Text Editor..." in [
        t.label for t in find_settings(targets, "text editor")
    ]
    assert built.dialog.text_editor_prefs is group


def test_ok_with_nothing_changed_asks_nothing(app, monkeypatch, boxes, cleanup) -> None:
    built = _quill(app, monkeypatch, FakeReader())
    cleanup.append(built.frame)
    assert built.group.commit() == "unchanged"
    assert boxes.asked == [] and built.fake.elevated == []


def test_checking_it_runs_the_same_flow_owned_by_the_window(
    app, monkeypatch, boxes, cleanup
) -> None:
    built = _quill(app, monkeypatch, FakeReader())
    cleanup.append(built.frame)
    built.group.notepad_check.SetValue(True)
    boxes.replies = [wx.YES]
    assert built.group.commit() == "on"
    caption, parent, _text = boxes.asked[0]
    assert caption == "Open QUILL Instead of Notepad"
    assert parent is built.dialog  # the question belongs to Preferences, not the frame
    assert len(built.fake.elevated) == 1
    assert built.group.notepad_check.GetValue() is True
    assert built.group.status.GetLabel() == "QUILL opens in place of Notepad."
    assert built.host.announcements == ["QUILL now opens in place of Notepad."]
    assert built.host.refocused == 0  # focus stays in Preferences
    assert built.host._text_editor_dialog_owner is None


def test_saying_no_puts_the_box_back_and_says_so_once(app, monkeypatch, boxes, cleanup) -> None:
    built = _quill(app, monkeypatch, FakeReader())
    cleanup.append(built.frame)
    built.group.notepad_check.SetValue(True)
    boxes.replies = [wx.NO]
    assert built.group.commit() == "cancelled"
    assert built.group.notepad_check.GetValue() is False
    assert built.fake.elevated == []
    assert built.host.announcements == ["Notepad is unchanged."]


def test_a_declined_prompt_puts_the_box_back_and_says_so_once(
    app, monkeypatch, boxes, cleanup
) -> None:
    built = _quill(app, monkeypatch, FakeReader(), outcome="declined")
    cleanup.append(built.frame)
    built.group.notepad_check.SetValue(True)
    boxes.replies = [wx.YES]
    assert built.group.commit() == "declined"
    assert built.group.notepad_check.GetValue() is False
    assert built.host.announcements == [
        "Nothing changed. Windows did not get administrator approval."
    ]


def test_unchecking_puts_notepad_back(app, monkeypatch, boxes, cleanup) -> None:
    built = _quill(app, monkeypatch, FakeReader({editor.IFEO_KEY: {"Debugger": QUILL_VALUE}}))
    cleanup.append(built.frame)
    assert built.group.notepad_check.GetValue() is True
    built.group.notepad_check.SetValue(False)
    boxes.replies = [wx.YES]
    assert built.group.commit() == "off"
    assert built.group.status.GetLabel() == (
        "Nothing opens in place of Notepad. Notepad opens as usual."
    )


def test_the_button_runs_make_my_text_editor(app, monkeypatch, boxes, cleanup) -> None:
    built = _quill(app, monkeypatch, FakeReader())
    cleanup.append(built.frame)
    boxes.replies = [wx.OK]
    built.group.make_default()
    caption, parent, _text = boxes.asked[0]
    assert caption == "Make QUILL My Text Editor" and parent is built.dialog
    assert built.fake.opened == ["ms-settings:defaultapps"]
    assert built.host.refocused == 0


def test_quills_settings_dialog_builds_the_group_and_commits_on_apply() -> None:
    """The Settings dialog is too large to build in a unit test; its two
    seams are one line each, and these are they."""
    source = Path("quill/ui/main_frame_preferences.py").read_text(encoding="utf-8")
    assert "self._add_text_editor_prefs(dialog, _p, _ps, _mark_dirty)" in source
    assert "dialog.text_editor_prefs.commit()" in source


# -- QUILL Lite: Preferences --------------------------------------------------------------


def test_quill_lites_preferences_carry_the_same_group(app, monkeypatch, boxes) -> None:
    from quill.apps import lite_preferences
    from quill.apps.lite_window_text_editor import DocumentTextEditorMixin
    from quill.core.lite.settings import Settings

    reader = FakeReader({editor.IFEO_KEY: {"Debugger": QUILL_VALUE}})
    monkeypatch.setattr("quill.apps.lite_window_text_editor.system", FakeSystem(reader, LITE_VALUE))

    class LiteParent(wx.Frame, DocumentTextEditorMixin):
        def _announce(self, message: str) -> None:
            pass

    parent = LiteParent(None)
    seen: dict[str, Any] = {}

    def fake_modal(dialog, _title):
        group = dialog.text_editor_prefs
        seen["labels"] = (group.make_button.GetLabel(), group.notepad_check.GetLabel())
        seen["status"] = group.status.GetLabel()
        seen["checked"] = group.notepad_check.GetValue()
        targets = _targets(dialog)
        seen["found"] = [t.label for t in find_settings(targets, "notepad")]
        keys: list[str] = []
        for child in dialog.GetChildren():
            label = child.GetLabel() if hasattr(child, "GetLabel") else ""
            match = re.search(r"&(\w)", label or "")
            if match:
                keys.append(match.group(1).lower())
        seen["keys"] = keys
        return wx.ID_CANCEL

    monkeypatch.setattr(lite_preferences, "show_modal_dialog", fake_modal)
    try:
        lite_preferences.edit_preferences(parent, Settings())
    finally:
        parent.Destroy()
    assert seen["labels"] == (
        "Make QUILL Lite My Te&xt Editor...",
        "&Open QUILL Lite instead of Notepad",
    )
    assert seen["status"] == "QUILL opens in place of Notepad."
    assert seen["checked"] is False
    assert "Open QUILL Lite instead of Notepad" in seen["found"]
    # GATE-14: neither new access key is claimed by anything else in the window.
    assert seen["keys"].count("x") == 1
    assert seen["keys"].count("o") == 1
