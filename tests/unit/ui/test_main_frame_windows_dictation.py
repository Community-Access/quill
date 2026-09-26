"""QUILL reaches Windows Dictation through hooks, never through its own commands."""

from __future__ import annotations

from quill.core.keymap import DEFAULT_KEYMAP
from quill.core.lite.commands import COMMANDS
from quill.core.lite.parity import COMMAND_EQUIVALENTS
from quill.ui.main_frame_windows_dictation import WindowsDictationCommandsMixin
from quill.ui.windows_dictation_commands import WindowsDictationMixin


def test_the_adapter_has_no_commands_of_its_own() -> None:
    """A second implementation is how the family rule gets broken quietly."""
    own = [name for name in vars(WindowsDictationCommandsMixin) if name.startswith("cmd_")]
    assert own == []
    assert "cmd_toggle_dictation" in vars(WindowsDictationMixin)
    assert "cmd_dictation_settings" in vars(WindowsDictationMixin)


def test_mainframe_has_the_shared_commands() -> None:
    from quill.ui.main_frame import MainFrame

    assert issubclass(MainFrame, WindowsDictationCommandsMixin)


def test_both_editors_put_the_two_commands_on_the_same_chords() -> None:
    lite_keys = {row[3]: row[2] for row in COMMANDS if row[3]}
    for handler in ("cmd_toggle_dictation", "cmd_dictation_settings"):
        quill_id = COMMAND_EQUIVALENTS[handler]
        assert DEFAULT_KEYMAP[quill_id] == lite_keys[handler], handler


def test_menu_ids_survive_a_rebuild_and_join_the_accelerator_map() -> None:
    class Base:
        def _command_to_menu_id_map(self) -> dict[str, int]:
            return {"file.new": 1}

    class Frame(WindowsDictationCommandsMixin, Base):
        pass

    frame = Frame()
    first = frame._windows_dictation_ids()
    assert frame._windows_dictation_ids() is first
    mapping = frame._command_to_menu_id_map()
    assert mapping["file.new"] == 1
    assert mapping["tools.windows_dictation_toggle"] == first[0]
    assert mapping["tools.windows_dictation_settings"] == first[1]
