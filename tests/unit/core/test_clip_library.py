"""Tests for the Clip Library (#895): a rolling history of Fragments beneath
Copy Tray's curated 12 slots."""

from __future__ import annotations

from pathlib import Path

from quill.core.clip_library import ClipLibrary
from quill.core.fragment import Fragment


def _lib(tmp_path: Path) -> ClipLibrary:
    return ClipLibrary(tmp_path)


def test_remember_adds_and_persists(tmp_path: Path) -> None:
    lib = _lib(tmp_path)
    assert lib.remember(Fragment(markup="hello world")) is True
    assert len(lib) == 1

    reloaded = ClipLibrary(tmp_path)
    assert len(reloaded) == 1
    assert reloaded.entry(0).fragment.markup == "hello world"


def test_remember_newest_first() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        lib = ClipLibrary(Path(tmp))
        lib.remember(Fragment(markup="first"))
        lib.remember(Fragment(markup="second"))
        assert lib.entry(0).fragment.markup == "second"
        assert lib.entry(1).fragment.markup == "first"


def test_remember_deduplicates_same_markup_and_source(tmp_path: Path) -> None:
    lib = _lib(tmp_path)
    lib.remember(Fragment(markup="x", source="Clipboard"))
    assert lib.remember(Fragment(markup="x", source="Clipboard")) is False
    assert len(lib) == 1
    # Same markup, different source is not a duplicate.
    assert lib.remember(Fragment(markup="x", source="Look Up")) is True
    assert len(lib) == 2


def test_remember_rejects_blank_markup(tmp_path: Path) -> None:
    lib = _lib(tmp_path)
    assert lib.remember(Fragment(markup="   ")) is False
    assert len(lib) == 0


def test_eviction_at_capacity_drops_oldest_non_favorite(tmp_path: Path) -> None:
    lib = _lib(tmp_path)
    lib.CAPACITY = 3  # shrink for a fast test
    lib.remember(Fragment(markup="a"))
    lib.remember(Fragment(markup="b"))
    lib.remember(Fragment(markup="c"))
    assert len(lib) == 3
    lib.remember(Fragment(markup="d"))
    assert len(lib) == 3
    markups = [lib.entry(i).fragment.markup for i in range(len(lib))]
    assert "a" not in markups  # oldest evicted
    assert "d" in markups


def test_favorite_protects_from_eviction(tmp_path: Path) -> None:
    lib = _lib(tmp_path)
    lib.CAPACITY = 2
    lib.remember(Fragment(markup="keep-me"))
    lib.set_favorite(0, True)
    lib.remember(Fragment(markup="b"))
    assert len(lib) == 2
    lib.remember(Fragment(markup="c"))
    markups = [lib.entry(i).fragment.markup for i in range(len(lib))]
    assert "keep-me" in markups
    assert "b" not in markups  # non-favorite evicted instead


def test_remove_and_clear(tmp_path: Path) -> None:
    lib = _lib(tmp_path)
    lib.remember(Fragment(markup="a"))
    lib.remember(Fragment(markup="b"))
    lib.remove(0)
    assert len(lib) == 1
    lib.clear()
    assert len(lib) == 0


def test_search_matches_title_source_and_markup(tmp_path: Path) -> None:
    lib = _lib(tmp_path)
    lib.remember(
        Fragment(markup="Ada Lovelace was a mathematician.", title="Ada", source="Wikipedia")
    )
    lib.remember(Fragment(markup="unrelated text"))
    results = lib.search("wikipedia")
    assert len(results) == 1
    assert results[0][1].fragment.title == "Ada"


def test_search_blank_query_returns_all_entries(tmp_path: Path) -> None:
    lib = _lib(tmp_path)
    lib.remember(Fragment(markup="a"))
    lib.remember(Fragment(markup="b"))
    assert len(lib.search("")) == 2


def test_promote_to_tray_renders_plain_text_and_copies(tmp_path: Path) -> None:
    lib = _lib(tmp_path)
    lib.remember(Fragment(markup="**bold** text"))

    class FakeTray:
        def __init__(self) -> None:
            self.copied: dict[int, str] = {}

        def copy_to(self, slot: int, text: str) -> None:
            self.copied[slot] = text

    tray = FakeTray()
    result = lib.promote_to_tray(0, tray, 3)
    assert result == "bold text"
    assert tray.copied[3] == "bold text"


def test_corrupt_file_starts_fresh(tmp_path: Path) -> None:
    (tmp_path / "clip_library.json").write_text("not json", encoding="utf-8")
    lib = ClipLibrary(tmp_path)
    assert len(lib) == 0


def test_display_label_prefers_title_then_preview() -> None:
    from quill.core.clip_library import ClipEntry

    titled = ClipEntry(fragment=Fragment(markup="x", title="My Title"))
    assert titled.display_label() == "My Title"
    untitled = ClipEntry(fragment=Fragment(markup="a long clip with no title at all here"))
    assert untitled.display_label() == untitled.preview(40)
