"""Remember where the user stopped listening in each audiobook.

The two functions here are the long-standing API the Workbench player and the
standalone Media Player call. The store behind them now lives in
:mod:`quill.core.media.positions`, which keys a position by the file's
**contents** rather than its absolute path -- so a position survives moving the
file, and can cross to another machine or operating system, which a path key
never could.

Kept as a wrapper rather than rewritten at the call sites: the signature was
already the right one, and the portability is not something a caller should
have to know about. Positions saved by earlier versions are read under their
old path key and re-filed portably on the next save, so nobody loses their
place on upgrade.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.media.positions import PositionStore


def load_position_ms(data_dir: Path, book: Path) -> int:
    """The saved position for *book*, or 0 (start) when unknown/stale."""
    return PositionStore(data_dir).position_for(book)


def save_position_ms(data_dir: Path, book: Path, position_ms: int) -> None:
    """Record *position_ms* for *book* (oldest entries pruned; best-effort).

    A position at the very start clears the entry rather than storing it --
    "three seconds in" is the beginning, and offering to resume there is a
    prompt the listener has to dismiss for no benefit.
    """
    PositionStore(data_dir).remember(book, position_ms)


def clear_position(data_dir: Path, book: Path) -> None:
    """Forget *book*'s position -- it finished, or playback restarted."""
    PositionStore(data_dir).forget(book)


__all__ = ["clear_position", "load_position_ms", "save_position_ms"]
