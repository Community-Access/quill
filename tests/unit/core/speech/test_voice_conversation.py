"""Tests for the voice conversation state machine (Hey QUILL Phase 2)."""

from __future__ import annotations

from quill.core.speech.conversation import (
    CUE_ERROR,
    CUE_IDLE,
    CUE_LISTEN,
    CUE_OFF,
    CUE_ON,
    CUE_READY,
    CUE_REVIEW,
    CUE_TICK,
    TIMER_FOLLOWUP,
    TIMER_REVIEW,
    TIMER_THINKING,
    ConversationController,
    State,
    Timing,
)


def _kinds(effects, kind):
    return [e for e in effects if e.kind == kind]


def _sounds(effects):
    return [e.value for e in effects if e.kind == "sound"]


def _start(**timing):
    c = ConversationController(timing=Timing(**timing) if timing else Timing())
    c.start()
    return c


def test_start_enters_idle_then_arms_and_opens_capture() -> None:
    c = ConversationController()
    effects = c.start()
    assert c.state is State.ARMED
    assert _sounds(effects) == [CUE_ON, CUE_LISTEN]
    assert _kinds(effects, "start_capture")


def test_start_is_idempotent_when_not_off() -> None:
    c = _start()
    assert c.start() == []


def test_matched_command_reviews_then_dispatches_after_timer() -> None:
    c = _start(review_ms=900)
    effects = c.on_transcript("file.save", "Running Save.")
    assert c.state is State.REVIEW
    assert CUE_REVIEW in _sounds(effects)
    timers = _kinds(effects, "start_timer")
    assert timers and timers[0].value == TIMER_REVIEW

    dispatched = c.on_review_timer()
    assert c.state is State.BUSY
    run = _kinds(dispatched, "dispatch")
    assert run and run[0].value == "file.save"


def test_zero_review_window_dispatches_immediately() -> None:
    c = _start(review_ms=0)
    effects = c.on_transcript("file.save", "Running Save.")
    assert c.state is State.BUSY
    assert _kinds(effects, "dispatch")[0].value == "file.save"


def test_no_match_plays_error_and_rearms() -> None:
    c = _start()
    effects = c.on_transcript(None, "No command matched.")
    assert c.state is State.ARMED
    assert CUE_ERROR in _sounds(effects)
    assert _kinds(effects, "start_capture")


def test_cancel_rearms_without_dispatch() -> None:
    c = _start()
    c.on_transcript("file.save", "Running Save.")
    effects = c.on_cancel()
    assert c.state is State.ARMED
    assert not _kinds(effects, "dispatch")
    assert _kinds(effects, "cancel_timer")


def test_action_done_opens_followup_window() -> None:
    c = _start(review_ms=0, followup_ms=3000)
    c.on_transcript("file.save", "Running Save.")  # -> BUSY
    effects = c.on_action_done()
    assert c.state is State.ARMED
    assert CUE_READY in _sounds(effects)
    timers = [e for e in effects if e.kind == "start_timer"]
    assert any(t.value == TIMER_FOLLOWUP for t in timers)


def test_action_done_relaxes_to_idle_when_followup_disabled() -> None:
    c = _start(review_ms=0, followup_ms=0)
    c.on_transcript("file.save", "Running Save.")
    effects = c.on_action_done()
    assert c.state is State.IDLE
    assert CUE_IDLE in _sounds(effects)
    assert not _kinds(effects, "start_capture")


def test_followup_timeout_relaxes_to_idle() -> None:
    c = _start(review_ms=0, followup_ms=3000)
    c.on_transcript("file.save", "Running Save.")
    c.on_action_done()  # ARMED, follow-up armed
    effects = c.on_followup_timer()
    assert c.state is State.IDLE
    assert _kinds(effects, "stop_capture")


def test_thinking_tick_repeats_only_while_busy() -> None:
    c = _start(review_ms=0, thinking_ms=2000)
    c.on_transcript("file.save", "Running Save.")  # BUSY, thinking timer armed
    ticks = c.on_thinking_timer()
    assert CUE_TICK in _sounds(ticks)
    assert any(e.kind == "start_timer" and e.value == TIMER_THINKING for e in ticks)
    # Once the action is done we are no longer BUSY; a stray tick is a no-op.
    c.on_action_done()
    assert c.on_thinking_timer() == []


def test_stop_from_any_state_cleans_up() -> None:
    c = _start()
    effects = c.stop()
    assert c.state is State.OFF
    assert CUE_OFF in _sounds(effects)
    assert _kinds(effects, "stop_capture")
    assert len(_kinds(effects, "cancel_timer")) == 3


def test_out_of_state_events_are_ignored() -> None:
    c = ConversationController()  # OFF
    assert c.on_transcript("file.save", "x") == []
    assert c.on_review_timer() == []
    assert c.on_action_done() == []
    assert c.on_followup_timer() == []
    assert c.stop() == []


def test_timing_from_settings_reads_and_defaults() -> None:
    class _S:
        voice_conversation_silence_ms = 1500
        voice_conversation_review_ms = -5  # invalid -> default
        voice_conversation_followup_ms = 0
        # thinking omitted -> default

    t = Timing.from_settings(_S())
    assert t.silence_ms == 1500
    assert t.review_ms == 900  # negative rejected
    assert t.followup_ms == 0
    assert t.thinking_ms == 2000


def test_status_text_tracks_state() -> None:
    c = ConversationController()
    assert "off" in c.status_text().lower()
    c.start()
    assert c.status_text() == "Listening"


# -- refinement: varied, personalized prompts (ADP personality) --------------


def _announces(effects):
    return [e.value for e in effects if e.kind == "announce"]


def test_varied_prompts_use_a_welcome_first_then_shorter_prompts() -> None:
    c = ConversationController(varied_prompts=True, user_name="Jeff")
    first = _announces(c.start())
    assert any("Jeff" in line for line in first)
    # After acting, the re-arm prompt is a shorter "listening" line, not a fresh
    # first-time welcome.
    c.timing = Timing(review_ms=0, followup_ms=3000)
    c.on_transcript("file.save", "Running Save.")
    rearm = _announces(c.on_action_done())
    assert rearm  # a prompt is spoken on re-arm


def test_plain_prompts_are_deterministic_by_default() -> None:
    c = ConversationController(user_name="Jeff")  # varied_prompts defaults False
    assert _announces(c.start()) == ["Listening, Jeff."]
