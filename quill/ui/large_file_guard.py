"""Large-file open guard (#1150).

Opening a very large file used to freeze QUILL -- and the screen reader with it
-- because the file was read and pushed into the text control synchronously on
the UI thread. This module holds the small, wx-free decision logic: the size
threshold, a human-readable size, and the confirmation message. The wx dialog
and the background-read routing live in the open path (``MainFrame.open_file``),
which uses these helpers so the behaviour is unit-testable without a UI.
"""

from __future__ import annotations

#: At or above this size, warn before opening and read on a worker thread so
#: the UI (and the screen reader) stay responsive while the file loads.
LARGE_FILE_WARN_BYTES = 8 * 1024 * 1024  # 8 MiB


def is_large_file(size_bytes: int) -> bool:
    """True when *size_bytes* is large enough to warn about / read off-thread."""
    return size_bytes >= LARGE_FILE_WARN_BYTES


def human_size(size_bytes: int) -> str:
    """A compact human-readable size, e.g. ``"32.0 MB"`` or ``"1.4 GB"``."""
    size = float(size_bytes)
    for unit in ("bytes", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            if unit == "bytes":
                return f"{int(size)} bytes"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def large_file_warning(name: str, size_bytes: int) -> str:
    """The confirmation message shown before opening a large file."""
    return (
        f"{name} is {human_size(size_bytes)}. Opening a file this large may make "
        "QUILL -- and your screen reader -- unresponsive for a while as it loads. "
        "Open it anyway?"
    )
