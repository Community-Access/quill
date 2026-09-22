"""The read-only field that says what the buttons would do.

Asked for by name on 2026-09-21: *"a read-only edit field ... that describes the
state of restorable items in significant detail ... maintained to show what
actions would or would not be performed after making selections so that the user
can see this."*

Both startup choosers grew one. A list of checkboxes answers "what is here" one
row at a time and never answers "what happens when I press the button" -- and
that second question is the one somebody is actually asking, because the buttons
are the irreversible part. Sighted users assemble the answer by glancing down
the list; assembling it by ear costs a pass through every row, and the pass has
to be repeated after every tick.

The text is built wx-free in ``quill/core/recovery_triage.py`` and
``quill/core/session_restore.py``, so what it says is testable without a
display. That the windows keep it in step is
``tests/unit/ui/test_restore_dialog_summaries.py``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from quill.core.recovery_triage import describe_plan, triage
from quill.core.session_restore import describe_session_plan, read_entries

_NOW = 1_700_000_000.0
_DAY = 86400.0


@dataclass
class FakeSlot:
    mode: str
    original_path: str
    content_path: Path

    @property
    def title(self) -> str:
        return Path(self.original_path).name if self.original_path else "Untitled"


def _slot(tmp_path: Path, name: str, text: str, *, path: str = "", age_days: float = 0.0):
    content = tmp_path / name
    content.write_text(text, encoding="utf-8")
    written = _NOW - age_days * _DAY
    os.utime(content, (written, written))
    return FakeSlot(mode="plain", original_path=path, content_path=content)


# --------------------------------------------------------------------------- #
# Unsaved work
# --------------------------------------------------------------------------- #


def test_it_numbers_every_row_and_says_which_are_ticked(tmp_path: Path) -> None:
    """The row number is the handle somebody uses to come back to a row."""
    slots = [_slot(tmp_path, "a.txt", "one"), _slot(tmp_path, "b.txt", "two")]
    result = triage(slots, now=_NOW)

    text = describe_plan(result, (True, False), now=_NOW)

    assert "1. Ticked." in text
    assert "2. Not ticked." in text


def test_it_says_what_each_button_would_do_right_now(tmp_path: Path) -> None:
    slots = [_slot(tmp_path, "a.txt", "one"), _slot(tmp_path, "b.txt", "two")]
    result = triage(slots, now=_NOW)

    text = describe_plan(result, (True, False), now=_NOW)

    assert "Restore Checked opens 1 document" in text
    assert "Discard Checked permanently deletes 1 ticked document" in text
    assert "Restore All opens all 2" in text
    assert "Discard Everything permanently deletes all 2" in text
    assert "Not Now changes nothing" in text


def test_nothing_ticked_says_the_buttons_would_do_nothing(tmp_path: Path) -> None:
    """The case somebody is most likely to be wrong about, said outright."""
    result = triage([_slot(tmp_path, "a.txt", "one")], now=_NOW)

    text = describe_plan(result, (False,), now=_NOW)

    assert "Restore Checked does nothing: no rows are ticked." in text
    assert "Discard Checked does nothing: no rows are ticked." in text


def test_it_says_what_survives_a_discard(tmp_path: Path) -> None:
    """ "What would *not* be performed" is half of what was asked for."""
    slots = [_slot(tmp_path, "a.txt", "one"), _slot(tmp_path, "b.txt", "two")]
    result = triage(slots, now=_NOW)

    text = describe_plan(result, (True, False), now=_NOW)

    assert "1 unticked document stays saved aside" in text


def test_it_leads_with_what_was_tidied_before_the_list_existed(tmp_path: Path) -> None:
    """Tidying nobody is told about is indistinguishable from work going missing."""
    slots = [_slot(tmp_path, f"{index}.txt", "body") for index in range(4)]
    slots.append(_slot(tmp_path, "old.txt", "gone", age_days=99))
    result = triage(slots, now=_NOW)

    text = describe_plan(result, (True,), now=_NOW)

    assert text.startswith("Before this list was built:")
    assert "identical copies" in text
    assert "older than a month" in text


def test_a_clean_list_does_not_invent_a_tidying_line(tmp_path: Path) -> None:
    result = triage([_slot(tmp_path, "a.txt", "one")], now=_NOW)

    text = describe_plan(result, (True,), now=_NOW)

    assert "Before this list was built" not in text
    assert text.startswith("1 document of unsaved work, 1 ticked.")


def test_every_row_carries_its_size_and_age(tmp_path: Path) -> None:
    """How somebody tells a note they were writing from an abandoned paste."""
    result = triage([_slot(tmp_path, "a.txt", "x" * 40, age_days=3)], now=_NOW)

    text = describe_plan(result, (True,), now=_NOW)

    assert "40 characters" in text
    assert "3 days ago" in text


def test_a_short_checked_tuple_reads_the_rest_as_unticked(tmp_path: Path) -> None:
    """Defensive: a caller mid-rebuild must not make this raise."""
    slots = [_slot(tmp_path, "a.txt", "one"), _slot(tmp_path, "b.txt", "two")]
    result = triage(slots, now=_NOW)

    text = describe_plan(result, (True,), now=_NOW)

    assert "2. Not ticked." in text


# --------------------------------------------------------------------------- #
# Last session's documents
# --------------------------------------------------------------------------- #


def test_the_session_plan_numbers_rows_and_marks_them(tmp_path: Path) -> None:
    here = tmp_path / "here.md"
    here.write_text("x", encoding="utf-8")
    entries = read_entries([str(here), str(tmp_path / "gone.md")])

    text = describe_session_plan(entries, (True, True))

    assert "1. Ticked." in text
    assert "2. Ticked." in text


def test_the_session_plan_says_what_cannot_be_opened(tmp_path: Path) -> None:
    """A ticked row whose file has gone is the one case silence misleads about."""
    here = tmp_path / "here.md"
    here.write_text("x", encoding="utf-8")
    entries = read_entries([str(here), str(tmp_path / "gone.md")])

    text = describe_session_plan(entries, (True, True))

    assert "Open Checked reopens 1: here.md." in text
    assert "1 ticked cannot be opened, because the files have gone: gone.md." in text


def test_the_session_plan_says_forgetting_touches_no_file(tmp_path: Path) -> None:
    """The reassurance belongs in the sentence, not in a warning box."""
    here = tmp_path / "here.md"
    here.write_text("x", encoding="utf-8")
    entries = read_entries([str(here)])

    text = describe_session_plan(entries, (True,))

    assert "No file is touched" in text
    assert "Clear the List forgets all 1. Again, no file is touched." in text


def test_the_session_plan_says_when_nothing_would_open(tmp_path: Path) -> None:
    entries = read_entries([str(tmp_path / "gone.md")])

    text = describe_session_plan(entries, (False,))

    assert "Open Checked opens nothing" in text
    assert "Forget Checked does nothing: no rows are ticked." in text


def test_the_session_plan_agrees_with_itself_about_one_missing_file(
    tmp_path: Path,
) -> None:
    entries = read_entries([str(tmp_path / "gone.md")])

    text = describe_session_plan(entries, (True,))

    assert "1 of these files is no longer where they were" in text
