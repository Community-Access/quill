"""Opt-in real Windows capture of this test's own native window only."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.machine_global,
    pytest.mark.skipif(
        os.name != "nt" or os.environ.get("QUILL_CAPTURE_LIVE_TEST") != "1",
        reason="Run explicitly on Windows with QUILL_CAPTURE_LIVE_TEST=1",
    ),
]


def test_capture_named_native_window_contains_expected_pixels(wx_session_app, tmp_path):
    import wx
    from PIL import Image

    from quill.core.studio_capture import save_capture_report, verify_capture
    from quill.platform.windows.studio_capture import capture_target, list_capture_targets

    frame = wx.Frame(None, title="QUILL Studio capture verification fixture", size=(420, 240))
    panel = wx.Panel(frame)
    panel.SetBackgroundColour(wx.Colour(12, 34, 56))
    label = wx.StaticText(panel, label="QUILL capture verification 12345", pos=(20, 20))
    label.SetForegroundColour(wx.WHITE)
    frame.Show()
    frame.Update()
    wx_session_app.Yield()
    try:
        targets = list_capture_targets()
        selected = next(t for t in targets if t.window_handle == frame.GetHandle())
        assert {"desktop", "display", "window", "active_window", "region"} <= {
            target.kind for target in targets
        }
        evidence = capture_target(tmp_path, selected)
        assert evidence.metadata["window_handle"] == frame.GetHandle()
        assert evidence.width > 200 and evidence.height > 100
        with Image.open(evidence.path) as image:
            colors = image.convert("RGB").getcolors(maxcolors=image.width * image.height)
            assert colors is not None
            assert sum(count for count, color in colors if color == (12, 34, 56)) > 100
        assert verify_capture(Path(evidence.path), evidence.target).sha256 == evidence.sha256
        assert save_capture_report(evidence).is_file()
    finally:
        frame.Destroy()
