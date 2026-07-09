"""Tests for Send as Email / Copy as Email Body (#900), the two new
PowerToolsActionsMixin methods."""

from __future__ import annotations

from urllib.parse import parse_qs, unquote, urlparse

import pytest
import wx

from quill.ui.main_frame_power_tools import PowerToolsActionsMixin


class _Editor:
    def __init__(self, text: str, selection: tuple[int, int]) -> None:
        self._text = text
        self._selection = selection

    def GetValue(self) -> str:
        return self._text

    def GetSelection(self) -> tuple[int, int]:
        return self._selection


class _Host(PowerToolsActionsMixin):
    def __init__(self, text: str, selection: tuple[int, int], doc_name: str = "My Doc.md") -> None:
        self.editor = _Editor(text, selection)
        self.document = type("D", (), {"name": doc_name})()
        self.settings = type("S", (), {"content_handoff_format": "text"})()
        self.status: list[str] = []

    def _set_status(self, message: str) -> None:
        self.status.append(message)


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _opened_urls(monkeypatch) -> list[str]:
    opened: list[str] = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url))
    return opened


def test_send_as_email_uses_selection_when_present(wx_app, monkeypatch) -> None:
    opened = _opened_urls(monkeypatch)
    host = _Host("full document text with a selection inside", selection=(5, 13))
    host.send_as_email()
    assert len(opened) == 1
    body = unquote(parse_qs(urlparse(opened[0]).query)["body"][0])
    assert body == "document"
    assert host.status == ["Opened your mail client with this content as the body."]


def test_send_as_email_uses_whole_document_when_no_selection(wx_app, monkeypatch) -> None:
    opened = _opened_urls(monkeypatch)
    host = _Host("the whole document", selection=(3, 3))
    host.send_as_email()
    body = unquote(parse_qs(urlparse(opened[0]).query)["body"][0])
    assert body == "the whole document"


def test_send_as_email_subject_is_the_document_name(wx_app, monkeypatch) -> None:
    opened = _opened_urls(monkeypatch)
    host = _Host("text", selection=(0, 0), doc_name="Report.md")
    host.send_as_email()
    subject = parse_qs(urlparse(opened[0]).query)["subject"][0]
    assert subject == "Report.md"


def test_send_as_email_empty_document_reports_status_and_does_not_open(wx_app, monkeypatch) -> None:
    opened = _opened_urls(monkeypatch)
    host = _Host("   ", selection=(0, 0))
    host.send_as_email()
    assert opened == []
    assert host.status == ["Nothing to send: the document is empty."]


def test_copy_as_email_body_empty_document_reports_status(wx_app) -> None:
    host = _Host("", selection=(0, 0))
    host.copy_as_email_body()
    assert host.status == ["Nothing to copy: the document is empty."]


def test_copy_as_email_body_puts_rendered_text_on_the_clipboard(wx_app) -> None:
    host = _Host("**bold** content", selection=(0, 0))
    host.copy_as_email_body()
    assert host.status == ["Copied to the clipboard as an email body."]
    assert wx.TheClipboard.Open()
    data = wx.TextDataObject()
    wx.TheClipboard.GetData(data)
    wx.TheClipboard.Close()
    assert data.GetText() == "bold content"
