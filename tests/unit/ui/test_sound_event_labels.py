"""Every sound event is findable, named, and in exactly one group.

The Sound Scheme window is built from :data:`EVENT_GROUPS`, so an event that
exists in the enum and not in that table is a sound the user can hear and cannot
reach -- no way to preview it, change it, or switch it off. That failure is
invisible: nothing throws, the window simply has one fewer row than it should,
and nobody counts the rows.

wx-free on purpose, so it runs everywhere and fails fast.
"""

from __future__ import annotations

from quill.core.sound_events import SoundEvent
from quill.ui.sound_event_labels import EVENT_GROUPS, GROUP_FOR, LABELS, label_for


def _listed() -> list[str]:
    return [event for _group, events in EVENT_GROUPS for event in events]


def test_every_declared_event_is_in_a_group() -> None:
    """Otherwise it is a sound you can hear and cannot reach."""
    missing = sorted({event.value for event in SoundEvent} - set(_listed()))
    assert missing == [], f"events with no group: {missing}"


def test_no_group_lists_an_event_that_does_not_exist() -> None:
    """A row for an event nothing ever posts is a row that can never be tested,
    and a preview button that plays nothing."""
    unknown = sorted(set(_listed()) - {event.value for event in SoundEvent})
    assert unknown == [], f"groups name events that do not exist: {unknown}"


def test_no_event_is_in_two_groups() -> None:
    """The list index maps back to an event; a duplicate makes that ambiguous."""
    listed = _listed()
    assert len(listed) == len(set(listed))


def test_every_event_has_a_human_label() -> None:
    """An id is an honest last resort, not an acceptable shipping state."""
    bare = sorted(event for event in _listed() if event not in LABELS)
    assert bare == [], f"events with no label: {bare}"


def test_a_label_never_comes_back_empty() -> None:
    """A blank row is one nobody notices; an ugly id is one somebody fixes."""
    assert label_for("some_event_nobody_added") == "some_event_nobody_added"
    assert label_for("") == ""


def test_a_label_is_the_moment_not_the_mechanism() -> None:
    assert label_for("text_pasted") == "Paste"
    assert label_for("nothing_to_undo") == "Nothing left to undo"


def test_group_lookup_agrees_with_the_groups() -> None:
    for group, events in EVENT_GROUPS:
        for event in events:
            assert GROUP_FOR[event] == group


def test_the_desktop_parity_events_are_all_present() -> None:
    """The set every desktop suite has had since the nineties, and QUILL did
    not: open, close, cut, copy, paste, delete, undo, redo, print, and the
    message tones. They were the events most in need of a sound, because they
    are the ones a screen reader says nothing about."""
    for event in (
        "document_opened",
        "document_closed",
        "text_cut",
        "text_copied",
        "text_pasted",
        "text_deleted",
        "undo_performed",
        "redo_performed",
        "nothing_to_undo",
        "print_started",
        "print_complete",
        "information",
        "question",
        "task_complete",
        "app_started",
        "app_exiting",
    ):
        assert hasattr(SoundEvent, event.upper()), event
        assert event in LABELS, event
