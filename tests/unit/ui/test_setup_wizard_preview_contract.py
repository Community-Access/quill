"""Regression guard for the Setup Wizard preview accessibility (#610 follow-up).

The wizard preview text must be a read-only multi-line wx.TextCtrl for
screen-reader users — the one control NVDA/JAWS (Windows) and VoiceOver (macOS)
can both arrow through line by line, matching the About window. A wx.StaticText
is NOT keyboard-focusable, so Windows screen-reader users could not reach or
read the text (they only landed on the heading). Source-contract test so it runs
in the fast suite without constructing wx.
"""

from __future__ import annotations

from pathlib import Path


def _source() -> str:
    root = Path(__file__).resolve().parents[3]
    return (root / "quill" / "ui" / "setup_wizard_pages.py").read_text(encoding="utf-8")


def test_sr_preview_uses_readonly_multiline_textctrl() -> None:
    src = _source()
    assert "wx.TE_MULTILINE | wx.TE_READONLY" in src, (
        "Wizard SR preview must be a read-only multi-line TextCtrl (arrow-navigable "
        "on Windows and VoiceOver), like the About window."
    )
    assert "_make_readonly_text" in src


def test_sr_preview_is_not_static_text() -> None:
    src = _source()
    # The screen-reader preview path must not regress to a (non-focusable)
    # StaticText that Windows screen readers cannot arrow through.
    assert "_make_static_text" not in src
    assert "wx.StaticText(parent, label=text" not in src
