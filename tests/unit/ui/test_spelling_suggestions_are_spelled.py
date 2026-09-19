"""The suggestion list spells itself as you arrow (bad.md P1.14, rule 10).

The last half of P1.14, and it was the quietest kind of gap: QUILL built the
announcer with the shared voicing settings, shipped an Announcements window to
edit them, and never called ``spell_suggestion`` -- so one of the twelve settings
that window offers did nothing at all in QUILL, while QuillLite had been spelling
suggestions since it shipped.

Choosing between "receive" and "recieve" by ear is exactly as impossible in a
list of corrections as it was in the document. A sighted user compares the two
spellings at a glance; a listener arrowing through eight near-identical
suggestions hears eight identical sounds.
"""

from __future__ import annotations

from pathlib import Path

DIALOG = Path(__file__).resolve().parents[3] / "quill" / "ui" / "spelling_review_dialog.py"
LITE = Path(__file__).resolve().parents[3] / "quill" / "apps" / "lite_window_spelling.py"


def test_quill_spells_the_highlighted_suggestion() -> None:
    source = DIALOG.read_text(encoding="utf-8")
    handler = source[source.index("    def _on_suggestion_select(self") :][:1400]
    assert "self._announcer.spell_suggestion(" in handler


def test_both_editors_spell_suggestions_so_neither_is_ahead() -> None:
    """Rule 10: QuillLite is never allowed to be ahead of QUILL."""
    assert "spell_suggestion" in DIALOG.read_text(encoding="utf-8")
    assert "_spell_suggestion" in LITE.read_text(encoding="utf-8")


def test_the_shared_announcer_owns_the_timing() -> None:
    """Neither editor reimplements the pause, so they cannot disagree about it."""
    from quill.core.spelling.announcements import AccessibilityAnnouncer

    assert hasattr(AccessibilityAnnouncer, "spell_suggestion")


def test_the_setting_the_window_offers_is_actually_read() -> None:
    """A setting nothing reads is a switch that does nothing, quietly."""
    from quill.core.spelling.voicing import SpellAloudPolicy

    class _Settings:
        spell_aloud_suggestions = True
        spell_aloud_suggestion_delay_ms = 250

    policy = SpellAloudPolicy.from_settings(_Settings())
    assert policy.suggestions is True
    assert policy.suggestion_delay_ms == 250
