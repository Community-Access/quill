"""Dictation acceptance, second pass: the cases the first pass left between its rows.

The harness is :mod:`tests.unit.apps.test_dictation_acceptance` -- the same
``editor`` fixture, so every test here runs in QUILL and in QUILL Lite through
each editor's own ``cmd_toggle_dictation``, the shared controller and parser,
the document ports and each editor's library. The recogniser is the fake that
hands over the words a test names; the text control is ``FakeControl``.
Nothing opens a microphone, a clipboard or a screen reader.

What this file adds is the edges: where the cursor lands when the words are
repeated and the cursor is not at the end, what is said at each step, what
"scratch that" takes when the last phrase went into the middle of the text,
clips into a selection, snippet names written with hyphens and capitals, the
spacing mode, an address with digits and underscores, and an exact expected
text for every Markdown word rather than "the mark is in there somewhere".
"""

from __future__ import annotations

import pytest

from quill.core.snippets import Snippet
from quill.core.windows_dictation.vocabulary import MARKS
from quill.ui import windows_dictation_commands as shared
from tests.unit.apps import test_dictation_acceptance as _harness

# The first pass's fixtures, reused rather than copied: one editor, one fake
# engine, one patched focus.
editor = _harness.editor
focused = _harness.focused
recognizers = _harness.recognizers


def _at(session, position: int):
    """Put the cursor at *position*, as the arrow keys would before dictating."""
    session.win.control.SetSelection(position, position)
    return session


# -- inserting before and after a spoken phrase ------------------------------ #


def test_go_after_the_last_word_then_dictate_keeps_the_full_stop(editor) -> None:
    session = editor("Meet me on Friday.").start()
    session.hear("go after friday")
    assert session.selection() == (17, 17)
    assert "After Friday." in session.said
    session.hear("morning")
    assert session.text == "Meet me on Friday morning."


def test_go_to_the_first_word_then_dictate_capitalises_the_new_start(editor) -> None:
    session = editor("meet me on Friday.").start()
    session.hear("go to meet")
    assert session.selection() == (0, 0)
    session.hear("please")
    assert session.text.startswith("Please meet me")


def test_scratch_that_after_inserting_in_the_middle_takes_only_the_insertion(editor) -> None:
    session = editor("Meet me on Friday.").start()
    session.hear("go to friday", "next")
    assert session.text == "Meet me on next Friday."
    session.hear("scratch that")
    assert session.text == "Meet me on Friday."
    assert "Scratched: next" in session.said


def test_two_insertions_at_two_places_scratch_back_in_order(editor) -> None:
    session = editor("One three five.").start()
    session.hear("go after one", "two")
    session.hear("go after three", "four")
    assert session.text == "One two three four five."
    session.hear("scratch that")
    assert session.text == "One two three five."
    session.hear("scratch that")
    assert session.text == "One three five."


def test_a_far_go_to_says_the_line_it_landed_on(editor) -> None:
    text = "Dear Sam,\none\ntwo\nthree\nfour\nfive\nLove, Ann."
    session = editor(text).start()
    session.hear("go after dear sam")
    assert session.selection() == (8, 8)
    assert "After Dear Sam, line 1." in session.said


def test_go_to_matches_whatever_the_case_and_punctuation(editor) -> None:
    session = editor("Ready? SET, go!").start()
    session.hear("go to set go")
    assert session.selection() == (7, 7)
    assert "Before SET, go." in session.said


# -- repeated matches -------------------------------------------------------- #


def test_with_the_cursor_at_the_top_the_first_match_after_it_is_chosen(editor) -> None:
    session = _at(editor("Red, red, red."), 0).start()
    session.hear("select red")
    assert session.selection() == (0, 3)
    assert session.said[-1] == "Selected: Red."
    session.hear("select previous")
    assert session.said[-1] == "None before that."
    session.hear("select next")
    assert session.selection() == (5, 8)
    assert session.said[-1] == "Selected: red."


def test_with_the_cursor_in_the_middle_the_match_before_it_wins(editor) -> None:
    # The cursor sits between the second and third "red": the second is nearer
    # behind it, and behind is where people mean.
    session = _at(editor("Red, red, red."), 9).start()
    session.hear("select red")
    assert session.selection() == (5, 8)


