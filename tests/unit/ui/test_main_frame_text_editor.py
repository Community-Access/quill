"""Make QUILL My Text Editor, and Open QUILL instead of Notepad (Settings only).

The flows' behaviour is QUILL Lite's, tested in
``tests/unit/apps/test_lite_text_editor_commands.py`` against the same shared
module (:mod:`quill.ui.text_editor_commands`); the Preferences group that runs
them is tested in ``tests/unit/ui/test_text_editor_prefs.py``. What is QUILL's
and tested here: that QUILL runs the shared flows rather than its own, with
QUILL's profile (``quill.exe -m quill``, ``Quill.Document``, QUILL's Default apps
page), its own frame as the dialog parent, no menu row and no chord (Settings is
the only door since 2026-10-03), and that only one editor at a time owns
Notepad -- each names the other before replacing it.

No test here writes a registry value or raises an administrator prompt: the
system seam is a fake that applies reg.exe's effect to a dict.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core import windows_editor as editor  # noqa: E402
from quill.core.keymap import DEFAULT_KEYMAP  # noqa: E402
from quill.ui import text_editor_commands as shared  # noqa: E402
from quill.ui.main_frame_text_editor import TextEditorMixin  # noqa: E402
from quill.ui.text_editor_commands import TextEditorCommandsMixin  # noqa: E402

QUILL_EXE = r"C:\Program Files\QUILL for All\quill.exe"
QUILL_ARGV = [QUILL_EXE, "-m", "quill"]
QUILL_VALUE = f'"{QUILL_EXE}" -m quill --notepad'
LITE_VALUE = r'"C:\Program Files\QUILL Lite\QuillLite.exe" --notepad'


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
                self.reader.keys.setdefault(key, {})["Debugger"] = QUILL_VALUE
            elif editor.is_ours(editor.QUILL, self.reader.value(key, "Debugger")):
                del self.reader.keys[key]["Debugger"]
        return self.DONE


class Host(TextEditorMixin):
    """What QUILL's MainFrame supplies to the mixin, and nothing more."""

    def __init__(self) -> None:
        self.frame = SimpleNamespace()
        self.announcements: list[str] = []
        self.refocused = 0

    def _announce(self, message: str, **_kwargs: Any) -> None:
        self.announcements.append(message)

    def _return_focus_to_editor(self) -> None:
        self.refocused += 1


def _on(host: Any) -> bool:
    """Whether Windows opens *host*'s editor in place of Notepad, read now."""
    reader = host._text_editor_system().MachineReader()
    return editor.read_notepad_state(host._text_editor_profile(), reader).on


@pytest.fixture
def answers(monkeypatch):
    """The message boxes, answered in order; records caption, text and parent."""
    state = SimpleNamespace(replies=[], asked=[])

    def fake_box(message, caption, style, parent=None, **_kw):
        state.asked.append((caption, message, parent))
        return state.replies.pop(0)

    monkeypatch.setattr(shared, "show_message_box", fake_box)
    monkeypatch.setattr(shared, "launcher", lambda _profile: (QUILL_ARGV, f"{QUILL_EXE},0"))
    return state


def _system(monkeypatch, reader: FakeReader | None = None, **kwargs: Any) -> FakeSystem:
    fake = FakeSystem(reader or FakeReader(), **kwargs)
    monkeypatch.setattr(shared, "system", fake)
    return fake


def _windows_11(**debuggers: str) -> FakeReader:
    keys: dict[str, dict[str, object]] = {editor.IFEO_KEY: {"UseFilter": 1}}
    for index, path in enumerate((
        r"C:\Windows\System32\notepad.exe",
        r"C:\Windows\SysWOW64\notepad.exe",
    )):
        keys[rf"{editor.IFEO_KEY}\{index}"] = {"FilterFullPath": path}
    for key, value in debuggers.items():
        target = editor.IFEO_KEY if key == "parent" else rf"{editor.IFEO_KEY}\{key[1:]}"
        keys[target]["Debugger"] = value
    return FakeReader(keys)


# -- one capability, not two ------------------------------------------------------


