"""Spike probe: what does UI Automation report for tables in a wx RichEdit?

Not shipped (lives under docs/, not quill/). Run with the system Python:

    py -3.14 docs/design/spikes/table_uia/probe_richedit_table_uia.py

It opens a small wx frame with two TE_RICH2 controls (class RICHEDIT50W):

* ``native`` -- a real Rich Edit table (RTF ``\\trowd`` rows) loaded with
  EM_SETTEXTEX, the same table storage TOM ``ITextRange2::InsertTable`` makes.
* ``pipe``   -- the same table as QUILL shows it today, as Markdown pipe rows.

It then starts a *second* process (UIA clients should not run on the provider's
own UI thread) that dumps, for each control: whether msftedit answers with its
own server-side UIA provider, the element's control type and patterns, the
TextPattern document text, ``GetChildren()`` of the document range, the raw-view
child elements, and ``GetEnclosingElement()`` for a range inside cell "B2"
(the call NVDA uses to build table control fields). No screen reader needed.
"""

from __future__ import annotations

import ctypes
import subprocess
import sys
from ctypes import wintypes

RTF_TABLE = (
    r"{\rtf1\ansi\deff0{\fonttbl{\f0 Segoe UI;}}\f0\fs20 "
    r"Before the table.\par "
    r"\trowd\trgaph100\cellx2000\cellx4000\cellx6000 "
    r"\intbl Name\cell Age\cell City\cell\row "
    r"\trowd\trgaph100\cellx2000\cellx4000\cellx6000 "
    r"\intbl A2\cell B2\cell C2\cell\row "
    r"\trowd\trgaph100\cellx2000\cellx4000\cellx6000 "
    r"\intbl A3\cell B3\cell C3\cell\row "
    r"\pard After the table.\par }"
)

PIPE_TABLE = (
    "Before the table.\n"
    "| Name | Age | City |\n"
    "| --- | --- | --- |\n"
    "| A2 | B2 | C2 |\n"
    "| A3 | B3 | C3 |\n"
    "After the table.\n"
)

EM_SETTEXTEX = 0x0461


class SETTEXTEX(ctypes.Structure):
    _fields_ = [("flags", wintypes.DWORD), ("codepage", wintypes.UINT)]


def _set_rtf(hwnd: int, rtf: str) -> int:
    send = ctypes.windll.user32.SendMessageW
    send.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
    send.restype = ctypes.c_ssize_t
    info = SETTEXTEX(0, 0)  # ST_DEFAULT, CP_ACP: "{\rtf" is recognised as RTF
    data = ctypes.create_string_buffer(rtf.encode("ascii"))
    return send(hwnd, EM_SETTEXTEX, ctypes.addressof(info), ctypes.addressof(data))


# --------------------------------------------------------------------------- #
# Provider side: the wx frame
# --------------------------------------------------------------------------- #


def run_frame() -> int:
    import wx

    app = wx.App(False)
    frame = wx.Frame(None, title="Table UIA probe", size=(700, 500))
    panel = wx.Panel(frame)
    style = wx.TE_MULTILINE | wx.TE_RICH2
    native = wx.TextCtrl(panel, style=style, name="native")
    pipe = wx.TextCtrl(panel, style=style, name="pipe")
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(native, 1, wx.EXPAND | wx.ALL, 4)
    sizer.Add(pipe, 1, wx.EXPAND | wx.ALL, 4)
    panel.SetSizer(sizer)
    frame.Show()
    print("set_rtf returned", _set_rtf(native.GetHandle(), RTF_TABLE))
    pipe.SetValue(PIPE_TABLE)
    print("native GetValue:", repr(native.GetValue()))
    state: dict[str, object] = {}

    def start() -> None:
        args = [sys.executable, __file__, "--dump", str(native.GetHandle()), str(pipe.GetHandle())]
        state["proc"] = subprocess.Popen(args)
        timer.Start(200)

    def poll(_evt: object) -> None:
        proc = state["proc"]
        assert isinstance(proc, subprocess.Popen)
        if proc.poll() is not None:
            timer.Stop()
            state["rc"] = proc.returncode
            frame.Destroy()

    timer = wx.Timer(frame)
    frame.Bind(wx.EVT_TIMER, poll, timer)
    wx.CallLater(800, start)
    app.MainLoop()
    return int(state.get("rc", 1))  # type: ignore[call-overload]


# --------------------------------------------------------------------------- #
# Client side: the UIA dump (separate process)
# --------------------------------------------------------------------------- #

CONTROL_TYPES = {
    50004: "Edit",
    50006: "Image",
    50020: "Text",
    50029: "DataItem",
    50030: "Document",
    50033: "Pane",
    50036: "Table",
    50028: "DataGrid",
    50032: "Window",
    50025: "Custom",
    50023: "List",
}
PATTERNS = {
    "Text": 10014,
    "Text2": 10024,
    "Table": 10012,
    "Grid": 10006,
    "TableItem": 10013,
    "GridItem": 10007,
    "Value": 10002,
}
UIA_ProviderDescriptionPropertyId = 30107
UIA_StyleNameAttributeId = 40042
UIA_StyleIdAttributeId = 40034


