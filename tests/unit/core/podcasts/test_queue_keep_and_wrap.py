"""Keep finished episodes in the Play Queue (earshot.md E4) and start the queue
again from its first unplayed episode (E7). Pure, no wx."""

from __future__ import annotations

from quill.core.podcasts.models import PodcastEpisode, PodcastShow, QueueItem
from quill.core.podcasts.queue_steps import step_after_finishing
from quill.core.podcasts.subscriptions import PodcastLibrary


def _library(*guids: str, keep: bool = False, wrap: bool = False) -> PodcastLibrary:
    show = PodcastShow(
        id="s1",
        title="Show",
        feed_url="https://e/f.xml",
        episodes=[
            PodcastEpisode(guid=guid, title=guid, audio_url=f"https://e/{guid}.mp3")
            for guid in guids
        ],
    )
    library = PodcastLibrary(shows=[show])
    library.queue = [QueueItem(show_id="s1", episode_guid=guid) for guid in guids]
    library.settings.keep_finished_in_queue = keep
    library.settings.wrap_queue = wrap
    return library


def _finish(library: PodcastLibrary, guid: str) -> str:
    library.shows[0].find_episode(guid).played = True  # what record_finish did
    step, _freed = step_after_finishing(library, "s1", guid)
    return step.episode.guid if step.kind == "play" else step.kind


def _queue(library: PodcastLibrary) -> list[str]:
    return [item.episode_guid for item in library.queue]


def test_by_default_a_finished_episode_leaves() -> None:
    library = _library("a", "b", "c")
    assert _finish(library, "a") == "b"
    assert _queue(library) == ["b", "c"]


def test_kept_episodes_stay_and_the_run_steps_over_them() -> None:
    library = _library("a", "b", "c", keep=True)
    assert _finish(library, "a") == "b"
    assert _queue(library) == ["a", "b", "c"]
    assert _finish(library, "b") == "c"
    assert _finish(library, "c") == "edge"
    assert _queue(library) == ["a", "b", "c"]


def test_kept_finished_episodes_earlier_in_the_queue_are_skipped() -> None:
    library = _library("a", "b", "c", keep=True)
    library.shows[0].find_episode("b").played = True  # finished earlier
    assert _finish(library, "a") == "c"


def test_wrap_starts_again_from_the_first_unplayed_episode() -> None:
    # "a" was skipped past earlier and is still unplayed at the front.
    library = _library("a", "b", "c", wrap=True)
    library.queue = [QueueItem(show_id="s1", episode_guid=g) for g in ("a", "c")]
    assert _finish(library, "c") == "a"


def test_wrap_never_loops_on_finished_episodes() -> None:
    library = _library("a", "b", keep=True, wrap=True)
    assert _finish(library, "a") == "b"
    assert _finish(library, "b") == "edge"


def test_wrap_off_ends_the_run() -> None:
    library = _library("a", "b")
    assert _finish(library, "a") == "b"
    assert _finish(library, "b") == "edge"
