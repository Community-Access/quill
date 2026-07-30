"""App-neutral host-services adapter for Quillins in the companion apps.

:class:`_AppHostServices` adapts an :class:`~quill.ui.app_shell.AppShellFrame`
(Quill Radio, Quill Cast, ...) to the Quillins ``HostServices`` protocol -- but
only the *app-neutral* half of it. The editor-only methods (``editor.read``/
``editor.write`` and friends) have no document to act on in a companion app, so
they raise :class:`~quill.core.quillins.model.CapabilityError`. In practice they
are never reached: manifest validation forbids an editor-only capability on a
non-editor ``target``, so the host's capability gate refuses the call before it
ever arrives here -- these raises are the defensive backstop.

The app-neutral surface is: ``ui.announce``/``ui.prompt``/``ui.status``/
``ui.choices``, clipboard read/write, and *contained* filesystem read/write
(the host confines every path to the extension directory before this runs).
``net`` (fetch) is intentionally not wired in this foundation -- it would add a
new outbound egress site to review -- so it raises for now; see the report.

``core``/``io`` stay wx-free; this UI module owns all ``wx`` use, marshalling
effects on the UI thread per the host-services contract.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.quillins.model import CapabilityError


class _AppHostServices:
    """Adapt an ``AppShellFrame`` to the app-neutral ``HostServices`` surface."""

    def __init__(self, frame: Any) -> None:
        self._frame = frame

    # -- editor-only surface (absent in a companion app) ---------------------
    def _no_editor(self, capability: str) -> CapabilityError:
        return CapabilityError(capability, detail="no editor in this app")

    def get_text(self) -> str:
        raise self._no_editor("editor.read")

    def get_selection(self) -> str:
        raise self._no_editor("editor.read")

    def get_cursor(self) -> dict[str, int]:
        raise self._no_editor("editor.read")

    def get_cursor_offset(self) -> int:
        raise self._no_editor("editor.read")

    def get_selection_range(self) -> dict[str, int]:
        raise self._no_editor("editor.read")

    def insert_text(self, text: str) -> None:
        raise self._no_editor("editor.write")

    def replace_selection(self, text: str) -> None:
        raise self._no_editor("editor.write")

    def set_text(self, text: str) -> None:
        raise self._no_editor("editor.write")

    def open_buffer(self, text: str, title: str) -> None:
        raise self._no_editor("editor.write")

    def set_cursor(self, offset: int) -> None:
        raise self._no_editor("editor.write")

    def replace_range(self, start: int, end: int, text: str) -> None:
        raise self._no_editor("editor.write")

    # -- app-neutral ui surface ----------------------------------------------
    def announce(self, message: str) -> None:
        self._frame._announce(message)

    def is_verbosity_speech_enabled(self) -> bool:
        settings = getattr(self._frame, "settings", None)
        if settings is None:
            return True
        return bool(getattr(settings, "verbosity_speech_enabled", True))

    def prompt(self, title: str, label: str, default: str) -> str | None:
        wx = getattr(self._frame, "_wx", None)
        if wx is None:
            return None
        dialog = wx.TextEntryDialog(self._frame.frame, label or title, title, default)
        try:
            if self._frame._show_modal_dialog(dialog, title) == wx.ID_OK:
                return str(dialog.GetValue())
            return None
        finally:
            dialog.Destroy()

    def set_status(self, message: str) -> None:
        self._frame._set_status(message)

    def show_choices(self, title: str, items: list[str]) -> str | None:
        wx = getattr(self._frame, "_wx", None)
        if wx is None:
            return None
        dialog = wx.SingleChoiceDialog(self._frame.frame, title, title, items)
        try:
            if self._frame._show_modal_dialog(dialog, title) == wx.ID_OK:
                return str(dialog.GetStringSelection())
            return None
        finally:
            dialog.Destroy()

    # -- contained filesystem (path confined by the host before this runs) ---
    def read_file(self, path: str) -> str:
        return Path(path).read_text(encoding="utf-8")

    def write_file(self, path: str, text: str) -> None:
        Path(path).write_text(text, encoding="utf-8")

    # -- net (deferred in this foundation) -----------------------------------
    def fetch(self, url: str, method: str, body: str | None) -> dict[str, Any]:
        raise CapabilityError("net", detail="network access for app Quillins is not available yet")

    # -- clipboard -----------------------------------------------------------
    def get_clipboard(self) -> str:
        wx = getattr(self._frame, "_wx", None)
        clipboard = getattr(wx, "TheClipboard", None) if wx is not None else None
        if clipboard is None or not clipboard.Open():
            return ""
        try:
            data = wx.TextDataObject()
            if clipboard.GetData(data):
                return str(data.GetText())
            return ""
        finally:
            clipboard.Close()

    def set_clipboard(self, text: str) -> None:
        wx = getattr(self._frame, "_wx", None)
        clipboard = getattr(wx, "TheClipboard", None) if wx is not None else None
        if clipboard is None or not clipboard.Open():
            return
        try:
            clipboard.SetData(wx.TextDataObject(text))
        finally:
            clipboard.Close()
