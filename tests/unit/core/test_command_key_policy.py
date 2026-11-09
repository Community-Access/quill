"""The Command Key's policy: what it runs, asks, refuses and says (command-key.md 6, 8, 10)."""

from __future__ import annotations

from pathlib import Path

import pytest
from command_key_fakes import FakeHost, host_for

from quill.core.command_catalogue import row
from quill.core.command_catalogue.args import read_args
from quill.core.command_catalogue.policy import (
    ASK_MESSAGE,
    NOT_HERE_MESSAGE,
    CommandKeySession,
    Outcome,
    Refusal,
    decide,
)
from quill.core.command_catalogue.resolver import Candidate


def _session(host: FakeHost) -> CommandKeySession:
    return CommandKeySession(host)


# -- running ------------------------------------------------------------------


def test_a_confident_safe_command_runs_through_the_registry() -> None:
    host = host_for("radio")
    decision = _session(host).submit("turn it down a bit")
    assert decision.outcome is Outcome.RUN and decision.command_id == "radio.volume_down"
    assert host.registry.ran == ["radio.volume_down"]
    assert host.questions == []
    # Volume Down says its own new level, so the box says nothing after it.
    assert host.spoken == []


def test_a_lot_louder_runs_three_steps() -> None:
    host = host_for("radio")
    _session(host).submit("a lot louder")
    assert host.registry.ran == ["radio.volume_up"] * 3
    assert host.registry.repeats == [3]


def test_a_command_that_does_not_speak_for_itself_gets_one_line() -> None:
    host = host_for("quill")
    _session(host).submit("make this bold")
    assert host.registry.ran == ["format.bold"]
    assert host.spoken == ["Bold."]


def test_a_dialog_command_says_nothing_because_the_reader_says_the_dialog() -> None:
    host = host_for("quill")
    _session(host).submit("check my spelling")
    assert host.registry.ran == ["tools.spell_check_dialog"]
    assert host.spoken == []


def test_arguments_go_to_the_app_when_it_takes_them() -> None:
    got: list[tuple[str, dict[str, object]]] = []

    def take(spec, args):  # type: ignore[no-untyped-def]
        got.append((spec.id, dict(args)))
        return True

    host = host_for("radio", with_args=take)
    _session(host).submit("play favourite 3")
    assert got == [("radio.play_favorite", {"number": 3})]
    assert host.registry.ran == []


def test_arguments_the_app_does_not_take_fall_back_to_a_plain_run() -> None:
    host = host_for("radio")
    _session(host).submit("skip back 30 seconds")
    assert host.registry.ran == ["radio.rewind"]


# -- confirming ---------------------------------------------------------------


def test_a_confirm_command_asks_first_and_runs_on_yes() -> None:
    host = host_for("radio")
    _session(host).submit("stop all the recordings")
    assert host.questions == ["Stop Every Recording? Enter to go ahead, Escape to cancel."]
    assert host.registry.ran == ["radio.stop_all_recordings"]


def test_a_confirm_command_does_nothing_on_no() -> None:
    host = host_for("quill", confirm_answer=False)
    _session(host).submit("close this document")
    assert host.questions and host.registry.ran == []


def test_a_command_that_became_unavailable_while_confirming_does_not_run() -> None:
    host = host_for("quill")
    original = host.confirm

    def confirm_then_disable(question: str) -> bool:
        host.registry.reasons["file.close_document"] = "There is no document to close."
        return original(question)

    host.confirm = confirm_then_disable  # type: ignore[method-assign]
    _session(host).submit("close this document")
    assert host.registry.ran == []
    assert host.spoken == ["There is no document to close."]


# -- did you mean ----------------------------------------------------------------


def test_a_split_decision_asks_which_and_runs_the_pick() -> None:
    host = host_for("quill", choose_index=1)
    decision = _session(host).submit("headings")
    assert decision.outcome is Outcome.CHOOSE
    offered = host.offered_choices[0]
    assert "navigate.next_heading" in offered and len(offered) == 3
    assert host.registry.ran == [offered[1]]


