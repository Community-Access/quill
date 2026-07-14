"""Scintilla editor surface -- the "Notepad++ experiment" (Experimental tab).

Hosts ``wx.stc.StyledTextCtrl`` (Win32 window class "Scintilla", the engine
behind Notepad++) as an experimental editor surface. Scintilla is the only
alternative surface that natively provides multi-level undo AND redo while
remaining a real windowed control that screen readers can address; NVDA
supports it well (it drives Notepad++ daily), JAWS support is partial. The
full risk analysis lives in docs/planning/editor-surface-experiments.md
("stc" section).

StyledTextCtrl implements the wx.TextCtrl-compatible API QUILL relies on
(value, caret, selection tuples, Replace/GetRange, PositionToXY, undo/redo),
verified by probe. Four contract gaps remain, all shimmed here:

* ``wx.EVT_TEXT`` never fires natively -- only ``EVT_STC_CHANGE`` -- so dirty
  tracking, word count, and the Reveal Codes sync would go dead. The wrapper
  forwards each change as a ``wxEVT_TEXT`` command event.
* ``ChangeValue`` fires change notifications and leaves the buffer reported
  as modified; QUILL loads documents through ``ChangeValue`` and must not see
  a fresh document as dirty. The wrapper suppresses forwarding and sets the
  Scintilla save point (and empties the undo buffer, matching a load).
* ``SetInsertionPoint`` moves the caret but leaves the selection anchor
  behind, so a later ``WriteText`` replaces the dragged selection. The
  wrapper uses ``GotoPos``, which collapses the selection like wx.TextCtrl.
* Line endings pass through unconverted; QUILL's buffer is LF-only. The
  wrapper pins ``STC_EOL_LF``, converts on load, and converts pasted text.

JAWS compatibility: none, and not for lack of trying. Three bridging
attempts (system caret mirror; classic WM_GETTEXT/EM_* window-proc answers;
those plus the EM_POSFROMCHAR/EM_CHARFROMPOS geometry set) all failed live
JAWS testing and were rolled back on 2026-07-03 -- full post-mortem in
docs/planning/editor-surface-experiments.md. NVDA reads and tracks this
surface well through the native SCI_* message support. Treat as NVDA-only.

Mirrors the rtf/win32 defensive pattern: on any failure the factory returns
a stock ``wx.TextCtrl`` so selecting this surface can never brick the editor.
"""

from __future__ import annotations

import sys
from typing import Any

try:
    import wx
    import wx.stc as _stc

    _SCINTILLA = True
except Exception:  # noqa: BLE001 - wx.stc absent/broken: surface unavailable
    _SCINTILLA = False


