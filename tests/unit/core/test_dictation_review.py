"""Review before inserting (D-2, 2026-10-15): the session, the conversation and
the controller's voice half.

Everything with fakes: an editor-like document, the external document QUILL
Transcribe types through with an injector that fails the test if anything is
typed before Insert, a review desk standing in for the window, and an AI that
answers when told to. The window itself is ``tests/unit/ui/test_dictation_review_frame.py``.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path
from typing import Any

import pytest

from quill.core.diffing import change_fraction, spoken_changes
from quill.core.windows_dictation import (
    DictationController,
    DictationPreferences,
    RecognizedPhrase,
    words_from_text,
)
from quill.core.windows_dictation.ports import DictationState, Moment
from quill.core.windows_dictation.review_conversation import ReviewConversation
from quill.core.windows_dictation.review_mixin import NOT_HERE
from quill.core.windows_dictation.review_session import (
    AI_OFF,
    CONSENT_VERSION,
    REVIEW_COMMANDS,
    ReviewSession,
    load_rescue,
    not_reviewing,
    review_request,
    save_rescue,
)
from quill.core.windows_dictation.settings_fields import DictationSettings, load_fields
from quill.core.windows_dictation.vocabulary import Command
from quill.ui.windows_dictation_external import ExternalDocument


def _sentences(text: str) -> int:
    return sum(text.count(mark) for mark in ".?!")


# -- the spoken diff ------------------------------------------------------------- #


def test_a_change_is_said_in_words_people_use() -> None:
    assert spoken_changes("see you next Thursday", "see you Friday") == (
        "Changed next Thursday to Friday."
    )
    assert spoken_changes("um so the plan is fine", "the plan is fine") == "Removed um so."
    assert spoken_changes("hello", "hello") == "No change."
    assert spoken_changes("hello there", "Hello there.") == "Changed punctuation or capitals only."


def test_a_summary_is_never_more_than_two_sentences() -> None:
    before = "one two three four five six seven eight nine ten eleven twelve"
    after = "one TWO 3 four 5 six 7 eight 9 ten eleven twelve thirteen"
    said = spoken_changes(before, after)
    assert _sentences(said) <= 2
    assert said.startswith("Changed")


def test_more_than_half_changed_is_flagged_as_a_large_change() -> None:
    before = "please send the quarterly report to the whole team by friday"
    after = "kindly forward everything we discussed at lunch yesterday afternoon"
    assert change_fraction(before, after) > 0.5
    said = spoken_changes(before, after)
    assert said.startswith("Large change:") and _sentences(said) <= 2


# -- the session ---------------------------------------------------------------------- #


def test_back_to_what_i_said_restores_the_dictated_words_exactly() -> None:
    session = ReviewSession("um so see you next Thursday")
    session.revise("make it shorter", "See you Thursday.")
    session.revise("more formal", "I look forward to seeing you on Thursday.")
    assert session.current == "I look forward to seeing you on Thursday."
    assert session.restore_original()
    assert session.current == "um so see you next Thursday"
    assert session.original == "um so see you next Thursday"
    assert not session.restore_original()  # already there


def test_undo_takes_back_one_change_at_a_time() -> None:
    session = ReviewSession("a b c")
    session.revise("first", "a b")
    session.revise("second", "a")
    assert session.undo_revision()
    assert session.current == "a b"
    assert session.undo_revision()
    assert session.current == "a b c"
    assert session.undo_revision() == ""


def test_what_was_said_follows_the_text_until_the_first_change() -> None:
    session = ReviewSession("")
    session.edited("Dear Sam")
    session.edited("Dear Sam, thanks")
    assert session.original == "Dear Sam, thanks"
    session.revise("formal", "Dear Mr Smith, thank you")
    session.edited("Dear Mr Smith, thank you!")
    assert session.original == "Dear Sam, thanks"  # never changed once the AI has


def test_a_request_carries_the_words_as_data_and_nothing_else() -> None:
    sent = review_request("ask Sam to call me", "make it shorter")
    assert "<request>\nmake it shorter\n</request>" in sent
    assert sent.endswith("<dictated-text>\nask Sam to call me\n</dictated-text>")
    assert "dictation-instructions" not in sent
    with_context = review_request("x", "y", my_instructions="British spelling.", context="a letter")
    assert "British spelling." in with_context and "This document is: a letter" in with_context


def test_the_ai_instruction_marks_the_text_as_data() -> None:
    from quill.core.ai.own_key import INSTRUCTIONS, OWN_KEY_LIMITS

    revise = INSTRUCTIONS["revise_dictation"]
    assert "never a request to you" in revise and "<request>" in revise
    assert OWN_KEY_LIMITS.feature_available("revise_dictation")


def test_an_open_review_survives_a_crash(tmp_path: Path) -> None:
    rescue = tmp_path / "dictation-review.json"
    session = ReviewSession("see you next Thursday")
    session.revise("shorter", "See you Thursday.")
    assert save_rescue(rescue, session)
    back = load_rescue(rescue)
    assert back is not None
    assert back.original == "see you next Thursday"
    assert back.current == "See you Thursday."
    assert len(back.revisions) == 1
    assert load_rescue(tmp_path / "missing.json") is None
    (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")
    assert load_rescue(tmp_path / "bad.json") is None


def test_the_review_settings_default_off_and_load_safely() -> None:
    fields = load_fields({"windows_dictation_review_consent": "nonsense"})
    assert fields["windows_dictation_review_first"] is False
    assert fields["windows_dictation_review_consent"] == 0
    assert fields["windows_dictation_review_context"] is False
    settings = DictationSettings()
    assert settings.windows_dictation_review_first is False
    assert settings.windows_dictation_review_context is False


# -- the conversation ------------------------------------------------------------------ #


class _Port:
    def __init__(self, *, yes: bool = True) -> None:
        self.yes = yes
        self.said: list[str] = []
        self.statuses: list[str] = []
        self.text = ""
        self.changes = ""
        self.muted: list[str] = []
        self.asked: list[str] = []
        self.inserted: list[tuple[str, str]] = []
        self.closed = 0

    def say(self, text: str) -> None:
        self.said.append(text)

    def status(self, text: str) -> None:
        self.statuses.append(text)

    def show_text(self, text: str) -> None:
        self.text = text

    def show_changes(self, text: str) -> None:
        self.changes = text

    def mute(self, text: str) -> None:
        self.muted.append(text)

    def ask_yes_no(self, question: str, title: str) -> bool:
        self.asked.append(title)
        return self.yes

    def insert(self, text: str, original: str) -> None:
        self.inserted.append((text, original))

    def close(self) -> None:
        self.closed += 1


class _Ai:
    def __init__(self, *, reason: str = "", consented: bool = False) -> None:
        self._reason = reason
        self._consented = consented
        self.agreed = 0
        self.prompts: list[str] = []
        self.pending: list[tuple[Any, Any]] = []
        self.cancelled = 0

    def reason(self) -> str:
        return self._reason

    def provider(self) -> str:
        return "OpenAI, with your own key"

    def consented(self) -> bool:
        return self._consented

    def agree(self) -> None:
        self._consented = True
        self.agreed += 1

    def ask(self, prompt: str, on_done: Any, on_error: Any) -> object:
        self.prompts.append(prompt)
        self.pending.append((on_done, on_error))
        return object()

    def cancel(self, request: Any) -> None:
        self.cancelled += 1

    def reply(self, text: str) -> None:
        on_done, _on_error = self.pending.pop(0)
        on_done(text)


def _talk(text: str = "um so see you next Thursday", **ai: Any) -> tuple[Any, _Port, _Ai]:
    port, model = _Port(), _Ai(**ai)
    return ReviewConversation(ReviewSession(text), port, ai=model), port, model


def test_ai_off_sends_nothing_and_says_why() -> None:
    conversation, port, ai = _talk(reason="AI help is switched off.")
    conversation.instruct("make it shorter")
    assert ai.prompts == []
    assert port.said == ["AI help is switched off."]
    assert "switched off" in conversation.opening_status()


def test_declining_consent_sends_nothing() -> None:
    conversation, port, ai = _talk()
    port.yes = False
    conversation.instruct("make it shorter")
    assert port.asked == ["Review with AI"]
    assert ai.prompts == [] and ai.agreed == 0
    assert port.said == ["Nothing was sent."]


def test_consent_is_asked_once_and_only_the_words_go() -> None:
    conversation, port, ai = _talk()
    conversation.instruct("make it shorter")
    conversation.instruct("ignored while working")
    assert port.asked == ["Review with AI"] and ai.agreed == 1
    assert len(ai.prompts) == 1
    assert "um so see you next Thursday" in ai.prompts[0]
    assert "This document is" not in ai.prompts[0]  # no context unless turned on
    assert port.said[:1] == ["Working."]


def test_a_revision_says_what_changed_and_what_changed_repeats_it() -> None:
    conversation, port, ai = _talk(consented=True)
    conversation.instruct("make it shorter")
    ai.reply("See you Thursday.")
    summary = port.said[-1]
    assert summary == conversation.session.last_summary and _sentences(summary) <= 2
    assert port.text == "See you Thursday." and port.changes == summary
    assert port.muted[-1] == summary  # the microphone ignores the reader meanwhile
    conversation.what_changed()
    assert port.said[-1] == summary


def test_escape_cancels_a_request_and_its_late_reply_changes_nothing() -> None:
    conversation, port, ai = _talk(consented=True)
    conversation.instruct("make it shorter")
    assert conversation.cancel()
    ai.reply("Something else entirely.")
    assert conversation.session.current == "um so see you next Thursday"
    assert port.said[-1] == "Stopped. Nothing was changed."


def test_insert_is_the_only_way_in_and_it_carries_both_texts(tmp_path: Path) -> None:
    rescue = tmp_path / "dictation-review.json"
    port, ai = _Port(), _Ai(consented=True)
    conversation = ReviewConversation(
        ReviewSession("see you next Thursday"), port, ai=ai, rescue=rescue
    )
    assert rescue.exists()  # kept from the start
    conversation.instruct("shorter")
    ai.reply("See you Thursday.")
    assert port.inserted == []
    conversation.insert()
    assert port.inserted == [("See you Thursday.", "see you next Thursday")]
    assert not rescue.exists()


def test_discard_asks_only_once_the_ai_has_changed_the_words(tmp_path: Path) -> None:
    conversation, port, ai = _talk(consented=True)
    port.yes = False
    conversation.discard()
    assert port.asked == [] and port.closed == 1  # nothing changed: no question
    conversation, port, ai = _talk(consented=True)
    conversation.instruct("shorter")
    ai.reply("See you.")
    port.yes = False
    conversation.discard()
    assert port.asked[-1] == "Discard These Words" and port.closed == 0


def test_closing_the_window_keeps_the_words(tmp_path: Path) -> None:
    rescue = tmp_path / "dictation-review.json"
    conversation = ReviewConversation(ReviewSession("hello there"), _Port(), ai=None, rescue=rescue)
    assert "kept" in conversation.closing()
    back = load_rescue(rescue)
    assert back is not None and back.current == "hello there"


def test_no_ai_means_no_network_call(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.ui.windows_dictation_review import ServiceReviewAi

    def no_network(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("AI off must not touch the network")

    monkeypatch.setattr(urllib.request, "urlopen", no_network)

    class _Service:
        direct = False
        route = "free"
        asked = 0

        def ask(self, *_a: Any, **_k: Any) -> None:
            self.asked += 1

    service = _Service()
    ai = ServiceReviewAi(
        service, off=lambda: "", consent=lambda: CONSENT_VERSION, agree=lambda: None
    )
    port = _Port()
    conversation = ReviewConversation(ReviewSession("hello"), port, ai=ai)
    conversation.instruct("make it shorter")
    assert service.asked == 0
    assert "ChatGPT subscription or your own AI key" in port.said[-1]
    off = ServiceReviewAi(service, off=lambda: "Off.", consent=lambda: 0, agree=lambda: None)
    ReviewConversation(ReviewSession("hello"), port, ai=off).instruct("shorter")
    assert service.asked == 0 and port.said[-1] == "Off."


# -- the controller's voice half ---------------------------------------------------------- #


class _Document:
    holds_phrases = False

    def __init__(self) -> None:
        self.text = ""
        self.reason = ""

    def unavailable_reason(self, *, writing: bool) -> str:
        return self.reason if writing else ""

    def context(self) -> tuple[str, str]:
        return self.text, ""

    def selection(self) -> tuple[int, int]:
        return len(self.text), len(self.text)

    def select(self, start: int, end: int) -> None:
        pass

    def insert(self, text: str) -> tuple[int, int]:
        start = len(self.text)
        self.text += text
        return start, len(self.text)

    def text_between(self, start: int, end: int) -> str:
        return self.text[start:end]

    def remove(self, start: int, end: int) -> None:
        self.text = self.text[:start] + self.text[end:]

    def replace(self, start: int, end: int, text: str) -> tuple[int, int]:
        self.text = self.text[:start] + text + self.text[end:]
        return start, start + len(text)

    def line_bounds(self) -> tuple[int, int]:
        return 0, len(self.text)

    def last_position(self) -> int:
        return len(self.text)

    def undo(self) -> bool:
        return False


class _Desk:
    """The review window, as the controller sees it."""

    def __init__(self, *, reason: str = "") -> None:
        self.controller: DictationController | None = None
        self.box = _Document()
        self.opened: list[str] = []
        self.commands: list[Command] = []
        self.instructions: list[str] = []
        self.reason = reason
        self.talk = False
        self.previous: Any = None

    def is_open(self) -> bool:
        return bool(self.opened)

    def talking(self) -> bool:
        return self.talk

    def ai_reason(self) -> str:
        return self.reason

    def focus(self) -> None:
        pass

    def open(self, text: str) -> None:
        self.opened.append(text)
        self.box.text = text
        assert self.controller is not None
        self.previous = self.controller.review_retarget(self.box)

    def close(self) -> None:
        self.opened.clear()
        assert self.controller is not None
        self.controller.review_retarget(self.previous)

    def command(self, command: Command) -> None:
        self.commands.append(command)

    def instruct(self, text: str) -> None:
        self.instructions.append(text)


class _Feedback:
    def __init__(self, desk: _Desk | None) -> None:
        self.desk = desk
        self.said: list[str] = []
        self.cues: list[Moment] = []

    def has_cue(self, moment: Moment) -> bool:
        return True

    def cue(self, moment: Moment) -> None:
        self.cues.append(moment)

    def say(self, text: str) -> None:
        self.said.append(text)

    def read_back(self, text: str) -> None:
        pass

    def show(self, text: str) -> None:
        pass

    def state_changed(self, state: Any) -> None:
        pass

    def show_commands(self) -> None:
        pass


class _Recognizer:
    def start(self, _microphone: str) -> None:
        pass

    def stop(self) -> None:
        pass


def _controller(
    document: Any = None, *, desk: _Desk | None = None, review: bool = True, **preferences: Any
) -> tuple[DictationController, Any, _Feedback, _Desk | None]:
    document = document if document is not None else _Document()
    desk = desk if desk is not None else (_Desk() if review else None)
    feedback = _Feedback(desk)
    if desk is not None:
        feedback.review = lambda: desk  # type: ignore[attr-defined]
    settings = DictationPreferences(phrase_feedback="silent", announce=False, **preferences)
    controller = DictationController(
        recognizer=lambda _c, _p: _Recognizer(),
        document=document,
        feedback=feedback,
        preferences=lambda: settings,
    )
    if desk is not None:
        desk.controller = controller
    controller.start()
    feedback.said.clear()
    feedback.cues.clear()
    return controller, document, feedback, desk


def _say(controller: DictationController, text: str) -> None:
    controller.on_phrase(RecognizedPhrase(words_from_text(text), text=text))


def test_review_that_takes_the_last_phrase_out_and_into_the_review() -> None:
    controller, document, feedback, desk = _controller()
    assert desk is not None
    _say(controller, "see you next Thursday")
    assert document.text == "See you next Thursday"
    _say(controller, "quill review that")
    assert document.text == ""
    assert desk.opened == ["See you next Thursday"]
    assert feedback.cues == [Moment.COMMAND_ON]
    _say(controller, "and bring the slides")  # dictated into the review, not the document
    assert document.text == ""
    assert "bring the slides" in desk.box.text


def test_review_that_with_ai_off_leaves_the_words_written() -> None:
    controller, document, feedback, desk = _controller(desk=_Desk(reason="AI is off."))
    assert desk is not None
    _say(controller, "hello there")
    _say(controller, "quill review that")
    assert document.text == "Hello there"
    assert desk.opened == []
    assert feedback.said == [AI_OFF]


def test_review_commands_wait_for_a_review() -> None:
    controller, _document, feedback, desk = _controller()
    assert desk is not None
    _say(controller, "quill insert it")
    assert feedback.said == [not_reviewing("QUILL")]
    assert desk.commands == []


def test_while_reviewing_the_command_word_gives_the_ai_its_instructions() -> None:
    controller, _document, _feedback, desk = _controller()
    assert desk is not None
    _say(controller, "hello there")
    _say(controller, "quill review that")
    _say(controller, "quill make it shorter")
    _say(controller, "quill sound more friendly please")
    _say(controller, "quill what changed")
    _say(controller, "quill insert it")
    assert desk.instructions == ["make it shorter", "sound more friendly please"]
    assert desk.commands == [Command.REVIEW_WHAT_CHANGED, Command.REVIEW_INSERT]


def test_dictation_commands_still_work_inside_the_review() -> None:
    controller, _document, _feedback, desk = _controller()
    assert desk is not None
    desk.open("")
    _say(controller, "first part")
    _say(controller, "second part")
    _say(controller, "quill scratch that")
    assert desk.box.text == "First part"
    assert desk.instructions == []


def test_talk_about_it_makes_every_utterance_an_instruction() -> None:
    controller, _document, _feedback, desk = _controller()
    assert desk is not None
    desk.open("hello there")
    desk.talk = True
    _say(controller, "more formal")
    _say(controller, "insert it")
    assert desk.instructions == ["more formal"]
    assert desk.commands == [Command.REVIEW_INSERT]
    assert desk.box.text == "hello there"  # nothing said was written into it


def test_the_held_words_go_into_the_review() -> None:
    document = _Document()
    document.holds_phrases = True  # type: ignore[misc]
    controller, document, _feedback, desk = _controller(document)
    assert desk is not None
    document.reason = "The focus moved."
    _say(controller, "first held")
    _say(controller, "second held")
    assert controller.held_count == 2 and controller.state is DictationState.PAUSED
    _say(controller, "quill review that")
    assert desk.opened == ["First held second held"]
    assert controller.held_count == 0 and controller.state is DictationState.LISTENING
    assert document.text == ""


def test_a_host_with_no_review_says_so() -> None:
    controller, document, feedback, _desk = _controller(review=False)
    _say(controller, "hello")
    _say(controller, "quill review that")
    assert feedback.said == [NOT_HERE]
    assert document.text == "Hello"


def _notepad(**preferences: Any) -> tuple[DictationController, list[str], dict[str, bool], _Desk]:
    typed: list[str] = []
    allowed = {"on": False}

    def type_text(text: str, *_args: Any) -> bool:
        assert allowed["on"], f"typed before Insert: {text!r}"
        typed.append(text)
        return True

    document = ExternalDocument(
        problem=lambda: "",
        where=lambda: ("notepad", 1, "edit"),
        type_text=type_text,
        backspace=lambda count: True,
    )
    controller, _doc, _feedback, desk = _controller(document, **preferences)
    assert desk is not None
    return controller, typed, allowed, desk


def test_nothing_reaches_another_program_before_insert() -> None:
    controller, typed, allowed, desk = _notepad(review_first=True, command_prefix_required=True)
    _say(controller, "dear Sam")
    _say(controller, "thanks for the notes")
    _say(controller, "quill make it more formal")
    assert typed == []
    assert desk.opened == [""] and "Dear Sam" in desk.box.text
    assert desk.instructions == ["make it more formal"]
    desk.close()  # Insert: dictation goes back to the field, then the words are typed once
    allowed["on"] = True
    assert controller.insert_reviewed("Dear Sam, thank you for the notes.") == ""
    assert typed == ["Dear Sam, thank you for the notes."]


def test_the_review_commands_are_one_table() -> None:
    assert REVIEW_COMMANDS[("review", "that")] is Command.REVIEW_THAT
    assert REVIEW_COMMANDS[("insert", "it")] is Command.REVIEW_INSERT
    assert REVIEW_COMMANDS[("back", "to", "what", "i", "said")] is Command.REVIEW_RESTORE
    assert ("make", "it", "shorter") not in REVIEW_COMMANDS  # an instruction, for the AI
