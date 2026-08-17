"""One-shot background workers for the Audio Studio UI (GATE-40 audited).

The Studio's panels run short, fire-and-forget scans — a folder count, a
selection preview — whose results land on the UI thread via ``wx.CallAfter``
and are simply discarded when the panel is gone. They deliberately do not ride
:class:`~quill.stability.task_manager.QuillTaskManager`: these are sub-second,
uncancellable-by-design lookups, and pooling them would let one slow disk walk
queue behind unrelated work. Centralised here so the exemption is audited once
instead of re-argued at every call site.
"""

from __future__ import annotations

import threading
from collections.abc import Callable


def run_one_shot(target: Callable[[], None], name: str) -> None:
    """Run *target* on a named daemon thread (CallAfter marshals results)."""
    threading.Thread(  # GATE-40-OK: audited one-shot pattern; see module docstring
        target=target, name=name, daemon=True
    ).start()
