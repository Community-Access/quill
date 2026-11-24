"""The Scribe Status dialog: opens, closes, refreshes, wraps, says each thing once."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.scribe import queue as q
from quill.core.scribe.errors import ScribeOfflineError
from tests.unit.ui.test_scribe_ui import (  # noqa: F401 - fixtures used by name
    controller,
    isolated,
)

pytestmark = pytest.mark.usefixtures("wx_session_app")


class Deferred:
    """The controller's background pool, answered when the test says."""

    def __init__(self) -> None:
        self.pending: list[tuple[Any, Any, Any]] = []

    def __call__(self, work: Any, done: Any, failed: Any = None) -> None:
        self.pending.append((work, done, failed))

    def run(self) -> None:
        while self.pending:
            work, done, failed = self.pending.pop(0)
            try:
                result = work()
            except Exception as error:  # noqa: BLE001
                failed(error)
                continue
            done(result)


@pytest.fixture
def pool(controller: Any, monkeypatch: pytest.MonkeyPatch) -> Deferred:  # noqa: F811
    deferred = Deferred()
    monkeypatch.setattr(controller, "_background", deferred)
    return deferred


def _dialog(controller: Any) -> Any:  # noqa: F811
    from quill.ui.scribe_status_dialog import ScribeStatusDialog

    return ScribeStatusDialog(None, controller)


def test_local_facts_at_once_then_the_account_without_blocking(
    controller: Any,  # noqa: F811
    pool: Deferred,
) -> None:
    controller.queue.add([q.Job(file_name="Notes.pdf", formats=["docx"])])
    controller.server.pages_remaining = 412
    dialog = _dialog(controller)
    try:
        assert dialog.GetTitle() == "Scribe Status"
        first = dialog.text.GetValue().split("\n")[0]
        assert first == "Signed in. Checking your Scribe account..."
        assert "Notes.pdf: Queued." in dialog.text.GetValue()
        assert controller.server.requests == []  # nothing on the UI thread
        pool.run()
        assert dialog.text.GetValue().split("\n")[0] == "Signed in as Pat Reader. 412 pages left."
        # Arrived before the dialog was showing: read on focus, not announced.
        assert controller.host.said == []
        assert not dialog.sign_in_button.IsShown()
    finally:
        dialog.Destroy()


def test_refresh_reads_again_and_says_so_once(controller: Any, pool: Deferred) -> None:  # noqa: F811
    import wx

    dialog = _dialog(controller)
    try:
        pool.run()
        controller.server.pages_remaining = 7
        dialog.refresh_button.Command(wx.CommandEvent(wx.wxEVT_BUTTON))
        # The last account stays while the new one is read.
        assert "Pat Reader" in dialog.text.GetValue().split("\n")[0]
        pool.run()
        assert controller.host.said == [
            "Scribe Status updated. Signed in as Pat Reader. 7 pages left."
        ]
        assert dialog.text.GetInsertionPoint() == 0
    finally:
        dialog.Destroy()


def test_an_account_read_after_showing_is_said_once(controller: Any, pool: Deferred) -> None:  # noqa: F811
    dialog = _dialog(controller)
    try:
        dialog._mark_shown()
        pool.run()
        pool.run()
        assert controller.host.said == ["Signed in as Pat Reader. 100 pages left."]
    finally:
        dialog.Destroy()