def test_escape_from_did_you_mean_runs_nothing() -> None:
    host = host_for("quill", choose_index=None)
    _session(host).submit("headings")
    assert host.registry.ran == []


def test_a_did_you_mean_pick_of_a_confirm_command_still_confirms() -> None:
    host = host_for("radio", confirm_answer=False)
    session = _session(host)
    spec = row("radio.record_toggle", "radio")
    assert spec is not None
    assert session.run_candidate(Candidate(spec)) is False
    assert host.questions and host.registry.ran == []


# -- refusing -------------------------------------------------------------------


def test_nonsense_is_refused_with_the_hint() -> None:
    host = host_for("radio")
    decision = _session(host).submit("flibbertigibbet")
    assert decision.refusal is Refusal.NOT_HERE
    assert host.spoken == [NOT_HERE_MESSAGE]


def test_a_question_for_the_world_goes_to_ask() -> None:
    host = host_for("quill")
    decision = _session(host).submit("write me a poem")
    assert decision.refusal is Refusal.ASK and host.spoken == [ASK_MESSAGE]
    assert host.registry.ran == []


def test_delete_is_refused_and_points_at_the_window() -> None:
    host = host_for("radio")
    decision = _session(host).submit("delete all my recordings")
    assert decision.refusal is Refusal.NEVER
    assert host.spoken == ["Not from a sentence: it's in Recordings."]
    assert host.registry.ran == []


def test_a_never_row_is_refused_with_where_it_is() -> None:
    host = host_for("quill")
    decision = _session(host).submit("quit")
    assert decision.refusal is Refusal.NEVER
    assert host.spoken == ["Not from a sentence: it's in File, Exit."]
    assert host.registry.ran == []


def test_a_disabled_command_says_the_probes_reason_and_is_not_swapped() -> None:
    host = host_for(
        "quill", disabled={"format.bold": "Bold needs a rich document. This one is plain text."}
    )
    decision = _session(host).submit("make this bold")
    assert decision.refusal is Refusal.DISABLED
    assert host.spoken == ["Bold needs a rich document. This one is plain text."]
    assert host.registry.ran == []


def test_another_apps_command_says_which_app() -> None:
    radio_play = row("radio.play_pause", "radio")
    assert radio_play is not None
    host = host_for("quill", other_apps=(("Quill Radio", radio_play),))
    decision = _session(host).submit("start the radio")
    assert decision.refusal is Refusal.OTHER_APP
    assert host.spoken == ["That's in Quill Radio."]


def test_clear_bookmarks_is_not_refused_for_saying_clear() -> None:
    host = host_for("quill")
    _session(host).submit("clear all my bookmarks")
    assert host.registry.ran == ["navigate.clear_numbered_bookmarks"]
    assert host.questions  # it is CONFIRM


# -- the shared rows -------------------------------------------------------------


@pytest.mark.parametrize(
    "text", ["what can I say", "help", "What can I ask?", "what can i do here"]
)
def test_what_can_i_say_opens_the_help_list(text: str) -> None:
    host = host_for("radio")
    assert _session(host).submit(text).outcome is Outcome.HELP
    assert host.help_filters == [""]


def test_what_can_i_say_about_filters_the_list() -> None:
    host = host_for("quill")
    _session(host).submit("what can I say about bookmarks")
    assert host.help_filters == ["bookmarks"]


def test_running_from_the_help_list_goes_through_the_same_checks() -> None:
    host = host_for("radio", help_pick="radio.stop_all_recordings", confirm_answer=False)
    _session(host).submit("what can I say")
    assert host.questions and host.registry.ran == []


def test_dictation_help_is_its_own_list() -> None:
    host = host_for("quill")
    assert _session(host).submit("what can I say while dictating").outcome is Outcome.DICTATION_HELP
    assert host.dictation_help_shown == 1 and host.help_filters == []


def test_undo_that_runs_the_opposite_of_the_last_step() -> None:
    host = host_for("radio")
    session = _session(host)
    session.submit("a lot louder")
    session.submit("undo that")
    assert host.registry.ran == ["radio.volume_up"] * 3 + ["radio.volume_down"] * 3


