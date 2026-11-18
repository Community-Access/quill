"""MainFrame mixin that makes the verbosity system live (verbosity sub-PR 1.5).

Holds a lazily-created :class:`~quill.core.verbosity.controller.VerbosityController`
and exposes the command handlers the keymap and menu bind to: toggle Quiet /
Meeting mode, undo a verbosity transition, the Where-am-I / What-changed /
Speak-status queries, and open the Verbosity Preferences dialog (which hosts the
1.4 panel and its sub-dialogs).

The controller is created on first use, so until the user engages verbosity the
announce path is byte-for-byte unchanged — no regression risk. Once it exists,
``MainFrame._announce`` routes through :meth:`VerbosityController.process` so
Quiet/Meeting actually suppress speech (the status-bar floor always remains) and
the announcement history records.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from quill.ui.dpi import dip_size

if TYPE_CHECKING:
    from quill.core.verbosity.controller import VerbosityController

__all__ = ["VerbosityCommandsMixin"]


#: Two presses closer together than this are one double press.
_SECOND_PRESS_SECONDS = 0.8


class VerbosityCommandsMixin:
    """Verbosity command handlers for the editor shell."""

    @property
    def verbosity(self) -> VerbosityController:
        """The live verbosity controller, created from settings on first use."""
        ctrl = getattr(self, "_verbosity_controller", None)
        if ctrl is None:
            from quill.core.verbosity.controller import VerbosityController
            from quill.core.verbosity.profiles import DEFAULT_PROFILE, active_profile

            settings = getattr(self, "settings", None)
            profile = active_profile(settings) if settings is not None else DEFAULT_PROFILE
            ctrl = VerbosityController(
                profile=profile,
                history_enabled=bool(getattr(settings, "verbosity_history_enabled", True)),
                history_limit=int(getattr(settings, "verbosity_history_limit", 100)),
                mastery_enabled=bool(getattr(settings, "verbosity_mastery_enabled", True)),
            )
            self._verbosity_controller = ctrl
        return ctrl

    def _route_verbosity_announcement(self, message: str) -> tuple[str, bool]:
        """Run ``message`` through the controller if it exists.

        Returns ``(text_to_speak, suppressed)``. When no controller has been
        created yet, returns the message unchanged and not suppressed, so the
        default announce path is untouched.
        """
        ctrl = getattr(self, "_verbosity_controller", None)
        if ctrl is None:
            return message, False
        outcome = ctrl.process(message)
        return outcome.speech, outcome.suppressed

    # -- mode toggles -------------------------------------------------------

    def toggle_quiet_mode(self) -> None:
        message = self.verbosity.toggle_quiet()
        self._verbosity_status(message)

    def toggle_meeting_mode(self) -> None:
        message = self.verbosity.toggle_meeting()
        self._verbosity_status(message)

    def verbosity_undo(self) -> None:
        self._verbosity_status(self.verbosity.undo())

    def _verbosity_status(self, message: str) -> None:
        badge = self.verbosity.status_badge()
        text = f"{badge} {message}".strip() if badge else message
        setter = getattr(self, "_set_status", None)
        if callable(setter):
            setter(text)

    # -- status queries -----------------------------------------------------

    def verbosity_where_am_i(self) -> None:
        """Say where the caret is; pressed twice quickly, show it all in a window.

        The second press is EdSharp's: everything Where Am I knows, then every
        command and its key, in a read-only window to arrow through.
        """
        import time

        now = time.monotonic()
        twice = now - getattr(self, "_where_am_i_at", -10.0) < _SECOND_PRESS_SECONDS
        self._where_am_i_at = -10.0 if twice else now
        line, column, total, percent = self._text_position()
        if line is None:
            line, column, total = self._caret_position()
        said = self.verbosity.where_am_i(line=line, column=column, total=total, percent=percent)
        if twice:
            self._show_where_am_i_review(said)
            return
        self._announce_text(said)

    def _where_am_i_review_text(self, position: str) -> str:
        """Everything for the second press: the document, then every command."""
        document = getattr(self, "document", None)
        lines = [position]
        name = str(getattr(document, "name", "") or "")
        if name:
            lines.append(f"Document: {name}")
        path = getattr(document, "path", None)
        if path:
            lines.append(f"Saved at: {path}")
        lines.append("Modified" if getattr(document, "modified", False) else "Saved")
        mirror = getattr(self, "doc_text", None)
        try:
            stats = mirror.stats() if mirror is not None else None
        except Exception:  # noqa: BLE001 - counts are a nicety here
            stats = None
        if stats is not None:
            lines.append(f"{stats.words:,} words, {stats.characters:,} characters")
        encoding = str(getattr(document, "encoding", "") or "")
        if encoding:
            lines.append(f"Encoding: {encoding}")
        build = getattr(self, "_build_cheatsheet_text", None)
        if callable(build):
            lines += ["", "Every command and its key, in menu order:", "", build("", "menu")]
        return "\n".join(lines)

    def _show_where_am_i_review(self, position: str) -> None:
        from quill.ui.wordpress_dialogs import show_report

        show_report(
            self.frame,
            self._show_modal_dialog,
            title="Where Am I",
            text=self._where_am_i_review_text(position),
            help_text=(
                "Where the caret is and what the document is, then every command and "
                "its key. Opened by pressing Where Am I twice."
            ),
        )

    def _text_position(self) -> tuple[int | None, int | None, int | None, int | None]:
        """Line, column, line count and percent through, counted in the text.

        Off the shared document mirror, the same one the status bar's Ln/Col
        cell reads, so a paragraph the window wraps is one line, as it is in
        the file. ``PositionToXY`` on Windows counts the wrapped screen lines.
        """
        editor = getattr(self, "editor", None)
        mirror = getattr(self, "doc_text", None)
        get_pos = getattr(editor, "GetInsertionPoint", None)
        if mirror is None or not callable(get_pos):
            return None, None, None, None
        try:
            position = int(get_pos())
            line, column = mirror.line_column(position)
            total = len(mirror.line_starts())
            length = len(mirror.text)
        except Exception:  # noqa: BLE001 - a dead control means "fall back"
            return None, None, None, None
        percent = round(100 * min(position, length) / length) if length else 0
        return line, column, total, percent

    def verbosity_what_changed(self) -> None:
        self._announce_text(self.verbosity.what_changed())

    def verbosity_speak_status(self) -> None:
        status = str(getattr(self, "_status_message", "") or "")
        self._announce_text(self.verbosity.speak_status(status))

    def _caret_position(self) -> tuple[int | None, int | None, int | None]:
        editor = getattr(self, "editor", None)
        get_pos = getattr(editor, "GetInsertionPoint", None)
        get_xy = getattr(editor, "PositionToXY", None)
        get_count = getattr(editor, "GetNumberOfLines", None)
        if not (callable(get_pos) and callable(get_xy)):
            return None, None, None
        try:
            ok, col, row = get_xy(get_pos())
        except Exception:
            return None, None, None
        if not ok:
            return None, None, None
        total = get_count() if callable(get_count) else None
        return row + 1, col + 1, total

    def _announce_text(self, message: str) -> None:
        announce = getattr(self, "_announce", None)
        if callable(announce):
            announce(message)

    # -- preferences --------------------------------------------------------

    def open_verbosity_preferences(self) -> None:
        """Open the Verbosity Preferences panel hosted in a modal dialog."""
        wx = getattr(self, "_wx", None)
        if wx is None:
            return
        from quill.ui.verbosity_prefs import VerbosityPrefsPanel

        dialog = wx.Dialog(
            self.frame,
            title="Verbosity Preferences",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        dialog.SetMinSize(dip_size(dialog, 640, 560))
        sizer = wx.BoxSizer(wx.VERTICAL)
        panel = VerbosityPrefsPanel(dialog, announce_cb=self._announce_text)
        sizer.Add(panel, 1, wx.EXPAND | wx.ALL, 8)
        button_row = wx.BoxSizer(wx.HORIZONTAL)
        button_row.AddStretchSpacer()
        close = wx.Button(dialog, id=wx.ID_CLOSE, label="C&lose")
        button_row.Add(close)
        sizer.Add(button_row, 0, wx.EXPAND | wx.ALL, 8)
        dialog.SetSizer(sizer)
        from quill.ui.dialog_contract import apply_modal_ids

        apply_modal_ids(dialog, cancel_id=wx.ID_CLOSE)
        close.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CLOSE))
        try:
            self._show_modal_dialog(dialog, "Verbosity Preferences")
        finally:
            dialog.Destroy()
