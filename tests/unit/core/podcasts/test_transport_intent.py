"""The Play button answers "play what?" -- in its label (reported 2026-09-30).

The button said "Play" and nothing else, so somebody hearing it had been told the
verb and none of the object. The first fix put the object in the accessible name,
which wxMSW never reads on a button, so it was inaudible (qc.md 6b, item 1). These
pin the second: Cast's reading of the shared :mod:`quill.core.transport_button`.
"""

from __future__ import annotations

from quill.core.podcasts import transport_intent as ti

# -- the visible label carries the object ------------------------------------ #


def test_resume_and_play_are_different_promises() -> None:
    """Play starts something at the beginning; Resume returns to a place. A
    listener who hears Resume knows their position survived."""
    assert ti.button_label(ti.STOPPED, selection="The Daily", can_play_selection=True) == (
        "Pla&y The Daily"
    )
    assert ti.button_label(ti.PAUSED, show_title="The Daily") == "Re&sume The Daily"
    assert ti.button_label(ti.PLAYING, show_title="The Daily") == "Pau&se The Daily"


def test_loading_is_pausable_so_the_label_says_pause() -> None:
    assert ti.button_label(ti.LOADING, show_title="The Daily").startswith("Pau&se")


def test_every_label_carries_an_access_key_the_menu_bar_does_not_own() -> None:
    """Pla&y, Pau&se, Re&sume: Y and S. The Podcasts menu owns P -- which the
    original ``&Pause`` reclaimed the moment anything played (6b, item 2)."""
    for label in ti.label_samples():
        mnemonic = label.replace("&&", "").split("&", 1)[1][0].upper()
        assert mnemonic in {"Y", "S"}, label


def test_the_label_and_the_sentence_come_from_one_reading() -> None:
    kwargs = {"show_title": "The Daily", "episode_title": "Thursday's episode"}
    face = ti.button_face(ti.PLAYING, **kwargs)
    assert face.label == ti.button_label(ti.PLAYING, **kwargs)
    assert face.spoken == ti.transport_name(ti.PLAYING, **kwargs)


# -- the sentence ---------------------------------------------------------------- #


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
    assert ti.button_label(ti.STOPPED, selection="News") == "Pla&y -- nothing selected"


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
