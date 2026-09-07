"""Live probe of the RichEdit surface. Run on Windows only; prints PASS/FAIL lines."""

from __future__ import annotations

import os
import tempfile

# Point every QuillLite path at a throwaway directory BEFORE importing the
# package: paths.data_dir() reads LOCALAPPDATA at call time. Without this a
# probe shares settings, the inbox and the recovery folder with a copy of
# QuillLite the user has open, and can delete their unsaved work.
os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="quilllite-probe-")

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import wx  # noqa: E402

from quilllite import editor as ed  # noqa: E402
from quilllite import settings as settings_mod  # noqa: E402

results: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append(f"{'PASS' if ok else 'FAIL'} {name} {detail}".rstrip())


class FakeApp:
    def __init__(self) -> None:
        self.settings = settings_mod.Settings()
        self.frames = []
        self.active_frame = None
        self.data_dir = Path(tempfile.gettempdir())

    def save_settings(self):
        pass

    def refresh_all_menus(self):
        pass

    def open_path(self, *a, **k):
        pass

    def new_window(self, *a, **k):
        pass

    def focus_frame(self, f):
        pass

    def cycle(self, *a):
        pass

    def forget_frame(self, f):
        pass

    def exit_all(self):
        pass


def acc_name_value(hwnd: int) -> tuple[str, str, str]:
    from ctypes import POINTER, byref, windll  # noqa: PLC0415

    import comtypes  # noqa: PLC0415
    import comtypes.client  # noqa: PLC0415

    comtypes.client.GetModule("oleacc.dll")
    from comtypes.gen.Accessibility import IAccessible  # noqa: PLC0415

    OBJID_CLIENT = -4
    ptr = POINTER(IAccessible)()
    hr = windll.oleacc.AccessibleObjectFromWindow(
        hwnd, OBJID_CLIENT, byref(IAccessible._iid_), byref(ptr)
    )
    if hr != 0:
        return ("", "", f"hr={hr}")
    try:
        name = ptr.accName(0) or ""
    except Exception as exc:
        name = f"err {exc}"
    try:
        value = ptr.accValue(0) or ""
    except Exception as exc:
        value = f"err {exc}"
    try:
        role = ptr.accRole(0)
    except Exception as exc:
        role = f"err {exc}"
    return (str(name), str(value), str(role))


