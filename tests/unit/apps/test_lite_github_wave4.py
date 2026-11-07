"""QUILL Lite reaches every Wave 4 GitHub feature through the shared surfaces.

Lite opens the same ``GitHubItemsDialog`` (and, from it, the same
``GitHubExploreDialog``) that QUILL does, so a Wave 4 feature is in Lite exactly
when it lives on one of those. This pins that it stayed there.
"""

from __future__ import annotations

from quill.core.github.explore_views import AUTH_VIEWS, QUERY_VIEWS, REPO_VIEWS, VIEWS
from quill.ui.github_explore_dialog import GitHubExploreDialog
from quill.ui.github_items_dialog import GitHubItemsDialog


def test_wave4_explore_views_are_in_the_shared_view_list() -> None:
    keys = {key for key, _label in VIEWS}
    assert {"code_search", "commit_search", "repo_search"} <= keys & QUERY_VIEWS
    assert {"insights", "community", "actions_caches", "secrets"} <= keys & REPO_VIEWS
    assert {"code_search", "insights", "actions_caches", "secrets"} <= AUTH_VIEWS


def test_wave4_actions_live_on_the_shared_dialogs() -> None:
    for name in (
        "_sync_fork",
        "_set_topics",
        "_choose_watch_level",
        "_set_archived",
        "_from_template",
        "_delete_repository",
        "_set_following",
        "_delete_cache",
        "_show_rate_limit",
        "_on_explore_char_hook",
        "_note_if_unchanged",
    ):
        assert callable(getattr(GitHubExploreDialog, name))
    for name in (
        "_lock_item",
        "_unlock_item",
        "_transfer_item",
        "_pin_item",
        "_set_item_type",
        "_reorder_sub_issues",
        "_edit_selected_release",
        "_upload_release_asset",
        "_delete_selected_asset",
        "_show_api_rate_limit",
    ):
        assert callable(getattr(GitHubItemsDialog, name))
