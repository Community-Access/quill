"""Paste File, saved replace jobs and snippet blanks, through QUILL Lite's window.

The handlers are QUILL's (``quill/ui/paste_file.py``, ``quill/ui/replace_jobs.py``,
``quill/ui/snippet_prompts.py``), reached here the way QUILL Lite's menu reaches
them. Every window is answered by the dialog recorder, which answers Cancel unless
a test says otherwise; the clipboard is replaced at the one function that reads it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.abbreviations import Abbreviation, AbbreviationLibrary
from quill.core.replace_jobs import ReplaceJob, ReplaceStep, load_replace_jobs
from quill.core.say_commands import ClipboardContents
from quill.ui import say_commands


@pytest.fixture
def copied(monkeypatch):
    """Put *paths* on a fake clipboard as copied files."""

    def put(*paths: Path) -> None:
        contents = ClipboardContents(files=tuple(str(p) for p in paths))
        monkeypatch.setattr(say_commands, "read_clipboard", lambda: contents)

    return put


# -- Paste File ------------------------------------------------------------ #


def test_paste_file_with_no_copied_files_says_how_to_get_some(lite_window, copied) -> None:
    win = lite_window("abc")
    copied()

    win.cmd_paste_file()

    assert win.control.GetValue() == "abc"
    assert win.announcements[-1].startswith("There are no copied files on the clipboard")


def test_paste_file_cancelled_pastes_nothing(lite_window, copied, lite_dialogs, tmp_path) -> None:
    note = tmp_path / "note.txt"
    note.write_text("hello", encoding="utf-8")
    win = lite_window("abc")
    copied(note)

    win.cmd_paste_file()

    assert lite_dialogs.names() == ["choose_paste_kind"]
    assert lite_dialogs.args_for("choose_paste_kind")[1] == ["note.txt"]
    assert win.control.GetValue() == "abc"
    assert win.announcements == []


def test_paste_file_puts_in_each_files_text(lite_window, copied, lite_dialogs, tmp_path) -> None:
    first = tmp_path / "one.txt"
    first.write_text("First", encoding="utf-8")
    second = tmp_path / "two.md"
    second.write_text("Second", encoding="utf-8")
    win = lite_window("[]", cursor=1)
    copied(first, second)
    lite_dialogs.answer("choose_paste_kind", "text")

    win.cmd_paste_file()

    assert win.control.GetValue() == "[First\n\nSecond]"
    assert win.modified
    assert win.announcements[-1] == "Pasted the text of 2 files"


def test_paste_file_can_put_in_the_paths(lite_window, copied, lite_dialogs, tmp_path) -> None:
    note = tmp_path / "note.txt"
    note.write_text("hello", encoding="utf-8")
    win = lite_window("")
    copied(note)
    lite_dialogs.answer("choose_paste_kind", "path")

    win.cmd_paste_file()

    assert win.control.GetValue() == str(note)
    assert win.announcements[-1] == "Pasted 1 path"


def test_paste_file_refuses_a_huge_file_and_says_why(
    lite_window, copied, lite_dialogs, tmp_path, monkeypatch
) -> None:
    from quill.core import paste_file

    monkeypatch.setattr(paste_file, "MAX_FILE_BYTES", 4)
    big = tmp_path / "big.log"
    big.write_text("far too long", encoding="utf-8")
    win = lite_window("abc")
    copied(big)
    lite_dialogs.answer("choose_paste_kind", "text")

    win.cmd_paste_file()

    assert win.control.GetValue() == "abc"
    assert "big.log is" in win.announcements[-1]
    assert "limit" in win.announcements[-1]


def test_paste_file_respects_the_read_only_guard(lite_window, copied, lite_dialogs) -> None:
    win = lite_window("abc")
    win._read_only = True

    win.cmd_paste_file()

    assert lite_dialogs.names() == []
    assert win.announcements[-1] == "Document is read-only"


# -- Replace jobs ---------------------------------------------------------- #


def _jobs(win) -> Path:
    return Path(win.app.data_dir) / "replace_jobs.json"


def test_run_replace_job_cancelled_changes_nothing(lite_window, lite_dialogs) -> None:
    win = lite_window("a  b")

    win.cmd_run_replace_job()

    assert lite_dialogs.names() == ["choose_replace_job"]
    assert lite_dialogs.kwargs_for("choose_replace_job") == {"in_selection": False}
    assert win.control.GetValue() == "a  b"
    assert win.control.focused


def test_run_replace_job_runs_a_sample_on_the_whole_document(lite_window, lite_dialogs) -> None:
    win = lite_window("a  b \nc")
    lite_dialogs.answer("choose_replace_job", 0)  # Tidy spaces, the first sample

    win.cmd_run_replace_job()

    assert win.control.GetValue() == "a b\nc"
    assert win.announcements[-1] == "Tidy spaces: 2 replacements. Step 1 found nothing"
    win.control.Undo()
    assert win.control.GetValue() == "a  b \nc"  # one step back undoes the whole job


def test_run_replace_job_on_the_selection_only(lite_window, lite_dialogs) -> None:
    win = lite_window("x  x  x")
    win.control.SetSelection(0, 4)
    lite_dialogs.answer("choose_replace_job", 0)

    win.cmd_run_replace_job()

    assert lite_dialogs.kwargs_for("choose_replace_job") == {"in_selection": True}
    assert win.control.GetValue() == "x x  x"
    assert win.announcements[-1].endswith("in the selection. Steps 1, 3 found nothing")


def test_run_replace_job_with_no_jobs_says_where_to_make_one(lite_window, lite_dialogs) -> None:
    from quill.core.replace_jobs import save_replace_jobs

    win = lite_window("abc")
    save_replace_jobs(_jobs(win), [])

    win.cmd_run_replace_job()

    assert lite_dialogs.names() == []
    assert "Manage Replace Jobs" in win.announcements[-1]


def test_a_broken_job_changes_nothing_and_says_which_step(lite_window, lite_dialogs) -> None:
    from quill.core.replace_jobs import save_replace_jobs

    win = lite_window("abc")
    save_replace_jobs(_jobs(win), [ReplaceJob("Bad", [ReplaceStep("(", "", regex=True)])])
    lite_dialogs.answer("choose_replace_job", 0)

    win.cmd_run_replace_job()

    assert win.control.GetValue() == "abc"
    assert win.announcements[-1].startswith("Step 1 of Bad:")
    assert win.announcements[-1].endswith("Nothing was changed")


def test_manage_replace_jobs_cancelled_saves_nothing(lite_window, lite_dialogs) -> None:
    win = lite_window("")

    win.cmd_manage_replace_jobs()

    assert lite_dialogs.names() == ["manage_replace_jobs"]
    assert not _jobs(win).exists()


def test_manage_replace_jobs_saves_what_was_changed(lite_window, lite_dialogs) -> None:
    win = lite_window("")
    mine = [ReplaceJob("Mine", [ReplaceStep("teh", "the")])]
    lite_dialogs.answer("manage_replace_jobs", mine)

    win.cmd_manage_replace_jobs()

    assert load_replace_jobs(_jobs(win)) == mine
    assert win.announcements[-1] == "Saved 1 replace job"


# -- Fields that ask you something ---------------------------------------- #


def _library(win, expansion: str) -> None:
    entry = Abbreviation(id="a1", abbreviation="mtg", expansion=expansion)
    win.app.abbreviations = AbbreviationLibrary(version=1, abbreviations=[entry])


def test_the_gallery_asks_the_fields_in_the_shared_form(lite_window, lite_dialogs) -> None:
    win = lite_window("")
    template = "Meeting: ${input:Topic}\nReader: ${choice:Reader|NVDA|JAWS}\n${cursor}Done"
    _library(win, template)
    lite_dialogs.answer("choose_from_rows", "a1")
    lite_dialogs.answer("prompt_for_fields", "Meeting: Budget\nReader: JAWS\n${cursor}Done")

    win.cmd_snippet_gallery()

    assert lite_dialogs.args_for("prompt_for_fields")[1] == template
    assert lite_dialogs.kwargs_for("prompt_for_fields")["title"] == "mtg"
    assert win.control.GetValue() == "Meeting: Budget\nReader: JAWS\nDone"
    assert win.control.GetInsertionPoint() == len("Meeting: Budget\nReader: JAWS\n")
    assert win.announcements[-1] == "Inserted mtg"


def test_cancelling_the_fields_inserts_nothing(lite_window, lite_dialogs) -> None:
    win = lite_window("keep")
    _library(win, "Dear ${field:Name},")
    lite_dialogs.answer("choose_from_rows", "a1")

    win.cmd_snippet_gallery()

    assert lite_dialogs.names()[-1] == "prompt_for_fields"
    assert win.control.GetValue() == "keep"


def test_an_expansion_without_fields_asks_nothing(lite_window, lite_dialogs) -> None:
    win = lite_window("")
    _library(win, "Yours sincerely")
    lite_dialogs.answer("choose_from_rows", "a1")

    win.cmd_snippet_gallery()

    assert "prompt_for_fields" not in lite_dialogs.names()
    assert win.control.GetValue() == "Yours sincerely"


def test_a_typed_abbreviation_asks_its_fields_too(lite_window, lite_dialogs) -> None:
    win = lite_window("")
    _library(win, "Dear ${input:Name}")
    lite_dialogs.answer("prompt_for_fields", "Dear Ann")
    win.control.WriteText("mtg ")

    win._maybe_expand()

    assert win.control.GetValue() == "Dear Ann "


def test_a_cancelled_typed_abbreviation_leaves_the_trigger(lite_window, lite_dialogs) -> None:
    win = lite_window("")
    _library(win, "Dear ${input:Name}")
    win.control.WriteText("mtg ")

    win._maybe_expand()

    assert win.control.GetValue() == "mtg "


def test_input_is_the_same_field_as_field() -> None:
    """A blank written the snippet way asks in an abbreviation too, in both editors."""
    from quill.core.expansion.fields import fill_fields, has_fields, parse_fields

    assert has_fields("Hi ${input:Name}")
    assert [spec.label for spec in parse_fields("${input:Name} ${field:name}")] == ["Name"]
    assert fill_fields("Hi ${input:Name}", {"name": "Sam"}) == "Hi Sam"