def test_quill_runs_the_shared_commands_rather_than_its_own() -> None:
    """A second implementation is how the family rule gets broken quietly."""
    assert issubclass(TextEditorMixin, TextEditorCommandsMixin)
    own = {name for name in vars(TextEditorMixin) if name.startswith("cmd_")}
    assert own == set(), f"QUILL has grown its own text-editor commands: {sorted(own)}"


def test_main_frame_answers_both_commands() -> None:
    from quill.ui.main_frame import MainFrame

    assert issubclass(MainFrame, TextEditorMixin)
    for name in ("cmd_make_default_editor", "cmd_toggle_notepad_replacement"):
        assert hasattr(MainFrame, name), name


def test_quill_lite_runs_the_same_commands() -> None:
    from quill.apps.lite_window_text_editor import DocumentTextEditorMixin

    assert issubclass(DocumentTextEditorMixin, TextEditorCommandsMixin)
    assert {n for n in vars(DocumentTextEditorMixin) if n.startswith("cmd_")} == set()


# -- Settings is the only door ------------------------------------------------------


def test_there_is_no_menu_row_and_no_chord() -> None:
    """Owner decision 2026-10-03: Settings > General > Windows and your files only."""
    for command_id in ("tools.make_default_editor", "tools.notepad_replacement"):
        assert command_id not in DEFAULT_KEYMAP
    root = Path(__file__).resolve().parents[3] / "quill" / "ui"
    for name in ("main_frame_menu.py", "main_frame_text_editor.py"):
        source = (root / name).read_text(encoding="utf-8")
        assert "_append_text_editor_rows" not in source, name
    own = (root / "main_frame_text_editor.py").read_text(encoding="utf-8")
    assert "try_register" not in own and "AppendCheckItem" not in own


# -- Make QUILL My Text Editor ---------------------------------------------------------


def test_ok_registers_quill_and_opens_quills_default_apps_page(monkeypatch, answers) -> None:
    fake = _system(monkeypatch)
    answers.replies = [wx.OK]
    host = Host()
    host.cmd_make_default_editor()
    caption, message, parent = answers.asked[0]
    assert caption == "Make QUILL My Text Editor"
    assert parent is host.frame
    assert "pick QUILL," in message and "Word" in message and "EPUB" in message
    command = r"Software\Classes\Quill.Document\shell\open\command"
    assert fake.written[(command, "")] == f'"{QUILL_EXE}" -m quill "%1"'
    assert fake.written[(r"Software\RegisteredApplications", "QUILL")] == (
        r"Software\QUILL\Capabilities"
    )
    assert fake.opened == ["ms-settings:defaultapps?registeredAppUser=QUILL"]
    assert host.announcements == [
        "QUILL is ready in Default apps. Choose it for .txt and any other type."
    ]


def test_cancel_writes_nothing_and_returns_to_the_document(monkeypatch, answers) -> None:
    fake = _system(monkeypatch)
    answers.replies = [wx.CANCEL]
    host = Host()
    host.cmd_make_default_editor()
    assert fake.written == {} and fake.opened == []
    assert host.refocused == 1


def test_an_administrator_install_of_quill_is_not_copied(monkeypatch, answers) -> None:
    reader = FakeReader({
        r"Software\Classes\Quill.Document\shell\open\command": {"": f'"{QUILL_EXE}" -m quill "%1"'},
        r"Software\RegisteredApplications": {"QUILL": r"Software\QUILL\Capabilities"},
    })
    fake = _system(monkeypatch, reader)
    answers.replies = [wx.OK]
    Host().cmd_make_default_editor()
    assert fake.written == {}
    assert fake.opened == ["ms-settings:defaultapps?registeredAppMachine=QUILL"]


# -- Open QUILL Instead of Notepad -----------------------------------------------------


def test_turning_it_on_asks_then_runs_reg_once(monkeypatch, answers) -> None:
    fake = _system(monkeypatch, _windows_11())
    answers.replies = [wx.YES, wx.NO]
    host = Host()
    host.cmd_toggle_notepad_replacement()
    caption, warning, _parent = answers.asked[0]
    assert caption == "Open QUILL Instead of Notepad"
    assert "every user on this computer" in warning
    assert "clear Open QUILL instead of Notepad" in warning  # how to undo it
    assert len(fake.elevated) == 1
    _exe, parameters = fake.elevated[0]
    assert parameters.count(" add ") == 3
    assert "-m quill --notepad" in parameters
    assert _on(host)
    assert host.announcements[0] == "QUILL now opens in place of Notepad."
    assert "App execution aliases" in answers.asked[1][1]


