"""Tests for saved playlists: Smart Playlist rule resolution (pure) and
manual Playlist item resolution (self-healing against stale references)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from quill.core.podcasts.models import (
    Playlist,
    PlaylistRules,
    PodcastEpisode,
    PodcastShow,
    QueueItem,
)
from quill.core.podcasts.playlists import new_playlist_id, resolve_playlist
from quill.core.podcasts.subscriptions import PodcastLibrary

_OLD = "Wed, 01 Jul 2026 00:00:00 GMT"
_NEW = "Wed, 15 Jul 2026 00:00:00 GMT"


def _episode(
    guid: str,
    *,
    title: str = "",
    published: str = "",
    duration: int = 0,
    played: bool = False,
    position_ms: int = 0,
) -> PodcastEpisode:
    return PodcastEpisode(
        guid=guid,
        title=title or guid,
        audio_url=f"https://x/{guid}.mp3",
        published=published,
        duration_seconds=duration,
        played=played,
        position_ms=position_ms,
    )


def _show(
    show_id: str, *, title: str = "", episodes: list[PodcastEpisode] | None = None
) -> PodcastShow:
    return PodcastShow(id=show_id, title=title or show_id, episodes=episodes or [])


def test_new_playlist_id_is_unique() -> None:
    assert new_playlist_id() != new_playlist_id()


def test_manual_playlist_resolves_in_stored_order() -> None:
    ep1, ep2 = _episode("g1"), _episode("g2")
    show = _show("s1", episodes=[ep1, ep2])
    library = PodcastLibrary(shows=[show])
    playlist = Playlist(
        id="p1",
        name="My Mix",
        kind="manual",
        items=[
            QueueItem(show_id="s1", episode_guid="g2"),
            QueueItem(show_id="s1", episode_guid="g1"),
        ],
    )
    resolved = resolve_playlist(library, playlist)
    assert [e.guid for _show, e in resolved] == ["g2", "g1"]


def test_manual_playlist_self_heals_stale_references() -> None:
    ep1 = _episode("g1")
    show = _show("s1", episodes=[ep1])
    library = PodcastLibrary(shows=[show])
    playlist = Playlist(
        id="p1",
        name="My Mix",
        kind="manual",
        items=[
            QueueItem(show_id="s1", episode_guid="g1"),
            QueueItem(show_id="unsubscribed-show", episode_guid="g9"),
            QueueItem(show_id="s1", episode_guid="vanished-episode"),
        ],
    )
    resolved = resolve_playlist(library, playlist)
    assert [e.guid for _show, e in resolved] == ["g1"]


def test_smart_playlist_all_defaults_matches_everything() -> None:
    show_a = _show("a", episodes=[_episode("g1", published=_NEW)])
    show_b = _show("b", episodes=[_episode("g2", published=_OLD)])
    library = PodcastLibrary(shows=[show_a, show_b])
    playlist = Playlist(id="p1", name="Everything", kind="smart", rules=PlaylistRules())
    resolved = resolve_playlist(library, playlist)
    assert {e.guid for _show, e in resolved} == {"g1", "g2"}


def test_smart_playlist_filters_by_show_ids() -> None:
    show_a = _show("a", episodes=[_episode("g1")])
    show_b = _show("b", episodes=[_episode("g2")])
    library = PodcastLibrary(shows=[show_a, show_b])
    playlist = Playlist(id="p1", name="Just A", kind="smart", rules=PlaylistRules(show_ids=["a"]))
    resolved = resolve_playlist(library, playlist)
    assert [e.guid for _show, e in resolved] == ["g1"]


def test_smart_playlist_filters_by_episode_status() -> None:
    show = _show(
        "a",
        episodes=[
            _episode("unplayed", played=False),
            _episode("played", played=True),
            _episode("in_progress", played=False, position_ms=5000),
        ],
    )
    library = PodcastLibrary(shows=[show])

    unplayed = resolve_playlist(
        library,
        Playlist(id="p1", name="U", kind="smart", rules=PlaylistRules(episode_status="unplayed")),
    )
    assert {e.guid for _show, e in unplayed} == {"unplayed", "in_progress"}

    played = resolve_playlist(
        library,
        Playlist(id="p2", name="P", kind="smart", rules=PlaylistRules(episode_status="played")),
    )
    assert {e.guid for _show, e in played} == {"played"}

    in_progress = resolve_playlist(
        library,
        Playlist(
            id="p3", name="IP", kind="smart", rules=PlaylistRules(episode_status="in_progress")
        ),
    )
    assert {e.guid for _show, e in in_progress} == {"in_progress"}


def test_smart_playlist_filters_by_duration_range() -> None:
    show = _show(
        "a",
        episodes=[
            _episode("short", duration=300),  # 5 min
            _episode("medium", duration=1800),  # 30 min
            _episode("long", duration=5400),  # 90 min
        ],
    )
    library = PodcastLibrary(shows=[show])
    playlist = Playlist(
        id="p1",
        name="Medium",
        kind="smart",
        rules=PlaylistRules(min_duration_minutes=10, max_duration_minutes=60),
    )
    resolved = resolve_playlist(library, playlist)
    assert [e.guid for _show, e in resolved] == ["medium"]


def test_smart_playlist_filters_by_published_within_days() -> None:
    recent = datetime.now(UTC) - timedelta(days=1)
    stale = datetime.now(UTC) - timedelta(days=30)
    show = _show(
        "a",
        episodes=[
            _episode("recent", published=recent.strftime("%a, %d %b %Y %H:%M:%S GMT")),
            _episode("stale", published=stale.strftime("%a, %d %b %Y %H:%M:%S GMT")),
            _episode("undated", published=""),
        ],
    )
    library = PodcastLibrary(shows=[show])
    playlist = Playlist(
        id="p1", name="Recent", kind="smart", rules=PlaylistRules(published_within_days=7)
    )
    resolved = resolve_playlist(library, playlist)
    assert [e.guid for _show, e in resolved] == ["recent"]


def test_smart_playlist_respects_sort_mode() -> None:
    show = _show("a", episodes=[_episode("old", published=_OLD), _episode("new", published=_NEW)])
    library = PodcastLibrary(shows=[show])
    playlist = Playlist(
        id="p1", name="Oldest first", kind="smart", rules=PlaylistRules(sort_mode="date_oldest")
    )
    resolved = resolve_playlist(library, playlist)
    assert [e.guid for _show, e in resolved] == ["old", "new"]


def test_playlist_rules_round_trip() -> None:
    original = PlaylistRules(
        show_ids=["a", "b"],
        episode_status="unplayed",
        published_within_days=14,
        min_duration_minutes=5,
        max_duration_minutes=90,
        sort_mode="title_az",
    )
    restored = PlaylistRules.from_dict(original.to_dict())
    assert restored == original


def test_playlist_round_trip_smart() -> None:
    original = Playlist(id="p1", name="My Smart", kind="smart", rules=PlaylistRules(show_ids=["a"]))
    restored = Playlist.from_dict(original.to_dict())
    assert restored == original


def test_playlist_round_trip_manual() -> None:
    original = Playlist(
        id="p2",
        name="My Manual",
        kind="manual",
        items=[QueueItem(show_id="a", episode_guid="g1")],
    )
    restored = Playlist.from_dict(original.to_dict())
    assert restored == original


def test_playlist_from_dict_requires_id_and_name() -> None:
    assert Playlist.from_dict({"name": "X"}) is None
    assert Playlist.from_dict({"id": "p1"}) is None
    assert Playlist.from_dict({}) is None
    assert Playlist.from_dict("junk") is None


def test_playlist_from_dict_rejects_unknown_kind() -> None:
    playlist = Playlist.from_dict({"id": "p1", "name": "X", "kind": "bogus"})
    assert playlist is not None
    assert playlist.kind == "manual"


def test_library_playlist_crud() -> None:
    library = PodcastLibrary()
    playlist = Playlist(id="p1", name="Mix")
    library.add_playlist(playlist)
    assert library.find_playlist("p1") is playlist
    assert library.rename_playlist("p1", "  New Name  ") is True
    assert playlist.name == "New Name"
    assert library.rename_playlist("missing", "X") is False
    assert library.rename_playlist("p1", "   ") is False
    assert library.remove_playlist("p1") is True
    assert library.find_playlist("p1") is None
    assert library.remove_playlist("p1") is False
