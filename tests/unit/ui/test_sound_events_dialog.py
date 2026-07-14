"""Source-contract test for SoundEventsDialog section headings (#331).

The live ``wx.Dialog`` is not runtime-instantiated in tests; the repo validates
dialog wiring through source contracts (see ``test_session_browser.py``).
"""

from __future__ import annotations

from pathlib import Path

SOURCE = (
    Path(__file__).resolve().parents[3] / "quill" / "ui" / "sound_events_dialog.py"
).read_text(encoding="utf-8")


def test_section_heading_has_accessible_name() -> None:
    assert 'lbl.SetName(f"{heading} heading")' in SOURCE
