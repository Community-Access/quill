"""Make QUILL Lite My Text Editor, and Open QUILL Lite instead of Notepad.

Reached from Preferences > Windows and your files only, with no menu row and no
chord, since 2026-10-03; the group itself is tested in
tests/unit/ui/test_text_editor_prefs.py. These tests drive the shared flows the
group runs.

The registry, the administrator prompt and Settings are all replaced: the fake
system records what would have been written, which command would have been
run elevated, and which Settings page would have opened. No test here writes a
real registry value or raises a real prompt.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

wx = pytest.importorskip("wx")

from quill.apps import lite_window_text_editor as module  # noqa: E402
from quill.core.lite import windows_editor as editor  # noqa: E402

LAUNCHER = r"C:\Program Files\QuillLite\QuillLite.exe"
ICON = r"C:\Program Files\QuillLite\quill-lite.ico"


class FakeReader:
    def __init__(self, keys: dict[str, dict[str, object]] | None = None) -> None:
        self.keys = keys or {}

    def value(self, path: str, name: str) -> object | None:
        return self.keys.get(path, {}).get(name)

    def subkeys(self, path: str) -> list[str]:
        prefix = path + "\\"
        return sorted({k[len(prefix) :].split("\\")[0] for k in self.keys if k.startswith(prefix)})


class FakeSystem:
    """``quill.platform.windows.editor_registration``, without the system."""

    DONE = "done"
    DECLINED = "declined"
    FAILED = "failed"

    def __init__(self, reader: FakeReader, *, build: int = 22631, outcome: str = "done") -> None:
        self.reader = reader
        self.build = build
        self.outcome = outcome
        self.written: dict[tuple[str, str], str] = {}
        self.opened: list[str] = []
        self.elevated: list[tuple[str, str]] = []
        self.notified = 0

    def CurrentUserWriter(self) -> object:  # noqa: N802 - the class it stands in for
        fake = self

        class _Writer:
            def set_value(self, path: str, name: str, data: str, kind: str) -> None:
                fake.written[(path, name)] = data

        return _Writer()

    def MachineReader(self) -> FakeReader:  # noqa: N802 - the class it stands in for
        return self.reader

    def notify_association_change(self) -> None:
        self.notified += 1

    def open_settings(self, uri: str) -> bool:
        self.opened.append(uri)
        return True

    def windows_build(self) -> int:
        return self.build

    def system32(self) -> Path:
        return Path(r"C:\Windows\System32")

    def run_elevated(self, executable: str, parameters: str) -> str:
        """Apply the reg.exe commands to the fake HKLM, the way Windows would."""
        self.elevated.append((executable, parameters))
        if self.outcome != self.DONE:
            return self.outcome
        turning_on = " add " in parameters
        for key in editor.notepad_keys(self.reader):
            if turning_on:
                self.reader.keys.setdefault(key, {})["Debugger"] = f'"{LAUNCHER}" --notepad'
            elif editor.is_ours(self.reader.value(key, "Debugger")):
                del self.reader.keys[key]["Debugger"]
        return self.DONE


@pytest.fixture
def answers(monkeypatch):
    """The message boxes, answered in order; records what each one said."""
    state = SimpleNamespace(replies=[], asked=[])

    def fake_box(message, caption, style, parent=None, **_kw):
        state.asked.append((caption, message))
        return state.replies.pop(0)

    monkeypatch.setattr(module, "show_message_box", fake_box)
    monkeypatch.setattr(module, "_launcher", lambda: ([LAUNCHER], ICON))
    return state


def _system(monkeypatch, reader: FakeReader | None = None, **kwargs) -> FakeSystem:
    fake = FakeSystem(reader or FakeReader(), **kwargs)
    monkeypatch.setattr(module, "system", fake)
    return fake


def _windows_11() -> FakeReader:
    keys: dict[str, dict[str, object]] = {editor.IFEO_KEY: {"UseFilter": 1}}
    for index, path in enumerate((
        r"C:\Windows\System32\notepad.exe",
        r"C:\Windows\SysWOW64\notepad.exe",
    )):
        keys[rf"{editor.IFEO_KEY}\{index}"] = {"FilterFullPath": path}
    return FakeReader(keys)


# -- Make QUILL Lite My Text Editor ------------------------------------------


def test_ok_registers_for_this_account_and_opens_quill_lites_default_apps_page(
    lite_window, monkeypatch, answers
) -> None:
    fake = _system(monkeypatch)
    answers.replies = [wx.OK]
    win = lite_window("", cursor=0)
    win.cmd_make_default_editor()
    caption, message = answers.asked[0]
    assert caption == "Make QUILL Lite My Text Editor"
    assert "only you can choose" in message
    assert "pick QUILL Lite" in message
    command = r"Software\Classes\QuillLite.Document\shell\open\command"
    assert fake.written[(command, "")] == f'"{LAUNCHER}" "%1"'
    assert fake.written[(r"Software\RegisteredApplications", "QUILL Lite")] == (
        editor.CAPABILITIES_KEY
    )
    assert not any("UserChoice" in path for path, _name in fake.written)
    assert fake.notified == 1
    assert fake.opened == ["ms-settings:defaultapps?registeredAppUser=QUILL%20Lite"]
    assert "Default apps" in win.announcements[-1]


def test_cancel_writes_nothing_and_opens_nothing(lite_window, monkeypatch, answers) -> None:
    fake = _system(monkeypatch)
    answers.replies = [wx.CANCEL]
    win = lite_window("", cursor=0)
    win.cmd_make_default_editor()
    assert fake.written == {}
    assert fake.opened == []
    assert win.announcements == []


def test_an_administrator_install_is_not_copied_into_this_account(
    lite_window, monkeypatch, answers
) -> None:
    reader = FakeReader({
        r"Software\Classes\QuillLite.Document\shell\open\command": {"": f'"{LAUNCHER}" "%1"'},
        r"Software\RegisteredApplications": {"QUILL Lite": editor.CAPABILITIES_KEY},
    })
    fake = _system(monkeypatch, reader)
    answers.replies = [wx.OK]
    win = lite_window("", cursor=0)
    win.cmd_make_default_editor()
    assert fake.written == {}
    assert fake.opened == ["ms-settings:defaultapps?registeredAppMachine=QUILL%20Lite"]


def test_windows_10_gets_the_general_default_apps_page(lite_window, monkeypatch, answers) -> None:
    fake = _system(monkeypatch, build=19045)
    answers.replies = [wx.OK]
    win = lite_window("", cursor=0)
    win.cmd_make_default_editor()
    assert fake.opened == ["ms-settings:defaultapps"]


# -- Open QUILL Lite Instead of Notepad --------------------------------------


def test_turning_it_on_asks_first_then_runs_reg_once_as_administrator(
    lite_window, monkeypatch, answers
) -> None:
    fake = _system(monkeypatch, _windows_11())
    answers.replies = [wx.YES, wx.NO]
    win = lite_window("", cursor=0)
    win.cmd_toggle_notepad_replacement()
    _caption, warning = answers.asked[0]
    assert "every user on this computer" in warning
    assert "administrator approval" in warning
    assert "Windows and your files in Preferences" in warning  # how to undo it
    assert len(fake.elevated) == 1
    executable, parameters = fake.elevated[0]
    assert executable == r"C:\Windows\System32\cmd.exe"
    assert parameters == editor.elevated_parameters(
        editor.turn_on_commands(_windows_11(), [LAUNCHER]), r"C:\Windows\System32\reg.exe"
    )
    assert parameters.count(" add ") == 3  # the parent and both Windows 11 subkeys
    assert _on(win)
    assert win.announcements[0] == "QUILL Lite now opens in place of Notepad."
    # Then the Windows 11 step: the app execution alias, explained.
    _caption, alias = answers.asked[1]
    assert "App execution aliases" in alias
    assert fake.opened == []  # answered No


def test_the_windows_11_alias_page_opens_when_asked(lite_window, monkeypatch, answers) -> None:
    fake = _system(monkeypatch, _windows_11())
    answers.replies = [wx.YES, wx.YES]
    win = lite_window("", cursor=0)
    win.cmd_toggle_notepad_replacement()
    assert fake.opened == ["ms-settings:advanced-apps"]


def test_windows_10_has_no_alias_step(lite_window, monkeypatch, answers) -> None:
    _system(monkeypatch, FakeReader(), build=19045)
    answers.replies = [wx.YES]
    win = lite_window("", cursor=0)
    win.cmd_toggle_notepad_replacement()
    assert len(answers.asked) == 1
    assert _on(win)


def test_saying_no_runs_nothing(lite_window, monkeypatch, answers) -> None:
    fake = _system(monkeypatch, _windows_11())
    answers.replies = [wx.NO]
    win = lite_window("", cursor=0)
    win.cmd_toggle_notepad_replacement()
    assert fake.elevated == []
    assert not _on(win)


def test_a_declined_administrator_prompt_changes_nothing_and_says_so(
    lite_window, monkeypatch, answers
) -> None:
    _system(monkeypatch, _windows_11(), outcome="declined")
    answers.replies = [wx.YES]
    win = lite_window("", cursor=0)
    win.cmd_toggle_notepad_replacement()
    assert not _on(win)
    assert win.announcements == ["Nothing changed. Windows did not get administrator approval."]


def test_turning_it_off_removes_only_quill_lites_values(lite_window, monkeypatch, answers) -> None:
    reader = _windows_11()
    ours = f'"{LAUNCHER}" --notepad'
    reader.keys[editor.IFEO_KEY]["Debugger"] = ours
    reader.keys[rf"{editor.IFEO_KEY}\0"]["Debugger"] = ours
    fake = _system(monkeypatch, reader)
    answers.replies = [wx.YES]
    win = lite_window("", cursor=0)
    assert _on(win)
    win.cmd_toggle_notepad_replacement()
    _caption, question = answers.asked[0]
    assert question.startswith("Put Notepad back?")
    _exe, parameters = fake.elevated[0]
    assert parameters.count(" delete ") == 2
    assert " add " not in parameters
    assert not _on(win)
    assert win.announcements == ["Notepad is back. QUILL Lite no longer opens in its place."]


def test_another_programs_replacement_is_named_before_it_is_replaced(
    lite_window, monkeypatch, answers
) -> None:
    reader = FakeReader({editor.IFEO_KEY: {"Debugger": r'"C:\npp\notepad++.exe" -z'}})
    _system(monkeypatch, reader, build=19045)
    answers.replies = [wx.NO]
    win = lite_window("", cursor=0)
    win.cmd_toggle_notepad_replacement()
    _caption, warning = answers.asked[0]
    assert "notepad++.exe" in warning


def test_quill_lite_has_no_menu_row_and_no_chord_for_either() -> None:
    """Owner decision 2026-10-03: Preferences > Windows and your files only."""
    from quill.core.lite.commands import COMMANDS

    handlers = {row[3] for row in COMMANDS}
    assert "cmd_make_default_editor" not in handlers
    assert "cmd_toggle_notepad_replacement" not in handlers


def _on(win) -> bool:
    """Whether Windows opens QUILL Lite in place of Notepad, read now."""
    reader = win._text_editor_system().MachineReader()
    return editor.read_notepad_state(reader).on
