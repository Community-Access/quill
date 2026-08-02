"""Insert > Insert Equation... (#1197, contributed by @salorajan).

The dialog itself is the shared accessible web form; what matters here is the
text QUILL builds from what the author typed, and the "edit the equation I
selected" convenience that strips delimiters on the way in.
"""

from __future__ import annotations

from pathlib import Path

import quill.ui.web_form as web_form
from quill.core.document import Document
from quill.ui.main_frame_equations import (
    EquationsMixin,
    equation_snippet,
    split_existing_equation,
)


class _Editor:
    def __init__(self, selection: str = "") -> None:
        self._selection = selection

    def GetStringSelection(self) -> str:
        return self._selection


class _Host(EquationsMixin):
    """The slice of MainFrame the equation command touches."""

    def __init__(self, selection: str = "") -> None:
        self.document = Document(path=Path("note.md"), text="")
        self.editor = _Editor(selection)
        self.frame = object()
        self._wx = object()
        self.status = ""
        self.inserted: list[str] = []

    def _set_status(self, message: str) -> None:
        self.status = message

    def _apply_insertion_result(self, result: object) -> None:
        self.inserted.append(result.inserted_text)  # type: ignore[attr-defined]


def _form(monkeypatch, returned: dict | None, captured: dict | None = None):
    def fake_show_web_form(_parent, _wx, **kwargs):
        if captured is not None:
            captured.update(kwargs)
        return returned

    monkeypatch.setattr(web_form, "show_web_form", fake_show_web_form)


# -- the snippet builder -------------------------------------------------------


def test_latex_is_wrapped_inline_or_block() -> None:
    assert equation_snippet("E = mc^2", "inline") == "$E = mc^2$"
    assert equation_snippet("E = mc^2", "block") == "$$\nE = mc^2\n$$"


def test_mathml_is_inserted_verbatim() -> None:
    # MathML is already a complete element; wrapping it in $ would break it.
    mathml = "<math><mi>x</mi></math>"
    assert equation_snippet(mathml, "inline") == mathml
    assert equation_snippet(mathml, "block") == mathml


def test_empty_input_produces_nothing() -> None:
    assert equation_snippet("   ", "inline") == ""


# -- editing an equation that is already in the document -----------------------


def test_a_selected_inline_equation_comes_back_without_its_delimiters() -> None:
    assert split_existing_equation("$E = mc^2$") == ("E = mc^2", "inline")


def test_a_selected_block_equation_preselects_block_mode() -> None:
    assert split_existing_equation("$$ E = mc^2 $$") == ("E = mc^2", "block")


def test_ordinary_selected_text_is_offered_as_is() -> None:
    assert split_existing_equation("just words") == ("just words", "inline")
    assert split_existing_equation("") == ("", "inline")


# -- the command ---------------------------------------------------------------


def test_insert_equation_inserts_inline_latex(monkeypatch) -> None:
    host = _Host()
    captured: dict = {}
    _form(monkeypatch, {"equation": "E = mc^2", "display_mode": "inline"}, captured)

    host.insert_equation()

    assert host.inserted == ["$E = mc^2$"]
    assert host.status == "Inserted equation"
    assert {field["name"] for field in captured["fields"]} == {"equation", "display_mode"}
    assert captured["save_label"] == "Insert"


def test_insert_equation_inserts_block_latex(monkeypatch) -> None:
    host = _Host()
    _form(monkeypatch, {"equation": "\\int_0^1 x dx", "display_mode": "block"})

    host.insert_equation()

    assert host.inserted == ["$$\n\\int_0^1 x dx\n$$"]


def test_insert_equation_prefills_the_selection_for_editing(monkeypatch) -> None:
    host = _Host(selection="$$E = mc^2$$")
    captured: dict = {}
    _form(monkeypatch, None, captured)

    host.insert_equation()

    equation_field = next(f for f in captured["fields"] if f["name"] == "equation")
    mode_field = next(f for f in captured["fields"] if f["name"] == "display_mode")
    assert equation_field["value"] == "E = mc^2"
    assert mode_field["value"] == "block"


def test_cancelling_inserts_nothing(monkeypatch) -> None:
    host = _Host()
    _form(monkeypatch, None)

    host.insert_equation()

    assert host.inserted == []
    assert host.status == "Insert equation cancelled"


def test_an_empty_equation_inserts_nothing(monkeypatch) -> None:
    host = _Host()
    _form(monkeypatch, {"equation": "   ", "display_mode": "inline"})

    host.insert_equation()

    assert host.inserted == []
    assert host.status == "Insert equation cancelled"


# -- wiring --------------------------------------------------------------------


def test_the_command_is_registered_with_a_chord_and_a_feature() -> None:
    from quill.core.feature_command_map import COMMAND_FEATURE_MAP
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.keymap_packs import _PACK_LABELS

    assert DEFAULT_KEYMAP["edit.insert_equation"] == "Ctrl+Shift+E"
    assert _PACK_LABELS["edit.insert_equation"] == "Insert Equation"
    assert COMMAND_FEATURE_MAP["edit.insert_equation"] == "core.format"


def test_main_frame_exposes_the_command() -> None:
    from quill.ui.main_frame import MainFrame

    assert hasattr(MainFrame, "insert_equation")
