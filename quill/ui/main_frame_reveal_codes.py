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
