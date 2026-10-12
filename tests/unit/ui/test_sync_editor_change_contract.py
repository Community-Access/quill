"""#1198: WordDocumentSurface calls its ``on_change`` callback with no
arguments, and MainFrame wires that callback to ``_sync_editor_change``. So
``_sync_editor_change`` must be callable with no positional arguments, or a
text change in the accessible Word view crashes with a TypeError."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from quill.ui.main_frame import MainFrame
from quill.ui.word_view import WordDocumentSurface


def test_sync_editor_change_is_callable_with_no_status() -> None:
    sig = inspect.signature(MainFrame._sync_editor_change)
    status = sig.parameters["status"]
    assert status.default is not inspect.Parameter.empty, (
        "_sync_editor_change must default `status` so it can serve as the "
        "zero-argument WordDocumentSurface on_change callback (#1198)."
    )


def test_word_surface_invokes_on_change_with_no_args() -> None:
    # Guards the other half of the contract: the surface really does call
    # on_change() with no arguments, so the default above is load-bearing.
    src = inspect.getsource(WordDocumentSurface._on_text_changed)
    assert "self._on_change()" in src


def test_every_word_surface_on_change_callback_takes_no_arguments() -> None:
    """Every ``WordDocumentSurface(..., on_change)`` in the tree, not just one.

    #1632 was #1198 again, from an older 0.9.0 install. The checks above pin
    ``_sync_editor_change`` by name; this one reads every construction site,
    resolves a ``self.<method>`` callback on MainFrame, and binds it with no
    arguments -- so a new wiring to a method with a required parameter fails
    here instead of on the first keystroke in the Word view.
    """
    repo = Path(__file__).resolve().parents[3]
    checked: list[str] = []
    problems: list[str] = []
    for path in sorted((repo / "quill").rglob("*.py")):
        source = path.read_text(encoding="utf-8", errors="replace")
        if "WordDocumentSurface(" not in source:
            continue
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name != "WordDocumentSurface":
                continue
            where = f"{path.relative_to(repo).as_posix()}:{node.lineno}"
            callback = node.args[3] if len(node.args) >= 4 else None
            for kw in node.keywords:
                if kw.arg == "on_change":
                    callback = kw.value
            if not (
                isinstance(callback, ast.Attribute)
                and isinstance(callback.value, ast.Name)
                and callback.value.id == "self"
            ):
                problems.append(f"{where}: on_change is not a self.<method> this test can resolve")
                continue
            method = getattr(MainFrame, callback.attr, None)
            if method is None:
                problems.append(f"{where}: MainFrame has no {callback.attr}")
                continue
            try:
                inspect.signature(method).bind(object())  # self only
            except TypeError as exc:
                problems.append(
                    f"{where}: {callback.attr}() cannot be called with no arguments: {exc}"
                )
            checked.append(where)

    assert checked, "found no WordDocumentSurface construction at all"
    assert not problems, "\n".join(problems)
