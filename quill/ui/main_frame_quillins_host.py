"""Editor host-services adapter for Quillins (extracted from the menu mixin).

Holds :class:`_EditorHostServices`, which adapts :class:`MainFrame`'s editor to
the Quillins host ``HostServices`` protocol. It lives in its own module so
``main_frame_quillins.py`` stays within the GATE-11 module-size budget; the
runtime wiring and Manager UI remain in that mixin.

``core``/``io`` stay wx-free; like its sibling module this UI file owns all
``wx`` use, marshalling editor effects on the UI thread per the host services
contract.

Note for the no-silent-network gate (GATE-9): the ``fetch`` method below is the
single reviewed egress site for Quillins, registered in
``quill/tools/network_egress_audit.py`` as
``ui/main_frame_quillins_host.py::fetch``. It is reached only after the host's
capability + consent check passes.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path
from typing import Any


class _EditorHostServices:
    """Adapt :class:`MainFrame`'s editor to the host ``HostServices`` protocol.

    Editor writes go through the same ``wx.TextCtrl`` the user edits, so they
    participate in normal undo. Filesystem/network/clipboard methods are only
    ever reached after the host's capability + consent gate has approved them.
    """

    def __init__(self, frame: Any) -> None:
        self._frame = frame

    def get_text(self) -> str:
        return str(self._frame.editor.GetValue())

    def get_selection(self) -> str:
        return str(self._frame.editor.GetStringSelection())

    def get_cursor(self) -> dict[str, int]:
        editor = self._frame.editor
        position = int(editor.GetInsertionPoint())
        text = str(editor.GetValue())
        line = text.count("\n", 0, position) + 1
        column = position - (text.rfind("\n", 0, position) + 1) + 1
        percent = int((position / len(text)) * 100) if text else 0
        return {"line": line, "column": column, "percent": percent}

    def get_cursor_offset(self) -> int:
        return int(self._frame.editor.GetInsertionPoint())

    def get_selection_range(self) -> dict[str, int]:
        start, end = self._frame.editor.GetSelection()
        return {"start": int(start), "end": int(end)}

    def insert_text(self, text: str) -> None:
        self._frame.editor.WriteText(text)

    def replace_selection(self, text: str) -> None:
        editor = self._frame.editor
        start, end = editor.GetSelection()
        if start == end:
            editor.WriteText(text)
        else:
            editor.Replace(start, end, text)

    def set_text(self, text: str) -> None:
        """Replace the whole document as one undoable edit and sync the model."""

        self._frame._replace_document_text(text)
        self._frame.document.set_text(text)

    def set_cursor(self, offset: int) -> None:
        self._frame.editor.SetInsertionPoint(int(offset))

    def replace_range(self, start: int, end: int, text: str) -> None:
        self._frame.editor.Replace(int(start), int(end), text)

    def open_buffer(self, text: str, title: str) -> None:
        """Open ``text`` in a new editor tab, leaving the current one untouched."""

        self._frame._power_tools_open_text_in_new_buffer(text, title or "Opened Quillin result")

    def announce(self, message: str) -> None:
        self._frame._announce(message)

    def is_verbosity_speech_enabled(self) -> bool:
        settings = getattr(self._frame, "settings", None)
        if settings is None:
            return True
        return bool(getattr(settings, "verbosity_speech_enabled", True))

    def prompt(self, title: str, label: str, default: str) -> str | None:
        return self._frame._power_tools_prompt_single(title, label, default)

    def set_status(self, message: str) -> None:
        self._frame._set_status(message)

    def show_choices(self, title: str, items: list[str]) -> str | None:
        wx = self._frame._wx if hasattr(self._frame, "_wx") else None
        if wx is None:
            return None
        dialog = wx.SingleChoiceDialog(self._frame, title, title, items)
        try:
            if self._frame._show_modal_dialog(dialog, title) == wx.ID_OK:
                return dialog.GetStringSelection()
            return None
        finally:
            dialog.Destroy()

    def read_file(self, path: str) -> str:
        return Path(path).read_text(encoding="utf-8")

    def write_file(self, path: str, text: str) -> None:
        Path(path).write_text(text, encoding="utf-8")

    def fetch(self, url: str, method: str, body: str | None) -> dict[str, Any]:
        data = body.encode("utf-8") if body is not None else None
        request = urllib.request.Request(url, data=data, method=method)  # noqa: S310
        with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310
            payload = response.read().decode("utf-8", errors="replace")
            return {"status": int(getattr(response, "status", 200)), "body": payload}

    def get_clipboard(self) -> str:
        return str(self._frame._read_clipboard_text())

    def set_clipboard(self, text: str) -> None:
        self._frame._write_clipboard_text(text)
