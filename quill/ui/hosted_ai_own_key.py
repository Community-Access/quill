"""Use My Own API Key: AI help on the user's own OpenAI or Google Gemini account.

One window, shared by QUILL and QUILL Lite (Tools > AI in both, Alt+F2). It
says plainly where the text goes -- straight to OpenAI or Google Gemini, on the
user's account, with no QUILL server in between -- then takes the key and the model.
There is no separate switch: **a saved key (or environment key) lifts every limit**,
and **Remove the Saved Key** puts AI help straight back on QUILL's free service.

The key is stored where QUILL's AI Hub keeps its keys (Windows Credential
Manager, or an encrypted file in a portable copy), and it is never shown again
once saved.

**The model is a list, filled from the account.** Once the key is known to be
good -- Test the Key, or simply opening this window with a key already configured --
every model the key can use for text is listed, with estimated costs.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core.ai.own_key import (
    OWN_KEY_PROVIDER,
    OWN_KEY_PROVIDERS,
    active_own_key_provider,
    default_model,
    has_own_key,
)
from quill.core.ai.own_key_models import (
    choice_label,
    describe_estimate,
    estimate_note_for,
    list_models,
    pricing_url_for,
)
from quill.ui.dialog_contract import apply_modal_ids

__all__ = [
    "GEMINI_USAGE_URL",
    "OPENAI_USAGE_URL",
    "OwnKeyDialog",
    "OwnKeyUsageFrame",
    "own_key_about_text",
]

OPENAI_USAGE_URL = "https://platform.openai.com/usage"
GEMINI_USAGE_URL = "https://ai.google.dev/"

_PAD = 8

_EXPLANATION = (
    "With your own API key (OpenAI or Google Gemini), the AI help commands -- "
    "Summarize, Rewrite, Proofread, Explain, and questions about a document -- "
    "send the passage straight from this computer to the provider, on your own "
    "account. Nothing goes through QUILL's servers, there is no QUILL allowance "
    "and no size limit beyond the model's own, and the provider bills your "
    "account under its own terms.\n\n"
    "Keys set in your environment (GEMINI_API_KEY or OPENAI_API_KEY) or stored "
    "securely in Windows Credential Manager are automatically recognized."
)

_PROVIDER_CHOICES: list[tuple[str, str]] = [
    ("gemini", "Google Gemini"),
    ("openai", "OpenAI"),
]


class OwnKeyDialog(wx.Dialog):
    """Switch own-key AI on or off, and store the provider, key, and model."""

    def __init__(
        self, parent: Any, settings: Any, announce: Callable[[str], None] | None = None
    ) -> None:
        super().__init__(parent, title="Use My Own API Key")
        self._announce = announce or (lambda _message: None)
        self._settings = settings
        root = wx.BoxSizer(wx.VERTICAL)

        about_label = wx.StaticText(self, label="&About this:")
        about = wx.TextCtrl(
            self,
            value=_EXPLANATION,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
            size=(-1, 130),
        )
        about.SetHelpText("Where your text goes with your own key. Read with the arrow keys.")
        root.Add(about_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(about, 0, wx.EXPAND | wx.ALL, _PAD)

        # Provider selection
        prov_label = wx.StaticText(self, label="&Provider:")
        self._current_provider = (
            str(getattr(settings, "ai_own_key_provider", "") or "").strip().lower()
            or active_own_key_provider(settings)
        )
        prov_index = 0
        for idx, (pid, _) in enumerate(_PROVIDER_CHOICES):
            if pid == self._current_provider:
                prov_index = idx
                break
        self.provider_choice = wx.Choice(
            self, choices=[label for _, label in _PROVIDER_CHOICES]
        )
        self.provider_choice.SetSelection(prov_index)
        self.provider_choice.SetHelpText("Choose between Google Gemini and OpenAI.")
        self.provider_choice.Bind(wx.EVT_CHOICE, self._on_provider_change)
        root.Add(prov_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.provider_choice, 0, wx.EXPAND | wx.ALL, _PAD)

        saved = has_own_key(self._current_provider)
        self.key_label = wx.StaticText(self, label=self._key_label(self._current_provider, saved))
        self.key = wx.TextCtrl(self, style=wx.TE_PASSWORD)
        self.key.SetHelpText(
            "Paste your API key. It is stored securely and never shown again; "
            "leave empty to keep the existing saved or environment key."
        )
        root.Add(self.key_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.key, 0, wx.EXPAND | wx.ALL, _PAD)

        model_label = wx.StaticText(self, label="&Model:")
        self._chosen = str(getattr(settings, "ai_own_key_model", "") or "").strip()
        self._models: list[str] = [self._chosen or default_model(self._current_provider)]
        self._listed = False
        self.model = wx.Choice(
            self, choices=[choice_label(name, provider=self._current_provider) for name in self._models]
        )
        self.model.SetSelection(0)
        self.model.SetHelpText(
            "Which model answers, with an estimate of what each might cost. "
            "Every model your key can use for text is listed once checked."
        )
        self.model.Bind(wx.EVT_CHOICE, lambda _event: self._show_estimate())
        root.Add(model_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.model, 0, wx.EXPAND | wx.ALL, _PAD)

        cost_label = wx.StaticText(self, label="&Cost estimate:")
        self.cost = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2, size=(-1, 80)
        )
        self.cost.SetHelpText(
            "What the chosen model might cost for a typical request, and where real prices are."
        )
        root.Add(cost_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.cost, 0, wx.EXPAND | wx.ALL, _PAD)
        self._show_estimate()

        status_label = wx.StaticText(self, label="S&tatus:")
        self.status = wx.TextCtrl(
            self,
            value=self._saved_status(self._current_provider, saved),
            style=wx.TE_READONLY,
        )
        self.status.SetHelpText("What the last test said, or whether a key is configured.")
        root.Add(status_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.status, 0, wx.EXPAND | wx.ALL, _PAD)

        actions = wx.BoxSizer(wx.HORIZONTAL)
        test = wx.Button(self, label="Test the Ke&y")
        test.SetHelpText(
            "Checks the key with the provider, lists every usable model, then sends "
            "one tiny request to verify the connection."
        )
        test.Bind(wx.EVT_BUTTON, self._on_test)
        self.remove = wx.Button(self, label="&Remove the Saved Key")
        self.remove.SetHelpText(
            "Forgets the saved key now, and puts AI help back on QUILL's free service."
        )
        self.remove.Bind(wx.EVT_BUTTON, self._on_remove)
        self.remove.Enable(saved)
        actions.Add(test, 0, wx.RIGHT, _PAD)
        actions.Add(self.remove, 0)
        root.Add(actions, 0, wx.ALL, _PAD)

        buttons = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, _PAD)
        self.SetSizerAndFit(root)
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        self.key.SetFocus()
        if saved:
            self._list_saved_key_models()

    def _selected_provider(self) -> str:
        idx = self.provider_choice.GetSelection()
        if 0 <= idx < len(_PROVIDER_CHOICES):
            return _PROVIDER_CHOICES[idx][0]
        return "gemini"

    def _on_provider_change(self, _event: Any) -> None:
        prov = self._selected_provider()
        self._current_provider = prov
        saved = has_own_key(prov)
        self.key_label.SetLabel(self._key_label(prov, saved))
        self.status.SetValue(self._saved_status(prov, saved))
        self.remove.Enable(saved)
        self._chosen = ""
        self._models = [default_model(prov)]
        self._listed = False
        self.model.Set([choice_label(name, provider=prov) for name in self._models])
        self.model.SetSelection(0)
        self._show_estimate()
        if saved:
            self._list_saved_key_models()

    @staticmethod
    def _key_label(provider: str, saved: bool) -> str:
        prov_name = "Google Gemini" if provider == "gemini" else "OpenAI"
        if saved:
            return f"{prov_name} API &key (a key is configured; leave empty to keep it):"
        return f"{prov_name} API &key:"

    @staticmethod
    def _saved_status(provider: str, saved: bool) -> str:
        from quill.core.assistant_ai import provider_api_key_source

        prov_name = "Google Gemini" if provider == "gemini" else "OpenAI"
        source = provider_api_key_source(provider)
        if source == "environment":
            env_var = "GEMINI_API_KEY" if provider == "gemini" else "OPENAI_API_KEY"
            return f"{prov_name} is configured via your {env_var} environment variable."
        if source == "stored" or saved:
            return f"A {prov_name} key is saved, so AI help uses your {prov_name} account with no limits."
        return "No key is configured for this provider, so AI help uses QUILL's free service."

    # -- buttons ---------------------------------------------------------- #

    def _key_to_use(self) -> str:
        typed = self.key.GetValue().strip()
        if typed:
            return typed
        from quill.core.assistant_ai import load_provider_api_key

        return load_provider_api_key(self._selected_provider())

    def _set_status(self, text: str) -> None:
        if not self:
            return
        self.status.SetValue(text)
        self._announce(text)

    # -- the model list ---------------------------------------------------- #

    def _selected_model(self) -> str:
        row = self.model.GetSelection()
        prov = self._selected_provider()
        return self._models[row] if 0 <= row < len(self._models) else default_model(prov)

    def _show_estimate(self) -> None:
        prov = self._selected_provider()
        model = self._selected_model()
        self.cost.SetValue(f"{describe_estimate(model, provider=prov)}\n\n{estimate_note_for(prov)}")

    def _preferred(self, models: list[str], current: str = "") -> str:
        """The row to select: what is selected now, else what was saved, else the first."""
        for name in (current, self._chosen):
            if name and name in models:
                return name
        return models[0] if models else default_model(self._selected_provider())

    def _fill_models(self, models: list[str], select: str) -> None:
        if not self or not models:
            return
        prov = self._selected_provider()
        self._models = list(models)
        self._listed = True
        self.model.Set([choice_label(name, provider=prov) for name in self._models])
        self.model.SetSelection(self._models.index(select) if select in self._models else 0)
        self._show_estimate()

    def _list_saved_key_models(self) -> None:
        """Fill the list for a key already configured."""
        from quill.ui.update_download import thread_submit

        key = self._key_to_use()
        prov = self._selected_provider()
        if not key:
            return
        self.status.SetValue(f"Listing models for {prov}...")

        def work(**_kwargs: Any) -> tuple[list[str], str]:
            return list_models(key, provider=prov)

        def done(_name: str, result: Any) -> None:
            models, error = result
            wx.CallAfter(self._after_quiet_listing, models, error)

        thread_submit("quill-ai-own-key-models", work, on_success=done, on_failure=_ignore)

    def _after_quiet_listing(self, models: list[str], error: str) -> None:
        if not self:
            return
        if error:
            self.status.SetValue(f"The models could not be listed. {error}")
            return
        self._fill_models(models, self._preferred(models, self._selected_model()))
        prov_name = "Google Gemini" if self._selected_provider() == "gemini" else "OpenAI"
        self.status.SetValue(f"{prov_name} key ready. {len(models)} models listed.")

    def _on_test(self, _event: Any) -> None:
        key = self._key_to_use()
        prov = self._selected_provider()
        prov_name = "Google Gemini" if prov == "gemini" else "OpenAI"
        if not key:
            self._set_status(f"Enter your {prov_name} key first.")
            return
        from quill.core.assistant_ai import (
            AssistantConnectionSettings,
            default_host_for_provider,
            test_chat,
        )
        from quill.ui.update_download import thread_submit

        current = self._selected_model() if self._listed else ""
        self._set_status(f"Checking the key with {prov_name}...")

        def work(**_kwargs: Any) -> tuple[list[str], str, str]:
            models, error = list_models(key, provider=prov)
            if error:
                return [], "", f"The key did not work. {error}"
            model = self._preferred(models, current)
            connection = AssistantConnectionSettings(
                provider=prov,
                host=default_host_for_provider(prov),
                model=model,
            )
            ok, message = test_chat(connection, key)
            listed = f"The key works. {len(models)} models are listed"
            if ok:
                return models, model, f"{listed}, and {model} answered."
            return models, model, f"{listed}, but {model} did not answer. {message}"

        def done(_name: str, result: Any) -> None:
            models, model, sentence = result
            wx.CallAfter(self._after_test, models, model, sentence)

        def failed(_name: str, error: BaseException) -> None:
            wx.CallAfter(self._set_status, f"The test could not run: {error}")

        thread_submit("quill-ai-own-key-test", work, on_success=done, on_failure=failed)

    def _after_test(self, models: list[str], model: str, sentence: str) -> None:
        if not self:
            return
        self._fill_models(models, model)
        self._set_status(sentence)

    def _on_remove(self, _event: Any) -> None:
        """Forget the stored key now."""
        from quill.core.assistant_ai import clear_provider_api_key

        prov = self._selected_provider()
        prov_name = "Google Gemini" if prov == "gemini" else "OpenAI"
        clear_provider_api_key(prov)
        self.key.SetValue("")
        saved = has_own_key(prov)
        self.key_label.SetLabel(self._key_label(prov, saved))
        self.remove.Enable(saved)
        self.key.SetFocus()
        if saved:
            env_var = "GEMINI_API_KEY" if prov == "gemini" else "OPENAI_API_KEY"
            self._set_status(
                f"The saved key was removed, but a {env_var} environment variable "
                f"is still set, so AI help continues using it."
            )
            return
        self._set_status(f"The {prov_name} key was removed. AI help is back on QUILL's free service.")

    # -- after OK -------------------------------------------------------- #

    def apply(self, settings: Any) -> str:
        """Store chosen provider, typed key, and model into *settings*."""
        from quill.core.assistant_ai import save_provider_api_key

        prov = self._selected_provider()
        prov_name = "Google Gemini" if prov == "gemini" else "OpenAI"
        typed = self.key.GetValue().strip()
        settings.ai_own_key_provider = prov
        settings.ai_own_key_model = self._selected_model()
        if typed and not save_provider_api_key(prov, typed):
            return (
                f"The {prov_name} key could not be stored securely on this computer, so it was not "
                "saved. AI help stays on QUILL's free service."
            )
        if has_own_key(prov):
            return f"AI help uses your own {prov_name} key ({self._selected_model()}), with no limits."
        return "AI help uses QUILL's free service."


# --------------------------------------------------------------------------- #
# Usage and About, when AI help is on the user's own key
# --------------------------------------------------------------------------- #


def _ignore(_name: str, _error: BaseException) -> None:
    """A background listing that failed: the status line already says what to try."""


def _usage_text(model: str, provider: str = "openai") -> str:
    prov_name = "Google Gemini" if provider.strip().lower() == "gemini" else "OpenAI"
    url = pricing_url_for(provider)
    return (
        f"AI help is using your own {prov_name} key.\n\n"
        f"Model: {model}\n\n"
        f"{describe_estimate(model, provider=provider)} {estimate_note_for(provider)}\n\n"
        "To change the provider or model, press Alt+F2 or choose Use My Own API Key in the "
        "AI menu.\n\n"
        "There is no QUILL allowance and no size limit beyond the model's own. "
        f"Requests go straight from this computer to {prov_name}; nothing goes through "
        "QUILL's servers, so QUILL keeps no count of them.\n\n"
        f"Your usage and charges are on your {prov_name} account ({url}).\n\n"
        "To go back to QUILL's free AI, choose Use My Own API Key in the AI "
        "menu and press Remove the Saved Key."
    )


def own_key_about_text(model: str, provider: str = "openai") -> str:
    """What the About windows add when AI help is on the user's own key."""
    prov_name = "Google Gemini" if provider.strip().lower() == "gemini" else "OpenAI"
    url = GEMINI_USAGE_URL if provider.strip().lower() == "gemini" else OPENAI_USAGE_URL
    return (
        "\n\nAI help\n"
        f"Using your own {prov_name} key, with the model {model}. No QUILL allowance "
        "or size limit applies, and nothing goes through QUILL's servers. Your "
        f"usage and account are at: {url}"
    )


