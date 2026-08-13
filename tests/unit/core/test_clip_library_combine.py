"""Unit tests for naming, editing, and combining kept clips.

Scope note: these are conveniences for assembling text already kept in QUILL,
not a clipboard manager. Nothing here watches the system clipboard.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.clip_library import (
    COMBINE_SEPARATORS,
    ClipLibrary,
    combine_texts,
)
from quill.core.fragment import Fragment


def _library(tmp_path: Path, *texts: str) -> ClipLibrary:
    library = ClipLibrary(tmp_path)
    for text in texts:
        library.remember(Fragment(markup=text, source="Document"))
    return library


def test_combine_texts_joins_in_the_order_given() -> None:
    assert combine_texts(["one", "two", "three"], ", ") == "one, two, three"


def test_combine_texts_drops_empty_entries_so_no_separator_dangles() -> None:
    assert combine_texts(["one", "   ", "", "two"], " | ") == "one | two"


def test_combine_texts_trims_each_entry() -> None:
    assert combine_texts(["  one  ", "two  "], " ") == "one two"


def test_combine_texts_of_nothing() -> None:
    assert combine_texts([], ", ") == ""


def test_every_offered_separator_is_usable() -> None:
    for separator in COMBINE_SEPARATORS.values():
        assert combine_texts(["a", "b"], separator) == f"a{separator}b"


def test_combine_uses_the_marked_order_not_the_list_order(tmp_path: Path) -> None:
    # remember() inserts at the front, so the newest clip is index 0.
    library = _library(tmp_path, "third", "second", "first")
    assert library.combine([0, 1, 2], " ") == "first second third"
    assert library.combine([2, 1, 0], " ") == "third second first"


def test_combine_with_a_line_break(tmp_path: Path) -> None:
    library = _library(tmp_path, "b", "a")
    assert library.combine([0, 1], "\n") == "a\nb"


def test_combine_rejects_an_index_that_is_not_there(tmp_path: Path) -> None:
    library = _library(tmp_path, "only")
    with pytest.raises(ValueError):
        library.combine([0, 5], " ")


def test_rename_gives_an_entry_a_findable_name(tmp_path: Path) -> None:
    library = _library(tmp_path, "12 High Street, Anytown")
    library.rename(0, "Home address")
    assert library.entry(0).display_label() == "Home address"


def test_rename_to_empty_falls_back_to_the_preview(tmp_path: Path) -> None:
    library = _library(tmp_path, "12 High Street")
    library.rename(0, "Home")
    library.rename(0, "   ")
    assert library.entry(0).display_label() == "12 High Street"


def test_rename_survives_a_reload(tmp_path: Path) -> None:
    library = _library(tmp_path, "some text")
    library.rename(0, "Named")
    assert ClipLibrary(tmp_path).entry(0).display_label() == "Named"


def test_set_text_fixes_a_clip_in_place(tmp_path: Path) -> None:
    library = _library(tmp_path, "teh wrong text")
    library.set_text(0, "the right text")
    assert library.entry(0).fragment.markup == "the right text"
    assert ClipLibrary(tmp_path).entry(0).fragment.markup == "the right text"
