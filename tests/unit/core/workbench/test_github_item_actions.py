"""GitHub's context-menu table against GitHub PRD section 5's rules."""

from __future__ import annotations

from quill.core.github.item_actions import (
    CODESPACES_COMMAND,
    CODESPACES_ROW_TYPES,
    GITHUB_ACTIONS,
    PROPERTIES_COMMAND,
    RATE_LIMIT_COMMAND,
)
from quill.core.workbench.actions import MENU_TOP_LIMIT, ActionScope, Tier

PRD_ROW_TYPES = {
    "issue",
    "pull_request",
    "run",
    "workflow",
    "release",
    "release_asset",
    "branch",
    "commit",
    "tag",
    "notification",
    "repository",
    "person",
    "label",
    "gist",
    "discussion",
    "security_alert",
    "cache",
    "saved_search",
    "node",
}


def test_every_row_type_in_the_prd_table_has_a_menu() -> None:
    assert PRD_ROW_TYPES <= set(GITHUB_ACTIONS.row_types)


def test_rule_1_the_default_comes_first_and_never_deletes() -> None:
    for kind in GITHUB_ACTIONS.row_types:
        first = GITHUB_ACTIONS.rows_for(kind)[0]
        assert first.default, kind
        assert first.tier < Tier.DESTRUCTIVE, kind


def test_rule_2_only_rows_about_the_row() -> None:
    for kind in GITHUB_ACTIONS.row_types:
        assert all(row.scope is ActionScope.ITEM for row in GITHUB_ACTIONS.rows_for(kind))


def test_rule_3_about_eight_rows_then_more_and_nothing_lost() -> None:
    for kind in GITHUB_ACTIONS.row_types:
        top, more = GITHUB_ACTIONS.menu_for(kind)
        assert len(top) + (1 if more else 0) <= MENU_TOP_LIMIT, kind
        shown = [row.command_id for row in [*top[:-1], *more, top[-1]]]
        assert shown == [row.command_id for row in GITHUB_ACTIONS.rows_for(kind)], kind


def test_rule_4_codespaces_only_on_a_repository_branch_or_pull_request() -> None:
    assert set(GITHUB_ACTIONS.row_types_offering(CODESPACES_COMMAND)) == CODESPACES_ROW_TYPES


def test_rule_5_the_rate_limit_is_on_no_context_menu() -> None:
    assert RATE_LIMIT_COMMAND not in GITHUB_ACTIONS.commands()
    for kind in GITHUB_ACTIONS.row_types:
        assert not any("Rate Limit" in label for label in GITHUB_ACTIONS.labels(kind))


def test_rule_6_properties_is_the_last_row_everywhere() -> None:
    for kind in GITHUB_ACTIONS.row_types:
        top, _more = GITHUB_ACTIONS.menu_for(kind)
        assert top[-1].command_id == PROPERTIES_COMMAND, kind


def test_every_row_says_what_it_does() -> None:
    for kind in GITHUB_ACTIONS.row_types:
        for row in GITHUB_ACTIONS.rows_for(kind):
            assert row.help.endswith("."), (kind, row.command_id)


def test_the_prd_defaults() -> None:
    defaults = {kind: GITHUB_ACTIONS.default_for(kind).label for kind in PRD_ROW_TYPES}
    assert defaults["pull_request"] == "Review..."
    assert defaults["run"] == "Jobs and Logs"
    assert defaults["release"] == "Assets"
    assert defaults["branch"] == "Commits"
    assert defaults["issue"] == "Open"
