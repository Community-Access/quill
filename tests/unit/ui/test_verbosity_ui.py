"""Source-contract tests for the verbosity UI (sub-PR 1.4).

These verify the A11Y-4 dialog contract and dialog-inventory registration for the
verbosity UI surfaces **without constructing wx widgets** (no wx dependency
here), matching the house pattern for UI dialog tests. The behavior these
dialogs drive is already covered by the pure-core verbosity tests.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_UI = Path(__file__).resolve().parents[3] / "quill" / "ui"
_INVENTORY = Path(__file__).parent / "fixtures" / "dialog_inventory.json"


def _inventory() -> dict[str, str]:
    return json.loads(_INVENTORY.read_text(encoding="utf-8"))


def _source(module: str) -> str:
    return (_UI / module).read_text(encoding="utf-8")


# (module, dialog class, core module it must wire to)
_DIALOGS = [
    ("verbosity_token_editor.py", "VerbosityTokenEditorDialog", "verbosity.parser"),
    ("verbosity_data_order.py", "VerbosityDataOrderDialog", "verbosity.data_order"),
    ("verbosity_chord_editor.py", "VerbosityChordEditorDialog", "verbosity.registry"),
    ("verbosity_library.py", "VerbosityLibraryDialog", "verbosity.library"),
    ("verbosity_qvp_install.py", "VerbosityQvpInstallDialog", "verbosity.qvp"),
    ("verbosity_history.py", "VerbosityHistoryDialog", "verbosity.history"),
    ("verbosity_preview_lab.py", "VerbosityPreviewLabDialog", "verbosity.preview"),
    ("verbosity_safe_mode.py", "VerbositySafeModeDialog", ""),
    ("verbosity_import_export.py", "VerbosityImportExportDialog", "verbosity.import_export"),
]


@pytest.mark.parametrize(("module", "cls", "_core"), _DIALOGS)
def test_dialog_registered_in_inventory(module: str, cls: str, _core: str) -> None:
    key = f"quill/ui/{module}::{cls}.__init__::wx.Dialog"
    inv = _inventory()
    assert key in inv, f"Dialog surface not registered: {key}"
    assert inv[key] == "hardened_custom"


@pytest.mark.parametrize(("module", "cls", "_core"), _DIALOGS)
def test_dialog_applies_modal_ids(module: str, cls: str, _core: str) -> None:
    assert "apply_modal_ids" in _source(module), f"{cls} must call apply_modal_ids"


@pytest.mark.parametrize(("module", "cls", "_core"), _DIALOGS)
def test_dialog_exposes_show_and_close(module: str, cls: str, _core: str) -> None:
    source = _source(module)
    assert "def show(" in source, f"{cls} must expose show()"
    assert "def close(" in source, f"{cls} must expose close()"


@pytest.mark.parametrize(("module", "cls", "_core"), _DIALOGS)
def test_dialog_destroys_itself(module: str, cls: str, _core: str) -> None:
    # A raw wx.Dialog must be Destroy()ed somewhere in the module (banned-pattern gate).
    assert ".Destroy()" in _source(module), f"{cls} must Destroy its dialog"


@pytest.mark.parametrize(("module", "cls", "core"), _DIALOGS)
def test_dialog_wires_to_core(module: str, cls: str, core: str) -> None:
    if not core:
        return
    assert f"quill.core.{core}" in _source(module), f"{cls} should wire to quill.core.{core}"


@pytest.mark.parametrize(("module", "cls", "_core"), _DIALOGS)
def test_dialog_no_align_right_button(module: str, cls: str, _core: str) -> None:
    # A11Y-4: button sizers use wx.EXPAND / stretch spacers, never wx.ALIGN_RIGHT.
    assert "wx.ALIGN_RIGHT" not in _source(module)


# --- the embeddable preferences panel ---


def test_prefs_panel_registered_or_panel() -> None:
    # The prefs surface is a wx.Panel (embedded in Preferences), not a modal dialog,
    # so it is intentionally not in the dialog inventory.
    source = _source("verbosity_prefs.py")
    assert "class VerbosityPrefsPanel(wx.Panel)" in source


def test_prefs_panel_initial_focus_on_filter() -> None:
    source = _source("verbosity_prefs.py")
    assert "self._filter.SetFocus()" in source


def test_prefs_panel_has_named_status_line() -> None:
    source = _source("verbosity_prefs.py")
    # A human-readable accessible name (screen readers speak it verbatim), not a
    # snake_case identifier.
    assert 'SetName("Verbosity status")' in source


def test_prefs_panel_visual_floor_named() -> None:
    source = _source("verbosity_prefs.py")
    assert "VISUAL_ALWAYS_ON_NAME" in source


def test_prefs_panel_does_not_disable_focus() -> None:
    # A11Y-TAB-1: must not override AcceptsFocus to return False on a panel.
    source = _source("verbosity_prefs.py")
    assert "def AcceptsFocus" not in source


def test_token_editor_has_radiobox_view_switch() -> None:
    # §5 decision 6: Simple/Advanced switch is a RadioBox, not a Notebook.
    source = _source("verbosity_token_editor.py")
    assert "wx.RadioBox" in source
    assert "wx.Notebook" not in source


def test_token_editor_has_char_hook() -> None:
    assert "EVT_CHAR_HOOK" in _source("verbosity_token_editor.py")


def test_no_checklistbox_anywhere() -> None:
    # A11Y-SR-1 (#161): wx.CheckListBox is banned in quill/ui.
    for module, _cls, _core in _DIALOGS:
        assert "wx.CheckListBox" not in _source(module)
    assert "wx.CheckListBox" not in _source("verbosity_prefs.py")
