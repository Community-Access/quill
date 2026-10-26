"""The menu bar of an empty QUILL Lite window.

With every document closed the shell is the only window left, and its bar is the
one a screen reader walks. Until 2026-10-25 that bar was File alone -- New, Open
and Exit -- on the argument that a short bar beats no bar. It is a better
argument for a *full* bar: Recent Documents, Preferences, Check for Updates,
What's New and About need no document at all, and a listener who closed the last
one should not have to open a blank page to reach Help.

**The rows come from the command table**, filtered to :data:`NO_DOCUMENT_COMMANDS`,
so the empty bar shows the same labels, the same order and the *resolved* keys
(whatever the user has rebound them to) as a document's bar, and a feature
switched off in Customize Features is off here too. A hand-built list would be a
second copy of those rows, and second copies are how the two drift.

**The handlers are the document window's own**, called with the shell standing
in for the window: :class:`~quill.apps.lite_window.DocumentFrame`'s
``cmd_about`` run against the shell is the About QUILL Lite window, not a second
one. That only works for a handler that asks its window for nothing the shell
lacks, so the shell supplies the handful every one of them reaches for
(``app``, ``_announce``, ``control``, ``path``) and
``tests/unit/apps/test_lite_empty_window_menu.py`` checks, by reading each
handler's source, that none reaches for anything more. Open is the one exception:
the document window's Open reuses a blank document, and there is none here, so
the shell has its own :meth:`ShellMenuMixin.open_from_dialog` (moved here from
the app, which only this bar ever called).
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.speakable import speakable_controls

__all__ = ["NO_DOCUMENT_COMMANDS", "ShellMenuMixin"]

#: The commands an empty window offers, by handler. Order is the command
#: table's, not this tuple's.
NO_DOCUMENT_COMMANDS: tuple[str, ...] = (
    # File
    "cmd_new",
    "cmd_new_rich",
    "cmd_new_plain",
    "cmd_open",
    "cmd_recent_documents",
    "cmd_reopen_last_session",
    "cmd_exit",
    # Tools
    "cmd_preferences",
    "cmd_keyboard_manager",
    "cmd_sound_scheme",
    "cmd_backup_settings",
    "cmd_restore_settings",
    # Help
    "cmd_context_help",
    "cmd_tutorials",
    "cmd_shortcuts",
    "cmd_get_help_from_support",
    "cmd_check_updates",
    "cmd_release_channel",
    "cmd_whats_new",
    "cmd_about",
)

#: Handlers the shell answers itself rather than borrowing (see the module doc).
_SHELL_OWN = frozenset({"cmd_open"})


class ShellMenuMixin:
    """The empty-window bar, and the few attributes its borrowed handlers read."""

    app: Any
    #: No document, so nothing a handler could offer to save or start from.
    path = None
    modified = False

    @property
    def control(self) -> Any:
        """Where a handler puts focus back when it is done: the shell itself."""
        return self

    def _announce(self, message: str, *, interrupt: bool = True) -> None:
        """Say *message* through the app's voice, which brailles what it speaks."""
        self.app.voice.speak(speakable_controls(message), interrupt=interrupt)

    def _default_document_folder(self) -> str:
        from quill.apps.lite_window_commands import DocumentCommandsMixin

        return DocumentCommandsMixin._default_document_folder(self)  # type: ignore[arg-type]

    def _show_lite_modal(self, dialog: Any, label: str) -> int:
        from quill.ui.dialog_contract import show_modal_dialog

        return int(show_modal_dialog(dialog, label))

    def ai_about_usage(self, field: Any) -> None:
        """About's AI usage line is a document window's: hosted AI lives there."""

    def _build_placeholder_menu(self) -> None:
        """Build the empty-window bar from the command table (see the module doc)."""
        from quill.core.lite.commands import SUBMENU_SEP
        from quill.core.lite.keymap import resolved_commands

        wanted = set(NO_DOCUMENT_COMMANDS)
        menu_bar = wx.MenuBar()
        menus: dict[str, wx.Menu] = {}
        order: list[str] = []
        pending_separator: dict[str, bool] = {}
        # Defaults for a host still being built (or a test's bare one): every
        # area on and the shipped keys, which is what a new install has anyway.
        is_enabled = getattr(self.app, "feature_enabled", lambda _area: True)
        for path, label, key, handler, kind in resolved_commands(
            is_enabled, getattr(self.app, "keymap", None)
        ):
            if SUBMENU_SEP in path:
                continue
            if kind == "sep":
                if path in menus:
                    pending_separator[path] = True
                continue
            if handler not in wanted:
                continue
            menu = menus.get(path)
            if menu is None:
                menu = menus[path] = wx.Menu()
                order.append(path)
            elif pending_separator.get(path):
                menu.AppendSeparator()
            pending_separator[path] = False
            item = menu.Append(wx.ID_ANY, f"{label}\t{key}" if key else label)
            self.Bind(wx.EVT_MENU, lambda _e, h=handler: self.run_shell_command(h), item)  # type: ignore[attr-defined]
        for path in order:
            menu_bar.Append(menus[path], path)
        self.SetMenuBar(menu_bar)  # type: ignore[attr-defined]

    def open_from_dialog(self) -> None:
        """File > Open with no document open: choose files, open each through
        the app's one funnel (``open_path``), where the large-file guard sits."""
        from pathlib import Path

        from quill.core.lite.filetypes import OPEN_WILDCARD

        with wx.FileDialog(
            self,  # type: ignore[arg-type]
            "Open",
            wildcard=OPEN_WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE,
        ) as dialog:
            if self._show_lite_modal(dialog, "Open") != wx.ID_OK:
                return
            paths = [Path(chosen) for chosen in dialog.GetPaths()]
        for path in paths:
            self.app.open_path(path)

    def rebuild_empty_menu(self) -> None:
        """Rebuild the bar after the keys or the feature set changed.

        Called once the last document has closed: on wxMSW an MDI child's bar
        takes the parent's place while the child is active, so replacing the
        parent's bar with a document open would put it over the document's.
        """
        try:
            self._build_placeholder_menu()
        except RuntimeError:
            pass  # the shell is on its way out

    def run_shell_command(self, handler: str) -> None:
        """Run *handler* with no document open."""
        if handler in _SHELL_OWN:
            self.open_from_dialog()
            return
        from quill.apps.lite_window import DocumentFrame

        getattr(DocumentFrame, handler)(self)