def test_a_cursor_inside_a_match_counts_as_that_match(editor) -> None:
    session = _at(editor("cat dog cat dog"), 9).start()
    session.hear("select cat")
    assert session.selection() == (8, 11)


def test_go_after_a_repeated_word_then_select_next_keeps_going_after(editor) -> None:
    session = _at(editor("Tea or tea or tea."), 0).start()
    session.hear("go after tea")
    assert session.selection() == (3, 3)
    session.hear("select next")
    assert session.selection() == (10, 10)
    assert session.said[-1] == "After tea."
    session.hear("now")
    assert session.text == "Tea or tea now or tea."


def test_correct_a_repeated_word_steps_to_the_one_meant(editor) -> None:
    session = editor("Ann met Ann.").start()
    session.hear("correct ann")
    assert session.selection() == (8, 11)
    session.hear("select previous")
    assert session.selection() == (0, 3)
    assert session.said[-1] == "Correcting Ann. Say the new words."
    session.hear("Anne")
    assert session.text == "Anne met Ann."


@pytest.mark.xfail(
    strict=True,
    reason="select next reuses match offsets found before the replacement moved the text",
)
def test_select_next_after_replacing_a_match_finds_the_next_one_where_it_now_is(editor) -> None:
    session = _at(editor("The cat sat. The cat ran. The cat slept."), 0).start()
    session.hear("select the cat", "a big dog")
    assert session.text == "A big dog sat. The cat ran. The cat slept."
    session.hear("select next")
    # Today it selects ". The c" and says so: the old offsets of the second match.
    assert session.selected() == "The cat"
    assert session.said[-1] == "Selected: The cat."


def test_each_step_is_said_once(editor) -> None:
    session = editor("a b a b a").start()
    session.hear("select a")
    before = len(session.said)
    session.hear("select previous")
    assert len(session.said) == before + 1


def test_select_again_with_nothing_found_by_voice_is_written_as_words(editor) -> None:
    session = editor("").start()
    session.hear("select again")
    # Nothing to step from: the words are kept as text rather than lost.
    assert session.text == "Select again"
    assert "Not found, written as text." in session.said


def test_a_new_search_forgets_the_old_one(editor) -> None:
    session = editor("cat dog cat dog").start()
    session.hear("select cat")
    assert session.selection() == (8, 11)
    session.hear("select dog")
    assert session.selection() == (4, 7)  # nearest behind the cursor, now at the cat
    session.hear("select previous")
    assert session.said[-1] == "None before that."  # steps through dogs, not cats
    session.hear("select next")
    assert session.selection() == (12, 15)


# -- selecting by words ------------------------------------------------------ #


def test_select_through_takes_the_first_end_after_the_start(editor) -> None:
    session = _at(editor("stop one go two stop three go"), 0).start()
    session.hear("select stop through go")
    assert session.selected() == "stop one go"


def test_select_through_with_no_end_after_the_start_writes_the_words(editor) -> None:
    session = editor("go first, then stop.").start()
    session.hear("select stop through go")
    assert "Not found, written as text." in session.said
    assert session.text.startswith("go first, then stop.")


def test_select_ignores_case_and_the_punctuation_between_words(editor) -> None:
    session = editor("DEAR Sam, hello.").start()
    session.hear("select dear sam hello")
    assert session.selected() == "DEAR Sam, hello"


def test_select_that_selects_the_last_phrase_and_the_next_replaces_it(editor) -> None:
    session = editor("").start()
    session.hear("first part period", "second part")
    session.hear("select that")
    assert session.selected() == "Second part"
    assert "Selected: Second part" in session.said
    session.hear("third")
    assert session.text == "First part. Third"


def test_replace_with_changes_the_words_in_place(editor) -> None:
    session = editor("See you on Tuesday at ten.").start()
    session.hear("replace tuesday with wednesday")
    assert session.text == "See you on Wednesday at ten."  # the capital it replaced is kept
    assert session.said[-1] == "Replaced Tuesday with Wednesday."


def test_select_then_scratch_that_leaves_the_typed_text_alone(editor) -> None:
    session = editor("The quick brown fox.").start()
    session.hear("select quick", "scratch that")
    assert session.text == "The quick brown fox."
    assert session.said[-1] == "Nothing has been dictated yet."


# -- Copy All ---------------------------------------------------------------- #


