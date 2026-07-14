"""Win32 native-EDIT editor surface — a pywin32 spike (Windows only, experimental).

A proof-of-concept "fifth surface" for the Experimental settings tab: instead of a
``wx.TextCtrl`` (which itself wraps a native EDIT/RichEdit on Windows), this hosts
the **raw Win32 ``EDIT`` control** — the exact control Notepad uses — as a child of
a ``wx.Window``, driven over Win32 messages via ``pywin32`` with no C compilation.

What it demonstrates:
* The genuine native EDIT feel/perf, embedded in QUILL's frame and splitter.
* Bridging the control back into QUILL's pipeline: an ``EN_CHANGE`` notification
  (caught by subclassing the host window proc) is forwarded to the main frame's
  ``_on_text_changed`` via ``wx.CallAfter``, so dirty-tracking, word count, and the
  Reveal Codes idle sync keep working.

Known spike limitations (the point of a spike — surfacing the real integration
cost, documented rather than hidden):
* **CRLF vs LF.** The EDIT control stores line breaks as ``\r\n``; QUILL uses
  ``\n``. ``GetValue``/``SetValue`` translate the *text*, but caret/selection
  offsets are reported in the control's own space, so multi-line offset-precise
  features can be off by the number of preceding newlines.
* **Selection packing.** ``EM_GETSEL``'s packed return clamps to ~64K, so caret
  reporting past that is approximate.
* **Key/mouse events** go to the native control, not wx, so wx-level key features
  (type-time autoformat, describe-key) do not fire in this surface.

The factory always returns ``None`` on failure (or off-Windows), so selecting this
surface can never brick the editor — the caller falls back to a ``wx.TextCtrl``.
"""

from __future__ import annotations

import sys
from typing import Any

import wx

_WIN32 = sys.platform == "win32"

if _WIN32:
    try:
        import win32api
        import win32con
        import win32gui

        _PYWIN32 = True
    except Exception:  # noqa: BLE001 - pywin32 absent/broken: surface unavailable
        _PYWIN32 = False
else:  # pragma: no cover - non-Windows
    _PYWIN32 = False

_EDIT_ID = 1001  # control id so WM_COMMAND/EN_CHANGE identifies our child


def win32_edit_surface_available() -> bool:
    """True only where the native-EDIT spike surface can be built."""
    return bool(_WIN32 and _PYWIN32)


def create_win32_edit_host(parent: Any) -> Any | None:
    """Build a native-EDIT host, or ``None`` if unavailable/unsupported.

    Defensive: any failure returns ``None`` so the caller falls back to a stock
    ``wx.TextCtrl`` and the editor is never broken by selecting this surface.
    """
    if not win32_edit_surface_available():
        return None
    try:
        return _Win32EditHost(parent)
    except Exception:  # noqa: BLE001 - hosting is best-effort; fall back to wx
        return None


