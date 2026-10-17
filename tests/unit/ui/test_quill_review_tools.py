"""QUILL's adapters for the shared review commands own no commands of their own.

Inline notes, Toggle Task Done and Export as HTML are QUILL Lite's and QUILL's
from one shared module each. A ``cmd_`` method on QUILL's side would be a second
implementation -- the quiet way the family rule gets broken -- so this asserts
the absence, and checks the two things QUILL does differently: the browse-mode
N key and the Pandoc route for Export as HTML.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.keymap import DEFAULT_ALIASES, DEFAULT_KEYMAP
from quill.core.lite.commands import COMMANDS
from quill.ui import main_frame_inline_notes, main_frame_review


def test_the_adapters_define_no_commands() -> None:
    for cls in (main_frame_inline_notes.InlineNotesMixin, main_frame_review.ReviewToolsMixin):
        own = [name for name in vars(cls) if name.startswith("cmd_")]
        assert own == [], f"{cls.__name__} grew a command of its own: {own}"


def test_both_editors_use_the_same_chords() -> None:
    lite = {row[3]: row[2] for row in COMMANDS if row[3]}
    pairs = {
        "cmd_add_inline_note": "notes.add_inline_note",
        "cmd_next_inline_note": "notes.next_inline_note",
        "cmd_previous_inline_note": "notes.previous_inline_note",
        "cmd_speak_inline_note": "notes.speak_inline_note",
        "cmd_delete_inline_note": "notes.delete_inline_note",
        "cmd_list_inline_notes": "notes.list_inline_notes",
        "cmd_toggle_task_done": "format.toggle_task_done",
        "cmd_export_html": "file.export_html",
    }
    for handler, command_id in pairs.items():
        assert lite[handler] == DEFAULT_KEYMAP[command_id], handler
    assert lite["cmd_snippet_gallery"] == DEFAULT_ALIASES["power.open_snippet_gallery"]
    assert DEFAULT_KEYMAP["quill.quick_nav.inline_note"] == "N"


class _Host(main_frame_inline_notes.InlineNotesMixin):
    """Just enough of MainFrame for the browse key and the Pandoc override."""

    def __init__(self) -> None:
        self.calls: list[bool] = []

    def _go_to_inline_note(self, *, forward: bool) -> None:
        self.calls.append(forward)


def test_browse_mode_n_and_shift_n_walk_notes() -> None:
    host = _Host()
    host._browse_inline_note(reverse=False)
    host._browse_inline_note(reverse=True)
    assert host.calls == [True, False]


class _Exporter(main_frame_review.ReviewToolsMixin):
    settings = type("S", (), {"spellcheck_language": "en_GB"})()


def test_markdown_export_runs_pandoc_standalone(monkeypatch, tmp_path) -> None:
    seen: dict = {}

    class _Status:
        installed = True

    def fake_convert(source: Path, target: Path, **kwargs) -> Path:
        seen["source"] = source.read_text(encoding="utf-8")
        seen.update(kwargs)
        target.write_text("<html></html>", encoding="utf-8")
        return target

    monkeypatch.setattr("quill.core.external_tools.get_external_tool_status", lambda _n: _Status())
    monkeypatch.setattr("quill.io.pandoc.convert_file_with_pandoc", fake_convert)
    target = tmp_path / "plan.html"
    _Exporter()._write_html_export(
        target, "# P\n\nx\n<!-- quill-note: n -->\n", "markdown", "Plan", False
    )
    assert seen["extra_args"][:3] == (
        "--standalone",
        "--metadata=title:Plan",
        "--metadata=lang:en-GB",
    )
    assert "quill-note" not in seen["source"]
    assert target.exists()


def test_without_pandoc_quills_own_renderer_writes_the_page(monkeypatch, tmp_path) -> None:
    class _Status:
        installed = False

    monkeypatch.setattr("quill.core.external_tools.get_external_tool_status", lambda _n: _Status())
    target = tmp_path / "plan.html"
    _Exporter()._write_html_export(target, "- [x] done\n", "markdown", "Plan", False)
    assert '<html lang="en-GB">' in target.read_text(encoding="utf-8")


class _Editor:
    """The slice of QUILL's editor the shared commands touch."""

    def __init__(self, text: str, caret: int) -> None:
        self.text = text
        self.sel = (caret, caret)

    def GetValue(self) -> str:  # noqa: N802 - wx API shape
        return self.text

    def GetSelection(self) -> tuple[int, int]:  # noqa: N802
        return self.sel

    def GetInsertionPoint(self) -> int:  # noqa: N802
        return self.sel[0]

    def GetLastPosition(self) -> int:  # noqa: N802
        return len(self.text)

    def SetInsertionPoint(self, pos: int) -> None:  # noqa: N802
        self.sel = (pos, pos)

    def SetSelection(self, start: int, end: int) -> None:  # noqa: N802
        self.sel = (start, end)

    def WriteText(self, text: str) -> None:  # noqa: N802
        start, end = self.sel
        self.text = self.text[:start] + text + self.text[end:]
        self.sel = (start + len(text), start + len(text))


