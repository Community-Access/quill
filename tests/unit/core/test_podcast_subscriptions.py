"""Tests for the podcast library store: subscriptions, folders, settings,
and episode merge (pure JSON persistence; no network)."""

from __future__ import annotations

from pathlib import Path

from quill.core.podcasts.models import PodcastEpisode, PodcastSettings, PodcastShow
from quill.core.podcasts.subscriptions import (
    PodcastLibrary,
    load_library,
    merge_episodes,
    save_library,
)

_SHOW_A = PodcastShow(id="a1", title="Show A", feed_url="https://a.example.com/feed.xml")
_SHOW_B = PodcastShow(id="b1", title="Show B", feed_url="https://b.example.com/feed.xml")


def test_load_library_missing_file_returns_empty(tmp_path: Path) -> None:
    library = load_library(tmp_path)
    assert library.shows == []
    assert library.folders == []


def test_load_library_corrupt_file_returns_empty(tmp_path: Path) -> None:
    (tmp_path / "podcasts_library.json").write_text("not json", encoding="utf-8")
    library = load_library(tmp_path)
    assert library.shows == []


def test_add_show_and_find() -> None:
    library = PodcastLibrary()
    assert library.add_show(_SHOW_A) is True
    assert library.find_show("a1") is _SHOW_A
    assert library.find_show_by_feed_url("https://a.example.com/feed.xml") is _SHOW_A
    assert library.find_show("missing") is None


def test_add_show_refuses_duplicate_feed_url() -> None:
    library = PodcastLibrary()
    library.add_show(_SHOW_A)
    duplicate = PodcastShow(id="a2", title="Show A Again", feed_url=_SHOW_A.feed_url)
    assert library.add_show(duplicate) is False
    assert len(library.shows) == 1


def test_remove_show() -> None:
    library = PodcastLibrary()
    library.add_show(_SHOW_A)
    assert library.remove_show("a1") is True
    assert library.find_show("a1") is None
    assert library.remove_show("a1") is False


def test_add_folder_and_find() -> None:
    library = PodcastLibrary()
    folder = library.add_folder("News")
    assert library.find_folder(folder.id) is folder
    assert folder.parent_folder_id is None


def test_find_or_create_folder_path_creates_nested_chain() -> None:
    library = PodcastLibrary()
    leaf_id = library.find_or_create_folder_path(["Tech", "Deep Dives"])
    assert leaf_id is not None
    leaf = library.find_folder(leaf_id)
    assert leaf is not None and leaf.name == "Deep Dives"
    parent = library.find_folder(leaf.parent_folder_id)  # type: ignore[arg-type]
    assert parent is not None and parent.name == "Tech"
    assert len(library.folders) == 2


def test_find_or_create_folder_path_reuses_existing_folders() -> None:
    library = PodcastLibrary()
    first = library.find_or_create_folder_path(["Tech"])
    second = library.find_or_create_folder_path(["Tech"])
    assert first == second
    assert len(library.folders) == 1


def test_effective_settings_prefers_show_override() -> None:
    library = PodcastLibrary(settings=PodcastSettings(speed=1.0))
    show_with_override = PodcastShow(id="s1", title="S", settings=PodcastSettings(speed=2.0))
    show_without_override = PodcastShow(id="s2", title="S2")
    assert library.effective_settings(show_with_override).speed == 2.0
    assert library.effective_settings(show_without_override).speed == 1.0


def test_merge_episodes_adds_new_and_updates_existing_metadata() -> None:
    existing = PodcastEpisode(
        guid="g1", title="Old Title", audio_url="https://x/e1.mp3", played=True, position_ms=5000
    )
    show = PodcastShow(id="s1", title="Show", episodes=[existing])
    fetched = [
        PodcastEpisode(guid="g1", title="New Title", audio_url="https://x/e1-updated.mp3"),
        PodcastEpisode(guid="g2", title="Episode Two", audio_url="https://x/e2.mp3"),
    ]
    new_count = merge_episodes(show, fetched)
    assert new_count == 1
    assert len(show.episodes) == 2
    updated = show.find_episode("g1")
    assert updated is not None
    assert updated.title == "New Title"
    assert updated.audio_url == "https://x/e1-updated.mp3"
    # local state preserved despite the feed refresh
    assert updated.played is True
    assert updated.position_ms == 5000


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    library = PodcastLibrary()
    library.add_show(_SHOW_A)
    folder = library.add_folder("News")
    show_in_folder = PodcastShow(id="c1", title="Show C", folder_id=folder.id, is_local=True)
    library.add_show(show_in_folder)
    save_library(tmp_path, library)

    reloaded = load_library(tmp_path)
    assert len(reloaded.shows) == 2
    assert reloaded.find_show("a1") is not None
    reloaded_c = reloaded.find_show("c1")
    assert reloaded_c is not None
    assert reloaded_c.folder_id == folder.id
    assert len(reloaded.folders) == 1
    assert reloaded.folders[0].name == "News"
