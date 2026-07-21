"""Entry point for ``python -m quill_radio_mac``.

Delegates to :func:`quill_radio_mac.app.main`, which owns the wx.App
bootstrap (safe mode, single frame, accessibility wiring). The import of
``quill_radio_mac.app`` -- and therefore of wx itself -- happens inside
the ``__main__`` guard, so merely importing this module (for example
during test collection, or via ``runpy`` introspection) never pulls in
wxPython. That keeps the package's wx-free import contract intact.

Threading contract: runs on the process's main thread; ``main()`` blocks
in the wx main loop until the app quits.

macOS notes: on macOS the process must be launched on the main thread for
AppKit to accept it as a GUI app; ``python -m quill_radio_mac`` from a
normal shell satisfies that.
"""

from __future__ import annotations

if __name__ == "__main__":
    from quill_radio_mac.app import main

    main()
