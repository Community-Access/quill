"""The Inbox curation layer: folders for episodes, remembered per-show
filing, forget-remembered, and persistence -- pure, no UI."""

from __future__ import annotations

from quill.core.podcasts import inbox
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary, load_library, save_library


def _library_with_inbox_show() -> tuple[PodcastLibrary, PodcastShow, PodcastEpisode]:
    library = PodcastLibrary()
    show = PodcastShow(
        id="s1", title="Routed Show", feed_url="https://a/feed.xml", route_to_inbox=True
    )
    episode = PodcastEpisode(guid="g1", title="Ep 1", audio_url="https://a/1.mp3")
    show.episodes.append(episode)
    library.add_show(show)
    return library, show, episode


def test_inbox_pairs_only_include_routed_unplayed_episodes() -> None:
    library, show, episode = _library_with_inbox_show()
    played = PodcastEpisode(guid="g2", title="Old", audio_url="https://a/2.mp3", played=True)
    show.episodes.append(played)
    other = PodcastShow(id="s2", title="Unrouted", feed_url="https://b/feed.xml")
    other.episodes.append(PodcastEpisode(guid="g3", title="X", audio_url="https://b/1.mp3"))
    library.add_show(other)

    pairs = inbox.inbox_pairs(library)
    assert [(s.id, e.guid) for s, e in pairs] == [("s1", "g1")]


def test_first_manual_filing_is_remembered_for_the_show() -> None:
    library, show, episode = _library_with_inbox_show()
    folder = inbox.add_inbox_folder(library, "Listen Soon")

    remembered = inbox.file_episode(library, show, episode, folder.id)

    assert remembered is True
    assert show.inbox_default_folder_id == folder.id
    assert inbox.effective_inbox_folder_id(library, show, episode) == folder.id


def test_remembered_folder_auto_files_future_episodes() -> None:
    library, show, episode = _library_with_inbox_show()
    folder = inbox.add_inbox_folder(library, "Listen Soon")
    inbox.file_episode(library, show, episode, folder.id)

    fresh = PodcastEpisode(guid="g9", title="New Ep", audio_url="https://a/9.mp3")
    show.episodes.append(fresh)

    assert inbox.effective_inbox_folder_id(library, show, fresh) == folder.id
    filed = inbox.inbox_pairs_in_folder(library, folder.id)
    assert {e.guid for _s, e in filed} == {"g1", "g9"}


def test_second_manual_filing_does_not_overwrite_remembered_folder() -> None:
    library, show, episode = _library_with_inbox_show()
    first = inbox.add_inbox_folder(library, "First")
    second = inbox.add_inbox_folder(library, "Second")
    inbox.file_episode(library, show, episode, first.id)

    other = PodcastEpisode(guid="g2", title="Ep 2", audio_url="https://a/2.mp3")
    show.episodes.append(other)
    remembered = inbox.file_episode(library, show, other, second.id)

    assert remembered is False
    assert show.inbox_default_folder_id == first.id
    assert inbox.effective_inbox_folder_id(library, show, other) == second.id


def test_explicit_unfile_overrides_the_remembered_folder() -> None:
    library, show, episode = _library_with_inbox_show()
    folder = inbox.add_inbox_folder(library, "Listen Soon")
    inbox.file_episode(library, show, episode, folder.id)

    inbox.file_episode(library, show, episode, None)

    assert inbox.effective_inbox_folder_id(library, show, episode) is None
    assert inbox.inbox_pairs_in_folder(library, None) == [(show, episode)]


def test_forget_remembered_folder_keeps_manual_placements() -> None:
    library, show, episode = _library_with_inbox_show()
    folder = inbox.add_inbox_folder(library, "Listen Soon")
    inbox.file_episode(library, show, episode, folder.id)

    inbox.forget_remembered_folder(show)

    fresh = PodcastEpisode(guid="g9", title="New Ep", audio_url="https://a/9.mp3")
    show.episodes.append(fresh)
    assert show.inbox_default_folder_id is None
    assert inbox.effective_inbox_folder_id(library, show, fresh) is None
    # The earlier manual placement is untouched.
    assert inbox.effective_inbox_folder_id(library, show, episode) == folder.id


def test_deleted_folder_reads_as_unfiled_not_vanished() -> None:
    library, show, episode = _library_with_inbox_show()
    folder = inbox.add_inbox_folder(library, "Temp")
    inbox.file_episode(library, show, episode, folder.id)
    library.inbox_folders.remove(folder)

    assert inbox.effective_inbox_folder_id(library, show, episode) is None
    assert (show, episode) in inbox.inbox_pairs_in_folder(library, None)


def test_nested_inbox_folders() -> None:
    library, show, episode = _library_with_inbox_show()
    parent = inbox.add_inbox_folder(library, "News")
    child = inbox.add_inbox_folder(library, "Politics", parent_folder_id=parent.id)
    inbox.file_episode(library, show, episode, child.id)
    assert inbox.inbox_pairs_in_folder(library, child.id) == [(show, episode)]
    assert inbox.inbox_pairs_in_folder(library, parent.id) == []


def test_inbox_persists_through_save_and_load(tmp_path) -> None:
    library, show, episode = _library_with_inbox_show()
    folder = inbox.add_inbox_folder(library, "Listen Soon")
    inbox.file_episode(library, show, episode, folder.id)

    save_library(tmp_path, library)
    restored = load_library(tmp_path)

    assert [f.name for f in restored.inbox_folders] == ["Listen Soon"]
    restored_show = restored.find_show("s1")
    assert restored_show is not None
    assert restored_show.inbox_default_folder_id == folder.id
    restored_episode = restored_show.find_episode("g1")
    assert restored_episode is not None
    assert inbox.effective_inbox_folder_id(restored, restored_show, restored_episode) == folder.id


def test_rename_inbox_folder() -> None:
    library, _show, _episode = _library_with_inbox_show()
    folder = inbox.add_inbox_folder(library, "Listen Soon")
    assert inbox.rename_inbox_folder(library, folder.id, "Later") is True
    assert inbox.find_inbox_folder(library, folder.id).name == "Later"
    assert inbox.rename_inbox_folder(library, folder.id, "  ") is False


def test_delete_inbox_folder_repoints_filings_and_defaults() -> None:
    library, show, episode = _library_with_inbox_show()
    parent = inbox.add_inbox_folder(library, "News")
    child = inbox.add_inbox_folder(library, "Politics", parent_folder_id=parent.id)
    inbox.file_episode(library, show, episode, child.id)
    assert show.inbox_default_folder_id == child.id

    assert inbox.delete_inbox_folder(library, child.id) is True

    # Filing and remembered default both move up to the parent.
    assert inbox.effective_inbox_folder_id(library, show, episode) == parent.id
    assert show.inbox_default_folder_id == parent.id
    assert inbox.find_inbox_folder(library, child.id) is None


def test_delete_top_level_inbox_folder_unfiles_episodes() -> None:
    library, show, episode = _library_with_inbox_show()
    folder = inbox.add_inbox_folder(library, "Temp")
    inbox.file_episode(library, show, episode, folder.id)

    inbox.delete_inbox_folder(library, folder.id)

    assert inbox.effective_inbox_folder_id(library, show, episode) is None
    assert show.inbox_default_folder_id is None
    assert (show, episode) in inbox.inbox_pairs_in_folder(library, None)