def test_quill_lite_is_named_before_quill_replaces_it(monkeypatch, answers) -> None:
    """One hook, one owner: say who loses it, by name, not as a command line."""
    _system(monkeypatch, _windows_11(parent=LITE_VALUE, k0=LITE_VALUE), build=19045)
    answers.replies = [wx.YES]
    host = Host()
    host.cmd_toggle_notepad_replacement()
    _caption, warning, _parent = answers.asked[0]
    assert warning.startswith("QUILL Lite opens in place of Notepad now.")
    assert "QUILL Lite no longer will" in warning
    assert "QuillLite.exe" not in warning
    assert _on(host)


def test_quill_is_named_before_quill_lite_replaces_it(monkeypatch, answers) -> None:
    from quill.apps.lite_window_text_editor import DocumentTextEditorMixin

    class LiteHost(DocumentTextEditorMixin):
        control = SimpleNamespace(SetFocus=lambda: None)

        def _announce(self, message: str) -> None:
            pass

    reader = _windows_11(parent=QUILL_VALUE)
    monkeypatch.setattr("quill.apps.lite_window_text_editor.system", FakeSystem(reader))
    asked: list[str] = []
    monkeypatch.setattr(
        "quill.apps.lite_window_text_editor.show_message_box",
        lambda message, *_a, **_k: asked.append(message) or wx.NO,
    )
    LiteHost().cmd_toggle_notepad_replacement()
    assert asked[0].startswith("QUILL opens in place of Notepad now.")


def test_turning_quill_off_leaves_quill_lites_value_alone(monkeypatch, answers) -> None:
    reader = _windows_11(parent=QUILL_VALUE, k0=QUILL_VALUE, k1=LITE_VALUE)
    fake = _system(monkeypatch, reader)
    answers.replies = [wx.YES]
    host = Host()
    host.cmd_toggle_notepad_replacement()
    _exe, parameters = fake.elevated[0]
    assert parameters.count(" delete ") == 2
    assert reader.value(rf"{editor.IFEO_KEY}\1", "Debugger") == LITE_VALUE
    assert host.announcements == ["Notepad is back. QUILL no longer opens in its place."]


def test_a_declined_prompt_changes_nothing(monkeypatch, answers) -> None:
    _system(monkeypatch, _windows_11(), outcome="declined")
    answers.replies = [wx.YES]
    host = Host()
    host.cmd_toggle_notepad_replacement()
    assert not _on(host)
    assert host.announcements == ["Nothing changed. Windows did not get administrator approval."]


# -- launched as Notepad ---------------------------------------------------------------


def test_quills_command_line_honours_notepad(monkeypatch) -> None:
    """Windows runs the Debugger value with Notepad's command line after it."""
    import quill.__main__ as entry

    seen: list[list[str]] = []

    class _Stop(Exception):
        pass

    def capture(arguments: list[str]) -> None:
        seen.append(arguments)
        raise _Stop

    monkeypatch.setattr(entry, "_parse_cli_arguments", capture)
    monkeypatch.setattr(
        entry.sys, "argv", ["quill", "--notepad", r"C:\Windows\notepad.exe", r"C:\notes\a.txt"]
    )
    with pytest.raises(_Stop):
        entry.main()
    assert seen == [[r"C:\notes\a.txt"]]


def test_quills_parser_accepts_what_notepad_mode_produces() -> None:
    from quill.__main__ import _parse_cli_arguments

    blank = _parse_cli_arguments(editor.translate_notepad_argv(["--notepad", "notepad.exe"]))
    assert blank.document_kind == "plain" and blank.paths == []
    opened = _parse_cli_arguments(
        editor.translate_notepad_argv(
            ["--notepad", "notepad.exe", "/p", r"C:\notes\a.txt"], exists=lambda _p: True
        )
    )
    assert opened.paths == [r"C:\notes\a.txt"]
