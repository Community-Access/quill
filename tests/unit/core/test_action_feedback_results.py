"""The actual result, once (FUX-04): the words a save, change or recovery ends with.

``quill.core.action_feedback`` builds every one of these sentences for Quill
Cast, QUILL Lite and QUILL, so the two pilots and the editor QUILL Lite may
never be ahead of say the same thing about the same result. Each test names a
state and checks the sentence says that state -- and nothing that is not true.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import PureWindowsPath

from quill.core.action_feedback import (
    changes_result,
    place_of,
    recovered_result,
    saved_result,
    speed_result,
    when_said,
    written_result,
)

NOW = datetime(2026, 11, 19, 15, 0)


def test_a_saved_file_is_named_with_its_folder() -> None:
    path = PureWindowsPath(r"C:\Users\pat\Documents\notes.txt")
    assert saved_result(path) == "Saved notes.txt in Documents."


def test_a_file_at_the_root_of_a_drive_names_the_drive() -> None:
    assert place_of(PureWindowsPath("D:/notes.txt")) == "notes.txt in D:\\"


def test_a_bare_name_is_said_as_it_is() -> None:
    assert place_of("notes.txt") == "notes.txt"


def test_a_backup_that_failed_is_said_in_the_same_sentence() -> None:
    said = saved_result(PureWindowsPath(r"C:\work\note.txt"), backup_failed=True)
    assert said == "Saved note.txt in work, but could not write a backup."


def test_typing_during_a_background_save_is_never_called_saved_alone() -> None:
    said = saved_result(PureWindowsPath(r"C:\work\report.docx"), changed_since=True)
    assert said.startswith("Saved report.docx in work.")
    assert "not in it yet" in said


def test_a_written_file_says_where_it_went() -> None:
    said = written_result("Exported 3 podcasts", PureWindowsPath(r"C:\Users\pat\Downloads\a.opml"))
    assert said == "Exported 3 podcasts to a.opml in Downloads."


def test_when_is_the_shortest_unambiguous_thing() -> None:
    assert when_said(datetime(2026, 11, 19, 9, 5), NOW) == "today at 9:05 AM"
    assert when_said(datetime(2026, 11, 18, 0, 30), NOW) == "yesterday at 12:30 AM"
    assert when_said(datetime(2026, 11, 14, 18, 0), NOW) == "on 14 November at 6:00 PM"
    assert when_said(datetime(2025, 11, 14, 12, 0), NOW) == "on 14 November 2025 at 12:00 PM"


def test_one_recovered_draft_says_which_and_from_when_and_that_it_is_unsaved() -> None:
    said = recovered_result(["notes.txt"], asked=1, when=datetime(2026, 11, 19, 14, 2), now=NOW)
    assert said == "Recovered notes.txt, as it was today at 2:02 PM. It is not saved yet."


def test_recovery_counts_what_came_back_not_what_was_asked_for() -> None:
    said = recovered_result(["a.txt"], asked=2)
    assert said == "Recovered 1 of 2: a.txt. It is not saved yet."
    assert "2 unsaved" not in said


def test_every_draft_back_is_named() -> None:
    said = recovered_result(["a.txt", "Untitled", "b.md"], asked=3)
    assert (
        said
        == "Recovered 3 unsaved documents: a.txt, Untitled and b.md. None of them is saved yet."
    )


def test_a_recovery_that_brought_nothing_back_says_so() -> None:
    assert recovered_result([], asked=0) == "Nothing was restored."
    assert recovered_result([], asked=2) == "Restored none of the 2. The work is still saved aside."


def test_a_speed_that_reached_the_player_is_said_once() -> None:
    assert speed_result(1.5, "The Daily", playing_rate=1.5) == "Speed 1.5x for The Daily."
    assert speed_result(1.5, "The Daily") == "Speed 1.5x for The Daily."


def test_a_speed_the_player_did_not_take_says_what_is_heard() -> None:
    said = speed_result(1.5, "The Daily", playing_rate=1.2)
    assert said == "Speed 1.5x for The Daily. The episode playing stays at 1.2x."


def test_changes_in_use_are_not_called_saved_before_the_write_lands() -> None:
    said = changes_result(2, pending=True)
    assert said == "Preferences changed: 2 changes, in use now."
    assert "saved" not in said.lower()


def test_changes_already_written_are_called_saved() -> None:
    said = changes_result(1, pending=False, extra=("QUILL Cast will start with Windows.", ""))
    assert said == "Preferences saved: 1 change. QUILL Cast will start with Windows."
