"""The hosted-AI windows, built for real rather than through a recorder.

Every command test replaces these frames with a recorder, which is how
Connect or Sign Out and Usage both shipped with constructors that raised: the
Close button was parented to the frame while the sizer it sat in belonged to
the panel, wx asserted, and the command dropped the user back in the editor
with nothing said (reported 2026-09-25).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import wx

from quill.ui.hosted_ai_dialogs import AiSignInFrame, AiUsageFrame


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _service(signed_in: bool) -> SimpleNamespace:
    return SimpleNamespace(
        signed_in=signed_in,
        support_id="A1B2-C3D4",
        start_sign_in=lambda **_k: None,
        fetch_quota=lambda **_k: None,
        sign_out=lambda: None,
    )


@pytest.mark.parametrize("signed_in", [False, True])
def test_the_sign_in_window_builds_in_every_state(wx_app, signed_in) -> None:
    frame = AiSignInFrame(None, _service(signed_in), lambda _text: None)
    try:
        code = SimpleNamespace(user_code="ABCD1234", spoken="A B C D", verification_uri="https://x")
        frame._on_show_code(None)
        frame._show_code(code)
        frame._show_error("It did not work.")
        frame._show_connected("A1B2-C3D4")
    finally:
        frame.Destroy()


def test_the_usage_window_builds(wx_app) -> None:
    frame = AiUsageFrame(None, _service(True), lambda _text: None)
    frame.Destroy()


def _press_escape(frame) -> None:
    event = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
    event.SetKeyCode(wx.WXK_ESCAPE)
    event.SetEventObject(frame)
    frame.GetEventHandler().ProcessEvent(event)


@pytest.mark.parametrize("build", [AiSignInFrame, AiUsageFrame])
def test_escape_closes_the_window(wx_app, build) -> None:
    """A frame does nothing with Escape unless told to (reported 2026-09-25)."""
    frame = build(None, _service(True), lambda _text: None)
    closed = []
    frame.Bind(wx.EVT_CLOSE, lambda event: (closed.append(True), event.Skip()))
    _press_escape(frame)
    assert closed == [True]


def test_the_usage_window_puts_focus_on_the_allowance(wx_app) -> None:
    """With no focus target the frame itself kept focus, and neither the arrow
    keys nor Tab did anything (reported 2026-09-25)."""
    frame = AiUsageFrame(None, _service(True), lambda _text: None)
    try:
        assert getattr(frame, "_focus_target", None) is frame._body
    finally:
        frame.Destroy()


def test_a_window_with_no_target_still_focuses_a_control(wx_app) -> None:
    from quill.ui.hosted_ai_dialogs import _first_focusable

    frame = AiSignInFrame(None, _service(True), lambda _text: None)
    try:
        assert isinstance(_first_focusable(frame), wx.TextCtrl)
    finally:
        frame.Destroy()
