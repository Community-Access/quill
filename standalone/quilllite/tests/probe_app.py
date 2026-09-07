"""App-level probe: multiple windows, single-instance handover, recovery.

Windows only, run in the interactive desktop session.
"""

from __future__ import annotations

import os
import tempfile

# Point every QuillLite path at a throwaway directory BEFORE importing the
# package: paths.data_dir() reads LOCALAPPDATA at call time. Without this a
# probe shares settings, the inbox and the recovery folder with a copy of
# QuillLite the user has open, and can delete their unsaved work.
os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="quilllite-probe-")

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import wx  # noqa: E402

from quilllite import recovery  # noqa: E402
from quilllite.app import QuillLiteApp, hand_over_to_running_instance  # noqa: E402
from quilllite.editor import PLAIN, RICH  # noqa: E402
from quilllite.paths import inbox_dir  # noqa: E402

results: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    line = f"{'PASS' if ok else 'FAIL'} {name} {detail}".rstrip()
    results.append(line)
    print(line, flush=True)


def main() -> None:

    tmp = Path(tempfile.mkdtemp())
    alpha = tmp / "alpha.txt"
    alpha.write_text("alpha content\r\n", encoding="utf-8")
    bravo = tmp / "bravo.rtf"

    app = QuillLiteApp([alpha], None)
    outcome: dict = {}

    def body() -> None:
        try:
            run_checks(app, tmp, alpha, bravo)
        except Exception as exc:  # noqa: BLE001
            outcome["error"] = repr(exc)
        finally:
            for frame in list(app.frames):
                frame.modified = False
                frame.Close()
            app.ExitMainLoop()

    wx.CallLater(300, body)
    app.MainLoop()
    if "error" in outcome:
        print("ERROR", outcome["error"])
    print("\n".join([]))
    failures = [r for r in results if r.startswith("FAIL")]
    print(f"\n{len(results) - len(failures)} passed, {len(failures)} failed")


def run_checks(app, tmp: Path, alpha: Path, bravo: Path) -> None:
    wx.Yield()
    check("one window for one file", len(app.frames) == 1, str(len(app.frames)))
    check(
        "window loaded the file",
        app.frames[0].editor.get_text().startswith("alpha"),
        repr(app.frames[0].editor.get_text()),
    )
    check("window is a top level frame", app.frames[0].GetParent() is None)
    check("plain mode for .txt", app.frames[0].editor.mode == PLAIN)

    # A second window is a separate top-level frame, not a tab.
    second = app.new_window(RICH)
    wx.Yield()
    check("two windows", len(app.frames) == 2, str(len(app.frames)))
    check("second window independent", second is not app.frames[0] and second.GetParent() is None)
    check("second window is rich", second.editor.mode == RICH)
    titles = [f.GetTitle() for f in app.frames]
    check("titles name mode", "plain text" in titles[0] and "rich text" in titles[1], str(titles))

    # Window menu lists both, with Alt+n keys.
    menu_labels = [
        second._window_menu.FindItemById(i).GetItemLabel() for i in second._window_menu_items
    ]
    check(
        "window menu lists both",
        len(menu_labels) == 2 and "Alt+1" in menu_labels[0],
        str(menu_labels),
    )

    # Opening the same file again focuses the existing window instead of duplicating.
    app.open_path(alpha)
    wx.Yield()
    check("no duplicate window for same file", len(app.frames) == 2, str(len(app.frames)))

    # Single-instance handover: write a request, let the poll timer pick it up.
    charlie = tmp / "charlie.txt"
    charlie.write_text("charlie", encoding="utf-8")
    hand_over_to_running_instance([charlie], None)
    check(
        "handover wrote a request file",
        bool(list(inbox_dir().glob("*.req"))),
        str([p.name for p in inbox_dir().glob("*")]),
    )
    check("inbox timer is running", app._inbox_timer.IsRunning())
    deadline = time.time() + 8
    while time.time() < deadline and len(app.frames) < 3:
        wx.MilliSleep(50)
        wx.YieldIfNeeded()
    check("inbox timer opened a third window", len(app.frames) == 3, str(len(app.frames)))
    check("handover consumed the request", not list(inbox_dir().glob("*.req")))
    if len(app.frames) < 3:
        raise SystemExit("cannot continue without the third window")

    # Recovery: modify a window, let the autosave write, confirm a slot exists.
    target = app.frames[2]
    target.editor.control.AppendText(" edited")
    wx.Yield()
    check("edit marks modified", target.modified)
    check("edit created a recovery slot", target._slot is not None)
    target._write_recovery_copy()
    pending = recovery.pending()
    check("recovery slot on disk", len(pending) == 1, str([p.title for p in pending]))
    check(
        "recovery content correct",
        pending and "edited" in pending[0].content_path.read_text(encoding="utf-8"),
    )

    # Saving clears the slot.
    target.save()
    wx.Yield()
    check("save cleared the slot", target._slot is None and not recovery.pending())
    check(
        "saved file on disk",
        charlie.read_text(encoding="utf-8").endswith("edited"),
        repr(charlie.read_text(encoding="utf-8")),
    )

    # Rich save through Save As path.
    rich = app.frames[1]
    rich.editor.control.AppendText("Heading here")
    rich.editor.control.SetInsertionPoint(0)
    rich.editor.set_heading(1)
    ok = rich.save(bravo)
    check("rich save as rtf", ok and bravo.exists() and bravo.read_bytes().startswith(b"{\\rtf"))
    check("rich file has heading weight", b"\\b" in bravo.read_bytes())

    # Closing one window leaves the others alone.
    closing = app.frames[0]
    closing.modified = False
    closing.Close()
    wx.Yield()
    check("closing one window leaves the rest", len(app.frames) == 2, str(len(app.frames)))


if __name__ == "__main__":
    main()