def test_undo_that_throws_a_toggle_back() -> None:
    host = host_for("radio")
    session = _session(host)
    session.submit("mute")
    session.submit("undo that")
    assert host.registry.ran == ["radio.mute_toggle", "radio.mute_toggle"]


def test_undo_that_uses_the_apps_undo_for_an_action() -> None:
    host = host_for("quill")
    session = _session(host)
    session.submit("make this all capitals")
    session.submit("undo that")
    assert host.registry.ran == ["format.upper_case", "format.lower_case"]
    session.submit("save it all")
    session.submit("undo that")
    assert host.registry.ran[-1] == "edit.undo"


def test_undo_walks_back_five_and_then_says_so() -> None:
    host = host_for("radio")
    session = _session(host)
    for _ in range(7):
        session.submit("louder")
    for _ in range(6):
        session.submit("undo that")
    assert host.registry.ran.count("radio.volume_down") == 5
    assert host.spoken[-1] == "Nothing to undo from here yet."


def test_undo_with_nothing_done_and_a_readout_that_cannot_be_undone() -> None:
    host = host_for("radio")
    session = _session(host)
    session.submit("undo that")
    assert host.spoken == ["Nothing to undo from here yet."]
    session.submit("what song is this")
    session.submit("undo that")
    assert host.spoken[-1] == "I can't undo Identify Song."


def test_do_that_again() -> None:
    host = host_for("radio")
    session = _session(host)
    session.submit("again")
    assert host.spoken == ["Nothing to do again yet."]
    session.submit("quieter")
    session.submit("do that again")
    assert host.registry.ran == ["radio.volume_down", "radio.volume_down"]


def test_do_that_again_when_it_is_no_longer_here() -> None:
    host = host_for("radio")
    session = _session(host)
    session.submit("quieter")
    host.registry.reasons["radio.volume_down"] = "Nothing is playing."
    session.submit("again")
    assert host.spoken[-1] == NOT_HERE_MESSAGE


def test_cancel_and_empty_do_nothing() -> None:
    host = host_for("radio")
    session = _session(host)
    assert session.submit("never mind").outcome is Outcome.CANCEL
    assert session.submit("   ").outcome is Outcome.EMPTY
    assert host.registry.ran == [] and host.spoken == []


# -- the boundary ---------------------------------------------------------------


def test_a_chosen_id_that_was_not_offered_is_never_run(caplog: pytest.LogCaptureFixture) -> None:
    host = host_for("radio")
    spec = row("radio.update_catalog", "radio")
    assert spec is not None
    assert _session(host).run_candidate(Candidate(spec)) is False
    assert host.registry.ran == []
    assert "QUILL-CORE-COMMAND-NOT-OFFERED" in caplog.text


def test_a_command_no_longer_registered_is_not_run(caplog: pytest.LogCaptureFixture) -> None:
    import logging

    caplog.set_level(logging.INFO)
    host = host_for("quill")
    session = _session(host)
    spec = row("format.bold")
    assert spec is not None
    candidate = Candidate(spec)
    host.registry.ids.discard("format.bold")
    host.rows = host.rows  # candidates are rebuilt from the registry
    assert session._run(candidate, read_args(""), (candidate,)) is False
    assert host.spoken == ["Bold can't be done right now."]
    assert "QUILL-CORE-COMMAND-NO-LONGER-AVAILABLE" in caplog.text


def test_only_the_policy_runs_a_command_for_a_sentence() -> None:
    """Section 15: the engine boundary. Nothing else in the catalogue package calls run."""
    package = Path(__file__).resolve().parents[3] / "quill" / "core" / "command_catalogue"
    callers = [
        path.name
        for path in package.glob("*.py")
        if ".run(" in path.read_text(encoding="utf-8") and path.name != "policy.py"
    ]
    assert callers == []


def test_decide_never_returns_a_never_row_even_if_handed_one() -> None:
    spec = row("app.exit")
    assert spec is not None
    decision = decide("exit", [Candidate(spec)])
    assert decision.outcome is not Outcome.RUN
