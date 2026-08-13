"""Every background callback that touches a widget checks the dialog first (#1353).

The reported crash -- ``RuntimeError: wrapped C/C++ object of type StaticText
has been deleted`` -- was the AI Hub's Ollama auto-probe landing after the user
closed the hub. The AI Hub is fixed; this is the sweep that says the same bug in
a *different* dialog cannot ship quietly. It is a source contract, because the
failure mode is structural: a worker thread posting a result back to a window
that is already gone.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import quill.ui as ui_package

_UI_ROOT = Path(str(ui_package.__file__)).parent

#: Callbacks reached by ``wx.CallAfter`` from a worker thread that must check
#: the dialog is still alive before touching a widget. Each entry is
#: ``module::function``; the guard may be ``dialog_alive(...)`` or a dialog's
#: own ``_alive()`` helper.
_GUARDED = [
    ("ai_hub_dialog.py", "_on_auto_probe_done"),
    ("ai_hub_dialog.py", "_on_hub_models_listed"),
    ("ai_hub_dialog.py", "_on_test_done"),
    ("ai_document_qa_dialog.py", "_on_answer_done"),
    ("ai_document_qa_dialog.py", "_on_answer_error"),
    ("ai_thesaurus_dialog.py", "_on_results"),
    ("ai_thesaurus_dialog.py", "_on_error"),
    ("ai_translation_dialog.py", "_on_done"),
    ("ai_translation_dialog.py", "_on_error"),
    ("ai_spell_check_dialog.py", "_on_paragraph_done"),
    ("ai_spell_check_dialog.py", "_begin_paragraph_ui"),
    ("ai_spell_check_dialog.py", "_set_status_safely"),
    ("ai_setup_wizard.py", "_on_verify_result"),
    ("ai_setup_wizard.py", "_on_model_pulled"),
    ("ai_setup_wizard.py", "_on_models_listed"),
    ("ai_setup_wizard.py", "_on_model_verified"),
    ("github_dialogs.py", "_on_repo_loaded"),
    ("github_dialogs.py", "_on_dir_loaded"),
    ("github_dialogs.py", "_on_load_error"),
]


def _function(module: str, name: str) -> tuple[ast.FunctionDef, str]:
    text = (_UI_ROOT / module).read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node, text
    raise AssertionError(f"{module}::{name} not found")


def _function_source(module: str, name: str) -> str:
    node, text = _function(module, name)
    return ast.get_source_segment(text, node) or ""


@pytest.mark.parametrize(("module", "name"), _GUARDED)
def test_background_callback_checks_the_dialog_is_alive(module: str, name: str) -> None:
    source = _function_source(module, name)
    assert "dialog_alive(" in source or "self._alive()" in source, (
        f"{module}::{name} runs after background work and touches widgets, but "
        "does not check the dialog still exists. Closing the dialog while the "
        "work is in flight raises 'wrapped C/C++ object ... has been deleted' "
        "(#1353). Add a dialog_alive(self.dialog) early return."
    )


@pytest.mark.parametrize(("module", "name"), _GUARDED)
def test_the_guard_is_the_first_thing_the_callback_does(module: str, name: str) -> None:
    """A guard that runs after the first widget touch is not a guard."""
    node, text = _function(module, name)
    statements = list(node.body)
    if statements and isinstance(statements[0], ast.Expr):
        first = statements[0].value
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            statements = statements[1:]  # docstring
    assert statements, f"{module}::{name} is empty"
    guard = ast.get_source_segment(text, statements[0]) or ""
    assert "dialog_alive(" in guard or "self._alive()" in guard, (
        f"{module}::{name} guards too late -- the liveness check must be the "
        "callback's first statement, before any widget access (#1353). Found: "
        f"{guard.splitlines()[0] if guard else '<nothing>'}"
    )