def test_an_api_error_is_shown_with_its_code_and_said_once(
    controller: Any,  # noqa: F811
    pool: Deferred,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Broken:
        def account(self) -> Any:
            raise ScribeOfflineError("Couldn't connect to Scribe.")

    monkeypatch.setattr(controller, "client", lambda: Broken())
    dialog = _dialog(controller)
    try:
        dialog._mark_shown()
        pool.run()
        first = dialog.text.GetValue().split("\n")[0]
        assert first.endswith("Couldn't connect to Scribe. (QUILL-SCRIBE-OFFLINE)")
        assert controller.host.said == [
            "Your Scribe account could not be read: Couldn't connect to Scribe."
        ]
    finally:
        dialog.Destroy()


def test_not_signed_in_offers_sign_in(controller: Any, pool: Deferred) -> None:  # noqa: F811
    controller.session.is_signed_in = lambda: False
    dialog = _dialog(controller)
    try:
        assert dialog.text.GetValue().startswith("You are not signed in")
        assert dialog.sign_in_button.IsShown()
        assert pool.pending == []  # nothing to read without a sign-in
    finally:
        dialog.Destroy()


def test_conversions_closes_this_and_opens_that(
    controller: Any,  # noqa: F811
    pool: Deferred,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import wx

    import quill.ui.dialog_contract as contract

    opened: list[str] = []
    monkeypatch.setattr(controller, "open_conversions", lambda: opened.append("conversions"))

    def show(dialog: Any, label: str, **_kw: Any) -> int:
        assert label == "Scribe Status"
        dialog.conversions_button.Command(wx.CommandEvent(wx.wxEVT_BUTTON))
        return wx.ID_CANCEL

    monkeypatch.setattr(contract, "show_modal_dialog", show)
    monkeypatch.setattr(wx.Dialog, "EndModal", lambda self, code: None)
    controller.status()
    assert opened == ["conversions"]


def test_close_and_escape_end_the_dialog(controller: Any, pool: Deferred, monkeypatch: Any) -> None:  # noqa: F811
    import wx

    dialog = _dialog(controller)
    ended: list[int] = []
    monkeypatch.setattr(dialog, "EndModal", lambda code: ended.append(code))
    try:
        close = dialog.FindWindow(wx.ID_CANCEL)
        assert close.GetLabel() == "Close"
        close.Command(wx.CommandEvent(wx.wxEVT_BUTTON))

        class Key:
            def GetKeyCode(self) -> int:  # noqa: N802 - wx API
                return wx.WXK_ESCAPE

        dialog._on_char_hook(Key())
        assert ended == [wx.ID_CANCEL, wx.ID_CANCEL]
        assert dialog.GetEscapeId() == wx.ID_CANCEL
    finally:
        dialog.Destroy()


def test_the_command_opens_the_dialog_through_the_contract(
    controller: Any,  # noqa: F811
    pool: Deferred,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import wx

    import quill.ui.dialog_contract as contract

    shown: list[str] = []
    monkeypatch.setattr(
        contract, "show_modal_dialog", lambda d, label, **_k: shown.append(label) or wx.ID_CANCEL
    )
    controller.status()
    assert shown == ["Scribe Status"]
    assert controller.host.said == []  # nothing spoken: the dialog shows it


def _inside(dialog: Any) -> None:
    client = dialog.GetClientSize()
    rect = dialog.text.GetRect()
    assert rect.x >= 0 and rect.x + rect.width <= client.width, (rect, client)


@pytest.mark.parametrize("scale", [1, 2])
def test_the_text_is_never_wider_than_the_dialog(
    controller: Any,  # noqa: F811
    pool: Deferred,
    scale: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Workbench details pane once ran wider than its window; this cannot."""
    import wx

    import quill.ui.scribe_status_dialog as module

    if scale > 1:  # 200 percent text: every measurement from the font doubles
        real = module.readable_min_size
        monkeypatch.setattr(
            module,
            "readable_min_size",
            lambda w, **kw: tuple(v * scale for v in real(w, **kw)),
        )
    controller.queue.add([q.Job(file_name="A very long file name " * 8 + ".pdf")])
    dialog = _dialog(controller)
    try:
        pool.run()
        assert not dialog.text.HasFlag(wx.HSCROLL)
        _inside(dialog)
        area = wx.Display(0).GetClientArea()
        assert dialog.GetSize().width <= area.width
        for width, height in ((200, 150), (500, 400), (1400, 900)):
            dialog.SetSize(wx.Size(width, height))
            dialog.Layout()
            _inside(dialog)
    finally:
        dialog.Destroy()


def test_access_keys_are_unique(controller: Any, pool: Deferred) -> None:  # noqa: F811
    import wx

    dialog = _dialog(controller)
    try:
        keys = []
        for child in dialog.GetChildren():
            label = child.GetLabel() if isinstance(child, (wx.Button, wx.StaticText)) else ""
            if "&" in label:
                keys.append(label[label.index("&") + 1].lower())
        assert len(keys) == len(set(keys)) and len(keys) == 5
    finally:
        dialog.Destroy()


def test_repeat_last_is_unchanged(controller: Any) -> None:  # noqa: F811
    controller.repeat_last()
    assert controller.host.said == ["Nothing from Scribe for Documents yet."]


def test_a_refresh_keeps_the_caret_where_the_person_is_reading(
    controller: Any,  # noqa: F811
    pool: Deferred,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import wx

    controller.queue.add([q.Job(file_name="Next.pdf"), q.Job(file_name="Later.pdf")])
    dialog = _dialog(controller)
    try:
        pool.run()
        monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: dialog.text))
        lines = dialog.text.GetValue().split(chr(10))
        target = next(i for i, line in enumerate(lines) if line.startswith("Later.pdf"))
        position = dialog.text.XYToPosition(2, target)
        dialog.text.SetInsertionPoint(position)
        dialog._mark_shown()
        dialog.refresh(announce=True)
        pool.run()
        _ok, column, line = dialog.text.PositionToXY(dialog.text.GetInsertionPoint())
        assert dialog.text.GetValue().split(chr(10))[line].startswith("Later.pdf")
        assert column == 2
        # Reading further down: told it changed, not the first line read out.
        assert controller.host.said == ["Scribe Status updated."]
    finally:
        dialog.Destroy()


def test_conversions_does_not_stop_at_the_opener_on_the_way(
    controller: Any,  # noqa: F811
    pool: Deferred,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import wx

    import quill.ui.dialog_contract as contract

    focused: list[str] = []

    class Opener:
        def __bool__(self) -> bool:
            return True

        def SetFocus(self) -> None:  # noqa: N802 - wx API
            focused.append("opener")

    monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: Opener()))
    monkeypatch.setattr(controller, "open_conversions", lambda: focused.append("conversions"))

    def show(dialog: Any, _label: str, **_kw: Any) -> int:
        dialog.then_open = "conversions"
        return wx.ID_CANCEL

    monkeypatch.setattr(contract, "show_modal_dialog", show)
    controller.status()
    assert focused == ["conversions"]
    monkeypatch.setattr(contract, "show_modal_dialog", lambda *_a, **_k: wx.ID_CANCEL)
    controller.status()
    assert focused == ["conversions", "opener"]
