"""BR-019/#242: Braille > Validation commands drive the validator and announce."""

from __future__ import annotations

from types import SimpleNamespace

from quill.ui.main_frame_braille_phase3 import BrailleProofingCommandsMixin


class _Editor:
    def __init__(self, text: str) -> None:
        self._text = text
        self.focused = False

    def GetValue(self) -> str:
        return self._text

    def SetFocus(self) -> None:
        self.focused = True


class _Ring:
    def __init__(self) -> None:
        self.records: list[int] = []

    def record(self, offset: int) -> None:
        self.records.append(offset)


class _SingleChoice:
    def __init__(self, selection: int) -> None:
        self._selection = selection

    def __enter__(self) -> _SingleChoice:
        return self

    def __exit__(self, *_a: object) -> bool:
        return False

    def GetSelection(self) -> int:
        return self._selection


class _Wx:
    ID_OK = 5100

    def __init__(self, selection: int = 0) -> None:
        self._selection = selection

    def SingleChoiceDialog(self, *_a: object, **_k: object) -> _SingleChoice:
        return _SingleChoice(self._selection)


class _Host(BrailleProofingCommandsMixin):
    def __init__(self, text: str, *, resolver: object = object(), selection: int = 0) -> None:
        self.editor = _Editor(text)
        self._resolver = resolver
        self.settings = SimpleNamespace(
            braille_cells_per_line=40, braille_lines_per_page=25, braille_use_form_feeds=True
        )
        self._wx = _Wx(selection)
        self.frame = object()
        self._location_ring = _Ring()
        self.said: list[str] = []
        self.not_braille = 0
        self.moved: list[int] = []

    def _active_brf_resolver(self) -> object:
        return self._resolver

    def _say(self, message: str) -> None:
        self.said.append(message)

    def _announce_not_braille(self) -> None:
        self.not_braille += 1

    def _move_point(self, offset: int) -> None:
        self.moved.append(offset)

    def _record_location_before_jump(self) -> None:
        pass

    def _show_modal_dialog(self, _dialog: object, _title: str) -> int:
        return _Wx.ID_OK


def _clean_brf() -> str:
    page = "\n".join(["ab"] * 6)
    return page + "\f" + page + "\n"


def test_validate_clean_file_announces_no_warnings() -> None:
    host = _Host(_clean_brf())
    host.validate_braille_file()
    assert host.said[-1] == "No braille layout warnings found."
    assert host._brf_validation_warnings == []


def test_validate_with_warning_opens_list_and_jumps() -> None:
    host = _Host("x" * 41 + "\n" + "\n".join(["ab"] * 6))
    host.validate_braille_file()
    assert host._brf_validation_warnings  # at least the long-line warning
    assert host.moved == [0]  # jumped to the first warning's offset
    assert host.said[-1].startswith("Warning 1 of ")


def test_validate_non_braille_announces() -> None:
    host = _Host("anything", resolver=None)
    host.validate_braille_file()
    assert host.not_braille == 1


def test_next_and_previous_navigation() -> None:
    host = _Host(_clean_brf())
    host._brf_validation_warnings = [
        SimpleNamespace(offset=10, line=1, page=1, message="first"),
        SimpleNamespace(offset=20, line=2, page=1, message="second"),
    ]
    host._brf_validation_index = -1
    host.next_validation_warning()
    assert host.moved[-1] == 10
    assert host.said[-1] == "Warning 1 of 2: first"
    host.next_validation_warning()
    assert host.said[-1] == "Warning 2 of 2: second"
    host.next_validation_warning()
    assert host.said[-1] == "No next warning."
    host.previous_validation_warning()
    assert host.said[-1] == "Warning 1 of 2: first"


def test_navigation_without_validation_hints() -> None:
    host = _Host(_clean_brf())
    host.next_validation_warning()
    assert host.said[-1] == "No warnings. Run Validate BRF Layout first."


def test_summary_before_and_after_validation() -> None:
    host = _Host("x" * 41)
    host.read_validation_summary()
    assert host.said[-1] == "No validation run yet. Run Validate BRF Layout first."
    host.validate_braille_file()  # selection 0 -> jumps; warnings stored
    host.read_validation_summary()
    assert host.said[-1].startswith("1 layout warning. Top categories: line too long (1)")