def _copy_all_report(session) -> list[str]:
    # QUILL reports it on the status bar (which speaks); QUILL Lite announces it.
    return session.win.status if session.name == "quill" else session.said


def test_copy_all_says_how_much_it_copied(editor) -> None:
    session = editor("Twelve chars").start()
    session.hear("copy all")
    report = _copy_all_report(session)
    assert any("12" in line and "copied" in line.lower() for line in report), report


def test_copy_all_leaves_a_selection_exactly_as_it_was(editor) -> None:
    session = editor("Alpha beta gamma.").start()
    session.hear("select beta")
    session.hear("copy all")
    assert session.clipboard() == ["Alpha beta gamma."]
    assert session.selected() == "beta"


def test_copy_all_is_not_a_phrase_scratch_that_can_take(editor) -> None:
    session = editor("Kept.").start()
    session.hear("more words", "copy all", "scratch that")
    assert session.text == "Kept."
    assert session.clipboard() == ["Kept. More words"]


def test_copy_all_in_an_empty_document_says_so(editor) -> None:
    session = editor("").start()
    session.hear("copy all")
    report = _copy_all_report(session)
    assert any("empty" in line.lower() for line in report), report


# -- removing only the last dictated phrase ---------------------------------- #


def test_text_typed_after_the_phrase_survives_scratch_that(editor) -> None:
    session = editor("").start()
    session.hear("hello there")
    control = session.win.control
    control.SetSelection(len(session.text), len(session.text))
    control.WriteText("!")
    session.hear("scratch that")
    assert session.text == "!"


def test_scratch_that_after_a_correction_takes_the_corrected_words(editor) -> None:
    session = editor("").start()
    session.hear("meeting notes", "capitalize that")
    assert session.text == "Meeting Notes"
    session.hear("scratch that")
    assert session.text == ""


def test_scratch_that_never_reaches_past_what_this_session_dictated(editor) -> None:
    session = editor("Typed by hand.").start()
    session.hear("one more", "scratch that", "scratch that", "scratch that")
    assert session.text == "Typed by hand."


def test_scratch_that_after_stopping_and_starting_again(editor) -> None:
    session = editor("").start()
    session.hear("before the break")
    session.win.cmd_toggle_dictation()  # stop
    session.start().hear("after the break")
    session.hear("scratch that")
    assert "after the break" not in session.text.lower()
    assert session.text.lower().startswith("before the break")


# -- the twelve clips -------------------------------------------------------- #


def test_paste_clip_number_three_is_slot_three(editor) -> None:
    session = editor("")
    session.put_in_slot(3, "third")
    session.start().hear("paste clip number three")
    assert session.text == "third"


def test_a_clip_replaces_a_selection(editor) -> None:
    session = editor("Call Bob today.")
    session.put_in_slot(1, "Alice")
    session.start().hear("select bob", "paste clip one")
    assert session.text == "Call Alice today."


def test_scratch_that_after_two_clips_takes_only_the_second(editor) -> None:
    session = editor("")
    session.put_in_slot(11, "eleven")
    session.put_in_slot(12, "twelve")
    session.start().hear("paste clip eleven", "paste clip twelve", "scratch that")
    assert session.text.strip() == "eleven"


def test_a_clip_of_several_lines_goes_in_whole_and_comes_out_whole(editor) -> None:
    session = editor("")
    session.put_in_slot(2, "line one\nline two\nline three")
    session.start().hear("paste clip two")
    assert session.text == "line one\nline two\nline three"
    assert session.said[-1] == "Pasted slot 2"  # the slot, not three lines read out
    session.hear("scratch that")
    assert session.text == ""


def test_a_clip_goes_in_where_go_to_put_the_cursor(editor) -> None:
    session = editor("Dear Sam, thanks.")
    session.put_in_slot(5, "and Ann")
    session.start().hear("go after sam", "paste clip five")
    assert "Sam" in session.text and "and Ann" in session.text
    assert session.text.index("Sam") < session.text.index("and Ann") < session.text.index("thanks")


@pytest.mark.parametrize("said", ["zero", "thirteen", "one two"])
def test_a_slot_number_out_of_range_is_said_not_pasted(editor, said: str) -> None:
    session = editor("")
    for slot in range(1, 13):
        session.put_in_slot(slot, f"clip {slot}")
    session.start().hear(f"paste clip {said}")
    assert session.text == ""
    assert session.said[-1] == "Say a slot number, like paste clip three."


