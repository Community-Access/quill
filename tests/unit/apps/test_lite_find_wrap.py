"""Whether a search carries on from the other end, and how a miss is reported.

QuillLite always wrapped, in both directions, with no way to say otherwise. That
is not a preference about tidiness. Somebody working down a document by F3 is
using the *end* of the search as the signal that they have finished; a search that
silently starts again at the top has moved them somewhere they did not ask to go,
and they find that out by reading. QUILL has had ``wrap_find`` all along, so this
is also the two products agreeing about a setting they both offer.

The other half is the report. A miss is the one failure a search can have, and F3
is pressed in runs -- "Not found" spoken on every press is the fastest way to make
somebody turn speech off altogether, which is why the tone alone is the default and
the words are a choice (``find_not_found_feedback``, the same four options as
``action_feedback``).

And the two misses are different facts, so they get different sentences. With
wrapping on, there is no such text in the document and the fix is a new pattern.
With wrapping off, the search has only run out of document in the direction it was
going, and the fix is to go to the other end -- so the sentence says which end it
stopped at rather than claiming the text is not there.
"""

from __future__ import annotations

from quill.core.sound_events import SoundEvent

DOC = "alpha bravo\ncharlie alpha\ndelta\n"


def _find(win, needle: str, *, reverse: bool = False) -> bool:
    return win._do_find(
        {"needle": needle, "match_case": False, "whole_word": False, "mode": "normal"},
        reverse,
    )


# --------------------------------------------------------------------- #
# Wrapping
# --------------------------------------------------------------------- #


def test_with_wrapping_on_find_next_carries_on_from_the_top(lite_window) -> None:
    win = lite_window(DOC, cursor=0)
    win.app.settings.wrap_find = True
    win.control.SetInsertionPoint(len(DOC))

    assert _find(win, "alpha") is True
    assert win.control.GetSelection() == (0, 5)
    assert SoundEvent.SEARCH_WRAPPED in win.cues


def test_with_wrapping_off_find_next_stops_at_the_end(lite_window) -> None:
    win = lite_window(DOC, cursor=0)
    win.app.settings.wrap_find = False
    win.control.SetInsertionPoint(len(DOC))

    assert _find(win, "alpha") is False
    assert win.control.GetSelection() == (len(DOC), len(DOC)), "the caret must not move"


def test_with_wrapping_on_find_previous_carries_on_from_the_bottom(lite_window) -> None:
    win = lite_window(DOC, cursor=0)
    win.app.settings.wrap_find = True

    assert _find(win, "alpha", reverse=True) is True
    assert win.control.GetSelection() == (20, 25)
    assert SoundEvent.SEARCH_WRAPPED in win.cues


def test_with_wrapping_off_find_previous_stops_at_the_start(lite_window) -> None:
    """Both directions, because a setting that only held one way would be worse
    than none: the user would learn to trust it and be wrong half the time."""
    win = lite_window(DOC, cursor=0)
    win.app.settings.wrap_find = False

    assert _find(win, "alpha", reverse=True) is False
    assert win.control.GetInsertionPoint() == 0


def test_wrapping_off_does_not_stop_an_ordinary_find_working(lite_window) -> None:
    win = lite_window(DOC, cursor=0)
    win.app.settings.wrap_find = False

    assert _find(win, "charlie") is True
    assert win.control.GetSelection() == (12, 19)


# --------------------------------------------------------------------- #
# What a miss says
# --------------------------------------------------------------------- #


def test_a_genuine_miss_names_the_needle(lite_window) -> None:
    win = lite_window(DOC, cursor=0)
    win.app.settings.wrap_find = True
    _find(win, "zulu")
    assert "Not found: zulu" in win.status_messages


def test_running_out_of_document_says_which_end_and_why(lite_window) -> None:
    """Not the same fact as "there is no such text", and not the same fix."""
    win = lite_window(DOC, cursor=0)
    win.app.settings.wrap_find = False
    win.control.SetInsertionPoint(len(DOC))
    _find(win, "alpha")
    said = win.status_messages[-1]
    assert "end of the document" in said
    assert "wrapping is off" in said


def test_running_out_backwards_names_the_start(lite_window) -> None:
    win = lite_window(DOC, cursor=0)
    win.app.settings.wrap_find = False
    _find(win, "alpha", reverse=True)
    assert "start of the document" in win.status_messages[-1]


def test_a_miss_is_a_tone_and_not_speech_by_default(lite_window) -> None:
    """F3 is pressed in runs. "Not found" on every press is what makes people
    turn the speech off altogether."""
    win = lite_window(DOC, cursor=0)
    _find(win, "zulu")
    assert SoundEvent.SEARCH_NOT_FOUND in win.cues
    assert win.app.voice.said == []


def test_a_miss_can_be_spoken_when_asked(lite_window) -> None:
    win = lite_window(DOC, cursor=0)
    win.app.settings.find_not_found_feedback = "speech"
    _find(win, "zulu")
    assert win.cues == []
    assert win.app.voice.said == ["Not found: zulu"]


def test_a_miss_can_be_both(lite_window) -> None:
    win = lite_window(DOC, cursor=0)
    win.app.settings.find_not_found_feedback = "both"
    _find(win, "zulu")
    assert SoundEvent.SEARCH_NOT_FOUND in win.cues
    assert win.app.voice.said == ["Not found: zulu"]


def test_a_miss_can_be_neither_and_still_reaches_the_status_bar(lite_window) -> None:
    """The bar is the record, not the feedback. A mode about audio has no business
    emptying it -- somebody who chose silence is exactly the person who then goes
    and reads it."""
    win = lite_window(DOC, cursor=0)
    win.app.settings.find_not_found_feedback = "silent"
    _find(win, "zulu")
    assert win.cues == []
    assert win.app.voice.said == []
    assert "Not found: zulu" in win.status_messages


def test_the_find_miss_setting_is_independent_of_action_feedback(lite_window) -> None:
    """Two settings on purpose: somebody may want every success spoken and the
    failure kept to a tone, or the exact opposite."""
    win = lite_window(DOC, cursor=0)
    win.app.settings.action_feedback = "speech"
    win.app.settings.find_not_found_feedback = "sound"
    _find(win, "zulu")
    assert SoundEvent.SEARCH_NOT_FOUND in win.cues
    assert win.app.voice.said == []
