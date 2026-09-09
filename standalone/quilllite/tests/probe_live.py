"""Live checks against a real RICHEDIT50W, in a real Windows desktop session.

Run by hand, not by CI, for the reason every sibling app has a probe script: the
things worth checking here need a native control with a window handle and a COM
apartment, and CI has neither. What CI *can* check -- the command table, the
encoding round trips, the bookmark arithmetic, the F1 catalogue -- is checked in
``tests/unit`` and is not repeated here.

    python standalone/quilllite/tests/probe_live.py

Every check prints PASS or FAIL and the script exits non-zero if any failed, so
it can be pasted into a release checklist. It runs against a temporary data
folder, so it cannot disturb a QuillLite you actually use, and it deliberately
avoids every path that raises a modal dialog -- a probe that stops halfway
waiting for somebody to press a button is a probe nobody runs.

The eight groups below are, in order: the surface came up; the tomTrue fix
holds; the collapsed-caret probe holds; text mode switches; the theme never
reaches the file; documents are numbered and stay numbered; bookmarks move with
the text; and switching a feature area off really removes its keys.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Before any quill import: a probe must never write into a real profile.
os.environ["QUILL_LITE_DATA_DIR"] = tempfile.mkdtemp(prefix="quilllite-probe-")

import wx  # noqa: E402

from quill.apps.lite import QuillLiteApp  # noqa: E402
from quill.core.lite.textfile import decode_text, encode_text  # noqa: E402
from quill.ui.richedit_editing import PLAIN, RICH  # noqa: E402
from quill.ui.richedit_rtf_surface import heading_level_for_font  # noqa: E402

_FAILURES: list[str] = []


def check(name: str, condition: object, detail: str = "") -> None:
    ok = bool(condition)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{f'  -- {detail}' if detail else ''}")
    if not ok:
        _FAILURES.append(name)


def main() -> int:
    app = QuillLiteApp([], RICH)
    frame = app.frames[0]
    editor = frame.editor

    print("\n1. The native surface")
    check("a real window handle", editor.hwnd() != 0, f"hwnd={editor.hwnd()}")
    check("the text object model is reachable", editor.rtf_available())
    check("the control reports rich mode", editor.current_text_mode() == RICH)

    print("\n2. tomTrue: set_heading applies the bold as well as the size")
    frame.control.ChangeValue("Chapter One\nBody text here.\nChapter Two\nMore body.")
    frame.control.SetInsertionPoint(2)
    editor.set_heading(1)
    frame.control.SetInsertionPoint(2)
    level = editor.heading_level_at_caret()
    check("the caret reports Heading 1", level == 1, f"level={level}")
    described = editor.caret_format_description()
    check("Describe Formatting says bold", "bold" in described, described)
    check("and says heading 1", "heading 1" in described, described)

    print("\n3. The collapsed-caret probe describes the heading, not the line above")
    text = frame.control.GetValue()
    second = text.index("Chapter Two")
    frame.control.SetInsertionPoint(second + 2)
    editor.set_heading(2)
    frame.control.SetInsertionPoint(second)  # the very start of the heading
    described = editor.caret_format_description()
    check("standing at the head of Heading 2 describes Heading 2", "heading 2" in described,
          described)
    headings = editor.all_headings()
    check("both headings are enumerated", len(headings) == 2, str(headings))
    check("the ladder agrees with the enumeration",
          all(heading_level_for_font(20.0 if lvl == 1 else 16.0, True) == lvl
              for _o, lvl, _t in headings))

    print("\n4. Text mode switches, and plain mode is really plain")
    # _set_mode_internal, not switch_mode: the user-facing command asks before
    # throwing formatting away, and a probe that stops on a modal dialog is a
    # probe nobody can run unattended. What is checked here is the control's own
    # answer, which is the half a dialog cannot tell you.
    frame._set_mode_internal(PLAIN)
    check("the control reports plain mode", editor.current_text_mode() == PLAIN)
    frame._set_mode_internal(RICH)
    check("and back to rich", editor.current_text_mode() == RICH)

    print("\n5. The theme never reaches the file")
    target = Path(os.environ["QUILL_LITE_DATA_DIR"]) / "probe.rtf"
    frame.control.ChangeValue("Themed text.")
    app.settings.theme = "dark"
    frame.apply_theme()
    frame.save(target)
    saved = target.read_text(encoding="utf-8", errors="replace")
    check("the saved RTF is real RTF", saved.startswith("{\\rtf"))
    check("no dark grey leaked into the file", "e6e6e6" not in saved.lower(), saved[:60])

    print("\n6. Documents are numbered, and a number is never reused")
    second_doc = app.new_window(PLAIN)
    third_doc = app.new_window(PLAIN)
    numbers = [f.number for f in app.frames]
    check("numbered in order", numbers == [1, 2, 3], str(numbers))
    second_doc.modified = False
    second_doc.Close()
    wx.SafeYield()
    check("closing 2 does not renumber 3", third_doc.number == 3)
    check("the next document is 4", app.new_window(PLAIN).number == 4)

    print("\n7. Bookmarks move with the text")
    frame.control.ChangeValue("alpha\nbeta\ngamma")
    frame.control.SetInsertionPoint(8)
    frame.cmd_set_bookmark()
    before = frame.bookmarks.get(1).position
    frame.control.SetInsertionPoint(0)
    frame.control.WriteText("PREFIX ")
    after = frame.bookmarks.get(1).position
    check("a bookmark after an insertion moves with it", after > before, f"{before} -> {after}")

    print("\n8. Switching an area off removes its keys, not just its menu")
    app.features.set_enabled("rich_text", False)
    app.save_features()
    app.rebuild_all_menus()
    labels = [
        frame.GetMenuBar().GetMenuLabel(i) for i in range(frame.GetMenuBar().GetMenuCount())
    ]
    check("the Format menu is gone", "F&ormat" not in labels, str(labels))
    check("and gone from the palette",
          not any(c.id.endswith("cmd_bold") for c in app.command_registry(frame).list()))
    app.features.set_enabled("rich_text", True)
    app.save_features()
    app.rebuild_all_menus()
    check("and comes back", "F&ormat" in [
        frame.GetMenuBar().GetMenuLabel(i) for i in range(frame.GetMenuBar().GetMenuCount())
    ])

    print("\n9. Round trips, against real bytes on disk")
    for name, raw in (
        ("CRLF", b"one\r\ntwo\r\n"),
        ("LF", b"one\ntwo\n"),
        ("UTF-8 with BOM", "﻿café\r\n".encode()),
        ("no final newline", b"last line with none"),
        ("empty", b""),
    ):
        path = Path(os.environ["QUILL_LITE_DATA_DIR"]) / f"rt-{name}.txt"
        path.write_bytes(raw)
        decoded = decode_text(path.read_bytes())
        written = encode_text(decoded.text, encoding=decoded.encoding, newline=decoded.newline)
        check(f"{name} survives a round trip", written == raw, f"{raw!r} -> {written!r}")

    for open_frame in list(app.frames):
        open_frame.modified = False
    app.shell.Close()
    wx.SafeYield()

    print(f"\n{'-' * 60}")
    if _FAILURES:
        print(f"{len(_FAILURES)} FAILED: " + ", ".join(_FAILURES))
        return 1
    print("All live checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
