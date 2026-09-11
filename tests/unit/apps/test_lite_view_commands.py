"""The View menu: what each command changes, and what it says it changed.

Every one of these is a state change plus a sentence, and the sentence is the
only part a listener gets -- nothing here moves focus, and a screen reader does
not read a setting that changed behind a window. So the assertion pattern
throughout is the pair: the setting moved *and* the words match what it moved
to. A command that flipped the setting and said the old word would be worse than
one that did nothing, because the user would believe it.

These handlers were ``shape_only`` in ``lite_command_coverage.json`` until
2026-09-10: known to exist, never exercised. See
:mod:`quill.tools.lite_command_coverage` for why that distinction earns a gate.
"""

from __future__ import annotations

import pytest

# --------------------------------------------------------------------------- #
# Theme, wrap and the status bar: app-wide switches
# --------------------------------------------------------------------------- #


def test_toggle_dark_flips_the_theme_and_says_which_way(lite_window):
    win = lite_window("hello")
    win.app.settings.theme = "dark"

    win.cmd_toggle_dark()
    assert win.app.settings.theme == "system"
    assert win.announcements[-1] == "Dark mode off"

    win.cmd_toggle_dark()
    assert win.app.settings.theme == "dark"
    assert win.announcements[-1] == "Dark mode on"


def test_toggle_dark_saves_and_reapplies(lite_window):
    """Both halves: a setting that is not saved is a setting that does not last,
    and one that is not re-applied is one that needs a restart to be seen."""
    win = lite_window("hello")
    before = (win.app.saved_settings, win.app.reapplied)
    win.cmd_toggle_dark()
    assert (win.app.saved_settings, win.app.reapplied) == (before[0] + 1, before[1] + 1)


def test_toggle_wrap_flips_and_announces(lite_window):
    win = lite_window("hello")
    win.app.settings.word_wrap = True
    win.cmd_toggle_wrap()
    assert win.app.settings.word_wrap is False
    assert win.announcements[-1] == "Word wrap off"
    win.cmd_toggle_wrap()
    assert win.app.settings.word_wrap is True
    assert win.announcements[-1] == "Word wrap on"


def test_toggle_status_bar_flips_and_announces(lite_window):
    win = lite_window("hello")
    win.app.settings.show_status_bar = True
    win.cmd_toggle_status_bar()
    assert win.app.settings.show_status_bar is False
    assert win.announcements[-1] == "Status bar hidden"
    win.cmd_toggle_status_bar()
    assert win.announcements[-1] == "Status bar shown"


# --------------------------------------------------------------------------- #
# Text size
# --------------------------------------------------------------------------- #


def test_zoom_in_and_out_move_one_point_at_a_time(lite_window):
    win = lite_window("hello")
    win.app.settings.font_size = 12
    win.cmd_zoom_in()
    assert win.app.settings.font_size == 13
    assert win.announcements[-1] == "13 point"
    win.cmd_zoom_out()
    assert win.app.settings.font_size == 12
    assert win.announcements[-1] == "12 point"


def test_zoom_reset_goes_to_the_default_whatever_it_was(lite_window):
    from quill.apps.lite_window_view import _DEFAULT_POINTS

    win = lite_window("hello")
    win.app.settings.font_size = 30
    win.cmd_zoom_reset()
    assert win.app.settings.font_size == _DEFAULT_POINTS
    assert win.announcements[-1] == f"{_DEFAULT_POINTS} point"


def test_zoom_out_stops_at_the_smallest_legible_size(lite_window):
    """The clamp is ``Settings.normalized``, and the announcement has to read the
    clamped value -- saying "3 point" while the font stayed at 6 is a lie the
    user cannot see through."""
    win = lite_window("hello")
    win.app.settings.font_size = 6
    for _ in range(6):
        win.cmd_zoom_out()
    size = win.app.settings.font_size
    assert size >= 6
    assert win.announcements[-1] == f"{size} point"


def test_zoom_in_stops_at_the_largest_size(lite_window):
    win = lite_window("hello")
    win.app.settings.font_size = 70
    for _ in range(10):
        win.cmd_zoom_in()
    size = win.app.settings.font_size
    assert size <= 72
    assert win.announcements[-1] == f"{size} point"


# --------------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------------- #


def test_statistics_speaks_the_three_numbers(lite_window):
    win = lite_window("one two three\nfour five\n")
    win.cmd_statistics()
    said = win.announcements[-1]
    assert "5 words" in said
    assert "characters" in said and "lines" in said


def test_statistics_groups_thousands_so_they_can_be_heard(lite_window):
    """A synthesiser reads 12345 as five digits; 12,345 it reads as a number."""
    win = lite_window("word " * 2000)
    win.cmd_statistics()
    assert "2,000 words" in win.announcements[-1]


def test_statistics_on_an_empty_document_says_zero_rather_than_nothing(lite_window):
    win = lite_window("")
    win.cmd_statistics()
    assert "0 words" in win.announcements[-1]


# --------------------------------------------------------------------------- #
# F6
# --------------------------------------------------------------------------- #


def test_focus_status_bar_moves_there_when_the_bar_is_shown(lite_window):
    win = lite_window("hello")
    win.app.settings.show_status_bar = True
    win.cmd_focus_status_bar()
    assert win.status_bar_focused == 1


def test_focus_status_bar_on_a_hidden_bar_says_so_and_how_to_undo_it(lite_window):
    """A key that does nothing reads as a broken key.

    The bar being hidden is the one state where F6 has nowhere to go, so the
    refusal has to name the key that brings it back -- otherwise the listener's
    only evidence is silence.
    """
    win = lite_window("hello")
    win.app.settings.show_status_bar = False
    win.cmd_focus_status_bar()
    assert win.status_bar_focused == 0
    assert "hidden" in win.announcements[-1]
    assert "Alt+Shift+B" in win.announcements[-1]


# --------------------------------------------------------------------------- #
# Quiet mode
# --------------------------------------------------------------------------- #


@pytest.fixture
def isolated_quill_settings(tmp_path, monkeypatch):
    """Quiet mode writes QUILL's *shared* settings, so the test needs its own.

    The point of the command is that silencing one editor silences the family,
    which means it reaches past QuillLite's settings file into the real one --
    exactly the reach a test must not make on the developer's machine.
    """
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    import quill.core.paths as paths

    # The env var is only honoured under _DEV_BUILD, which tests/conftest.py
    # sets for the session; the cache in front of it is what would otherwise
    # hand back a path resolved before the monkeypatch.
    clear = getattr(paths.app_data_dir, "cache_clear", None)
    if callable(clear):
        clear()
    return tmp_path


def test_toggle_quiet_mode_flips_the_shared_sound_setting(lite_window, isolated_quill_settings):
    from quill.core.settings import load_settings

    win = lite_window("hello")
    before = bool(getattr(load_settings(), "sound_enabled", True))
    win.cmd_toggle_quiet_mode()
    assert bool(getattr(load_settings(), "sound_enabled", True)) is not before


def test_toggle_quiet_mode_confirms_in_words_never_a_tone(lite_window, isolated_quill_settings):
    """The one command whose confirmation must not be an earcon.

    A cue saying "sounds are off" is the one sound that ignores the
    instruction, and a cue saying "sounds are on" arrives before the user can
    know it was allowed to.
    """
    win = lite_window("hello")
    cues_before = list(win.cues)
    win.cmd_toggle_quiet_mode()
    assert win.announcements, "the outcome has to be spoken"
    assert win.cues == cues_before
