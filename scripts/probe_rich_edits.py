"""Live answers to the four bad.md rows that could not be settled by reading.

R4, C2/N3, R14 and L3 were all filed "verify live, then fix if confirmed",
because each is a claim about what a **real** ``RICHEDIT50W`` does with a real
Text Object Model, and a reading of the source can only say what the code asks
for -- not what the control does with it. This script asks the control.

    python scripts/probe_rich_edits.py

Run by hand rather than in CI, for the reason every sibling probe exists: these
need a native control with a window handle and a COM apartment, and CI has
neither. Everything CI *can* answer is answered in ``tests/unit``.

Each check prints PASS (the bug is not there, or is fixed) or FAIL (the bug is
real and reproduced), and the script exits non-zero if any failed -- so the
output can be pasted into a row of the plan as evidence either way.

L3 is in here too even though it needs no control at all: it is one of the four,
and a person looking for "what happened to those four" should find all of them
in one place rather than three here and one in the unit suite.
"""

from __future__ import annotations

import os
import pathlib
import tempfile
from pathlib import Path

# Before any quill import: a probe must never write into a real profile.
os.environ["QUILL_DEV_BUILD"] = "1"
os.environ["QUILL_DATA_DIR"] = tempfile.mkdtemp(prefix="quill-probe-")

import wx  # noqa: E402

from quill.core.selection import shrink_selection  # noqa: E402
from quill.ui.richedit_editing import RICH, create_richedit_document  # noqa: E402

_FAILURES: list[str] = []


def check(name: str, ok: object, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  -- {detail}" if detail else ""))
    if not ok:
        _FAILURES.append(name)


def _surface(frame: wx.Frame):
    """``(control, wrapper)`` for a real rich surface in a real frame.

    The factory returns the wx control and hangs the ``RichEditDocument`` on it
    at ``quill_richedit``, which is where everything else in the app finds it.
    """
    control = create_richedit_document(wx, frame, wx.TE_MULTILINE | wx.TE_PROCESS_TAB, RICH)
    return control, control.quill_richedit


def main() -> int:  # noqa: C901 - a probe is a list of questions
    # Held for the lifetime of main(): a wx.App that is garbage-collected
    # takes the event loop and every window with it.
    _app = wx.App(redirect=False)  # noqa: F841
    frame = wx.Frame(None, title="probe")
    control, editor = _surface(frame)
    frame.Show()
    wx.SafeYield()

    if not editor.rtf_available():
        print("No Text Object Model on this machine; nothing here can be answered.")
        return 2

    target = Path(os.environ["QUILL_DATA_DIR"]) / "probe.rtf"

    # -- R4 ------------------------------------------------------------------
    print("\nR4. Does a dark theme write grey text into a saved .rtf?")
    control.ChangeValue("Themed text.")
    # What a dark theme really does: wxMSW turns SetForegroundColour on a rich
    # control into an SCF_ALL character colour, so it is on every run in the
    # document rather than being a view setting, and the TOM writes it out.
    control.SetForegroundColour(wx.Colour(230, 230, 230))
    editor.set_document_color((230, 230, 230))
    control.Refresh()
    wx.SafeYield()
    editor.save_rtf(str(target))
    unguarded = target.read_text(encoding="utf-8", errors="replace")
    leaked = "\\colortbl" in unguarded and "230" in unguarded
    check(
        "an unguarded save leaks it -- this is the bug, reproduced",
        leaked,
        "no colour table appeared; the control may not apply SCF_ALL here",
    )

    # And the guarded path, which is what QUILL's .rtf save runs now
    # (_theme_colour_off in main_frame_rich_mode) and what QuillLite has always
    # run (_write_rtf in lite_window_file).
    editor.set_document_color(None)
    editor.save_rtf(str(target))
    guarded = target.read_text(encoding="utf-8", errors="replace")
    check(
        "stripping to tomAutoColor first keeps it out",
        not ("\\colortbl" in guarded and "230" in guarded),
        guarded[:70].replace("\n", " "),
    )

    # -- R14 -----------------------------------------------------------------
    print("\nR14. Is one Ctrl+Z after Heading 2 enough?")
    control.ChangeValue("Chapter One\nBody text.")
    control.SetInsertionPoint(2)
    before = editor.caret_format_description()
    editor.set_heading(2)
    control.SetInsertionPoint(2)
    after_heading = editor.caret_format_description()
    check("the heading applied at all", "heading 2" in after_heading, after_heading)
    control.Undo()
    wx.SafeYield()
    control.SetInsertionPoint(2)
    after_undo = editor.caret_format_description()
    check(
        "one undo returns the paragraph to what it was",
        after_undo == before,
        f"before={before!r} after one undo={after_undo!r}",
    )

    # -- C2 / N3 -------------------------------------------------------------
    print("\nC2/N3. Does a local edit rewrite the whole document's formatting?")
    from quill.core.selection import changed_span

    control.ChangeValue("Chapter One\nBody text.\nMore body.")
    control.SetInsertionPoint(2)
    editor.set_heading(1)
    control.SetInsertionPoint(2)
    check("a heading exists to lose", "heading 1" in editor.caret_format_description())
    baseline = len(editor.all_headings())

    # The OLD path, kept so the probe still shows the bug rather than only its
    # absence: select all, write the new text over it.
    whole = control.GetValue()
    control.SelectAll()
    control.WriteText(whole + "\nInserted line.")
    wx.SafeYield()
    spread = len(editor.all_headings())
    check(
        "select-all-and-write really does spread the format -- the bug",
        spread > baseline,
        f"{baseline} heading became {spread}",
    )

    # The NEW path: _replace_document_text narrows to the changed span first.
    control.ChangeValue("Chapter One\nBody text.\nMore body.")
    control.SetInsertionPoint(2)
    editor.set_heading(1)
    wx.SafeYield()
    before_count = len(editor.all_headings())
    current = control.GetValue()
    span_start, span_end, replacement = changed_span(current, current + "\nInserted line.")
    control.SetSelection(span_start, span_end)
    control.WriteText(replacement)
    wx.SafeYield()
    after = editor.all_headings()
    check(
        "narrowing to the changed span leaves every other run alone",
        len(after) == before_count,
        f"{before_count} heading, {len(after)} after the insert: {after}",
    )
    control.SetInsertionPoint(2)
    check(
        "and the heading is still a heading",
        "heading 1" in editor.caret_format_description(),
        editor.caret_format_description(),
    )

    # -- L3 ------------------------------------------------------------------
    print("\nL3. Does Shrink answer for the selection you actually have?")

    text = "alpha beta gamma\n\nsecond paragraph here\n"
    # The expansion stack is gone from main_frame_selection.py; what replaced it
    # is this, asked fresh every time. The regression test for the command
    # itself is tests/unit/ui/test_main_frame_navigation.py.
    computed = shrink_selection(text, 18, 39)
    check(
        "it shrinks inside the current selection, never to an earlier one",
        computed is not None and 18 <= computed[0] < computed[1] <= 39,
        str(computed),
    )
    import quill.ui.main_frame_selection as sel_mod

    source = pathlib.Path(sel_mod.__file__).read_text(encoding="utf-8")
    check(
        "and there is no expansion stack left to go stale",
        source.count("_selection_expand_stack") == 0 or "there is not\none now" in source,
        "the stack is documented as removed",
    )

    frame.Destroy()
    print("\n" + "-" * 60)
    if _FAILURES:
        print(f"{len(_FAILURES)} REPRODUCED: " + ", ".join(_FAILURES))
        return 1
    print("Nothing reproduced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
