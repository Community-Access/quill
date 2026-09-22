"""Window > Close Other Documents in QuillLite (Ctrl+Shift+F4).

Reported by a user who opened QuillLite to sixty-nine restored windows and found
that the only way back to one document was Ctrl+W sixty-eight times, answering a
save prompt on each. QUILL has had this command since 2026-06-15; QuillLite
never got it, which is the wrong direction for a key learned in one editor and
pressed in the other.

Then, from the same user: the prompt itself has to carry **Save All** and
**Don't Save Any**, "so that a user can save all open with one command or
discard all with one selection". A command that exists to save sixty-eight
keystrokes must not charge sixty-eight prompts instead.

Two branches matter most and both are here: the **latch** (one "any" answers
every remaining document) and the **failed save** (a save that does not happen
must never read as consent to discard -- closing on a failed save *is* the data
loss).
"""

from __future__ import annotations

import pytest

from quill.core.close_prompt import CANCEL, DISCARD, DISCARD_ALL, SAVE, SAVE_ALL


def _second_window(window):
    """Another document in the same app, of the same stub shape as the first.

    Its ``save`` is recorded **per instance**, not on the stub class: the real
    ``DocumentFileMixin.save`` is what ``test_lite_save_path.py`` exercises, and
    shadowing it in the shared conftest would quietly hollow out those tests.
    What this command depends on is only the True/False a save comes back with,
    which is exactly what a per-instance stand-in can give it honestly.
    """
    other = type(window)("other", 0, window.editor.mode)
    other.app = window.app
    other.number = len(window.app.frames) + 1
    other.saves = 0
    other.save_succeeds = True

    def _save(target=None, text=None, _frame=other):
        _frame.saves += 1
        if not _frame.save_succeeds:
            return False
        _frame.modified = False
        return True

    other.save = _save
    window.app.frames.append(other)
    return other


@pytest.fixture
def answers(monkeypatch):
    """Drive the bulk prompt from a script, and record what it was asked.

    Patched where ``lite.py`` imports it -- inside the method, so the module
    under test is the one that has to be patched, not the one that defines it
    (the trap ``tests/unit/apps/conftest.py`` names for every dialog).
    """
    asked: list[str] = []
    scripted: list[str] = []

    def fake(_parent, question):
        asked.append(question)
        return scripted.pop(0) if scripted else DISCARD

    monkeypatch.setattr("quill.ui.bulk_close_dialog.ask_bulk_unsaved", fake)
    return type("Answers", (), {"asked": asked, "script": scripted})()


def test_it_closes_every_other_window_and_keeps_this_one(lite_window, answers) -> None:
    window = lite_window("first")
    second = _second_window(window)
    third = _second_window(window)

    window.cmd_close_other_windows()

    assert second.closed == 1
    assert third.closed == 1
    assert window.closed == 0
    assert window.app.frames == [window]


def test_an_unmodified_window_is_never_asked_about(lite_window, answers) -> None:
    """The prompt is about losing work. There is none to lose here."""
    window = lite_window("first")
    _second_window(window)

    window.cmd_close_other_windows()

    assert answers.asked == []


def test_it_says_how_many_it_closed(lite_window, answers) -> None:
    """The one fact the reader cannot deduce from the windows that vanished."""
    window = lite_window("first")
    _second_window(window)
    _second_window(window)

    window.cmd_close_other_windows()

    assert "Closed 2 other documents" in " ".join(window.app.voice.said)


def test_one_window_open_says_so_rather_than_doing_nothing(lite_window, answers) -> None:
    """A command that answers silently is one somebody presses twice."""
    window = lite_window("only")

    window.cmd_close_other_windows()

    assert window.closed == 0
    assert "This is the only document open" in " ".join(window.app.voice.said)


def test_each_modified_window_is_focused_before_it_is_asked_about(lite_window, answers) -> None:
    """An MDI child cannot be raised, so the prompt would name the wrong document."""
    window = lite_window("first")
    second = _second_window(window)
    second.modified = True

    window.cmd_close_other_windows()

    assert len(answers.asked) == 1
    assert window.app.focused[0] is second
    assert window.app.focused[-1] is window


