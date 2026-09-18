"""The two typing modes: overtype, and what the Tab key does.

Both are *modes* rather than actions -- they change what the next ordinary
keystroke means, they persist until changed back, and neither makes a sound of
its own. That combination is what makes them an accessibility problem rather
than a preference: a sighted user discovers overtype by watching a letter
disappear, and a listener discovers it by finding the sentence gone. So each
mode has a focusable status-bar cell that can be asked at any time ("Insert" /
"Overwrite", "Indent" / "Tab char"), a checkable menu item that mirrors it, and
a spoken outcome when it changes.

**Overtype is the control's, not ours.** RICHEDIT50W implements
insert-versus-overwrite itself and toggles it on VK_INSERT; it exposes no way to
set the mode and no way to read it back. So :attr:`_overwrite_mode` is a
*mirror*, never a source of truth, and the whole correctness argument is that
every route which moves the control also moves the mirror:

* the **Insert key**, which the control answers whether QUILL asks it to or not
  -- watched in ``_on_editor_key_down``, which flips the mirror and then skips
  so the control can act. The key is deliberately never *claimed*: Insert is
  NVDA's and JAWS's own modifier;
* **Ctrl+Alt+Shift+W** (``view.toggle_overwrite_mode``), which goes through
  :meth:`~quill.ui.richedit_editing.RichEditDocument.toggle_overtype` -- the
  shared implementation QuillLite's ``cmd_toggle_overwrite`` calls too.

Until 2026-09-09 the second of those flipped the mirror and told the control
nothing. ``_overwrite_mode`` was written in three places and read in exactly one
-- the status bar -- so the cell could announce "Overwrite" while typing still
inserted, and the Insert key would then toggle the two further apart rather than
back together. A status cell that misreports what typing is about to do, to
somebody who cannot check by looking, is the same defect as the Cast
playback-speed bug in ``CHANGELOG.md``: a control that misreports what you are
hearing. Hence the rule this module keeps -- **the command refuses rather than
announces when the control cannot be told**, because "nothing happened and I
said so" is a usable answer and "I claimed a mode I did not set" is not.

**Tab mode is ours.** The Tab key is intercepted in ``_on_editor_key_down``, and
:attr:`_tab_inserts_literal` decides whether it runs the smart line indent
(QUILL's default) or types a tab character (Notepad's). Shift+Tab outdents in
either mode, so a stray indent can be undone without first leaving the mode.
QuillLite ships the same toggle with the opposite default, for the reason
recorded in ``quill/apps/lite_window_typing.py``: it is a Notepad replacement,
and Notepad's Tab types a tab.

Extracted from ``main_frame.py`` on 2026-09-09 under GATE-11, which is the
ratchet that turns "the frame grew again" into "the frame gained a seam".
"""

from __future__ import annotations

from typing import Any

from quill.core.i18n import _

__all__ = ["TypingModesMixin"]


