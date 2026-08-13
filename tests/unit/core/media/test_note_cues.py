"""Speaking a bookmark's note when playback reaches it (x.md item 4).

Local audio already had positioned, note-bearing marks; what it lacked was the
half that matters while you are listening rather than managing a list --
arriving at 14:32 and being read the note you left there.

The interesting behaviour is all in what it *refuses* to say. A naive "any mark
between the last position and this one" works during playback and is awful
everywhere else: it reads out twenty notes when you drag the scrubber, repeats
one when you skip back, and announces the same note forever while paused. Each
of those is a rule in ``cues_reached`` and a test here.
"""

from __future__ import annotations

from quill.core.media.bookmarks import MediaBookmark
from quill.core.media.note_cues import announcement_for, cues_reached


def _mark(position_ms: int, note: str = "a point", label: str = "") -> MediaBookmark:
    return MediaBookmark(position_ms=position_ms, label=label, note=note)


# -- reaching one -----------------------------------------------------------


def test_a_mark_between_two_ticks_is_reached() -> None:
    assert [m.position_ms for m in cues_reached([_mark(5_000)], 4_500, 5_500)] == [5_000]


def test_a_mark_exactly_on_the_current_position_is_reached() -> None:
    """Closed at the end, so a mark landing on the tick is not skipped."""
    assert cues_reached([_mark(5_000)], 4_000, 5_000)


def test_a_mark_on_the_previous_position_is_not_announced_twice() -> None:
    """Half-open at the start -- this is what makes it fire exactly once."""
    assert cues_reached([_mark(5_000)], 5_000, 5_800) == []


def test_several_marks_in_one_tick_come_back_in_timeline_order() -> None:
    marks = [_mark(5_400, "second"), _mark(5_100, "first")]
    assert [m.note for m in cues_reached(marks, 5_000, 5_500)] == ["first", "second"]


def test_a_small_stutter_still_counts_as_playback() -> None:
    """Slack for a dropped tick: a busy UI thread must not lose a note."""
    assert cues_reached([_mark(6_000)], 5_000, 6_500)


# -- and, more importantly, refusing to -------------------------------------


def test_seeking_forwards_announces_nothing() -> None:
    """The feature's worst possible behaviour: dragging the scrubber across an
    hour and being read every note it passed."""
    marks = [_mark(ms) for ms in (10_000, 20_000, 30_000, 40_000)]
    assert cues_reached(marks, 5_000, 3_600_000) == []


def test_seeking_backwards_announces_nothing() -> None:
    """Skipping back ten seconds must not repeat what you just heard."""
    assert cues_reached([_mark(5_000)], 9_000, 1_000) == []


def test_a_paused_player_announces_nothing() -> None:
    """Position reports keep arriving while paused; nothing has been crossed,
    so a range check would announce the same note forever."""
    assert cues_reached([_mark(5_000)], 5_000, 5_000) == []


def test_a_bookmark_with_no_note_says_nothing() -> None:
    """A bookmark is a place to jump to. Announcing one with nothing to say
    would be noise."""
    assert cues_reached([_mark(5_000, note="")], 4_500, 5_500) == []
    assert cues_reached([_mark(5_000, note="   ")], 4_500, 5_500) == []


def test_a_noteless_bookmark_does_not_hide_a_noted_one() -> None:
    marks = [_mark(5_100, note=""), _mark(5_200, note="say this")]
    assert [m.note for m in cues_reached(marks, 5_000, 5_500)] == ["say this"]


def test_no_marks_means_nothing_to_announce() -> None:
    assert cues_reached([], 0, 1_000) == []


def test_the_seek_threshold_is_adjustable() -> None:
    """A caller that ticks less often can widen it without editing the rule."""
    assert cues_reached([_mark(9_000)], 1_000, 10_000, max_advance_ms=30_000)


# -- what it says -----------------------------------------------------------


def test_an_unlabelled_note_is_marked_so_it_is_not_heard_as_the_audio() -> None:
    """A bare sentence spoken over an audiobook sounds like part of the book."""
    assert announcement_for(_mark(1_000, "check this")) == "Note: check this"


def test_a_labelled_mark_speaks_its_label() -> None:
    assert announcement_for(_mark(1_000, "the good bit", label="Chapter 4")) == (
        "Chapter 4: the good bit"
    )


def test_the_announcement_carries_no_timestamp() -> None:
    """You are at that moment, so saying it aloud is noise -- and a spoken
    "3:10" is ambiguous, which is why the stack says "3 minutes 10 seconds"
    (rule A-8)."""
    spoken = announcement_for(_mark(190_000, "here"))
    assert "3:10" not in spoken and "190" not in spoken
