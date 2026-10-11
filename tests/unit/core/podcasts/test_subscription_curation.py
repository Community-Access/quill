from __future__ import annotations

from quill.core.podcasts import subscription_curation as curation
from quill.core.podcasts.models import ExpiredEntry, Playlist, PodcastFolder, PodcastShow, QueueItem
from quill.core.podcasts.models_filters import EpisodeFilterConfiguration
from quill.core.podcasts.models_playlists import PlaylistRules
from quill.core.podcasts.subscriptions import PodcastLibrary


def _library() -> PodcastLibrary:
    library = PodcastLibrary(
        shows=[PodcastShow(id="one", title="One"), PodcastShow(id="two", title="Two")],
        folders=[PodcastFolder("copy", "Copy")],
        queue=[QueueItem("two", "before"), QueueItem("one", "removed")],
        inbox_folders=[PodcastFolder("inbox", "Inbox folder")],
        inbox_assignments={"one\nremoved": "inbox", "two\nkept": ""},
        playlists=[
            Playlist(id="manual", name="Manual", items=[QueueItem("one", "removed")]),
            Playlist(id="smart", name="Smart", kind="smart", rules=PlaylistRules(show_ids=["one"])),
        ],
        recently_expired=[ExpiredEntry("one", "expired"), ExpiredEntry("two", "kept")],
        show_folder_copies={"one": ["copy"]},
        show_labels={"one": ["Label"], "two": ["Keep"]},
        scope_overrides={"show:one": {"speed": 1.5}, "show:two": {"speed": 2.0}},
        show_check_state={"one": {"failures": 2}},
        episode_filters={"one": EpisodeFilterConfiguration()},
        episode_filter_reviews={"one": "Needs review"},
        episode_filter_exceptions={"one": ["removed"]},
    )
    return library


def test_unfollow_removes_only_the_subscriptions_local_references() -> None:
    library = _library()

    assert library.remove_show("one")

    assert [(item.show_id, item.episode_guid) for item in library.queue] == [("two", "before")]
    assert library.inbox_assignments == {"two\nkept": ""}
    assert library.playlists[0].items == []
    assert library.playlists[1].rules.show_ids == ["one"]
    assert [(item.show_id, item.episode_guid) for item in library.recently_expired] == [
        ("two", "kept")
    ]
    assert library.show_labels == {"two": ["Keep"]}
    assert library.scope_overrides == {"show:two": {"speed": 2.0}}
    assert not library.show_folder_copies
    assert not library.show_check_state
    assert not library.episode_filters
    assert not library.episode_filter_reviews
    assert not library.episode_filter_exceptions


def test_undo_restores_the_delta_without_replacing_current_curation() -> None:
    library = _library()
    show = library.shows[0]
    removed = curation.capture(library, show.id)
    library.remove_show(show.id)
    arrived = QueueItem("two", "new")
    library.queue.append(arrived)
    library.playlists[0].items.append(arrived)
    library.inbox_assignments["two\nnew"] = ""
    library.show_labels["two"].append("New label")
    library.shows.append(show)

    curation.restore(library, show.id, removed)
    curation.restore(library, show.id, removed)

    assert library.queue[-1] is arrived
    assert [item.episode_guid for item in library.queue] == ["before", "removed", "new"]
    assert [item.episode_guid for item in library.playlists[0].items] == ["removed", "new"]
    assert library.inbox_assignments["two\nnew"] == ""
    assert library.inbox_assignments["one\nremoved"] == "inbox"
    assert library.show_labels["two"] == ["Keep", "New label"]
    assert library.show_folder_copies == {"one": ["copy"]}
    assert library.show_check_state == {"one": {"failures": 2}}
    assert library.episode_filters["one"] == removed.filters
    assert library.episode_filter_reviews["one"] == "Needs review"
    assert library.episode_filter_exceptions["one"] == ["removed"]
    assert sum(item.show_id == "one" for item in library.recently_expired) == 1


def test_undo_does_not_recreate_deleted_destinations_or_duplicate_the_primary() -> None:
    library = _library()
    library.show_folder_copies["one"].append(None)
    show = library.shows[0]
    removed = curation.capture(library, show.id)
    library.remove_show(show.id)
    library.folders.clear()
    library.inbox_folders.clear()
    library.playlists.clear()
    library.shows.append(show)

    curation.restore(library, show.id, removed)

    assert library.show_folder_copies == {}
    assert "one\nremoved" not in library.inbox_assignments
    assert library.playlists == []
    assert library.folders == []
    assert library.inbox_folders == []


def test_undo_keeps_newer_settings_and_episode_placements() -> None:
    library = _library()
    show = library.shows[0]
    removed = curation.capture(library, show.id)
    library.remove_show(show.id)
    library.shows.append(show)
    library.show_labels[show.id] = ["New"]
    library.scope_overrides[f"show:{show.id}"] = {"speed": 2.5}
    library.inbox_assignments["one\nremoved"] = ""
    current = QueueItem("one", "removed", reason="Added manually")
    library.queue.append(current)

    curation.restore(library, show.id, removed)

    assert library.show_labels[show.id] == ["New"]
    assert library.scope_overrides[f"show:{show.id}"] == {"speed": 2.5}
    assert library.inbox_assignments["one\nremoved"] == ""
    assert library.queue[-1] is current
