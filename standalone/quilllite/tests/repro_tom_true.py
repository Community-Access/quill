"""Reproduction: _TOM_TRUE was tomUndefined, so Font.Bold never applied.

**FIXED in QUILL on 2026-09-08.** This script is kept, unchanged and still
runnable, because it is the evidence rather than the report: it demonstrates the
control's behaviour directly, against a real RICHEDIT50W, and anyone who doubts
the fix -- or who meets the same class of bug in another TOM property -- can run
it and watch the two lines differ. Contributed with PR #1490 by Steven Scott.

The description below is written in the present tense against the *pre-fix*
source, which is what it was reproducing. `quill/ui/richedit_rtf_surface.py` now
declares `_TOM_TRUE = -1` and names `-9999999` as `_TOM_UNDEFINED`.

Self-contained. Needs only wxPython and comtypes on Windows; it does not import
QuillLite or QUILL, so a maintainer can run it against a clean checkout.

tom.h defines:

    tomFalse      = 0
    tomTrue       = -1
    tomUndefined  = -9999999
    tomToggle     = -9999998

quill/ui/richedit_rtf_surface.py declares ``_TOM_TRUE = -9999999``, which is
tomUndefined. Assigning it to ``ITextFont.Bold`` asks the control to leave bold
undefined, so nothing happens and no error is raised.

Run:  python repro_tom_true.py
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

import comtypes
import comtypes.client
import wx

EM_GETOLEINTERFACE = 0x0400 + 60
TOM_TYPELIB = ("{8CC497C9-A1DF-11CE-8098-00AA0047BE5D}", 1, 0)
TOM_UNIT_PARAGRAPH = 4

QUILL_TOM_TRUE = -9999999  # what quill/ui/richedit_rtf_surface.py uses
REAL_TOM_TRUE = -1  # what tom.h says


def text_document(hwnd: int):
    send = ctypes.windll.user32.SendMessageW
    send.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
    send.restype = ctypes.c_ssize_t
    ptr = ctypes.c_void_p(0)
    send(hwnd, EM_GETOLEINTERFACE, 0, ctypes.addressof(ptr))
    if not ptr.value:
        raise RuntimeError("EM_GETOLEINTERFACE returned nothing")
    module = comtypes.client.GetModule(TOM_TYPELIB)
    unknown = ctypes.cast(ptr.value, ctypes.POINTER(comtypes.IUnknown))
    return unknown.QueryInterface(module.ITextDocument)


def apply_heading_like_quill(control, document, bold_value: int) -> tuple[int, int]:
    """The body of QUILL's QuillRichEdit.set_heading, with the constant varied."""
    control.ChangeValue("Alpha\nBravo\nCharlie")
    control.SetInsertionPoint(6)
    selection = document.Selection
    selection.SetRange(6, 6)
    span = selection.Duplicate
    span.Expand(TOM_UNIT_PARAGRAPH)
    font = span.Font
    font.Size = 16.0  # HEADING_POINT_SIZES[2]
    font.Bold = bold_value  # _TOM_TRUE
    check = document.Range(6, 6)
    check.Expand(TOM_UNIT_PARAGRAPH)
    return int(check.Font.Bold), int(check.Font.Weight)


def main() -> int:
    if sys.platform != "win32":
        print("Windows only")
        return 1
    _app = wx.App(redirect=False)  # must stay referenced for the lifetime of the call
    frame = wx.Frame(None)
    control = wx.TextCtrl(frame, style=wx.TE_MULTILINE | wx.TE_RICH2)
    frame.Show()
    wx.Yield()

    class_name = ctypes.create_unicode_buffer(256)
    ctypes.windll.user32.GetClassNameW(int(control.GetHandle()), class_name, 256)
    document = text_document(int(control.GetHandle()))

    print(f"control class : {class_name.value}")
    print(f"wxPython      : {wx.version()}")
    print(f"windows build : {sys.getwindowsversion().build}")
    print()

    bold, weight = apply_heading_like_quill(control, document, QUILL_TOM_TRUE)
    print(f"Bold = {QUILL_TOM_TRUE} (QUILL's _TOM_TRUE)   -> Bold={bold} Weight={weight}")
    quill_ok = weight >= 700

    bold, weight = apply_heading_like_quill(control, document, REAL_TOM_TRUE)
    print(f"Bold = {REAL_TOM_TRUE} (tom.h tomTrue)          -> Bold={bold} Weight={weight}")
    real_ok = weight >= 700

    print()
    print(f"QUILL's constant applies bold : {quill_ok}")
    print(f"tom.h tomTrue applies bold    : {real_ok}")
    frame.Destroy()

    if not quill_ok and real_ok:
        print("\nReproduced: the heading gets its point size but never its bold.")
        return 0
    print("\nNot reproduced on this machine.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
