"""A settings save whose failure is said, and never mistaken for success.

The family settings audit (2026-11-20) found QUILL Studio, Quill Media Player
and QUILL Transcribe catching a failed settings write and carrying on as if
it had worked -- ``except Exception: pass`` around the save, then "Preferences
saved". A choice that is gone at the next launch then sounds exactly like one
that was kept.

The write itself goes through :func:`quill.core.persistence_outcome.guarded_write`,
which tells the app's Activity window (once, with Retry and Open Folder, by
``quill.ui.persistence_reporting``). What is left for the call site is one
honest answer, and that is all this module gives it:

* :func:`saved` runs a save that is already guarded and answers whether it
  worked. ``False`` means the listener has been told; the caller must not
  claim the save, and must not say the failure a second time either.
* :func:`save_reported` guards a raw write and answers the same.

wx-free, strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from quill.core.persistence_outcome import guarded_write

__all__ = ["save_reported", "saved"]


def saved(save: Callable[[], None]) -> bool:
    """Run *save* (a guarded writer); ``False`` when it failed and was reported."""
    try:
        save()
    except OSError:
        return False
    return True


def save_reported(what: str, path: Path, write: Callable[[], None]) -> bool:
    """Guard *write* as *what* at *path*; ``False`` when it failed and was reported.

    *write* should serialise the live state as it runs, so that Retry --
    which runs it again -- writes what is current rather than a stale copy.
    """
    return saved(lambda: guarded_write(what, path, write))
