"""BR-017/#240: Braille > Proofing commands persist to the sidecar and announce."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from quill.core.brf_sidecar import BRFSidecar, read_sidecar, write_sidecar
from quill.ui.main_frame_braille_phase3 import BrailleProofingCommandsMixin


class _Pos:
    page = 12
    page_count = 87


class _FakeMenu:
    def __init__(self) -> None:
        self.items: list[str] = []
        self.submenus: list[tuple[object, str]] = []

    def Append(self, _id: object, label: str) -> None:
        self.items.append(label)

    def AppendSubMenu(self, menu: object, label: str) -> None:
        self.submenus.append((menu, label))


class _FakeTextEntry:
    def __init__(self, value: str) -> None:
        self._value = value

    def __enter__(self) -> _FakeTextEntry:
        return self

    def __exit__(self, *_a: object) -> bool:
        return False

    def GetValue(self) -> str:
        return self._value


class _FakeWx:
    ID_OK = 5100

    def __init__(self, entry_value: str = "a note") -> None:
        self._entry_value = entry_value

    def Menu(self) -> _FakeMenu:
        return _FakeMenu()

    def NewIdRef(self) -> object:
        return object()

    def TextEntryDialog(self, *_a: object, **_k: object) -> _FakeTextEntry:
        return _FakeTextEntry(self._entry_value)


class _Host(BrailleProofingCommandsMixin):
    def __init__(self, path: Path | None, *, resolved: object = (object(), _Pos())) -> None:
        self.document = SimpleNamespace(path=path)
        self._resolved = resolved
        self._wx = _FakeWx()
        self.frame = object()
        self.said: list[str] = []
        self.not_braille = 0

    # stubs for MainFrame-provided helpers
    def _braille_position(self) -> object:
        return self._resolved

    def _say(self, message: str) -> None:
        self.said.append(message)

    def _announce_not_braille(self) -> None:
        self.not_braille += 1

    def _menu_label(self, label: str, _command_id: str) -> str:
        return label

    def _show_modal_dialog(self, _dialog: object, _title: str) -> int:
        return _FakeWx.ID_OK


def test_mark_proofed_persists_and_announces(tmp_path: Path) -> None:
    brf = tmp_path / "notes.brf"
    host = _Host(brf)
    host.mark_page_proofed()
    assert host.said[-1] == "Braille page 12 marked proofed."
    assert read_sidecar(brf).proofing.proofed_pages == [12]


def test_needs_review_then_clear(tmp_path: Path) -> None:
    brf = tmp_path / "notes.brf"
    host = _Host(brf)
    host.mark_page_needs_review()
    assert read_sidecar(brf).proofing.pages_needing_review == [12]
    host.clear_proofing_mark()
    sidecar = read_sidecar(brf)
    assert sidecar.proofing.pages_needing_review == []
    assert sidecar.proofing.proofed_pages == []


def test_progress_summary_speaks(tmp_path: Path) -> None:
    brf = tmp_path / "notes.brf"
    write_sidecar(brf, BRFSidecar())
    host = _Host(brf)
    host.mark_page_proofed()
    host.read_proofing_progress()
    summary = host.said[-1]
    assert summary.startswith("Progress summary. 87 braille pages. Current page 12.")
    assert "1 page proofed." in summary


def test_add_note_persists(tmp_path: Path) -> None:
    brf = tmp_path / "notes.brf"
    host = _Host(brf)
    host._wx = _FakeWx(entry_value="fix the running head")
    host.add_proofing_note()
    notes = read_sidecar(brf).notes
    assert notes[0].braille_page == 12
    assert notes[0].text == "fix the running head"


def test_not_a_braille_document_is_announced(tmp_path: Path) -> None:
    host = _Host(tmp_path / "notes.brf", resolved=None)
    host.mark_page_proofed()
    assert host.not_braille == 1
    assert host.said == []


def test_unsaved_document_hints_to_save() -> None:
    host = _Host(None)
    host.mark_page_proofed()
    assert host.said[-1] == "Save the braille file before tracking proofing."


def test_phase3_registers_proofing_and_validation_commands(tmp_path: Path) -> None:
    host = _Host(tmp_path / "notes.brf")
    ids = [cid for cid, _label, _handler in host._phase3_braille_commands()]
    assert ids == [
        "braille.mark_page_proofed",
        "braille.mark_page_needs_review",
        "braille.clear_proofing_mark",
        "braille.add_proofing_note",
        "braille.read_proofing_progress",
        "braille.list_proofed_pages",
        "braille.list_pages_needing_review",
        "braille.export_proofing_report",
        "braille.validate_layout",
        "braille.next_warning",
        "braille.previous_warning",
        "braille.warnings_summary",
    ]


def test_proofing_submenu_has_eight_items(tmp_path: Path) -> None:
    host = _Host(tmp_path / "notes.brf")
    host._mint_phase3_braille_ids()
    menu = _FakeMenu()
    host._append_proofing_submenu(menu)
    assert len(menu.submenus) == 1
    submenu, label = menu.submenus[0]
    assert label == "Proo&fing"
    assert len(submenu.items) == 8
