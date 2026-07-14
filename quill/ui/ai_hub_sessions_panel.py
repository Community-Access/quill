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

from quill.core.i18n import _


class SessionsPanel:
    """The Sessions tab panel and its behaviour."""

    def __init__(
        self,
        notebook: object,
        *,
        parent_dialog: object,
        announce: Callable[[str], None],
    ) -> None:
        import wx

        self._wx = wx
        self._parent_dialog = parent_dialog
        self._announce = announce

        self.panel = wx.Panel(notebook)
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

        self.panel.SetSizer(sizer)
        self.browse_btn.Bind(wx.EVT_BUTTON, self._on_browse)

    def _set_status(self, message: str) -> None:
        self.status.SetLabel(message)
        if message:
            self._announce(message)

    def _on_browse(self, _event: object) -> None:
        from quill.core.ai.sessions import most_recent_session
        from quill.ui.session_browser import SessionBrowserDialog

        session = most_recent_session()
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
