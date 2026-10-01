"""The Play button answers "play what?" (reported 2026-09-30).

The button said "Play" and nothing else, so somebody hearing it had been told the
verb and none of the object. These cases are the four states it can be in, and the
one that matters most is the last: stopped with nothing playable, where the button
genuinely does nothing and used to look identical to the state where it would start
an episode.
"""

from __future__ import annotations

from quill.core.podcasts import transport_intent as ti

# -- the visible label ------------------------------------------------------- #


def test_resume_and_play_are_different_promises() -> None:
    """Play starts something at the beginning; Resume returns to a place. A
    listener who hears Resume knows their position survived."""
    assert ti.button_label(ti.STOPPED) == "&Play"
    assert ti.button_label(ti.PAUSED) == "&Resume"
    assert ti.button_label(ti.PLAYING) == "&Pause"


def test_every_label_carries_an_access_key() -> None:
    for state in (ti.STOPPED, ti.PAUSED, ti.PLAYING):
        assert "&" in ti.button_label(state)


# -- the accessible name ----------------------------------------------------- #


def test_playing_names_what_would_be_paused() -> None:
    said = ti.transport_name(ti.PLAYING, show_title="The Daily", episode_title="Thursday's episode")
    assert said == "Pause The Daily, Thursday's episode"


def test_paused_names_what_would_be_resumed() -> None:
    said = ti.transport_name(ti.PAUSED, show_title="The Daily", episode_title="Episode 4")
    assert said == "Resume The Daily, Episode 4"


def test_a_half_known_episode_still_names_the_half_it_has() -> None:
    """A feed with no episode title, or a loading state before the title has
    arrived, should still say the show rather than falling back to the bare verb."""
    assert ti.transport_name(ti.PLAYING, show_title="The Daily") == "Pause The Daily"
    assert ti.transport_name(ti.PLAYING, episode_title="Episode 4") == "Pause Episode 4"
    assert ti.transport_name(ti.PLAYING) == "Pause"


def test_stopped_with_a_playable_selection_names_it() -> None:
    said = ti.transport_name(ti.STOPPED, selection="The Daily", can_play_selection=True)
    assert said == "Play The Daily"


def test_a_folder_under_the_cursor_is_never_described_as_playable() -> None:
    """A button announcing that it would play "News" when News is a folder has
    lied about the one thing it was asked."""
    said = ti.transport_name(ti.STOPPED, selection="News", can_play_selection=False)
    assert "Play News" not in said
    assert "Nothing is selected that can be played" in said


def test_the_one_dead_state_says_what_to_do_instead() -> None:
    """This was the report. A button that does nothing and says only "Play" is
    indistinguishable from a broken one."""
    said = ti.transport_name(ti.STOPPED)
    assert "choose a podcast or an episode in the library" in said
    assert "Continue Listening" in said


def test_the_name_describes_the_effect_not_the_player_state() -> None:
    """A button named after the state is a readout wearing a button's clothes --
    the same mistake Radio's status bar was redesigned to stop making."""
    for state in (ti.PLAYING, ti.PAUSED, ti.STOPPED):
        said = ti.transport_name(state, show_title="The Daily", episode_title="Episode 4")
        assert not said.lower().startswith(("playing", "paused", "stopped"))