def main() -> None:
    _app = wx.App(redirect=False)  # must stay referenced for the lifetime of the call
    from quilllite.window import DocumentFrame  # noqa: PLC0415

    fake = FakeApp()
    frame = DocumentFrame(fake, mode=ed.RICH)
    fake.frames.append(frame)
    frame.Show()
    wx.Yield()
    e = frame.editor
    check("native TOM available", e.native())
    check("rich text mode", e.current_native_mode() == ed.RICH, e.current_native_mode())

    # Offsets: GetValue text vs insertion point across line breaks.
    frame._loading = True
    e.set_text("Alpha\nBravo\nCharlie")
    frame._loading = False
    text = e.get_text()
    check("newline normalised", text == "Alpha\nBravo\nCharlie", repr(text))
    idx = text.index("Charlie")
    e.control.SetInsertionPoint(idx)
    e.control.SetSelection(idx, idx + 7)
    sel = e.control.GetSelection()
    check("selection offsets match text", sel == (idx, idx + 7), str(sel))
    check(
        "TOM paragraph at offset", e.paragraph_text_at(idx) == "Charlie", e.paragraph_text_at(idx)
    )

    # Heading ladder through the TOM.
    e.control.SetInsertionPoint(text.index("Bravo"))
    e.set_heading(2)
    check(
        "heading 2 detected at caret",
        e.heading_level_at_caret() == 2,
        str(e.heading_level_at_caret()),
    )
    desc = e.describe_caret()
    check("describe mentions heading 2", "heading 2" in desc, desc)
    e.control.SetInsertionPoint(0)
    nxt = e.next_heading(0, reverse=False)
    check("next heading from top", nxt == (text.index("Bravo"), 2), str(nxt))
    prev = e.next_heading(len(text), reverse=True)
    check("previous heading from end", prev == (text.index("Bravo"), 2), str(prev))
    check(
        "all_headings",
        e.all_headings() == [(text.index("Bravo"), 2, "Bravo")],
        str(e.all_headings()),
    )
    e.control.SetInsertionPoint(0)
    check("body line not heading", e.heading_level_at_caret() is None)

    # Bold toggle state.
    e.control.SetSelection(0, 5)
    state = e.toggle("Bold")
    check("bold on", state is True)
    state = e.toggle("Bold")
    check("bold off", state is False)

    # RTF round trip via a file, with the dark-theme colour reset.
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "probe.rtf"
        ok = frame.save(target)
        check("save rtf", ok and target.exists() and target.read_bytes().startswith(b"{\\rtf"))
        raw = target.read_text(encoding="utf-8", errors="replace")
        check(
            "saved rtf has no theme grey",
            "\\red230\\green230\\blue230" not in raw,
            raw[:300].replace("\n", " "),
        )
        check("saved rtf has heading size 16pt (fs32)", "\\fs32" in raw)
        frame2 = DocumentFrame(fake, path=target, mode=ed.RICH)
        wx.Yield()
        e2 = frame2.editor
        check("reload text", e2.get_text() == "Alpha\nBravo\nCharlie", repr(e2.get_text()))
        check(
            "reload heading survives",
            e2.all_headings() == [(6, 2, "Bravo")],
            str(e2.all_headings()),
        )
        check("reload not modified", not frame2.modified)
        frame2.modified = False
        frame2.Destroy()

    # Mode switch to plain and back.
    frame.switch_mode = frame.switch_mode  # real method
    frame.modified = False
    orig_msgbox = wx.MessageBox
    wx.MessageBox = lambda *a, **k: wx.YES
    try:
        frame.switch_mode(ed.PLAIN)
    finally:
        wx.MessageBox = orig_msgbox
    check(
        "plain text mode after switch", e.current_native_mode() == ed.PLAIN, e.current_native_mode()
    )
    check(
        "text preserved after switch", e.get_text() == "Alpha\nBravo\nCharlie", repr(e.get_text())
    )
    frame.switch_mode(ed.RICH)
    check("rich again", e.current_native_mode() == ed.RICH)

    # Accessibility: MSAA name, value, role of the editor.
    try:
        name, value, role = acc_name_value(e.hwnd())
        check(
            "accValue reports text",
            "Alpha" in value,
            f"name={name!r} role={role} value={value[:40]!r}",
        )
    except Exception as exc:
        check("accValue probe", False, str(exc))

    # Plain-mode file save/load with CRLF.
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "probe.txt"
        target.write_bytes(b"one\r\ntwo\r\nthree")
        frame3 = DocumentFrame(fake, path=target, mode=ed.PLAIN)
        wx.Yield()
        check(
            "plain load",
            frame3.editor.get_text() == "one\ntwo\nthree",
            repr(frame3.editor.get_text()),
        )
        check("plain newline detected", frame3.newline == "\r\n")
        frame3.editor.control.AppendText("\nfour")
        check("plain modified after edit", frame3.modified)
        frame3.save()
        check(
            "plain save crlf",
            target.read_bytes() == b"one\r\ntwo\r\nthree\r\nfour",
            repr(target.read_bytes()),
        )
        frame3.modified = False
        frame3.Destroy()

    from quilllite import speech  # noqa: PLC0415

    check("speech backend", True, speech.backend_name())
    frame.modified = False
    frame.Destroy()
    print("\n".join(results))
    failures = [r for r in results if r.startswith("FAIL")]
    print(f"\n{len(results) - len(failures)} passed, {len(failures)} failed")


if __name__ == "__main__":
    main()