# -- named text containing spaces -------------------------------------------- #


def test_a_hyphenated_name_is_found_by_its_words(editor) -> None:
    session = editor("")
    session.add_named_text("Sign-off", "Regards")
    session.start().hear("insert snippet sign off")
    assert session.text == "Regards"


def test_a_name_with_capitals_is_found_said_in_small_letters(editor) -> None:
    session = editor("")
    session.add_named_text("Home Address", "1 Main Street")
    session.start().hear("insert snippet home address")
    assert session.text == "1 Main Street"


def test_the_start_of_a_long_name_is_enough_when_it_is_the_only_one(editor) -> None:
    session = editor("")
    session.add_named_text("weekly status report", "Status: green")
    session.start().hear("insert snippet weekly status")
    assert session.text == "Status: green"


def test_a_name_that_is_not_there_is_said_and_nothing_is_written(editor) -> None:
    session = editor("")
    session.add_named_text("sign off", "Regards")
    session.start().hear("insert snippet good bye")
    assert session.said[-1] == "No snippet called good bye."
    assert session.text == ""


def test_expand_abbreviation_is_the_same_as_insert_abbreviation(editor) -> None:
    session = editor("")
    session.add_abbreviation("work phone", "555 0100")
    session.start().hear("expand abbreviation work phone")
    assert session.text == "555 0100"


def test_a_snippet_cursor_mark_puts_the_cursor_inside_it(editor) -> None:
    session = editor("")
    if session.name != "quill":
        pytest.skip("QUILL Lite's named text is an abbreviation, which has no cursor mark")
    session.win._snippet_library.snippets.append(
        Snippet("1", "greeting", ";gr", "Dear ${cursor}, thanks.")
    )
    session.start().hear("insert snippet greeting")
    assert session.text == "Dear , thanks."
    assert session.selection() == (5, 5)
    session.hear("Sam")
    assert session.text == "Dear Sam, thanks."


# -- every capitalization mode ----------------------------------------------- #


def test_no_space_on_joins_words_until_no_space_off(editor) -> None:
    session = editor("").start()
    # Not "quill editor": a phrase that opens with QUILL is a command phrase.
    session.hear("no space on", "my site dot com", "no space off", "is the site")
    assert session.text.lower().startswith("mysitedotcom")
    assert session.text.endswith(" is the site")


def test_a_phrase_opening_with_quill_is_never_typed_by_mistake(editor) -> None:
    session = editor("").start()
    session.hear("quill editor dot com")
    assert session.text == ""
    assert session.said[-1].startswith("Not a command.")


def test_all_caps_on_takes_over_from_caps_on_and_all_caps_off_ends_both(editor) -> None:
    # One capitals mode at a time: the last said wins, and either "off" is
    # "back to ordinary capitals", as the reference puts it.
    session = editor("").start()
    session.hear("caps on", "all caps on")
    assert shared._controller.mode_text == "all caps"
    session.hear("loud words", "all caps off")
    assert shared._controller.mode_text == ""
    session.hear("plain words", "caps on", "title words", "caps off")
    assert session.text == "LOUD WORDS plain words Title Words"


def test_caps_on_twice_is_said_and_stays_on(editor) -> None:
    session = editor("").start()
    session.hear("caps on", "caps on", "two words")
    assert session.text == "Two Words"


def test_capitalize_that_with_nothing_dictated_says_so(editor) -> None:
    session = editor("typed").start()
    session.hear("capitalize that")
    assert session.text == "typed"
    assert session.said[-1] == "Nothing has been dictated yet."


def test_all_caps_that_after_a_sentence_keeps_its_punctuation(editor) -> None:
    session = editor("").start()
    session.hear("stop right there exclamation point", "all caps that")
    assert session.text == "STOP RIGHT THERE!"


def test_caps_on_lasts_across_a_full_stop(editor) -> None:
    session = editor("").start()
    session.hear("caps on", "one word period two words", "caps off")
    assert session.text == "One Word. Two Words"


# -- an email address, character by character -------------------------------- #


