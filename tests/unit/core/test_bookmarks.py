from pathlib import Path

from quill.core.bookmarks import (
    BookmarkVault,
    bookmark_names,
    bookmark_position,
    set_bookmark,
)


def test_set_bookmark_adds_or_replaces_position() -> None:
    bookmarks: dict[str, int] = {}
    bookmarks = set_bookmark(bookmarks, "Intro", 12)
    bookmarks = set_bookmark(bookmarks, "Intro", 20)
    assert bookmark_position(bookmarks, "Intro") == 20


def test_set_bookmark_ignores_blank_name() -> None:
    bookmarks = set_bookmark({}, "   ", 10)
    assert bookmarks == {}


def test_bookmark_names_sorted_case_insensitive() -> None:
    bookmarks = {"zeta": 1, "Alpha": 2}
    assert bookmark_names(bookmarks) == ["Alpha", "zeta"]


# --- #300 BookmarkVault persistence wrapper -----------------------------


def test_bookmark_vault_round_trip(tmp_path: Path) -> None:
    """#300: set -> save -> load must return the same bookmarks."""
    target = tmp_path / "bookmarks.json"
    vault = BookmarkVault(path=target)
    vault.set("Intro", 12)
    vault.set("Body", 200)
    vault.set("Conclusion", 999)

    loaded = BookmarkVault.load(target)
    assert loaded.names() == ["Body", "Conclusion", "Intro"]
    assert loaded.position("Intro") == 12
    assert loaded.position("Body") == 200
    assert loaded.position("Conclusion") == 999


def test_bookmark_vault_load_missing_file_returns_empty(tmp_path: Path) -> None:
    """#300: a missing bookmark file must yield an empty vault, never raise."""
    target = tmp_path / "does-not-exist.json"
    vault = BookmarkVault.load(target)
    assert vault.names() == []
    assert vault.bookmarks == {}


def test_bookmark_vault_load_malformed_file_returns_empty(tmp_path: Path) -> None:
    """#300: a malformed JSON file must yield an empty vault."""
    target = tmp_path / "bookmarks.json"
    with open(target, "wb") as f:
        f.write(b"{not valid json")
    vault = BookmarkVault.load(target)
    assert vault.bookmarks == {}


def test_bookmark_vault_set_clamps_negative_position(tmp_path: Path) -> None:
    """#300: negative positions must be clamped to zero so a corrupt
    or out-of-range offset never survives a save/load cycle."""
    target = tmp_path / "bookmarks.json"
    vault = BookmarkVault(path=target)
    vault.set("Anchor", -10)
    assert vault.position("Anchor") == 0
    loaded = BookmarkVault.load(target)
    assert loaded.position("Anchor") == 0


def test_bookmark_vault_set_ignores_blank_name(tmp_path: Path) -> None:
    """#300: blank names must not be persisted."""
    target = tmp_path / "bookmarks.json"
    vault = BookmarkVault(path=target)
    vault.set("   ", 10)
    vault.set("", 20)
    assert vault.bookmarks == {}
    assert not target.exists()


def test_bookmark_vault_remove_returns_true_when_present(tmp_path: Path) -> None:
    """#300: remove must return True when a bookmark was removed
    and persist the new state."""
    target = tmp_path / "bookmarks.json"
    vault = BookmarkVault(path=target)
    vault.set("Intro", 12)
    assert vault.remove("Intro") is True
    loaded = BookmarkVault.load(target)
    assert loaded.position("Intro") is None


def test_bookmark_vault_remove_returns_false_when_absent(tmp_path: Path) -> None:
    """#300: remove must return False when no such bookmark exists."""
    target = tmp_path / "bookmarks.json"
    vault = BookmarkVault(path=target)
    assert vault.remove("Missing") is False


def test_bookmark_vault_clear_empties_and_persists(tmp_path: Path) -> None:
    """#300: clear must empty the in-memory map and persist the
    empty state so the next session starts clean."""
    target = tmp_path / "bookmarks.json"
    vault = BookmarkVault(path=target)
    vault.set("A", 1)
    vault.set("B", 2)
    vault.clear()
    assert vault.bookmarks == {}
    loaded = BookmarkVault.load(target)
    assert loaded.bookmarks == {}


# --- DocumentMemory: per-document persistence + last position (persistent bookmarks) ---
from pathlib import Path as _Path  # noqa: E402

from quill.core.bookmarks import DocumentMemory  # noqa: E402


def test_document_memory_persists_bookmarks_and_last_position(tmp_path: _Path) -> None:
    store = tmp_path / "document_memory.json"
    mem = DocumentMemory(path=store)
    key = DocumentMemory.key_for(tmp_path / "Report.md")
    mem.set_bookmarks(key, {"intro": 10, "end": 200})
    mem.set_last_position(key, 123)
    reloaded = DocumentMemory.load(store)
    assert reloaded.bookmarks_for(key) == {"intro": 10, "end": 200}
    assert reloaded.last_position(key) == 123


def test_document_memory_is_per_document(tmp_path: _Path) -> None:
    mem = DocumentMemory(path=tmp_path / "dm.json")
    a = DocumentMemory.key_for(tmp_path / "a.md")
    b = DocumentMemory.key_for(tmp_path / "b.md")
    mem.set_bookmarks(a, {"x": 1})
    mem.set_last_position(b, 50)
    assert mem.bookmarks_for(a) == {"x": 1}
    assert mem.bookmarks_for(b) == {}  # a's bookmarks never leak into b
    assert mem.last_position(a) is None
    assert mem.last_position(b) == 50


def test_document_memory_untitled_is_never_persisted(tmp_path: _Path) -> None:
    mem = DocumentMemory(path=tmp_path / "dm.json")
    assert DocumentMemory.key_for(None) is None
    assert DocumentMemory.key_for("") is None
    mem.set_bookmarks(None, {"x": 1})  # no-op, no crash
    mem.set_last_position(None, 5)
    assert mem.bookmarks_for(None) == {}
    assert mem.last_position(None) is None
    assert not store_exists(tmp_path / "dm.json")


def store_exists(p: _Path) -> bool:
    return p.exists()


def test_document_memory_load_is_forgiving(tmp_path: _Path) -> None:
    bad = tmp_path / "dm.json"
    bad.write_text("{ this is not json", encoding="utf-8")
    mem = DocumentMemory.load(bad)  # must not raise
    assert mem.documents == {}


def test_document_memory_keys_are_path_normalized(tmp_path: _Path) -> None:
    k1 = DocumentMemory.key_for(tmp_path / "Doc.md")
    k2 = DocumentMemory.key_for(str(tmp_path / "Doc.md"))
    assert k1 == k2 and k1 is not None
