"""QUILL Lite's File > Import / Convert Document, through the handler the menu binds.

The converter is QUILL's (``quill.io.docconvert``) and is patched where the
mixin imports it; the window, the commit into it, the question before OCR and
every sentence are the shipped code. The task manager runs work at once, so a
test reads top to bottom in the order the person would hear it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import wx

from quill.core.import_convert import CANCELLED_SENTENCE, opened_sentence
from quill.io.docconvert import (
    TIER_OWN_READER,
    TIER_PDF_TEXT,
    TIER_WINDOWS_OCR,
    ConversionOutcome,
    DocConvertError,
)


class _SyncTasks:
    """Runs a submitted task at once, the way the app's pool eventually does."""

    def __init__(self) -> None:
        self.submitted: list[str] = []
        self.held: list[Any] = []
        self.hold = False

    def submit(self, name: str, func: Any, *, on_success: Any, on_failure: Any, **kwargs: Any):
        self.submitted.append(name)

        def run() -> None:
            on_progress = kwargs.get("on_progress")
            try:
                result = func(
                    progress_callback=lambda said: on_progress("op", said) if on_progress else None
                )
            except Exception as exc:  # noqa: BLE001 - as the real pool reports it
                on_failure("op", exc)
                return
            on_success("op", result)

        if self.hold:
            self.held.append(run)
        else:
            run()


@pytest.fixture
def importing(lite_window: Any, fake_wx_dialog: Any, tmp_path: Path):
    """A blank window, a chosen file, and a synchronous task manager."""

    def make(name: str, text: str = "") -> tuple[Any, Path, _SyncTasks]:
        source = tmp_path / name
        source.write_bytes(b"not read: the converter is patched")
        fake_wx_dialog("FileDialog", wx.ID_OK, GetPath=str(source))
        win = lite_window(text)
        win.app.task_manager = _SyncTasks()
        return win, source, win.app.task_manager

    return make


def _convert_returns(monkeypatch: pytest.MonkeyPatch, outcome: ConversionOutcome) -> None:
    monkeypatch.setattr("quill.io.docconvert.convert_document", lambda path, **_kw: outcome)


def test_cancelling_the_file_box_converts_nothing(lite_window: Any, fake_wx_dialog: Any) -> None:
    fake_wx_dialog("FileDialog", wx.ID_CANCEL)
    win = lite_window("")
    win.app.task_manager = tasks = _SyncTasks()
    win.cmd_import_convert()
    assert tasks.submitted == []
    assert win.announcements == []


