"""Regression tests for ``DevToolsMixin``'s ``ConsoleHost`` editor methods.

Two methods previously called attributes that have never existed on
``MainFrame``:

- ``console_get_document_name`` called ``self._active_document_path()``
  (the real accessor is the ``self.document.path`` attribute).
- ``console_set_editor_text`` / ``console_replace_selection`` called
  ``self._mark_document_modified()``, which called ``self._set_modified(True)``.
  Both editor calls already fire ``wx.EVT_TEXT`` -> ``_sync_editor_change``,
  which marks the document modified on its own, so the dead call was simply
  removed rather than rewired.

Both bugs were silently swallowed by a broad ``except Exception: pass`` /
``return ""``, so they never crashed -- they just made the Developer
Console's document-name lookup always return "" and made the now-removed
modified-marking call a silent no-op.
"""

from __future__ import annotations

from pathlib import Path

from quill.ui.main_frame_devtools import DevToolsMixin


class _FakeDocument:
    def __init__(self, path: Path | None) -> None:
        self.path = path


class _FakeEditor:
    def __init__(self, text: str = "") -> None:
        self._text = text

    def GetValue(self) -> str:  # noqa: N802
        return self._text

    def SetValue(self, text: str) -> None:  # noqa: N802
        self._text = text

    def GetStringSelection(self) -> str:  # noqa: N802
        return ""

    def WriteText(self, text: str) -> None:  # noqa: N802
        self._text += text


class _FakeFrame(DevToolsMixin):
    def __init__(self, *, path: Path | None) -> None:
        self.editor = _FakeEditor()
        self.document = _FakeDocument(path)


def test_console_get_document_name_returns_basename() -> None:
    frame = _FakeFrame(path=Path("/tmp/notes.md"))

    assert frame.console_get_document_name() == "notes.md"


def test_console_get_document_name_empty_for_unsaved_document() -> None:
    frame = _FakeFrame(path=None)

    assert frame.console_get_document_name() == ""


def test_console_set_editor_text_does_not_raise() -> None:
    frame = _FakeFrame(path=None)

    frame.console_set_editor_text("hello")

    assert frame.editor.GetValue() == "hello"


def test_console_replace_selection_does_not_raise() -> None:
    frame = _FakeFrame(path=None)

    frame.console_replace_selection("world")

    assert frame.editor.GetValue() == "world"
