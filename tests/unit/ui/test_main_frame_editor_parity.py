"""QUILL's half of Paste Copied Files and the replace jobs: rows and hooks, no commands.

The handlers are ``quill.ui.paste_file``'s and ``quill.ui.replace_jobs``'s, the
same ones QUILL Lite's table names. Checked here: the adapter defines no
``cmd_*``, every row is a QUILL Lite command with the same (empty) key, and the
commands run through QUILL's hooks -- one undo step, QUILL's data folder,
forced speech -- the way the shared handlers expect.
"""

from __future__ import annotations

import ast
from pathlib import Path

from quill.core.keymap import DEFAULT_KEYMAP
from quill.core.lite.commands import COMMANDS
from quill.core.lite.parity import COMMAND_EQUIVALENTS
from quill.core.replace_jobs import ReplaceJob, ReplaceStep, save_replace_jobs
from quill.core.say_commands import ClipboardContents
from quill.ui import main_frame_editor_parity as adapter
from quill.ui import paste_file, replace_jobs, say_commands
from quill.ui.main_frame_editor_parity import (
    PASTE_FILE_ROW,
    REPLACE_JOB_ROWS,
    EditorParityAdapterMixin,
)


def test_the_adapter_defines_no_command_of_its_own() -> None:
    tree = ast.parse(Path(adapter.__file__).read_text(encoding="utf-8"))
    defined = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("cmd_")
    ]
    assert defined == []


def test_every_row_is_a_lite_command_with_the_same_key() -> None:
    lite_keys = {handler: key for _menu, _label, key, handler, _kind in COMMANDS if handler}
    for command_id, _label, handler in (PASTE_FILE_ROW, *REPLACE_JOB_ROWS):
        assert hasattr(EditorParityAdapterMixin, handler), handler
        assert COMMAND_EQUIVALENTS[handler] == command_id
        assert DEFAULT_KEYMAP[command_id] == lite_keys[handler] == "", command_id


class _Editor:
    def __init__(self, text: str) -> None:
        self.text = text
        self.selection = (0, 0)
        self.caret = 0
        self.focused = False

    def GetValue(self) -> str:  # noqa: N802 - wx API shape
        return self.text

    def GetSelection(self) -> tuple[int, int]:  # noqa: N802
        return self.selection

    def SetSelection(self, start: int, end: int) -> None:  # noqa: N802
        self.selection = (start, end)

    def SetInsertionPoint(self, pos: int) -> None:  # noqa: N802
        self.caret = pos

    def SetFocus(self) -> None:  # noqa: N802
        self.focused = True


class _Document:
    def __init__(self) -> None:
        self.text = ""

    def set_text(self, text: str) -> None:
        self.text = text


class _Host(EditorParityAdapterMixin):
    def __init__(self, text: str, data_dir: Path) -> None:
        self.editor = _Editor(text)
        self.document = _Document()
        self.frame = object()
        self.said: list[tuple[str, bool]] = []
        self.atomic: list[tuple[int, int, str]] = []
        self.read_only = False
        self.data_dir = data_dir

    def _announce(self, message: str, *, force: bool = False, sound: str = "") -> None:
        self.said.append((message, force))

    def _atomic_replace(self, start: int, end: int, updated: str) -> None:
        self.atomic.append((start, end, updated))
        self.editor.text = self.editor.text[:start] + updated + self.editor.text[end:]

    def _document_is_read_only(self) -> bool:
        return self.read_only

    def _confirm_whole_document_rewrite(self) -> bool:
        return True

    def _show_modal_dialog(self, _dialog: object, _title: str) -> int:
        raise AssertionError("every window is replaced in these tests")

    def _replace_jobs_dir(self) -> Path:
        return self.data_dir


def test_quill_keeps_its_jobs_in_its_own_data_folder(tmp_path) -> None:
    from quill.core.paths import app_data_dir

    assert EditorParityAdapterMixin._replace_jobs_dir(_Host("", tmp_path)) == Path(app_data_dir())


def test_run_replace_job_writes_once_and_speaks_with_force(tmp_path, monkeypatch) -> None:
    host = _Host("teh cat, teh hat", tmp_path)
    save_replace_jobs(
        tmp_path / "replace_jobs.json", [ReplaceJob("Fix", [ReplaceStep("teh", "the")])]
    )
    monkeypatch.setattr(replace_jobs, "choose_replace_job", lambda *_a, **_k: 0)

    host.cmd_run_replace_job()

    assert host.atomic == [(0, 16, "the cat, the hat")]
    assert host.document.text == "the cat, the hat"
    assert host.said == [("Fix: 2 replacements", True)]
    assert host.editor.focused


def test_run_replace_job_on_the_selection(tmp_path, monkeypatch) -> None:
    host = _Host("teh teh", tmp_path)
    host.editor.selection = (4, 7)
    save_replace_jobs(
        tmp_path / "replace_jobs.json", [ReplaceJob("Fix", [ReplaceStep("teh", "the")])]
    )
    seen: dict[str, bool] = {}

    def chooser(*_a, in_selection: bool, **_k) -> int:
        seen["in_selection"] = in_selection
        return 0

    monkeypatch.setattr(replace_jobs, "choose_replace_job", chooser)

    host.cmd_run_replace_job()

    assert seen == {"in_selection": True}
    assert host.editor.text == "teh the"


def test_a_read_only_document_is_refused_before_any_window(tmp_path, monkeypatch) -> None:
    host = _Host("abc", tmp_path)
    host.read_only = True
    monkeypatch.setattr(
        replace_jobs, "choose_replace_job", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError)
    )

    host.cmd_run_replace_job()
    host.cmd_paste_file()

    assert [message for message, _ in host.said] == ["Document is read-only"] * 2


def test_paste_file_inserts_at_the_caret_as_one_undo_step(tmp_path, monkeypatch) -> None:
    note = tmp_path / "note.txt"
    note.write_text("hello", encoding="utf-8")
    host = _Host("[]", tmp_path)
    host.editor.selection = (1, 1)
    contents = ClipboardContents(files=(str(note),))
    monkeypatch.setattr(say_commands, "read_clipboard", lambda: contents)
    monkeypatch.setattr(paste_file, "choose_paste_kind", lambda *_a, **_k: "text")

    host.cmd_paste_file()

    assert host.atomic == [(1, 1, "hello")]
    assert host.editor.caret == 6
    assert host.said == [("Pasted the text of 1 file", True)]


def test_open_keyboard_reference_shows_its_key_in_the_help_menu(tmp_path) -> None:
    class _Menu:
        def __init__(self) -> None:
            self.labels: dict[int, str] = {}

        def SetLabel(self, menu_id: int, label: str) -> None:  # noqa: N802
            self.labels[menu_id] = label

    class _Chain:
        def _install_whats_new_item(self, _menu: object) -> None:
            self.whats_new_installed = True

    class _Frame(EditorParityAdapterMixin, _Chain):
        _id_open_keyboard_reference = 42

        def _menu_label(self, label: str, command_id: str) -> str:
            return f"{label}\t{DEFAULT_KEYMAP[command_id]}"

    frame, menu = _Frame(), _Menu()
    frame._install_whats_new_item(menu)

    assert menu.labels[42] == "Open Keyboard &Reference\tCtrl+Shift+Grave, Shift+K"
    assert frame.whats_new_installed
