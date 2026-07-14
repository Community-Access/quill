"""Recently-used and favorited emoji store (Insert > Emoji...)."""

from __future__ import annotations

from pathlib import Path

from quill.core.emoji_usage import EmojiUsage


def _store(tmp_path: Path) -> EmojiUsage:
    return EmojiUsage.load(tmp_path / "emoji_usage.json")


def test_record_used_moves_to_front_dedups_and_persists(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.record_used("\U0001f600")
    store.record_used("\U0001f436")
    store.record_used("\U0001f600")  # re-used -> moves back to front, not duplicated

    assert store.recent == ["\U0001f600", "\U0001f436"]
    assert _store(tmp_path).recent == ["\U0001f600", "\U0001f436"]


def test_record_used_ignores_empty_char(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.record_used("")
    assert store.recent == []


def test_record_used_caps_at_thirty(tmp_path: Path) -> None:
    store = _store(tmp_path)
    for i in range(35):
        store.record_used(chr(0x1F600 + i))
    assert len(store.recent) == 30
    # Most recently used stays at the front.
    assert store.recent[0] == chr(0x1F600 + 34)


def test_clear_recent(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.record_used("\U0001f600")
    store.clear_recent()
    assert store.recent == []
    assert _store(tmp_path).recent == []


def test_favorite_add_remove_toggle_round_trip(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.is_favorite("\U0001f600") is False

    assert store.add_favorite("\U0001f600") is True
    assert store.add_favorite("\U0001f600") is False  # already a favorite
    assert store.is_favorite("\U0001f600") is True
    assert _store(tmp_path).favorites == ["\U0001f600"]

    assert store.remove_favorite("\U0001f600") is True
    assert store.remove_favorite("\U0001f600") is False  # not a favorite anymore
    assert store.is_favorite("\U0001f600") is False
    assert _store(tmp_path).favorites == []


def test_toggle_favorite_flips_state_and_returns_new_state(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.toggle_favorite("\U0001f436") is True
    assert store.is_favorite("\U0001f436") is True
    assert store.toggle_favorite("\U0001f436") is False
    assert store.is_favorite("\U0001f436") is False


def test_add_favorite_rejects_empty_char(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.add_favorite("") is False
    assert store.favorites == []


def test_corrupt_file_degrades_to_empty(tmp_path: Path) -> None:
    path = tmp_path / "emoji_usage.json"
    path.write_text("not json", encoding="utf-8")
    store = EmojiUsage.load(path)
    assert store.recent == []
    assert store.favorites == []


def test_unfavoriting_never_touches_the_catalog(tmp_path: Path, monkeypatch) -> None:
    """Un-favoriting is bookkeeping on this store only -- it must never call
    into quill.core.emoji_data (the read-only shared catalog) at all."""
    import quill.core.emoji_data as emoji_data

    def _boom(*_a: object, **_k: object) -> None:
        raise AssertionError("emoji_usage must never touch the catalog")

    monkeypatch.setattr(emoji_data, "_load", _boom)
    store = _store(tmp_path)
    store.add_favorite("\U0001f600")
    store.remove_favorite("\U0001f600")  # must not raise
