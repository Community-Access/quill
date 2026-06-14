"""Source-contract tests for power-tool (EDS-1..21) UI wiring in main_frame.py.

These assert that every power-tool command is registered (palette + Keymap Editor)
and recirculated into its conventional menu, and that the read-only guard and
key/indent event hooks are wired. Live wx construction is impractical for the full
menu tree in CI, so we verify the wiring via the source text and the declarative
manifest — the same strategy used by the A11Y-4 dialog-contract guard and the
menu-contract test.

Phase 5 (menus-as-data): the command table and the menu recirculation are both
derived from the wx-free :data:`quill.ui.main_frame_power_tools_menu.POWER_TOOLS_COMMANDS`
manifest, so these tests read the data directly rather than parsing a literal
table body.
"""

from __future__ import annotations

from pathlib import Path

import quill.ui.main_frame as main_frame_module
import quill.ui.main_frame_menu as main_frame_menu_module
import quill.ui.main_frame_power_tools_menu as eds_menu_module
from quill.ui.main_frame_power_tools_menu import POWER_TOOLS_COMMANDS, POWER_TOOLS_REGISTRAR

_SOURCE = (
    Path(main_frame_module.__file__).read_text(encoding="utf-8")
    + "\n"
    + Path(main_frame_menu_module.__file__).read_text(encoding="utf-8")
)
_MENU_SOURCE = Path(eds_menu_module.__file__).read_text(encoding="utf-8")

# Every power-tool command id that must be both registered and menu-wired.
_POWER_TOOLS_COMMAND_IDS = [
    "power.insert_special_character",
    "power.insert_date_time",
    "power.calculate_and_insert_date",
    "power.insert_file_content",
    "power.new_document_from_clipboard",
    "power.paste_html_as_markdown",
    "power.number_lines",
    "power.hard_wrap_lines",
    "power.delete_to_line_start",
    "power.delete_to_line_end",
    "power.delete_to_document_start",
    "power.delete_to_document_end",
    "power.delete_paragraph",
    "power.set_lines_first_not_second",
    "power.set_lines_common",
    "power.count_regex_matches",
    "power.extract_regex_matches",
    "power.speak_cursor_address",
    "power.speak_document_status",
    "power.speak_selection_length",
    "power.go_to_percent",
    "power.move_to_first_non_blank",
    "power.move_to_last_non_blank",
    "power.toggle_read_only_guard",
    "power.toggle_clipboard_collector",
    "power.collect_clipboard_now",
    "power.toggle_key_describer",
    "power.toggle_indent_announce",
    "power.infer_indent",
    "power.run_current_file",
    "power.run_target_at_cursor",
    "power.rename_current_file",
    "power.delete_current_file",
    # §4.22/§4.23 TextMonkey/EdSharp-parity additions
    "power.trim_blank_lines",
    "power.strip_html_tags",
    "power.decode_html_entities",
    "power.encode_html_entities",
    "power.encode_all_non_ascii",
    "power.show_non_ascii",
    "power.reencode_file",
    "power.shuffle_lines",
    "power.sort_lines_numeric",
    "power.sort_lines_by_length",
    "power.keep_unique_lines",
    "power.delete_lines_containing",
    "power.delete_lines_not_containing",
    # Copy Tray (dialog-level commands only; per-slot commands register directly
    # in MainFrame._build_commands to avoid duplicate menu entries)
    "edit.open_copy_tray",
    "edit.clear_all_tray_slots",
]


def test_command_table_lists_every_power_tools_command() -> None:
    manifest_ids = {command.id for command in POWER_TOOLS_COMMANDS}
    for command_id in _POWER_TOOLS_COMMAND_IDS:
        assert command_id in manifest_ids, (
            f"{command_id} missing from POWER_TOOLS_COMMANDS manifest"
        )


