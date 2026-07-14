"""Tests for ImageAltMixin (#899): Insert Image and Describe Image at Cursor."""

from __future__ import annotations

from quill.ui.main_frame_image_alt import ImageAltMixin


class _Editor:
    def __init__(self, text: str, pos: int) -> None:
        self._text = text
        self._pos = pos

    def GetValue(self) -> str:
        return self._text

    def GetInsertionPoint(self) -> int:
        return self._pos

    def SetInsertionPoint(self, pos: int) -> None:
        self._pos = pos

    def SetSelection(self, start: int, end: int) -> None:
        pass


class _Document:
    def __init__(self) -> None:
        self.text = ""

    def set_text(self, text: str) -> None:
        self.text = text


class _Host(ImageAltMixin):
    def __init__(self, text: str, pos: int, *, read_only: bool = False) -> None:
        self.editor = _Editor(text, pos)
        self.document = _Document()
        self.frame = None
        self.status: list[str] = []
        self._read_only = read_only

    def _document_is_read_only(self) -> bool:
        return self._read_only

    def _set_status(self, message: str) -> None:
        self.status.append(message)

    def _announce(self, _message: str) -> None:
        pass

    def _replace_document_text(self, updated_text: str) -> None:
        self.editor._text = updated_text


def test_describe_image_at_cursor_reports_present_alt_text() -> None:
    text = "Here: ![a sunset](sunset.png) end."
    host = _Host(text, pos=text.index("sunset.png"))
    host.describe_image_at_cursor()
    assert host.status == ["Image: sunset.png, alt text: a sunset"]


def test_describe_image_at_cursor_reports_missing_alt_text() -> None:
    text = "![](photo.jpg)"
    host = _Host(text, pos=2)
    host.describe_image_at_cursor()
    assert host.status == ["Image: photo.jpg, alt text MISSING"]


def test_describe_image_at_cursor_no_image_reports_status() -> None:
    host = _Host("just text here", pos=3)
    host.describe_image_at_cursor()
    assert host.status == ["No image at the cursor."]


def test_insert_image_respects_read_only_guard() -> None:
    host = _Host("", pos=0, read_only=True)
    host.insert_image()
    assert host.status == ["Document is read-only"]


def test_insert_image_inserts_the_returned_markdown_at_cursor(monkeypatch) -> None:
    class _FakeDialog:
        def __init__(self, parent, announce_cb=None) -> None:
            pass

        def show(self) -> str:
            return "![a cat](cat.png)"

        def close(self) -> None:
            pass

    monkeypatch.setattr("quill.ui.insert_image_dialog.InsertImageDialog", _FakeDialog)
    host = _Host("before after", pos=len("before "))
    host.insert_image()
    assert host.editor.GetValue() == "before ![a cat](cat.png)after"
    assert host.document.text == "before ![a cat](cat.png)after"
    assert host.status == ["Image inserted."]


def test_insert_image_canceled_dialog_does_nothing(monkeypatch) -> None:
    class _FakeDialog:
        def __init__(self, parent, announce_cb=None) -> None:
            pass

        def show(self) -> None:
            return None

        def close(self) -> None:
            pass

    monkeypatch.setattr("quill.ui.insert_image_dialog.InsertImageDialog", _FakeDialog)
    host = _Host("unchanged", pos=3)
    host.insert_image()
    assert host.editor.GetValue() == "unchanged"
    assert host.status == []
