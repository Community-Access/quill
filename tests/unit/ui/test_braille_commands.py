"""#234: Braille Phase 1 commands are registered, mapped, and behave."""

from __future__ import annotations

from quill.core.commands import CommandRegistry
from quill.core.document import Document
from quill.core.features import feature_for_command
from quill.ui.main_frame import MainFrame

BRAILLE_COMMAND_IDS = [
    "braille.read_status",
    "braille.read_detailed_status",
    "braille.read_line_and_cell",
    "braille.read_braille_page",
    "braille.read_print_page",
    "braille.read_progress_summary",
    "braille.go_to_page",
    "braille.next_page",
    "braille.previous_page",
    "braille.insert_page_break",
    "braille.remove_page_break",
    "braille.normalize_line_endings",
    "braille.recalculate_page_map",
    "braille.save_as_clean",
]

HANDLER_METHODS = [
    "read_braille_status",
    "read_detailed_braille_status",
    "read_current_line_and_cell",
    "read_current_braille_page",
    "read_current_print_page",
    "read_progress_summary",
    "go_to_braille_page",
    "next_braille_page",
    "previous_braille_page",
    "insert_braille_page_break",
    "remove_braille_page_break",
]


class _Editor:
    def __init__(self, pos: int, text: str = "") -> None:
        self._pos = pos
        self._text = text

    def GetCurrentPos(self) -> int:
        return self._pos

    def GetValue(self) -> str:
        return self._text


def _registry_frame() -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame.commands = CommandRegistry()
    frame.keymap = {}
    frame._register_braille_commands()
    return frame


def _brf_frame(text: str, pos: int) -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame.document = Document(
        text=text,
        source_metadata={
            "source_kind": "brf",
            "brf_suffix": "brf",
            "brf_cell_width": 40,
            "brf_line_height": 25,
            "brf_non_ascii_offsets": [],
            "brf_had_bom": False,
            "brf_profile": "ueb_english",
        },
    )
    frame.editor = _Editor(pos, text)  # type: ignore[attr-defined]
    frame.settings = type("S", (), {"braille_status_verbosity": "normal"})()
    frame._announced = []  # type: ignore[attr-defined]
    frame._status = []  # type: ignore[attr-defined]
    frame._announce = lambda m: frame._announced.append(m)  # type: ignore[attr-defined]
    frame._set_status = lambda m: frame._status.append(m)  # type: ignore[attr-defined]
    return frame


def test_all_braille_commands_registered() -> None:
    frame = _registry_frame()
    for command_id in BRAILLE_COMMAND_IDS:
        assert frame.commands.get(command_id) is not None, command_id


def test_braille_commands_map_to_core_braille_feature() -> None:
    for command_id in BRAILLE_COMMAND_IDS:
        assert feature_for_command(command_id) == "core.braille", command_id


def test_handler_methods_exist() -> None:
    for name in HANDLER_METHODS:
        assert callable(getattr(MainFrame, name, None)), name


def test_read_braille_status_announces_position() -> None:
    frame = _brf_frame("hello world\x0cpage two text\x0c", 3)
    frame.read_braille_status()
    assert frame._announced
    assert "Braille page" in frame._announced[-1]


def test_read_status_on_non_braille_announces_not_braille() -> None:
    frame = MainFrame.__new__(MainFrame)
    frame.document = Document(text="plain", source_metadata={"source_kind": "text"})
    frame.editor = _Editor(0, "plain")  # type: ignore[attr-defined]
    frame._announced = []  # type: ignore[attr-defined]
    frame._status = []  # type: ignore[attr-defined]
    frame._announce = lambda m: frame._announced.append(m)  # type: ignore[attr-defined]
    frame._set_status = lambda m: frame._status.append(m)  # type: ignore[attr-defined]
    frame.read_braille_status()
    assert "not a braille document" in frame._announced[-1].lower()


def test_read_progress_summary_includes_percent() -> None:
    frame = _brf_frame("a\x0cb\x0cc\x0c", 0)
    frame.read_progress_summary()
    assert "percent" in frame._announced[-1]
