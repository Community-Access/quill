"""Faithful repro harness for the "JAWS reads line 1 on the empty line" quirk.

Goal: isolate whether the misread is (a) the native RichEdit's line accounting,
(b) QUILL's braille fix (SES_EMULATESYSEDIT) changing how the control exposes
text to screen readers, or (c) JAWS reading an otherwise-correct control. NO
QUILL code is imported -- this rebuilds QUILL's *exact* editor control from raw
wx + one ctypes message, so whatever it shows is the control's behaviour, not
QUILL logic on top.

WHY THIS MATCHES QUILL
  On Windows QUILL's editor is NOT a plain wx.TextCtrl. It is
  create_richedit_rtf(...) -> wx.TextCtrl(TE_RICH2 | TE_NOHIDESEL) (a native
  RICHEDIT50W control) with SES_EMULATESYSEDIT applied via EM_SETEDITSTYLE (the
  braille "text from cell 1 / selection dots" fix, on by default) and a
  BORDER_NONE frame (also part of the braille fix). This harness reproduces all
  of that and lets you toggle each piece, so you can A/B whether the braille
  fix -- not QUILL's own code -- is what makes JAWS misread the empty line.

HOW TO USE
  1. Run it:  python jaws_blank_line_repro.py
  2. Leave the checkboxes at their defaults (they match QUILL's editor exactly).
  3. Turn JAWS on.
  4. Click "Load: short line + Enter" (or type the text and press Enter yourself).
  5. With the caret on the empty second line, do a JAWS "say current line"
     (Insert+Up). Note what JAWS speaks.
  6. Read the DIAGNOSTICS panel: it shows what the *control itself* reports for
     the caret's line, plus whether SES_EMULATESYSEDIT is actually on.
  7. Now A/B: uncheck "SES_EMULATESYSEDIT (braille fix)", click Apply, reload the
     test case, and repeat the JAWS read.

READING THE RESULT
  - Misreads with SES_EMULATESYSEDIT ON but reads "blank" with it OFF
        -> QUILL's braille fix is implicated. Fix/space it in QUILL (or raise
           with the RichEdit/JAWS interaction), do NOT punt blindly.
  - Misreads regardless of SES_EMULATESYSEDIT, but the control reports the caret
    line as "" (blank) in DIAGNOSTICS
        -> the control is correct; JAWS is misreading. Punt to JAWS with this repro.
  - The control's DIAGNOSTICS ALSO reports line 1 for the empty-line caret
        -> native RichEdit / wx bug below both QUILL and JAWS. Punt to wx/MS.
  - Plain wx.TextCtrl (uncheck TE_RICH2) does NOT misread but the RichEdit does
        -> RichEdit-specific; note it when filing.

Report back the JAWS speech + DIAGNOSTICS line for each combo you try.
"""

from __future__ import annotations

import sys

import wx

# richedit.h constants (mirrors quill/ui/richedit_rtf_surface.py exactly).
_EM_SETEDITSTYLE = 0x0400 + 204  # 0x04CC
_EM_GETEDITSTYLE = 0x0400 + 205  # 0x04CD
_SES_EMULATESYSEDIT = 0x00000001

TEST_SHORT = "This **is** a *test*."
TEST_LONG = "This **is** a *test*. Thank you for playing this game with me."


def _send_message(hwnd: int, msg: int, wparam: int, lparam: int) -> int:
    import ctypes

    fn = ctypes.windll.user32.SendMessageW  # type: ignore[attr-defined]
    fn.argtypes = (
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_size_t,
        ctypes.c_ssize_t,
    )
    fn.restype = ctypes.c_ssize_t
    return int(fn(hwnd, msg, wparam, lparam))


def _apply_emulate_system_edit(editor: wx.TextCtrl, enabled: bool) -> None:
    if sys.platform != "win32":
        return
    try:
        hwnd = int(editor.GetHandle())
        style = _SES_EMULATESYSEDIT if enabled else 0
        _send_message(hwnd, _EM_SETEDITSTYLE, style, _SES_EMULATESYSEDIT)
    except Exception as exc:  # noqa: BLE001
        print("apply SES_EMULATESYSEDIT failed:", exc)


def _current_edit_style(editor: wx.TextCtrl) -> int | None:
    if sys.platform != "win32":
        return None
    try:
        return _send_message(int(editor.GetHandle()), _EM_GETEDITSTYLE, 0, 0)
    except Exception:  # noqa: BLE001
        return None


