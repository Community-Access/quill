"""Save As in QUILL Lite: the typed name decides, and a Word name needs rich text.

QUILL Lite writes text, Markdown and rich text, and the name somebody types
decides which (2026-10-16, item 41). Until that date ``minutes.docx`` got the
window's text written under a Word name -- a file Word will not open -- and it
was then refused. Since 2026-10-17 a **rich** window writes a real Word
document through QUILL's writer (quill.core.docx_open); a plain text window is
still refused, and so is every other Word extension.

Every case runs ``cmd_save_as`` with a stand-in Save As window and checks the
file on disk in its own format.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import wx

TEXT = "# Minutes\n\nWe agreed the budget.\n"


@pytest.fixture
def boxes(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    shown: list[tuple[str, str]] = []

    def record(message: str, caption: str, *_args: Any, **_kwargs: Any) -> int:
        shown.append((caption, message))
        return wx.NO

    monkeypatch.setattr("quill.apps.lite_window_file.show_message_box", record)
    monkeypatch.setattr("quill.apps.lite_window_commands.show_message_box", record)
    monkeypatch.setattr("quill.apps.lite_window_pdf.show_message_box", record)
    return shown


def _save_as(win: Any, fake_wx_dialog: Any, target: Path, answer: int = wx.ID_OK) -> bool:
    fake_wx_dialog("FileDialog", answer, GetPath=str(target), SetFilterIndex=lambda _i: None)
    return bool(win.cmd_save_as())


@pytest.mark.parametrize("name", ["minutes.docx", "MINUTES.DOCX", "minutes.docm", "letter.dotx"])
def test_a_word_name_is_refused_and_nothing_is_written(
    lite_window, fake_wx_dialog, boxes, tmp_path, name
) -> None:
    win = lite_window(TEXT)
    assert _save_as(win, fake_wx_dialog, tmp_path / name) is False
    assert not (tmp_path / name).exists()
    caption, message = boxes[-1]
    assert caption == "Format not supported"
    assert f"so {name} was not written" in message and "Rich Text (.rtf)" in message
    if name.lower().endswith(".docx"):
        assert "Switch Document Mode" in message, "says how to make it saveable"
    assert win.path is None, "the window still holds an unnamed document"


def test_a_rich_document_saves_a_real_word_document_without_flattening(
    lite_window, fake_wx_dialog, boxes, tmp_path
) -> None:
    docx = pytest.importorskip("docx")
    win = lite_window("# Minutes\n\nformatted words", mode="rich")
    assert _save_as(win, fake_wx_dialog, tmp_path / "minutes.docx") is True
    assert boxes == [], "no 'removes all formatting' question: nothing is flattened"
    reopened = docx.Document(str(tmp_path / "minutes.docx"))
    written = [(p.style.name, p.text) for p in reopened.paragraphs if p.text]
    assert written == [("Heading 1", "Minutes"), ("Normal", "formatted words")]
    assert win.path == tmp_path / "minutes.docx"


@pytest.mark.parametrize("name", ["minutes.docm", "letter.dotx"])
def test_a_rich_document_is_still_refused_other_word_names(
    lite_window, fake_wx_dialog, boxes, tmp_path, name
) -> None:
    win = lite_window("formatted words", mode="rich")
    assert _save_as(win, fake_wx_dialog, tmp_path / name) is False
    assert not (tmp_path / name).exists()
    assert [caption for caption, _m in boxes] == ["Format not supported"]


@pytest.mark.parametrize("name", ["notes.txt", "notes.md", "NOTES.TXT", "page.html", "notes.log"])
def test_text_names_are_written_as_the_text_stands(
    lite_window, fake_wx_dialog, boxes, tmp_path, name
) -> None:
    win = lite_window(TEXT)
    assert _save_as(win, fake_wx_dialog, tmp_path / name) is True
    assert (tmp_path / name).read_text(encoding="utf-8").replace("\r\n", "\n") == TEXT
    assert win.path == tmp_path / name


def test_an_rtf_name_writes_rich_text(lite_window, fake_wx_dialog, boxes, tmp_path) -> None:
    win = lite_window(TEXT, mode="rich")
    assert _save_as(win, fake_wx_dialog, tmp_path / "notes.RTF") is True
    assert (tmp_path / "notes.RTF").exists()


def test_cancel_writes_nothing(lite_window, fake_wx_dialog, boxes, tmp_path) -> None:
    win = lite_window(TEXT)
    assert _save_as(win, fake_wx_dialog, tmp_path / "minutes.docx", answer=wx.ID_CANCEL) is False
    assert list(tmp_path.glob("minutes*")) == []
    assert boxes == []


@pytest.mark.parametrize("name", ["budget.xlsx", "minutes.pdf", "old.doc"])
def test_formats_only_quill_reads_are_refused(
    lite_window, fake_wx_dialog, boxes, tmp_path, name
) -> None:
    win = lite_window(TEXT)
    assert _save_as(win, fake_wx_dialog, tmp_path / name) is False
    assert not (tmp_path / name).exists()
    assert boxes and boxes[-1][0] == "Format not supported"


def test_save_on_a_window_that_holds_a_word_name_is_refused_too(
    lite_window, boxes, tmp_path
) -> None:
    win = lite_window(TEXT)
    win.path = tmp_path / "opened.docx"
    # An opened Word file is read-only like an opened PDF: Save offers Save As
    # (lite_window_file.save -> refuse_save_over_source) instead of writing.
    offered: list[bool] = []
    win.cmd_save_as = lambda: offered.append(True) or False
    assert win.save() is False
    assert offered == [True]
    assert not (tmp_path / "opened.docx").exists()


def test_the_clipboard_collector_will_not_write_a_word_name(lite_window, tmp_path) -> None:
    win = lite_window(TEXT)
    win.path = tmp_path / "collected.docx"
    reason = win.save_quietly()
    assert reason and "saves Word documents from rich text" in reason
    assert not (tmp_path / "collected.docx").exists()
