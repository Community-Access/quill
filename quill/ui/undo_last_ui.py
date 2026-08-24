"""Ctrl+Z in Quill Radio and QUILL Cast: take back the last destructive step.

The wx-facing half of :mod:`quill.core.undo_last`. Two things live here that
the pure module deliberately does not know about:

**A process-wide slot.** The verbs that need undoing are spread across
dialogs -- Unsubscribe is in the Podcast Manager, Delete Recording is in the
Recordings window, Mark All as Played is on a context menu three windows from
the frame. Threading a slot reference through all of them would be a lot of
plumbing to say one thing, so the slot is module state, claimed by whichever
app frame calls :func:`activate` at startup. One app runs per process, so
there is exactly one slot and exactly one owner.

**An off switch that matters.** QUILL itself does *not* activate: its Ctrl+Z
is the editor's undo and always will be. That is not merely a keybinding
difference -- :func:`hold_or_delete` moves deleted files aside only while a
consumer is active, so in QUILL a delete stays a delete and no bytes are held
by a slot nobody can reach.

The offer is spoken, not merely available: every verb that remembers an undo
ends its own announcement with "Ctrl+Z undoes this", because an undo you do
not know about is not an undo.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from quill.core.undo_last import (
    HELD_DIR_NAME,
    UndoableAction,
    UndoSlot,
    discard_held,
    hold_files,
    restore_held,
)

#: Set by :func:`activate`; None in QUILL, which owns Ctrl+Z for the editor.
_slot: UndoSlot | None = None
_data_dir: Path | None = None

#: The tail every undoable announcement ends with, so the offer is heard.
OFFER_TAIL = "Ctrl+Z undoes this."


def activate(data_dir: Path) -> UndoSlot:
    """Claim the slot for this app, holding deleted files under *data_dir*."""
    global _slot, _data_dir
    _slot = UndoSlot()
    _data_dir = data_dir
    # A holding folder left behind by a crash is one step of deletions nobody
    # can reach any more: clear it on the way in rather than growing it.
    sweep_holding_dir()
    return _slot


def is_active() -> bool:
    """True when an app owns Ctrl+Z for undo (Radio and Cast; not QUILL)."""
    return _slot is not None


def slot() -> UndoSlot | None:
    return _slot


def holding_dir() -> Path | None:
    """Where a deletion's files wait until the step is displaced."""
    if _data_dir is None:
        return None
    return _data_dir / HELD_DIR_NAME


def sweep_holding_dir() -> None:
    """Empty the holding folder (startup, and after the slot is disposed)."""
    directory = holding_dir()
    if directory is None or not directory.exists():
        return
    for path in directory.iterdir():
        try:
            if path.is_file():
                path.unlink(missing_ok=True)
        except OSError:
            continue


def remember(
    verb: str,
    subject: str,
    restores: str,
    undo: Callable[[], None],
    *,
    caveat: str = "",
    dispose: Callable[[], None] | None = None,
) -> bool:
    """Hold one undoable step. False (and nothing held) when no app owns undo."""
    if _slot is None:
        return False
    _slot.remember(
        UndoableAction(
            verb=verb,
            subject=subject,
            restores=restores,
            undo=undo,
            caveat=caveat,
            dispose=dispose,
        )
    )
    return True


def offer(sentence: str) -> str:
    """*sentence* with the undo offer appended, when undo is available.

    In QUILL (no slot) the sentence is returned untouched, so the shared
    action code can say the same thing in both places without claiming a key
    that does something else there.
    """
    if _slot is None:
        return sentence
    text = sentence.rstrip()
    if text and not text.endswith((".", "!", "?")):
        text += "."
    return f"{text} {OFFER_TAIL}".strip()


def hold_or_delete(paths: list[Path]) -> dict[Path, Path]:
    """Move *paths* aside so Ctrl+Z can bring them back -- or delete them.

    Returns the held mapping (empty when nothing was held). With no active
    slot, or no data directory, the files are deleted outright exactly as
    before: undo must never turn a delete into a leak.
    """
    directory = holding_dir()
    if _slot is None or directory is None:
        for path in paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                continue
        return {}
    return hold_files(paths, directory)


@contextmanager
def capturing_deletes() -> Iterator[dict[Path, Path]]:
    """Hold every file the block deletes *through retention*, for one undo.

    Marking a show played can delete downloads -- delete-after-play, the
    keep-last-N sweep, the storage cap -- and the verb that fired it has no
    way to know which rule ran or which files it touched. Retention's delete
    hook (:func:`quill.core.podcasts.retention.set_delete_hook`) answers that:
    inside this block every retention deletion is moved aside instead, and
    the mapping it yields is what Ctrl+Z restores.

    Outside an app that owns undo the block is a no-op and deletes proceed
    exactly as before.
    """
    from quill.core.podcasts import retention

    held: dict[Path, Path] = {}
    directory = holding_dir()
    if _slot is None or directory is None:
        yield held
        return

    def _hook(path: Path) -> bool:
        captured = hold_files([path], directory)
        if not captured:
            return False
        # Keys collide across a batch (index 0000 every call), so re-key each
        # capture onto a name that cannot repeat within this block.
        for target, original in captured.items():
            unique = target.with_name(f"{len(held):04d}-{original.name}")
            try:
                if unique != target:
                    target.rename(unique)
            except OSError:
                unique = target
            held[unique] = original
        return True

    previous = retention.set_delete_hook(_hook)
    try:
        yield held
    finally:
        retention.set_delete_hook(previous)


def restore(held: dict[Path, Path]) -> int:
    """Move held files back; the undo half of :func:`hold_or_delete`."""
    return restore_held(held)


def discard(held: dict[Path, Path]) -> None:
    """Delete held files for good; the disposer half."""
    discard_held(held)


class UndoLastMixin:
    """The frame's side: one command, one handler, one honest refusal.

    Mixed into ``RadioAppFrame`` and ``PodcastsAppFrame`` only. The handler
    speaks whatever the undo callable's owner wants said -- the action's own
    ``done()`` sentence -- so a window that has to refresh a list does it
    inside its callable and this stays one method long.
    """

    def _init_undo_last(self) -> None:
        from quill.core.paths import app_data_dir

        activate(app_data_dir())

    def _register_undo_last_command(self) -> None:
        commands: Any = self.commands  # type: ignore[attr-defined]
        commands.try_register(
            "app.undo_last",
            "Undo Last Action",
            self.undo_last_action,
            feature_id="core.app",
        )
        commands.register_non_repeatable("app.undo_last")

    def undo_last_menu_label(self) -> str:
        """ "Undo Unsubscribe" / "Undo" -- what the menu item should read."""
        current = slot()
        return current.menu_label() if current is not None else "Undo"

    def undo_last_action(self) -> None:
        """Ctrl+Z: take back the last destructive step, once."""
        announce: Any = getattr(self, "_announce", None)
        current = slot()
        action = current.take() if current is not None else None
        if action is None:
            if callable(announce):
                announce("Nothing to undo.")
            return
        try:
            action.undo()
        except Exception as error:  # noqa: BLE001 - an undo that fails must say so
            if callable(announce):
                announce(f"Could not undo {action.verb}: {error}.")
            return
        if callable(announce):
            announce(action.done())