def test_commands_are_registered_and_keymap_assignable() -> None:
    assert "self._register_power_tools_commands()" in _SOURCE
    assert "PowerToolsMenuMixin" in _SOURCE.split("class MainFrame(")[1].split(")")[0]
    register = _MENU_SOURCE[_MENU_SOURCE.index("def _register_power_tools_commands") :][:400]
    # Registration goes through the standard command registry (palette + Keymap
    # Editor) and reads any user binding rather than shipping a default.
    assert "self.commands.register(" in register
    assert "self._binding_for(command_id)" in register


def test_every_command_is_menu_wired() -> None:
    # menus.md Phase 4 + 5: the power-tools monolith is dissolved and the menu
    # recirculation is data-driven. Each command carries a menu placement (group)
    # in the declarative manifest, and the generic group helper appends it.
    valid_groups = {
        "insert",
        "edit",
        "copy_tray",
        "file_ops",
        "format_line",
        "sort_filter",
        "trim_blank",
        "html_encoding",
        "navigate",
        "search",
        "accessibility",
        "power_tools",
    }
    for command in POWER_TOOLS_COMMANDS:
        assert command.placement.group in valid_groups, (
            f"{command.id} has unknown menu group {command.placement.group!r}"
        )
        assert command.placement.label, f"{command.id} has no menu label"
    # Every group is actually wired to a menu (the helpers / Power Tools submenu
    # delegate to the single data-driven primitive).
    assert "self._append_power_tools_group(" in _MENU_SOURCE
    # The cohesive remainder ships as Tools > Advanced (expanded inline build
    # per §10.3; the power_tools group is still appended via the data-driven helper).
    assert '_append_power_tools_group(power_tools_menu, "power_tools")' in _SOURCE
    assert 'tools_menu.AppendSubMenu(power_tools_menu, "&Advanced")' in _SOURCE
    for helper in (
        "_append_power_tools_insert_items",
        "_append_power_tools_edit_items",
        "_append_power_tools_file_ops_items",
        "_append_power_tools_format_line_items",
        "_append_power_tools_sort_filter_items",
        "_append_power_tools_trim_blank_items",
        "_append_power_tools_html_encoding_items",
        "_append_power_tools_navigate_items",
        "_append_power_tools_search_items",
        "_append_power_tools_accessibility_items",
        "_append_power_tools_copy_tray_items",
    ):
        assert f"self.{helper}(" in _SOURCE, f"{helper} is not called from the menu build"


def test_menu_items_are_bound() -> None:
    # The shared _power_tools_menu_item helper appends and binds every entry in one step.
    assert "self.frame.Bind(wx.EVT_MENU, lambda _e, run=handler: run(), id=item_id)" in _MENU_SOURCE


def test_read_only_guard_protects_edit_helpers() -> None:
    guard = (
        "if self._document_is_read_only():\n"
        '            self._set_status("Document is read-only")\n'
        "            return"
    )
    assert _SOURCE.count(guard) >= 3, "read-only guard missing from one of the _apply_* helpers"


def test_event_hooks_are_wired() -> None:
    char_hook = _SOURCE[_SOURCE.index("def _on_editor_char_hook") :][:200]
    assert "if self._maybe_describe_key(event):" in char_hook
    caret = _SOURCE[_SOURCE.index("def _on_editor_caret_activity") :][:200]
    assert "self._maybe_announce_indent()" in caret


def test_read_only_state_refreshes_on_tab_switch() -> None:
    activate = _SOURCE[_SOURCE.index("def _activate_tab") :][:1200]
    assert "self._refresh_read_only_state()" in activate


def test_read_only_state_refreshes_on_open() -> None:
    # Newly opened/selected tabs must re-apply a persisted read-only guard.
    create_tab = _SOURCE[_SOURCE.index("def _create_document_tab") :][:1700]
    assert "self._refresh_read_only_state()" in create_tab


def test_command_table_is_exactly_the_expected_ids_with_no_duplicates() -> None:
    ids = [command.id for command in POWER_TOOLS_COMMANDS]
    assert len(ids) == len(_POWER_TOOLS_COMMAND_IDS)
    assert len(set(ids)) == len(ids), "duplicate command id in manifest"
    assert set(ids) == set(_POWER_TOOLS_COMMAND_IDS)


