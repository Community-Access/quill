"""The media host plumbing and the media dialogs (wordpress.md 6.2, 6.7, 6.8, 10)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import wx

from quill.ui import wordpress_item_dialogs as idlg
from quill.ui import wordpress_media_dialogs as mdlg
from quill.ui import wordpress_media_host as mhost


class FakeService:
    def __init__(self, connection: str = "chatgpt") -> None:
        self.connection_in_use = connection
        self.asked: list[tuple[Any, str, tuple[str, ...]]] = []

    def describe_image(self, path, question, *, on_done, on_error, requires) -> None:
        self.asked.append((path, question, requires))
        on_done("A stall.")


class FakeEditor:
    def __init__(self, *, on: bool = True, capable: bool = True, connection: str = "chatgpt"):
        self.on = on
        self.capable = capable
        self.service = FakeService(connection)

    def _ai_switched_on(self) -> bool:
        return self.on

    def _ai_capable(self, capability: str) -> bool:
        assert capability == "pictures"
        return self.capable

    def _ai_service(self) -> FakeService:
        return self.service


@pytest.fixture
def consent(monkeypatch):
    answers = {"value": True, "asked": []}

    def ask(host, connection):
        answers["asked"].append(connection)
        return answers["value"]

    import quill.ui.hosted_ai_picture_consent as consent_module

    monkeypatch.setattr(consent_module, "ask_picture_consent", ask)
    return answers


def test_the_editor_ai_is_asked_after_every_gate(consent) -> None:
    editor = FakeEditor()
    done: list[str] = []
    assert mhost.ask_editor_ai(editor, Path("a.png"), "What?", done.append, done.append)
    assert done == ["A stall."]
    assert editor.service.asked == [(Path("a.png"), "What?", ("text", "pictures"))]
    assert consent["asked"] == ["chatgpt"]


@pytest.mark.parametrize(
    "editor",
    [FakeEditor(on=False), FakeEditor(capable=False)],
    ids=["switched off", "cannot see pictures"],
)
def test_a_closed_gate_sends_nothing(editor, consent) -> None:
    assert not mhost.ask_editor_ai(editor, Path("a.png"), "What?", print, print)
    assert editor.service.asked == []


def test_declining_the_picture_agreement_sends_nothing(consent) -> None:
    consent["value"] = False
    editor = FakeEditor()
    assert not mhost.ask_editor_ai(editor, Path("a.png"), "What?", print, print)
    assert editor.service.asked == []


def test_a_window_with_no_ai_says_so() -> None:
    said: list[str] = []
    assert not mhost.ask_editor_ai(object(), Path("a.png"), "What?", print, said.append)
    assert said == ["AI help is not available in this window."]


def test_both_adapters_hand_media_to_the_shared_helpers(monkeypatch) -> None:
    from quill.apps.lite_window_wordpress import LiteWordPressHost
    from quill.ui.main_frame_wordpress import QuillWordPressHost

    calls: list[Any] = []
    monkeypatch.setattr(mhost, "read_clipboard_png", lambda: b"png")
    monkeypatch.setattr(mhost, "ask_editor_ai", lambda ai, *a: calls.append(ai) or True)
    frame, window = object(), object()
    for host, owner in ((QuillWordPressHost(frame), frame), (LiteWordPressHost(window), window)):
        assert host.clipboard_image_png() == b"png"
        assert host.ai_describe_image(Path("a.png"), "Q", print, print) is True
        assert calls[-1] is owner


# --------------------------------------------------------------------------- #
# dialogs


def test_the_image_dialog_suggest_fills_the_field_later(wx_session_app) -> None:
    frame = wx.Frame(None)
    fills: list[Any] = []

    def show_modal(dialog: Any, _label: str) -> int:
        assert dialog.suggest.IsEnabled()
        dialog._on_suggest_click(None)
        fills[0]("Two volunteers behind a stall")
        assert dialog.alt.GetStringSelection() == "Two volunteers behind a stall"
        return wx.ID_OK

    try:
        answer = idlg.ask_image(
            frame, show_modal, name="fair.png", size_text="", on_suggest_async=fills.append
        )
    finally:
        frame.Destroy()
    assert answer is not None and answer.alt == "Two volunteers behind a stall"


def test_upload_details_for_a_picture(wx_session_app) -> None:
    frame = wx.Frame(None)
    fills: list[Any] = []
    described: list[bool] = []

    def show_modal(dialog: Any, label: str) -> int:
        assert label == "Upload: fair.png"
        for button in (dialog.suggest, dialog.describe):
            event = wx.CommandEvent(wx.wxEVT_BUTTON, button.GetId())
            event.SetEventObject(button)
            button.GetEventHandler().ProcessEvent(event)
        fills[0]("A stall")
        dialog.caption.SetValue(" Photo: Sam ")
        return wx.ID_OK

    try:
        answer = mdlg.ask_upload_details(
            frame,
            show_modal,
            name="fair.png",
            site_name="Community Radio",
            is_image=True,
            title="Fair",
            on_suggest_async=fills.append,
            on_describe=lambda: described.append(True),
        )
    finally:
        frame.Destroy()
    assert answer == mdlg.UploadDetails(
        title="Fair", alt="A stall", caption="Photo: Sam", decorative=False
    )
    assert described == [True]


def test_upload_details_decorative_and_documents(wx_session_app) -> None:
    frame = wx.Frame(None)

    def decorative(dialog: Any, _label: str) -> int:
        dialog.alt.SetValue("ignored")
        dialog.decorative.SetValue(True)
        return wx.ID_OK

    try:
        picture = mdlg.ask_upload_details(
            frame, decorative, name="line.png", site_name="R", is_image=True
        )
        document = mdlg.ask_upload_details(
            frame,
            lambda d, _l: wx.ID_OK if d.alt is None and d.decorative is None else wx.ID_CANCEL,
            name="report.pdf",
            site_name="R",
            is_image=False,
            title="Report",
        )
        cancelled = mdlg.ask_upload_details(
            frame, lambda _d, _l: wx.ID_CANCEL, name="a.png", site_name="R", is_image=True
        )
    finally:
        frame.Destroy()
    assert picture is not None and picture.decorative and picture.alt == ""
    assert document == mdlg.UploadDetails(title="Report", alt="", caption="", decorative=False)
    assert cancelled is None
