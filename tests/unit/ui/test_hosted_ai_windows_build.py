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


def _every_static_text_labels_a_field(frame) -> list[str]:
    """Static text that is not immediately followed by a control Tab reaches."""
    loose = []
    for panel in frame.GetChildren():
        children = list(panel.GetChildren())
        for index, child in enumerate(children):
            if isinstance(child, wx.StaticText):
                following = children[index + 1] if index + 1 < len(children) else None
                if following is None or isinstance(following, wx.StaticText):
                    loose.append(child.GetLabel())
    return loose


def test_every_sentence_in_the_sign_in_window_is_reachable_by_tab(wx_app) -> None:
    """Reported 2026-09-25: text in a StaticText cannot be tabbed to, so a
    sentence there is heard once or never. Every static label here names a
    field, and the sentences themselves live in read-only fields."""
    code = SimpleNamespace(
        user_code="ABCD1234",
        spoken="A B C D",
        verification_uri="https://x",
        verification_uri_complete="https://x?code=ABCD1234",
    )
    frame = AiSignInFrame(None, _service(False), lambda _text: None)
    try:
        assert _every_static_text_labels_a_field(frame) == []
        frame._show_code(code)
        assert _every_static_text_labels_a_field(frame) == []
    finally:
        frame.Destroy()


def test_an_error_is_spoken_when_the_window_is_not_in_front(wx_app) -> None:
    from quill.ui.hosted_ai_dialogs import show_problem

    frame = AiUsageFrame(None, _service(True), lambda _text: None)
    said: list[str] = []
    try:
        show_problem(frame, frame._body, "It did not work.", said.append)
        assert frame._body.GetValue() == "It did not work."
        assert frame._focus_target is frame._body
        assert said == ["It did not work."]  # never shown, so never active
    finally:
        frame.Destroy()


def test_an_error_sentence_leads_with_words_not_the_code() -> None:
    from quill.core.ai.gateway_errors import GatewayQuotaError
    from quill.ui.hosted_ai_service import _sentence

    text = _sentence(GatewayQuotaError("You've reached this hour's request limit."))
    assert text.startswith("You've reached")
    assert "Error code QUILL-" in text
    assert "[" not in text