def test_a_word_file_opens_as_untitled_converted_text_in_this_blank_window(
    importing: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    win, source, tasks = importing("report.docx")
    outcome = ConversionOutcome(
        text="Quarterly report\n\nSales rose.\n",
        tier=TIER_OWN_READER,
        source=source,
        reader="QUILL's own Word reader",
    )
    _convert_returns(monkeypatch, outcome)
    win.cmd_import_convert()
    assert tasks.submitted == ["lite-import"]
    assert win.control.GetValue() == "Quarterly report\n\nSales rose.\n"
    assert win.path is None  # never the .docx: saving must not write over it
    assert win.download_name == "report (converted)"
    assert win.modified is True  # the text exists nowhere else yet
    assert win.announcements == [
        "Converting report.docx",
        "Opened report.docx as editable text, read by QUILL's own Word reader. "
        "Nothing was uploaded.",
    ]


def test_a_window_with_work_in_it_is_left_alone_and_a_new_one_opens(
    importing: Any, monkeypatch: pytest.MonkeyPatch, lite_window: Any
) -> None:
    win, source, _tasks = importing("manual.pdf", text="my notes")
    other = lite_window("")
    monkeypatch.setattr(win.app, "new_window", lambda mode: other)
    outcome = ConversionOutcome(
        text="Page one\fPage two\n", tier=TIER_PDF_TEXT, source=source, page_count=2
    )
    _convert_returns(monkeypatch, outcome)
    win.cmd_import_convert()
    assert win.control.GetValue() == "my notes"
    assert other.control.GetValue() == "Page one\fPage two\n"
    assert other.announcements[-1] == opened_sentence("manual.pdf", outcome)
    assert "2 pages" in other.announcements[-1]


def test_a_warning_is_said_with_the_result(importing: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    win, source, _tasks = importing("long.pdf")
    outcome = ConversionOutcome(
        text="text\n",
        tier=TIER_PDF_TEXT,
        source=source,
        page_count=340,
        warnings=("Only the first 200 of 340 pages were read.",),
    )
    _convert_returns(monkeypatch, outcome)
    win.cmd_import_convert()
    assert win.announcements[-1].endswith(
        "Nothing was uploaded. Only the first 200 of 340 pages were read."
    )


def _scanned(source: Path) -> ConversionOutcome:
    return ConversionOutcome(
        text="", tier=TIER_PDF_TEXT, source=source, page_count=3, offer_local_ocr=True
    )


def test_a_scanned_file_is_cancelled_by_default_and_nothing_opens(
    importing: Any, monkeypatch: pytest.MonkeyPatch, lite_dialogs: Any
) -> None:
    win, source, tasks = importing("scan.pdf")
    _convert_returns(monkeypatch, _scanned(source))
    win.cmd_import_convert()
    question = lite_dialogs.args_for("show_message_box_import")[0]
    assert question.startswith("QUILL Lite could not find readable text in scan.pdf.")
    assert "does not upload anything" in question
    assert tasks.submitted == ["lite-import"]  # no OCR without a yes
    assert win.status_messages[-1] == CANCELLED_SENTENCE
    assert not win.modified


def test_yes_reads_the_scan_with_ocr_on_this_computer(
    importing: Any, monkeypatch: pytest.MonkeyPatch, lite_dialogs: Any
) -> None:
    win, source, tasks = importing("scan.pdf")
    _convert_returns(monkeypatch, _scanned(source))
    lite_dialogs.answer("show_message_box_import", wx.YES)
    read = ConversionOutcome(
        text="<!-- Page 1 -->\n\nRead by Windows.\n",
        tier=TIER_WINDOWS_OCR,
        source=source,
        page_count=3,
    )
    seen: dict[str, Any] = {}

    def on_device(path: Path, **kwargs: Any) -> ConversionOutcome:
        seen.update(kwargs, path=path)
        kwargs["on_progress"](0.5, "Recognizing page 2 of 3")
        return read

    monkeypatch.setattr("quill.io.docconvert_windows.convert_with_on_device_ocr", on_device)
    win.cmd_import_convert()
    assert tasks.submitted == ["lite-import", "lite-import-ocr"]
    assert seen["path"] == source and seen["language"] == "eng"
    assert seen["cancel_requested"]() is False  # the window is still open
    assert "Recognizing page 2 of 3" in win.status_messages
    assert win.control.GetValue() == "<!-- Page 1 -->\n\nRead by Windows.\n"
    assert win.announcements[-2] == "Reading scan.pdf with OCR on this computer"
    assert win.announcements[-1] == (
        "Opened scan.pdf from Windows OCR on this computer. 3 pages. Nothing was uploaded. "
        "Check the text; OCR makes mistakes."
    )


def test_no_opens_the_little_text_there_is(
    importing: Any, monkeypatch: pytest.MonkeyPatch, lite_dialogs: Any
) -> None:
    win, source, tasks = importing("scan.pdf")
    _convert_returns(monkeypatch, _scanned(source))
    lite_dialogs.answer("show_message_box_import", wx.NO)
    win.cmd_import_convert()
    assert tasks.submitted == ["lite-import"]
    assert win.download_name == "scan (converted)"
    assert win.modified is True


def test_a_failure_is_a_box_in_quill_lites_words(
    importing: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    win, _source, _tasks = importing("locked.pdf")

    def refuse(_path: Path, **_kw: Any) -> ConversionOutcome:
        raise DocConvertError("locked.pdf is password-protected. Open it with File > Open instead.")

    monkeypatch.setattr("quill.io.docconvert.convert_document", refuse)
    win.cmd_import_convert()
    caption, message = win.failures[-1]
    assert caption == "Import / Convert Document"
    assert message.startswith("QUILL Lite could not convert locked.pdf.")
    assert "Open it with File > Open instead." in message
    assert win.control.GetValue() == ""


def test_a_copy_with_no_pdf_reader_does_not_send_you_to_quills_menu(
    importing: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.apps.lite_window_pdf import NO_PDF_READER

    win, _source, _tasks = importing("manual.pdf")

    def unavailable(_path: Path, **_kw: Any) -> ConversionOutcome:
        raise DocConvertError(
            "QUILL has no PDF text reader available. Open Help > Download Optional "
            "Components and download it."
        )

    monkeypatch.setattr("quill.io.docconvert.convert_document", unavailable)
    win.cmd_import_convert()
    message = win.failures[-1][1]
    assert NO_PDF_READER in message
    assert "Download Optional Components" not in message


def test_no_ocr_engine_at_all_is_said_not_downloaded(
    importing: Any, monkeypatch: pytest.MonkeyPatch, lite_dialogs: Any
) -> None:
    from quill.io.docconvert_windows import NO_ON_DEVICE_OCR

    win, source, _tasks = importing("scan.pdf")
    _convert_returns(monkeypatch, _scanned(source))
    lite_dialogs.answer("show_message_box_import", wx.YES)

    def no_engine(_path: Path, **_kw: Any) -> ConversionOutcome:
        raise DocConvertError(NO_ON_DEVICE_OCR)  # what the router says with neither engine

    monkeypatch.setattr("quill.io.docconvert_windows.convert_with_on_device_ocr", no_engine)
    win.cmd_import_convert()
    assert NO_ON_DEVICE_OCR in win.failures[-1][1]


def test_closing_the_window_drops_a_conversion_still_running(
    importing: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    win, source, tasks = importing("report.docx")
    tasks.hold = True
    _convert_returns(
        monkeypatch, ConversionOutcome(text="late\n", tier=TIER_OWN_READER, source=source)
    )
    win.cmd_import_convert()
    from quill.apps.lite_window_open import DocumentBackgroundOpenMixin

    # What closing the window calls (the stub window does not carry that mixin).
    DocumentBackgroundOpenMixin.cancel_background_load(win)
    tasks.held.pop()()
    assert win.control.GetValue() == ""
    assert win.announcements == ["Converting report.docx"]
