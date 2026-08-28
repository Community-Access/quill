"""GATE-PLAYER-HELP: F1 help ships with every Media Player surface and control.

The mirror of ``test_radio_help_audit`` and ``test_cast_help_audit`` -- the
same three facts, judged against the Media Player's own catalogue
(:mod:`quill.core.media.surface_help`, authored 2026-08-27) and its own
inventory:

1. **Every window title resolves to a purpose.** A new ``wx.Frame`` /
   ``wx.Dialog`` in the media UI whose title has no entry fails here, so a
   window cannot ship without saying what it is for.
2. **Every helpable control is accounted for.** The committed inventory
   classifies every construction site; a brand-new site is ``missing`` until
   a human either authors help or classifies it -- and ``missing`` fails.
3. **The wiring cannot silently disappear.** The player re-activates the
   shared engine with its own resolver at startup, after the app shell's
   generic activation.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.media import surface_help
from quill.tools import player_help_audit

REPO = Path(__file__).resolve().parents[3]


def test_every_player_window_title_has_an_authored_purpose() -> None:
    _sites, violations = player_help_audit.scan()
    assert violations == [], "\n".join(
        f"{v.key}:{v.line}: {v.title!r} -- {v.reason}" for v in violations
    )


def test_control_inventory_matches_source_with_nothing_missing() -> None:
    sites, _violations = player_help_audit.scan()
    committed = player_help_audit.load_snapshot()
    live = player_help_audit.build_snapshot(sites, committed)
    assert live == committed, (
        "Helpable-control sites changed. Run "
        "'python -m quill.tools.player_help_audit --write', then author "
        "SetHelpText for each new site (or classify it deliberately) -- a "
        "control without help is a question F1 cannot answer."
    )
    missing = sorted(key for key, status in committed.items() if status == "missing")
    assert missing == [], (
        "These controls have no help and no reviewed classification: " + ", ".join(missing)
    )
    assert set(committed.values()) <= player_help_audit.STATUSES


def test_the_f1_wiring_is_in_place() -> None:
    player_app = (REPO / "quill" / "apps" / "player.py").read_text(encoding="utf-8")
    assert "from quill.ui.media import context_help" in player_app
    assert "context_help.activate()" in player_app
    shim = (REPO / "quill" / "ui" / "media" / "context_help.py").read_text(encoding="utf-8")
    assert "app_context_help.activate(surface_help.purpose_for_title)" in shim


def test_the_unscanned_window_titles_are_answered_by_the_catalogue() -> None:
    """Windows built via ``super().__init__`` (or ``wx.TextEntryDialog``) are
    outside the title scan; their catalogue entries are pinned here instead."""
    for title in (
        "Quill Media Player",  # the main frame, titled by _init_app_shell
        "Go to Position",  # super().__init__ with a _() title
        "Book Library",  # super().__init__
        "Mini Player",  # super().__init__
        "Voice Command",  # wx.TextEntryDialog
        "Jump to File",  # wx.TextEntryDialog (winamp_mixin)
        "Add Bookmark",  # wx.TextEntryDialog (_prompt_text)
        "Edit Bookmark",  # wx.TextEntryDialog (_prompt_text)
    ):
        assert surface_help.is_known_title(title), title


def test_the_generic_purpose_is_the_floor_not_a_ceiling() -> None:
    assert surface_help.purpose_for_title("Some Unknown Window") == surface_help.GENERIC_PURPOSE
    assert surface_help.purpose_for_title("Quill Media Player") != surface_help.GENERIC_PURPOSE
    assert surface_help.purpose_for_title("Help: Chapters").startswith("This is the help window")
