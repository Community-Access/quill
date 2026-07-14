"""Thread-stack dump, fault handler, and environment summary helpers.

Implements: ROADMAP STAB-3 (the ``dump_all_thread_stacks`` /
``setup_fault_handler`` primitives the crash-bundle builder and the
heartbeat watchdog call when the main thread appears stuck) and the
``collect_environment_info`` snapshot the About dialog and the
diagnostic bundle share.
"""

from __future__ import annotations

import faulthandler
import platform
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import TextIO

from quill.core.paths import app_data_dir, ensure_app_directories

_OPEN_HANDLES: list[TextIO] = []


def _diagnostics_dir() -> Path:
    ensure_app_directories()
    return app_data_dir() / "diagnostics"


def close_diagnostic_handles() -> None:
    """Close all open fault-handler file handles. Call before shutdown."""
    while _OPEN_HANDLES:
        handle = _OPEN_HANDLES.pop()
        try:
            handle.close()
        except Exception:
            pass


def setup_fault_handler() -> Path:
    diagnostics_dir = _diagnostics_dir()
    diagnostics_dir.mkdir(parents=True, exist_ok=True)
    dump_file = diagnostics_dir / f"quill-faulthandler-{int(time.time())}.log"
    # Close the previous handle before enabling a new one so handles don't
    # accumulate over the lifetime of a long-running session.
    if _OPEN_HANDLES:
        try:
            faulthandler.cancel_dump_traceback_later()
        except Exception:
            pass
        close_diagnostic_handles()
    handle = dump_file.open("a", encoding="utf-8")
    _OPEN_HANDLES.append(handle)
    faulthandler.enable(file=handle, all_threads=True)
    faulthandler.dump_traceback_later(30, repeat=True, file=handle, exit=False)
    return dump_file


def dump_all_thread_stacks(reason: str) -> Path:
    diagnostics_dir = _diagnostics_dir()
    diagnostics_dir.mkdir(parents=True, exist_ok=True)
    dump_file = diagnostics_dir / f"quill-thread-dump-{int(time.time())}.log"
    frames = sys._current_frames()

    with dump_file.open("w", encoding="utf-8") as handle:
        handle.write("QUILL thread dump\n")
        handle.write(f"Reason: {reason}\n")
        handle.write(f"Python: {sys.version}\n")
        handle.write(f"Platform: {platform.platform()}\n\n")
        for thread in threading.enumerate():
            handle.write("=" * 80 + "\n")
            handle.write(f"Thread: {thread.name} ident={thread.ident} daemon={thread.daemon}\n")
            # ``thread.ident`` is documented as ``int | None`` (None for
            # synthetic threads without a real OS thread id). Skip those
            # here -- the frames dict is keyed on the int ident.
            ident = thread.ident
            if ident is None:
                handle.write("No Python frame available (no OS ident).\n\n")
                continue
            frame = frames.get(ident)
            if frame is None:
                handle.write("No Python frame available.\n\n")
                continue
            handle.write("".join(traceback.format_stack(frame)))
            handle.write("\n")

    return dump_file
