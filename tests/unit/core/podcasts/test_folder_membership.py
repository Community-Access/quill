from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.podcasts import folder_actions, folder_membership, library_view, opml, opml_import
from quill.core.podcasts.models import PodcastEpisode, PodcastFolder, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary, load_library, save_library


def library() -> PodcastLibrary:
    return PodcastLibrary(
        shows=[
            PodcastShow(
                id="show",
                title="One show",
                feed_url="https://example.test/rss",
                folder_id="news",
                episodes=[
                    PodcastEpisode(
                        guid="episode", title="Episode", audio_url="https://example.test/audio"
                    )
                ],
            )
        ],
        folders=[
            PodcastFolder(id="news", name="News"),
            PodcastFolder(id="short", name="Short", parent_folder_id="news"),
            PodcastFolder(id="other", name="Other"),
        ],
    )


def test_copy_shares_one_subscription_episode_and_history() -> None:
    value = library()
    show = value.shows[0]
    episode = show.episodes[0]
    assert folder_membership.copy_to(value, show, "other")
    assert not folder_membership.copy_to(value, show, "other")
    assert len(value.shows) == 1
    assert folder_actions.subtree_show_ids(value, "news") == [show.id]
    assert folder_actions.subtree_show_ids(value, "other") == [show.id]
    episode.played = True
    assert value.find_show(show.id).episodes[0] is episode
    assert value.find_show(show.id).episodes[0].played


def test_move_changes_only_the_selected_placement() -> None:
    value = library()
    show = value.shows[0]
    folder_membership.copy_to(value, show, "other")
    assert folder_membership.move_to(value, show, "short", source="other")
    assert folder_membership.placements(value, show) == ("news", "short")
    assert folder_membership.move_to(value, show, "short", source="news")
    assert folder_membership.placements(value, show) == ("short",)


def test_top_level_copy_is_a_real_placement() -> None:
    value = library()
    show = value.shows[0]
    folder_membership.copy_to(value, show, None)
    assert folder_membership.move_to(value, show, "other", source=None)
    assert folder_membership.placements(value, show) == ("news", "other")


def test_missing_destination_or_source_is_rejected() -> None:
    value = library()
    show = value.shows[0]
    with pytest.raises(ValueError, match="destination"):
        folder_membership.copy_to(value, show, "missing")
    with pytest.raises(ValueError, match="selected folder"):
        folder_membership.move_to(value, show, "other", source="missing")
    assert folder_membership.placements(value, show) == ("news",)


def test_subtree_counts_count_a_subscription_once() -> None:
    value = library()
    folder_membership.copy_to(value, value.shows[0], "short")
    assert folder_actions.subtree_show_ids(value, "news") == ["show"]
    assert library_view._folder_totals(value, value.shows, {"show": 1}) == {
        "news": (1, 1),
        "short": (1, 1),
        "other": (0, 0),
    }


def test_promote_preserves_copies_without_duplicate_placements() -> None:
    value = library()
    show = value.shows[0]
    folder_membership.copy_to(value, show, "short")
    folder_membership.copy_to(value, show, "other")
    value.delete_folder("short")
    assert folder_membership.placements(value, show) == ("news", "other")
    value.delete_folder("news")
    assert folder_membership.placements(value, show) == (None, "other")
    assert len(value.shows) == 1


def test_explicit_unfollow_folder_removes_subscription_everywhere() -> None:
    value = library()
    show = value.shows[0]
    folder_membership.copy_to(value, show, "other")
    assert value.delete_folder("other", contents="remove") == [show]
    assert value.shows == []
    assert value.show_folder_copies == {}


def test_copies_survive_atomic_save_and_load(tmp_path: Path) -> None:
    value = library()
    folder_membership.copy_to(value, value.shows[0], "other")
    folder_membership.copy_to(value, value.shows[0], None)
    save_library(tmp_path, value)
    restored = load_library(tmp_path)
    assert len(restored.shows) == 1
    assert folder_membership.placements(restored, restored.shows[0]) == ("news", "other", None)


def test_opml_round_trip_keeps_placements_without_duplicate_subscriptions() -> None:
    value = library()
    show = value.shows[0]
    folder_membership.copy_to(value, show, "other")
    folder_membership.copy_to(value, show, None)
    exported = opml.export_opml(value)
    restored = PodcastLibrary()
    plan = opml_import.plan_import(
        restored, opml.parse_opml(exported), folders=opml.parse_opml_folders(exported)
    )
    assert len(opml_import.apply_plan(restored, plan)) == 1
    assert len(restored.shows) == 1
    restored_show = restored.shows[0]
    folder_names = {
        restored.find_folder(folder).name if folder else None
        for folder in folder_membership.placements(restored, restored_show)
    }
    assert folder_names == {"News", "Other", None}
    assert len(opml.parse_opml(opml.export_subtree(value, "other"))) == 1


def test_import_existing_subscription_adds_only_a_missing_placement() -> None:
    value = library()
    entries = [
        opml.ImportedShow(
            title="One show",
            feed_url="http://EXAMPLE.test/rss/",
            homepage="",
            folder_path=["Other"],
        )
    ]
    plan = opml_import.plan_import(value, entries)
    assert opml_import.apply_plan(value, plan) == []
    assert plan.copied_placements == 1
    assert folder_membership.placements(value, value.shows[0]) == ("news", "other")


def test_custom_reordering_uses_the_selected_copy_folder() -> None:
    value = library()
    show = value.shows[0]
    neighboring = PodcastShow(id="neighbor", title="Neighbor", folder_id="other")
    unrelated = PodcastShow(id="unrelated", title="Unrelated", folder_id="news")
    value.shows.extend([unrelated, neighboring])
    folder_membership.copy_to(value, show, "other")

    assert folder_membership.reorder(value, show, 1, folder_id="other")

    assert [item.id for item in value.shows] == ["neighbor", "unrelated", "show"]
    assert not folder_membership.reorder(value, show, 1, folder_id="other")
    assert folder_membership.placements(value, show) == ("news", "other")
