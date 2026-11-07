"""Per-account workbench resume state is local, bounded, and validated."""

from __future__ import annotations

import json

from quill.core.github import navigation_state
from quill.core.github.navigation_state import GitHubItemsContext, GitHubNavigationState


def test_resume_state_is_saved_per_token_digest_without_persisting_the_token(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(navigation_state, "app_data_dir", lambda: tmp_path)
    token = "ghp_test_secret_value"
    context = GitHubItemsContext(
        repository="owner/repo",
        view="runs",
        state="all",
        sort="created_desc",
        search_query="is:failure",
        quick_filter_query="build",
        selected_key="run:12345",
    )

    assert GitHubNavigationState.load(token).save(context)
    saved_text = (tmp_path / "github_items_context.json").read_text(encoding="utf-8")

    assert token not in saved_text
    assert GitHubNavigationState.load(token).context == context
    assert GitHubNavigationState.load("another-token").context == GitHubItemsContext()


def test_corrupt_or_malformed_resume_state_degrades_to_defaults(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(navigation_state, "app_data_dir", lambda: tmp_path)
    path = tmp_path / "github_items_context.json"
    path.write_text("{", encoding="utf-8")

    assert GitHubNavigationState.load(None).context == GitHubItemsContext()

    path.write_text(
        json.dumps({
            "accounts": {
                "anonymous": {
                    "repository": "owner/repo",
                    "view": [],
                    "show": [],
                    "state": [],
                }
            }
        }),
        encoding="utf-8",
    )
    assert GitHubNavigationState.load(None).context == GitHubItemsContext(repository="owner/repo")


def test_resume_state_rejects_non_repository_paths_and_trims_large_filters(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(navigation_state, "app_data_dir", lambda: tmp_path)
    state = GitHubNavigationState.load(None)
    state.save(
        GitHubItemsContext(
            repository="owner/repo/issues/2",
            search_query="x" * 1000,
            quick_filter_query="y" * 1000,
            selected_key="issue:" + "z" * 500,
        )
    )

    restored = GitHubNavigationState.load(None).context
    assert restored.repository == ""
    assert len(restored.search_query) == 512
    assert len(restored.quick_filter_query) == 512
    assert len(restored.selected_key) == 256


def test_recent_location_history_supports_back_forward_and_branching(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(navigation_state, "app_data_dir", lambda: tmp_path)
    state = GitHubNavigationState.load("history-token")
    first = GitHubItemsContext(repository="owner/one", selected_key="issue:1")
    second = GitHubItemsContext(repository="owner/one", view="branches", selected_key="branch:main")
    third = GitHubItemsContext(repository="owner/two", selected_key="pr:9")

    state.record(first)
    state.record(second)
    state.record(third)
    assert state.can_go_back and not state.can_go_forward
    assert state.back() == second
    state.record(second)
    assert state.can_go_forward
    assert state.forward() == third
    assert state.back() == second
    assert state.back() == first
    assert state.forward() == second
    state.record(GitHubItemsContext(repository="owner/three", selected_key="issue:4"))
    assert not state.can_go_forward
    assert state.can_go_back
    assert state.save(state.context)

    restored = GitHubNavigationState.load("history-token")
    assert restored.context.repository == "owner/three"
    assert restored.back() == second
    assert restored.forward() == GitHubItemsContext(
        repository="owner/three", selected_key="issue:4"
    )
