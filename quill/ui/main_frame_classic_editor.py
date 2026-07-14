"""Classic-editor power features, mixed into :class:`MainFrame`.

Three keyboard-first conveniences in the lineage of the WordPerfect Editor that
have no prior equivalent in QUILL:

- **Repeat Next Command** (``edit.repeat_command``) — a numeric repeat prefix for
  any command, armed on :class:`~quill.core.commands.CommandRegistry`.
- **Restore Deleted Text** (``edit.restore_deletion``) — re-insert a recent
  deletion chosen from an accessible list (the ``DeletionRing`` kill-ring).
- **Describe Character at Cursor** (``power.describe_character``) — the
  screen-reader descendant of "Reveal Codes", shown in the same accessible
  read-only dialog the F1 help uses.

The handlers resolve by convention from the power-tools manifest
(``power.describe_character`` -> ``self.describe_character``,
``edit.repeat_command`` -> ``self.repeat_command``, etc.), so they live on a
mixin in MainFrame's MRO. The wx-free logic lives in ``quill/core``
(``char_describe``, ``deletion_ring``, and the repeat state on
``CommandRegistry``); this layer only wires it to the editor, dialogs, and
announcements.

Extracted from :mod:`quill.ui.main_frame_power_tools` to keep that module within
its GATE-11 size budget.
"""

from __future__ import annotations

from quill.core.char_describe import describe_character


def _deletion_preview(entry: str, index: int, max_chars: int = 60) -> str:
    """A short, speakable label for one deletion-ring entry."""
    flat = " ".join(entry.split())
    if len(flat) > max_chars:
        flat = flat[:max_chars] + "..."
    chars = len(entry)
    noun = "character" if chars == 1 else "characters"
    ordinal = "Most recent" if index == 0 else f"{index + 1} deletions ago"
    return f"{ordinal} ({chars} {noun}): {flat}"


class ClassicEditorMixin:
    """Repeat, Restore Deleted Text, and Describe Character, on :class:`MainFrame`.

    Relies on MainFrame helpers: ``self.commands``, ``self.editor``, ``self.frame``,
    ``self._wx``, ``self._deletion_ring``, ``self._set_status``, ``self._announce``,
    ``self._show_modal_dialog``, ``self._document_is_read_only``,
    ``self._power_tools_prompt_single``, and ``self._power_tools_insert_at_cursor``.
    """

    # ----------------------------------- Repeat next command (ED "Repeat")
    def repeat_command(self) -> None:
        """Arm a repeat count so the next command runs several times.

        The WordPerfect Editor "Repeat" feature for a keyboard-first editor:
        prompt for a count, then the very next command dispatched through the
        command registry (a movement, a delete, an insertion, a macro) runs
        that many times. The arming command is registered non-repeatable, so
        re-arming never multiplies itself.
        """
        raw = self._power_tools_prompt_single(
            "Repeat Next Command",
            "Repeat the next command how many times?",
            "2",
        )
        if raw is None:
            return
        try:
            count = int(raw.strip())
        except ValueError:
            self._set_status("Enter a whole number")
            return
        if count < 1:
            self._set_status("Enter a count of 1 or more")
            return
        self.commands.arm_repeat(count)
        self._announce(f"Next command will repeat {count} times")

    # ----------------------------------- Restore deleted text (ED "Cancel")
    def restore_deletion(self) -> None:
        """Re-insert recently deleted text chosen from an accessible list.

        The descendant of the WordPerfect Editor "Cancel" buffer: QUILL's
        structured delete commands record what they removed into a small ring,
        and this command lets the user pick any of the recent deletions and
        re-insert it at the cursor — distinct from Undo, which only reverts the
        last edit in place.
        """
        if self._document_is_read_only():
            self._set_status("Document is read-only")
            return
        ring = getattr(self, "_deletion_ring", None)
        if ring is None or ring.is_empty():
            self._set_status("No deleted text to restore")
            return
        entries = ring.entries()
        if len(entries) == 1:
            chosen = entries[0]
        else:
            wx = self._wx
            labels = [_deletion_preview(entry, index) for index, entry in enumerate(entries)]
            with wx.SingleChoiceDialog(
                self.frame,
                "Choose deleted text to re-insert at the cursor:",
                "Restore Deleted Text",
                labels,
            ) as dialog:
                if self._show_modal_dialog(dialog, "Restore Deleted Text") != wx.ID_OK:
                    self._set_status("Restore deleted text cancelled")
                    return
                index = dialog.GetSelection()
            if index < 0 or index >= len(entries):
                return
            chosen = entries[index]
        self._power_tools_insert_at_cursor(chosen, "Restored deleted text")

    # ----------------------------------- Describe character at cursor
    def describe_character(self) -> None:
        """Show an accessible dialog describing the character at the cursor.

        The screen-reader descendant of "Reveal Codes": it names the exact
        character under the caret — its Unicode name, code point, category, and
        plain-language notes for invisibles (no-break space, zero-width
        characters, smart quotes, line endings). Rendered in the same read-only
        dialog the F1 context help uses so a screen reader reads it in one pass.
        """
        from quill.core.help import HelpTopic
        from quill.ui.context_help import ContextHelpDialog

        text = self.editor.GetValue()
        position = self.editor.GetInsertionPoint()
        description = describe_character(text, position)
        self._set_status(description.summary)
        topic = HelpTopic(
            id="character_inspector",
            title="Character at Cursor",
            body=description.detail,
        )
        dialog = ContextHelpDialog(self.frame, dialog_topic=None, ctrl_topic=topic)
        self._show_modal_dialog(dialog, "Character at Cursor")
        dialog.Destroy()
