"""QUILL's settings, changed where every open window will see them.

The family settings audit (2026-11-20) found QUILL dialogs that loaded a
fresh copy of the settings file, changed it and saved it: AI Hub's Services
page and image styles, the Assistant's setup strip and image prompts, the
Vision Prompt Manager, and the chapter workbench's nudge step. The main
window's own settings object never heard of the change, so

* it did not take effect until QUILL was restarted, and
* the window's next save -- any toggle, minutes later -- wrote its older copy
  of that field back over the file. The choice was gone, with nothing said.

So a window that owns QUILL's settings (``MainFrame``, every
``AppShellFrame``) :func:`register`\\ s itself, and such a dialog makes its
change with :func:`change_and_save`: the change lands on every live copy in
this process -- in effect at once -- and the first of them is saved. With no
window open (a test, a tool), it lands on a fresh load, as before.

Owners are held weakly, and read through their ``settings`` attribute each
time, so a window that replaces its settings object (Import Settings) is
still the one changed. wx-free, strict-typed.
"""

from __future__ import annotations

import threading
import weakref
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quill.core.settings import Settings

__all__ = ["change_and_save", "live_copies", "register"]

_lock = threading.Lock()
_owners: list[weakref.ref[object]] = []


def register(owner: object) -> None:
    """Make *owner*'s ``settings`` one of the copies every change reaches."""
    with _lock:
        _owners[:] = [ref for ref in _owners if ref() is not None and ref() is not owner]
        _owners.append(weakref.ref(owner))


def live_copies() -> list[Settings]:
    """Each open window's settings object, once each, in the order they registered."""
    from quill.core.settings import Settings

    with _lock:
        owners = [ref() for ref in _owners]
    copies: list[Settings] = []
    for owner in owners:
        settings = getattr(owner, "settings", None) if owner is not None else None
        if isinstance(settings, Settings) and not any(settings is c for c in copies):
            copies.append(settings)
    return copies


def change_and_save(change: Callable[[Settings], None]) -> Settings:
    """Apply *change* to every live copy (or a fresh load) and save; the saved copy.

    A failed write raises ``OSError`` after the shared persistence feedback has
    reported it, exactly as :func:`quill.core.settings.save_settings` does; the
    change stays in effect for this session either way.
    """
    from quill.core.settings import load_settings, save_settings

    copies = live_copies() or [load_settings()]
    for copy in copies:
        change(copy)
    save_settings(copies[0])
    return copies[0]


def _forget() -> None:
    """Tests only: no window is open."""
    with _lock:
        _owners.clear()
