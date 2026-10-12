from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.core.podcasts.library_payload import LibraryPayload, serialize
from quill.core.podcasts.models import PodcastEpisode, PodcastShow, QueueItem
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.podcasts.save_snapshot import Changes, SaveScope, coherent_chunks


@pytest.mark.parametrize("json_payload", [False, True])
def test_sustained_position_updates_do_not_restart_the_catalogue_copy(json_payload) -> None:
    library = PodcastLibrary(
        shows=[
            PodcastShow(
                id=f"s{show_index}",
                title="Synthetic",
                episodes=[
                    PodcastEpisode(guid=f"e{index}", title="Episode", audio_url="")
                    for index in range(300)
                ],
            )
            for show_index in range(10)
        ]
    )
    host = SimpleNamespace(_podcast_library=library, _podcast_library_revision=0)
    changes = Changes()
    steps = coherent_chunks(host, changes, json_payload=json_payload)
    episode = library.shows[0].episodes[-1]
    turns = 0
    while True:
        episode.position_ms += 1000
        host._podcast_library_revision += 1
        changes.record(SaveScope("s0", episode.guid))
        try:
            next(steps)
        except StopIteration as outcome:
            snapshot = outcome.value
            break
        turns += 1
        assert turns < 150
    data = snapshot.data if isinstance(snapshot, LibraryPayload) else serialize(snapshot)
    assert data["shows"][0]["episodes"][-1]["position_ms"] == episode.position_ms
    assert data["shows"][0]["episodes"][-1] is not episode
    assert len(data["shows"]) == 10


@pytest.mark.parametrize("json_payload", [False, True])
def test_show_and_queue_changes_catch_up_to_one_coherent_generation(json_payload) -> None:
    episode = PodcastEpisode(guid="old", title="Old", audio_url="")
    library = PodcastLibrary(shows=[PodcastShow(id="s", title="Show", episodes=[episode])])
    host = SimpleNamespace(_podcast_library=library, _podcast_library_revision=0)
    changes = Changes()
    steps = coherent_chunks(host, changes, json_payload=json_payload)
    next(steps)
    library.shows[0].episodes.append(PodcastEpisode(guid="new", title="New", audio_url=""))
    library.queue.append(QueueItem(show_id="s", episode_guid="new"))
    host._podcast_library_revision += 1
    changes.record(SaveScope("s"))
    while True:
        try:
            next(steps)
        except StopIteration as outcome:
            snapshot = outcome.value
            break
    data = snapshot.data if isinstance(snapshot, LibraryPayload) else serialize(snapshot)
    assert [item["guid"] for item in data["shows"][0]["episodes"]] == ["old", "new"]
    assert [(item["show_id"], item["episode_guid"]) for item in data["queue"]] == [("s", "new")]
    assert data["queue"] is not library.queue
    assert data["queue"][0] is not library.queue[0]
