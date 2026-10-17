"""D-20 (self-repair, the named styles), D-21 (learning from corrections, the
per-context lists) and P3 "Polish my dictation", with fakes only: no
microphone, no network, no window."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from quill.core.windows_dictation.correction_learning import (
    ANSWER_SECONDS,
    CorrectionLearner,
    add_learned_correction,
    offer_question,
    replaced_span,
)
from quill.core.windows_dictation.profile import context_profile, rewriter
from quill.core.windows_dictation.review_session import (
    POLISH_INSTRUCTION,
    POLISH_OFF,
    REVIEW_COMMANDS,
    ReviewSession,
)
from quill.core.windows_dictation.self_repair import (
    CUSTOM_STYLE,
    STYLE_FIELDS,
    repair_text,
    style_choices,
    style_of,
)
from quill.core.windows_dictation.settings_fields import DictationSettings, load_fields
from quill.core.windows_dictation.vocabulary import Command
from quill.core.windows_dictation.words_file import (
    Entry,
    context_list,
    load_words,
    parse_words,
    render_words,
    save_words,
)
from tests.unit.core.test_dictation_live_controller import _controller, _hear

# -- D-20: self-repair -------------------------------------------------------- #

REPAIRS = [
    ("meet on Thursday, no, Friday at noon", "meet on Friday at noon"),
    ("Thursday, I mean Friday", "Friday"),
    ("in June, no I mean July", "in July"),
    ("I have two no three cats", "I have three cats"),
    ("Two, no, three apples", "Three apples"),
    ("call me at 5, sorry, 6", "call me at 6"),
    ("send it to Ana, sorry, Maria", "send it to Maria"),  # names from My Words
    ("Monday scratch that word Tuesday", "Tuesday"),
]

#: Things a person says that look a little like a repair and are not one.
LEFT_ALONE = [
    "no, I don't think so",
    "Is it Thursday? No, Friday.",  # a question answered: two sentences
    "I said no, Friday",  # a verb before the marker
    "I may, no, March",  # "may" the verb, not the month
    "I mean it",
    "sorry, Friday is out",  # nothing before the marker
    "Thursday, no",  # nothing after it
    "send it to Bob, no, Maria",  # Bob is not in My Words
    "two, no more",  # different kinds
    "Friday. No, Saturday works better",  # a full stop ends the first
]


@pytest.mark.parametrize(("said", "written"), REPAIRS)
def test_a_repair_between_two_of_a_kind_keeps_the_second(said: str, written: str) -> None:
    assert repair_text(said, ["Ana", "Maria"]) == written


@pytest.mark.parametrize("said", LEFT_ALONE)
def test_anything_else_is_written_as_said(said: str) -> None:
    assert repair_text(said, ["Ana", "Maria"]) == said


def test_self_repair_is_off_by_default_and_loads_safely() -> None:
    assert DictationSettings().windows_dictation_self_repair is False
    assert DictationSettings().windows_dictation_polish is False
    fields = load_fields({"windows_dictation_self_repair": 1, "windows_dictation_polish": ""})
    assert fields["windows_dictation_self_repair"] is True
    assert fields["windows_dictation_polish"] is False


def test_the_controller_repairs_only_when_asked() -> None:
    controller, doc, _f, _r, _c, holder = _controller()
    _hear(controller, "meet on Thursday, no, Friday")
    assert doc.text == "Meet on Thursday, no, Friday"
    holder["prefs"] = replace(holder["prefs"], self_repair=True)
    doc.text = ""
    controller.history.clear()
    _hear(controller, "meet on Thursday, no, Friday")
    assert doc.text == "Meet on Friday"


def test_a_live_transcript_never_repairs() -> None:
    from quill.core.windows_dictation.preferences import DictationPreferences

    settings = DictationSettings(windows_dictation_self_repair=True)
    assert DictationPreferences.from_settings(settings).self_repair is True
    assert DictationPreferences.from_settings(settings, profile="transcript").self_repair is False


# -- D-20: the named styles --------------------------------------------------- #


def test_each_named_style_is_recognised_from_its_fields() -> None:
    for style, fields in STYLE_FIELDS.items():
        assert style_of(fields) == style
    assert style_of({"windows_dictation_remove_fillers": True}) == CUSTOM_STYLE


def test_polished_is_offered_only_when_ai_is_on() -> None:
    assert "polished" not in dict(style_choices(ai_on=False))
    assert "polished" in dict(style_choices(ai_on=True))
    assert STYLE_FIELDS["polished"]["windows_dictation_review_first"] is True


# -- D-21: learning from corrections ------------------------------------------ #


def test_the_replaced_word_is_found_and_anything_bigger_is_not() -> None:
    assert replaced_span("write to Ann", "write to Anne") == ("Ann", "Anne")
    assert replaced_span("call Doco today", "call Doko today.") == ("Doco", "Doko")
    assert replaced_span("hello", "Hello.") is None  # case and marks only
    assert replaced_span("a b c", "x b y") is None  # two places
    assert replaced_span("send it", "send it now") is None  # an addition


def test_the_offer_comes_on_the_second_identical_correction_and_only_once() -> None:
    learner = CorrectionLearner()
    assert learner.note("write to Ann", "write to Anne") is None
    assert learner.note("tell Ann", "tell Anne") == ("Ann", "Anne")
    assert learner.note("tell Ann", "tell Anne") is None
    assert offer_question("Ann", "Anne") == "Add a correction: Ann becomes Anne?"


def test_a_yes_adds_it_to_the_corrections_section(tmp_path: Path) -> None:
    path = tmp_path / "dictation.md"
    save_words(path, parse_words("## Vocabulary\n\n- QUILL\n"))
    said = add_learned_correction(path, "Ann", "Anne")
    assert said == "Added: Ann becomes Anne. It is in My Words and Phrases."
    words = load_words(path)
    assert ("Ann", "Anne") in words.corrections
    assert words.words == ["QUILL"]
    assert "already has a correction" in add_learned_correction(path, "ann", "Anna")


def _learning(tmp_path: Path, *, window: bool) -> tuple[Any, Any, Any, Any, list[Any]]:
    controller, doc, feedback, _r, clock, _h = _controller(engine="windows")
    path = tmp_path / "dictation.md"
    feedback.words_path = lambda: path
    asked: list[Any] = []
    if window:
        feedback.confirm_correction = lambda question, on_yes: asked.append((question, on_yes))
    return controller, doc, feedback, clock, asked


def _correct_twice(controller: Any, doc: Any) -> None:
    for _round in range(2):
        _hear(controller, "write to Ann", alternatives=("write to Anne",))
        _hear(controller, "correct that")
        _hear(controller, "choose one")
        assert doc.text.endswith("write to Anne")


def test_the_editors_ask_in_a_window_and_add_only_on_yes(tmp_path: Path) -> None:
    controller, doc, feedback, _clock, asked = _learning(tmp_path, window=True)
    _correct_twice(controller, doc)
    assert [question for question, _yes in asked] == ["Add a correction: Ann becomes Anne?"]
    assert not (tmp_path / "dictation.md").exists()  # nothing yet: no answer
    asked[0][1]()  # Yes
    assert ("Ann", "Anne") in load_words(tmp_path / "dictation.md").corrections
    assert feedback.said[-1].startswith("Added: Ann becomes Anne.")


def test_without_a_window_quill_yes_answers_the_spoken_offer(tmp_path: Path) -> None:
    controller, doc, feedback, _clock, _asked = _learning(tmp_path, window=False)
    _correct_twice(controller, doc)
    assert feedback.said[-1] == (
        "Add a correction: Ann becomes Anne? Say QUILL yes to add it, or QUILL no."
    )
    _hear(controller, "quill yes")
    assert ("Ann", "Anne") in load_words(tmp_path / "dictation.md").corrections


def test_quill_no_and_a_late_yes_add_nothing(tmp_path: Path) -> None:
    controller, doc, feedback, clock, _asked = _learning(tmp_path, window=False)
    _correct_twice(controller, doc)
    _hear(controller, "quill no")
    assert feedback.said[-1] == "Not added."
    assert not (tmp_path / "dictation.md").exists()
    controller2, doc2, _f2, clock2, _a2 = _learning(tmp_path, window=False)
    _correct_twice(controller2, doc2)
    clock2.now += ANSWER_SECONDS + 1
    _hear(controller2, "quill yes")
    assert not (tmp_path / "dictation.md").exists()
    del clock


def test_correct_x_then_the_new_words_counts_as_a_correction(tmp_path: Path) -> None:
    controller, doc, feedback, _clock, asked = _learning(tmp_path, window=True)
    for _round in range(2):
        _hear(controller, "write to Ann.")
        _hear(controller, "correct Ann")
        _hear(controller, "Anne")
        assert "Anne" in doc.text.split("write to")[-1]
    assert [question for question, _yes in asked] == ["Add a correction: Ann becomes Anne?"]


def test_words_after_correct_x_written_elsewhere_count_for_nothing(tmp_path: Path) -> None:
    controller, doc, _feedback, _clock, asked = _learning(tmp_path, window=True)
    for _round in range(2):
        _hear(controller, "write to Ann.")
        _hear(controller, "correct Ann")
        _hear(controller, "select all")  # another command: the correction is off
        doc.select(len(doc.text), len(doc.text))
        _hear(controller, "Anne")
    assert asked == []


def test_a_host_without_a_word_list_never_offers() -> None:
    controller, doc, feedback, _r, _c, _h = _controller(engine="windows")
    _correct_twice(controller, doc)
    assert not any("Add a correction" in said for said in feedback.said)


# -- D-21: lists per context --------------------------------------------------- #

FILE = """\
## Vocabulary