class ReproFrame(wx.Frame):
    def __init__(self) -> None:
        super().__init__(None, title="JAWS blank-line repro (matches QUILL's editor)")
        panel = wx.Panel(self)
        outer = wx.BoxSizer(wx.VERTICAL)

        # -- options: default checked state MATCHES QUILL's editor exactly ---- #
        self._cb_rich = wx.CheckBox(panel, label="TE_RICH2 (native RichEdit)")
        self._cb_rich.SetValue(True)
        self._cb_nohide = wx.CheckBox(panel, label="TE_NOHIDESEL")
        self._cb_nohide.SetValue(True)
        self._cb_emulate = wx.CheckBox(panel, label="SES_EMULATESYSEDIT (braille fix)")
        self._cb_emulate.SetValue(True)
        self._cb_borderless = wx.CheckBox(panel, label="BORDER_NONE (braille fix)")
        self._cb_borderless.SetValue(True)
        self._cb_wrap = wx.CheckBox(panel, label="Word wrap")
        self._cb_wrap.SetValue(True)
        opts = wx.WrapSizer(wx.HORIZONTAL)
        for cb in (
            self._cb_rich,
            self._cb_nohide,
            self._cb_emulate,
            self._cb_borderless,
            self._cb_wrap,
        ):
            opts.Add(cb, 0, wx.ALL, 6)
        outer.Add(opts, 0, wx.EXPAND)

        row = wx.BoxSizer(wx.HORIZONTAL)
        b_apply = wx.Button(panel, label="Apply (rebuild control)")
        b_apply.Bind(wx.EVT_BUTTON, lambda _e: self._build_editor())
        row.Add(b_apply, 0, wx.ALL, 4)
        b_short = wx.Button(panel, label="Load: short line + Enter")
        b_short.Bind(wx.EVT_BUTTON, lambda _e: self._load(TEST_SHORT))
        row.Add(b_short, 0, wx.ALL, 4)
        b_long = wx.Button(panel, label="Load: long line + Enter")
        b_long.Bind(wx.EVT_BUTTON, lambda _e: self._load(TEST_LONG))
        row.Add(b_long, 0, wx.ALL, 4)
        b_clear = wx.Button(panel, label="Clear")
        b_clear.Bind(wx.EVT_BUTTON, lambda _e: self._load(""))
        row.Add(b_clear, 0, wx.ALL, 4)
        outer.Add(row, 0, wx.EXPAND)

        self._holder = wx.BoxSizer(wx.VERTICAL)
        outer.Add(self._holder, 1, wx.EXPAND | wx.ALL, 4)

        self._diag = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
            size=(-1, 190),
        )
        self._diag.SetName("Diagnostics")
        outer.Add(self._diag, 0, wx.EXPAND | wx.ALL, 4)

        panel.SetSizer(outer)
        self._panel = panel
        self._editor: wx.TextCtrl | None = None
        self._build_editor()
        self.SetSize((820, 660))

    # -- editor lifecycle ------------------------------------------------ #
    def _build_editor(self) -> None:
        style = wx.TE_MULTILINE
        if self._cb_rich.GetValue():
            style |= wx.TE_RICH2
        if self._cb_nohide.GetValue():
            style |= wx.TE_NOHIDESEL
        if not self._cb_wrap.GetValue():
            style |= wx.TE_DONTWRAP
        if self._cb_borderless.GetValue():
            style |= wx.BORDER_NONE
        old = self._editor
        editor = wx.TextCtrl(self._panel, style=style)
        editor.SetName("Document")  # QUILL names its editor "Document"
        editor.Bind(wx.EVT_KEY_UP, self._on_activity)
        editor.Bind(wx.EVT_LEFT_UP, self._on_activity)
        self._holder.Add(editor, 1, wx.EXPAND)
        if old is not None:
            self._holder.Detach(old)
            old.Destroy()
        self._editor = editor
        # Apply the braille edit-style fix AFTER the HWND exists.
        _apply_emulate_system_edit(editor, self._cb_emulate.GetValue())
        self._panel.Layout()
        editor.SetFocus()
        self._report()

    def _load(self, line: str) -> None:
        editor = self._editor
        if editor is None:
            return
        # Mirror "type the line, then press Enter": value ends with a newline and
        # the caret sits at the start of the empty second line.
        editor.SetValue(line + "\n" if line else "")
        editor.SetInsertionPointEnd()
        editor.SetFocus()
        self._report()

    # -- diagnostics ----------------------------------------------------- #
    def _on_activity(self, event: wx.Event) -> None:
        event.Skip()
        self._report()

    def _report(self) -> None:
        editor = self._editor
        if editor is None:
            return
        pos = editor.GetInsertionPoint()
        last = editor.GetLastPosition()
        num_lines = editor.GetNumberOfLines()
        ok, col, row = self._position_to_xy(editor, pos)
        cur_line_text = editor.GetLineText(row) if 0 <= row < num_lines else "<out of range>"
        try:
            cur_line_len = editor.GetLineLength(row)
        except Exception:  # noqa: BLE001
            cur_line_len = -1
        style = _current_edit_style(editor)
        emulate_on = style is not None and bool(style & _SES_EMULATESYSEDIT)
        lines_dump = "\n".join(f"    line {i}: {editor.GetLineText(i)!r}" for i in range(num_lines))
        if cur_line_text == "":
            verdict = (
                "control reports the caret line as BLANK -> if JAWS still speaks "
                "line 1, the bug is JAWS (or the SES_EMULATESYSEDIT exposure)"
            )
        else:
            verdict = "control reports the caret line as NON-EMPTY -> compare to JAWS"
        self._diag.SetValue(
            f"SES_EMULATESYSEDIT requested={self._cb_emulate.GetValue()}  "
            f"actual edit style={hex(style) if style is not None else 'n/a'}  "
            f"(emulate {'ON' if emulate_on else 'off'})\n"
            f"value repr = {editor.GetValue()!r}\n"
            f"insertion point = {pos}   last position = {last}   "
            f"number of lines = {num_lines}\n"
            f"PositionToXY({pos}) -> ok={ok} col={col} row(line)={row}\n"
            f"current caret line text = {cur_line_text!r}   length = {cur_line_len}\n"
            f"all lines:\n{lines_dump}\n\n"
            f"VERDICT: {verdict}"
        )

    @staticmethod
    def _position_to_xy(editor: wx.TextCtrl, pos: int):
        result = editor.PositionToXY(pos)
        if isinstance(result, tuple) and len(result) == 3:
            return result
        if isinstance(result, tuple) and len(result) == 2:
            return (True, result[0], result[1])
        return (False, -1, -1)


def main() -> int:
    app = wx.App(False)
    frame = ReproFrame()
    frame.Show()
    app.MainLoop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
