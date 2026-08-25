"""Play becomes Stop on the ACB Media Schedule, including while it connects.

Reported 2026-08-25: *"the play button label does not become stop when Play is
pressed on the community screen."* Three separate reasons, all of them true at
once:

1. ``playing_stream_name`` asked ``RUNNING_STATES``, which is PLAYING and
   BUFFERING only -- so for the second or two a stream spends CONNECTING it
   answered "nothing is on".
2. ``calendar_verbs._play`` re-faced the window in its *stop* branch and not
   its play branch, so nothing re-read the label after starting anything.
3. Nothing re-faced it when CONNECTING became PLAYING either, because that
   arrives on a background thread and the window had no hook for it.

Fix one alone would still leave the button reading Play for the whole
broadcast, which is why all three are covered here.
"""

from __future__ import annotations

from pathlib import Path

from quill.ui.radio.playback_state import RadioPlayerState

_UI = Path(__file__).resolve().parents[3] / "quill" / "ui" / "radio"
_VERBS = (_UI / "calendar_verbs.py").read_text(encoding="utf-8")
_DIALOG = (_UI / "calendar_dialog.py").read_text(encoding="utf-8")
_APP = (Path(__file__).resolve().parents[3] / "quill" / "apps" / "radio.py").read_text(
    encoding="utf-8"
)


def _host(phase: RadioPlayerState, name: str = "ACB Media 5"):
    station = type("S", (), {"name": name})()
    state = type("St", (), {"state": phase, "station": station})()
    return type("H", (), {"_radio_controller": type("C", (), {"state": state})()})()


def test_a_connecting_stream_already_counts_as_on() -> None:
    """The whole of the reported bug: Play is pressed, the stream is
    CONNECTING, and the window decided nothing was playing."""
    from quill.ui.radio import calendar_verbs

    assert calendar_verbs.playing_stream_name(_host(RadioPlayerState.CONNECTING)) == "ACB Media 5"


def test_every_on_the_air_state_counts_and_the_off_ones_do_not() -> None:
    from quill.ui.radio import calendar_verbs

    for phase in (
        RadioPlayerState.CONNECTING,
        RadioPlayerState.BUFFERING,
        RadioPlayerState.PLAYING,
        RadioPlayerState.RECONNECTING,
        RadioPlayerState.PAUSED,
    ):
        assert calendar_verbs.playing_stream_name(_host(phase)), phase
    for phase in (RadioPlayerState.STOPPED, RadioPlayerState.ERROR):
        assert calendar_verbs.playing_stream_name(_host(phase)) == "", phase


def test_the_label_and_the_action_are_still_one_answer() -> None:
    """``_play`` asks the same function the button label asks.

    A button that says Stop and restarts is worse than one that only ever said
    Play, so widening the state set must widen both or neither.
    """
    assert _VERBS.count("playing_stream_name(host)") >= 1
    assert "ACTIVE_STATES | {RadioPlayerState.PAUSED}" in _VERBS
    imports = [line for line in _VERBS.splitlines() if "playback_state import" in line]
    assert imports and not [line for line in imports if "RUNNING_STATES" in line], imports


def test_the_window_re_faces_after_every_verb_not_just_stop() -> None:
    invoke = _DIALOG[_DIALOG.index("    def _invoke") :]
    invoke = invoke[: invoke.index("\n    # --")]

    assert "calendar_verbs.run(" in invoke
    assert "self._sync()" in invoke
    # The stop branch's private copy is gone: one place, or Play is the one
    # that gets forgotten again.
    assert "window_sync" not in _VERBS


def test_the_open_schedule_follows_state_changes_it_did_not_cause() -> None:
    """CONNECTING becomes PLAYING on a background thread, and a stream can also
    stall, reconnect or die with nobody pressing anything."""
    assert "def refresh_open(" in _DIALOG
    assert "calendar_dialog.refresh_open(self)" in _APP


def test_refreshing_with_no_schedule_open_is_a_no_op() -> None:
    from quill.ui.radio import calendar_dialog

    calendar_dialog.refresh_open()  # must not raise
    calendar_dialog.refresh_open(object())
