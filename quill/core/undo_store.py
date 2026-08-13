from __future__ import annotations

from hashlib import sha1
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic


def load_undo_history(path: Path) -> list[str]:
    raw = read_json(_undo_path(path), default=[])
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, str)]


#: Total characters of history kept on disk for one document.
#:
#: The count limit alone is not a bound on anything that matters. A hundred
#: snapshots of a shopping list is nothing; a hundred snapshots of a 1 MB
#: manuscript is 100 MB, held in memory *and* rewritten in full every few
#: seconds while you type, because the whole history is one JSON file. The cost
#: scales with the document, which is exactly backwards -- the longer the piece
#: you are working on, the heavier every keystroke gets.
#:
#: Eight million characters keeps the full hundred steps for anything up to
#: ~80 KB, which is most documents, and degrades by keeping fewer steps rather
#: than by writing more. Deep undo on a huge document is the thing worth giving
#: up; a responsive editor is not.
MAX_HISTORY_CHARS = 8_000_000


def bound_history(
    history: list[str], limit: int = 100, max_chars: int = MAX_HISTORY_CHARS
) -> list[str]:
    """The newest snapshots that fit in both budgets, oldest first.

    Always returns at least the newest snapshot when there is one, even if that
    single snapshot is larger than *max_chars*: a history of nothing would mean
    Ctrl+Z does nothing at all, which is a worse answer than one large entry.
    """
    bounded = history[-max(limit, 1) :]
    if not bounded:
        return []
    kept: list[str] = []
    total = 0
    for snapshot in reversed(bounded):
        if kept and total + len(snapshot) > max_chars:
            break
        kept.append(snapshot)
        total += len(snapshot)
    kept.reverse()
    return kept


def save_undo_history(
    path: Path,
    history: list[str],
    limit: int = 100,
    max_chars: int = MAX_HISTORY_CHARS,
) -> list[str]:
    """Persist *history*, trimmed to the newest entries that fit the budgets.

    Returns what was actually written so the caller can keep its in-memory copy
    in step -- otherwise the editor would hold snapshots that no longer exist on
    disk and offer undo steps that vanish on reopen.
    """
    bounded = bound_history(history, limit, max_chars)
    write_json_atomic(_undo_path(path), bounded)
    return bounded


def save_and_reanchor(path: Path, history: list[str], index: int) -> tuple[list[str], int]:
    """Persist *history*, and report what survived plus where *index* now points.

    The budget drops snapshots from the **front**, so a caller holding a cursor
    into the list has to move it by however many went. Getting that wrong is not
    a crash, which is what makes it worth having in one place with a test: the
    index would silently point at the wrong snapshot, and the next Ctrl+Z would
    restore text from somewhere else in your history.
    """
    bounded = save_undo_history(path, history)
    return bounded, max(0, index - (len(history) - len(bounded)))


def clear_undo_history(path: Path) -> None:
    target = _undo_path(path)
    if target.exists():
        target.unlink()


def _undo_path(path: Path) -> Path:
    digest = sha1(str(path.resolve()).encode("utf-8")).hexdigest()
    return app_data_dir() / "undo" / f"{digest}.json"