if _WIN32 and _PYWIN32:

    class _Win32EditHost(wx.Window):
        """A ``wx.Window`` that hosts and drives a native Win32 EDIT control."""

        def __init__(self, parent: Any) -> None:
            super().__init__(parent)
            self._main: Any = None
            self._old_proc: Any = None
            self._proc_ref: Any = None
            hwnd_parent = int(self.GetHandle())
            style = (
                win32con.WS_CHILD
                | win32con.WS_VISIBLE
                | win32con.ES_MULTILINE
                | win32con.ES_AUTOVSCROLL
                | win32con.ES_AUTOHSCROLL
                | win32con.ES_WANTRETURN
                | win32con.ES_NOHIDESEL
                | win32con.WS_VSCROLL
            )
            self._edit = win32gui.CreateWindowEx(
                0,
                "EDIT",
                "",
                style,
                0,
                0,
                10,
                10,
                hwnd_parent,
                _EDIT_ID,
                win32api.GetModuleHandle(None),
                None,
            )
            try:
                font = win32gui.GetStockObject(win32con.DEFAULT_GUI_FONT)
                win32gui.SendMessage(self._edit, win32con.WM_SETFONT, font, 1)
            except Exception:  # noqa: BLE001
                pass
            self._fit_child()
            self.Bind(wx.EVT_SIZE, self._on_size)
            self._install_wndproc()

        def surface_kind(self) -> str:
            return "win32"

        # -- layout ----------------------------------------------------- #
        def _fit_child(self) -> None:
            w, h = self.GetClientSize()
            try:
                win32gui.MoveWindow(self._edit, 0, 0, max(0, int(w)), max(0, int(h)), True)
            except Exception:  # noqa: BLE001
                pass

        def _on_size(self, event: Any) -> None:
            self._fit_child()
            event.Skip()

        # -- EN_CHANGE bridge (subclass the host window proc) ----------- #
        def _install_wndproc(self) -> None:
            try:
                self._proc_ref = self._wndproc
                self._old_proc = win32gui.SetWindowLong(
                    int(self.GetHandle()), win32con.GWL_WNDPROC, self._proc_ref
                )
            except Exception:  # noqa: BLE001 - no bridge; typing still works
                self._old_proc = None

        def _wndproc(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
            try:
                if msg == win32con.WM_COMMAND and (wparam >> 16) & 0xFFFF == win32con.EN_CHANGE:
                    if self._main is not None:
                        wx.CallAfter(self._notify_change)
            except Exception:  # noqa: BLE001 - never let the proc raise
                pass
            if self._old_proc:
                return win32gui.CallWindowProc(self._old_proc, hwnd, msg, wparam, lparam)
            return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

        def _notify_change(self) -> None:
            if self._main is not None:
                try:
                    self._main._on_text_changed(None)
                except Exception:  # noqa: BLE001
                    pass

        # -- QUILL editor-event hook ------------------------------------ #
        def bind_editor_events(self, main_frame: Any) -> None:
            self._main = main_frame
            self.Bind(wx.EVT_SET_FOCUS, lambda e: (self.SetFocus(), e.Skip()))

        # -- text (CRLF <-> LF) ----------------------------------------- #
        def GetValue(self) -> str:  # noqa: N802
            try:
                return win32gui.GetWindowText(self._edit).replace("\r\n", "\n")
            except Exception:  # noqa: BLE001
                return ""

        def SetValue(self, value: str) -> None:  # noqa: N802
            try:
                win32gui.SetWindowText(self._edit, (value or "").replace("\n", "\r\n"))
            except Exception:  # noqa: BLE001
                pass
            if self._main is not None:
                wx.CallAfter(self._notify_change)

        def ChangeValue(self, value: str) -> None:  # noqa: N802
            # SetWindowText does not raise EN_CHANGE, so this is the no-event setter.
            try:
                win32gui.SetWindowText(self._edit, (value or "").replace("\n", "\r\n"))
            except Exception:  # noqa: BLE001
                pass

        def WriteText(self, text: str) -> None:  # noqa: N802
            ip = self.GetInsertionPoint()
            value = self.GetValue()
            self.SetValue(value[:ip] + text + value[ip:])
            self.SetInsertionPoint(ip + len(text))

        def AppendText(self, text: str) -> None:  # noqa: N802
            self.SetValue(self.GetValue() + text)

        def Clear(self) -> None:  # noqa: N802
            self.SetValue("")

        def IsEmpty(self) -> bool:  # noqa: N802
            return not self.GetValue()

        # -- caret / selection ------------------------------------------ #
        def GetLastPosition(self) -> int:  # noqa: N802
            return len(self.GetValue())

        def _sel(self) -> tuple[int, int]:
            try:
                packed = win32gui.SendMessage(self._edit, win32con.EM_GETSEL, 0, 0)
                return packed & 0xFFFF, (packed >> 16) & 0xFFFF
            except Exception:  # noqa: BLE001
                return 0, 0

        def GetInsertionPoint(self) -> int:  # noqa: N802
            return self._sel()[0]

        def SetInsertionPoint(self, pos: int) -> None:  # noqa: N802
            try:
                win32gui.SendMessage(self._edit, win32con.EM_SETSEL, int(pos), int(pos))
            except Exception:  # noqa: BLE001
                pass

        def GetSelection(self) -> tuple[int, int]:  # noqa: N802
            return self._sel()

        def SetSelection(self, start: int, end: int) -> None:  # noqa: N802
            try:
                win32gui.SendMessage(self._edit, win32con.EM_SETSEL, int(start), int(end))
            except Exception:  # noqa: BLE001
                pass

        def GetStringSelection(self) -> str:  # noqa: N802
            start, end = self._sel()
            return self.GetValue()[start:end]

        def GetRange(self, start: int, end: int) -> str:  # noqa: N802
            return self.GetValue()[start:end]

        def Replace(self, start: int, end: int, text: str) -> None:  # noqa: N802
            value = self.GetValue()
            self.SetValue(value[:start] + text + value[end:])
            self.SetInsertionPoint(start + len(text))

        def Remove(self, start: int, end: int) -> None:  # noqa: N802
            self.Replace(start, end, "")

        def ShowPosition(self, pos: int) -> None:  # noqa: N802
            self.SetInsertionPoint(pos)
            try:
                win32gui.SendMessage(self._edit, win32con.EM_SCROLLCARET, 0, 0)
            except Exception:  # noqa: BLE001
                pass

        def GetNumberOfLines(self) -> int:  # noqa: N802
            try:
                return int(win32gui.SendMessage(self._edit, win32con.EM_GETLINECOUNT, 0, 0))
            except Exception:  # noqa: BLE001
                return 1

        # -- modified / editable ---------------------------------------- #
        def IsModified(self) -> bool:  # noqa: N802
            try:
                return bool(win32gui.SendMessage(self._edit, win32con.EM_GETMODIFY, 0, 0))
            except Exception:  # noqa: BLE001
                return False

        def SetModified(self, modified: bool) -> None:  # noqa: N802
            try:
                win32gui.SendMessage(self._edit, win32con.EM_SETMODIFY, 1 if modified else 0, 0)
            except Exception:  # noqa: BLE001
                pass

        def MarkDirty(self) -> None:  # noqa: N802
            self.SetModified(True)

        def DiscardEdits(self) -> None:  # noqa: N802
            self.SetModified(False)

        def SetEditable(self, editable: bool) -> None:  # noqa: N802
            try:
                win32gui.SendMessage(self._edit, win32con.EM_SETREADONLY, 0 if editable else 1, 0)
            except Exception:  # noqa: BLE001
                pass

        def IsEditable(self) -> bool:  # noqa: N802
            try:
                style = win32api.GetWindowLong(self._edit, win32con.GWL_STYLE)
                return not bool(style & win32con.ES_READONLY)
            except Exception:  # noqa: BLE001
                return True

        # -- clipboard / undo (native EDIT commands) -------------------- #
        def Copy(self) -> None:  # noqa: N802
            self._cmd(win32con.WM_COPY)

        def Cut(self) -> None:  # noqa: N802
            self._cmd(win32con.WM_CUT)

        def Paste(self) -> None:  # noqa: N802
            self._cmd(win32con.WM_PASTE)

        def Undo(self) -> None:  # noqa: N802
            self._cmd(win32con.WM_UNDO)

        def CanUndo(self) -> bool:  # noqa: N802
            try:
                return bool(win32gui.SendMessage(self._edit, win32con.EM_CANUNDO, 0, 0))
            except Exception:  # noqa: BLE001
                return False

        def _cmd(self, msg: int) -> None:
            try:
                win32gui.SendMessage(self._edit, msg, 0, 0)
            except Exception:  # noqa: BLE001
                pass

        # -- focus ------------------------------------------------------ #
        def SetFocus(self) -> None:  # noqa: N802
            try:
                win32gui.SetFocus(self._edit)
            except Exception:  # noqa: BLE001
                super().SetFocus()
