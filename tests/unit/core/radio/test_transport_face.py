"""One control that starts and ends, one that pauses.

The report (2026-08-25): *"can we get the play button to convert to a stop
button instead of two buttons"* -- and then, a minute later, the part that
makes it interesting: *"we need a way to handle stop in the cases of podcasts
along with play and pause/stop... as well as local or offline content"*.

Live radio has two verbs and a podcast has three, and the surfaces were solving
that by showing Play/Pause beside Stop everywhere -- so on a live station one
of the two was always a lie (a live stream cannot be paused; Play/Pause meant
Play/Restart). These pin the answer: the first control always starts and always
ends, the second owns pause and *says* why it is dim on a station.
"""

from __future__ import annotations

from quill.core.radio import transport_commands as tc


def test_the_primary_control_says_play_when_nothing_is_on() -> None:
    face = tc.primary_face(playing=False, paused=False)

    assert face.plain == "Play"
    assert face.command_id == tc.PLAY_PAUSE
    assert face.enabled


def test_the_primary_control_says_stop_for_live_and_for_a_recording_alike() -> None:
    # The whole point: one promise, whatever is playing. A listener does not
    # have to know what kind of thing is on to know how to end it.
    for paused in (False, True):
        face = tc.primary_face(playing=not paused, paused=paused)
        assert face.plain == "Stop", paused
        assert face.command_id == tc.STOP, paused


def test_the_primary_mnemonic_does_not_move_when_the_label_does() -> None:
    """Alt+P presses it in both states.

    A mnemonic that moves is a mnemonic nobody can learn -- and this is the one
    control whose label changes underneath the listener.
    """
    play = tc.primary_face(playing=False)
    stop = tc.primary_face(playing=True)

    assert play.label.split("&", 1)[1][0].lower() == "p"
    assert stop.label.split("&", 1)[1][0].lower() == "p"


def test_pause_is_dimmed_on_live_radio_and_says_why_rather_than_vanishing() -> None:
    face = tc.pause_face(playing=True, bounded=False, paused=False)

    assert face.plain == "Pause"
    assert not face.enabled
    assert "live radio" in face.reason
    # And it points at the control that *can* end a station, rather than
    # leaving "you cannot do that" as the whole answer (11.2).
    assert "Stop" in face.reason


def test_pause_works_for_a_podcast_a_recording_or_a_local_file() -> None:
    face = tc.pause_face(playing=True, bounded=True, paused=False)

    assert face.plain == "Pause"
    assert face.enabled
    assert face.command_id == tc.PLAY_PAUSE


def test_a_paused_recording_offers_resume_and_still_offers_stop() -> None:
    """Paused is the state where three verbs really are needed at once."""
    primary = tc.primary_face(playing=False, paused=True)
    pause = tc.pause_face(playing=False, bounded=True, paused=True)

    assert primary.plain == "Stop"
    assert pause.plain == "Resume"
    assert pause.enabled


def test_pause_and_resume_share_a_mnemonic_too() -> None:
    pause = tc.pause_face(playing=True, bounded=True, paused=False)
    resume = tc.pause_face(playing=False, bounded=True, paused=True)

    assert pause.label.split("&", 1)[1][0].lower() == "s"
    assert resume.label.split("&", 1)[1][0].lower() == "s"


def test_pause_with_nothing_playing_is_dim_and_honest() -> None:
    face = tc.pause_face(playing=False, bounded=False, paused=False)

    assert not face.enabled
    assert face.reason == "nothing is playing"


def test_the_two_controls_never_claim_the_same_mnemonic() -> None:
    """They sit next to each other; a repeated mnemonic presses neither."""
    for playing, bounded, paused in (
        (False, False, False),
        (True, False, False),
        (True, True, False),
        (False, True, True),
    ):
        primary = tc.primary_face(playing=playing, paused=paused)
        pause = tc.pause_face(playing=playing, bounded=bounded, paused=paused)
        keys = {
            primary.label.split("&", 1)[1][0].lower(),
            pause.label.split("&", 1)[1][0].lower(),
        }
        assert len(keys) == 2, (playing, bounded, paused, primary.label, pause.label)


def test_every_face_names_a_verb_the_table_can_actually_run() -> None:
    """No new commands, no new keys: this is a re-facing, not a feature.

    Ctrl+P is still play/pause and Ctrl+. is still stop, in both apps, so a
    keymap somebody has rebound is untouched.
    """
    for playing, bounded, paused in (
        (False, False, False),
        (True, True, False),
        (True, False, False),
    ):
        for face in (
            tc.primary_face(playing=playing, paused=paused),
            tc.pause_face(playing=playing, bounded=bounded, paused=paused),
        ):
            assert tc.command(face.command_id) is not None, face.label
            assert face.key == tc.command(face.command_id).key
