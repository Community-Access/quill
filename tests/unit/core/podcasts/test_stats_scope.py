"""Listening statistics narrowed to a folder and its subfolders (earshot.md E9)."""

from __future__ import annotations

from quill.core.podcasts import stats
from quill.core.podcasts.models import PodcastFolder, PodcastShow
from quill.core.podcasts.stats_scope import ALL, UNFILED, scope_choices, show_ids_in
from quill.core.podcasts.subscriptions import PodcastLibrary


def _library() -> PodcastLibrary:
    library = PodcastLibrary(
        shows=[
            PodcastShow(id="news", title="News", folder_id="f-news"),
            PodcastShow(id="local", title="Local", folder_id="f-local"),
            PodcastShow(id="loose", title="Loose"),
        ]
    )
    library.folders = [
        PodcastFolder(id="f-news", name="News"),
        PodcastFolder(id="f-local", name="Local", parent_folder_id="f-news"),
    ]
    library.show_folder_copies = {"local": ["f-news"]}  # filed twice in the subtree
    return library


def _session(show_id: str, seconds: float) -> stats.ListeningSession:
    return stats.ListeningSession(
        show_id=show_id, episode_guid="e", date="2026-11-15T10:00:00+00:00", seconds=seconds
    )


def test_choices_are_all_then_folders_by_path_then_unfiled() -> None:
    assert scope_choices(_library()) == [
        (ALL, "All folders"),
        ("f-news", "News"),
        ("f-local", "News / Local"),
        (UNFILED, "Unfiled"),
    ]


def test_a_folder_means_its_subtree_and_counts_a_show_once() -> None:
    library = _library()
    assert show_ids_in(library, "f-news") == {"news", "local"}
    assert show_ids_in(library, "f-local") == {"local"}
    assert show_ids_in(library, UNFILED) == {"loose"}
    assert show_ids_in(library, ALL) is None


def test_summarize_narrows_to_the_scope() -> None:
    library = _library()
    sessions = [_session("news", 60), _session("local", 120), _session("loose", 600)]
    narrowed = stats.summarize(sessions, show_ids=show_ids_in(library, "f-news"))
    assert narrowed.total_seconds == 180
    assert stats.summarize(sessions).total_seconds == 780