def _describe(uia_mod: object, el: object) -> str:
    try:
        ct = el.CurrentControlType  # type: ignore[attr-defined]
        name = el.CurrentName  # type: ignore[attr-defined]
        cls = el.CurrentClassName  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001
        return f"<unreadable: {exc}>"
    pats = []
    for label, pid in PATTERNS.items():
        try:
            if el.GetCurrentPattern(pid):  # type: ignore[attr-defined]
                pats.append(label)
        except Exception:  # noqa: BLE001
            pass
    return f"{CONTROL_TYPES.get(ct, ct)} name={name!r} class={cls!r} patterns={pats}"


def _walk(uia_mod: object, walker: object, el: object, depth: int) -> int:
    """Print the raw-view subtree under *el* (3 levels); return direct-child count."""
    child = _safe(lambda: walker.GetFirstChildElement(el))  # type: ignore[attr-defined]
    n = 0
    while child and n < 30:
        print("  " * depth + "raw child:", _describe(uia_mod, child))
        _print_grid(uia_mod, child, depth)
        if depth < 3:
            _walk(uia_mod, walker, child, depth + 1)
        child = _safe(lambda c=child: walker.GetNextSiblingElement(c))  # type: ignore[attr-defined]
        n += 1
    return n


def _safe(fn: object) -> object:
    try:
        return fn()  # type: ignore[operator]
    except Exception:  # noqa: BLE001 - comtypes raises on a NULL sibling
        return None


def _print_grid(uia_mod: object, el: object, depth: int) -> None:
    pad = "  " * depth + "  "
    grid = _safe(lambda: el.GetCurrentPattern(PATTERNS["Grid"]))  # type: ignore[attr-defined]
    if grid:
        g = grid.QueryInterface(uia_mod.IUIAutomationGridPattern)  # type: ignore[attr-defined]
        print(pad + f"Grid rows={g.CurrentRowCount} cols={g.CurrentColumnCount}")
    item = _safe(lambda: el.GetCurrentPattern(PATTERNS["GridItem"]))  # type: ignore[attr-defined]
    if item:
        gi = item.QueryInterface(uia_mod.IUIAutomationGridItemPattern)  # type: ignore[attr-defined]
        print(pad + f"GridItem row={gi.CurrentRow} col={gi.CurrentColumn}")
    vp = _safe(lambda: el.GetCurrentPattern(PATTERNS["Text"]))  # type: ignore[attr-defined]
    if vp:
        tp = vp.QueryInterface(uia_mod.IUIAutomationTextPattern)  # type: ignore[attr-defined]
        print(pad + "text:", repr(tp.DocumentRange.GetText(-1)))


def run_dump(hwnds: list[int]) -> int:
    import comtypes.client

    uia_mod = comtypes.client.GetModule("UIAutomationCore.dll")
    uia = comtypes.client.CreateObject(uia_mod.CUIAutomation, interface=uia_mod.IUIAutomation)
    core = ctypes.windll.uiautomationcore
    walker = uia.RawViewWalker
    for label, hwnd in zip(("native", "pipe"), hwnds, strict=True):
        print(f"\n===== {label} (hwnd {hwnd:#x}) =====")
        print("UiaHasServerSideProvider:", bool(core.UiaHasServerSideProvider(hwnd)))
        el = uia.ElementFromHandle(hwnd)
        print("element:", _describe(uia_mod, el))
        print("provider:", el.GetCurrentPropertyValue(UIA_ProviderDescriptionPropertyId))
        print("raw children:", _walk(uia_mod, walker, el, 1))
        raw = el.GetCurrentPattern(PATTERNS["Text"])
        if not raw:
            print("NO TextPattern")
            continue
        tp = raw.QueryInterface(uia_mod.IUIAutomationTextPattern)
        doc = tp.DocumentRange
        print("document text:", repr(doc.GetText(-1)))
        kids = doc.GetChildren()
        print("DocumentRange.GetChildren() length:", kids.Length)
        for i in range(kids.Length):
            print("  child:", _describe(uia_mod, kids.GetElement(i)))
        rng = doc.FindText("B2", False, False)
        if rng is None:
            print("FindText('B2') found nothing")
            continue
        enc = rng.GetEnclosingElement()
        print("B2 enclosing element:", _describe(uia_mod, enc))
        parent = walker.GetParentElement(enc)
        depth = 0
        while parent and depth < 4:
            print("  ancestor:", _describe(uia_mod, parent))
            parent = _safe(lambda p=parent: walker.GetParentElement(p))
            depth += 1
        for attr_label, attr in (
            ("StyleName", UIA_StyleNameAttributeId),
            ("StyleId", UIA_StyleIdAttributeId),
        ):
            try:
                value = rng.GetAttributeValue(attr)
                unsupported = value == uia.ReservedNotSupportedValue
                print(f"B2 {attr_label}:", "NotSupported" if unsupported else repr(value))
            except Exception as exc:  # noqa: BLE001
                print(f"B2 {attr_label}: error {exc}")
        line = doc.FindText("B2", False, False)
        line.ExpandToEnclosingUnit(3)  # TextUnit_Line
        print("B2 line unit:", repr(line.GetText(-1)))
        para = doc.FindText("B2", False, False)
        para.ExpandToEnclosingUnit(4)  # TextUnit_Paragraph
        print("B2 paragraph unit:", repr(para.GetText(-1)))
    tables = uia.ElementFromHandle(hwnds[0]).FindAll(
        4,  # TreeScope_Descendants
        uia.CreatePropertyCondition(30038, True),  # IsTablePatternAvailable
    )
    print("\nnative: descendants with Table pattern:", tables.Length)
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--dump":
        sys.exit(run_dump([int(a) for a in sys.argv[2:4]]))
    sys.exit(run_frame())
