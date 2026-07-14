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

if TYPE_CHECKING:
    from quill.core.verbosity.controller import VerbosityController

__all__ = ["VerbosityCommandsMixin"]


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
        line, column, total = self._caret_position()
        self._announce_text(self.verbosity.where_am_i(line=line, column=column, total=total))

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
        dialog.SetMinSize(wx.Size(640, 560))
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

        apply_modal_ids(dialog)
        close.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CLOSE))
        try:
            self._show_modal_dialog(dialog, "Verbosity Preferences")
        finally:
            dialog.Destroy()