class TypingModesMixin:
    """``view.toggle_overwrite_mode`` and ``format.toggle_tab_insert_mode``.

    Mixed into :class:`~quill.ui.main_frame.MainFrame`, which supplies
    ``editor``, ``frame``, ``_overwrite_mode``, ``_tab_inserts_literal``,
    ``_synthetic_insert_key``, ``_refresh_statusbar`` and ``_set_status``.
    """

    def _tell_control_overwrite_toggled(self) -> bool:
        """Hand the editor the Insert keystroke that flips its overtype mode.

        The mechanism is the shared one --
        :meth:`~quill.ui.richedit_editing.RichEditDocument.toggle_overtype`,
        which QuillLite's own command calls too, so the two products cannot
        drift on what "overwrite mode" does. Returns True when the control was
        told, so the caller can refuse to announce a mode change it could not
        make: a status cell that misreports what typing is about to do is
        exactly the defect this product cannot ship.
        """
        editor = getattr(self, "editor", None)
        richedit = getattr(editor, "quill_richedit", None)
        toggle = getattr(richedit, "toggle_overtype", None)
        if not callable(toggle):
            return False
        # The synthesised key comes back through this frame's own EVT_KEY_DOWN
        # (verified on the live control), so the guard has to be up for the
        # whole send or the handler would flip the flag straight back.
        self._synthetic_insert_key = True
        try:
            return bool(toggle())
        except Exception:  # noqa: BLE001 - best effort; the flag stays honest
            return False
        finally:
            self._synthetic_insert_key = False

    def toggle_overwrite_mode(self, enabled: bool | None = None) -> None:
        """Toggle overtype, in the control as well as in the status bar.

        The flag alone used to be the whole implementation, so this command
        could leave the status cell claiming "Overwrite" while typing still
        inserted -- and the Insert key would then toggle the two further apart
        rather than back together.
        """
        next_state = (not self._overwrite_mode) if enabled is None else enabled
        if next_state == self._overwrite_mode:
            # Already there. Say so rather than sending the control a
            # keystroke that would toggle it out of agreement.
            self._set_status("Overwrite mode on" if next_state else "Insert mode on")
            return
        if not self._tell_control_overwrite_toggled():
            self._set_status("Overwrite mode is not available on this editing surface")
            return
        self._overwrite_mode = next_state
        self._refresh_statusbar()
        self._set_status("Overwrite mode on" if next_state else "Insert mode on")

    def _tab_types_a_tab(self) -> bool:
        """Whether Tab types a tab character right now (bad.md T3, P1.21).

        The toggle wins when it has been used; otherwise the document kind
        decides, through the shared ``quill.core.tab_behaviour`` rule QuillLite
        reads too. Before this, QUILL indented in every kind and QuillLite typed
        a tab in every kind, and each was wrong in the other's documents.
        """
        from quill.core.tab_behaviour import tab_inserts_a_tab

        if getattr(self, "_tab_mode_chosen", False):
            return bool(self._tab_inserts_literal)
        return tab_inserts_a_tab(self._effective_markup_kind())

    def toggle_tab_insert_mode(self, enabled: bool | None = None) -> None:
        """Toggle whether the Tab key inserts a literal tab or indents lines.

        Until this is called the document kind decides (``_tab_types_a_tab``);
        calling it fixes the answer for the session. On, Tab types a tab
        character at the caret like a plain text editor. The new mode is spoken
        and reflected in the Tab Mode status-bar cell and the Format menu check
        item."""
        next_state = (not self._tab_inserts_literal) if enabled is None else enabled
        self._tab_inserts_literal = next_state
        # From here the kind stops deciding: somebody has said what they want
        # (bad.md T3, P1.21), and a document's extension must not overrule them.
        self._tab_mode_chosen = True
        self._sync_tab_mode_menu_check()
        self._refresh_statusbar()
        self._set_status(
            "Tab key inserts a tab character" if next_state else "Tab key indents the line"
        )

    def build_indent_mode_items(self, format_menu: Any) -> None:
        """The Format menu's two indentation *modes*, after Indent and Outdent.

        The menu items live beside the handlers they open rather than inline in
        ``main_frame_menu.py``. That is GATE-11's doing, and it is also simply
        right: a check item whose tick is set in one module and cleared in
        another (:meth:`_sync_tab_mode_menu_check`) is a pair that drifts.
        """
        self._id_toggle_tab_mode = self._wx.NewIdRef()
        format_menu.AppendCheckItem(
            self._id_toggle_tab_mode,
            self._menu_label(_("Tab Key Inserts Tab &Character"), "format.toggle_tab_insert_mode"),
        )
        format_menu.Check(self._id_toggle_tab_mode, getattr(self, "_tab_inserts_literal", False))
        # Leading whitespace is what a screen reader does not read back, so the
        # depth is the one fact about a line that has to be *askable*.
        self._id_describe_indent_depth = self._wx.NewIdRef()
        format_menu.Append(
            self._id_describe_indent_depth,
            self._menu_label(_("Describe Indent Dep&th"), "format.describe_indent_depth"),
        )

    def describe_indent_depth(self) -> None:
        """Say how deeply the caret's line is indented, when asked.

        Leading whitespace is the one part of a line a screen reader routinely
        does not speak, so in a configuration file, a code block or a nested
        list the shape of the document is invisible by ear -- and until now
        there was no way to ask. QUILL could only announce the depth *as you
        moved* (``settings.announce_indent_depth``, and after Tab), which
        answers the question while you are busy with something else and says
        nothing at the moment you actually want to know: before you type.

        The phrasing is :func:`~quill.core.format_ops.describe_indent_depth`'s,
        the same one Tab already speaks, so "4 spaces" means the same thing
        however it was reached. QuillLite has the command on the same key.
        """
        self._set_status(self._current_line_indent_phrase())

    def _sync_tab_mode_menu_check(self) -> None:
        menu_bar = getattr(self.frame, "GetMenuBar", None)
        menu_id = getattr(self, "_id_toggle_tab_mode", None)
        if menu_id is None or not callable(menu_bar):
            return
        bar = menu_bar()
        if bar is None:
            return
        item = bar.FindItemById(menu_id)
        if item is not None and item.IsCheckable():
            item.Check(self._tab_inserts_literal)