if _SCINTILLA:

    class StcEditorSurface(_stc.StyledTextCtrl):  # type: ignore[misc]
        """StyledTextCtrl configured to honor the wx.TextCtrl editor contract."""

        def __init__(self, parent: Any, style: int = 0) -> None:
            super().__init__(parent, style=style)
            self._suppress_text_events = 0
            # LF-only buffer so caret offsets match GetValue() string indices,
            # including for text pasted with CRLF endings.
            self.SetEOLMode(_stc.STC_EOL_LF)
            self.SetPasteConvertEndings(True)
            # A clean text surface: no line-number/fold/symbol margins.
            for margin in range(5):
                self.SetMarginWidth(margin, 0)
            # Match the default wx.TextCtrl word wrap.
            self.SetWrapMode(_stc.STC_WRAP_WORD)
            self.Bind(_stc.EVT_STC_CHANGE, self._forward_text_event)

        def surface_kind(self) -> str:
            return "stc"

        def accessibility_diagnostic_summary(self) -> str:
            """Return a document-content-free snapshot of the STC accessibility surface."""
            lines = [
                "Editor surface diagnostics",
                "Surface: stc",
                f"Platform: {sys.platform}",
                f"Handle: {self._safe_int(self.GetHandle())}",
                f"STC text length: {self._safe_call_int(self.GetTextLength)}",
                f"STC line count: {self._safe_call_int(self.GetLineCount)}",
                f"STC current position: {self._safe_call_int(self.GetCurrentPos)}",
                f"STC current line: {self._safe_call_int(self.GetCurrentLine)}",
                f"STC current column: {self._safe_call_int(self.GetColumn, self.GetCurrentPos())}",
                f"STC selection: {self._safe_selection()}",
            ]
            lines.extend(self._win32_accessibility_diagnostics())
            lines.append("Document content included: no")
            return "\n".join(lines)

        @staticmethod
        def _safe_int(value: Any) -> int | str:
            try:
                return int(value)
            except Exception:  # noqa: BLE001 - diagnostics must not raise
                return "unavailable"

        @classmethod
        def _safe_call_int(cls, func: Any, *args: Any) -> int | str:
            try:
                return cls._safe_int(func(*args))
            except Exception:  # noqa: BLE001 - diagnostics must not raise
                return "unavailable"

        def _safe_selection(self) -> str:
            try:
                start, end = self.GetSelection()
                return f"{int(start)}..{int(end)}"
            except Exception:  # noqa: BLE001 - diagnostics must not raise
                return "unavailable"

        def _win32_accessibility_diagnostics(self) -> list[str]:
            if sys.platform != "win32":
                return ["Win32 classic text diagnostics: unavailable on this platform"]
            try:
                import ctypes
                from ctypes import wintypes

                user32 = ctypes.WinDLL("user32", use_last_error=True)
                hwnd = wintypes.HWND(int(self.GetHandle()))
                class_name = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, class_name, len(class_name))
                wm_gettextlength = 0x000E
                em_getsel = 0x00B0
                em_exgetsel = 0x0434

                lparam = getattr(wintypes, "LPARAM", ctypes.c_ssize_t)
                user32.SendMessageW.argtypes = [
                    wintypes.HWND,
                    wintypes.UINT,
                    wintypes.WPARAM,
                    lparam,
                ]
                user32.SendMessageW.restype = lparam

                class _CharRange(ctypes.Structure):
                    _fields_ = [("cpMin", wintypes.LONG), ("cpMax", wintypes.LONG)]

                packed_selection = int(user32.SendMessageW(hwnd, em_getsel, 0, 0))
                extended_selection = _CharRange()
                user32.SendMessageW(hwnd, em_exgetsel, 0, ctypes.addressof(extended_selection))
                focus_hwnd = int(user32.GetFocus() or 0)
                handle = int(hwnd.value or 0)
                text_length = int(user32.SendMessageW(hwnd, wm_gettextlength, 0, 0))
                extended_start = int(extended_selection.cpMin)
                extended_end = int(extended_selection.cpMax)
                return [
                    f"Win32 class name: {class_name.value or 'unavailable'}",
                    f"Win32 focused: {focus_hwnd == handle}",
                    f"Win32 WM_GETTEXTLENGTH: {text_length}",
                    f"Win32 EM_GETSEL packed: {packed_selection}",
                    f"Win32 EM_EXGETSEL: {extended_start}..{extended_end}",
                ]
            except Exception as error:  # noqa: BLE001 - diagnostics must not raise
                return [f"Win32 classic text diagnostics failed: {error.__class__.__name__}"]

        def _forward_text_event(self, event: Any) -> None:
            event.Skip()
            if self._suppress_text_events:
                return
            text_event = wx.CommandEvent(wx.wxEVT_TEXT, self.GetId())
            text_event.SetEventObject(self)
            wx.PostEvent(self.GetEventHandler(), text_event)

        def _release_text_events(self) -> None:
            if self._suppress_text_events:
                self._suppress_text_events -= 1

        def ChangeValue(self, value: str) -> None:  # noqa: N802 - wx API
            self._suppress_text_events += 1
            try:
                self.SetText(value or "")
                self.ConvertEOLs(_stc.STC_EOL_LF)
                self.EmptyUndoBuffer()
                self.SetSavePoint()
            finally:
                # Change notifications may arrive queued as well as inline;
                # lift the suppression only after the queue has drained.
                wx.CallAfter(self._release_text_events)

        def SetValue(self, value: str) -> None:  # noqa: N802 - wx API
            # Same normalization as ChangeValue, but the change event fires
            # (wx.TextCtrl.SetValue semantics).
            self.SetText(value or "")
            self.ConvertEOLs(_stc.STC_EOL_LF)
            self.EmptyUndoBuffer()
            self.SetSavePoint()

        def SetInsertionPoint(self, pos: int) -> None:  # noqa: N802 - wx API
            # GotoPos moves caret AND anchor; the inherited implementation
            # leaves the anchor behind, silently dragging a selection.
            self.GotoPos(int(pos))


def create_stc_editor(wx_module: Any, parent: Any, style: int) -> Any:
    """Build the Scintilla surface, or a stock ``wx.TextCtrl`` fallback."""
    if _SCINTILLA:
        try:
            return StcEditorSurface(parent, style=style)
        except Exception:  # noqa: BLE001 - hosting is best-effort; fall back to wx
            pass
    return wx_module.TextCtrl(parent, style=style)
