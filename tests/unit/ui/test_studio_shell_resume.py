"""Headless smoke for the standalone Studio shell's resume-on-launch (2.5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.audio_studio.history import load_history


@pytest.fixture
def app():
    import wx

    a = wx.App(False)
    yield a
    a.Destroy()


def _make_frame(tmp_path: Path):
    from quill.apps.studio import StudioAppFrame

    frame = StudioAppFrame()
    return frame


def test_resume_toggle_persists(app, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    frame = _make_frame(tmp_path)
    try:
        initial = frame._history.resume_on_launch
        frame._toggle_resume_on_launch()
        assert frame._history.resume_on_launch is (not initial)
        # Reload from disk to confirm the toggle persisted.
        reloaded = load_history(tmp_path)
        assert reloaded.resume_on_launch is (not initial)
    finally:
        frame.frame.Destroy()


def test_record_play_populates_recent_submenu(app, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    frame = _make_frame(tmp_path)
    try:
        # A fake book path is fine -- _record_play only stamps history.
        frame._record_play(Path(str(tmp_path / "fakebook.m4b")))
        assert frame._history.last_played is not None
        frame._rebuild_recent_submenu(frame._recent_submenu)
        # One non-empty entry should be present.
        items = frame._recent_submenu.GetMenuItems()
        assert len(items) >= 1
    finally:
        frame.frame.Destroy()