"""Pinned repositories + favorites store (GHManage parity, QUILL conventions)."""

from __future__ import annotations

from pathlib import Path

import quill.core.github.saved_items as saved_items_module
from quill.core.github.saved_items import FavoriteItem, GitHubSavedItems


def _store(tmp_path: Path) -> GitHubSavedItems:
    return GitHubSavedItems.load(tmp_path / "github_saved_items.json")


def test_pin_unpin_round_trip_with_case_insensitive_dedup(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.pin_repo("Community-Access/QUILL") is True
    assert store.pin_repo("community-access/quill") is False  # dedup
    assert store.pin_repo("no-slash") is False  # not owner/repo shaped
    assert store.is_pinned("COMMUNITY-ACCESS/QUILL") is True

    reloaded = _store(tmp_path)
    assert reloaded.pinned == ["Community-Access/QUILL"]
    assert reloaded.unpin_repo("community-access/QUILL") is True
    assert reloaded.unpin_repo("community-access/QUILL") is False
    assert _store(tmp_path).pinned == []


def test_favorites_round_trip_dedup_and_timestamp(tmp_path: Path) -> None:
    store = _store(tmp_path)
    entry = FavoriteItem(
        repo="o/r", item_type="issue", url="https://github.com/o/r/issues/1", title="#1 Bug"
    )
    assert store.add_favorite(entry) is True
    assert store.add_favorite(entry) is False  # dedup by repo+type+url
    assert store.add_favorite(FavoriteItem(repo="", item_type="issue", url="x", title="")) is False

    reloaded = _store(tmp_path)
    assert len(reloaded.favorites) == 1
    saved = reloaded.favorites[0]
    assert saved.title == "#1 Bug"
    assert saved.added_at  # stamped at add time
    assert reloaded.remove_favorite(saved.key) is True
    assert _store(tmp_path).favorites == []


def test_corrupt_store_degrades_to_empty(tmp_path: Path) -> None:
    target = tmp_path / "github_saved_items.json"
    target.write_text("not json at all", encoding="utf-8")
    store = GitHubSavedItems.load(target)
    assert store.pinned == [] and store.favorites == []
    assert store.get_columns("branches", ["name", "commit"]) == ["name", "commit"]


def test_column_prefs_round_trip_and_default_fallback(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.get_columns("branches", ["name", "protected"]) == ["name", "protected"]
    store.set_columns("branches", ["name"])

    reloaded = _store(tmp_path)
    assert reloaded.get_columns("branches", ["name", "protected"]) == ["name"]
    # A view never customized still falls back to the caller's default.
    assert reloaded.get_columns("issues", ["number", "title"]) == ["number", "title"]


def test_column_prefs_ignore_malformed_entries(tmp_path: Path) -> None:
    target = tmp_path / "github_saved_items.json"
    target.write_text(
        '{"columns": {"branches": ["name", 5], "bad": "not-a-list", "empty": []}}',
        encoding="utf-8",
    )
    store = GitHubSavedItems.load(target)
    assert store.get_columns("branches", ["name", "protected"]) == ["name"]
    assert store.get_columns("bad", ["x"]) == ["x"]
    assert store.get_columns("empty", ["x"]) == ["x"]


def test_global_searches_and_recent_repositories_round_trip(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.save_search("is:pr review-requested:me")
    assert not store.save_search(" IS:PR REVIEW-REQUESTED:ME ")
    store.remember_repo("owner/first")
    store.remember_repo("owner/second")
    store.remember_repo("OWNER/first")
    loaded = _store(tmp_path)
    assert loaded.searches == ["is:pr review-requested:me"]
    assert loaded.recent == ["OWNER/first", "owner/second"]
    assert loaded.remove_search("IS:PR REVIEW-REQUESTED:ME")
    assert _store(tmp_path).searches == []


def test_saved_items_are_isolated_per_account_after_one_time_migration(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(saved_items_module, "app_data_dir", lambda: tmp_path)
    legacy = tmp_path / "github_saved_items.json"
    legacy.write_text('{"pinned": ["owner/legacy"]}', encoding="utf-8")

    anonymous = GitHubSavedItems.load(account_key="anonymous")
    assert anonymous.pinned == []

    first = GitHubSavedItems.load(account_key="account-one")
    assert first.pinned == ["owner/legacy"]
    first.pin_repo("owner/first-only")

    second = GitHubSavedItems.load(account_key="account-two")
    assert second.pinned == []
    assert GitHubSavedItems.load(account_key="account-one").pinned == [
        "owner/legacy",
        "owner/first-only",
    ]
    assert legacy.exists()  # migration leaves a local recovery copy


def test_legacy_saved_items_are_assigned_to_only_the_first_authenticated_account(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(saved_items_module, "app_data_dir", lambda: tmp_path)
    (tmp_path / "github_saved_items.json").write_text('{"searches": ["is:pr"]}', encoding="utf-8")

    assert GitHubSavedItems.load(account_key="first-account").searches == ["is:pr"]
    assert GitHubSavedItems.load(account_key="second-account").searches == []