def test_an_address_with_digits_dashes_and_an_underscore(editor) -> None:
    session = editor("").start()
    session.hear("start spelling")
    session.hear("alpha underscore bravo dash two zero at sign charlie dot delta")
    session.hear("stop spelling")
    assert session.text == "a_b-20@c.d"


def test_capitals_in_a_spelled_address(editor) -> None:
    session = editor("").start()
    session.hear("start spelling", "capital juliet oscar at sign capital echo dot io")
    session.hear("stop spelling")
    # "io" is not a letter word, so it is left out rather than guessed.
    assert session.text == "Jo@E."


def test_spell_that_replaces_the_last_phrase_with_letters(editor) -> None:
    session = editor("").start()
    session.hear("write to john at example")
    session.hear("spell that")
    assert session.said[-1].startswith("Spell ")
    session.hear("juliet oscar at sign echo x-ray dot charlie oscar")
    assert session.text == "jo@ex.co"
    # One phrase only: the next is words again.
    session.hear("thanks")
    assert session.text == "jo@ex.co thanks"


def test_stop_spelling_then_words_get_their_space_back(editor) -> None:
    session = editor("Mail").start()
    session.hear("start spelling", "alpha at sign bravo dot charlie", "stop spelling")
    session.hear("today")
    assert session.text == "Mail a@b.c today"


def test_dot_is_a_word_outside_spelling(editor) -> None:
    session = editor("").start()
    session.hear("connect the dot")
    assert session.text == "Connect the dot"


# -- the Markdown punctuation vocabulary ------------------------------------- #

#: What "Text." becomes when each Markdown or code word is said before "word",
#: exactly. "Text." ends a sentence, so the word after it takes a capital; marks
#: that start a line put the new line in front of themselves; a tilde and a
#: caret join the words either side, as an underscore does.
_EXACT = {
    "backtick": "Text. `Word",
    "back quote": "Text. `Word",
    "triple backtick": "Text.\n```\nWord",
    "code fence": "Text.\n```\nWord",
    "tilde": "Text.~Word",
    "vertical bar": "Text. | Word",
    "pipe symbol": "Text. | Word",
    "caret": "Text.^Word",
    "greater than sign": "Text. > Word",
    "less than sign": "Text. < Word",
    "bullet": "Text.\n- Word",
    "list item": "Text.\n- Word",
    "numbered item": "Text.\n1. Word",
    "block quote": "Text.\n> Word",
    **{
        f"heading {said}": "Text.\n" + "#" * level + " Word"
        for level, name in enumerate(("one", "two", "three", "four", "five", "six"), 1)
        for said in (name, str(level))
    },
}

_MARKDOWN_GROUPS = ("Markdown and code", "Starting a line (say these first)")
_MARKDOWN_PHRASES = [" ".join(m.phrase) for m in MARKS if m.group in _MARKDOWN_GROUPS]


def test_the_exact_table_names_every_markdown_word() -> None:
    assert sorted(_EXACT) == sorted(_MARKDOWN_PHRASES)


@pytest.mark.parametrize("phrase", _MARKDOWN_PHRASES)
def test_each_markdown_word_writes_exactly_its_mark(editor, phrase: str) -> None:
    session = editor("Text.").start()
    session.hear(phrase + " word")
    assert session.text == _EXACT[phrase]


@pytest.mark.parametrize("phrase", ["bullet", "numbered item", "block quote", "heading two"])
def test_scratch_that_takes_a_line_mark_with_its_words(editor, phrase: str) -> None:
    session = editor("Text.").start()
    session.hear(phrase + " word", "scratch that")
    assert session.text == "Text."


def test_a_backtick_pair_wraps_code_inside_a_sentence(editor) -> None:
    session = editor("").start()
    session.hear("run backtick pytest backtick now")
    assert session.text == "Run `pytest` now"


def test_a_code_fence_block_dictated_line_by_line(editor) -> None:
    session = editor("").start()
    session.hear("code fence", "print hello", "code fence")
    assert session.text == "```\nPrint hello\n```\n"
    assert session.said[-3:] == ["Code fence", "Print hello", "Code fence"]


@pytest.mark.parametrize("phrase", ["bullet", "block quote", "heading one", "backtick"])
def test_literal_before_any_markdown_word_writes_the_word(editor, phrase: str) -> None:
    session = editor("").start()
    session.hear(f"literal {phrase} here")
    assert session.text.lower() == f"{phrase} here"
