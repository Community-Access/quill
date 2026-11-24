"""Media Player: jumps with a way back, and a place that is the right place (FUX-01).

Moved out of ``player.py`` (GATE-11), which is at its budget, with what this
adds:

* **Back to Where I Was** (Alt+Left, the family's Go Back key). Go to Position
  and a chapter chosen in the Chapters tree note the place they leave
  (:class:`~quill.core.media.jump_back.JumpBack`); the command returns to it,
  and pressing it again returns to where you went back from. Before, a jump
  was one-way.
* **The place is saved under the file that is playing.** A book of several
  files saved the playing file's time under the *first* file's name, so
  reopening put you in track one at track four's time. Each file now keeps its
  own place.
* **A finished file starts again from the beginning.** The resume save ran on
  after the end and kept a place in the closing seconds, so the next open
  landed on the credits. Within :data:`~quill.core.media.positions.END_MARGIN_MS`
  of the end counts as finished, the rule Quill Radio's recordings use.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import wx

from quill.core.media import format_spoken
from quill.core.media.jump_back import MIN_JUMP_MS, NOTHING_TO_GO_BACK_TO, JumpBack, back_sentence
from quill.ui.media.go_to_position_dialog import GoToPositionDialog

__all__ = ["PlayerJumpsMixin"]


class PlayerJumpsMixin:
    """Go to Position, chapter jumps, Back to Where I Was, and the saved place."""

    _book_key: str | None
    _book_path: Path | None

    # -- where you were ------------------------------------------------------

    def _jump_item(self) -> str:
        """The book a remembered place belongs to; the file is kept beside it."""
        return self._book_key or ""

    def _jumps(self) -> JumpBack:
        jumps = getattr(self, "_jump_back", None)
        if jumps is None:
            jumps = JumpBack()
            self._jump_back = jumps
        return jumps

    def _note_jump(self, target_ms: int | None = None) -> None:
        """Note the place before a jump; *target_ms* None is a jump to another file."""
        here = self._player.playhead_ms()
        target = here + MIN_JUMP_MS if target_ms is None else target_ms
        if self._jumps().before_jump(self._jump_item(), here, target):
            self._jump_file = self._book_path

    def _on_back_to_where_i_was(self, _event: Any = None) -> None:
        """Return to the place before the last jump, and say where, once."""
        item = self._jump_item()
        if not item:
            self._announce("Open a file first.")
            return
        if self._player.length_ms() <= 0:
            self._announce("Still loading.")  # the place is kept for when it has
            return
        here_file = self._book_path
        target = self._jumps().back(item, self._player.playhead_ms())
        if target is None:
            self._announce(NOTHING_TO_GO_BACK_TO)
            return
        there_file = getattr(self, "_jump_file", here_file)
        self._jump_file = here_file
        if there_file is not None and there_file != here_file:
            # The place was in another file of the book: load it there, paused
            # or playing as the player is now.
            self._save_resume()
            self._player.load(str(there_file), [], resume_ms=target, autoplay=True)
            self._book_path = there_file
        else:
            self._player.seek_to(target, announce=False)
        self._announce(back_sentence(target))

    # -- the jumps -------------------------------------------------------------

    def _on_go_to_position(self, _event: Any) -> None:
        if not self._book_key:  # a streamed address has a length too
            self._show_message_box("Open a file first.", "Quill Media Player")
            return
        dialog = GoToPositionDialog(
            self.frame,
            duration_ms=self._player.length_ms(),
            current_ms=self._player.playhead_ms(),
            announce=self._announce,
        )
        try:
            if self._show_modal_dialog(dialog, "Go to Position") == wx.ID_OK:
                target = dialog.get_target_ms()
                self._note_jump(target)
                self._player.seek_to(target, announce=False)  # said once, below
                clamped = dialog.clamped_message()
                if clamped:
                    self._announce(clamped)
                else:
                    self._announce(f"Jumped to {format_spoken(target)}.")
        finally:
            dialog.Destroy()

    def _on_chapter_activate(self, event: Any) -> None:
        item = event.GetItem()
        if not (item and item.IsOk()):
            return
        payload = self._chapter_tree.GetItemData(item)
        if not payload:
            return
        kind = payload[0]
        if kind == "seek":
            self._note_jump(int(payload[1]))
            self._player.seek_to(int(payload[1]))
        elif kind in ("load", "track"):
            self._note_jump()  # another file of the book
            self._play_track_node(payload, self._chapter_tree.GetItemText(item))

    # -- the saved place -------------------------------------------------------

    def _save_resume(self) -> None:
        if self._book_path is None:
            return
        try:
            from quill.core.media.positions import PositionStore
            from quill.core.paths import app_data_dir

            PositionStore(app_data_dir()).remember(
                self._book_path,
                self._player.playhead_ms(),
                duration_ms=self._player.length_ms(),
            )
        except Exception:  # noqa: BLE001 - resume is best-effort, never fatal
            pass