def test_every_table_handler_exists_on_the_actions_mixin() -> None:
    from quill.ui.main_frame_copy_tray import CopyTrayMixin
    from quill.ui.main_frame_power_tools import PowerToolsActionsMixin
    from quill.ui.main_frame_power_tools_menu import _MIGRATED_HANDLERS

    for command in POWER_TOOLS_COMMANDS:
        if command.id in _MIGRATED_HANDLERS:
            # Migrated onto the contribution grammar: handler lives in a feature
            # module and runs through the Host facade, not on the mixin.
            assert callable(_MIGRATED_HANDLERS[command.id])
            continue
        name = command.handler_name
        # Copy Tray commands live on CopyTrayMixin, not PowerToolsActionsMixin.
        if command.placement.group == "copy_tray":
            assert hasattr(CopyTrayMixin, name), (
                f"missing handler {name} on CopyTrayMixin for {command.id}"
            )
            continue
        assert hasattr(PowerToolsActionsMixin, name), (
            f"missing handler {name} on PowerToolsActionsMixin for {command.id}"
        )


def test_line_transforms_are_migrated_off_the_mixin() -> None:
    # Wave 2 / §9: number_lines + hard_wrap_lines no longer live on the mixin;
    # they are resolved from the line_transforms feature module instead.
    from quill.ui.main_frame_power_tools import PowerToolsActionsMixin
    from quill.ui.main_frame_power_tools_menu import _MIGRATED_HANDLERS

    assert set(_MIGRATED_HANDLERS) >= {"power.number_lines", "power.hard_wrap_lines"}
    assert not hasattr(PowerToolsActionsMixin, "number_lines")
    assert not hasattr(PowerToolsActionsMixin, "hard_wrap_lines")


def test_menu_recirculation_preserves_shipped_group_order() -> None:
    # The data-driven group helper appends commands in declaration order; verify
    # each conventional menu's power-tools group is in the exact shipped sequence.
    expected = {
        "insert": [
            "power.insert_special_character",
            "power.insert_date_time",
            "power.calculate_and_insert_date",
            "power.insert_file_content",
        ],
        "edit": [
            "power.paste_html_as_markdown",
            "power.new_document_from_clipboard",
        ],
        "copy_tray": [
            "edit.open_copy_tray",
            "edit.clear_all_tray_slots",
        ],
        "format_line": [
            "power.number_lines",
            "power.hard_wrap_lines",
            "power.delete_paragraph",
            "power.delete_to_line_start",
            "power.delete_to_line_end",
            "power.delete_to_document_start",
            "power.delete_to_document_end",
        ],
        "sort_filter": [
            "power.shuffle_lines",
            "power.sort_lines_numeric",
            "power.sort_lines_by_length",
            "power.keep_unique_lines",
            "power.delete_lines_containing",
            "power.delete_lines_not_containing",
        ],
        "trim_blank": [
            "power.trim_blank_lines",
        ],
        "html_encoding": [
            "power.strip_html_tags",
            "power.decode_html_entities",
            "power.encode_html_entities",
            "power.encode_all_non_ascii",
            "power.show_non_ascii",
            "power.reencode_file",
        ],
        "navigate": [
            "power.go_to_percent",
            "power.move_to_first_non_blank",
            "power.move_to_last_non_blank",
            "power.run_target_at_cursor",
        ],
        "search": [
            "power.count_regex_matches",
            "power.extract_regex_matches",
            "power.set_lines_first_not_second",
            "power.set_lines_common",
        ],
        "power_tools": [
            "power.run_current_file",
            "power.toggle_read_only_guard",
            "power.toggle_clipboard_collector",
            "power.collect_clipboard_now",
            "power.toggle_key_describer",
            "power.toggle_indent_announce",
            "power.infer_indent",
        ],
    }
    for group, ids in expected.items():
        actual = [c.id for c in POWER_TOOLS_REGISTRAR.commands_in_group(group)]
        assert actual == ids, f"group {group} order drifted: {actual}"
