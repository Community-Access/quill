"""GATE-GITHUB-PERM (GitHub PRD 18.6, GH-R-062): every write declares what it needs, and its tier.

A new write cannot ship without knowing who may use it: every write command
in the Workbench's action table and bar, and every editable field on every
Properties sheet, names a requirement in the vocabulary
``quill.core.github.permissions.check`` reads and a tier of section 18.4.
Appendix C's objects all have a sheet, and Appendix D's rows all have a home.
"""

from __future__ import annotations

import pytest

from quill.core.github.item_actions import GITHUB_ACTIONS
from quill.core.github.permissions import ViewerContext, WriteTier, check
from quill.core.github.sheet_catalog import SHEETS
from quill.core.github.sheets_projects import ProjectField, project_item_sheet
from quill.core.github.workbench_window_menu import WINDOW_MENU
from quill.core.github.write_requirements import COMMAND_REQUIREMENTS
from quill.core.workbench.actions import Tier
from quill.core.workbench.menus import all_rows

_KINDS = {"repo", "org", "team", "scope", "viewer", "self", "sign_in", "local"}

#: Appendix C's objects, by the sheet kind each is.
APPENDIX_C = (
    "repository",
    "branch",
    "tag",
    "commit",
    "file",
    "ruleset",
    "branch_protection",
    "issue",
    "pull_request",
    "comment",
    "discussion",
    "label",
    "milestone",
    "issue_type",
    "project",
    "workflow",
    "run",
    "job",
    "artifact",
    "cache",
    "environment",
    "deployment",
    "runner",
    "secret",
    "variable",
    "release",
    "release_asset",
    "package",
    "person",
    "organization",
    "team",
    "collaborator",
    "invitation",
    "gist",
    "codespace",
    "security_alert",
    "notification",
    "webhook",
    "deploy_key",
)


def _valid(requirement: str) -> bool:
    tokens = [t for t in requirement.split("+") if t]
    return bool(tokens) and all(t.partition(":")[0] in _KINDS for t in tokens)


def test_every_write_command_declares_a_requirement_and_a_tier() -> None:
    missing = []
    for kind in GITHUB_ACTIONS.row_types:
        for row in GITHUB_ACTIONS.rows_for(kind):
            if row.tier <= Tier.READ:
                continue
            declared = COMMAND_REQUIREMENTS.get(row.command_id)
            if declared is None:
                missing.append(row.command_id)
                continue
            requirement, tier = declared
            assert _valid(requirement), row.command_id
            if row.tier == Tier.DESTRUCTIVE:
                assert tier == WriteTier.DESTRUCTIVE, row.command_id
    assert missing == []


def test_every_declared_command_is_a_real_row() -> None:
    known = {row.command_id for _m, row in all_rows(WINDOW_MENU)} | GITHUB_ACTIONS.commands()
    access_tools = {
        "access_add",
        "access_change",
        "access_remove",
        "delete_team",
        "create_team",
        "save_search",
        "new_issue",
    }
    for command_id in COMMAND_REQUIREMENTS:
        verb = command_id.removeprefix("github.workbench.")
        assert command_id in known or verb in access_tools, command_id


@pytest.mark.parametrize("kind", sorted(SHEETS))
def test_every_editable_field_has_a_write_with_requirement_and_tier(kind: str) -> None:
    sheet = SHEETS[kind]
    for key in sheet.editable_keys():
        write = sheet.writes.get(key)
        assert write is not None, f"{kind}.{key} is editable with no write"
        assert _valid(write.requirement), f"{kind}.{key}: {write.requirement!r}"
        assert isinstance(write.tier, WriteTier)


def test_a_project_item_sheet_built_from_its_fields_declares_too() -> None:
    sheet = project_item_sheet([
        ProjectField("F1", "Status", "SINGLE_SELECT", (("Todo", "o1"), ("Done", "o2"))),
        ProjectField("F2", "Estimate", "NUMBER"),
        ProjectField("F3", "Title", "TITLE"),
    ])
    for key in sheet.editable_keys():
        assert _valid(sheet.writes[key].requirement)
    status = sheet.sheet.field("f_F1")
    assert status.choices == ("Todo", "Done")


def test_every_appendix_c_object_has_a_sheet_that_opens_on_general() -> None:
    for kind in APPENDIX_C:
        assert kind in SHEETS, kind
        assert SHEETS[kind].sheet.pages[0].key == "general"


def test_destructive_writes_are_tier_3_and_access_writes_need_admin_or_owner() -> None:
    assert SHEETS["repository"].writes["visibility"].tier == WriteTier.DESTRUCTIVE
    for kind in ("ruleset", "environment", "collaborator"):
        for write in SHEETS[kind].writes.values():
            assert write.tier >= WriteTier.ACCESS, kind
            assert check(write.requirement, ViewerContext(repo_role="write")), kind
            assert not check(write.requirement, ViewerContext(repo_role="admin")), kind


def test_safe_mode_and_read_only_lock_every_field_of_every_sheet() -> None:
    from quill.core.github.permissions import AccessLevel
    from quill.core.github.sheet_engine import locked_fields

    ctx = ViewerContext(
        repo_role="admin",
        org_role="owner",
        team_role="maintainer",
        is_self=True,
        level=AccessLevel.READ_ONLY,
    )
    for sheet in SHEETS.values():
        locked = locked_fields(sheet, ctx)
        assert set(locked) == set(sheet.writes), sheet.kind
