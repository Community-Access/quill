"""ADP Assistant wiring (mixin on ``MainFrame``) -- pre-release, unlock-gated.

Everything here is invisible until ``future.adp_assistant`` is unlocked by a
signed code (Help > Redeem Unlock Code...): the Media menu items are only
built when the feature is enabled, and the commands are registered with the
feature id so the palette and keybindings obey the same gate. Deliberately
absent from user documentation until public launch.

The rich ADP Settings dialog lives inline here (a small wx form): server
address, client access key (stored in the OS credential vault, never
settings), your first name (personalizes answers and keys rate limits),
speak-answers default, and hands-free conversation routing (spoken
questions from the existing Hey QUILL flow open Ask ADP pre-filled --
voice capture and speech never leave this device).
"""

from __future__ import annotations

from quill.core.adp.models import AskResponse

_ADP_SAFE_MODE_MESSAGE = "The ADP Assistant is disabled in Safe Mode."


class AdpMixin:
    """Adds the (unlock-gated) ADP Assistant to ``MainFrame``."""

    # -- menu ------------------------------------------------------------------

    def _append_adp_media_items(self, media_menu: object) -> None:
        """Called from the Media submenu builder; no-op unless unlocked."""
        if not self._feature_enabled("future.adp_assistant"):
            return
        wx = self._wx
        media_menu.AppendSeparator()
        ask_id = wx.NewIdRef()
        media_menu.Append(ask_id, self._menu_label("Ask AD&P...", "adp.ask"))
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_ask_adp(), id=ask_id)
        settings_id = wx.NewIdRef()
        media_menu.Append(settings_id, "ADP Se&ttings...")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_adp_settings(), id=settings_id)

    def _register_adp_commands(self) -> None:
        self.commands.try_register(
            "adp.ask",
            "ADP: Ask about Described Movies and TV...",
            self.open_ask_adp,
            self._binding_for("adp.ask"),
            feature_id="future.adp_assistant",
        )
        self.commands.try_register(
            "adp.settings",
            "ADP: Settings...",
            self.open_adp_settings,
            self._binding_for("adp.settings"),
            feature_id="future.adp_assistant",
        )

    # -- ask ----------------------------------------------------------------------

    def open_ask_adp(self, *, initial_question: str = "", auto_ask: bool = False) -> None:
        if self._safe_mode:
            self._show_message_box(
                _ADP_SAFE_MODE_MESSAGE, "ADP Assistant", self._wx.ICON_INFORMATION | self._wx.OK
            )
            return
        from quill.core.adp import client as adp_client
        from quill.ui.adp_dialog import AdpAskDialog

        def _ask(question: str, *, history: list[object] | None = None) -> AskResponse:
            return adp_client.ask(
                question,
                base_url=str(
                    getattr(self.settings, "adp_base_url", "") or adp_client.DEFAULT_BASE_URL
                ),
                history=history,
                user_name=str(getattr(self.settings, "adp_user_name", "")),
                safe_mode=self._safe_mode,
            )

        dialog = AdpAskDialog(
            self.frame,
            ask=_ask,
            task_manager=self._task_manager,
            speak_answers=bool(getattr(self.settings, "adp_speak_answers", True)),
            initial_question=initial_question,
            auto_ask=auto_ask,
            announce_cb=self._announce,
        )
        dialog.show()

    def _adp_route_voice_question(self, transcript: str) -> bool:
        """Hands-free hook for the existing voice-question router: when the
        feature is unlocked and conversation routing is on, a spoken question
        opens Ask ADP pre-filled and auto-asks. Returns True when consumed."""
        if not self._feature_enabled("future.adp_voice_mode"):
            return False
        if not bool(getattr(self.settings, "adp_route_voice_questions", False)):
            return False
        from quill.core.speech.voice_routing import QUESTION, classify, question_text

        if classify(transcript) != QUESTION:
            return False
        self._announce("Asking ADP.")
        self.open_ask_adp(initial_question=question_text(transcript), auto_ask=True)
        return True

    # -- settings --------------------------------------------------------------------

    def open_adp_settings(self) -> None:
        from quill.core.adp import client as adp_client
        from quill.core.settings import save_settings
        from quill.ui.dialog_contract import set_accessible_name

        wx = self._wx
        dialog = wx.Dialog(self.frame, title="ADP Settings")
        root = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(cols=2, vgap=8, hgap=8)
        grid.AddGrowableCol(1, 1)

        grid.Add(wx.StaticText(dialog, label="&Server address:"), 0, wx.ALIGN_CENTER_VERTICAL)
        url_ctrl = wx.TextCtrl(
            dialog,
            value=str(getattr(self.settings, "adp_base_url", "") or adp_client.DEFAULT_BASE_URL),
        )
        set_accessible_name(url_ctrl, "ADP server address; https only")
        grid.Add(url_ctrl, 1, wx.EXPAND)

        grid.Add(wx.StaticText(dialog, label="Client access &key:"), 0, wx.ALIGN_CENTER_VERTICAL)
        key_ctrl = wx.TextCtrl(dialog, style=wx.TE_PASSWORD, value=adp_client.load_client_key())
        set_accessible_name(
            key_ctrl, "ADP client access key; stored in the system credential vault"
        )
        grid.Add(key_ctrl, 1, wx.EXPAND)

        grid.Add(wx.StaticText(dialog, label="Your &first name:"), 0, wx.ALIGN_CENTER_VERTICAL)
        name_ctrl = wx.TextCtrl(dialog, value=str(getattr(self.settings, "adp_user_name", "")))
        set_accessible_name(name_ctrl, "First name, used to personalize spoken answers; optional")
        grid.Add(name_ctrl, 1, wx.EXPAND)

        root.Add(grid, 0, wx.EXPAND | wx.ALL, 10)

        speak_check = wx.CheckBox(dialog, label="S&peak answers automatically")
        set_accessible_name(speak_check, "Speak each ADP answer aloud through Quill's own voice")
        speak_check.SetValue(bool(getattr(self.settings, "adp_speak_answers", True)))
        root.Add(speak_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        voice_check = wx.CheckBox(
            dialog, label="Route spoken &questions to ADP (hands-free conversation)"
        )
        set_accessible_name(
            voice_check,
            "When Hey Quill hears a question, open Ask ADP with it and ask "
            "immediately; voice stays on this device",
        )
        voice_check.SetValue(bool(getattr(self.settings, "adp_route_voice_questions", False)))
        voice_check.Enable(self._feature_enabled("future.adp_voice_mode"))
        root.Add(voice_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        save_btn = wx.Button(dialog, id=wx.ID_OK, label="&Save")
        cancel_btn = wx.Button(dialog, id=wx.ID_CANCEL, label="Cancel")
        buttons.Add(save_btn, 0, wx.RIGHT, 6)
        buttons.Add(cancel_btn, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        dialog.SetSizerAndFit(root)

        from quill.ui.dialog_contract import apply_modal_ids

        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        dialog.CentreOnParent()
        result = self._show_modal_dialog(dialog, "ADP Settings")
        if result == wx.ID_OK:
            url = url_ctrl.GetValue().strip()
            if url and not url.startswith("https://"):
                self._announce("The server address must start with https; not saved.")
            else:
                self.settings.adp_base_url = url
            self.settings.adp_user_name = name_ctrl.GetValue().strip()
            self.settings.adp_speak_answers = speak_check.GetValue()
            self.settings.adp_route_voice_questions = voice_check.GetValue()
            save_settings(self.settings)
            if not adp_client.save_client_key(key_ctrl.GetValue()):
                self._announce(
                    "Settings saved, but the access key could not be stored "
                    "in the credential vault."
                )
            else:
                self._announce("ADP settings saved.")
        dialog.Destroy()