- QUILL

## Corrections

quill light => QUILL Lite

## Context: email

- Okonkwo
regards => Kind regards

## Context: Code

pie test => pytest
"""


def test_context_lists_are_read_kept_on_save_and_picked_without_case(tmp_path: Path) -> None:
    words = parse_words(FILE)
    email = context_list(words, "EMAIL")
    assert email is not None
    assert email.words == ["Okonkwo"]
    assert email.corrections == [("regards", "Kind regards")]
    assert context_list(words, "") is None
    assert context_list(words, "letters") is None
    words.add(Entry("word", "NVDA"))
    again = parse_words(render_words(words))
    assert [c.name for c in again.contexts] == ["email", "Code"]
    assert again.words == ["QUILL", "NVDA"]


def test_a_context_list_applies_only_while_that_profile_is_active(tmp_path: Path) -> None:
    path = tmp_path / "dictation.md"
    path.write_text(FILE, encoding="utf-8")
    plain = rewriter(path)
    email = rewriter(path, context="email")
    assert plain is not None and email is not None
    assert plain("regards from quill light") == "regards from QUILL Lite"
    assert email("regards from quill light") == "Kind regards from QUILL Lite"
    assert context_profile(path, "").is_empty
    assert context_profile(path, "code").replacements == (("pie test", "pytest"),)


def test_the_general_profile_parser_ignores_context_sections() -> None:
    from quill.core.speech.dictation_profile import parse_profile

    profile = parse_profile(FILE)
    assert profile.vocabulary == ("QUILL",)
    assert ("regards", "Kind regards") not in profile.replacements


# -- P3: Polish my dictation ---------------------------------------------------- #


def test_polish_that_is_a_review_command() -> None:
    assert REVIEW_COMMANDS[("polish", "that")] is Command.REVIEW_POLISH


def _polishing(*, on: bool, consented: bool = False, yes: bool = True) -> tuple[Any, Any, Any]:
    from quill.core.windows_dictation.review_conversation import ReviewConversation
    from tests.unit.core.test_dictation_review import _Ai, _Port

    port, ai = _Port(yes=yes), _Ai(consented=consented)
    talk = ReviewConversation(
        ReviewSession("see you thursday i think"), port, ai=ai, polish_on=lambda: on
    )
    return talk, port, ai


def test_polish_is_off_by_default_and_sends_nothing() -> None:
    talk, port, ai = _polishing(on=False)
    talk.polish()
    assert port.said == [POLISH_OFF]
    assert ai.prompts == []


def test_polish_asks_consent_first_and_declining_sends_nothing() -> None:
    talk, port, ai = _polishing(on=True, yes=False)
    talk.polish()
    assert port.asked == ["Review with AI"]
    assert ai.prompts == []
    assert port.said == ["Nothing was sent."]


def test_polish_sends_one_fixed_request_and_undo_takes_it_back() -> None:
    talk, port, ai = _polishing(on=True)
    talk.polish()
    assert len(ai.prompts) == 1
    assert POLISH_INSTRUCTION in ai.prompts[0]
    assert "<dictated-text>\nsee you thursday i think\n</dictated-text>" in ai.prompts[0]
    assert port.said == ["Polishing."]
    assert port.statuses[-1] == "Working: polish. Escape stops it."
    ai.reply("See you Thursday, I think.")
    assert port.text == "See you Thursday, I think."
    assert port.inserted == []  # never inserted by itself
    talk.undo_change()
    assert port.text == "see you thursday i think"


def test_quill_polish_that_opens_the_last_phrase_then_polishes() -> None:
    from tests.unit.core.test_dictation_review import _controller as review_controller
    from tests.unit.core.test_dictation_review import _say

    controller, document, feedback, desk = review_controller(polish=False)
    assert desk is not None
    _say(controller, "see you thursday")
    _say(controller, "quill polish that")
    assert feedback.said == [POLISH_OFF]
    assert desk.opened == [] and document.text == "See you thursday"
    controller, document, _feedback, desk = review_controller(polish=True)
    assert desk is not None
    _say(controller, "see you thursday")
    _say(controller, "quill polish that")
    assert desk.opened == ["See you thursday"]
    assert desk.commands == [Command.REVIEW_POLISH]
    assert document.text == ""


def test_the_names_for_self_repair_come_from_my_words_only_when_it_is_on(
    tmp_path: Path,
) -> None:
    from quill.core.windows_dictation.preferences import DictationPreferences
    from quill.core.windows_dictation.profile import with_repair_names

    path = tmp_path / "dictation.md"
    path.write_text("## Vocabulary\n\n- Ana\n- Maria\n", encoding="utf-8")
    off = DictationPreferences()
    assert with_repair_names(off, path) is off
    on = with_repair_names(DictationPreferences(self_repair=True), path)
    assert on.repair_names == ("Ana", "Maria")
    assert repair_text("send it to Ana, sorry, Maria", on.repair_names) == "send it to Maria"
