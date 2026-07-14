"""Live-wx regression for issue #624: opening Quill Eraser on a document that
has problems crashed with ``TypeError: Dialog(): argument 1 has unexpected
type 'MainFrame'``.

The cause: ``HygieneMixin._run_hygiene`` was passing ``self`` (the mixin
instance) as the dialog parent, but ``MainFrame`` is a pure mixin class that
does not inherit from ``wx.Window``. The dialog must be parented to the real
``wx.Frame`` stored as ``self.frame`` on the mixin.

This test instantiates the real ``HygieneReviewDialog`` with a stand-in mixin
whose ``self.frame`` is the real wx frame, and asserts the dialog is created
without raising.

Runs on Windows only (where wxPython is installed); skipped on Linux CI.
"""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from quill.core.hygiene.findings import HygieneFinding  # noqa: E402
from quill.ui.hygiene_dialog import HygieneReviewDialog  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _make_finding() -> HygieneFinding:
    return HygieneFinding(
        rule_id="prose.multiple_spaces",
        title="Multiple spaces",
        description="Two or more spaces in a row.",
        confidence="high",
        start_offset=5,
        end_offset=7,
        line=1,
        column=5,
        original_text="  ",
        suggested_text=" ",
        can_auto_fix=True,
    )


def test_dialog_accepts_real_wx_frame_parent(wx_app) -> None:
    """Regression for #624: the dialog must be parented to a wx.Window, not a
    MainFrame mixin instance."""
    parent = wx.Frame(None, title="parent")
    try:
        findings = [_make_finding()]
        dlg = HygieneReviewDialog(
            parent,
            findings,
            on_apply_fix=lambda _f: None,
            on_go_to=lambda _f: None,
            on_rescan=lambda: None,
        )
        try:
            assert dlg is not None
        finally:
            dlg.close()
    finally:
        parent.Destroy()


def test_dialog_rejects_mainframe_mixin_parent(wx_app) -> None:
    """Documents the original bug: passing a MainFrame mixin (which is not a
    wx.Window) raises ``TypeError`` from wxPython's SIP wrapper. This test
    pins that behavior so future refactors do not silently regress to
    passing ``self`` again."""

    class _FakeMainFrame:
        # Intentionally does NOT inherit from wx.Window — mirrors the real
        # MainFrame, which is a pure mixin.
        pass

    parent = _FakeMainFrame()
    findings = [_make_finding()]
    with pytest.raises(TypeError, match="unexpected type"):
        HygieneReviewDialog(
            parent,  # type: ignore[arg-type]
            findings,
            on_apply_fix=lambda _f: None,
            on_go_to=lambda _f: None,
            on_rescan=lambda: None,
        )
