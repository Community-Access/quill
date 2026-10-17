"""QUILL's File > Open offers OCR for a scanned PDF, as QUILL Lite does (2026-10-15).

QUILL Lite may never be ahead of QUILL: when QUILL Lite gained the scanned-PDF
question at the open, QUILL got the same question, the same words and the same
engines in the same change. Driven headless over a fake host, no engine runs.
Also here: QUILL's Go To gains the Outline kind QUILL Lite has, from the same
shared rows, and the page cell and outline bookmarks read through the shared
helpers.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from quill.core.document import Document
from quill.core.pdf_open import ENGINE_OCR, PdfOpen
from quill.ui.main_frame_go_to import GoToMixin
from quill.ui.main_frame_pdf_open import PdfOpenOcrMixin


class _Wx(SimpleNamespace):
    YES = 5103
    NO = 5104
    OK = 4
    YES_NO = 10
    YES_DEFAULT = 0
    ICON_QUESTION = 1024
    ICON_ERROR = 512

    def __init__(self) -> None:
        super().__init__()
        self.later: list[tuple[Any, tuple[Any, ...]]] = []

    def CallAfter(self, fn: Any, *args: Any) -> None:  # noqa: N802 - wx API shape
        self.later.append((fn, args))


class _Tasks:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.names: list[str] = []

    def submit(self, name, func, *, on_success=None, on_failure=None, on_progress=None, **_kw):
        self.names.append(name)
        token = SimpleNamespace(is_cancelled=lambda: False)
        try:
            value = func(progress_callback=lambda m: on_progress("op", m), cancellation_token=token)
        except BaseException as exc:  # noqa: BLE001 - mirrors the task manager
            on_failure("op", exc)
            return
        on_success("op", value)


class _Host(PdfOpenOcrMixin):
    def __init__(self, answer: int, path: Path, text: str) -> None:
        self._wx = _Wx()
        self._answer = answer
        self.boxes: list[str] = []
        self.spoken: list[str] = []
        self.statuses: list[str] = []
        self.settings = SimpleNamespace(ocr_language="", tesseract_path="")
        self._task_manager = _Tasks(None)
        self.tab = SimpleNamespace(
            document=Document(text=text, path=path, modified=False),
            editor=SimpleNamespace(value=text),
        )
        self.tab.editor.ChangeValue = lambda value: setattr(self.tab.editor, "value", value)
        self._document_tabs = [self.tab]
        self.created: list[Document] = []
        self.titles = 0

    def _show_message_box(self, message: str, _title: str, _style: int) -> int:
        self.boxes.append(message)
        return self._answer

    def _announce(self, message: str) -> None:
        self.spoken.append(message)

    def _set_status(self, message: str) -> None:
        self.statuses.append(message)

    def _find_tab_index(self, path: Path) -> int:
        return 0 if path == self.tab.document.path else -1

    def _create_document_tab(self, document: Document, select: bool = True) -> int:
        self.created.append(document)
        return 1

    def _set_tab_page_text(self, _index: int, _title: str) -> None:
        pass

    def _refresh_title(self) -> None:
        self.titles += 1

    def _docconvert_language(self) -> str:
        return "eng"

    def _docconvert_tesseract_override(self) -> str | None:
        return None


def _scanned(path: Path) -> Document:
    return Document(
        text="(No selectable text was found.)\n",
        path=path,
        source_metadata={"source_kind": "pdf", "engine": "empty", "page_count": 0},
    )


def test_a_text_pdf_is_not_asked_about(tmp_path: Path) -> None:
    path = tmp_path / "report.pdf"
    host = _Host(_Wx.YES, path, "x")
    words = "Plenty of real words on this page, nothing scanned about it at all. " * 2
    loaded = Document(
        text=f"{words}\f{words}",
        path=path,
        source_metadata={"source_kind": "pdf", "engine": "pdfplumber", "page_count": 2},
    )
    host._offer_ocr_for_scanned_pdf(loaded, path, ".pdf")
    host._offer_ocr_for_scanned_pdf(_scanned(path), path, ".txt")
    assert host._wx.later == []


def test_a_scanned_pdf_is_asked_after_the_open_and_no_leaves_it(tmp_path: Path) -> None:
    path = tmp_path / "scan.pdf"
    host = _Host(_Wx.NO, path, "(No selectable text was found.)\n")
    host._offer_ocr_for_scanned_pdf(_scanned(path), path, ".pdf")
    fn, args = host._wx.later[0]  # deferred until the open settles
    fn(*args)
    assert "it looks scanned" in host.boxes[0] and "Nothing is uploaded" in host.boxes[0]
    assert host._task_manager.names == []
    assert host.tab.document.modified is False


def test_yes_reads_the_pages_into_the_pdfs_tab_with_real_pages(monkeypatch, tmp_path) -> None:
    path = tmp_path / "scan.pdf"
    host = _Host(_Wx.YES, path, "(No selectable text was found.)\n")
    seen: dict[str, Any] = {}

    def fake_ocr(source: Path, found: PdfOpen, **kwargs: Any) -> PdfOpen:
        seen.update(kwargs, source=source)
        kwargs["on_progress"](0.5, "Recognizing page 1 of 2...")
        return PdfOpen(text="One\fTwo\n", engine=ENGINE_OCR, page_count=2)

    monkeypatch.setattr("quill.ui.main_frame_pdf_open.ocr_pdf_for_open", fake_ocr)
    host._offer_ocr_for_scanned_pdf(_scanned(path), path, ".pdf")
    fn, args = host._wx.later[0]
    fn(*args)
    assert seen["source"] == path and seen["language"] == "eng"
    assert host._task_manager.names == ["pdf-open-ocr"]
    assert host.spoken[0] == "Scanned; reading the pages with OCR on this computer"
    assert "Recognizing page 1 of 2..." in host.statuses
    assert host.tab.document.text == "One\fTwo\n" and host.tab.editor.value == "One\fTwo\n"
    assert host.tab.document.modified is True  # the only copy of that text
    assert host.spoken[-1] == "OCR done, 2 pages. Check the text; OCR makes mistakes."


def test_an_edited_tab_is_never_overwritten_by_ocr(monkeypatch, tmp_path) -> None:
    path = tmp_path / "scan.pdf"
    host = _Host(_Wx.YES, path, "my own notes")
    host.tab.document.modified = True
    monkeypatch.setattr(
        "quill.ui.main_frame_pdf_open.ocr_pdf_for_open",
        lambda *_a, **_k: PdfOpen(text="OCR\n", engine=ENGINE_OCR, page_count=1),
    )
    host._ask_ocr_for_scanned_pdf(path, PdfOpen(text="", engine="empty"))
    assert host.tab.editor.value == "my own notes"
    assert [document.text for document in host.created] == ["OCR\n"]


def test_no_engine_says_so_in_a_box(monkeypatch, tmp_path) -> None:
    from quill.io.docconvert import DocConvertError

    path = tmp_path / "scan.pdf"
    host = _Host(_Wx.YES, path, "x")

    def no_engine(*_a: Any, **_k: Any) -> PdfOpen:
        raise DocConvertError("No OCR engine is available on this computer.")

    monkeypatch.setattr("quill.ui.main_frame_pdf_open.ocr_pdf_for_open", no_engine)
    host._ask_ocr_for_scanned_pdf(path, PdfOpen(text="", engine="empty"))
    assert "No OCR engine is available" in host.boxes[-1]
    assert host.tab.editor.value == "x"


# -- Go To: the Outline kind QUILL Lite has, in QUILL too ----------------------------- #


class _GoToHost(GoToMixin):
    def __init__(self, metadata: dict[str, Any]) -> None:
        self.document = SimpleNamespace(source_metadata=metadata)
        self.settings = SimpleNamespace(page_estimate_words_per_page=300)


def test_quills_go_to_offers_the_pdf_outline(tmp_path: Path) -> None:
    host = _GoToHost({"pdf_outline": [("Start", 1), ("End", 2)]})
    rows = host._go_to_outline_targets("one\ftwo")
    assert [(row.label, row.position) for row in rows] == [("Start, page 1", 0), ("End, page 2", 4)]
    assert _GoToHost({})._go_to_outline_targets("one\ftwo") == []
    pages = host._go_to_page_targets("one\ftwo")
    assert [(row.label, row.position) for row in pages] == [("1", 0), ("2", 4)]


def test_quills_go_to_says_a_nested_entrys_level_and_lands_on_its_title() -> None:
    host = _GoToHost({
        "pdf_outline": [("Part One", 1), ("Summary", 2)],
        "pdf_outline_levels": [1, 3],
    })
    text = "Part One\fA long line of body text.\nSummary\nShort."
    rows = host._go_to_outline_targets(text)
    assert [(row.label, row.position) for row in rows] == [
        ("Part One, page 1", 0),
        ("Summary, level 3, page 2", text.index("Summary")),
    ]
