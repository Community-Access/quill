"""The Read-Only Guard's shared memory (quill/core/read_only_guards.py, 2026-10-16).

Three things are checked here because each was wrong before:

* a guard set on a file must be found again however the next open spells the
  path -- File Explorer, Open Recent and the Open window do not agree on case;
* a guard that could not be written must say so instead of promising it will
  be remembered;
* lists written by older builds (a bare list, raw spellings) still load.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from quill.core import read_only_guards as guards_mod
from quill.core.read_only_guards import (
    GUARD_FILENAME,
    READ_ONLY_REFUSAL,
    DocumentReadOnlyError,
    ReadOnlyGuards,
    guard_key,
    refuse_if_guarded,
    toggle_sentence,
)


def _book(tmp_path: Path) -> Path:
    path = tmp_path / "Library" / "Long Book.md"
    path.parent.mkdir()
    path.write_text("# Chapter 1\n\nText.\n", encoding="utf-8")
    return path


def test_a_guard_survives_a_restart(tmp_path: Path) -> None:
    store = tmp_path / GUARD_FILENAME
    book = _book(tmp_path)
    assert ReadOnlyGuards(store).set(book, True) == ""
    # A fresh object is a fresh session: it reads the file, not a cache.
    assert ReadOnlyGuards(store).is_guarded(book)
    stored = json.loads(store.read_text(encoding="utf-8"))
    assert stored["schema_version"] == 1
    assert stored["paths"] == [guard_key(book)]


def test_the_explorer_spelling_finds_the_guard_set_from_open_recent(tmp_path: Path) -> None:
    store = tmp_path / GUARD_FILENAME
    book = _book(tmp_path)
    ReadOnlyGuards(store).set(book, True)
    reopened = ReadOnlyGuards(store)
    # The shell hands over its own spelling: other case, a dot segment, the
    # other slash. All of them are the same file.
    as_explorer_spells_it = str(book).upper() if os.name == "nt" else str(book)
    dotted = book.parent / "." / book.name
    assert reopened.is_guarded(as_explorer_spells_it)
    assert reopened.is_guarded(dotted)
    assert reopened.is_guarded(str(book).replace("\\", "/"))


def test_turning_it_off_forgets_it(tmp_path: Path) -> None:
    store = tmp_path / GUARD_FILENAME
    book = _book(tmp_path)
    ReadOnlyGuards(store).set(book, True)
    ReadOnlyGuards(store).set(book, False)
    assert not ReadOnlyGuards(store).is_guarded(book)


def test_lists_from_older_builds_still_load(tmp_path: Path) -> None:
    book = _book(tmp_path)
    bare = tmp_path / "bare.json"
    bare.write_text(json.dumps([str(book)]), encoding="utf-8")
    assert ReadOnlyGuards(bare).is_guarded(book)
    raw_spelling = tmp_path / "raw.json"
    raw_spelling.write_text(
        json.dumps({"schema_version": 1, "paths": [str(book).lower()]}), encoding="utf-8"
    )
    if os.name == "nt":
        assert ReadOnlyGuards(raw_spelling).is_guarded(book)


def test_a_damaged_list_is_an_empty_one(tmp_path: Path) -> None:
    store = tmp_path / GUARD_FILENAME
    store.write_text("{not json", encoding="utf-8")
    assert not ReadOnlyGuards(store).is_guarded(_book(tmp_path))


def test_a_failed_save_is_reported_not_swallowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _full_disk(*_args: object, **_kwargs: object) -> None:
        raise OSError(28, "There is not enough space on the disk")

    monkeypatch.setattr("quill.core.storage.write_json_atomic", _full_disk)
    store = tmp_path / GUARD_FILENAME
    guards = ReadOnlyGuards(store)
    book = _book(tmp_path)
    reason = guards.set(book, True)
    assert reason == "There is not enough space on the disk"
    # Still on for this session, as the person asked.
    assert guards.is_guarded(book)
    assert not store.exists()


def test_an_untitled_document_cannot_be_remembered(tmp_path: Path) -> None:
    assert ReadOnlyGuards(tmp_path / GUARD_FILENAME).set(None, True) == "it has no file name yet"


def test_the_sentences() -> None:
    assert toggle_sentence(True, saved=True) == "Document is read-only"
    assert toggle_sentence(False, saved=True) == "Document is editable"
    said = toggle_sentence(True, saved=False, reason="Access is denied")
    assert said == (
        "Document is read-only for now, but it could not be remembered for next "
        "time (Access is denied)."
    )


def test_the_refusal_is_a_coded_error_with_the_shared_sentence() -> None:
    error = DocumentReadOnlyError()
    assert error.code == "QUILL-CORE-READONLY-REFUSED"
    assert READ_ONLY_REFUSAL in str(error)


class _Host:
    def __init__(self, guarded: bool) -> None:
        self.guarded = guarded
        self.said: list[str] = []

    def _host_read_only(self) -> bool:
        return self.guarded

    def _announce(self, text: str) -> None:
        self.said.append(text)


def test_refuse_if_guarded_speaks_only_when_it_refuses() -> None:
    open_host, guarded_host = _Host(False), _Host(True)
    assert refuse_if_guarded(open_host) is False
    assert open_host.said == []
    assert refuse_if_guarded(guarded_host) is True
    assert guarded_host.said == [READ_ONLY_REFUSAL]
    assert refuse_if_guarded(object()) is False


def test_the_module_keeps_wx_out() -> None:
    source = Path(guards_mod.__file__).read_text(encoding="utf-8")
    assert "import wx" not in source
