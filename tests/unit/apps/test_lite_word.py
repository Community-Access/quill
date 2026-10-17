"""Word documents in QUILL Lite: open as rich text, ask, back up, save as Word.

From 2026-10-17 QUILL Lite edits a ``.docx`` through QUILL's own Word code,
moved into :mod:`quill.core.docx_open` in the same change. These tests drive
QUILL Lite's half with real Word files written by python-docx and read back by
python-docx: open (clean and fidelity-flagged), each of the three answers and
Cancel, edit, save, the one-time backup, the theme colour guard, Save As, and
"Still saving" when Save is pressed during a long Word save.

The window is the shared ``lite_window`` stand-in: the shipped mixins over a
fake control, whose RTF is QUILL's own RTF writer and reader. The real Rich
Edit control's half of the round trip is ``tests/unit/ui/test_word_rich_round_trip.py``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import wx

docx = pytest.importorskip("docx")

from quill.core import docx_open  # noqa: E402 - after the importorskip
from quill.core.lite.open_prepare import PLAIN, RICH, prepare  # noqa: E402


def _clean_docx(path: Path) -> Path:
    document = docx.Document()
    document.add_heading("Quarterly report", level=1)
    document.add_paragraph("Sales grew in every region.")
    document.add_heading("North", level=5)
    document.add_heading("Detail", level=6)
    document.save(str(path))
    return path


def _flagged_docx(path: Path) -> Path:
    document = docx.Document()
    document.add_heading("Team list", level=1)
    table = document.add_table(rows=2, cols=2)
    for (row, col), text in {(0, 0): "Name", (0, 1): "Role", (1, 0): "Ann", (1, 1): "Lead"}.items():
        table.cell(row, col).text = text
    document.add_paragraph("After the table.")
    document.save(str(path))
    return path


def _styles(path: Path) -> list[tuple[str, str]]:
    return [(p.style.name, p.text) for p in docx.Document(str(path)).paragraphs]


@pytest.fixture
def no_boxes(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    shown: list[str] = []

    def record(message: str, *_args: Any, **_kwargs: Any) -> int:
        shown.append(message)
        return wx.NO

    for module in ("lite_window_file", "lite_window_pdf", "lite_window_commands"):
        monkeypatch.setattr(f"quill.apps.{module}.show_message_box", record)
    return shown


@pytest.fixture
def answer(monkeypatch: pytest.MonkeyPatch, fake_wx_dialog: Any) -> Any:
    """Answer the fidelity question: ``answer(row)`` or ``answer(None)`` for Cancel."""

    def install(row: int | None) -> Any:
        cls = fake_wx_dialog(
            "SingleChoiceDialog",
            wx.ID_CANCEL if row is None else wx.ID_OK,
            GetSelection=0 if row is None else row,
            SetSelection=lambda _i: None,
            SetHelpText=lambda _t: None,
        )
        monkeypatch.setattr(
            "quill.apps.lite_window_word.show_modal_dialog",
            lambda dialog, _label: dialog.ShowModal(),
        )
        return cls

    return install


def _open(win: Any, path: Path) -> bool:
    from quill.apps.lite_window_word import open_mode_for

    return bool(win._commit_load(path, prepare(path, open_mode_for(win, path))))


# -- the shared module ------------------------------------------------------------- #


def test_both_editors_ask_the_same_question_in_the_same_words() -> None:
    findings = ["tables (1)", "comments"]
    assert docx_open.fidelity_choices(findings)[0].endswith("(recommended)")
    assert "tables (1), comments" in docx_open.fidelity_choices(findings)[1]
    question = docx_open.fidelity_question("a.docx", findings, app="QUILL Lite")
    assert question.startswith("a.docx contains features QUILL Lite's rich editor cannot carry")
    assert [docx_open.choice_for_selection(i) for i in (-1, 0, 1, 2, 9)] == [
        "text",
        "text",
        "rich",
        "copy",
        "copy",
    ]


def test_quill_and_quill_lite_share_one_implementation() -> None:
    """A second copy is how the rule breaks quietly (CLAUDE.md)."""
    rich_mode = Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame_rich_mode.py"
    source = rich_mode.read_text(encoding="utf-8")
    assert "docx_open.fidelity_question" in source
    assert "docx_open.write_docx_from_rtf" in source
    assert "from quill.io.docx_reader" not in source
    assert "from quill.io.docx_writer" not in source


def test_the_backup_name_is_dated_beside_the_original(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    named = docx_open.backup_path_for(
        tmp_path / "report.docx", now=datetime(2026, 10, 17, 14, 30, 5, tzinfo=UTC)
    )
    assert named == tmp_path / "report.backup-20261017-143005.docx"
    assert not docx_open.needs_backup(flagged=True, backup_done=False, target=named)
    (tmp_path / "report.docx").write_bytes(b"x")
    target = tmp_path / "report.docx"
    assert docx_open.needs_backup(flagged=True, backup_done=False, target=target)
    assert not docx_open.needs_backup(flagged=False, backup_done=False, target=target)
    assert not docx_open.needs_backup(flagged=True, backup_done=True, target=target)


def test_saving_the_same_document_again_adds_no_blank_paragraphs(tmp_path: Path) -> None:
    path = _clean_docx(tmp_path / "again.docx")
    before = _styles(path)
    for _ in range(3):
        # The rich control ends its RTF with a paragraph mark of its own.
        rtf = docx_open.read_docx_as_rtf(path).rstrip().removesuffix("}") + "\\pard\\par}"
        path.write_bytes(docx_open.rtf_to_docx_bytes(rtf))
    assert _styles(path) == before


# -- prepare: the half on the worker ----------------------------------------------- #


def test_a_clean_word_document_prepares_as_rich_text_with_nothing_to_ask(tmp_path: Path) -> None:
    prepared = prepare(_clean_docx(tmp_path / "clean.docx"), RICH)
    assert prepared.mode == RICH and prepared.word
    assert prepared.word_findings == ()
    assert b"Quarterly report" in prepared.rtf
    assert prepared.text == "", "no text read: there is no question to answer with it"


def test_a_flagged_document_names_what_a_save_drops_and_brings_its_text(tmp_path: Path) -> None:
    prepared = prepare(_flagged_docx(tmp_path / "team.docx"), RICH)
    assert prepared.word_findings == ("tables (1)",)
    assert "Ann" in prepared.text


def test_asked_for_as_text_a_word_document_is_text_as_before(tmp_path: Path) -> None:
    prepared = prepare(_clean_docx(tmp_path / "clean.docx"), PLAIN)
    assert prepared.mode == PLAIN and not prepared.word
    assert "Quarterly report" in prepared.text


def test_a_failed_rich_read_falls_back_to_the_text_and_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _clean_docx(tmp_path / "odd.docx")

    def broken(_path: Path) -> str:
        raise ValueError("unexpected part")

    monkeypatch.setattr("quill.core.lite.open_prepare.read_docx_as_rtf", broken)
    prepared = prepare(path, RICH)
    assert prepared.mode == PLAIN and "Quarterly report" in prepared.text
    assert prepared.word_note == "Opened odd.docx as extracted text; the rich load failed."


def test_a_docm_and_a_window_without_rich_text_open_as_text(lite_window, tmp_path: Path) -> None:
    from quill.apps.lite_window_word import open_mode_for

    win = lite_window("")
    assert open_mode_for(win, tmp_path / "a.docx") == RICH
    assert open_mode_for(win, tmp_path / "a.docm") == PLAIN
    assert open_mode_for(win, tmp_path / "a.rtf") == RICH
    win.editor.rtf = False
    assert open_mode_for(win, tmp_path / "a.docx") == PLAIN


# -- open, edit, save, reopen -------------------------------------------------------- #


def test_open_edit_save_and_reopen_in_word(lite_window, no_boxes, tmp_path: Path) -> None:
    path = _clean_docx(tmp_path / "report.docx")
    win = lite_window("")
    assert _open(win, path) is True
    assert win.editor.mode == RICH
    assert win.announcements[-1] == docx_open.OPENED_RICH_SENTENCE
    # Type a new paragraph, as the control would hold it.
    win.editor.rtf_bytes = None
    win.control.ChangeValue(win.control.GetValue().rstrip() + "\n\nAdded in QUILL Lite.\n")
    win.modified = True
    assert win.save() is True
    styles = _styles(path)
    assert ("Heading 1", "Quarterly report") in styles
    assert ("Heading 5", "North") in styles and ("Heading 6", "Detail") in styles
    assert styles[-1] == ("Normal", "Added in QUILL Lite.")
    assert win.announcements[-1] == "Saved report.docx"
    assert no_boxes == [], "Save on an opened Word document writes it, no Save As"
    assert list(tmp_path.glob("report.backup-*")) == [], "a clean file is not backed up"


def test_the_theme_colour_is_off_the_document_while_it_is_read_for_saving(
    lite_window, no_boxes, tmp_path: Path
) -> None:
    path = _clean_docx(tmp_path / "dark.docx")
    win = lite_window("")
    _open(win, path)
    win.colour_calls.clear()
    assert win.save() is True
    assert win.colour_calls[:2] == [None, "restored"], "stripped, then put back"


def test_a_failed_word_save_still_puts_the_theme_colour_back(
    lite_window, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.ui.richedit_rtf_surface import RichEditRtfError

    path = _clean_docx(tmp_path / "locked.docx")
    win = lite_window("")
    _open(win, path)
    win.colour_calls.clear()

    def refuse() -> bytes:
        raise RichEditRtfError("the control would not give up its text")

    monkeypatch.setattr(win.editor, "get_rtf", refuse)
    assert win.save() is False
    assert win.colour_calls == [None, "restored"]
    assert win.failures and win.failures[-1][0] == "Save failed"


@pytest.mark.parametrize("row", [None, 0])
def test_cancel_or_the_first_answer_opens_the_text_and_never_writes_it_back(
    lite_window, answer, no_boxes, tmp_path: Path, row: int | None
) -> None:
    path = _flagged_docx(tmp_path / "team.docx")
    original = path.read_bytes()
    answer(row)
    win = lite_window("")
    assert _open(win, path) is True
    assert win.editor.mode == PLAIN
    assert "Ann" in win.control.GetValue()
    offered: list[bool] = []
    win.cmd_save_as = lambda: offered.append(True) or False
    assert win.save() is False and offered == [True]
    assert path.read_bytes() == original


def test_editing_a_flagged_document_backs_the_original_up_once(
    lite_window, answer, no_boxes, tmp_path: Path
) -> None:
    path = _flagged_docx(tmp_path / "team.docx")
    original = path.read_bytes()
    dialog = answer(1)
    win = lite_window("")
    assert _open(win, path) is True
    (args, _kwargs) = dialog.constructed[-1]
    assert "QUILL Lite's rich editor cannot carry: tables (1)" in args[1]
    assert win.editor.mode == RICH and win.word_flagged
    assert win.save() is True
    backups = list(tmp_path.glob("team.backup-*.docx"))
    assert len(backups) == 1 and backups[0].read_bytes() == original
    said = [line for line in win.announcements if line.startswith("Backed up the original to ")]
    assert len(said) == 1 and "team.backup-" in said[0]
    assert win.save() is True
    assert len(list(tmp_path.glob("team.backup-*.docx"))) == 1, "once, not every save"
    # The table survives as a real table, header row first.
    tables = docx.Document(str(path)).tables
    rows = [[cell.text for cell in row.cells] for row in tables[0].rows]
    assert rows == [["Name", "Role"], ["Ann", "Lead"]]


def test_editing_a_copy_leaves_the_original_untouched(
    lite_window, answer, no_boxes, tmp_path: Path
) -> None:
    path = _flagged_docx(tmp_path / "team.docx")
    original = path.read_bytes()
    answer(2)
    win = lite_window("")
    assert _open(win, path) is True
    assert win.path != path and win.path.name.startswith("team.backup-")
    assert win.announcements[-1] == (
        f"{docx_open.OPENED_RICH_SENTENCE} Editing a copy, {win.path.name}. "
        "The original is untouched."
    )
    win.modified = True
    assert win.save() is True
    assert path.read_bytes() == original


# -- Save As -------------------------------------------------------------------------- #


def test_save_as_opens_on_the_word_row_for_a_word_document(
    lite_window, fake_wx_dialog, no_boxes, tmp_path: Path
) -> None:
    from quill.core.lite.filetypes import SAVE_FILTER_WORD, SAVE_WILDCARD_RICH

    path = _clean_docx(tmp_path / "report.docx")
    win = lite_window("")
    _open(win, path)
    picked: list[int] = []
    cls = fake_wx_dialog(
        "FileDialog", wx.ID_OK, GetPath=str(tmp_path / "copy.docx"), SetFilterIndex=picked.append
    )
    assert win.cmd_save_as() is True
    assert picked == [SAVE_FILTER_WORD]
    assert SAVE_WILDCARD_RICH.split("|")[SAVE_FILTER_WORD * 2] == "Word document (*.docx)"
    assert cls.constructed[-1][1]["defaultFile"] == "report.docx"
    assert ("Heading 1", "Quarterly report") in _styles(tmp_path / "copy.docx")


# -- Still saving ------------------------------------------------------------------- #


class _HeldTasks:
    """A task manager that holds the work until the test lets it finish."""

    def __init__(self) -> None:
        self.submitted: list[dict[str, Any]] = []

    def submit(self, name: str, func: Any, **kwargs: Any) -> None:
        self.submitted.append({"name": name, "func": func, **kwargs})

    def finish(self, index: int = 0) -> None:
        task = self.submitted[index]
        task["on_success"]("op", task["func"]())


def test_save_pressed_again_during_a_long_word_save_says_still_saving(
    lite_window, no_boxes, tmp_path: Path
) -> None:
    path = _clean_docx(tmp_path / "long.docx")
    win = lite_window("")
    _open(win, path)
    win.app.task_manager = tasks = _HeldTasks()
    win.modified = True
    win.cmd_save()
    assert len(tasks.submitted) == 1 and win.status_messages[-1] == "Saving long.docx"
    win.cmd_save()
    assert win.announcements[-1] == "Still saving long.docx"
    assert win.save() is False, "the close prompt's save waits too"
    assert win.save_quietly() == "Still saving long.docx"
    assert len(tasks.submitted) == 1, "no second save started"
    tasks.finish()
    assert win.announcements[-1] == "Saved long.docx"
    assert win.modified is False
    assert ("Heading 1", "Quarterly report") in _styles(path)
    win.cmd_save()
    assert len(tasks.submitted) == 2, "finished, so Save works again"


def test_typing_during_a_background_save_keeps_the_window_unsaved(
    lite_window, no_boxes, tmp_path: Path
) -> None:
    path = _clean_docx(tmp_path / "typed.docx")
    win = lite_window("")
    _open(win, path)
    win.app.task_manager = tasks = _HeldTasks()
    win.modified = True
    win.cmd_save()
    win.control.ChangeValue(win.control.GetValue() + "more")
    tasks.finish()
    assert win.modified is True, "what was typed during the save is not in the file"


def test_a_failed_background_save_is_reported_and_frees_save(lite_window, tmp_path: Path) -> None:
    path = _clean_docx(tmp_path / "gone.docx")
    win = lite_window("")
    _open(win, path)
    win.app.task_manager = tasks = _HeldTasks()
    win.cmd_save()
    tasks.submitted[0]["on_failure"]("op", OSError("disk full"))
    assert win.failures[-1] == ("Save failed", "Could not save gone.docx.\n\ndisk full")
    assert win._word_save_busy == ""


def test_a_changed_word_document_reloads_as_it_is_held(lite_window, tmp_path: Path) -> None:
    """Reload from disk keeps a Word document rich (lite_window_watch)."""
    from quill.apps.lite_window_watch import DocumentDiskWatchMixin
    from quill.core.external_change import FileSnapshot

    path = _clean_docx(tmp_path / "shared.docx")
    win = lite_window("")
    win.__class__ = type("Watched", (DocumentDiskWatchMixin, type(win)), {})
    _open(win, path)
    other = docx.Document(str(path))
    other.add_paragraph("Added by a colleague.")
    other.save(str(path))
    win._reload_from_disk(FileSnapshot.of(path))
    assert win.editor.mode == RICH
    assert "Added by a colleague." in win.control.GetValue()
