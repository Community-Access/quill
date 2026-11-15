"""GH-E: every kind x scope x operation across repositories is a decided cell (PRD 22.11)."""

from __future__ import annotations

import pytest

from quill.core.github.across_scope_matrix import (
    BY_NAME_KINDS,
    CATEGORY_KINDS,
    OPERATIONS,
    SCOPES,
    classify,
    matrix,
)
from quill.core.github.item_actions import GITHUB_ACTIONS


def test_no_cell_is_blank() -> None:
    cells = matrix()
    total = (len(CATEGORY_KINDS) + len(BY_NAME_KINDS)) * len(SCOPES) * len(OPERATIONS)
    assert len(cells) == total
    for key, cell in cells.items():
        assert cell.reason.strip(), key
        assert bool(cell.verb) == cell.supported, key


def test_every_supported_verb_is_a_real_command_or_the_list_loader() -> None:
    commands = {c.removeprefix("github.workbench.") for c in GITHUB_ACTIONS.commands()}
    for key, cell in matrix().items():
        if cell.supported and not cell.verb.startswith("load_"):
            assert cell.verb in commands, key


def test_every_supported_verb_has_a_handler() -> None:
    pytest.importorskip("wx")
    from quill.ui.github_workbench_window import GitHubWorkbenchProvider

    for key, cell in matrix().items():
        if cell.supported:
            name = cell.verb if cell.verb.startswith("load_") else f"_do_{cell.verb}"
            assert callable(getattr(GitHubWorkbenchProvider, name, None)), key


@pytest.mark.parametrize(
    ("family", "kind", "scope", "op", "supported"),
    [
        ("by_name", "labels", "repository_set", "merge", True),
        ("by_name", "labels", "organization", "rename", True),
        ("by_name", "labels", "every_permitted", "rename", True),
        ("by_name", "labels", "organization", "promote_org", False),
        ("by_name", "milestones", "filter_set", "close", True),
        ("by_name", "milestones", "repository_set", "merge", True),
        ("by_name", "milestones", "repository_set", "rename", False),
        ("by_name", "topics", "repository_set", "copy_missing", True),
        ("by_name", "topics", "repository_set", "make_same", False),
        ("by_name", "rules", "repository_set", "make_same", True),
        ("by_name", "rules", "organization", "promote_org", True),
        ("by_name", "rules", "every_permitted", "promote_org", False),
        ("by_name", "fleet", "own_repositories", "list", True),
        ("by_name", "secrets_variables", "repository_set", "make_same", False),
        ("category", "issues", "repository_set", "list", True),
        ("category", "issues", "repository_set", "delete", False),
        ("category", "alerts", "every_permitted", "list", True),
    ],
)
def test_the_decided_cells(family: str, kind: str, scope: str, op: str, supported: bool) -> None:
    assert classify(family, kind, scope, op).supported is supported


def test_an_organization_is_a_filter_made_set_and_says_so() -> None:
    cell = classify("by_name", "labels", "organization", "make_same")
    assert "org:name" in cell.reason
