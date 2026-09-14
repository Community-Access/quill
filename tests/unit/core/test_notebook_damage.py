"""A damaged notebook costs you the notebook, never the app (#1499).

The reported failure was not "a notebook looked wrong". It was that
``NotebookEntry.from_dict`` read ``data["path"]`` directly, so an entry without
one raised a bare ``KeyError`` -- straight past the caller's
``except NotebookFormatError``, into the crash handler, and out. The reporter's
words: "I expected the application to open."

Two rules are tested here, and they pull in opposite directions on purpose.
**Nothing escapes as a raw exception**, so the caller's one ``except`` clause is
enough to keep the app alive. And **damage is local**: one unreadable row loses
that row, not the other thirty-nine, because a writer with forty chapters and
one bad record wants the thirty-nine.
"""

from __future__ import annotations

import json

import pytest

from quill.core.notebook_store import (
    Notebook,
    NotebookEntry,
    NotebookFormatError,
    load_notebook,
    save_notebook,
)

SCHEMA = "quill.notebook/1"


def _file(tmp_path, data):
    path = tmp_path / "book.quillnotebook"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _notebook(entries):
    return {"schema": SCHEMA, "name": "Novel", "entries": entries}


# --------------------------------------------------------------------- #
# Nothing escapes as a raw exception


def test_an_entry_with_no_path_does_not_raise_a_keyerror(tmp_path) -> None:
    """The exact shape of #1499. A KeyError here ended the process."""
    path = _file(tmp_path, _notebook([{"id": "a"}]))
    notebook = load_notebook(path)  # must not raise at all
    assert notebook.entries == []


def test_a_file_damaged_any_other_way_is_still_a_notebook_format_error(tmp_path) -> None:
    """The caller has one except clause. Every kind of damage has to land in it,
    or the next unhandled shape is the next crash report."""
    # A goal with an unrecognised field is NOT in this list, deliberately: an
    # unknown key there falls back to the default target, which is tolerance
    # working rather than damage. These four are files that cannot be read.
    for broken in (
        {"schema": SCHEMA},  # no name at all
        {"schema": SCHEMA, "name": "n", "snapshots": [{"id": "s"}]},
        {"schema": SCHEMA, "name": "n", "saved_searches": [{}]},
        {"schema": SCHEMA, "name": "n", "goal": "a daily word target"},
    ):
        with pytest.raises(NotebookFormatError):
            load_notebook(_file(tmp_path, broken))


def test_the_error_names_the_file_so_the_message_is_actionable(tmp_path) -> None:
    path = _file(tmp_path, {"schema": SCHEMA})
    with pytest.raises(NotebookFormatError) as caught:
        load_notebook(path)
    assert path.name in str(caught.value)


def test_a_wrong_schema_is_still_refused(tmp_path) -> None:
    """Tolerance is for damage, not for a file that is something else."""
    with pytest.raises(NotebookFormatError):
        load_notebook(_file(tmp_path, {"schema": "something.else/9", "name": "n"}))


def test_entries_that_are_not_objects_at_all_are_dropped(tmp_path) -> None:
    path = _file(tmp_path, _notebook(["just a string", 7, None, {"id": "a", "path": "a.md"}]))
    notebook = load_notebook(path)
    assert [e.path for e in notebook.entries] == ["a.md"]
    assert notebook.unreadable_entries == 3


# --------------------------------------------------------------------- #
# Damage is local


def test_one_bad_entry_does_not_cost_the_good_ones(tmp_path) -> None:
    path = _file(
        tmp_path,
        _notebook([
            {"id": "1", "path": "one.md"},
            {"id": "2"},  # no path: unusable
            {"id": "3", "path": "three.md"},
        ]),
    )
    notebook = load_notebook(path)
    assert [e.path for e in notebook.entries] == ["one.md", "three.md"]


def test_the_number_dropped_is_recorded_so_the_window_can_say_it(tmp_path) -> None:
    """A silently shorter list is indistinguishable from a notebook that always
    had that many entries."""
    path = _file(tmp_path, _notebook([{"id": "1", "path": "a.md"}, {"id": "2"}, {"id": "3"}]))
    assert load_notebook(path).unreadable_entries == 2


def test_a_healthy_notebook_reports_nothing_dropped(tmp_path) -> None:
    path = _file(tmp_path, _notebook([{"id": "1", "path": "a.md"}]))
    assert load_notebook(path).unreadable_entries == 0


def test_an_entry_with_no_id_is_repaired_rather_than_dropped(tmp_path) -> None:
    """An id is only ever compared with other ids in the same file, so one can
    be minted. A path names a document on disk and cannot be."""
    path = _file(tmp_path, _notebook([{"path": "kept.md"}]))
    notebook = load_notebook(path)
    assert [e.path for e in notebook.entries] == ["kept.md"]
    assert notebook.entries[0].id
    assert notebook.unreadable_entries == 0


def test_a_nonsense_caret_position_does_not_lose_the_entry(tmp_path) -> None:
    """It is a scroll position. Nothing about it is worth an exception."""
    path = _file(tmp_path, _notebook([{"id": "1", "path": "a.md", "last_caret_pos": "middle"}]))
    notebook = load_notebook(path)
    assert notebook.entries[0].last_caret_pos == 0


# --------------------------------------------------------------------- #
# What the tolerance must not break


def test_a_notebook_that_round_trips_is_unchanged(tmp_path) -> None:
    """Every repair above has to be invisible to a healthy file."""
    original = Notebook(name="Novel")
    original.entries = [NotebookEntry.create("one.md", title="One")]
    path = tmp_path / "round.quillnotebook"
    save_notebook(original, path)
    loaded = load_notebook(path)
    assert loaded.name == "Novel"
    assert [(e.id, e.path, e.title) for e in loaded.entries] == [
        (original.entries[0].id, "one.md", "One")
    ]
    assert loaded.unreadable_entries == 0


def test_the_dropped_count_is_not_written_back_out(tmp_path) -> None:
    """It describes the file that was read, not the notebook to be written; a
    saved copy of a repaired notebook is simply a healthy notebook."""
    path = _file(tmp_path, _notebook([{"id": "1", "path": "a.md"}, {"id": "2"}]))
    notebook = load_notebook(path)
    assert notebook.unreadable_entries == 1
    save_notebook(notebook, path)
    assert "unreadable_entries" not in path.read_text(encoding="utf-8")
    assert load_notebook(path).unreadable_entries == 0
