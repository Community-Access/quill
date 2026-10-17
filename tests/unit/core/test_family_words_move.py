"""The family's word list moves to %LOCALAPPDATA%\\QuillVille\\Dictation (D-12, D-13).

``quill/core/windows_dictation/family_words.py``: copied, never moved; the old
file is left as the backup; read through the old place until the copy exists;
words added later in the old place are merged, never lost.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.windows_dictation import family_words
from quill.core.windows_dictation.family_store import family_dictation_dir
from quill.core.windows_dictation.family_words import (
    MERGE_BACKUP_NAME,
    RECORD_NAME,
    WORDS_NAME,
    bring_over,
    family_profile_path,
)
from quill.core.windows_dictation.words_file import WordsFile, load_words, save_words


def _old_folder(tmp_path: Path, words: list[str]) -> Path:
    old = tmp_path / "Quill"
    save_words(old / WORDS_NAME, WordsFile(words=words, phrases=[("my sig", "Jeff")]))
    (old / "dictation-instructions.md").write_text("Write British spelling.\n", encoding="utf-8")
    (old / "dictation-contexts.json").write_text('{"contexts": []}', encoding="utf-8")
    return old


def test_the_first_ask_copies_all_three_files_and_leaves_the_old_ones(tmp_path: Path) -> None:
    old = _old_folder(tmp_path, ["NVDA", "Okonkwo"])
    before = {p.name: p.read_bytes() for p in old.iterdir()}

    path = family_profile_path(old)

    folder = family_dictation_dir()
    assert path == folder / WORDS_NAME
    assert load_words(path).words == ["NVDA", "Okonkwo"]
    for name, data in before.items():
        assert (folder / name).read_bytes() == data  # a byte-for-byte copy
        assert (old / name).read_bytes() == data  # the old one, untouched: the backup


def test_a_second_ask_writes_nothing(tmp_path: Path) -> None:
    """Asked for on every phrase: no copy, no record write, when nothing changed."""
    old = _old_folder(tmp_path, ["NVDA"])
    family_profile_path(old)
    record = family_dictation_dir() / RECORD_NAME
    first = record.stat().st_mtime_ns
    assert bring_over(old, family_dictation_dir()) == []
    assert record.stat().st_mtime_ns == first


def test_the_family_list_is_never_overwritten_by_the_old_one(tmp_path: Path) -> None:
    old = _old_folder(tmp_path, ["NVDA"])
    path = family_profile_path(old)
    family = load_words(path)
    family.words.append("Zoë")
    save_words(path, family)

    family_profile_path(old)  # the old file has not changed: nothing happens
    assert load_words(path).words == ["NVDA", "Zoë"]


def test_words_added_later_in_the_old_place_are_merged_not_lost(tmp_path: Path) -> None:
    """An older build still running writes to the old file after the move."""
    old = _old_folder(tmp_path, ["NVDA"])
    path = family_profile_path(old)
    mine = load_words(path)
    mine.words.append("Zoë")
    save_words(path, mine)
    before_merge = path.read_bytes()

    older = load_words(old / WORDS_NAME)
    older.words.append("Tucson")
    save_words(old / WORDS_NAME, older)

    assert bring_over(old, family_dictation_dir()) == [WORDS_NAME]
    assert load_words(path).words == ["NVDA", "Zoë", "Tucson"]
    assert (family_dictation_dir() / MERGE_BACKUP_NAME).read_bytes() == before_merge


def test_a_copy_that_fails_reads_through_the_old_place(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The list never looks empty: the old file is read until the copy exists."""
    old = _old_folder(tmp_path, ["NVDA"])
    from quill.core import storage

    def refuse(*_args: Any, **_kwargs: Any) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(storage, "write_bytes_atomic", refuse)
    assert family_profile_path(old) == old / WORDS_NAME
    assert not (family_dictation_dir() / WORDS_NAME).exists()

    monkeypatch.undo()
    assert family_profile_path(old) == family_dictation_dir() / WORDS_NAME  # tried again


def test_nothing_to_bring_is_a_new_empty_list_in_the_family_folder(tmp_path: Path) -> None:
    assert family_profile_path(tmp_path / "empty") == family_dictation_dir() / WORDS_NAME


def test_the_same_folder_is_left_alone(tmp_path: Path) -> None:
    old = _old_folder(tmp_path, ["NVDA"])
    assert bring_over(old, old) == []
    assert not (old / RECORD_NAME).exists()


def test_default_profile_path_is_the_family_list() -> None:
    from quill.core.speech.dictation_profile import default_profile_path

    assert default_profile_path() == family_dictation_dir() / family_words.WORDS_NAME
