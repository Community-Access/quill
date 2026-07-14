"""Tests for the Header/Footer Builder's MainFrame wiring (#892): the
per-document store accessor, the edit command, and the print methods
passing the spec through to the printout builder."""

from __future__ import annotations

from pathlib import Path

import pytest
import wx

from quill.core.document import Document
from quill.core.header_footer import HeaderFooterSpec
from quill.core.header_footer_store import key_for
from quill.ui.main_frame import MainFrame


@pytest.fixture(autouse=True)
def _isolated_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


class _Editor:
    def __init__(self, text: str) -> None:
        self._text = text

    def GetValue(self) -> str:
        return self._text


def _build_frame(wx_app, text: str, *, doc_path: Path | None) -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame._wx = wx
    frame.document = Document(path=doc_path)
    frame.editor = _Editor(text)
    frame.frame = wx.Frame(None)
    frame._print_data = wx.PrintData()
    frame._page_setup_data = wx.PageSetupDialogData(frame._print_data)
    frame.status: list[str] = []
    frame._set_status = lambda msg: frame.status.append(msg)
    frame._announce = lambda _msg: None
    return frame


def test_edit_header_footer_requires_a_saved_document(wx_app) -> None:
    frame = _build_frame(wx_app, "text", doc_path=None)
    frame.edit_header_footer()
    assert "Save the document first" in frame.status[-1]
    frame.frame.Destroy()


def test_edit_header_footer_saves_the_returned_spec(wx_app, tmp_path: Path, monkeypatch) -> None:
    saved_spec = HeaderFooterSpec(header_left="{title}", footer_right="{page}")

    class _FakeDialog:
        def __init__(self, parent, spec, announce_cb=None) -> None:
            pass

        def show(self) -> HeaderFooterSpec:
            return saved_spec

        def close(self) -> None:
            pass

    monkeypatch.setattr("quill.ui.header_footer_dialog.HeaderFooterDialog", _FakeDialog)
    doc_path = tmp_path / "report.md"
    frame = _build_frame(wx_app, "text", doc_path=doc_path)
    frame.edit_header_footer()
    assert frame.status[-1] == "Header and footer saved"
    assert frame._current_header_footer_spec() == saved_spec
    frame.frame.Destroy()


def test_edit_header_footer_cancelled_reports_unchanged(
    wx_app, tmp_path: Path, monkeypatch
) -> None:
    class _FakeDialog:
        def __init__(self, parent, spec, announce_cb=None) -> None:
            pass

        def show(self) -> None:
            return None

        def close(self) -> None:
            pass

    monkeypatch.setattr("quill.ui.header_footer_dialog.HeaderFooterDialog", _FakeDialog)
    doc_path = tmp_path / "report.md"
    frame = _build_frame(wx_app, "text", doc_path=doc_path)
    frame.edit_header_footer()
    assert frame.status[-1] == "Header and footer unchanged"
    assert frame._current_header_footer_spec() is None
    frame.frame.Destroy()


def test_current_header_footer_spec_is_none_for_unsaved_document(wx_app) -> None:
    frame = _build_frame(wx_app, "text", doc_path=None)
    assert frame._current_header_footer_spec() is None
    frame.frame.Destroy()


def test_print_document_passes_the_saved_spec_to_the_printout_builder(
    wx_app, tmp_path: Path, monkeypatch
) -> None:
    doc_path = tmp_path / "report.md"
    frame = _build_frame(wx_app, "hello", doc_path=doc_path)
    spec = HeaderFooterSpec(header_left="{title}")
    frame._header_footer_store().set(key_for(doc_path), spec)
    captured: dict[str, object] = {}

    def _fake_build(title, text, pages=None, header_footer=None):
        captured["header_footer"] = header_footer
        return object()

    frame._build_text_printout = _fake_build
    frame._run_print_job = lambda printout: None
    frame.print_document()
    assert captured["header_footer"] == spec
    frame.frame.Destroy()


def test_draw_header_footer_row_positions_left_center_right(wx_app) -> None:
    frame = _build_frame(wx_app, "text", doc_path=None)

    class _FakeDC:
        def __init__(self) -> None:
            self.drawn: list[tuple[str, int, int]] = []

        def GetTextExtent(self, text: str) -> tuple[int, int]:
            return (len(text) * 10, 12)

        def DrawText(self, text: str, x: int, y: int) -> None:
            self.drawn.append((text, x, y))

    dc = _FakeDC()
    frame._draw_header_footer_row(dc, "Left", "Mid", "Right", y=5, width=200)
    assert dc.drawn[0] == ("Left", 50, 5)  # left at the margin
    assert dc.drawn[1][0] == "Mid"
    assert dc.drawn[1][1] == (200 - 30) // 2  # centered: "Mid" is 3 chars * 10
    assert dc.drawn[2][0] == "Right"
    assert dc.drawn[2][1] == 200 - 50 - 50  # right-aligned within the margin
    frame.frame.Destroy()


def test_draw_header_footer_row_skips_empty_zones(wx_app) -> None:
    frame = _build_frame(wx_app, "text", doc_path=None)

    class _FakeDC:
        def __init__(self) -> None:
            self.drawn: list[tuple[str, int, int]] = []

        def GetTextExtent(self, text: str) -> tuple[int, int]:
            return (len(text) * 10, 12)

        def DrawText(self, text: str, x: int, y: int) -> None:
            self.drawn.append((text, x, y))

    dc = _FakeDC()
    frame._draw_header_footer_row(dc, "", "Only Center", "", y=5, width=200)
    assert len(dc.drawn) == 1
    assert dc.drawn[0][0] == "Only Center"
    frame.frame.Destroy()
