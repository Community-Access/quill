"""A settings file that could not be read: keep it, start safely, and say so.

plan.md (settings review): Inkwell's loader raised ``ValueError`` on
``schema_version="invalid"`` and Weather's raised ``OverflowError`` on
``refresh_minutes: 1e309`` -- readable JSON, unusable values -- and the apps
call those loaders while they are being built, with nothing to catch them.

The recovery is the same everywhere, so it lives here:

* **Keep the file.** Its bytes are copied beside it, as
  ``<name>.damaged-<time>.json``, before anything can save over it. Once per
  file per launch: Weather reads its settings from several places.
* **Start safely.** The loader goes on with defaults for what it could not
  use; that is the caller's half.
* **Say so, once.** :func:`take_notice` hands the app one sentence, naming the
  copy, to announce when its window is up. Saying it is the point: a choice
  that silently went back to its default is the failure this replaces.

wx-free, strict-typed. Never raises: recovery that can fail is not recovery.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = ["announce_later", "keep_damaged", "take_notice"]

_lock = threading.Lock()
#: File -> the copy made this launch (``None`` when the copy failed).
_kept: dict[Path, Path | None] = {}
#: App label -> the sentence still to be said.
_notices: dict[str, str] = {}


def keep_damaged(path: Path, *, app: str, what: str = "settings") -> Path | None:
    """Copy the damaged *path* aside and queue the sentence *app* will say.

    Returns the copy, or ``None`` when it could not be made (the sentence then
    says the file was left where it is).
    """
    key = path.resolve() if path.exists() else path
    with _lock:
        if key in _kept:
            return _kept[key]
    copy: Path | None = None
    try:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        copy = path.with_name(f"{path.stem}.damaged-{stamp}{path.suffix}")
        copy.write_bytes(path.read_bytes())
    except OSError as error:
        logger.warning("QUILL-SETTINGS-RECOVERY: could not keep %s (%s)", path.name, error)
        copy = None
    logger.warning("QUILL-SETTINGS-RECOVERY: %s had values %s could not use", path.name, app)
    if copy is not None:
        sentence = (
            f"Some of your {app} {what} could not be read, so {app} is using its "
            f"defaults for them. Your file was kept as {copy.name}, in {copy.parent}."
        )
    else:
        sentence = (
            f"Some of your {app} {what} could not be read, so {app} is using its "
            f"defaults for them. The file {path.name} was left in {path.parent}."
        )
    with _lock:
        _kept[key] = copy
        _notices.setdefault(app, sentence)
    return copy


def take_notice(app: str) -> str:
    """The sentence for *app* to say, once; ``""`` when nothing was recovered."""
    with _lock:
        return _notices.pop(app, "")


def announce_later(
    app: str, announce: Callable[[str], None], call_after: Callable[..., object]
) -> None:
    """Have *app* say its recovery sentence once its window is up, if it has one."""
    if notice := take_notice(app):
        call_after(announce, notice)


def _forget() -> None:
    """Tests only: start a fresh launch."""
    with _lock:
        _kept.clear()
        _notices.clear()
