"""Guarded smoke tests for the media player dialog (PRD 19).

Builds the player against the deterministic null engine, exercises seek/skip/
speed and transcript quoting without any audio backend, then destroys the
dialog. No ``ShowModal``/``MainLoop`` is used.
"""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from quill_social.model import Media  # noqa: E402
from quill_social.services.transcripts import from_srt  # noqa: E402

_SRT = """1
00:00:00,000 --> 00:00:02,000
Hello there

2
00:00:02,000 --> 00:00:05,000
General Kenobi
"""


@pytest.fixture
def app():
    try:
        application = wx.App()
    except Exception:  # pragma: no cover - no display
        pytest.skip("wx cannot initialize in this environment")
    yield application
    application.Destroy()


def _media() -> Media:
    return Media(
        kind="audio",
        uri="mock://clip.mp3",
        caption="Test clip",
        duration_ms=5000,
    )


def test_player_transport_uses_null_engine(app):
    from quill_social.ui.media_player import MediaPlayerDialog

    dlg = MediaPlayerDialog(None, _media())
    try:
        assert dlg.player.engine.name == "null"
        # Play, then seek the deterministic engine and confirm status reflects it.
        dlg._on_toggle()
        dlg.seek_to(2000)
        assert dlg.player.engine.position_ms() == 2000
        assert "0:02" in dlg.status.GetValue()

        dlg._on_skip_back()
        assert dlg.player.engine.position_ms() == 0

        dlg._on_stop()
        assert dlg.player.engine.position_ms() == 0
    finally:
        dlg.Destroy()


def test_player_transcript_seek_and_quote(app):
    from quill_social.ui.media_player import MediaPlayerDialog

    transcript = from_srt(_SRT, resource_id="mock://clip.mp3")
    dlg = MediaPlayerDialog(None, _media(), transcript=transcript)
    try:
        assert dlg.cues is not None
        assert dlg.cues.GetItemCount() == 2

        # Seek to the second cue's start, then quote the current time point.
        dlg.seek_to(transcript.cues[1].start_ms)
        dlg._on_quote()
        assert "General Kenobi" in dlg.quoted_text
        assert "@" in dlg.quoted_text
    finally:
        dlg.Destroy()
