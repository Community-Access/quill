from __future__ import annotations

from pathlib import Path

_SOURCE = Path("quill/ui/main_frame.py").read_text(encoding="utf-8")


def test_ai_compare_and_dark_mode_commands_use_registered_keybindings() -> None:
    for command_id in (
        "tools.ai_spell_check",
        "tools.ai_spell_check_interactive",
        "tools.ai_grammar_style",
        "tools.ai_translate_selection",
        "tools.ai_thesaurus",
        "tools.ai_switch_engine",
        "tools.compare_next_difference",
        "tools.compare_previous_difference",
        "tools.compare_announce_difference",
        "view.toggle_dark_mode",
    ):
        assert f'self.commands.register(\n            "{command_id}"' in _SOURCE, (
            f"{command_id} should be registered in MainFrame"
        )
        assert f'self._binding_for("{command_id}")' in _SOURCE, (
            f"{command_id} should use the shared binding helper"
        )


def test_command_shortcuts_are_added_to_accelerator_menu_map() -> None:
    for command_id in (
        "tools.ai_spell_check",
        "tools.ai_spell_check_interactive",
        "tools.ai_grammar_style",
        "tools.ai_translate_selection",
        "tools.ai_thesaurus",
        "tools.ai_switch_engine",
        "tools.compare_next_difference",
        "tools.compare_previous_difference",
        "tools.compare_announce_difference",
    ):
        assert f'"{command_id}": self._id_' in _SOURCE, (
            f"{command_id} should be included in _command_to_menu_id_map"
        )
