"""Palette toggles must carry their own state in their label (#1383).

The Command Palette lists ``Command.title`` verbatim and has no checkmark
column, so "Toggle Soft Wrap" reads identically whether soft wrap is on or off
-- the one fact the user opened the palette to learn. Announce Track Titles was
reported; every other boolean command had the same defect, so the fix is a
refresh pass over all of them rather than one label.
"""

from __future__ import annotations

import types

from quill.core.commands import CommandRegistry
from quill.ui.main_frame import MainFrame


def _frame(**settings: object) -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame.commands = CommandRegistry()  # type: ignore[assignment]
    frame.settings = types.SimpleNamespace(**settings)  # type: ignore[assignment]
    return frame


def test_state_is_stamped_onto_every_registered_toggle() -> None:
    frame = _frame(soft_wrap=True, spellcheck_as_you_type=False, theme="dark")
    frame.commands.register("view.toggle_soft_wrap", "Toggle Soft Wrap", lambda: None)
    frame.commands.register(
        "view.toggle_spellcheck_as_you_type", "Toggle Spell Check As You Type", lambda: None
    )
    frame.commands.register("view.toggle_dark_mode", "Toggle Dark Mode", lambda: None)
    frame._refresh_palette_toggle_titles()
    assert frame.commands.get("view.toggle_soft_wrap").title == "Toggle Soft Wrap (currently On)"
    assert (
        frame.commands.get("view.toggle_spellcheck_as_you_type").title
        == "Toggle Spell Check As You Type (currently Off)"
    )
    assert frame.commands.get("view.toggle_dark_mode").title == "Toggle Dark Mode (currently On)"


def test_refreshing_twice_does_not_stack_suffixes() -> None:
    frame = _frame(soft_wrap=True)
    frame.commands.register("view.toggle_soft_wrap", "Toggle Soft Wrap", lambda: None)
    frame._refresh_palette_toggle_titles()
    frame.settings.soft_wrap = False
    frame._refresh_palette_toggle_titles()
    assert frame.commands.get("view.toggle_soft_wrap").title == "Toggle Soft Wrap (currently Off)"


def test_session_only_toggles_read_the_frame_not_settings() -> None:
    frame = _frame()
    frame._overwrite_mode = True
    frame._tab_inserts_literal = False
    frame.commands.register("view.toggle_overwrite_mode", "Toggle Overwrite Mode", lambda: None)
    frame.commands.register("format.toggle_tab_insert_mode", "Toggle Tab Insert Mode", lambda: None)
    frame._refresh_palette_toggle_titles()
    assert "currently On" in frame.commands.get("view.toggle_overwrite_mode").title
    assert "currently Off" in frame.commands.get("format.toggle_tab_insert_mode").title


def test_unregistered_toggles_are_simply_skipped() -> None:
    frame = _frame(soft_wrap=True)
    frame._refresh_palette_toggle_titles()  # must not raise on an empty registry


def test_palette_refreshes_labels_before_it_opens() -> None:
    import inspect

    source = inspect.getsource(MainFrame._open_palette_dialog)
    assert "_refresh_palette_toggle_titles()" in source
