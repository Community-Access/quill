"""#245 (BR-022): Translation submenu gating and command behavior."""

from __future__ import annotations

import quill.core.braille_pack as pack
import quill.core.braille_worker_client as worker
from quill.ui.main_frame import MainFrame


def _frame() -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame._safe_mode = False
    frame._announced = []  # type: ignore[attr-defined]
    frame._status = []  # type: ignore[attr-defined]
    frame._announce = lambda m: frame._announced.append(m)  # type: ignore[attr-defined]
    frame._set_status = lambda m: frame._status.append(m)  # type: ignore[attr-defined]
    return frame


class _Editor:
    def __init__(self, text: str = "hello", selection: str = "") -> None:
        self._text = text
        self._selection = selection

    def GetValue(self) -> str:
        return self._text

    def GetStringSelection(self) -> str:
        return self._selection


def test_translation_items_hidden_when_pack_absent(monkeypatch) -> None:
    monkeypatch.setattr(pack, "is_braille_pack_installed", lambda: False)
    assert _frame()._braille_translation_items() == []


def test_translation_items_shown_when_pack_present(monkeypatch) -> None:
    monkeypatch.setattr(pack, "is_braille_pack_installed", lambda: True)
    items = _frame()._braille_translation_items()
    assert [command_id for _label, command_id in items] == [
        "braille.translate_ueb_g2",
        "braille.translate_ueb_g1",
        "braille.translate_selection",
        "braille.back_translate",
        "braille.translate_standard_g2",
        "braille.translate_standard_g1",
    ]


def test_translation_items_hidden_in_safe_mode(monkeypatch) -> None:
    monkeypatch.setattr(pack, "is_braille_pack_installed", lambda: True)
    frame = _frame()
    frame._safe_mode = True
    assert frame._braille_translation_items() == []


def test_translate_opens_document_and_announces(monkeypatch) -> None:
    monkeypatch.setattr(worker, "forward_translate", lambda *_a, **_k: ",hello _w\x0c")
    frame = _frame()
    frame.editor = _Editor("hello world")  # type: ignore[attr-defined]
    opened: list[str] = []
    frame._create_document_tab = lambda doc, select=True: opened.append(doc.text)  # type: ignore[attr-defined]

    frame.translate_to_ueb_g2()

    assert opened == [",hello _w\x0c"]
    assert "Translated to UEB G2" in frame._announced[-1]


def test_back_translate_labels_draft(monkeypatch) -> None:
    monkeypatch.setattr(worker, "back_translate", lambda *_a, **_k: "hello world")
    frame = _frame()
    frame.editor = _Editor(",hello _w")  # type: ignore[attr-defined]
    frame._create_document_tab = lambda doc, select=True: None  # type: ignore[attr-defined]

    frame.back_translate_ueb()

    assert "draft" in frame._announced[-1].lower()


def test_translation_failure_is_announced(monkeypatch) -> None:
    def _boom(*_a, **_k):
        raise worker.WorkerError("liblouis is not installed")

    monkeypatch.setattr(worker, "forward_translate", _boom)
    frame = _frame()
    frame.editor = _Editor("hello")  # type: ignore[attr-defined]
    opened: list[str] = []
    frame._create_document_tab = lambda doc, select=True: opened.append(doc.text)  # type: ignore[attr-defined]

    frame.translate_to_ueb_g2()

    assert opened == []  # no empty document on failure
    assert "Translation failed" in frame._announced[-1]
