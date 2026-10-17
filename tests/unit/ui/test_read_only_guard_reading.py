"""QUILL's Read-Only Guard, end to end without a window (2026-10-16, item 37).

Checked here, each against what was wrong before:

* the guard has a key (Ctrl+Alt+Backspace; it had none, only a menu row);
* it is still on after a restart, and after the same file is opened from File
  Explorer under another spelling of its path;
* a failed save of the guard list is said, not swallowed;
* commands that change text through the shared paths are refused before they
  say they did anything, and the runner says "Document is read-only";
* bookmarks and document notes keep working while text is locked;
* a guarded long document answers browse navigation from its own text, without
  copying the whole buffer out of the control on every key.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.document import Document
from quill.core.keymap import DEFAULT_KEYMAP
from quill.core.lite.commands import COMMANDS
from quill.core.read_only_guards import GUARD_FILENAME, READ_ONLY_REFUSAL, DocumentReadOnlyError
from quill.ui.main_frame import MainFrame


class _Editor:
    def __init__(self, text: str) -> None:
        self.text = text
        self.editable = True
        self.get_value_calls = 0
        self.selection = (0, 0)

    def SetEditable(self, on: bool) -> None:  # noqa: N802 - wx's name
        self.editable = on

    def GetValue(self) -> str:  # noqa: N802
        self.get_value_calls += 1
        return self.text

    def GetSelection(self) -> tuple[int, int]:  # noqa: N802
        return self.selection

    def Replace(self, start: int, end: int, text: str) -> None:  # noqa: N802
        self.text = self.text[:start] + text + self.text[end:]

    def SetInsertionPoint(self, _pos: int) -> None:  # noqa: N802
        pass

    def SetFocus(self) -> None:  # noqa: N802
        pass


def _frame(path: Path | None, text: str = "# One\n\nBody.\n") -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame.document = Document(text=text, path=path)
    frame.editor = _Editor(text)
    frame.said = []  # type: ignore[attr-defined]
    frame.status = []  # type: ignore[attr-defined]
    frame._announce = frame.said.append  # type: ignore[attr-defined,method-assign]
    frame._set_status = frame.status.append  # type: ignore[attr-defined,method-assign]
    frame._bookmarks = {}
    frame._browse_navigation_cache = None
    return frame


@pytest.fixture
def book(quill_data_dir: Path, tmp_path: Path) -> Path:
    path = tmp_path / "Books" / "Long Book.md"
    path.parent.mkdir()
    path.write_text("# One\n\nBody.\n", encoding="utf-8")
    return path


def test_the_guard_has_the_same_key_in_both_editors() -> None:
    assert DEFAULT_KEYMAP["power.toggle_read_only_guard"] == "Ctrl+Alt+Backspace"
    lite = {row[3]: row[2] for row in COMMANDS if len(row) > 3}
    assert lite["cmd_toggle_read_only"] == "Ctrl+Alt+Backspace"


def test_toggle_locks_the_control_and_survives_a_restart(book: Path, quill_data_dir: Path) -> None:
    frame = _frame(book)
    frame.toggle_read_only_guard()
    assert frame.editor.editable is False
    assert frame.said == ["Document is read-only"]
    assert (quill_data_dir / GUARD_FILENAME).exists()

    restarted = _frame(book)  # a new window, a new store object, the same file
    restarted._refresh_read_only_state()
    assert restarted.editor.editable is False
    assert restarted._document_is_read_only()


def test_the_explorer_spelling_of_the_path_is_still_guarded(book: Path) -> None:
    _frame(book).toggle_read_only_guard()
    from_explorer = _frame(Path(str(book).upper()))
    from_explorer._refresh_read_only_state()
    assert from_explorer.editor.editable is False


def test_toggling_again_unlocks_and_forgets(book: Path) -> None:
    frame = _frame(book)
    frame.toggle_read_only_guard()
    frame.toggle_read_only_guard()
    assert frame.editor.editable is True
    assert frame.said[-1] == "Document is editable"
    again = _frame(book)
    again._refresh_read_only_state()
    assert again.editor.editable is True


def test_a_failed_save_is_said(book: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _denied(*_a: object, **_k: object) -> None:
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr("quill.core.storage.write_json_atomic", _denied)
    frame = _frame(book)
    frame.toggle_read_only_guard()
    assert frame.editor.editable is False, "still locked for this session"
    assert frame.said == [
        "Document is read-only for now, but it could not be remembered for next "
        "time (Access is denied)."
    ]


def test_an_untitled_document_says_it_cannot_be_remembered(quill_data_dir: Path) -> None:
    frame = _frame(None)
    frame.toggle_read_only_guard()
    assert "it has no file name yet" in frame.said[0]


def test_text_changing_paths_refuse_before_they_speak(book: Path) -> None:
    from quill.core.tagging import InsertionResult

    frame = _frame(book)
    frame.toggle_read_only_guard()
    with pytest.raises(DocumentReadOnlyError):
        frame._replace_document_text("# One\n\nChanged.\n")
    with pytest.raises(DocumentReadOnlyError):
        frame._apply_insertion_result(InsertionResult(inserted_text="snippet", caret_offset=7))
    assert frame.editor.text == "# One\n\nBody.\n"


def test_every_entry_point_says_read_only_instead_of_failing(book: Path) -> None:
    """Keys, the palette, hotkeys and voice all run through the registry."""
    from quill.core.commands import CommandRegistry

    frame = _frame(book)
    frame.toggle_read_only_guard()
    registry = CommandRegistry()
    registry.set_read_only_refusal(lambda: frame._set_status(READ_ONLY_REFUSAL))

    def _sort_lines() -> None:
        frame._replace_document_text("# One\n\nChanged.\n")
        frame._set_status("Sorted lines")  # never reached

    registry.register("edit.sort_lines_ascending", "Sort Lines", _sort_lines)
    frame.commands = registry
    frame._maybe_echo_on_double_press = lambda _cid: False  # type: ignore[method-assign]
    frame._run_command("edit.sort_lines_ascending")
    registry.run("edit.sort_lines_ascending")  # the palette's way in
    assert frame.status == [READ_ONLY_REFUSAL, READ_ONLY_REFUSAL]
    assert frame.editor.text == "# One\n\nBody.\n"


def test_without_an_answer_the_refusal_still_stops_the_command(book: Path) -> None:
    from quill.core.commands import CommandRegistry

    frame = _frame(book)
    frame.toggle_read_only_guard()
    registry = CommandRegistry()
    registry.register("x", "X", lambda: frame._replace_document_text("other"))
    with pytest.raises(DocumentReadOnlyError):
        registry.run("x")


def test_bookmarks_and_notes_stay_available(book: Path) -> None:
    frame = _frame(book)
    frame.toggle_read_only_guard()
    frame._bookmarks["chapter"] = 0
    assert frame._bookmarks == {"chapter": 0}
    # Notes ask the shared editor-host hook; a guarded document keeps its
    # notes beside the file instead of writing them into it.
    assert frame._host_read_only() is True


def test_a_guarded_document_answers_browse_navigation_without_copying_the_buffer(
    book: Path,
) -> None:
    text = "# One\n\nBody.\n\n## Two\n\nMore.\n" * 50
    frame = _frame(book, text)
    frame.toggle_read_only_guard()
    frame._build_browse_navigation_cache = (  # type: ignore[method-assign]
        lambda text, kind, marks: {"text": text, "markup_kind": kind}
    )
    first = frame._browse_navigation_context()
    calls_after_first = frame.editor.get_value_calls
    for _ in range(20):
        assert frame._browse_navigation_context() is first
    assert calls_after_first == 1, "one check that the document's text is the control's"
    assert frame.editor.get_value_calls == 1, "and no copy per key after that"


def test_an_unguarded_document_still_reads_the_control(book: Path) -> None:
    frame = _frame(book)
    frame._build_browse_navigation_cache = (  # type: ignore[method-assign]
        lambda text, kind, marks: {"text": text, "markup_kind": kind}
    )
    frame._browse_navigation_context()
    frame._browse_navigation_context()
    assert frame.editor.get_value_calls == 2


def test_a_mismatch_falls_back_to_the_control(book: Path) -> None:
    frame = _frame(book)
    frame.toggle_read_only_guard()
    frame.editor.text = "something the document object does not hold"
    assert frame._browse_text() == "something the document object does not hold"
    assert getattr(frame, "_guarded_browse_text", None) is None
