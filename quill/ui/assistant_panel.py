"""The "Ask Quill" AI chat dialog.

A11Y-4 hardened modal dialog (Alt+Q). Generation always runs off the UI thread
so the dialog stays responsive while the model is working.

If no AI backend is configured (neither the AI-13 connection file nor the
simple chat settings), an inline setup strip lets the user pick a provider,
enter a model ID, and supply an API key without leaving the dialog.
"""

from __future__ import annotations

import threading
import time

from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

SUGGESTED_PROMPTS: tuple[str, ...] = (
    "Summarize this document",
    "Fix spelling and grammar",
    "Write an introduction for this",
    "List the key action items",
    "Save the document",
    "Read this aloud",
)

_PROVIDER_LABELS: dict[str, str] = {
    "openrouter": "OpenRouter",
    "openai": "OpenAI",
    "ollama_local": "Ollama (local)",
    "ollama_cloud": "Ollama Cloud",
}
_PROVIDER_IDS: list[str] = list(_PROVIDER_LABELS)


def classify_assistant_error(error: str) -> tuple[str, bool]:
    """Return (user-facing message, whether to disable input)."""
    text = (error or "").strip()
    lowered = text.lower()
    if "failed to load native code" in lowered or "0xc000001d" in lowered:
        return (
            "On-device AI couldn't start. This processor may not support the built-in "
            "AI engine. Use the setup strip to connect a cloud provider, or turn AI off "
            "from Tools > AI Assistant.",
            True,
        )
    return (f"Error: {text}", False)


