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
        ("by_name", "milestones", "repository_set", "rename", True),
        ("by_name", "milestones", "organization", "delete", True),
        ("by_name", "topics", "repository_set", "copy_missing", True),
        ("by_name", "topics", "repository_set", "make_same", False),
        ("by_name", "rules", "repository_set", "make_same", True),
        ("by_name", "rules", "organization", "promote_org", True),
        ("by_name", "rules", "every_permitted", "promote_org", False),
        ("by_name", "fleet", "own_repositories", "list", True),
        ("by_name", "secrets", "repository_set", "make_same", True),
        ("by_name", "secrets", "organization", "promote_org", True),
        ("by_name", "variables", "repository_set", "promote_org", True),
        ("by_name", "webhooks", "repository_set", "on_off", True),
        ("by_name", "webhooks", "every_permitted", "promote_org", False),
        ("by_name", "environments", "repository_set", "make_same", True),
        ("by_name", "environments", "repository_set", "promote_org", False),
        ("by_name", "environments", "repository_set", "copy_missing", True),
        ("by_name", "deploy_keys", "repository_set", "copy_missing", False),
        ("by_name", "deploy_keys", "repository_set", "promote_org", False),
        ("by_name", "autolinks", "repository_set", "promote_org", False),
        ("by_name", "tags", "repository_set", "copy_missing", True),
        ("by_name", "tags", "repository_set", "compare", True),
        ("by_name", "branches", "repository_set", "rename", True),
        ("by_name", "rules", "repository_set", "copy_missing", True),
        ("by_name", "branches", "filter_set", "delete", True),
        ("by_name", "releases", "repository_set", "make_same", True),
        ("by_name", "alerts", "every_permitted", "make_same", True),
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


# -- the single-repository rule (PRD 22.11; complete.md 1.3) --------------------------


def _live_verbs() -> set[str]:
    import importlib.util
    import sys
    from pathlib import Path

    qa = Path(__file__).resolve().parents[3] / "docs" / "qa"
    if str(qa) not in sys.path:
        sys.path.insert(0, str(qa))
    spec = importlib.util.spec_from_file_location(
        "github_live_verbs_m", qa / "github_live_verbs.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return set(module.VERBS)


def _covered(home: str, live: set[str]) -> bool:
    """A home exists and is covered: a sheet field (the sheets pass changes, reads back and
    puts back every one), or a command the live run has a row for. The editor's own
    commands are covered by their own suites."""
    from quill.core.github.api_coverage import home_exists
    from quill.core.github.write_requirements import COMMAND_REQUIREMENTS, EDITOR_REQUIREMENTS

    if home.startswith("sheet:"):
        return home_exists(home)
    command = home.removeprefix("command:")
    if command in EDITOR_REQUIREMENTS:
        return True
    return command in COMMAND_REQUIREMENTS and command.removeprefix("github.workbench.") in live


def test_a_write_across_repositories_is_done_only_when_the_single_repository_one_is() -> None:
    from quill.core.github.across_scope_matrix import SINGLE_REPOSITORY, WRITE_OPERATIONS

    live = _live_verbs()
    for (family, kind, _scope, op), cell in matrix().items():
        if family != "by_name" or op not in WRITE_OPERATIONS or not cell.supported:
            continue
        homes = SINGLE_REPOSITORY.get((kind, op))
        assert homes, f"{kind} {op} is done across repositories with no single-repository home"
        for home in homes:
            assert _covered(home, live), f"{kind} {op}: {home} is missing or not covered"
        assert cell.verb in live, f"{kind} {op}: the batch {cell.verb} has no live-run row"


def test_every_single_repository_home_is_for_a_cell_that_is_done() -> None:
    from quill.core.github.across_scope_matrix import SINGLE_REPOSITORY

    for kind, op in SINGLE_REPOSITORY:
        assert classify("by_name", kind, "repository_set", op).supported, (kind, op)


def test_held_back_writes_say_why_and_are_not_done() -> None:
    from quill.core.github.across_scope_matrix import HELD_BACK

    assert set(HELD_BACK) == set()  # may only shrink; GH-R-151 emptied it
    for (kind, op), reason in HELD_BACK.items():
        assert not classify("by_name", kind, "repository_set", op).supported
        assert "single-repository rule" in reason


def test_category_lists_never_write() -> None:
    from quill.core.github.across_scope_matrix import WRITE_OPERATIONS

    for (family, _kind, _scope, op), cell in matrix().items():
        if family == "category" and op in WRITE_OPERATIONS:
            assert not cell.supported, (family, _kind, op)
