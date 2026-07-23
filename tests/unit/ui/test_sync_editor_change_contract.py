"""#1198: WordDocumentSurface calls its ``on_change`` callback with no
arguments, and MainFrame wires that callback to ``_sync_editor_change``. So
``_sync_editor_change`` must be callable with no positional arguments, or a
text change in the accessible Word view crashes with a TypeError."""

from __future__ import annotations

import inspect

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
