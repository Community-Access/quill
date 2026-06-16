from __future__ import annotations

from pathlib import Path

import quill.ui.web_form as web_form
from quill.core.document import Document
from quill.ui.main_frame import MainFrame


class _Editor:
    def __init__(self, selection: str = "") -> None:
        self._selection = selection

    def GetStringSelection(self) -> str:
        return self._selection


def _build_frame(*, path: Path | None, selection: str = "") -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame.document = Document(path=path, text="")
    frame.editor = _Editor(selection)
    frame._status_message = "Ready"
    frame._wx = object()
    frame.frame = object()
    frame._set_status = lambda message: setattr(frame, "_status_message", message)
    return frame


def test_insert_equation_inline_latex(monkeypatch) -> None:
    frame = _build_frame(path=Path("note.md"), selection="E = mc^2")
    captured: dict[str, object] = {}

    def fake_show_web_form(parent, wx, **kwargs):  # noqa: ANN001, ANN003
        captured["kwargs"] = kwargs
        return {"equation": "E = mc^2", "display_mode": "inline"}

    monkeypatch.setattr(web_form, "show_web_form", fake_show_web_form)

    inserted: list[str] = []
    frame._apply_insertion_result = lambda result: inserted.append(result.inserted_text)

    frame.insert_equation()

    assert inserted == ["$E = mc^2$"]
    assert frame._status_message == "Inserted math equation"
    fields = {field["name"] for field in captured["kwargs"]["fields"]}
    assert fields == {"equation", "display_mode"}
    assert captured["kwargs"]["save_label"] == "Insert"


def test_insert_equation_block_latex(monkeypatch) -> None:
    frame = _build_frame(path=Path("note.md"))
    monkeypatch.setattr(
        web_form,
        "show_web_form",
        lambda *a, **k: {"equation": "\\frac{1}{2}", "display_mode": "block"},
    )

    inserted: list[str] = []
    frame._apply_insertion_result = lambda result: inserted.append(result.inserted_text)

    frame.insert_equation()

    assert inserted == ["\n$$\n\\frac{1}{2}\n$$\n"]
    assert frame._status_message == "Inserted math equation"


def test_insert_equation_mathml(monkeypatch) -> None:
    frame = _build_frame(path=Path("note.md"))
    mathml_eq = "<math><mfrac><mn>1</mn><mn>2</mn></mfrac></math>"
    monkeypatch.setattr(
        web_form,
        "show_web_form",
        lambda *a, **k: {"equation": mathml_eq, "display_mode": "inline"},
    )

    inserted: list[str] = []
    frame._apply_insertion_result = lambda result: inserted.append(result.inserted_text)

    frame.insert_equation()

    assert inserted == [mathml_eq]
    assert frame._status_message == "Inserted math equation"


def test_insert_equation_cancel(monkeypatch) -> None:
    frame = _build_frame(path=Path("note.md"))
    monkeypatch.setattr(web_form, "show_web_form", lambda *a, **k: None)

    called: list[object] = []
    frame._apply_insertion_result = lambda result: called.append(result)

    frame.insert_equation()

    assert called == []
    assert frame._status_message == "Insert equation cancelled"


def test_insert_equation_empty_value(monkeypatch) -> None:
    frame = _build_frame(path=Path("note.md"))
    monkeypatch.setattr(
        web_form,
        "show_web_form",
        lambda *a, **k: {"equation": "  ", "display_mode": "inline"},
    )

    called: list[object] = []
    frame._apply_insertion_result = lambda result: called.append(result)

    frame.insert_equation()

    assert called == []
    assert frame._status_message == "Insert equation cancelled"
