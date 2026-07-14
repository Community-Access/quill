"""Tests for Format > Update/Remove Outline Numbering (#894), the two new
PowerToolsActionsMixin methods."""

from __future__ import annotations

from quill.ui.main_frame_power_tools import PowerToolsActionsMixin


class _Editor:
    def __init__(self, text: str) -> None:
        self._text = text

    def GetValue(self) -> str:
        return self._text

    def SetValue(self, text: str) -> None:
        self._text = text

    def SetSelection(self, start: int, end: int) -> None:
        pass


class _Document:
    def __init__(self) -> None:
        self.text = ""

    def set_text(self, text: str) -> None:
        self.text = text


class _Host(PowerToolsActionsMixin):
    def __init__(self, text: str, *, read_only: bool = False, style: str = "numeric") -> None:
        self.editor = _Editor(text)
        self.document = _Document()
        self.settings = type("S", (), {"auto_outline_style": style})()
        self.status: list[str] = []
        self._read_only = read_only

    def _document_is_read_only(self) -> bool:
        return self._read_only

    def _set_status(self, message: str) -> None:
        self.status.append(message)

    def _replace_document_text(self, updated_text: str) -> None:
        self.editor.SetValue(updated_text)


def test_apply_auto_outline_numbering_numbers_headings() -> None:
    host = _Host("# Intro\n## Background\n")
    host.apply_auto_outline_numbering()
    assert host.editor.GetValue() == "# 1. Intro\n## 1.1. Background\n"
    assert host.document.text == "# 1. Intro\n## 1.1. Background\n"
    assert host.status == ["Outline numbering updated."]


def test_apply_auto_outline_numbering_uses_legal_style_setting() -> None:
    host = _Host("# Intro\n## Background\n", style="legal")
    host.apply_auto_outline_numbering()
    assert host.editor.GetValue() == "# I. Intro\n## I.A. Background\n"


def test_apply_auto_outline_numbering_no_headings_reports_status() -> None:
    host = _Host("just a paragraph\n")
    host.apply_auto_outline_numbering()
    assert host.status == ["No headings to number."]
    assert host.editor.GetValue() == "just a paragraph\n"


def test_apply_auto_outline_numbering_respects_read_only_guard() -> None:
    host = _Host("# Intro\n", read_only=True)
    host.apply_auto_outline_numbering()
    assert host.status == ["Document is read-only"]
    assert host.editor.GetValue() == "# Intro\n"


def test_remove_auto_outline_numbering_reverts_numbered_headings() -> None:
    host = _Host("# 1. Intro\n## 1.1. Background\n")
    host.remove_auto_outline_numbering()
    assert host.editor.GetValue() == "# Intro\n## Background\n"
    assert host.status == ["Outline numbering removed."]


def test_remove_auto_outline_numbering_no_op_reports_status() -> None:
    host = _Host("# Intro\n")
    host.remove_auto_outline_numbering()
    assert host.status == ["No outline numbering to remove."]


def test_remove_auto_outline_numbering_respects_read_only_guard() -> None:
    host = _Host("# 1. Intro\n", read_only=True)
    host.remove_auto_outline_numbering()
    assert host.status == ["Document is read-only"]
    assert host.editor.GetValue() == "# 1. Intro\n"
