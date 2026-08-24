"""The status line has to stop saying "playing" through dead air.

Two failures these pin.

**A stalled stream said it was playing.** mpv reports ``paused-for-cache`` when
a live stream runs out of audio; Quill Radio announced "Buffering..." and left
the playback state at PLAYING, so the focusable status bar's Now Playing cell
and the tray tooltip both went on claiming playback through silence -- the one
thing a listener can already tell is false.

**A reconnect said nothing at all.** ``live_reconnect`` composes "Reconnecting
to X. Attempt 1 of 3." and its docstring promises each attempt is announced
with its number. The sentence went into ``RadioPlaybackState.message``, which
nothing spoke and which the status text ignored, so what a listener got was one
earcon followed by up to twenty-two seconds indistinguishable from a hang.

Tested against the pure wording module rather than a controller: the whole point
of extracting it was that a test of the sentence should not have to build a
window to read it.
"""

from __future__ import annotations

from quill.ui.radio.playback_status import status_text, transition_announcement

# -- one line per state --------------------------------------------------------


def test_stopped_says_stopped_whatever_station_is_remembered() -> None:
    assert status_text(state="STOPPED", station="WQXR") == "Radio: stopped"


def test_no_station_reads_as_stopped_in_every_state() -> None:
    # A state with no station is not a state anybody can act on.
    for state in ("PLAYING", "CONNECTING", "BUFFERING", "RECONNECTING", "ERROR"):
        assert status_text(state=state, station="") == "Radio: stopped"


def test_connecting_names_the_station_it_is_reaching_for() -> None:
    assert status_text(state="CONNECTING", station="WQXR") == "Radio: connecting to WQXR..."


def test_buffering_is_its_own_word_not_playing() -> None:
    # The regression this whole change exists for.
    assert status_text(state="BUFFERING", station="WQXR") == "Radio: buffering WQXR..."


def test_buffering_is_not_the_same_line_as_connecting() -> None:
    # "We have not started" and "we started and ran out" are different facts.
    assert status_text(state="BUFFERING", station="WQXR") != status_text(
        state="CONNECTING", station="WQXR"
    )


def test_playing_says_so_and_says_when_it_is_muted() -> None:
    assert status_text(state="PLAYING", station="WQXR") == "Radio: playing WQXR"
    assert status_text(state="PLAYING", station="WQXR", muted=True) == "Radio: playing WQXR (muted)"


def test_paused_reads_as_paused() -> None:
    assert status_text(state="PAUSED", station="WQXR") == "Radio: paused - WQXR"


def test_an_error_carries_the_reason_it_was_given() -> None:
    line = status_text(state="ERROR", station="WQXR", message="That stream could not be opened.")
    assert line == "Radio: could not play WQXR - That stream could not be opened."


# -- reconnecting --------------------------------------------------------------


def test_reconnecting_renders_the_sentence_live_reconnect_already_wrote() -> None:
    # Rather than composing a second copy that drifts from it by next release.
    line = status_text(
        state="RECONNECTING",
        station="KFI AM 640",
        message="Reconnecting to KFI AM 640. Attempt 2 of 3.",
    )
    assert line == "Radio: Reconnecting to KFI AM 640. Attempt 2 of 3."


def test_reconnecting_without_a_message_still_says_which_station() -> None:
    assert status_text(state="RECONNECTING", station="KFI") == "Radio: reconnecting to KFI..."


# -- robustness ----------------------------------------------------------------


def test_an_unknown_state_answers_the_prefix_rather_than_raising() -> None:
    # A status line is the last thing that should be able to take the window
    # down; a new enum member that arrives before its branch is a wording bug.
    assert status_text(state="TELEPORTING", station="WQXR") == "Radio"


def test_surrounding_whitespace_in_a_station_name_does_not_reach_the_line() -> None:
    assert status_text(state="PLAYING", station="  WQXR  ") == "Radio: playing WQXR"


# -- what gets spoken ----------------------------------------------------------


def test_a_reconnect_attempt_is_spoken() -> None:
    words = transition_announcement(
        state="RECONNECTING",
        message="Reconnecting to KFI AM 640. Attempt 1 of 3.",
        previous_state="PLAYING",
        previous_message="",
    )
    assert words == "Reconnecting to KFI AM 640. Attempt 1 of 3."


def test_each_attempt_is_news_and_is_spoken_again() -> None:
    words = transition_announcement(
        state="RECONNECTING",
        message="Reconnecting to KFI AM 640. Attempt 2 of 3.",
        previous_state="RECONNECTING",
        previous_message="Reconnecting to KFI AM 640. Attempt 1 of 3.",
    )
    assert words


def test_re_entering_the_same_attempt_is_not_said_twice() -> None:
    words = transition_announcement(
        state="RECONNECTING",
        message="Reconnecting to KFI AM 640. Attempt 1 of 3.",
        previous_state="RECONNECTING",
        previous_message="Reconnecting to KFI AM 640. Attempt 1 of 3.",
    )
    assert words == ""


def test_ordinary_playback_transitions_stay_silent() -> None:
    # They are cued with earcons on purpose. A radio that says "playing" every
    # time it starts is a radio nobody can write a document beside. ERROR is
    # NOT in this list -- see below.
    for state in ("PLAYING", "BUFFERING", "CONNECTING", "STOPPED", "PAUSED"):
        assert (
            transition_announcement(
                state=state, message="anything", previous_state="STOPPED", previous_message=""
            )
            == ""
        )


def test_a_failure_is_spoken_with_its_reason() -> None:
    # Reported 2026-08-23: "it just freezes: Radio: connecting to <url>...".
    # It had not frozen -- the play had failed, with a perfectly good reason,
    # into a status cell nobody was told to go and read.
    words = transition_announcement(
        state="ERROR",
        message="That YouTube link could not be opened.",
        previous_state="CONNECTING",
        previous_message="",
    )
    assert words == "Could not play. That YouTube link could not be opened."


def test_a_failure_without_a_reason_stays_silent() -> None:
    # The earcon already said something went wrong; "Could not play." on its
    # own adds nothing a listener can act on.
    assert (
        transition_announcement(
            state="ERROR", message="", previous_state="CONNECTING", previous_message=""
        )
        == ""
    )


def test_the_same_failure_is_not_said_twice() -> None:
    assert (
        transition_announcement(
            state="ERROR",
            message="No audio stream.",
            previous_state="ERROR",
            previous_message="No audio stream.",
        )
        == ""
    )
