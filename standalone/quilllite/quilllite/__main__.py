"""python -m quilllite [--rich | --plain] [--check] [file ...]

--check writes a diagnostic to %LOCALAPPDATA%\\QuillLite\\check.log and exits
without opening a window. Useful for a support question, and the only way to
smoke test a frozen build without disturbing a running copy.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    mode: str | None = None
    check = False
    paths: list[Path] = []
    for arg in argv:
        if arg == "--check":
            check = True
        elif arg == "--rich":
            mode = "rich"
        elif arg == "--plain":
            mode = "plain"
        elif arg in {"-h", "--help"}:
            print(__doc__)
            return 0
        else:
            paths.append(Path(arg))

    import wx  # noqa: PLC0415

    from quilllite import APP_NAME  # noqa: PLC0415
    from quilllite.app import QuillLiteApp, hand_over_to_running_instance  # noqa: PLC0415

    if check:
        return _run_check()

    # One process for every window: a second launch hands its files to the
    # first and exits, so opening a file from Explorer is instant.
    checker = wx.SingleInstanceChecker(f"{APP_NAME}-{wx.GetUserId()}")
    if checker.IsAnotherRunning():
        if hand_over_to_running_instance(paths, mode):
            return 0
    app = QuillLiteApp(paths, mode)
    app.MainLoop()
    del checker
    return 0


def _run_check() -> int:
    """Report what this build can do, to stdout and to check.log."""
    import wx  # noqa: PLC0415

    from quilllite import APP_NAME, __version__, speech  # noqa: PLC0415
    from quilllite import editor as editor_mod  # noqa: PLC0415
    from quilllite.paths import data_dir  # noqa: PLC0415

    _app = wx.App(redirect=False)  # must stay referenced for the lifetime of the call
    frame = wx.Frame(None)
    editor = editor_mod.create_editor(wx, frame, editor_mod.RICH)
    lines = [
        f"{APP_NAME} {__version__}",
        f"frozen: {getattr(sys, 'frozen', False)}",
        f"python: {sys.version.split()[0]}",
        f"wxPython: {wx.version()}",
        f"native rich edit: {editor.native()}",
        f"text mode: {editor.current_native_mode()}",
        f"screen reader: {speech.backend_name()}",
        f"data dir: {data_dir()}",
    ]
    try:
        editor.set_text("check")
        editor.set_heading(1)
        lines.append(f"heading applied: {editor.heading_level_at_caret() == 1}")
        lines.append(f"describe: {editor.describe_caret()}")
    except Exception as exc:  # noqa: BLE001
        lines.append(f"heading check failed: {exc}")
    frame.Destroy()
    report = "\n".join(lines)
    try:
        (data_dir() / "check.log").write_text(report + "\n", encoding="utf-8")
    except OSError:
        pass
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