class _Document:
    path = None
    modified = False

    def set_text(self, value: str) -> None:
        self.modified = True


class _Quill(main_frame_inline_notes.InlineNotesMixin, main_frame_review.ReviewToolsMixin):
    """QUILL's two adapters over a fake frame: QUILL's hooks, the shared commands."""

    def __init__(self, text: str, caret: int, kind: str = "markdown") -> None:
        self.editor = _Editor(text, caret)
        self.document = _Document()
        self.frame = object()
        self.settings = type("S", (), {"inline_notes_in_file": False})()
        self.statuses: list[str] = []
        self._inline_notes: list = []
        self._kind = kind

    def _set_status(self, message: str) -> None:
        self.statuses.append(message)

    def _effective_markup_kind(self) -> str:
        return self._kind

    def _document_is_read_only(self) -> bool:
        return False

    def _active_tab(self):  # noqa: ANN202
        return None


def test_quill_toggles_a_task_through_its_own_editor() -> None:
    quill = _Quill("- [ ] one\n- [x] two\n", 3)
    quill.cmd_toggle_task_done()
    assert quill.editor.text == "- [x] one\n- [x] two\n"
    assert quill.statuses == ["Checked: one. 2 of 2 tasks complete."]
    assert quill.document.modified is True


def test_quill_writes_a_note_into_the_file(monkeypatch) -> None:
    monkeypatch.setattr(
        "quill.ui.inline_note_dialog.show_inline_note_dialog",
        lambda *_a, **_k: ("save", "check this", True),
    )
    quill = _Quill("Para one.\n\nPara two.\n", 2)
    quill.cmd_add_inline_note()
    assert quill.editor.text == "Para one.\n<!-- quill-note: check this -->\n\nPara two.\n"
    assert quill.statuses == ["Inline note written into the file."]
    quill.cmd_next_inline_note()
    assert quill.statuses[-1] == "Inline note 1 of 1: check this"


def test_quill_cues_a_noted_line_with_its_own_sound_and_braille(monkeypatch) -> None:
    """QUILL's hooks: the earcon through CueMixin.cue, "note" to braille through
    the announcement engine, and nothing more while the caret stays on the line."""
    from quill.core.inline_notes import make_inline_note

    text = "First line.\nSecond line has a note.\nThird.\n"
    quill = _Quill(text, 0, kind="plain")
    line = text.index("Second")
    quill._inline_notes = [make_inline_note("Check.", text, line, line)]
    quill.settings.inline_note_line_cue = "sound"
    played: list[str] = []
    brailled: list[str] = []
    quill.cue = played.append
    quill._announcement_engine = type("E", (), {"braille": staticmethod(brailled.append)})()
    monkeypatch.setattr("quill.ui.sound_manager.has_sound_for", lambda _e: True)

    quill.cue_inline_note_line()
    quill.editor.SetInsertionPoint(line + 3)
    quill.cue_inline_note_line()
    quill.editor.SetInsertionPoint(line + 9)
    quill.cue_inline_note_line()
    assert played == ["inline_note_line"]
    assert brailled == ["note"]
    assert quill.statuses == [], "a tone, not a sentence"


def test_quills_caret_handler_asks_for_the_cue() -> None:
    """MainFrame._on_editor_caret_activity is where the cue rides in QUILL."""
    from types import SimpleNamespace

    from quill.ui.main_frame import MainFrame

    asked: list[str] = []
    quiet = lambda *_a: None  # noqa: E731
    frame = SimpleNamespace(
        _schedule_statusbar_refresh=quiet,
        _maybe_announce_indent=quiet,
        _maybe_play_indent_tone=quiet,
        _maybe_announce_format_transition=quiet,
        announce_structure_at_caret=quiet,
        _maybe_announce_braille_movement=quiet,
        cue_inline_note_line=asked.append,
        _maybe_announce_page_crossing=lambda: asked.append("page"),
    )
    MainFrame._on_editor_caret_activity(frame, SimpleNamespace(Skip=quiet))
    assert asked == ["inline_note_line", "page"]
