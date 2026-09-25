"""An app's sound roster must match the sounds it actually fires.

Reported by ear, 2026-09-10: *"there is 119 entries in that soundpack listing,
really, wow! are all of them supported in both quill and quill lite?"* They were
not. The Sound Scheme window listed every event the enum **declares**, and only
38 of 141 had a call site anywhere -- so most rows could be previewed, silenced
and re-sounded, and would then never make a noise. A settings list that promises
more than the code delivers is worse than a shorter one: somebody spends a
minute choosing a sound for something that will never happen, and has no way to
discover that.

This gate reads each app's own modules back and compares them with its roster,
and it fails **both ways**:

* rostered but never posted -- a row that does nothing, the original complaint;
* posted but not rostered -- worse, because the sound fires and the window does
  not offer it, so nobody can change it or switch it off.

The scan itself lives in :mod:`quill.tools.sound_event_audit`, which walks the
syntax tree rather than the text. That is not fussiness: three hand-rolled greps
answered this question three different ways and every one was wrong -- a regex
over ``post_sound(`` misses the cues routed through a helper, widening it to any
event-shaped string counts docstrings, and neither notices the
``_announce(..., sound=SoundEvent.X)`` form most of the companion apps use.

Where the audit does guess, it guesses *wide*: in a file that posts at all, an
event it merely names is counted. Chasing table-dispatched cues precisely would
mean a dataflow analysis, and the two wrong answers are not equal -- crediting
an event that is only mentioned costs a spare row in a settings window, while
missing a real one means a sound nobody can switch off.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.sound_app_events import APP_ROSTERS, events_for
from quill.core.sound_events import SoundEvent
from quill.tools.sound_event_audit import posted_events, unposted_events

_REPO = Path(__file__).resolve().parents[3]

#: Where each rostered app's own code lives. Only its own: QUILL Lite must not
#: be credited with a cue that only Quill Radio posts.
_APP_SOURCES: dict[str, tuple[str, ...]] = {
    "quilllite": ("quill/apps/lite*.py", "quill/core/lite/*.py"),
}

_NAMES = {event.name: event.value for event in SoundEvent}


def _mentioned(patterns: tuple[str, ...]) -> set[str]:
    """What an app posts, measured structurally.

    Delegated to :mod:`quill.tools.sound_event_audit` rather than done with a
    regex here, because three hand-rolled greps gave three different answers to
    this exact question and every one of them was wrong: one missed the cues
    that go through a helper, one counted docstrings, and none saw the
    ``_announce(..., sound=SoundEvent.X)`` form the companion apps use.
    """
    del patterns  # the audit knows where each app's code lives
    return set(posted_events("quilllite"))


def test_every_rostered_event_is_actually_fired() -> None:
    """The original complaint: rows in a settings window that can never sound."""
    for app_id, patterns in _APP_SOURCES.items():
        rostered = {str(event) for event in APP_ROSTERS[app_id]}
        fired = _mentioned(patterns)
        idle = sorted(rostered - fired)
        assert idle == [], f"{app_id} lists but never plays: {idle}"


def test_every_fired_event_is_rostered() -> None:
    """The worse direction: a sound that fires and cannot be switched off."""
    for app_id, patterns in _APP_SOURCES.items():
        rostered = {str(event) for event in APP_ROSTERS[app_id]}
        unreachable = sorted(_mentioned(patterns) - rostered)
        assert unreachable == [], f"{app_id} plays but does not list: {unreachable}"


def test_an_app_with_no_roster_is_offered_everything() -> None:
    """The right default for the full editor, and for anything added later: an
    app whose roster nobody has written should show too much rather than too
    little, because a missing row is a sound somebody cannot silence."""
    everything = {event.value for event in SoundEvent}
    assert events_for("quill") == everything
    assert events_for("something-nobody-has-written-yet") == everything


def test_a_rostered_app_is_offered_only_its_own() -> None:
    lite = events_for("quilllite")
    assert lite < {event.value for event in SoundEvent}
    assert SoundEvent.TEXT_PASTED in lite
    # No assistant, no conversation mode, no radio: rows that could not fire.
    assert SoundEvent.AI_RESPONSE_RECEIVED not in lite
    assert SoundEvent.CONVERSATION_WAKE not in lite
    assert SoundEvent.RADIO_PLAYING not in lite


def test_the_desktop_moments_are_all_in_quilllites_roster() -> None:
    """The set every desktop suite has had since the nineties. These are the
    ones a screen reader says nothing about, which is what makes an earcon the
    only feedback they can have -- so a text editor with none of them wired was
    the wrong way round."""
    for event in (
        SoundEvent.APP_STARTED,
        SoundEvent.APP_EXITING,
        SoundEvent.DOCUMENT_OPENED,
        SoundEvent.DOCUMENT_SAVED,
        SoundEvent.DOCUMENT_CLOSED,
        SoundEvent.TEXT_CUT,
        SoundEvent.TEXT_COPIED,
        SoundEvent.TEXT_PASTED,
        SoundEvent.TEXT_DELETED,
        SoundEvent.UNDO_PERFORMED,
        SoundEvent.REDO_PERFORMED,
        SoundEvent.PRINT_STARTED,
        SoundEvent.PRINT_COMPLETE,
    ):
        assert event in APP_ROSTERS["quilllite"], event


# ---------------------------------------------------------------------------
# Coverage: an event nothing posts is a promise nothing keeps


def test_quill_posts_every_event_it_owns() -> None:
    """QUILL is the full editor, so its answer to "do you support all of them?"
    has to be yes. It was 45 of 141 when this was first measured -- the missing
    ones being cut, copy, paste, delete, undo, redo, open, close, print, start
    and exit, which is to say every moment a screen reader is silent about and
    an earcon is therefore the only feedback available."""
    assert unposted_events("quill", own_only=True) == []


def test_every_named_event_is_posted_somewhere_in_the_product() -> None:
    """A declared event nothing ever posts is a row in the Sound Scheme window
    that can be chosen, previewed and switched off, and will never be heard."""
    everywhere = posted_events("quill") | posted_events("companions") | posted_events("quilllite")
    ladders = ("indent_", "progress_", "copy_slot_", "bookmark_slot_")
    orphans = sorted(
        event.value
        for event in SoundEvent
        if event.value not in everywhere
        and event.value != "keepalive"  # posted by the manager's own timer
        and not event.value.startswith(ladders)
    )
    assert orphans == [], f"declared but nothing plays them: {orphans}"
