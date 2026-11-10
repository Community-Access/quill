"""The GitHub Workbench tree: nothing dropped, and the PRD's shape (sections 3.3, 10, 14.4)."""

from __future__ import annotations

from quill.core.github import explore_views
from quill.core.github.workbench_tree import GITHUB_TREE, PLANNED, node_for_items_view
from quill.core.workbench.coverage import CoverageStatus
from quill.core.workbench.tree import MAX_DEPTH, Need
from quill.ui import github_items_view


def test_nothing_dropped_every_items_and_explore_view_has_exactly_one_home() -> None:
    homes = GITHUB_TREE.homes()
    for key, _label in github_items_view.VIEWS:
        assert len(homes.get(f"items:{key}", [])) == 1, key
    for key, _label in explore_views.VIEWS:
        assert len(homes.get(f"explore:{key}", [])) == 1, key


def test_every_items_or_explore_loader_names_a_real_view() -> None:
    known = {f"items:{key}" for key, _ in github_items_view.VIEWS} | {
        f"explore:{key}" for key, _ in explore_views.VIEWS
    }
    used = {name for name in GITHUB_TREE.loaders() if name.startswith(("items:", "explore:"))}
    assert used <= known, used - known


def test_the_top_level_is_the_prd_order() -> None:
    assert [node.label for node in GITHUB_TREE.roots()] == [
        "Start Here",
        "Needs My Attention",
        "Repositories",
        "Search",
        "People",
        "Gists",
        "Projects",
        "Watches",
        "Across Repositories",
    ]


def test_every_repository_gets_the_same_children_in_order() -> None:
    labels = [node.label for node in GITHUB_TREE.children("repository", template="repository")]
    assert labels[:5] == [
        "Overview",
        "Issues",
        "Pull Requests",
        "Issues and Pull Requests",
        "Discussions",
    ]
    assert labels[-3:] == ["GitHub Pages", "Security", "Settings"]
    runs = GITHUB_TREE.template_node("repository", "runs")
    assert runs.parent == "actions"


def test_no_node_is_more_than_four_levels_deep() -> None:
    for node in GITHUB_TREE:
        assert GITHUB_TREE.depth(node.key) <= MAX_DEPTH, node.key


def test_nodes_needing_sign_in_or_permission_are_listed_not_hidden() -> None:
    needing = [node.key for _t, node in GITHUB_TREE.all_nodes() if node.needs]
    assert "notifications" in needing
    secrets = GITHUB_TREE.template_node("repository", "secrets")
    assert Need.ADMIN in secrets.needs
    assert Need.OPT_IN in GITHUB_TREE.template_node("repository", "health").needs


def test_the_seven_items_views_map_to_repository_nodes() -> None:
    for key, _label in github_items_view.VIEWS:
        node = GITHUB_TREE.template_node("repository", node_for_items_view(key))
        assert node.loader == f"items:{key}"
        assert node.home


def test_planned_features_have_a_future_home_and_no_node_yet() -> None:
    assert PLANNED.rows
    assert all(row.status is CoverageStatus.PLANNED for row in PLANNED.rows)
    labels = {node.label for _t, node in GITHUB_TREE.all_nodes()}
    assert "Wiki" not in labels
    assert "Packages" not in labels
