"""The Workbench's one level check, as words (GitHub PRD 18.3.1, GH-R-060 to GH-R-066).

quill.core.github.write_gate decides, for one command, whether the account's
Workbench level allows it, and says why not in one sentence. The UI half (the
dispatcher calling it before anything is read or sent) is
tests/unit/ui/test_github_workbench_level_gate.py.
"""

from __future__ import annotations

import re

import pytest

from quill.core.github.outcome_feedback import Outcome, classify
from quill.core.github.permissions import AccessLevel, WriteTier
from quill.core.github.write_gate import (
    CHECKED_INSIDE,
    command_refusal,
    command_title,
    gated_commands,
    gated_tier,
    needed_level,
    refusal,
)
from quill.core.github.write_requirements import COMMAND_REQUIREMENTS, EDITOR_REQUIREMENTS

_P = "github.workbench."


@pytest.fixture(autouse=True)
def _not_safe_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)


def _level(level: AccessLevel):  # type: ignore[no-untyped-def]
    return lambda: level


def test_the_needed_level_follows_the_tier() -> None:
    assert needed_level(WriteTier.ORGANIZING) is AccessLevel.ORGANIZE
    assert needed_level(WriteTier.VISIBLE) is AccessLevel.ORGANIZE
    assert needed_level(WriteTier.ACCESS) is AccessLevel.FULL
    assert needed_level(WriteTier.DESTRUCTIVE) is AccessLevel.FULL


def test_read_only_names_the_command_both_levels_and_where_it_changes() -> None:
    said = command_refusal(f"{_P}close_reopen", _level(AccessLevel.READ_ONLY))
    assert said == (
        "Cannot run Close or Reopen: it needs Organize in the Workbench, and this account is "
        "Read Only; Account, Roles and Access, Workbench Level for This Account changes it."
    )


def test_organize_refuses_a_full_command_and_says_full() -> None:
    said = command_refusal(f"{_P}delete_branch", _level(AccessLevel.ORGANIZE))
    assert said.startswith("Cannot run Delete Branch: it needs Full in the Workbench")
    assert "this account is Organize" in said
    assert command_refusal(f"{_P}comment", _level(AccessLevel.ORGANIZE)) == ""


def test_safe_mode_is_named_as_the_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    said = refusal("run Comment", WriteTier.VISIBLE, AccessLevel.READ_ONLY)
    assert said == (
        "Cannot run Comment: it needs Organize in the Workbench, and QUILL is in Safe Mode, "
        "which keeps every account Read Only until QUILL is started normally."
    )


@pytest.mark.parametrize("command_id", sorted(gated_commands()))
def test_every_refusal_is_one_sentence_spoken_as_a_failure(command_id: str) -> None:
    said = command_refusal(command_id, _level(AccessLevel.READ_ONLY))
    assert said.endswith(".") and not re.search(r"\.\s", said), said
    assert command_title(command_id) in said
    assert classify(said) is Outcome.FAILURE  # always spoken, with the error tone


def test_every_gated_command_is_named_by_its_row_or_by_name() -> None:
    from quill.core.github.write_gate import _OWN_TITLES, _titles

    unnamed = [c for c in gated_commands() if c not in _titles() and c not in _OWN_TITLES]
    assert unnamed == []


def test_reads_local_lists_and_the_level_itself_are_never_gated() -> None:
    def never() -> AccessLevel:
        raise AssertionError("the level is read only for a command that writes")

    assert command_refusal(f"{_P}open", never) == ""
    assert command_refusal(f"{_P}account_level", never) == ""  # how you leave Read Only
    for command_id, (requirement, _tier) in COMMAND_REQUIREMENTS.items():
        if requirement == "local":
            assert gated_tier(command_id) is None, command_id
    for command_id in CHECKED_INSIDE:
        assert gated_tier(command_id) is None


def test_every_declared_write_but_local_and_checked_inside_is_gated() -> None:
    declared = {**COMMAND_REQUIREMENTS, **EDITOR_REQUIREMENTS}
    expected = {
        command_id: tier
        for command_id, (requirement, tier) in declared.items()
        if requirement != "local" and command_id not in CHECKED_INSIDE
    }
    assert gated_commands() == expected
    assert f"{_P}delete_branch" in expected and "github.rename_repository" in expected