class OwnKeyUsageFrame(wx.Frame):
    """AI Usage with the user's own key: what is in use, and where the bill is."""

    def __init__(self, parent: Any, service: Any, announce: Callable[[str], None]) -> None:
        from quill.ui.hosted_ai_dialogs import _close_row, _read_only, focus_on

        super().__init__(parent, title="AI Usage")
        self._announce = announce
        prov = getattr(service, "own_key_provider", "openai")
        prov_name = "Google Gemini" if prov == "gemini" else "OpenAI"
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(sizer)
        self.body = _read_only(
            panel,
            sizer,
            f"Your own {prov_name} key",
            _usage_text(service.own_key_model, provider=prov),
            f"Which model AI help is using with your own {prov_name} key, and where your "
            "usage and charges are. Read with the arrow keys.",
        )
        usage_url = GEMINI_USAGE_URL if prov == "gemini" else OPENAI_USAGE_URL
        usage = wx.Button(panel, label=f"Open My {prov_name} &Account")
        usage.SetHelpText(
            f"Opens your {prov_name} account page in your browser."
        )
        usage.Bind(wx.EVT_BUTTON, lambda _evt: self._on_usage(usage_url))
        _close_row(self, sizer, usage)
        focus_on(self, self.body)
        self.SetInitialSize((520, 380))
        self.Centre()

    def _on_usage(self, url: str) -> None:
        if not wx.LaunchDefaultBrowser(url):
            self._announce(f"Could not open a browser. Go to {url}.")
