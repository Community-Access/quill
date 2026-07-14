"""``wx.App`` subclass that receives macOS "Open File" Apple Events.

Without this override, launching QUILL via Finder's "Open With" menu,
dragging a file onto the Dock icon, or running ``open -a Quill somefile.txt``
from Terminal never loads the file's content: on macOS those actions are
delivered to the running process as an ``NSApplication``
``openFile``/``application:openFile:`` Apple Event, not a ``sys.argv`` entry.
wxPython only surfaces that event through the ``wx.App.MacOpenFile`` /
``MacOpenFiles`` overrides -- the base ``wx.App`` used previously by
``quill.ui.main_frame.run_app`` did nothing with it, so QUILL launched into a
blank document as if no file had been requested at all.

``MacOpenFile``/``MacOpenFiles`` are Mac-only wx hooks; on Windows/Linux they
are simply never invoked, so this subclass is used unconditionally rather
than gated behind a platform check.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import wx  # type: ignore[import-not-found]

from quill.core.ipc import OpenRequest


class MacOpenFileApp(wx.App):
    """Buffers/dispatches Finder- or Terminal-originated file-open requests.

    ``main_frame`` is ``None`` until :func:`quill.ui.main_frame.run_app`
    finishes constructing the ``MainFrame`` and assigns it. A cold launch --
    QUILL not yet running, started by double-clicking a file in Finder --
    can deliver the Apple Event before that assignment happens, so any
    paths that arrive early are buffered and flushed once ``main_frame`` is
    set (see :meth:`flush_pending`).
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.main_frame: Any | None = None
        self._pending_paths: list[str] = []
        super().__init__(*args, **kwargs)

    def MacOpenFile(self, filename: str) -> None:  # noqa: N802 - wx override name
        self.MacOpenFiles([filename])

    def MacOpenFiles(self, filenames: list[str]) -> None:  # noqa: N802 - wx override name
        if self.main_frame is None:
            self._pending_paths.extend(filenames)
            return
        self._dispatch(filenames)

    def flush_pending(self) -> None:
        """Dispatch any paths buffered before ``main_frame`` was assigned."""
        if not self._pending_paths:
            return
        pending, self._pending_paths = self._pending_paths, []
        self._dispatch(pending)

    def _dispatch(self, filenames: list[str]) -> None:
        main_frame = self.main_frame
        if main_frame is None:
            return
        opened = False
        for raw_path in filenames:
            path = Path(raw_path).expanduser()
            if path.exists() and path.is_file():
                main_frame._handle_shell_request(OpenRequest(path=path.resolve()))
                opened = True
        if not opened:
            return
        # Mirrors the IPC secondary-instance path in main_frame's
        # ``_on_ipc_timer``: bring the already-running app to the front so
        # the newly opened document is visible immediately.
        frame = getattr(main_frame, "frame", None)
        if frame is not None:
            frame.Show(True)
            frame.Raise()
            frame.RequestUserAttention()
