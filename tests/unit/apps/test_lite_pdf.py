"""QUILL Lite opens PDFs as text, and never writes one back (2026-10-15).

The reading itself is QUILL's and is tested in tests/unit/core/test_pdf_open.py.
What is tested here is QUILL Lite's window doing the right thing with each
thing the reader can find, on the real mixins over the wx-free stand-in:

* a PDF always opens on the worker, with a password or an OCR read when the
  commit asks for one -- and the password never lands on the window;
* locked asks (cancel first, because cancel is the branch people forget),
  damaged says why and opens nothing, scanned offers OCR (No opens what text
  there is, Yes reads the pages), text opens with one sentence;
* the OCR result is marked changed, because it exists nowhere else;
* pages: Go To offers Page and Outline only for a document that has them, and
  the Page cell reads "Page 2 of 3";
* Save never writes to the .pdf: it says why and goes to Save As with a .txt
  proposed, and Save As refuses a .pdf name.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import wx

from quill.apps.lite_status_cells import CELLS, SHOWN_ONLY_WITH_TEXT, page_cell_text
from quill.apps.lite_window_open import DocumentBackgroundOpenMixin
from quill.core.lite import open_prepare
from quill.core.lite.filetypes import OPEN_WILDCARD
from quill.core.lite.open_prepare import PLAIN, PreparedDocument
from quill.core.pdf_open import ENGINE_OCR, PdfOpen
from tests.wx_session import patch_call_after

_WORDS = "A page of real words, long enough that nobody would call it scanned at all. "
_TEXT = f"Page one. {_WORDS}\fPage two. {_WORDS}\fPage three. {_WORDS}\n"


def _found(**overrides: Any) -> PdfOpen:
    values: dict[str, Any] = {
        "text": _TEXT,
        "engine": "pdfplumber",
        "page_count": 3,
        "page_scores": (80, 80, 80),
        "outline": (("Start", 1), ("Middle", 2)),
    }
    values.update(overrides)
    return PdfOpen(**values)


@pytest.fixture
def later(monkeypatch) -> list[tuple[Any, tuple[Any, ...], dict[str, Any]]]:
    """``wx.CallAfter`` recorded, not run: what the window queued, in order."""
    queued: list[tuple[Any, tuple[Any, ...], dict[str, Any]]] = []
    patch_call_after(monkeypatch, lambda fn, *a, **k: queued.append((fn, a, k)))
    return queued


def _pdf_window(lite_window, tmp_path: Path) -> Any:
    window = lite_window("")
    window.begin_background_load = lambda path, **kwargs: window.reloads.append((path, kwargs))
    window.reloads = []
    return window


def _commit(window: Any, path: Path, found: PdfOpen) -> bool:
    return window._commit_load(path, PreparedDocument(mode=PLAIN, text=found.text, pdf=found))


# -- the open --------------------------------------------------------------------- #


def test_the_open_dialog_offers_pdfs() -> None:
    assert "*.pdf" in OPEN_WILDCARD.split("|")[1]
    assert "PDF documents, opened as text (*.pdf)|*.pdf" in OPEN_WILDCARD


def test_every_pdf_is_read_on_the_worker(tmp_path: Path) -> None:
    tiny = tmp_path / "tiny.pdf"
    tiny.write_bytes(b"%PDF-1.4")
    assert open_prepare.prepare_in_background(tiny) is True


def test_prepare_reads_a_pdf_through_the_shared_reader(monkeypatch, tmp_path: Path) -> None:
    seen: list[str | None] = []

    def read(path: Path, *, password: str | None = None) -> PdfOpen:
        seen.append(password)
        return _found()

    monkeypatch.setattr(open_prepare, "read_pdf_for_open", read)
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    prepared = open_prepare.prepare(pdf, open_prepare.PLAIN, password="pw")
    assert prepared.mode == PLAIN and prepared.text == _TEXT and prepared.pdf is not None
    assert seen == ["pw"]
    with pytest.raises(OSError):
        open_prepare.prepare(tmp_path / "gone.pdf", open_prepare.PLAIN)


def test_load_sends_a_pdf_to_the_background(lite_window, tmp_path: Path) -> None:
    window = _pdf_window(lite_window, tmp_path)
    assert window.load(tmp_path / "report.pdf") is True
    assert window.reloads == [(tmp_path / "report.pdf", {})]


def test_a_text_pdf_opens_with_its_outline_and_one_sentence(lite_window, tmp_path) -> None:
    window = _pdf_window(lite_window, tmp_path)
    pdf = tmp_path / "report.pdf"
    assert _commit(window, pdf, _found()) is True
    assert window.control.GetValue() == _TEXT
    assert window.path == pdf and window.modified is False
    assert window.pdf_outline == (("Start", 1), ("Middle", 2))
    assert window.announcements[-1] == (
        "Opened as text, 3 pages, 2 outline entries in Go To. "
        "Saving makes a new file; the PDF is not changed."
    )


def test_a_text_file_after_a_pdf_forgets_the_pdfs_outline(lite_window, tmp_path) -> None:
    window = _pdf_window(lite_window, tmp_path)
    _commit(window, tmp_path / "report.pdf", _found())
    notes = tmp_path / "notes.txt"
    notes.write_text("plain\n", encoding="utf-8")
    assert window.load(notes) is True
    assert window.pdf_outline == ()


# -- locked ----------------------------------------------------------------------- #


def test_a_locked_pdf_cancelled_opens_nothing_and_says_so(
    lite_window, lite_dialogs, later, tmp_path
) -> None:
    window = _pdf_window(lite_window, tmp_path)
    locked = _found(text="(locked)\n", engine="encrypted", page_count=0, outline=())
    assert _commit(window, tmp_path / "locked.pdf", locked) is False
    assert window.path is None and window.control.GetValue() == ""
    assert lite_dialogs.opened[-1][0] == "ask_pdf_password"
    assert lite_dialogs.opened[-1][2] == {"incorrect": False}
    assert window.announcements[-1] == "Open cancelled. locked.pdf is password-protected."
    assert later == []


def test_a_password_goes_to_one_more_read_and_nowhere_else(
    lite_window, lite_dialogs, later, tmp_path
) -> None:
    window = _pdf_window(lite_window, tmp_path)
    lite_dialogs.answer("ask_pdf_password", "s3cret")
    rejected = _found(text="(no)\n", engine="encrypted", password_rejected=True, outline=())
    assert _commit(window, tmp_path / "locked.pdf", rejected) is False
    assert lite_dialogs.opened[-1][2] == {"incorrect": True}  # says the last one was wrong
    (fn, args, kwargs) = later[-1]
    assert args == (tmp_path / "locked.pdf",) and kwargs == {"password": "s3cret"}
    fn(*args, **kwargs)
    assert window.reloads[-1][1] == {"password": "s3cret"}
    # Not kept on the window under any name.
    assert all(value != "s3cret" for value in vars(window).values())


# -- damaged ------------------------------------------------------------------------ #


def test_a_damaged_pdf_says_why_and_opens_nothing(lite_window, tmp_path) -> None:
    window = _pdf_window(lite_window, tmp_path)
    damaged = _found(text="(bad.pdf could not be parsed -- it is damaged.)\n", engine="damaged")
    assert _commit(window, tmp_path / "bad.pdf", damaged) is False
    caption, message = window.failures[-1]
    assert caption == "Open failed"
    assert message == "Could not open bad.pdf.\n\nbad.pdf could not be parsed -- it is damaged."
    assert window.path is None


def test_a_copy_without_a_reader_does_not_send_you_to_quills_menu(lite_window, tmp_path) -> None:
    window = _pdf_window(lite_window, tmp_path)
    missing = _found(text="(Open Help > Download Optional Components.)\n", engine="unavailable")
    assert _commit(window, tmp_path / "a.pdf", missing) is False
    message = window.failures[-1][1]
    assert "Download Optional Components" not in message
    assert "This copy of QUILL Lite has no PDF reader" in message


# -- scanned -------------------------------------------------------------------------- #


def test_a_scanned_pdf_declined_opens_nothing_when_it_has_no_text(
    lite_window, lite_dialogs, later, tmp_path
) -> None:
    window = _pdf_window(lite_window, tmp_path)
    scanned = _found(text="(No selectable text.)\n", engine="empty", page_count=0, outline=())
    assert _commit(window, tmp_path / "scan.pdf", scanned) is False
    question = lite_dialogs.opened[-1][1][0]
    assert "it looks scanned" in question and "Nothing is uploaded" in question
    assert window.announcements[-1] == "Nothing opened. scan.pdf has no text to show."
    assert window.path is None and later == []


def test_a_thin_pdf_declined_opens_the_little_text_there_is(
    lite_window, lite_dialogs, later, tmp_path
) -> None:
    window = _pdf_window(lite_window, tmp_path)
    thin = _found(text="Cover\f\f\f\n", outline=())
    assert _commit(window, tmp_path / "thin.pdf", thin) is True
    assert window.control.GetValue() == "Cover\f\f\f\n"


def test_yes_reads_the_pages_with_ocr_in_the_background(
    lite_window, lite_dialogs, later, tmp_path
) -> None:
    window = _pdf_window(lite_window, tmp_path)
    lite_dialogs.answer("show_message_box_pdf", wx.YES)
    scanned = _found(text="(No selectable text.)\n", engine="empty", page_count=2, outline=())
    assert _commit(window, tmp_path / "scan.pdf", scanned) is False
    fn, args, kwargs = later[-1]
    assert args == (tmp_path / "scan.pdf",) and kwargs == {"ocr_of": scanned}


def test_the_ocr_result_opens_with_pages_and_is_marked_changed(lite_window, tmp_path) -> None:
    window = _pdf_window(lite_window, tmp_path)
    read = _found(text="First\fSecond\n", engine=ENGINE_OCR, page_count=2, outline=())
    assert _commit(window, tmp_path / "scan.pdf", read) is True
    assert window.control.GetValue() == "First\fSecond\n"
    assert window.modified is True  # the only copy: closing must ask
    assert window.announcements[-1] == ("OCR done, 2 pages. Check the text; OCR makes mistakes.")


# -- the background half: password and OCR are the same open ---------------------- #


class _Tasks:
    def __init__(self) -> None:
        self.submitted: list[dict[str, Any]] = []

    def submit(self, name: str, func: Any, **kwargs: Any) -> None:
        self.submitted.append({"name": name, "func": func, **kwargs})


class _Frame(DocumentBackgroundOpenMixin):
    def __init__(self) -> None:
        self.app = SimpleNamespace(shutting_down=False, task_manager=_Tasks())
        self.control = SimpleNamespace(SetEditable=lambda _on: None, SetFocus=lambda: None)
        self.number = 1
        self.path = None
        self.modified = False
        self.status: list[str] = []
        self.spoken: list[str] = []

    def SetTitle(self, _title: str) -> None:  # noqa: N802 - wx API shape
        pass

    def _set_status_message(self, message: str) -> None:
        self.status.append(message)

    def _announce(self, message: str) -> None:
        self.spoken.append(message)

    def _check_mode_available(self, mode: str) -> None:
        pass

    def IsBeingDeleted(self) -> bool:  # noqa: N802 - wx API shape
        return False


def test_a_password_read_passes_the_password_to_prepare_only(monkeypatch, tmp_path) -> None:
    seen: list[Any] = []
    monkeypatch.setattr(
        "quill.apps.lite_window_open.prepare_document",
        lambda path, mode, *, password=None: seen.append(password) or "prepared",
    )
    frame = _Frame()
    frame.begin_background_load(tmp_path / "locked.pdf", password="pw")
    assert frame.app.task_manager.submitted[0]["func"]() == "prepared"
    assert seen == ["pw"]
    assert not any("pw" == value for value in vars(frame).values())


def test_an_ocr_read_says_so_and_reports_pages_on_the_status_bar_only(
    monkeypatch, tmp_path
) -> None:
    calls: list[dict[str, Any]] = []

    def fake_ocr(path: Path, found: PdfOpen, **kwargs: Any) -> PdfOpen:
        kwargs["on_progress"](0.5, "Recognizing page 1 of 2...")
        calls.append(kwargs)
        return _found(text="One\fTwo\n", engine=ENGINE_OCR, page_count=2)

    monkeypatch.setattr("quill.core.pdf_open.ocr_pdf_for_open", fake_ocr)
    frame = _Frame()
    scanned = _found(text="", engine="empty", page_count=2)
    frame.begin_background_load(tmp_path / "scan.pdf", ocr_of=scanned)
    assert frame.spoken == ["Scanned; reading 2 pages with OCR on this computer"]
    task = frame.app.task_manager.submitted[0]
    progress: list[str] = []
    prepared = task["func"](progress_callback=progress.append)
    assert progress == ["Recognizing page 1 of 2..."]
    assert prepared.text == "One\fTwo\n" and prepared.pdf.engine == ENGINE_OCR
    assert calls[0]["cancel_requested"]() is False  # the window is open
    task["on_progress"]("op", "Recognizing page 2 of 2...")
    assert frame.status[-1] == "Recognizing page 2 of 2..."
    assert frame.spoken == ["Scanned; reading 2 pages with OCR on this computer"]


# -- pages -------------------------------------------------------------------------- #


def test_go_to_offers_page_and_outline_for_a_pdf(lite_window, lite_dialogs, tmp_path) -> None:
    window = _pdf_window(lite_window, tmp_path)
    _commit(window, tmp_path / "report.pdf", _found())
    window.cmd_goto_line()
    kinds = lite_dialogs.opened[-1][2]["kinds"]
    assert list(kinds) == ["Page", "Bookmark", "Heading", "Outline"]
    assert [target.label for target in kinds["Page"]] == ["1", "2", "3"]
    assert [target.label for target in kinds["Outline"]] == ["Start, page 1", "Middle, page 2"]
    assert kinds["Outline"][1].position == _TEXT.index("Page two.")
    assert lite_dialogs.opened[-1][2]["initial_kind"] is None


def test_enter_on_the_page_cell_opens_go_to_on_page(lite_window, lite_dialogs, tmp_path) -> None:
    window = _pdf_window(lite_window, tmp_path)
    _commit(window, tmp_path / "report.pdf", _found())
    window.go_to_a_page()
    assert lite_dialogs.opened[-1][2]["initial_kind"] == "Page"


def test_the_page_cell_reads_page_n_of_m_only_when_there_are_pages() -> None:
    assert page_cell_text(_TEXT, 0) == "Page 1 of 3"
    assert page_cell_text(_TEXT, _TEXT.index("Page two.")) == "Page 2 of 3"
    assert page_cell_text("no pages at all", 3) == ""
    keys = [cell.key for cell in CELLS]
    assert keys.index("page") == keys.index("position") + 1
    assert SHOWN_ONLY_WITH_TEXT == {"page"}


# -- Save never writes to the PDF ------------------------------------------------------ #


def test_save_on_a_pdf_says_why_and_goes_to_save_as(lite_window, lite_dialogs, tmp_path) -> None:
    window = _pdf_window(lite_window, tmp_path)
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF-1.4 original")
    _commit(window, pdf, _found())
    went: list[bool] = []
    window.cmd_save_as = lambda: went.append(True) or False
    window.cmd_save()
    assert went == [True]
    assert pdf.read_bytes() == b"%PDF-1.4 original"  # never written
    said = lite_dialogs.opened[-1][1][0]
    assert said.startswith("report.pdf was opened as extracted text. QUILL Lite cannot write .pdf")
    assert said.endswith("(text, Markdown or rich text).")


def test_save_as_proposes_a_text_file_named_after_the_pdf(lite_window, tmp_path) -> None:
    window = _pdf_window(lite_window, tmp_path)
    _commit(window, tmp_path / "report.pdf", _found())
    assert window.proposed_name_for_mode() == "report.txt"


def test_save_as_refuses_a_pdf_name(lite_window, lite_dialogs, tmp_path) -> None:
    window = lite_window("Some text\n")
    target = tmp_path / "copy.pdf"
    assert window.save(target) is False
    assert not target.exists()
    assert lite_dialogs.opened[-1][1][0].startswith("QUILL Lite cannot save to .pdf.")


def test_save_as_to_text_writes_the_pdfs_text(lite_window, tmp_path) -> None:
    window = _pdf_window(lite_window, tmp_path)
    _commit(window, tmp_path / "report.pdf", _found())
    target = tmp_path / "report.txt"
    assert window.save(target) is True
    assert target.read_text(encoding="utf-8").startswith("Page one.")
    assert window.path == target


def test_reopen_with_encoding_is_not_offered_for_a_pdf(lite_window, tmp_path) -> None:
    window = _pdf_window(lite_window, tmp_path)
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    _commit(window, pdf, _found())
    assert window._can_reopen_with_encoding() is False


# -- item 28: nesting kept for Go To, doubtful pages said -------------------------- #


def test_the_outline_levels_ride_with_the_outline(lite_window, tmp_path) -> None:
    window = _pdf_window(lite_window, tmp_path)
    _commit(window, tmp_path / "report.pdf", _found(outline_levels=(1, 2)))
    assert window.pdf_outline_levels == (1, 2)
    notes = tmp_path / "notes.txt"
    notes.write_text("plain\n", encoding="utf-8")
    assert window.load(notes) is True
    assert window.pdf_outline_levels == ()


def test_a_page_that_may_read_poorly_is_named_when_the_pdf_opens(lite_window, tmp_path) -> None:
    window = _pdf_window(lite_window, tmp_path)
    found = _found(
        page_scores=(80, 12, 80),
        page_engines=("pdfplumber", "pypdf", "pdfplumber"),
    )
    _commit(window, tmp_path / "report.pdf", found)
    assert window.announcements[-1] == (
        "Opened as text, 3 pages, 2 outline entries in Go To. Page 2 may read poorly. "
        "Saving makes a new file; the PDF is not changed."
    )
