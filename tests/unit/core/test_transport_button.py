"""The transport button says its verb and its object, in the label.

Two reports, one defect. Cast, 2026-09-30: "if I tab I see play, play what?"
Radio, 2026-10-01: "The stop button now always shows up in the app and doesn't
change to a play button when stopped." A button that says only its verb has
told a screen-reader user half of what they need, and a button that says Stop
while nothing is playing is a dead control wearing a live label.

The first fix put the object in the accessible name, which wxMSW never reads
on a button, so it was inaudible. These pin the second fix: the object is in
the *label*, fitted to a budget, with its ampersands escaped.
"""

from __future__ import annotations

from quill.core import transport_button as tb

# -- the object is in the label ----------------------------------------------- #


def test_stopped_with_a_playable_selection_offers_to_play_it_by_name() -> None:
    got = tb.face(tb.STOPPED, selection="The Daily", can_play_selection=True)
    assert got.label == "Pla&y The Daily"
    assert got.spoken == "Play The Daily"
    assert got.verb == "play"


def test_playing_names_what_would_be_paused_show_and_episode() -> None:
    got = tb.face(tb.PLAYING, object_name="The Daily", episode_title="Thursday's episode")
    assert got.label == "Pau&se The Daily, Thursday's episode"
    assert got.spoken == "Pause The Daily, Thursday's episode"
    assert got.verb == "pause"


def test_loading_counts_as_playing_so_the_button_can_stop_a_stream_opening() -> None:
    assert tb.face(tb.LOADING, object_name="KSPN", active_verb="stop").label == "S&top KSPN"


def test_paused_offers_resume_by_name_in_both_apps() -> None:
    cast = tb.face(tb.PAUSED, object_name="The Daily", episode_title="Episode 4")
    radio = tb.face(
        tb.PAUSED, object_name="Episode 4", active_verb="stop", mnemonics=tb.RADIO_MNEMONICS
    )
    assert cast.label == "Re&sume The Daily, Episode 4"
    assert radio.label == "Res&ume Episode 4"
    assert cast.verb == radio.verb == "resume"


def test_radio_main_window_stops_rather_than_pauses_while_something_plays() -> None:
    """One button that starts and ends: live radio cannot be paused."""
    got = tb.face(tb.PLAYING, object_name="KSPN", active_verb="stop", mnemonics=tb.RADIO_MNEMONICS)
    assert got.label == "S&top KSPN"
    assert got.spoken == "Stop KSPN"
    assert got.verb == "stop"


def test_a_half_known_episode_still_names_the_half_it_has() -> None:
    assert tb.face(tb.PLAYING, object_name="The Daily").label == "Pau&se The Daily"
    assert tb.face(tb.PLAYING, episode_title="Episode 4").label == "Pau&se Episode 4"
    assert tb.face(tb.PLAYING).label == "Pau&se"
    assert tb.face(tb.PLAYING).spoken == "Pause"


# -- the one dead state ------------------------------------------------------- #


def test_a_folder_under_the_cursor_is_never_described_as_playable() -> None:
    got = tb.face(tb.STOPPED, selection="News", can_play_selection=False)
    assert "News" not in got.label
    assert got.label == "Pla&y -- nothing selected"
    assert got.verb == "none"


def test_the_dead_state_says_what_to_do_instead_in_the_apps_own_words() -> None:
    got = tb.face(tb.STOPPED, dead_hint="choose a station in Favorites first")
    assert got.spoken == (
        "Play. Nothing is selected that can be played -- choose a station in Favorites first"
    )


def test_the_dead_state_is_still_enabled_so_it_can_explain_itself() -> None:
    """A dimmed button cannot say why it is dim (principle 11.2)."""
    assert tb.face(tb.STOPPED).enabled


# -- fitting the label -------------------------------------------------------- #


def _visible(label: str) -> str:
    return label.replace("&&", "\x00").replace("&", "").replace("\x00", "&")


def test_a_long_title_is_elided_so_the_row_never_reflows() -> None:
    title = "An episode title so long that it would push every button after it off the window"
    got = tb.face(tb.PLAYING, object_name="Show", episode_title=title)
    assert len(_visible(got.label)) <= tb.MAX_LABEL_CHARS
    assert got.label.endswith("...")
    assert got.spoken.endswith("off the window")  # the sentence is never cut


def test_the_verb_always_survives_elision() -> None:
    got = tb.face(tb.STOPPED, selection="x" * 500, can_play_selection=True)
    assert got.label.startswith("Pla&y ")


def test_an_ampersand_in_a_title_cannot_become_an_access_key() -> None:
    got = tb.face(tb.STOPPED, selection="Rock & Roll Hour", can_play_selection=True)
    assert got.label == "Pla&y Rock && Roll Hour"
    real_mnemonics = got.label.count("&") - 2 * got.label.count("&&")
    assert real_mnemonics == 1
    assert got.spoken == "Play Rock & Roll Hour"


def test_whitespace_in_a_title_is_normalised() -> None:
    got = tb.face(tb.STOPPED, selection="  The   Daily\n", can_play_selection=True)
    assert got.label == "Pla&y The Daily"


# -- what the gate reads ------------------------------------------------------ #


def _mnemonic(label: str) -> str:
    return label.replace("&&", "").split("&", 1)[1][0].upper()


def test_label_samples_cover_every_verb_the_button_can_show() -> None:
    cast = tb.label_samples(tb.CAST_MNEMONICS, active_verb="pause")
    radio = tb.label_samples(tb.RADIO_MNEMONICS, active_verb="stop")
    assert {_mnemonic(s) for s in cast} == {"Y", "S"}
    assert {_mnemonic(s) for s in radio} == {"L", "T", "U"}
    assert all("Sample" in s or "nothing selected" in s for s in cast + radio)


def test_cast_mnemonics_stay_off_the_cast_menu_bar() -> None:
    """P, E, D, V, Q, W, H are the Podcasts, Episode, Downloads, View, Quillins,
    Window and Help menus. The live check is GATE-15; this is the table it reads."""
    bar = set("PEDVQWH")
    for label in tb.label_samples(tb.CAST_MNEMONICS, active_verb="pause"):
        assert _mnemonic(label) not in bar, label


def test_radio_mnemonics_stay_off_the_radio_menu_bar_and_its_own_row() -> None:
    """Station, Edit, View, Playback, Audio, Video (D), Record, Community,
    QuillVille, Quillins (N), Window, Help; and on the row, Favorites (F), Volume
    (O) and Mute (M). The live check is tests/unit/ui/test_button_mnemonics.py."""
    bar = set("ACDEHNPQRSVW") | {"F", "O", "M"}
    for label in tb.label_samples(tb.RADIO_MNEMONICS, active_verb="stop"):
        assert _mnemonic(label) not in bar, label