def test_the_question_says_how_many_more_are_waiting(lite_window, answers) -> None:
    """What makes Don't Save Any the obvious answer rather than a discovery."""
    window = lite_window("first")
    for _ in range(3):
        _second_window(window).modified = True
    answers.script.extend([DISCARD, DISCARD, DISCARD])

    window.cmd_close_other_windows()

    assert "2 other documents also have unsaved changes" in answers.asked[0]
    assert "1 other document also has unsaved changes" in answers.asked[1]
    # The last one has nothing behind it, so it says nothing about others.
    assert "also have unsaved changes" not in answers.asked[2]
    assert "also has unsaved changes" not in answers.asked[2]


def test_dont_save_any_answers_every_remaining_document(lite_window, answers) -> None:
    """The whole point: one selection, not sixty-seven."""
    window = lite_window("first")
    others = [_second_window(window) for _ in range(5)]
    for frame in others:
        frame.modified = True
    answers.script.append(DISCARD_ALL)

    window.cmd_close_other_windows()

    assert len(answers.asked) == 1  # asked once, answered for all five
    assert all(frame.closed == 1 for frame in others)
    assert "discarded 5 unsaved" in " ".join(window.app.voice.said)


def test_save_all_saves_every_remaining_document(lite_window, answers) -> None:
    window = lite_window("first")
    others = [_second_window(window) for _ in range(4)]
    for frame in others:
        frame.modified = True
        frame.path = None
    answers.script.append(SAVE_ALL)

    window.cmd_close_other_windows()

    assert len(answers.asked) == 1
    assert all(frame.saves == 1 for frame in others)
    assert "saved 4" in " ".join(window.app.voice.said)


def test_save_and_dont_save_apply_to_one_document_only(lite_window, answers) -> None:
    """Neither of the single answers may latch -- they are about this one."""
    window = lite_window("first")
    first_other = _second_window(window)
    second_other = _second_window(window)
    first_other.modified = True
    second_other.modified = True
    answers.script.extend([SAVE, DISCARD])

    window.cmd_close_other_windows()

    assert len(answers.asked) == 2
    assert first_other.saves == 1
    assert second_other.saves == 0
    said = " ".join(window.app.voice.said)
    assert "saved 1" in said
    assert "discarded 1 unsaved" in said


def test_cancel_stops_the_whole_thing(lite_window, answers) -> None:
    """ "Not this one" means stop, not "skip it and close the other sixty-six"."""
    window = lite_window("first")
    second = _second_window(window)
    third = _second_window(window)
    second.modified = True
    answers.script.append(CANCEL)

    window.cmd_close_other_windows()

    assert second.closed == 0
    assert third.closed == 0
    assert window.closed == 0
    assert window.app.focused[-1] is window
    assert "Nothing closed." in " ".join(window.app.voice.said)


def test_cancel_partway_keeps_what_is_still_open_and_says_so(lite_window, answers) -> None:
    window = lite_window("first")
    second = _second_window(window)
    third = _second_window(window)
    third.modified = True
    answers.script.append(CANCEL)

    window.cmd_close_other_windows()

    assert second.closed == 1
    assert third.closed == 0
    said = " ".join(window.app.voice.said)
    assert "Closed 1 other document" in said
    assert "1 document still open" in said


def test_a_failed_save_stops_and_never_reads_as_consent_to_discard(lite_window, answers) -> None:
    """Closing on a failed save *is* the data loss."""
    window = lite_window("first")
    doomed = _second_window(window)
    doomed.modified = True
    doomed.save_succeeds = False
    answers.script.append(SAVE)

    window.cmd_close_other_windows()

    assert doomed.closed == 0
    assert "was not saved" in " ".join(window.app.voice.said)


def test_a_failed_save_breaks_a_save_all_latch(lite_window, answers) -> None:
    """ "Save all" cannot keep meaning "save all" once saving has stopped working."""
    window = lite_window("first")
    good = _second_window(window)
    doomed = _second_window(window)
    good.modified = True
    doomed.modified = True
    doomed.save_succeeds = False
    answers.script.append(SAVE_ALL)

    window.cmd_close_other_windows()

    assert good.closed == 1
    assert doomed.closed == 0
    assert "was not saved" in " ".join(window.app.voice.said)


def test_a_closed_window_is_not_asked_to_save_twice(lite_window, answers) -> None:
    """Marked clean before Close, exactly as Exit does it.

    Without it the close handler asks the same question again, which is two
    prompts per document -- the cost this command exists to remove.
    """
    window = lite_window("first")
    second = _second_window(window)
    second.modified = True
    answers.script.append(DISCARD)

    window.cmd_close_other_windows()

    assert second.modified is False
    assert second.closed == 1
