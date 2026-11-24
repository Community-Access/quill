"""AI Hub "Sessions" tab: browse and compare AI writing session branches.

Folds the former standalone "AI Session Branches" menu item into the Hub
(redesign §6.5), so AI configuration and history live behind one door. Extracted
into its own module — mirroring :mod:`quill.ui.ai_hub_engines_panel` — so the Hub
dialog stays within its GATE-11 size budget. The branch browsing itself is the
wx-free session-tree engine surfaced by :class:`~quill.ui.session_browser.SessionBrowserDialog`;
this panel only finds the most recent session and opens it.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from quill.core.ai.copilot_preferences import (
    CopilotPreferences,
    load_copilot_preferences,
    save_copilot_preferences,
)
from quill.core.i18n import _
from quill.ui.accessible_group import describe_group


class SessionsPanel:
    """The Sessions tab panel and its behaviour."""

    def __init__(
        self,
        notebook: object,
        *,
        parent_dialog: object,
        announce: Callable[[str], None],
        directory: Path | None = None,
        data_dir: Path | None = None,
        app_name: str = "QUILL",
    ) -> None:
        import wx

        self._wx = wx
        self._parent_dialog = parent_dialog
        self._announce = announce
        self._directory = directory
        self._data_dir = data_dir
        self._app_name = app_name
        self._preferences = load_copilot_preferences(data_dir)
        self._resume_session_id = self._preferences.resume_session_id
        self._sessions: tuple[object, ...] = ()
        self._refreshing = False

        self.panel = wx.ScrolledWindow(notebook, style=wx.VSCROLL)
        self.panel.SetScrollRate(0, 12)
        self.panel.SetName(str(_("AI writing and Copilot session settings")))
        self._build()

    def _build(self) -> None:
        wx = self._wx
        sizer = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            self.panel,
            label=_(
                "AI writing sessions are saved automatically as you chat in Ask Quill. "
                "Browse the branch tree of your most recent session to jump between "
                "branches or compare them — fully keyboard- and screen-reader-driven."
            ),
        )
        intro.Wrap(620)
        sizer.Add(intro, 0, wx.ALL, 8)

        self.browse_btn = wx.Button(self.panel, label=_("&Browse Session Branches..."))
        self.browse_btn.SetName("Browse AI session branches")
        sizer.Add(self.browse_btn, 0, wx.LEFT | wx.BOTTOM, 8)

        self.status = wx.StaticText(self.panel, label="")
        sizer.Add(self.status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        options = wx.StaticBoxSizer(
            wx.StaticBox(self.panel, label=str(_("GitHub Copilot options"))), wx.VERTICAL
        )
        options.Add(
            wx.StaticText(
                self.panel,
                label=_(
                    "These choices apply only to GitHub Copilot. Your selected provider "
                    "never changes automatically."
                ),
            ),
            0,
            wx.ALL,
            6,
        )

        options.Add(
            wx.StaticText(self.panel, label=str(_("When Copilot uses Auto, prioritize:"))),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            6,
        )
        self.auto_tier = wx.Choice(
            self.panel,
            choices=[
                str(_("Efficiency")),
                str(_("Balanced (recommended)")),
                str(_("Intelligence")),
            ],
        )
        self.auto_tier.SetName("GitHub Copilot Auto model priority")
        self.auto_tier.SetSelection(
            {"efficiency": 0, "balance": 1, "intelligence": 2}.get(self._preferences.auto_tier, 1)
        )
        options.Add(self.auto_tier, 0, wx.EXPAND | wx.ALL, 6)

        self.keep_sessions = wx.CheckBox(
            self.panel, label=str(_("Keep Copilot sessions on this device"))
        )
        self.keep_sessions.SetName("Keep Copilot sessions on this device")
        self.keep_sessions.SetValue(self._preferences.keep_sessions)
        options.Add(self.keep_sessions, 0, wx.ALL, 6)

        self.long_context = wx.CheckBox(
            self.panel, label=str(_("Let Copilot summarize older context for longer tasks"))
        )
        self.long_context.SetName("Allow Copilot long-task context summaries")
        self.long_context.SetHelpText(
            str(
                _(
                    "When enabled with session retention, Copilot may summarize older task "
                    "context to continue longer tasks. This may use additional Copilot "
                    "account usage."
                )
            )
        )
        self.long_context.SetValue(
            self._preferences.long_context and self._preferences.keep_sessions
        )
        self.long_context.Enable(self.keep_sessions.GetValue())
        options.Add(self.long_context, 0, wx.ALL, 6)

        self.share_skills = wx.CheckBox(
            self.panel,
            label=str(_("Let Copilot use enabled skills from the AI Library")),
        )
        self.share_skills.SetName("Share enabled AI Library skills with Copilot")
        self.share_skills.SetValue(self._preferences.share_enabled_skills)
        options.Add(self.share_skills, 0, wx.ALL, 6)
        describe_group(options, self.keep_sessions, self.long_context, self.share_skills)

        options.Add(
            wx.StaticText(
                self.panel,
                label=_(
                    "Session retention is off by default. When enabled, Copilot session "
                    "history can remain in this app's local data folder until you delete "
                    "it. Longer-task context summaries and skill sharing are also off by "
                    "default. Skill sharing includes only skills you have enabled."
                ),
            ),
            0,
            wx.ALL,
            6,
        )
        sizer.Add(options, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        saved = wx.StaticBoxSizer(
            wx.StaticBox(self.panel, label=str(_("Saved Copilot sessions"))), wx.VERTICAL
        )
        saved.Add(
            wx.StaticText(
                self.panel,
                label=_(
                    "Session IDs and last-updated times only are shown here; conversation "
                    "content stays in Copilot's local session store."
                ),
            ),
            0,
            wx.ALL,
            6,
        )
        self.sessions_list = wx.ListBox(self.panel, style=wx.LB_SINGLE)
        self.sessions_list.SetName("Saved Copilot sessions, identifiers and update times")
        saved.Add(self.sessions_list, 1, wx.EXPAND | wx.ALL, 6)

        session_buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.refresh_sessions_btn = wx.Button(self.panel, label=str(_("&Refresh saved sessions")))
        self.refresh_sessions_btn.SetName("Refresh saved Copilot sessions")
        session_buttons.Add(self.refresh_sessions_btn, 0, wx.RIGHT, 6)
        self.resume_session_btn = wx.Button(
            self.panel, label=str(_("&Use selected session for the next task"))
        )
        self.resume_session_btn.SetName("Use selected Copilot session for the next task")
        self.resume_session_btn.Disable()
        session_buttons.Add(self.resume_session_btn, 0)
        saved.Add(session_buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        self.confirm_delete = wx.CheckBox(
            self.panel,
            label=str(_("&Confirm permanent deletion of the selected session")),
        )
        self.confirm_delete.SetName("Confirm permanent deletion of selected Copilot session")
        saved.Add(self.confirm_delete, 0, wx.ALL, 6)
        describe_group(saved, self.confirm_delete)
        self.delete_session_btn = wx.Button(
            self.panel, label=str(_("&Delete selected session permanently"))
        )
        self.delete_session_btn.SetName("Delete selected Copilot session permanently")
        self.delete_session_btn.Disable()
        saved.Add(self.delete_session_btn, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        sizer.Add(saved, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.panel.SetSizer(sizer)
        self.panel.FitInside()
        self.browse_btn.Bind(wx.EVT_BUTTON, self._on_browse)
        self.refresh_sessions_btn.Bind(wx.EVT_BUTTON, self._on_refresh_sessions)
        self.resume_session_btn.Bind(wx.EVT_BUTTON, self._on_resume_selected)
        self.delete_session_btn.Bind(wx.EVT_BUTTON, self._on_delete_selected)
        self.sessions_list.Bind(wx.EVT_LISTBOX, self._on_session_selection)
        self.confirm_delete.Bind(wx.EVT_CHECKBOX, self._on_session_selection)
        self.keep_sessions.Bind(wx.EVT_CHECKBOX, self._on_keep_sessions_changed)

    def _on_keep_sessions_changed(self, _event: object) -> None:
        enabled = self.keep_sessions.GetValue()
        self.long_context.Enable(enabled)
        if not enabled:
            self.long_context.SetValue(False)

    def save_preferences(self) -> bool:
        tiers = ("efficiency", "balance", "intelligence")
        selection = self.auto_tier.GetSelection()
        tier = tiers[selection] if 0 <= selection < len(tiers) else "balance"
        self._preferences = CopilotPreferences(
            auto_tier=tier,
            keep_sessions=self.keep_sessions.GetValue(),
            long_context=self.long_context.GetValue() and self.keep_sessions.GetValue(),
            share_enabled_skills=self.share_skills.GetValue(),
            resume_session_id=(self._resume_session_id if self.keep_sessions.GetValue() else ""),
        )
        try:
            save_copilot_preferences(self._preferences, self._data_dir)
        except OSError:
            self.report_save_error()
            return False
        return True

    def report_save_error(self) -> None:
        self._set_status(
            _("Copilot options could not be saved. Check the app data folder and try again.")
        )

    def _set_status(self, message: str) -> None:
        self.status.SetLabel(message)
        if message:
            self._announce(message)

    def _on_refresh_sessions(self, _event: object) -> None:
        if self._refreshing:
            return
        from quill.ui.update_download import thread_submit

        self._refreshing = True
        self.refresh_sessions_btn.Disable()
        self._on_session_selection(None)
        self._set_status(_("Checking this device for saved Copilot sessions..."))

        def _work(**_kwargs: object) -> tuple[object, ...]:
            from quill.ai_packs.copilot import CopilotHarness

            harness = CopilotHarness(agent_name=self._app_name, data_dir=self._data_dir)
            return harness.list_saved_sessions()

        def _done(_name: str, sessions: tuple[object, ...]) -> None:
            self._call_after(self._show_saved_sessions, sessions)

        def _failed(_name: str, _error: BaseException) -> None:
            self._call_after(
                self._session_operation_failed,
                _("Could not load saved Copilot sessions. Check local app data."),
            )

        thread_submit(
            "quill-copilot-list-sessions",
            _work,
            on_success=_done,
            on_failure=_failed,
        )

    def _show_saved_sessions(self, sessions: tuple[object, ...]) -> None:
        if self.panel.IsBeingDeleted():
            return
        self._refreshing = False
        self.refresh_sessions_btn.Enable()
        self._sessions = sessions
        self.sessions_list.Clear()
        for session in sessions:
            session_id = str(getattr(session, "session_id", ""))
            modified_at = str(getattr(session, "modified_at", ""))
            self.sessions_list.Append(
                f"{session_id} - {modified_at}" if modified_at else session_id
            )
        self._on_session_selection(None)
        count = len(sessions)
        self._set_status(
            _("No saved Copilot sessions were found on this device.")
            if count == 0
            else _("Found {count} saved Copilot session(s) on this device.").format(count=count)
        )

    def _on_session_selection(self, _event: object) -> None:
        selected = not self._refreshing and self.sessions_list.GetSelection() != self._wx.NOT_FOUND
        self.resume_session_btn.Enable(selected)
        self.delete_session_btn.Enable(selected and self.confirm_delete.GetValue())

    def _on_resume_selected(self, _event: object) -> None:
        if self._refreshing:
            return
        index = self.sessions_list.GetSelection()
        if index == self._wx.NOT_FOUND:
            return
        self._resume_session_id = str(getattr(self._sessions[index], "session_id", ""))
        self.keep_sessions.SetValue(True)
        self._set_status(
            _(
                "Saved session selected for the next Copilot task. Save the AI Hub settings "
                "with OK, then start a document task."
            )
        )

    def _on_delete_selected(self, _event: object) -> None:
        if self._refreshing:
            return
        index = self.sessions_list.GetSelection()
        if index == self._wx.NOT_FOUND or not self.confirm_delete.GetValue():
            return
        session_id = str(getattr(self._sessions[index], "session_id", ""))
        from quill.ui.update_download import thread_submit

        self._refreshing = True
        self.refresh_sessions_btn.Disable()
        self.delete_session_btn.Disable()
        self._on_session_selection(None)
        self._set_status(_("Deleting the selected Copilot session..."))

        def _work(**_kwargs: object) -> str:
            preferences = load_copilot_preferences(self._data_dir)
            if preferences.resume_session_id == session_id:
                updated = CopilotPreferences(
                    auto_tier=preferences.auto_tier,
                    keep_sessions=preferences.keep_sessions,
                    long_context=preferences.long_context,
                    share_enabled_skills=preferences.share_enabled_skills,
                )
                save_copilot_preferences(updated, self._data_dir)
            from quill.ai_packs.copilot import CopilotHarness

            CopilotHarness(agent_name=self._app_name, data_dir=self._data_dir).delete_saved_session(
                session_id
            )
            return session_id

        def _done(_name: str, _deleted_id: str) -> None:
            self._call_after(self._session_deleted)

        def _failed(_name: str, _error: BaseException) -> None:
            self._call_after(
                self._session_operation_failed,
                _("The selected Copilot session could not be deleted. Try again."),
            )

        thread_submit(
            "quill-copilot-delete-session",
            _work,
            on_success=_done,
            on_failure=_failed,
        )

    def _session_deleted(self) -> None:
        if self.panel.IsBeingDeleted():
            return
        self._refreshing = False
        self._resume_session_id = ""
        self.confirm_delete.SetValue(False)
        self._set_status(_("Saved Copilot session deleted."))
        self._on_refresh_sessions(None)

    def _session_operation_failed(self, message: str) -> None:
        if self.panel.IsBeingDeleted():
            return
        self._refreshing = False
        self.refresh_sessions_btn.Enable()
        self._on_session_selection(None)
        self._set_status(message)

    def _call_after(self, callback: Callable, *args: object) -> None:
        call_after = getattr(self._wx, "CallAfter", None)
        if callable(call_after):
            call_after(callback, *args)
        else:
            callback(*args)

    def _on_browse(self, _event: object) -> None:
        from quill.core.ai.sessions import most_recent_session
        from quill.ui.session_browser import SessionBrowserDialog

        session = most_recent_session(directory=self._directory)
        if session is None:
            self._set_status(_("No saved AI writing sessions yet"))
            from quill.ui.dialog_contract import show_message_box

            show_message_box(
                _(
                    "No saved AI writing sessions yet. Start a conversation in Ask Quill "
                    "(sessions are saved automatically as you chat), then return here to "
                    "browse and compare its branches."
                ),
                _("AI Session Branches"),
                self._wx.OK | self._wx.ICON_INFORMATION,
                self._parent_dialog,
                announce=self._announce,
            )
            return
        SessionBrowserDialog(self._parent_dialog, session, announce=self._set_status).show()


def create_sessions_panel(
    notebook: object,
    *,
    parent_dialog: object,
    announce: Callable[[str], None],
    app_name: str,
    app_context: object | None,
) -> SessionsPanel:
    data_dir = getattr(app_context, "data_dir", None)
    if data_dir is not None:
        data_dir = Path(data_dir)
    if app_name == "QUILL Lite" and data_dir is None:
        raise RuntimeError("QUILL Lite AI Hub requires its app data directory.")
    directory = Path(data_dir) / "ai-sessions" if app_name == "QUILL Lite" else None
    return SessionsPanel(
        notebook,
        parent_dialog=parent_dialog,
        announce=announce,
        directory=directory,
        data_dir=data_dir,
        app_name=app_name,
    )
