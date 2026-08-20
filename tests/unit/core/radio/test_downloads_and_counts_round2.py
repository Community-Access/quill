"""The 2026-08-18 afternoon round: cleanup, ask-prefs, and truthful badges.

Four reports from the field, each pinned here by the seam that broke:

* Remove All Downloads deletes only inside the show's own folder, resolved
  through the same path logic that wrote the files.
* Don't ask me again for Mark All as Played is one shared answer for both
  apps, and cancelling with the box ticked changes nothing.
* The unheard badges subtract Radio's own finished listens, so an episode
  heard to the end here stops counting *before* Cast's next merge.
* Marking one episode played is an explicit library edit with an honest
  sentence for every miss.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.podcasts import ask_prefs
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.radio_listens import finished_audio_urls, record_listen
from quill.core.podcasts.sorting import unheard_count
from quill.core.podcasts.subscriptions import load_library, new_id, save_library
from quill.core.radio import download_cleanup, download_prefs
from quill.core.radio.podcast_follow import (
    mark_episode_played,
    show_facts_for_feed,
    unheard_for_feed,
)

FEED = "https://feeds.example/show"


def _seed_show(tmp_path: Path, *, episodes: int = 3, played: int = 0) -> None:
    library = load_library(tmp_path)
    show = PodcastShow(id=new_id(), title="The Show", feed_url=FEED)
    show.episodes = [
        PodcastEpisode(
            guid=f"g{i}",
            title=f"Episode {i}",
            audio_url=f"https://cdn.example/ep{i}.mp3",
            played=i < played,
        )
        for i in range(episodes)
    ]
    library.shows.append(show)
    save_library(tmp_path, library)


def _prefs_rooted(tmp_path: Path) -> None:
    download_prefs.save(tmp_path, download_prefs.DownloadPrefs(root=str(tmp_path / "dl")))


# -- download cleanup ----------------------------------------------------------


def test_remove_show_downloads_takes_files_and_leaves_strangers(tmp_path: Path) -> None:
    _prefs_rooted(tmp_path)
    folder = download_cleanup.show_download_dir(tmp_path, "The Show")
    folder.mkdir(parents=True)
    (folder / "Episode 1.mp3").write_bytes(b"x")
    (folder / "Episode 1.mp3.licence.txt").write_text("cc", encoding="utf-8")
    (folder / "notes").mkdir()  # not ours: left standing

    assert download_cleanup.downloaded_file_count(tmp_path, "The Show") == 2
    spoken = download_cleanup.remove_show_downloads(tmp_path, "The Show")
    assert "Removed 2 downloaded files." == spoken
    assert folder.exists()  # the stranger subfolder kept the folder alive
    assert (folder / "notes").exists()
    assert download_cleanup.downloaded_file_count(tmp_path, "The Show") == 0


def test_removing_an_empty_show_is_an_honest_sentence(tmp_path: Path) -> None:
    _prefs_rooted(tmp_path)
    spoken = download_cleanup.remove_show_downloads(tmp_path, "Never Downloaded")
    assert spoken == "There is nothing downloaded for that show."
    assert download_cleanup.remove_show_downloads(tmp_path, "") == (
        "There is nothing downloaded for that show."
    )


def test_the_emptied_folder_is_removed(tmp_path: Path) -> None:
    _prefs_rooted(tmp_path)
    folder = download_cleanup.show_download_dir(tmp_path, "The Show")
    folder.mkdir(parents=True)
    (folder / "ep.mp3").write_bytes(b"x")
    download_cleanup.remove_show_downloads(tmp_path, "The Show")
    assert not folder.exists()


# -- the shared ask preference -------------------------------------------------


def test_mark_all_asks_by_default_and_one_answer_quiets_both_apps(tmp_path: Path) -> None:
    assert ask_prefs.ask_before_mark_all_played(tmp_path) is True
    ask_prefs.set_ask_before_mark_all_played(tmp_path, False)
    assert ask_prefs.ask_before_mark_all_played(tmp_path) is False
    ask_prefs.set_ask_before_mark_all_played(tmp_path, True)
    assert ask_prefs.ask_before_mark_all_played(tmp_path) is True


def test_a_corrupt_prefs_file_answers_the_safe_default(tmp_path: Path) -> None:
    (tmp_path / "podcast-ask-prefs.json").write_text("{not json", encoding="utf-8")
    assert ask_prefs.ask_before_mark_all_played(tmp_path) is True


# -- badges that subtract Radio's own listens ----------------------------------


def test_a_finished_listen_stops_counting_before_cast_merges(tmp_path: Path) -> None:
    _seed_show(tmp_path, episodes=3)
    assert unheard_for_feed(tmp_path, FEED) == 3
    record_listen(
        tmp_path,
        feed_url=FEED,
        audio_url="https://cdn.example/ep1.mp3",
        finished=True,
    )
    # The library still says unplayed (the handoff is append-only), but the
    # badge tells the listener's truth.
    assert unheard_for_feed(tmp_path, FEED) == 2
    assert "https://cdn.example/ep1.mp3" in finished_audio_urls(tmp_path)


def test_a_part_heard_listen_does_not_count_as_finished(tmp_path: Path) -> None:
    _seed_show(tmp_path, episodes=2)
    record_listen(
        tmp_path, feed_url=FEED, audio_url="https://cdn.example/ep0.mp3", position_ms=90_000
    )
    assert unheard_for_feed(tmp_path, FEED) == 2


def test_unheard_count_exclusion_is_opt_in(tmp_path: Path) -> None:
    show = PodcastShow(id=new_id(), title="S", feed_url=FEED)
    show.episodes = [
        PodcastEpisode(guid="a", title="A", audio_url="https://a/1.mp3"),
        PodcastEpisode(guid="b", title="B", audio_url="https://a/2.mp3"),
    ]
    assert unheard_count(show) == 2  # Cast's view: unchanged
    assert unheard_count(show, exclude_audio={"https://a/1.mp3"}) == 1


# -- one library read for the whole menu ---------------------------------------


def test_show_facts_answer_the_three_menu_questions(tmp_path: Path) -> None:
    _seed_show(tmp_path, episodes=4, played=1)
    unheard, episodes, title = show_facts_for_feed(tmp_path, FEED)
    assert (unheard, episodes, title) == (3, 4, "The Show")
    assert show_facts_for_feed(tmp_path, "https://feeds.example/other") == (0, 0, "")


# -- marking one episode -------------------------------------------------------


@pytest.mark.parametrize("played", [True, False])
def test_mark_episode_round_trips_with_honest_sentences(tmp_path: Path, played: bool) -> None:
    _seed_show(tmp_path, episodes=2, played=0 if played else 2)
    audio = "https://cdn.example/ep0.mp3"
    spoken = mark_episode_played(tmp_path, FEED, audio, played=played)
    assert spoken == f"Marked Episode 0 as {'played' if played else 'unplayed'}."
    library = load_library(tmp_path)
    episode = library.shows[0].episodes[0]
    assert episode.played is played
    if played:
        assert episode.position_ms == 0
    # Saying it again says "already", and edits nothing.
    assert "Already marked" in mark_episode_played(tmp_path, FEED, audio, played=played)


def test_marking_an_unknown_episode_or_show_says_which(tmp_path: Path) -> None:
    assert "not in your subscriptions" in mark_episode_played(
        tmp_path, FEED, "https://a/x.mp3", played=True
    )
    _seed_show(tmp_path, episodes=1)
    assert "not in the library yet" in mark_episode_played(
        tmp_path, FEED, "https://a/ghost.mp3", played=True
    )
