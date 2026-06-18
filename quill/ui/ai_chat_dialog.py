"""Ask AI dialog — select a provider/model, enter a prompt, view the response.

Entry point: open_ask_ai() in MainFrame (Alt+Q / Tools > Ask AI...).
A11Y-4 hardened: apply_modal_ids, public show()/close(), dialog inventory.
Status changes are announced via announce_cb so SR users hear validation errors
and async state updates (finding #43).
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

import wx

from quill.core.ai_chat import (
    PROVIDERS,
    AIChatCredentialError,
    AIModel,
    list_models,
    send_prompt,
)
from quill.core.i18n import _, lazy_gettext, ngettext
from quill.ui.dialog_contract import apply_modal_ids, show_message_box

if TYPE_CHECKING:
    from quill.core.settings import Settings

_PROVIDER_SETUP_ADVICE: dict[str, object] = {
    "openrouter": lazy_gettext(
        "OpenRouter gives access to many models with one key.\n"
        "Sign up at openrouter.ai, then paste your key above and click Save Key."
    ),
    "openai": lazy_gettext(
        "OpenAI provides GPT-4o and other models.\n"
        "Get your key from platform.openai.com under API keys.\n"
        "Paste it above and click Save Key."
    ),
    "ollama_local": lazy_gettext(
        "Ollama runs models locally — no key required.\n"
        "Install from ollama.com and run: ollama serve\n"
        "Then pull a model, e.g.: ollama pull gemma3:4b"
    ),
    "ollama_cloud": lazy_gettext(
        "Ollama Cloud hosts large models remotely.\n"
        "Sign up at ollama.com, get your API key,\n"
        "then paste it above and click Save Key."
    ),
}


def _load_api_key(provider_id: str) -> str:
    cred_name = PROVIDERS.get(provider_id, {}).get("credential_name")
    if not cred_name:
        return ""
    try:
        from quill.platform.windows.credential_store import load_secret

        return load_secret(cred_name)
    except Exception:
        return ""


def _save_api_key(provider_id: str, key: str) -> None:
    cred_name = PROVIDERS.get(provider_id, {}).get("credential_name")
    if not cred_name:
        return
    try:
        from quill.platform.windows.credential_store import save_secret

        save_secret(cred_name, key)
    except Exception:
        pass


class AskAIDialog:
    """Main Ask AI dialog: provider selector, model selector, prompt, Send."""

    def __init__(
        self,
        parent: object,
        settings: Settings,
        *,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        self._settings = settings
        self._models: list[AIModel] = []
        self._loading = False
        self._announce = announce_cb or (lambda _: None)

        self.dialog = wx.Dialog(
            parent,
            title=_("Ask AI"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(560, 480))

        root = wx.BoxSizer(wx.VERTICAL)

        # -- Provider row --
        prov_row = wx.BoxSizer(wx.HORIZONTAL)
        prov_row.Add(
            wx.StaticText(self.dialog, label=_("&Provider:")),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._provider_choice = wx.Choice(self.dialog)
        self._provider_choice.SetName("Provider")
        for pid, pdef in PROVIDERS.items():
            self._provider_choice.Append(pdef["label"], pid)
        prov_row.Add(self._provider_choice, 1)
        root.Add(prov_row, 0, wx.EXPAND | wx.ALL, 8)

        # -- API key row (shown for keyed providers) --
        key_row = wx.BoxSizer(wx.HORIZONTAL)
        key_row.Add(
            wx.StaticText(self.dialog, label=_("A&PI Key:")),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._key_ctrl = wx.TextCtrl(self.dialog, style=wx.TE_PASSWORD)
        self._key_ctrl.SetName("API key")
        self._key_ctrl.SetHint(_("Paste key here and click Save Key"))
        key_row.Add(self._key_ctrl, 1)
        self._save_key_btn = wx.Button(self.dialog, label=_("Sa&ve Key"))
        key_row.Add(self._save_key_btn, 0, wx.LEFT, 4)
        root.Add(key_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # -- Setup advice (shown when no key is stored) --
        self._advice_ctrl = wx.StaticText(self.dialog, label="")
        self._advice_ctrl.SetName("Setup advice")
        self._advice_ctrl.Wrap(520)
        root.Add(self._advice_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # -- Model row --
        model_row = wx.BoxSizer(wx.HORIZONTAL)
        model_row.Add(
            wx.StaticText(self.dialog, label=_("&Model:")),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._model_choice = wx.Choice(self.dialog)
        self._model_choice.SetName("Model")
        model_row.Add(self._model_choice, 1)
        self._refresh_btn = wx.Button(self.dialog, label=_("Re&fresh"))
        self._refresh_btn.SetToolTip(_("Reload model list from provider"))
        model_row.Add(self._refresh_btn, 0, wx.LEFT, 4)
        root.Add(model_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # -- Prompt area --
        root.Add(
            wx.StaticText(self.dialog, label=_("Pro&mpt:")),
            0,
            wx.LEFT | wx.RIGHT,
            8,
        )
        self._prompt_ctrl = wx.TextCtrl(
            self.dialog,
            style=wx.TE_MULTILINE,
        )
        self._prompt_ctrl.SetName("Prompt")
        self._prompt_ctrl.SetMinSize(wx.Size(-1, 110))
        root.Add(self._prompt_ctrl, 1, wx.EXPAND | wx.ALL, 8)

        # -- Status label --
        self._status_label = wx.StaticText(self.dialog, label="")
        self._status_label.SetName("Status")
        root.Add(self._status_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # -- Buttons --
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._send_btn = wx.Button(self.dialog, id=wx.ID_OK, label=_("&Send"))
        self._clear_btn = wx.Button(self.dialog, label=_("C&lear"))
        self._close_btn = wx.Button(self.dialog, id=wx.ID_CANCEL, label=_("C&lose"))
        btn_row.Add(self._send_btn, 0, wx.RIGHT, 4)
        btn_row.Add(self._clear_btn, 0, wx.RIGHT, 4)
        btn_row.AddStretchSpacer()
        btn_row.Add(self._close_btn, 0)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)
        self.dialog.Layout()

        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label=_("Send"),
            cancel_id=wx.ID_CANCEL,
            cancel_label=_("Close"),
        )

        self._provider_choice.Bind(wx.EVT_CHOICE, self._on_provider_changed)
        self._refresh_btn.Bind(wx.EVT_BUTTON, self._on_refresh)
        self._save_key_btn.Bind(wx.EVT_BUTTON, self._on_save_key)
        self._send_btn.Bind(wx.EVT_BUTTON, self._on_send)
        self._clear_btn.Bind(wx.EVT_BUTTON, self._on_clear)

        self._select_provider(settings.ai_chat_default_provider)
        wx.CallAfter(self._set_initial_focus)

    def _set_status(self, msg: str) -> None:
        self._set_status(msg)
        if msg:
            self._announce(msg)

    def _set_initial_focus(self) -> None:
        pid = self._current_provider_id()
        pdef = PROVIDERS.get(pid, {})
        needs_key = pdef.get("needs_key", False)
        has_key = bool(_load_api_key(pid)) if needs_key else True
        if has_key:
            self._prompt_ctrl.SetFocus()
        else:
            self._provider_choice.SetFocus()

    def _select_provider(self, provider_id: str) -> None:
        for i in range(self._provider_choice.GetCount()):
            if self._provider_choice.GetClientData(i) == provider_id:
                self._provider_choice.SetSelection(i)
                break
        else:
            if self._provider_choice.GetCount() > 0:
                self._provider_choice.SetSelection(0)
        self._on_provider_changed(None)

    def _current_provider_id(self) -> str:
        idx = self._provider_choice.GetSelection()
        if idx == wx.NOT_FOUND:
            return "openrouter"
        return self._provider_choice.GetClientData(idx)

    def _on_provider_changed(self, _event: object) -> None:
        pid = self._current_provider_id()
        pdef = PROVIDERS.get(pid, {})
        needs_key = pdef.get("needs_key", False)
        has_stored_key = bool(_load_api_key(pid)) if needs_key else True

        self._key_ctrl.Show(needs_key)
        self._save_key_btn.Show(needs_key)
        if needs_key:
            self._key_ctrl.SetValue("")
            self._key_ctrl.SetHint(
                _("Key stored — paste new key to replace")
                if has_stored_key
                else _("Paste key here and click Save Key")
            )

        advice = ""
        if needs_key and not has_stored_key:
            advice = str(_PROVIDER_SETUP_ADVICE.get(pid, _("Enter your API key above.")))
        self._advice_ctrl.SetLabel(advice)
        self._advice_ctrl.Show(bool(advice))
        self._advice_ctrl.Wrap(520)

        self.dialog.Layout()
        self._load_models_async()

    def _on_refresh(self, _event: object) -> None:
        self._load_models_async()

    def _load_models_async(self) -> None:
        if self._loading:
            return
        self._loading = True
        self._model_choice.Clear()
        self._model_choice.Append(_("Loading..."))
        self._model_choice.SetSelection(0)
        self._send_btn.Disable()
        self._set_status(_("Fetching model list..."))
        pid = self._current_provider_id()
        key = _load_api_key(pid) or self._key_ctrl.GetValue().strip()
        ollama_url = self._settings.ollama_base_url or "http://localhost:11434"

        def _fetch() -> None:
            try:
                base_url = ollama_url if pid in ("ollama_local", "ollama_cloud") else ""
                models = list_models(pid, api_key=key, base_url=base_url)
            except AIChatCredentialError as e:
                wx.CallAfter(self._on_models_loaded, [], f"No key: {e}")
                return
            except Exception as e:
                wx.CallAfter(self._on_models_loaded, [], str(e))
                return
            wx.CallAfter(self._on_models_loaded, models, "")

        threading.Thread(  # GATE-40-OK: one-shot startup fetch; self-exits.
            target=_fetch, daemon=True
        ).start()

    def _on_models_loaded(self, models: list[AIModel], error: str) -> None:
        self._loading = False
        self._model_choice.Clear()

        if error or not models:
            pid = self._current_provider_id()
            advice = str(_PROVIDER_SETUP_ADVICE.get(pid, ""))
            if not models and not error:
                error = _("No models returned by provider.")
            self._model_choice.Append(_("(no models available)"))
            self._model_choice.SetSelection(0)
            detail = error or _("No models found.")
            if advice:
                self._set_status(_("{detail}  See setup advice above.").format(detail=detail))
                self._advice_ctrl.SetLabel(advice)
                self._advice_ctrl.Show(True)
                self._advice_ctrl.Wrap(520)
                self.dialog.Layout()
            else:
                self._set_status(detail)
            self._send_btn.Disable()
            return

        self._models = models
        default = self._settings.ai_chat_default_model
        sel = 0
        for i, m in enumerate(models):
            self._model_choice.Append(m.display_name, m)
            if m.id == default:
                sel = i
        self._model_choice.SetSelection(sel)
        count = len(models)
        self._set_status(
            ngettext("{n} model available", "{n} models available", count).format(n=count)
        )
        self._send_btn.Enable()

    def _on_save_key(self, _event: object) -> None:
        pid = self._current_provider_id()
        key = self._key_ctrl.GetValue().strip()
        if key:
            _save_api_key(pid, key)
            self._key_ctrl.SetValue("")
            self._key_ctrl.SetHint(_("Key stored — paste new key to replace"))
            self._advice_ctrl.SetLabel("")
            self._advice_ctrl.Show(False)
            self.dialog.Layout()
            self._set_status(_("API key saved. Loading models..."))
            self._load_models_async()
        else:
            self._set_status(_("Paste a key above before clicking Save Key."))

    def _current_model_id(self) -> str:
        idx = self._model_choice.GetSelection()
        if idx == wx.NOT_FOUND:
            return ""
        data = self._model_choice.GetClientData(idx)
        if isinstance(data, AIModel):
            return data.id
        return ""

    def _on_send(self, _event: object) -> None:
        prompt = self._prompt_ctrl.GetValue().strip()
        if not prompt:
            self._set_status(_("Enter a prompt before sending."))
            self._prompt_ctrl.SetFocus()
            return
        model_id = self._current_model_id()
        if not model_id:
            self._set_status(_("Select a model first."))
            return
        pid = self._current_provider_id()
        pdef = PROVIDERS.get(pid, {})
        key = _load_api_key(pid) or self._key_ctrl.GetValue().strip()
        if pdef.get("needs_key") and not key:
            self._set_status(_("Save an API key for this provider first."))
            return

        ollama_url = self._settings.ollama_base_url or "http://localhost:11434"
        base_url = ollama_url if pid in ("ollama_local", "ollama_cloud") else ""

        self._send_btn.Disable()
        self._set_status(_("Sending to {model}...").format(model=model_id))

        def _do_send() -> None:
            try:
                response = send_prompt(pid, model_id, prompt, api_key=key, base_url=base_url)
                wx.CallAfter(
                    self._on_response_received,
                    response,
                    model_id,
                    pdef.get("label", pid),
                )
            except Exception as e:
                wx.CallAfter(self._on_send_error, str(e))

        threading.Thread(  # GATE-40-OK: one-shot send worker; posts via CallAfter.
            target=_do_send, daemon=True
        ).start()

    def _on_response_received(self, response: str, model_id: str, provider_label: str) -> None:
        self._send_btn.Enable()
        self._set_status(_("Response received."))
        dlg = AIResponseDialog(self.dialog, response, model_id, provider_label)
        dlg.show()
        dlg.close()

    def _on_send_error(self, error: str) -> None:
        self._send_btn.Enable()
        self._set_status(_("Error — see details."))
        show_message_box(
            _("AI request failed:\n\n{error}").format(error=error),
            _("Ask AI — Error"),
            wx.OK | wx.ICON_ERROR,
            self.dialog,
            announce=self._announce,
        )

    def _on_clear(self, _event: object) -> None:
        self._prompt_ctrl.SetValue("")
        self._set_status("")
        self._prompt_ctrl.SetFocus()

    def show(self) -> int:
        return self.dialog.ShowModal()

    def close(self) -> None:
        self.dialog.Destroy()


class AIResponseDialog:
    """Read-only response dialog with Copy to Clipboard and OK button."""

    def __init__(
        self,
        parent: object,
        response: str,
        model_id: str,
        provider_label: str,
    ) -> None:
        self._response = response

        self.dialog = wx.Dialog(
            parent,
            title=_("AI Response"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(wx.Size(560, 440))

        root = wx.BoxSizer(wx.VERTICAL)

        info = wx.StaticText(
            self.dialog,
            label=_("Model: {model}  (via {provider})").format(
                model=model_id, provider=provider_label
            ),
        )
        root.Add(info, 0, wx.ALL, 8)

        self._text_ctrl = wx.TextCtrl(
            self.dialog,
            value=response,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
        )
        self._text_ctrl.SetName("AI response")
        root.Add(self._text_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._copy_btn = wx.Button(self.dialog, label=_("&Copy to Clipboard"))
        self._ok_btn = wx.Button(self.dialog, id=wx.ID_OK, label=_("&OK"))
        btn_row.Add(self._copy_btn, 0, wx.RIGHT, 4)
        btn_row.AddStretchSpacer()
        btn_row.Add(self._ok_btn, 0)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)
        self.dialog.Layout()

        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label=_("OK"),
            cancel_id=wx.ID_OK,
            cancel_label=_("OK"),
        )

        self._copy_btn.Bind(wx.EVT_BUTTON, self._on_copy)
        self._ok_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_OK))
        self._text_ctrl.SetFocus()

    def _on_copy(self, _event: object) -> None:
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self._response))
            wx.TheClipboard.Close()

    def show(self) -> int:
        return self.dialog.ShowModal()

    def close(self) -> None:
        self.dialog.Destroy()
