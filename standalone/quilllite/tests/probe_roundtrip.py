"""Byte-exact round trips, and the real event loop for timer-driven handover."""

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
    line = f"{'PASS' if ok else 'FAIL'} {name} {detail}".rstrip()
    results.append(line)
    print(line, flush=True)


class FakeApp:
    def __init__(self):
        self.settings = settings_mod.Settings()
        self.frames = []
        self.active_frame = None
        self.data_dir = Path(tempfile.gettempdir())

    def save_settings(self):
        pass

    def refresh_all_menus(self):
        pass

    def forget_frame(self, f):
        pass


def main() -> None:
    _app = wx.App(redirect=False)  # must stay referenced for the lifetime of the call
    from quilllite.window import DocumentFrame  # noqa: PLC0415

    fake = FakeApp()

    # What does the control do with a trailing newline?
    probe_frame = DocumentFrame(fake, mode=ed.PLAIN)
    probe_frame.Show()
    wx.Yield()
    e = probe_frame.editor
    for sample in ["a\n", "a\nb", "a\n\n", "", "\n"]:
        e.set_text(sample)
        got = e.get_text()
        check(f"set/get {sample!r}", got == sample, f"got {got!r}")
    probe_frame.modified = False
    probe_frame.Destroy()

    # The invariant that matters: open a file, save it unchanged, bytes identical.
    tmp = Path(tempfile.mkdtemp())
    samples = {
        "trailing_newline.txt": b"alpha content\r\n",
        "no_trailing.txt": b"one\r\ntwo\r\nthree",
        "blank_line_end.txt": b"a\r\n\r\n",
        "unix.txt": b"one\ntwo\n",
        "empty.txt": b"",
        "utf8_bom.txt": b"\xef\xbb\xbfcaf\xc3\xa9\r\n",
        "accents.txt": "café résumé\r\n".encode(),
    }
    for name, payload in samples.items():
        path = tmp / name
        path.write_bytes(payload)
        frame = DocumentFrame(fake, path=path, mode=ed.PLAIN)
        wx.Yield()
        frame.save()
        after = path.read_bytes()
        check(f"round trip {name}", after == payload, f"{payload!r} -> {after!r}")
        frame.modified = False
        frame.Destroy()

    # A save with no edit must not mark the document modified beforehand.
    path = tmp / "clean.txt"
    path.write_bytes(b"hello\r\n")
    frame = DocumentFrame(fake, path=path, mode=ed.PLAIN)
    wx.Yield()
    check("freshly opened file is not modified", not frame.modified)
    frame.modified = False
    frame.Destroy()

    print("\n".join([]))
    failures = [r for r in results if r.startswith("FAIL")]
    print(f"\n{len(results) - len(failures)} passed, {len(failures)} failed")


if __name__ == "__main__":
    main()
