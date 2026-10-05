"""Hold-to-talk, the live preview's pacing, and closing a sentence at a pause."""

from __future__ import annotations

from quill.core.windows_dictation.hold import HOLD_SECONDS, HoldAction, HoldToTalk
from quill.core.windows_dictation.preview import (
    PreviewThrottle,
    close_sentence,
    coerce_preview,
)

# -- hold-to-talk ------------------------------------------------------------ #


def test_a_quick_press_starts_and_dictation_stays_on() -> None:
    hold = HoldToTalk()
    assert hold.press(now=0.0, active=False, key_down=True) is HoldAction.START
    assert hold.poll(now=0.1, key_down=True) is HoldAction.WATCH
    assert hold.poll(now=0.2, key_down=False) is HoldAction.DONE
    assert not hold.watching


def test_holding_past_half_a_second_stops_on_release() -> None:
    hold = HoldToTalk()
    hold.press(now=0.0, active=False, key_down=True)
    assert hold.poll(now=HOLD_SECONDS + 0.01, key_down=True) is HoldAction.WATCH
    assert hold.holding
    assert hold.poll(now=3.0, key_down=False) is HoldAction.RELEASE


def test_repeats_while_the_key_is_held_are_ignored() -> None:
    hold = HoldToTalk()
    hold.press(now=0.0, active=False, key_down=True)
    assert hold.press(now=0.03, active=True, key_down=True) is HoldAction.IGNORE


def test_pressing_while_on_stops_and_letting_go_does_nothing_more() -> None:
    hold = HoldToTalk()
    assert hold.press(now=0.0, active=True, key_down=True) is HoldAction.STOP
    assert hold.poll(now=2.0, key_down=False) is HoldAction.DONE


def test_with_hold_off_a_long_press_is_still_only_a_toggle() -> None:
    hold = HoldToTalk(hold_enabled=False)
    hold.press(now=0.0, active=False, key_down=True)
    assert hold.poll(now=2.0, key_down=False) is HoldAction.DONE


def test_a_press_from_a_menu_is_a_plain_toggle() -> None:
    hold = HoldToTalk()
    assert hold.press(now=0.0, active=False, key_down=False) is HoldAction.START
    assert not hold.watching
    assert hold.press(now=0.1, active=True, key_down=False) is HoldAction.STOP


# -- the preview ------------------------------------------------------------- #


def test_the_status_bar_is_updated_a_few_times_a_second_at_most() -> None:
    throttle = PreviewThrottle()
    assert throttle.to_show("can you", 0.0) == "can you"
    assert throttle.to_show("can you send", 0.1) is None
    assert throttle.to_show("can you send", 0.5) == "can you send"
    assert throttle.to_show("can you send", 1.0) is None  # nothing new


def test_the_spoken_preview_says_only_new_words_and_not_too_often() -> None:
    throttle = PreviewThrottle()
    assert throttle.to_speak("can you send", 0.0) == "can you send"
    assert throttle.to_speak("can you send me the", 0.5) is None  # too soon
    assert throttle.to_speak("can you send me the report", 2.5) == "me the report"
    assert throttle.to_speak("can you send me the report", 5.0) is None


def test_a_changed_mind_is_said_from_where_it_changed() -> None:
    throttle = PreviewThrottle()
    throttle.to_speak("call doctor", 0.0)
    assert throttle.to_speak("call dr okonkwo", 3.0) == "dr okonkwo"


def test_preview_choice_is_coerced() -> None:
    assert coerce_preview("speak") == "speak"
    assert coerce_preview("loud") == "show"


# -- closing a sentence ----------------------------------------------------- #


def test_questions_get_a_question_mark_and_statements_a_full_stop() -> None:
    assert close_sentence("Can you send me the report by Friday") == (
        "Can you send me the report by Friday?"
    )
    assert close_sentence("Where did you put the keys") == "Where did you put the keys?"
    assert close_sentence("The meeting moved") == "The meeting moved."


def test_clauses_and_commands_are_not_mistaken_for_questions() -> None:
    assert close_sentence("When I get home I will call") == "When I get home I will call."
    assert close_sentence("Do the dishes") == "Do the dishes."
    assert close_sentence("Have a good day") == "Have a good day."


def test_an_engines_own_mark_is_kept_and_spanish_needs_the_opening_mark() -> None:
    assert close_sentence("What a surprise!") == "What a surprise!"
    assert close_sentence(chr(0xBF) + "Vienes mañana", "es") == chr(0xBF) + "Vienes mañana?"
    assert close_sentence("Vienes mañana", "es") == "Vienes mañana."
    assert close_sentence("   ") == ""
