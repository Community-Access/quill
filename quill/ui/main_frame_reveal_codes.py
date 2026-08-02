"""MainFrame mixin for the Reveal Codes pane (WordPerfect-style code inspector).

Owns the toggle (Alt+F3), the in-pane navigation commands, and the lightweight
idle-tick that keeps the pane's token stream and caret in sync with the active
editor. The pane widget and all token logic live in
:mod:`quill.ui.reveal_codes_pane` / :mod:`quill.core.reveal_codes`; the View-menu
item and its event binding are added in ``main_frame_menu.py`` (where the View menu
and gettext live). This mixin is the thin behaviour layer.
"""

from __future__ import annotations

from typing import Any

from quill.core.browser_preview import markup_offset_for_line


class RevealCodesMixin:
    # Provided by MainFrame; declared for type-checkers.
    _wx: Any
    frame: Any
    editor: Any
    settings: Any
    commands: Any

    def register_reveal_codes_commands(self) -> None:
        """Register the Reveal Codes commands (remappable/searchable). One line in
        MainFrame's command-registration sequence (GATE-11)."""
        specs: tuple[tuple[str, str, object], ...] = (
            ("view.reveal_codes_toggle", "Reveal Codes", self.toggle_reveal_codes),
            ("reveal.next_code", "Reveal Codes: Next Code", self.reveal_next_code),
            ("reveal.previous_code", "Reveal Codes: Previous Code", self.reveal_previous_code),
            ("reveal.go_to_pair", "Reveal Codes: Go to Matching Code", self.reveal_go_to_pair),
            ("reveal.toggle_speak", "Reveal Codes: Speak Codes Aloud", self.reveal_toggle_speak),
        )
        for command_id, label, handler in specs:
            self.commands.register(command_id, label, handler, self._binding_for(command_id))

    # ------------------------------------------------------------------ #
    # Toggle + visibility
    # ------------------------------------------------------------------ #
    def toggle_reveal_codes(self, show: bool | None = None) -> None:
        pane = getattr(self, "_reveal_pane", None)
        if pane is None:
            return
        visible = pane.panel.IsShown()
        target = (not visible) if show is None else bool(show)
        if target == visible:
            return
        # Hiding the pane while focus lives inside it would strand focus on a
        # hidden window; move it back to the editor first so the user lands
        # somewhere sensible (and the screen reader follows).
        if not target and pane.has_focus():
            editor = getattr(self, "editor", None)
            if editor is not None:
                try:
                    editor.SetFocus()
                except Exception:  # noqa: BLE001
                    pass
        pane.panel.Show(target)
        self.settings.reveal_codes_visible = target
        try:
            from quill.core.settings import save_settings

            save_settings(self.settings)
        except Exception:  # noqa: BLE001 - persistence is best-effort
            pass
        item_id = getattr(self, "_id_reveal_codes", None)
        menu_bar = self.frame.GetMenuBar()
        if item_id is not None and menu_bar is not None:
            try:
                menu_bar.Check(item_id, target)
            except Exception:  # noqa: BLE001
                pass
        frame_sizer = self.frame.GetSizer()
        if frame_sizer is not None:
            frame_sizer.Layout()
        if target:
            pane.rebuild()
            # _set_status_quiet keeps the longer hint on the status bar without
            # speaking it; _announce speaks the terser line (avoids #728 double-speak).
            self._set_status_quiet("Reveal Codes shown. Press F6 to move into it; Alt+F3 to hide.")
            self._announce("Reveal Codes shown.")
        else:
            self._set_status_quiet("Reveal Codes hidden.")
            self._announce("Reveal Codes hidden.")

    # ------------------------------------------------------------------ #
    # Editor <-> pane sync
    # ------------------------------------------------------------------ #
    def _reveal_move_editor_caret(self, markup_offset: int) -> None:
        """Move the editor caret to a markup offset (driven from the pane)."""
        editor = getattr(self, "editor", None)
        if editor is None:
            return
        try:
            editor.SetInsertionPoint(max(0, markup_offset))
            show = getattr(editor, "ShowPosition", None)
            if callable(show):
                show(max(0, markup_offset))
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------ #
    # Live preview -> editor caret (#1257)
    # ------------------------------------------------------------------ #
    def _on_preview_goto_source(self, payload: Any) -> None:
        """Move the editor caret to the block acted on in the live preview.

        Fired from the side preview's JS bridge when a screen-reader user
        right-clicks (``trigger="context"``) or presses Enter (``"enter"``) on a
        block the renderer stamped with a source line. A right-click offers an
        explicit menu item — matching the screen-reader convention that the
        Applications key opens a menu rather than firing an action outright —
        while Enter jumps straight there. Reuses :meth:`_reveal_move_editor_caret`
        (the same editor caret sink Reveal Codes drives).
        """
        tab = self._active_tab()
        if tab is None or getattr(tab, "editor", None) is None:
            return
        try:
            line = int(payload.get("src"))
        except (TypeError, ValueError):
            return
        label = str(payload.get("label") or "").strip()
        if str(payload.get("trigger") or "") == "context":
            self._popup_preview_goto_menu(tab, line, label)
        else:
            self._jump_editor_to_source_line(tab, line, label)

    def _popup_preview_goto_menu(self, tab: Any, line: int, label: str) -> None:
        control = getattr(tab.preview, "control", None) if tab.preview is not None else None
        if control is None:
            self._jump_editor_to_source_line(tab, line, label)
            return
        wx = self._wx
        menu = wx.Menu()
        item = menu.Append(wx.ID_ANY, "&Go to this location in the editor")
        # Bind on the transient menu (not the control) so the handler is scoped
        # to this popup's lifetime -- no per-popup binding leaks on the frame.
        menu.Bind(
            wx.EVT_MENU,
            lambda _e: self._jump_editor_to_source_line(tab, line, label),
            item,
        )
        try:
            control.PopupMenu(menu)
        finally:
            menu.Destroy()

    def _jump_editor_to_source_line(self, tab: Any, line: int, label: str) -> None:
        editor = getattr(tab, "editor", None)
        if editor is None:
            return
        offset = markup_offset_for_line(editor.GetValue(), line)
        self._reveal_move_editor_caret(offset)
        editor.SetFocus()
        self._set_active_region("Editor")
        self._announce(f"Editor moved to {label}" if label else "Editor moved to that location")

    def _reveal_on_idle(self, event: Any) -> None:
        event.Skip()
        pane = getattr(self, "_reveal_pane", None)
        if pane is None or not pane.panel.IsShown():
            return
        editor = getattr(self, "editor", None)
        if editor is None:
            return
        try:
            text_len = editor.GetLastPosition()
            caret = editor.GetInsertionPoint()
        except Exception:  # noqa: BLE001
            return
        state = (id(editor), text_len, caret)
        prev = getattr(self, "_reveal_last_state", None)
        if state == prev:
            return
        self._reveal_last_state = state
        # Rebuild only when the document (or active editor) changed; otherwise just
        # re-sync the caret highlight, keeping the idle path cheap. Skip re-syncing
        # while the pane itself has focus so user navigation there is not fought.
        if prev is None or prev[0] != state[0] or prev[1] != state[1]:
            pane.rebuild()
        elif not pane.has_focus():
            pane.sync_from_editor()

    # ------------------------------------------------------------------ #
    # In-pane navigation commands
    # ------------------------------------------------------------------ #
    def reveal_next_code(self) -> None:
        pane = getattr(self, "_reveal_pane", None)
        if pane is not None and pane.panel.IsShown():
            pane.next_code()

    def reveal_previous_code(self) -> None:
        pane = getattr(self, "_reveal_pane", None)
        if pane is not None and pane.panel.IsShown():
            pane.previous_code()

    def reveal_go_to_pair(self) -> None:
        pane = getattr(self, "_reveal_pane", None)
        if pane is not None and pane.panel.IsShown():
            pane.go_to_pair()

    def reveal_toggle_speak(self) -> None:
        """Toggle whether QUILL speaks the rich code phrase as you arrow (#1245).

        Off (default) leaves the screen reader as the single voice on flowed
        navigation — it narrates the line itself and QUILL mirrors the phrase to
        the status bar silently, which stops the doubled/inconsistent speech
        NVDA and JAWS produced (#1244). On restores the verbose spoken
        examination for users who prefer it.
        """
        new_value = not bool(getattr(self.settings, "reveal_codes_speak", False))
        self.settings.reveal_codes_speak = new_value
        try:
            from quill.core.settings import save_settings

            save_settings(self.settings)
        except Exception:  # noqa: BLE001 - persistence is best-effort
            pass
        self._announce(
            "Reveal Codes will speak codes aloud."
            if new_value
            else "Reveal Codes codes are now silent; your screen reader reads the line."
        )
