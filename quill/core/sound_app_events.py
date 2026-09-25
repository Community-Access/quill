"""Which sound events each app can actually fire.

Reported by ear, 2026-09-10: *"there is 119 entries in that soundpack listing,
really, wow! are all of them supported in both quill and quill lite?"* They were
not. The Sound Scheme window listed every event the enum **declares**, and a
declaration is not a call site: most of those rows could be previewed, silenced
and re-sounded, and would then never make a noise, because nothing in that app
ever posts them. A settings list that promises more than the code delivers is
worse than a shorter one -- somebody spends a minute choosing a sound for an
event that will never fire, and has no way to find out.

So each app declares what it fires, the window shows that, and
``tests/unit/core/test_sound_app_events.py`` reads the source back and fails if
a roster and its code disagree in either direction:

* an event **fired but not rostered** would be missing from the window, so its
  sound could not be changed or switched off;
* an event **rostered but not fired** is the original complaint, a row that
  does nothing.

QUILL is deliberately not enumerated: it is the full editor and the intent is
that it fires everything, so its roster is "all of them" and the gate holds it
to that. An event QUILL declares and does not post is a gap in QUILL, not an
exception to be written down here.
"""

from __future__ import annotations

from quill.core.sound_events import SoundEvent

__all__ = ["APP_ROSTERS", "QUILLLITE_EVENTS", "events_for", "is_editor_app"]

#: Everything QUILL Lite posts. Small on purpose: it is a text editor, so it has
#: no assistant, no conversation mode, no radio and no dictation, and rows for
#: those would be rows that cannot fire.
QUILLLITE_EVENTS: frozenset[str] = frozenset({
    SoundEvent.APP_STARTED,
    SoundEvent.APP_EXITING,
    SoundEvent.DOCUMENT_CREATED,
    SoundEvent.DOCUMENT_OPENED,
    SoundEvent.DOCUMENT_SAVED,
    SoundEvent.DOCUMENT_CLOSED,
    SoundEvent.PRINT_STARTED,
    SoundEvent.PRINT_COMPLETE,
    SoundEvent.TEXT_CUT,
    SoundEvent.TEXT_COPIED,
    SoundEvent.TEXT_PASTED,
    SoundEvent.TEXT_DELETED,
    SoundEvent.UNDO_PERFORMED,
    SoundEvent.REDO_PERFORMED,
    SoundEvent.NOTHING_TO_UNDO,
    SoundEvent.SPELLING_ALERT,
    SoundEvent.WORD_CORRECTED,
    SoundEvent.ABBREVIATION_EXPANDED,
    SoundEvent.SEARCH_FOUND,
    SoundEvent.SEARCH_NOT_FOUND,
    SoundEvent.SEARCH_WRAPPED,
    # F8 and Shift+F8. The clips shipped in the Ink pack from the start and
    # QUILL Lite posted neither, so the two rows were missing from its Sound Events
    # window as well -- an earcon nobody could hear and nobody could switch off.
    # Reported by ear, 2026-09-10, alongside the extend-mode bug itself.
    SoundEvent.SELECTION_STARTED,
    SoundEvent.SELECTION_COMPLETED,
    SoundEvent.ERROR,
})

# Not here, and each absence is a decision rather than an oversight: QUILL Lite
# has no long-running work to finish (TASK_COMPLETE), no information or question
# boxes of its own (INFORMATION, QUESTION, WARNING), no command that toggles
# sound (SOUND_ON, SOUND_OFF), and no edge or heading cue wired yet
# (DOCUMENT_TOP, DOCUMENT_BOTTOM, HEADING_JUMPED). Any of them can join the day
# something posts it -- and the gate will insist on it, in both directions.

#: App id -> the events that app fires. An app absent from here gets everything,
#: which is the right default for the full editor and for anything new: an app
#: whose roster nobody has written should show too much rather than too little,
#: because a missing row is a sound somebody cannot switch off.
APP_ROSTERS: dict[str, frozenset[str]] = {
    "quilllite": QUILLLITE_EVENTS,
}


def events_for(app_id: str) -> frozenset[str]:
    """The events *app_id* can fire, or every declared event when unrostered."""
    roster = APP_ROSTERS.get(app_id)
    if roster is not None:
        return roster
    return frozenset(event.value for event in SoundEvent)


def is_editor_app(app_id: str) -> bool:
    """Whether *app_id* has a roster of its own. For a window deciding whether
    to offer the "show every event" escape hatch at all."""
    return app_id in APP_ROSTERS
