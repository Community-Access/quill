"""Saving primitive generations preserves the complete durable library shape."""

from __future__ import annotations

import copy
from types import SimpleNamespace

from quill.core.podcasts.library_payload import LibraryPayload, serialize
from quill.core.podcasts.models import PodcastEpisode, PodcastSettings, PodcastShow, QueueItem
from quill.core.podcasts.namespace_tags import NamespaceTags, Person
from quill.core.podcasts.subscriptions import PodcastLibrary, load_library, save_library
from quill.ui.podcasts.save_snapshot import Changes, SaveScope, coherent_chunks


def _library() -> PodcastLibrary:
    episode = PodcastEpisode(
        guid="episode",
        title="Listener's episode name",
        feed_title="Publisher's episode name",
        audio_url="https://example.invalid/audio.mp3",
        played=True,
        position_ms=42_000,
        tags=NamespaceTags(people=[Person("Synthetic guest")], podroll=["https://example.invalid"]),
    )
    show = PodcastShow(
        id="show",
        title="Listener's show name",
        feed_title="Publisher's show name",
        feed_url="https://example.invalid/feed",
        episodes=[episode],
        settings=PodcastSettings(speed=1.5),
        tags=NamespaceTags(location="Synthetic location"),
    )
    library = PodcastLibrary(shows=[show])
    first = library.add_folder("First")
    second = library.add_folder("Second")
    show.folder_id = first.id
    library.show_folder_copies[show.id] = [second.id]
    library.queue.append(QueueItem(show_id=show.id, episode_guid=episode.guid))
    library.inbox_assignments["show/episode"] = ""
    library.show_labels[show.id] = ["Synthetic label"]
    library.extra_settings["synthetic"] = {"nested": ["retained"]}
    library.scope_overrides[f"show:{show.id}"] = {"speed": 1.75}
    library.show_check_state[show.id] = {"checked": "2026-10-07T00:00:00Z", "failures": 0}
    library.last_auto_check = "2026-10-07T00:00:00Z"
    return library


def _finish(steps):
    while True:
        try:
            next(steps)
        except StopIteration as result:
            return result.value


def test_payload_persists_the_same_json_as_the_model_and_round_trips(tmp_path) -> None:
    library = _library()
    save_library(tmp_path, library)
    expected = (tmp_path / "podcasts_library.json").read_bytes()
    host = SimpleNamespace(_podcast_library=library)

    payload = _finish(coherent_chunks(host, Changes(), json_payload=True))

    assert isinstance(payload, LibraryPayload)
    assert payload.data == serialize(library)
    save_library(tmp_path, payload)
    assert (tmp_path / "podcasts_library.json").read_bytes() == expected
    restored = load_library(tmp_path)
    assert len(restored.shows) == 1
    assert restored.shows[0].episodes[0].position_ms == 42_000
    assert restored.shows[0].episodes[0].tags.people == [Person("Synthetic guest")]
    assert restored.show_folder_copies == library.show_folder_copies
    assert restored.scope_overrides == library.scope_overrides


def test_payload_shares_no_mutable_metadata_with_the_live_library(tmp_path) -> None:
    library = _library()
    host = SimpleNamespace(_podcast_library=library)
    payload = _finish(coherent_chunks(host, Changes(), json_payload=True))
    expected = copy.deepcopy(serialize(library))

    library.shows[0].tags.location = "Changed"
    library.shows[0].settings.speed = 2.0
    library.shows[0].episodes[0].tags.people.clear()
    library.shows[0].episodes[0].tags.podroll.append("https://example.invalid/changed")
    library.queue.clear()
    library.extra_settings["synthetic"]["nested"].append("changed")
    library.show_folder_copies["show"].clear()
    library.show_labels["show"].clear()
    library.scope_overrides["show:show"]["speed"] = 3.0

    assert payload.data == expected
    save_library(tmp_path, payload)
    restored = load_library(tmp_path)
    assert restored.shows[0].tags.location == "Synthetic location"
    assert restored.shows[0].episodes[0].tags.people == [Person("Synthetic guest")]
    assert restored.scope_overrides["show:show"]["speed"] == 1.75


def test_scoped_tag_changes_and_added_episodes_catch_up_before_queueing() -> None:
    library = _library()
    host = SimpleNamespace(_podcast_library=library)
    changes = Changes()
    steps = coherent_chunks(host, changes, json_payload=True)
    next(steps)
    episode = library.shows[0].episodes[0]
    episode.tags.people.append(Person("New guest"))
    episode.position_ms = 84_000
    changes.record(SaveScope("show", episode.guid))
    library.shows[0].episodes.append(
        PodcastEpisode(guid="new", title="New episode", audio_url="https://example.invalid/new")
    )
    library.queue.append(QueueItem(show_id="show", episode_guid="new"))
    changes.record(SaveScope("show"))

    payload = _finish(steps)

    assert payload.data == serialize(library)
    assert len(payload.data["shows"][0]["episodes"]) == 2
    assert payload.data["shows"][0]["episodes"][0]["position_ms"] == 84_000
