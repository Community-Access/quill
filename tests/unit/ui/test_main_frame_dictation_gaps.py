"""QUILL's answers to the 2026-10-05 dictation commands (the adapter's hooks),
run against stand-ins for the frame -- no window is built."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.copy_tray import CopyTray
from quill.core.keymap import DEFAULT_KEYMAP
from quill.core.snippets import Snippet
from quill.ui.main_frame_windows_dictation import _ROWS, WindowsDictationCommandsMixin


class _Frame(WindowsDictationCommandsMixin):
    def __init__(self, tmp_path: Any) -> None:
        self._copy_tray_instance = CopyTray(tmp_path)
        self._snippet_library = SimpleNamespace(
            snippets=[
                Snippet("1", "Sign off", ";so", "Thanks,\n${input:name}${cursor}"),
                Snippet("2", "Hidden", ";h", "x", enabled=False),
            ]
        )

    def _tray(self) -> CopyTray:
        return self._copy_tray_instance


def test_quill_reaches_its_snippets_by_name_with_blanks_named(tmp_path) -> None:
    frame = _Frame(tmp_path)
    assert frame._dictation_snippet_names() == ["Sign off"]
    assert frame._dictation_snippet_text("Sign off") == ("Thanks,\n[name]", 0)
    assert frame._dictation_snippet_text("Hidden") is None


def test_quill_reaches_its_copy_tray_slots(tmp_path) -> None:
    frame = _Frame(tmp_path)
    frame._tray().copy_to(2, "kept")
    assert frame._dictation_slot_text(2) == "kept"
    assert frame._dictation_slot_text(3) == ""
    assert frame._dictation_slot_text(13) is None


def test_every_live_dictation_row_is_bound_and_wired() -> None:
    ids = {command_id for command_id, _label, _title, _handler in _ROWS}
    assert ids == {c for c in DEFAULT_KEYMAP if c.startswith("tools.windows_dictation_")}
    for command_id, _label, _title, handler in _ROWS:
        assert DEFAULT_KEYMAP[command_id], command_id
        assert callable(getattr(WindowsDictationCommandsMixin, handler)), handler
    assert DEFAULT_KEYMAP["tools.windows_dictation_switch_language"] == "Ctrl+Shift+F11"
    assert DEFAULT_KEYMAP["file.forget_external_change_answers"] == "Ctrl+Shift+0"
