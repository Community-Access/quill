"""Startup profiler: cProfile + per-task wall-clock timing.

Launches Quill, collects cProfile data for the full startup sequence, waits for
the per-task timing file (written by QUILL_PROFILE_STARTUP=1), then closes the
app automatically and prints a summary.

Usage:
    python tools/profile_startup.py

Output files (repo root):
    startup_cprofile.txt   -- top-60 cumulative cProfile entries
    startup_tasks.txt      -- copy of per-task wall-clock breakdown
"""

from __future__ import annotations

import cProfile
import io
import os
import pstats
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

os.environ["QUILL_PROFILE_STARTUP"] = "1"


def _install_auto_close() -> None:
    """Patch MainFrame to close itself after deferred startup tasks complete."""
    from quill.ui import main_frame as mf

    _orig = mf.MainFrame._write_startup_timing

    def _patched(self: object, times: list[tuple[str, float]]) -> None:  # type: ignore[override]
        _orig(self, times)  # type: ignore[arg-type]
        # Close after writing the timing file so the data is on disk before exit.
        import wx

        wx.CallAfter(self.frame.Close)

    mf.MainFrame._write_startup_timing = _patched  # type: ignore[method-assign]


if __name__ == "__main__":
    _install_auto_close()

    pr = cProfile.Profile()
    pr.enable()

    from quill.ui.main_frame import run_app

    run_app()

    pr.disable()

    # Write cProfile report
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps.print_stats(60)
    cprofile_out = REPO_ROOT / "startup_cprofile.txt"
    cprofile_out.write_text(s.getvalue(), encoding="utf-8")
    print(f"cProfile report     -> {cprofile_out}")

    # Find and copy the per-task timing file written by _write_startup_timing
    from quill.core.paths import app_data_dir

    task_file = app_data_dir() / "logs" / "startup_tasks.txt"
    task_out = REPO_ROOT / "startup_tasks.txt"
    if task_file.exists():
        text = task_file.read_text(encoding="utf-8")
        task_out.write_text(text, encoding="utf-8")
        print(f"Task timing report  -> {task_out}")
        print()
        print(text)
    else:
        print(f"Warning: task timing file not found at {task_file}")
        print(f"  (QUILL_PROFILE_STARTUP was set; check that app_data_dir() = {app_data_dir()})")
