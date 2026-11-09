"""The Developer profile is the only door to coding features, in both editors (code.md 6.4)."""

from __future__ import annotations

from quill.core.features import (
    PROFILE_DEFINITIONS,
    PROFILE_DEVELOPER_POWER_TEXT,
    PROFILE_FULL_QUILL,
    FeatureManager,
    feature_for_command,
)
from quill.core.keymap import DEFAULT_KEYMAP
from quill.core.lite.command_areas import area_for
from quill.core.lite.commands import COMMANDS
from quill.core.lite.features import PROFILES
from quill.core.lite.parity import COMMAND_EQUIVALENTS

#: Every developer command QUILL has: project tasks, local Git, the validator,
#: and the features that now depend on core.developer. Not core.github_remote,
#: since 2026-11-08: the Workbench is in every QUILL Lite profile, so it is in
#: QUILL's too (QUILL Lite may never be ahead).
_DEVELOPER_FEATURES = (
    "core.developer",
    "core.developer_console",
    "core.intellisense",
)


def test_the_github_workbench_is_not_a_developer_feature() -> None:
    manager = FeatureManager(active_profile_id="essential")
    assert manager.is_enabled("core.github_remote")
    assert manager.is_enabled(feature_for_command("file.open_github_items"))
    assert manager.is_enabled(feature_for_command("view.github_workbench_mode"))
    # Local Git is still coding, and still the Developer profile's.
    assert not manager.is_enabled(feature_for_command("localgit.worktrees"))


def _project_commands() -> list[str]:
    return [cid for cid in DEFAULT_KEYMAP if cid.startswith("project.")]


def test_project_and_git_commands_belong_to_core_developer() -> None:
    assert _project_commands(), "no project.* commands in the keymap"
    for command_id in (*_project_commands(), "localgit.worktrees", "tools.validate_agents"):
        assert feature_for_command(command_id) == "core.developer", command_id


def test_no_developer_command_is_visible_outside_the_developer_profiles() -> None:
    allowed = {PROFILE_DEVELOPER_POWER_TEXT, PROFILE_FULL_QUILL}
    for profile_id in PROFILE_DEFINITIONS:
        manager = FeatureManager(active_profile_id=profile_id)
        for feature_id in _DEVELOPER_FEATURES:
            visible = manager.is_visible(feature_id)
            if profile_id in allowed and feature_id == "core.developer":
                assert visible, profile_id
            elif profile_id not in allowed:
                assert not visible, f"{feature_id} is visible in {profile_id}"
        for command_id in _project_commands():
            shown = manager.is_visible(feature_for_command(command_id))
            assert shown == (profile_id in allowed), (profile_id, command_id)


def test_turning_core_developer_on_by_hand_is_the_escape_hatch() -> None:
    manager = FeatureManager(active_profile_id="essential")
    assert not manager.is_enabled("core.developer_console")
    manager.overrides["core.developer"] = "on"
    manager.overrides["core.developer_console"] = "on"
    assert manager.is_enabled("core.developer_console")


def test_the_profile_is_called_developer() -> None:
    assert str(PROFILE_DEFINITIONS[PROFILE_DEVELOPER_POWER_TEXT].name) == "Developer"


def test_both_editors_developer_profiles_turn_on_the_same_shared_commands() -> None:
    lite_rows = {row[3] for row in COMMANDS if row[3] and area_for(row[0], row[3]) == "coding"}
    assert lite_rows, "QUILL Lite has no Coding rows"
    quill_ids = {COMMAND_EQUIVALENTS[h] for h in lite_rows}
    assert quill_ids == set(_project_commands())
    developer = next(p for p in PROFILES if p.id == "developer")
    assert "coding" not in developer.disabled
    for profile in PROFILES:
        if profile.id != "developer":
            assert "coding" in profile.disabled, profile.id


def test_each_developer_command_sits_where_people_look_in_both_editors() -> None:
    """Jeff, 2026-11-04: not one submenu; the same menus in QUILL and QUILL Lite."""
    from quill.core.ai.ai_menu_layout import DEVELOPER_TASK_HANDLERS
    from quill.core.lite.commands_ai import AI_MENU_ROWS
    from quill.ui.main_frame_project_rows import PROJECT_ROWS

    lite_menu = {row[3]: row[0].split("|")[0].replace("&", "") for row in COMMANDS if row[3]}
    quill_menu = {
        COMMAND_EQUIVALENTS_BY_ID[cid]: menu
        for menu, rows in PROJECT_ROWS.items()
        for cid, _l, _h in rows
    }
    expected = {"file": "File", "edit": "Edit", "view": "View", "tools": "Tools", "ai": "Tools"}
    for handler, menu in quill_menu.items():
        assert lite_menu[handler] == expected[menu], (handler, menu, lite_menu[handler])
    handlers = [row[3] for row in AI_MENU_ROWS]
    task = handlers.index("cmd_ai_task")
    which = handlers.index("cmd_ai_which")
    for handler in DEVELOPER_TASK_HANDLERS:
        assert task < handlers.index(handler) < which, handler
    assert {h for _c, _l, h in PROJECT_ROWS["ai"]} == set(DEVELOPER_TASK_HANDLERS)


COMMAND_EQUIVALENTS_BY_ID = {quill_id: handler for handler, quill_id in COMMAND_EQUIVALENTS.items()}
