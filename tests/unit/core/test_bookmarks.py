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