class AskQuillChatDialog:
    def __init__(
        self,
        parent: object,
        assistant: object,
        *,
        get_document,
        get_selection,
        insert_text,
        replace_selection,
        set_text=None,
        open_new_document=None,
        run_command,
        tool_catalog: list[tuple[str, str]],
        announce=None,
        review_changes=None,
        conversation=None,
        voice_mode=False,
        voice=None,
        signal_sound=None,
        open_speech_player=None,
        rebuild_conversation=None,
        initial_prompt="",
    ) -> None:
        import wx

        self._wx = wx
        self._assistant = assistant
        # Voice conversation mode (Companion). ``voice`` is a VoiceServices for mic
        # capture (Ctrl+F9) and spoken answers; ``signal_sound(name)`` plays an
        # earcon ("thinking"/"response"/"error"); ``open_speech_player(text)`` opens
        # the transport popup for a spoken reply. All optional — absent => text only.
        self._voice_mode = bool(voice_mode)
        self._voice = voice
        self._signal_sound = signal_sound or (lambda _name: None)
        self._open_speech_player = open_speech_player
        self._recording = False
        from quill.core.ai.thinking import ThinkingIndicator

        self._thinking = ThinkingIndicator()
        self._thinking_timer = None
        # Phase 1 companion: a callable (message, document, selection) ->
        # (answer, edited, error). When supplied, each turn runs the multi-step
        # tool loop through the Safe Editor Tool Gateway (reads, reviewed edits,
        # undo, audit) instead of the legacy decide/answer heuristic. None falls
        # back to the legacy path so provider setup still works inline.
        self._conversation = conversation
        # Rebuild the companion conversation after switching provider/model in chat, so the
        # change takes effect live (the backend reads the active connection at build time).
        self._rebuild_conversation = rebuild_conversation
        self._get_document = get_document
        self._get_selection = get_selection
        self._insert_text = insert_text
        self._replace_selection = replace_selection
        self._set_text = set_text or (lambda _t: None)
        self._open_new_document = open_new_document or (lambda _t: None)
        self._run_command = run_command
        self._review_changes = review_changes
        self._tool_titles = dict(tool_catalog)
        self._tool_ids = tuple(tid for tid, _ in tool_catalog)
        # Route announcements through the verbosity engine's legacy passthrough
        # (a no-op for the user today) so engine.speak() is reachable from this
        # call site as the verbosity rebuild migrates paths onto it.
        from quill.core.verbosity.engine import speak_legacy_text

        _base_announce = announce or (lambda _m: None)
        self._announce = lambda message: _base_announce(speak_legacy_text(message))
        self._last_response = ""
        self._first_done = False
        self._session = None
        self._pending_user_message = ""
        self._stream_active = False
        self._stream_buffer = ""
        self._stream_announced = 0
        self._stream_last = 0.0

        self.dialog = wx.Dialog(
            parent,
            title="Ask Quill",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize((760, 760))
        outer = wx.BoxSizer(wx.VERTICAL)

        self._per_provider_models: dict[str, str] = {}
        self._setup_current_provider: str = _PROVIDER_IDS[0]
        self._setup_strip = self._build_setup_strip()
        self._update_key_visibility()
        outer.Add(self._setup_strip, 0, wx.EXPAND)

        # Always-visible bar: what provider/model is active, plus a quick reveal
        # of the setup strip to switch and set the default.
        active_row = wx.BoxSizer(wx.HORIZONTAL)
        self._active_status = wx.StaticText(self.dialog, label="")
        self._active_status.SetName("Active AI provider and model")
        active_row.Add(self._active_status, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        self._change_provider_btn = wx.Button(self.dialog, label="Change provider or model")
        active_row.Add(self._change_provider_btn, 0)
        outer.Add(active_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 12)

        self._full_messages: list[str] = []
        self._transcript: list[tuple[str, str]] = []
        # Hey QUILL Phase 4: a voice question routed here pre-fills the composer
        # so the user can confirm and send; voice never fires an AI request on
        # its own (a person stays in the loop for every network call).
        self._initial_prompt = str(initial_prompt or "").strip()
        self._webview = None
        self.messages = None
        self.input = None
        self.send_button = None
        self._suggestion_buttons: list = []
        try:
            from quill.ui.accessible_webview import AccessibleWebView

            self._webview = AccessibleWebView(
                self.dialog,
                title="Conversation",
                intro=("Quill", "Hi! Ask me to write, edit, or run something in your document."),
                suggestions=SUGGESTED_PROMPTS,
                on_send=self._submit,
                on_close=self._close,
            )
            outer.Add(self._webview.control, 1, wx.EXPAND | wx.ALL, 0)
        except Exception:  # noqa: BLE001
            self._webview = None
            self._build_fallback_input(outer)

        # Approval bar — nothing touches the document until the user approves.
        self._pending = None
        self.approval_label = wx.StaticText(self.dialog, label="")
        self.approve_button = wx.Button(self.dialog, label="Approve")
        self.discard_button = wx.Button(self.dialog, label="Discard")
        approval = wx.BoxSizer(wx.HORIZONTAL)
        approval.Add(self.approval_label, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        approval.Add(self.approve_button, 0, wx.RIGHT, 8)
        approval.Add(self.discard_button, 0)
        outer.Add(approval, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 14)
        self._show_approval(False)

        # Insert chat content into the document: the last response or the whole
        # transcript, as plain text, Markdown, or HTML.
        insert_row = wx.BoxSizer(wx.HORIZONTAL)
        insert_row.Add(
            wx.StaticText(self.dialog, label="Insert into document:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._insert_scope = wx.Choice(self.dialog, choices=["Last response", "Entire transcript"])
        self._insert_scope.SetName("Insert scope")
        self._insert_scope.SetSelection(0)
        insert_row.Add(self._insert_scope, 0, wx.RIGHT, 6)
        self._insert_format = wx.Choice(self.dialog, choices=["Plain text", "Markdown", "HTML"])
        self._insert_format.SetName("Insert format")
        self._insert_format.SetSelection(0)
        insert_row.Add(self._insert_format, 0, wx.RIGHT, 6)
        self._insert_button = wx.Button(self.dialog, label="Insert")
        self._insert_button.Enable(False)
        insert_row.Add(self._insert_button, 0)
        outer.Add(insert_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 14)

        # Direct text-action row — apply the last response without going through
        # the approval flow. Replace checks for an active selection at click time.
        text_action_row = wx.BoxSizer(wx.HORIZONTAL)
        text_action_row.Add(
            wx.StaticText(self.dialog, label="Text actions:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._action_insert_btn = wx.Button(self.dialog, label="Insert at Cursor")
        self._action_insert_btn.SetName("Insert last response at cursor")
        self._action_insert_btn.Enable(False)
        text_action_row.Add(self._action_insert_btn, 0, wx.RIGHT, 6)
        self._action_replace_btn = wx.Button(self.dialog, label="Replace")
        self._action_replace_btn.SetName(
            "Replace selection with last response,"
            " or replace all document text if nothing is selected"
        )
        self._action_replace_btn.Enable(False)
        text_action_row.Add(self._action_replace_btn, 0, wx.RIGHT, 6)
        self._action_new_doc_btn = wx.Button(self.dialog, label="Open as New Document")
        self._action_new_doc_btn.SetName("Open last response as a new document")
        self._action_new_doc_btn.Enable(False)
        text_action_row.Add(self._action_new_doc_btn, 0)
        outer.Add(text_action_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 14)

        footer = wx.BoxSizer(wx.HORIZONTAL)
        self.copy_button = wx.Button(self.dialog, label="Copy Last Response")
        self.copy_button.Enable(False)
        footer.Add(self.copy_button, 0, wx.RIGHT, 8)
        footer.AddStretchSpacer()
        footer.Add(wx.Button(self.dialog, wx.ID_CANCEL, label="Close"), 0)
        outer.Add(footer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 14)
        self.dialog.SetSizer(outer)

        self.approve_button.Bind(wx.EVT_BUTTON, self._on_approve)
        self.discard_button.Bind(wx.EVT_BUTTON, self._on_discard)
        self.copy_button.Bind(wx.EVT_BUTTON, self._on_copy)
        self._insert_button.Bind(wx.EVT_BUTTON, self._on_insert_into_document)
        self._action_insert_btn.Bind(wx.EVT_BUTTON, self._on_action_insert)
        self._action_replace_btn.Bind(wx.EVT_BUTTON, self._on_action_replace)
        self._action_new_doc_btn.Bind(wx.EVT_BUTTON, self._on_action_open_new_doc)
        self._change_provider_btn.Bind(wx.EVT_BUTTON, self._on_change_provider)
        self.dialog.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self._refresh_active_status()

        # Defer the availability check off the UI thread so the dialog opens
        # immediately. The greeting and setup strip appear once the check completes.
        self._setup_strip.Hide()

        def _check_available() -> None:
            # The companion's provider was already verified when the session was
            # built, so treat the dialog as ready and skip the legacy probe.
            if self._conversation is not None:
                self._wx.CallAfter(self._on_availability_checked, True, None)
                return
            avail, reason = assistant.is_available()
            self._wx.CallAfter(self._on_availability_checked, avail, reason)

        threading.Thread(  # GATE-40-OK: availability probe; posts via CallAfter.
            target=_check_available, daemon=True
        ).start()

    def _on_availability_checked(self, available: bool, reason: str | None) -> None:
        if not available:
            self._show_setup(reason or "No AI provider is configured.")
        else:
            self._setup_strip.Hide()
            self.dialog.Layout()
        if self._webview is None:
            greeting = (
                "Hi! Ask me to write, edit, or run something in your document."
                if available
                else "Hi! Ask me to write, edit, or run something."
            )
            self._append("Quill", greeting)
        self._set_busy(not available)

    # -- Setup strip ----------------------------------------------------------

    def _build_setup_strip(self) -> object:
        wx = self._wx
        panel = wx.Panel(self.dialog)
        panel.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_INFOBK))
        sizer = wx.BoxSizer(wx.VERTICAL)

        self._setup_msg = wx.StaticText(panel, label="")
        sizer.Add(self._setup_msg, 0, wx.LEFT | wx.TOP, 8)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(panel, label="Provider:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self._setup_provider = wx.Choice(
            panel, choices=[_PROVIDER_LABELS[p] for p in _PROVIDER_IDS]
        )
        # The adjacent "Provider:" StaticText is not auto-associated as the
        # accessible name on Windows, so set it explicitly or a screen reader
        # announces this combo box unlabeled when tabbed to.
        self._setup_provider.SetName("Provider")
        self._setup_provider.SetSelection(0)
        row.Add(self._setup_provider, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)

        row.Add(wx.StaticText(panel, label="Model:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        self._setup_model = wx.TextCtrl(panel, size=wx.Size(200, -1))
        self._setup_model.SetName("Model name or ID")
        row.Add(self._setup_model, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)

        self._setup_key_lbl = wx.StaticText(panel, label="API Key:")
        self._setup_key = wx.TextCtrl(panel, style=wx.TE_PASSWORD, size=wx.Size(180, -1))
        self._setup_key.SetName("API key")
        row.Add(self._setup_key_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
        row.Add(self._setup_key, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)

        self._setup_save_btn = wx.Button(panel, label="Save && Start")
        row.Add(self._setup_save_btn, 0, wx.ALIGN_CENTER_VERTICAL)

        sizer.Add(row, 0, wx.EXPAND | wx.ALL, 8)
        panel.SetSizer(sizer)
        panel.Hide()

        self._setup_provider.Bind(wx.EVT_CHOICE, self._on_setup_provider_changed)
        self._setup_save_btn.Bind(wx.EVT_BUTTON, self._on_setup_save)
        self._prefill_setup_from_settings()
        return panel

    def _prefill_setup_from_settings(self) -> None:
        from quill.core.ai.providers import default_model_for_provider

        for pid in _PROVIDER_IDS:
            self._per_provider_models[pid] = default_model_for_provider(pid)
        try:
            from quill.core.settings import load_settings

            s = load_settings()
            saved_provider = getattr(s, "ai_chat_default_provider", "") or ""
            saved_model = (
                getattr(s, "ai_prompt_default_model", "")
                or getattr(s, "ai_chat_default_model", "")
                or ""
            )
            if saved_provider in _PROVIDER_IDS:
                self._setup_provider.SetSelection(_PROVIDER_IDS.index(saved_provider))
                self._setup_current_provider = saved_provider
            if saved_model:
                self._per_provider_models[self._setup_current_provider] = saved_model
        except Exception:  # noqa: BLE001
            pass
        self._setup_model.SetValue(self._per_provider_models.get(self._setup_current_provider, ""))

    def _on_setup_provider_changed(self, _event: object) -> None:
        from quill.core.ai.providers import default_model_for_provider

        self._per_provider_models[self._setup_current_provider] = (
            self._setup_model.GetValue().strip()
        )
        new_pid = self._provider_id_for_selection()
        self._setup_current_provider = new_pid
        model = self._per_provider_models.get(new_pid) or default_model_for_provider(new_pid)
        self._setup_model.SetValue(model)
        self._update_key_visibility()
        self._setup_model.SetFocus()
        self._setup_model.SetSelection(-1, -1)

    def _provider_id_for_selection(self) -> str:
        idx = self._setup_provider.GetSelection()
        return _PROVIDER_IDS[idx] if 0 <= idx < len(_PROVIDER_IDS) else _PROVIDER_IDS[0]

    def _update_key_visibility(self) -> None:
        from quill.core.ai_chat import PROVIDERS

        pid = self._provider_id_for_selection()
        needs = PROVIDERS.get(pid, {}).get("needs_key", True)
        self._setup_key_lbl.Show(needs)
        self._setup_key.Show(needs)
        self._setup_strip.Layout()

    def _show_setup(self, message: str) -> None:
        self._setup_msg.SetLabel(message)
        self._setup_strip.Show(True)
        self.dialog.Layout()

    def _on_setup_save(self, _event: object) -> None:
        from quill.core.ai.provider_backend import SimpleChatBackend
        from quill.core.ai_chat import PROVIDERS
        from quill.core.settings import load_settings, save_settings

        pid = self._provider_id_for_selection()
        model = self._setup_model.GetValue().strip()
        pdef = PROVIDERS.get(pid, {})
        needs_key = pdef.get("needs_key", True)
        key = self._setup_key.GetValue().strip() if needs_key else ""

        if not model:
            self._setup_msg.SetLabel("Enter a model name.")
            return
        if needs_key and not key:
            self._setup_msg.SetLabel(f"Enter an API key for {pdef.get('label', pid)}.")
            return

        try:
            s = load_settings()
            s.ai_chat_default_provider = pid
            s.ai_chat_default_model = model
            save_settings(s)
            self._per_provider_models[pid] = model
            self._setup_current_provider = pid
            if needs_key and key:
                from quill.platform.windows.credential_store import save_secret

                cred = pdef.get("credential_name") or f"quill-{pid}-api-key"
                save_secret(cred, key)
        except Exception as exc:  # noqa: BLE001
            self._setup_msg.SetLabel(f"Could not save settings: {exc}")
            return

        self._assistant.backend = SimpleChatBackend(pid, model)
        self._setup_strip.Hide()
        self._refresh_active_status()
        self.dialog.Layout()
        self._set_busy(False)
        if self._webview is None:
            self._append("Quill", "Hi! Ask me to write, edit, or run something in your document.")
        self._wx.CallAfter(self._focus_composer)

    # -- Close ----------------------------------------------------------------

    def _close(self) -> None:
        # Works whether the dialog was shown modal (EndModal) or modeless (Close ->
        # EVT_CLOSE -> Destroy, which also restores the menu bar via the on_close hook).
        if self.dialog.IsModal():
            self.dialog.EndModal(self._wx.ID_CANCEL)
        else:
            self.dialog.Close()

    def _on_char_hook(self, event: object) -> None:
        wx = self._wx
        key = event.GetKeyCode()
        if key == wx.WXK_ESCAPE:
            self._close()
            return
        # Ctrl+F9: ask a question by voice (record -> transcribe -> send).
        if key == wx.WXK_F9 and event.ControlDown():
            self._toggle_voice_question()
            return
        event.Skip()

    # -- Voice question (Ctrl+F9) ---------------------------------------------

    def _toggle_voice_question(self) -> None:
        if self._voice is None or not self._voice.input_available():
            self._announce(
                "Voice input is not available. Connect a microphone and install a "
                "speech-to-text model in Speech settings."
            )
            return
        if not self._recording:
            try:
                self._voice.start_recording()
            except Exception as exc:  # noqa: BLE001
                self._announce(f"Could not start recording: {exc}")
                return
            self._recording = True
            self._announce("Recording. Press Control F9 again to stop and send.")
            return

        self._recording = False
        self._announce("Transcribing your question")
        self._set_busy(True)

        def worker() -> None:
            try:
                text = self._voice.stop_and_transcribe()
            except Exception as exc:  # noqa: BLE001
                self._wx.CallAfter(self._on_voice_question, "", str(exc))
                return
            self._wx.CallAfter(self._on_voice_question, text, "")

        threading.Thread(  # GATE-40-OK: STT worker; posts via CallAfter.
            target=worker, daemon=True
        ).start()

    def _on_voice_question(self, text: str, error: str) -> None:
        self._set_busy(False)
        if error:
            self._announce(f"Could not transcribe: {error}")
            return
        text = (text or "").strip()
        if not text:
            self._announce("I didn't catch that. Please try again.")
            return
        self._submit(text)

    # -- Fallback UI (no WebView) ---------------------------------------------

    def _build_fallback_input(self, outer) -> None:
        wx = self._wx
        outer.Add(
            wx.StaticText(self.dialog, label="Conversation"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 14
        )
        self.messages = wx.ListBox(self.dialog, style=wx.LB_SINGLE | wx.LB_NEEDED_SB)
        self.messages.SetName("Conversation")
        outer.Add(self.messages, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 14)

        outer.Add(
            wx.StaticText(self.dialog, label="Suggestions"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 14
        )
        suggestions = wx.WrapSizer(wx.HORIZONTAL)
        for text in SUGGESTED_PROMPTS:
            button = wx.Button(self.dialog, label=text)
            button.Bind(wx.EVT_BUTTON, lambda _e, t=text: self._submit(t))
            suggestions.Add(button, 0, wx.RIGHT | wx.BOTTOM, 6)
            self._suggestion_buttons.append(button)
        outer.Add(suggestions, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 14)

        outer.Add(
            wx.StaticText(self.dialog, label="Your message"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 14
        )
        input_row = wx.BoxSizer(wx.HORIZONTAL)
        self.input = wx.TextCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
        self.input.SetName("Your message to Quill")
        self.input.SetHint("Ask Quill to write, edit, or run something…")
        input_row.Add(self.input, 1, wx.EXPAND | wx.RIGHT, 8)
        self.send_button = wx.Button(self.dialog, label="Send")
        self.send_button.SetDefault()
        input_row.Add(self.send_button, 0)
        outer.Add(input_row, 0, wx.EXPAND | wx.ALL, 14)

        self.input.Bind(wx.EVT_TEXT_ENTER, lambda _e: self._submit(self.input.GetValue()))
        self.send_button.Bind(wx.EVT_BUTTON, lambda _e: self._submit(self.input.GetValue()))

    # -- Conversation ---------------------------------------------------------

    def _append(self, speaker: str, text: str) -> None:
        self._full_messages.append(text)
        self._transcript.append((speaker, text))
        if getattr(self, "_insert_button", None) is not None:
            self._insert_button.Enable(True)
        if self._webview is not None:
            self._webview.append_message(speaker, text)
            return
        display = f"{speaker}: {' '.join(text.splitlines())}"
        index = self.messages.GetCount()
        self.messages.Append(display)
        self.messages.SetSelection(index)
        if hasattr(self.messages, "EnsureVisible"):
            self.messages.EnsureVisible(index)

    def _announce_incoming(self, text: str, *, prefix: str = "Quill says") -> None:
        compact = " ".join((text or "").split())
        if not compact:
            return
        if len(compact) > 140:
            compact = compact[:137].rstrip() + "..."
        self._announce(f"{prefix}: {compact}")

    def _set_busy(self, busy: bool) -> None:
        self._update_thinking(busy)
        if self._webview is not None:
            self._webview.set_input_enabled(not busy)
            return
        self.send_button.Enable(not busy)
        self.input.Enable(not busy)
        for button in self._suggestion_buttons:
            button.Enable(not busy)

    def _update_thinking(self, busy: bool) -> None:
        """Drive the 'thinking' / 'still thinking' cue while waiting for a reply."""
        import time

        wx = self._wx
        if busy:
            self._thinking.start(time.monotonic())
            if self._thinking_timer is None:
                self._thinking_timer = wx.Timer(self.dialog)
                self.dialog.Bind(wx.EVT_TIMER, self._on_thinking_tick, self._thinking_timer)
            self._thinking_timer.Start(1000)
        else:
            self._thinking.stop()
            if self._thinking_timer is not None:
                self._thinking_timer.Stop()

    def _on_thinking_tick(self, _event: object) -> None:
        import time

        wx = self._wx
        # Never loop the cue over a modal dialog (share consent / approval) or into the
        # background. Those run a nested event loop with busy still set, so without this
        # guard a turn that pauses for the user would repeat "still thinking" forever.
        # Only speak when our chat window is the active foreground window.
        if wx.GetActiveWindow() is not self.dialog:
            return
        if self._thinking.due_for_cue(time.monotonic()):
            self._signal_sound("thinking")
            self._announce("Quill is still thinking")

    def _focus_composer(self) -> None:
        if self._initial_prompt and self.input is not None:
            # Pre-fill once from a routed voice question, then clear so it does
            # not reappear on later focus passes. The user presses Enter to send.
            self.input.SetValue(self._initial_prompt)
            self.input.SetInsertionPointEnd()
            self._initial_prompt = ""
        if self._webview is not None:
            self._webview.focus()
        elif self.input is not None:
            self.input.SetFocus()
        else:
            self.dialog.SetFocus()

    def _submit(self, message: str) -> None:
        message = (message or "").strip()
        if not message:
            self._focus_composer()
            return
        self._append("You", message)
        self._pending_user_message = message
        if self.input is not None:
            self.input.SetValue("")
        if not self._first_done:
            self._first_done = True
            if self._webview is not None:
                self._webview.hide_suggestions()
        self._set_busy(True)
        if self._webview is not None:
            self._webview.set_status("Quill is responding")
        self._announce("Working")
        document = self._get_document()
        selection = self._get_selection()
        self._stream_active = False
        self._stream_buffer = ""
        self._stream_announced = 0
        self._stream_last = 0.0

        def worker() -> None:
            if self._conversation is not None:
                try:
                    answer, edited, error = self._conversation(message, document, selection)
                    result = ("conversation", answer or "", "edited" if edited else "", error or "")
                except Exception as exc:  # noqa: BLE001
                    result = ("error", "", "", str(exc))
                    self._pending_fallback_hint = self._fallback_hint(exc)
                self._wx.CallAfter(self._apply, *result)
                return
            try:
                decision = self._assistant.decide(message, document, self._tool_ids)
                action = decision.action
                if action == "run" and decision.tool:
                    result = ("run", "", decision.tool, "")
                elif action == "insert":
                    text = self._assistant.write_for_document(message, document)
                    result = ("insert", text, "", "")
                elif action == "replace":
                    if selection:
                        text = self._assistant.rewrite_selection(message, selection)
                    else:
                        text = self._assistant.write_for_document(message, document)
                    result = ("replace", text, "", "")
                else:
                    self._stream_active = True

                    def on_delta(fragment: str) -> None:
                        self._wx.CallAfter(self._on_stream_delta, fragment)

                    text = self._assistant.answer_stream(message, document, on_delta)
                    result = ("answer", text, "", "")
            except Exception as exc:  # noqa: BLE001
                result = ("error", "", "", str(exc))
                self._pending_fallback_hint = self._fallback_hint(exc)
            self._wx.CallAfter(self._apply, *result)

        threading.Thread(  # GATE-40-OK: streaming response worker; posts deltas via CallAfter.
            target=worker, daemon=True
        ).start()

    def _on_stream_delta(self, fragment: str) -> None:
        if not fragment:
            return
        self._stream_buffer += fragment
        now = time.monotonic()
        if now - self._stream_last < 0.8:
            return
        self._announce_stream_progress()

    def _announce_stream_progress(self) -> None:
        pending = self._stream_buffer[self._stream_announced :]
        if not pending.strip():
            return
        boundary = max(
            pending.rfind(". "),
            pending.rfind("! "),
            pending.rfind("? "),
            pending.rfind("\n"),
        )
        if boundary < 0:
            if len(pending) < 80:
                return
            consumed = len(pending)
            chunk = pending
        else:
            consumed = boundary + 1
            chunk = pending[:consumed]
        spoken = " ".join(chunk.split())
        self._stream_announced += consumed
        if not spoken:
            return
        self._stream_last = time.monotonic()
        if self._webview is not None:
            self._webview.set_status(spoken)
        else:
            self._announce(spoken)

    def _show_approval(self, show: bool, label: str = "") -> None:
        self.approval_label.SetLabel(label)
        self.approve_button.Show(show)
        self.discard_button.Show(show)
        self.approve_button.Enable(show)
        self.discard_button.Enable(show)
        self.dialog.Layout()

    def _fallback_hint(self, exc: Exception) -> str:
        """A consent-safe, accessible fallback suggestion for a failed AI call, or "".

        Uses the tested :mod:`quill.core.ai.fallback` decision: only on a connectivity
        failure (offline/timeout/rate-limit/5xx), and only for the offline direction
        (a cloud call failed and an on-device model exists). Never switches providers
        automatically — the privacy posture is the user's choice — it only announces
        the option, so a screen-reader user hears a way forward instead of a dead end.
        """
        try:
            from quill.core.ai import fallback
            from quill.core.ai.model_manager import existing_model
            from quill.core.settings import load_settings

            kind = fallback.classify_exception(exc)
            provider = str(getattr(load_settings(), "ai_chat_default_provider", "") or "")
            plan = fallback.plan_fallback(
                primary_provider=provider or "cloud",
                failure_kind=kind,
                local_available=existing_model() is not None,
                cloud_available=False,  # only the offline (cloud->local) direction here
                cloud_provider=provider,
            )
            if plan.offer and plan.to_provider == "local":
                return (
                    "The AI service could not be reached. You have an on-device model "
                    "available — open AI settings to switch to it and keep working offline."
                )
        except Exception:  # noqa: BLE001 - a fallback hint must never mask the real error
            pass
        return ""

    def _apply(self, action: str, text: str, tool: str, error: str) -> None:
        # Phase 4: after a connectivity failure, announce the consent-safe fallback
        # option (posted so it follows the error announcement below). Cleared once used.
        fallback_hint = getattr(self, "_pending_fallback_hint", "")
        self._pending_fallback_hint = ""
        if error and fallback_hint:
            self._wx.CallAfter(self._announce, fallback_hint)
        if action == "conversation":
            # The gateway already performed (and the user already reviewed) any
            # edit; here we just surface the assistant's answer. ``tool`` carries
            # the "edited" marker so we announce a change vs a plain answer.
            self._last_response = text or ""
            self._append("Quill", text or "(no response)")
            if error:
                self._signal_sound("error")
                self._announce_incoming(error, prefix="Quill error")
            elif tool == "edited":
                self._signal_sound("response")
                self._announce("Quill updated the document. Press Control Z to undo.")
            else:
                self._signal_sound("response")
                self._announce_incoming(text or "No response")
            self._record_session_exchange(text or "")
            # Voice mode: speak the reply with transport controls (Pause/Stop/Play/
            # Save). Only when a speech player was provided (TTS output available);
            # otherwise the screen reader already voiced the announcement above.
            if not error and self._voice_mode and self._open_speech_player and (text or "").strip():
                self._open_speech_player(text)
            self.copy_button.Enable(bool(self._last_response))
            self._action_insert_btn.Enable(bool(self._last_response))
            self._action_replace_btn.Enable(bool(self._last_response))
            self._action_new_doc_btn.Enable(bool(self._last_response))
            self._set_busy(False)
            if self._webview is not None:
                self._webview.set_status("Quill responded")
            self._focus_composer()
            return
        if action == "error":
            message, disable_chat = classify_assistant_error(error)
            self._append("Quill", message)
            self._announce_incoming(message, prefix="Quill error")
            if disable_chat:
                self._set_busy(True)
                if self._webview is not None:
                    self._webview.set_status("Quill is unavailable")
                self._announce("On-device AI unavailable")
                return
        elif action == "run" and tool:
            title = self._tool_titles.get(tool, tool)
            self._pending = ("run", "", tool)
            proposal = f"I'd like to run: {title}. Approve to run it."
            self._append("Quill", proposal)
            self._announce_incoming(proposal, prefix="Quill proposal")
            self._show_approval(True, f"Run “{title}”?")
        elif action in ("insert", "replace") and text:
            self._last_response = text
            self._pending = (action, text, "")
            verb = (
                "insert this at the cursor"
                if action == "insert"
                else "replace the selection with this"
            )
            proposal = f"I'd like to {verb} (approve to apply):\n{text}"
            self._append("Quill", proposal)
            self._announce_incoming(text, prefix="Quill proposal")
            self._show_approval(True, "Apply this to the document?")
            self._record_session_exchange(text)
        else:
            self._last_response = text
            self._append("Quill", text or "(no response)")
            if self._stream_active:
                self._stream_active = False
            else:
                self._announce_incoming(text or "No response")
            self._record_session_exchange(text)
        self.copy_button.Enable(bool(self._last_response))
        self._action_insert_btn.Enable(bool(self._last_response))
        self._action_replace_btn.Enable(bool(self._last_response))
        self._action_new_doc_btn.Enable(bool(self._last_response))
        self._set_busy(False)
        if self._webview is not None:
            self._webview.set_status("Quill responded")
        if self._pending:
            self._announce("Quill is proposing a change. Approve or discard.")
            self.approve_button.SetFocus()
        else:
            self._announce("Response ready")

    def _record_session_exchange(self, assistant_text: str) -> None:
        user_message = self._pending_user_message
        self._pending_user_message = ""
        if not user_message or not assistant_text:
            return
        try:
            from quill.core.ai.sessions import (
                ROLE_ASSISTANT,
                ROLE_USER,
                append_turn,
                new_session,
                save_session,
            )

            if self._session is None:
                title = " ".join(user_message.split())[:60] or "Writing session"
                self._session = new_session(title)
            self._session = append_turn(self._session, ROLE_USER, user_message)
            self._session = append_turn(self._session, ROLE_ASSISTANT, assistant_text)
            save_session(self._session)
        except Exception:  # noqa: BLE001
            pass

    def _on_approve(self, _event: object) -> None:
        if not self._pending:
            return
        action, text, tool = self._pending
        self._pending = None
        self._show_approval(False)
        try:
            if action == "run":
                title = self._tool_titles.get(tool, tool)
                self._run_command(tool)
                self._append("Quill", f"Ran: {title}")
            elif action == "insert":
                self._insert_text(text)
                self._append("Quill", "Inserted into the document.")
            elif action == "replace":
                if self._get_selection():
                    selection = self._get_selection()
                    if self._review_changes is not None and selection != text:
                        self._review_changes(selection, text, self._apply_reviewed_replace)
                        self._append("Quill", "Opened the change review.")
                    else:
                        self._replace_selection(text)
                        self._append("Quill", "Replaced the selection.")
                else:
                    self._insert_text(text)
                    self._append("Quill", "No selection — inserted at the cursor.")
        except Exception as exc:  # noqa: BLE001
            self._append("Quill", f"Couldn't apply that: {exc}")
        self._announce("Applied")
        self._focus_composer()

    def _apply_reviewed_replace(self, reviewed_text: str) -> None:
        self._replace_selection(reviewed_text)
        self._append("Quill", "Applied the reviewed changes.")
        self._announce("Applied reviewed changes")

    def _on_discard(self, _event: object) -> None:
        self._pending = None
        self._show_approval(False)
        self._append("Quill", "Discarded — nothing was changed.")
        self._announce("Discarded")
        self._focus_composer()

    def _on_copy(self, _event: object) -> None:
        wx = self._wx
        if not self._last_response:
            return
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(self._last_response))
            finally:
                wx.TheClipboard.Close()
            self._announce("Copied last response to clipboard")

    # -- Insert into document + provider status -------------------------------

    def _on_insert_into_document(self, _event: object) -> None:
        from quill.core.ai.chat_export import render_message, render_transcript

        fmt = {0: "plain", 1: "markdown", 2: "html"}.get(
            self._insert_format.GetSelection(), "plain"
        )
        if self._insert_scope.GetSelection() == 1:
            content = render_transcript(self._transcript, fmt)
            what = "transcript"
        else:
            if not self._last_response.strip():
                self._announce("No response to insert yet.")
                return
            content = render_message("", self._last_response, fmt)
            what = "last response"
        if not content.strip():
            self._announce("Nothing to insert yet.")
            return
        self._insert_text(content)
        self._announce(f"Inserted {what} into the document as {fmt}.")

    # -- Direct text actions (bypass approval flow) ---------------------------

    def _on_action_insert(self, _event: object) -> None:
        if not self._last_response:
            return
        try:
            self._insert_text(self._last_response)
        except Exception as exc:  # noqa: BLE001
            self._append("Quill", f"Couldn't insert: {exc}")
            return
        self._announce("Inserted last response at cursor")

    def _on_action_replace(self, _event: object) -> None:
        if not self._last_response:
            return
        try:
            selection = self._get_selection()
            if selection:
                self._replace_selection(self._last_response)
                self._announce("Replaced selection with last response")
            else:
                self._set_text(self._last_response)
                self._announce("Replaced all document text with last response")
        except Exception as exc:  # noqa: BLE001
            self._append("Quill", f"Couldn't replace: {exc}")

    def _on_action_open_new_doc(self, _event: object) -> None:
        if not self._last_response:
            return
        try:
            self._open_new_document(self._last_response)
        except Exception as exc:  # noqa: BLE001
            self._append("Quill", f"Couldn't open new document: {exc}")
            return
        self._announce("Opened last response as a new document")

    def _switch_provider_list(self) -> list:
        """Providers offered in the in-chat switcher: ones you've configured, plus
        on-device Ollama (which needs no key). As ``(id, display name)``."""
        import quill.core.ai.onboarding as ob

        items = list(ob.configured_cloud_providers())
        ollama = (ob.ONDEVICE_PROVIDER_OPTION.id, ob.ONDEVICE_PROVIDER_OPTION.name)
        if ollama not in items:
            items.append(ollama)
        return items

    def _on_change_provider(self, _event: object) -> None:
        """A light switcher: pick a configured provider + model and Set. No key field —
        keys come from setup; on-device Ollama needs none. Applies live to the open chat."""
        import quill.core.ai.onboarding as ob
        from quill.core.ai.providers import (
            default_model_for_provider,
            recommended_models_for_provider,
        )

        wx = self._wx
        providers = self._switch_provider_list()
        if not providers:
            # Nothing configured yet: fall back to the inline key setup for first run.
            self._show_setup("Add a provider to get started.")
            self._setup_provider.SetFocus()
            return

        dlg = wx.Dialog(self.dialog, title="Switch AI provider and model")
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(wx.StaticText(dlg, label="&Provider:"), 0, wx.LEFT | wx.TOP, 10)
        prov = wx.Choice(dlg, choices=[name for _id, name in providers])
        prov.SetName("AI provider")
        prov.SetSelection(0)
        root.Add(prov, 0, wx.EXPAND | wx.ALL, 10)
        root.Add(wx.StaticText(dlg, label="&Model:"), 0, wx.LEFT, 10)
        model_combo = wx.ComboBox(dlg, style=wx.CB_DROPDOWN)
        model_combo.SetName("Model — choose a suggestion or type a model id")
        root.Add(model_combo, 0, wx.EXPAND | wx.ALL, 10)
        buttons = dlg.CreateButtonSizer(wx.OK | wx.CANCEL)
        set_btn = dlg.FindWindowById(wx.ID_OK)
        if set_btn is not None:
            set_btn.SetLabel("Set")
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        dlg.SetSizerAndFit(root)

        def fill_models() -> None:
            pid = providers[prov.GetSelection()][0]
            model_combo.Set(recommended_models_for_provider(pid))
            model_combo.SetValue(ob.stored_provider_model(pid) or default_model_for_provider(pid))

        fill_models()
        prov.Bind(wx.EVT_CHOICE, lambda _e: fill_models())
        apply_modal_ids(dlg, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            if show_modal_dialog(dlg, "Switch AI provider and model") != wx.ID_OK:
                return
            pid, name = providers[prov.GetSelection()]
            chosen_model = model_combo.GetValue().strip() or default_model_for_provider(pid)
        finally:
            dlg.Destroy()

        if pid == "ollama":
            ob.apply_on_device_setup(model=chosen_model)
        else:
            ob.apply_cloud_setup(pid, ob.stored_provider_key(pid), model=chosen_model)
        # Apply live: the backend and companion both read the active connection at build
        # time, so rebuild them now and the open chat uses the new provider/model at once.
        try:
            from quill.core.ai.provider_backend import ProviderChatBackend

            self._assistant.backend = ProviderChatBackend()
        except Exception:  # noqa: BLE001 - never break the open chat on a switch
            pass
        if self._rebuild_conversation is not None:
            try:
                self._conversation = self._rebuild_conversation()
            except Exception:  # noqa: BLE001
                pass
        self._setup_strip.Hide()
        self._set_busy(False)
        self.dialog.Layout()
        self._refresh_active_status()
        self._announce(f"Now using {name}, model {chosen_model}.")

    def _refresh_active_status(self) -> None:
        # Read the unified assistant_ai connection so chat reflects the same provider/model
        # the wizard and the rest of the app use (not the legacy chat-only settings).
        try:
            from quill.core.ai.providers import provider_display_name
            from quill.core.assistant_ai import load_assistant_connection_settings

            conn = load_assistant_connection_settings()
            provider = conn.provider.strip().lower()
            if not provider or provider == "off":
                self._active_status.SetLabel("Active provider: (none) — choose one to start")
                return
            label = provider_display_name(provider)
            model = conn.model.strip() or "(provider default)"
            self._active_status.SetLabel(f"Active provider: {label}  —  Model: {model}")
        except Exception:  # noqa: BLE001
            self._active_status.SetLabel("")

    # -- Lifecycle ------------------------------------------------------------

    def show(self) -> None:
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_CANCEL,
            escape_id=self._wx.ID_CANCEL,
        )
        try:
            self._wx.CallAfter(self._focus_composer)
            show_modal_dialog(self.dialog, "Ask Quill")
        finally:
            self.dialog.Destroy()

    def show_modeless(self, *, on_close=None) -> None:
        """Show the chat without blocking, so the user can keep working and reach the slim
        Chat menu. ``on_close`` runs when the dialog closes (used to restore the menu bar).
        """
        self._on_close_cb = on_close
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_CANCEL,
            escape_id=self._wx.ID_CANCEL,
        )
        self.dialog.Bind(self._wx.EVT_CLOSE, self._on_evt_close)
        self.dialog.Show()
        self.dialog.Raise()
        self._wx.CallAfter(self._focus_composer)

    def _on_evt_close(self, _event: object) -> None:
        cb = getattr(self, "_on_close_cb", None)
        if cb is not None:
            try:
                cb()
            except Exception:  # noqa: BLE001 - close must always proceed
                pass
        self.dialog.Destroy()
