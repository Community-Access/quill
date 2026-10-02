"""Use My Own AI Key: AI help on the user's own OpenAI or Google Gemini account.

One window, shared by QUILL and QUILL Lite (Tools > AI in both, Alt+F2). It
opens on a **Provider** list -- OpenAI, or Google Gemini -- and everything
under it follows the choice: the About text says plainly where the text goes
for *that* company and where a key is made, the key field names the company,
the model list is that account's own models with that company's prices, and
Test the Key tests against that company. The provider is an explicit choice
saved with the settings (``ai_own_key_provider``); nothing is ever inferred
from a key that happens to be saved or from a model's name, because a request
that quietly went to a company the person did not choose is the one outcome
this window exists to prevent (qc.md X-07). Both keys may be saved; the
Provider list says which one runs, and the status line says when the other
company's key is there too.

There is no separate switch: **a saved key for the chosen provider lifts every
limit**, and **Remove the Saved Key** puts AI help straight back on QUILL's free
service. Saving a key here *is* the consent for this route: the free service's
agreement is about QUILL's servers, which this route never touches.

Each key is stored where QUILL's AI Hub keeps that provider's key (Windows
Credential Manager, or an encrypted file in a portable copy), and it is never
shown again once saved -- the box stays empty and says a key is saved. Leaving
it empty keeps the saved key. Removing takes effect at once, not at OK, and is
spoken, so nobody is left wondering which service their next request will use.

**The model is a list, filled from the account.** Once the key is known to be
good -- Test the Key, or simply opening this window with a key already saved --
every model the key can use for text is listed, the current flagship first
(:mod:`quill.core.ai.own_key_models`). Each row carries an *estimated* cost at
that company's prices, so arrowing through the list is enough to compare them,
and the Cost estimate box says plainly that the figures are estimates and where
the real prices are.

**Test the Key** checks the key by listing the models (which costs nothing),
then sends one tiny request ("reply with the word pong") to the chosen model.
Both run on a worker thread; the result arrives in the status line and is
spoken, because a label changing under an unfocused control is exactly what a
screen reader does not announce.

With a Gemini key, **Ask About an Image** works too: Gemini's models read
pictures, which the free service and an OpenAI key here do not.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core.ai.own_key import (
    OWN_KEY_PROVIDERS,
    default_model,
    has_own_key,
    key_url,
    normalize_provider,
    provider_name,
    usage_url,
)
from quill.core.ai.own_key_models import (
    choice_label,
    describe_estimate,
    estimate_note,
    list_models,
)
from quill.ui.dialog_contract import apply_modal_ids

__all__ = ["OPENAI_USAGE_URL", "OwnKeyDialog", "OwnKeyUsageFrame", "own_key_about_text"]

#: Where an OpenAI account's usage and charges are. QUILL keeps no count of
#: own-key requests -- they never reach it -- so this is the only true answer.
OPENAI_USAGE_URL = usage_url("openai")

_PAD = 8

#: The Provider list, in the order it reads.
_PROVIDER_LABELS = tuple(provider_name(p) for p in OWN_KEY_PROVIDERS)


def _explanation(provider: str) -> str:
    name = provider_name(provider)
    pictures = (
        " Gemini's models also read pictures, so Ask About an Image works with a Gemini key."
        if provider == "gemini"
        else ""
    )
    return (
        f"With your own {name} key, the AI help commands -- Summarize, Rewrite, "
        "Proofread, Explain, the dictionary and questions about a document -- send "
        f"the passage straight from this computer to {name}, on your own {name} "
        "account. Nothing goes through QUILL's servers, there is no QUILL allowance "
        f"and no size limit beyond the model's own, and {name} bills your account "
        "for each request under its own terms and privacy policy."
        f"{pictures} "
        f"Create a key at {key_url(provider)}. "
        "While a key is saved for the provider chosen above, every limit is "
        "lifted. Remove the saved key to go back to QUILL's free AI help, with its "
        "free allowance. The key is stored on this computer in Windows' credential "
        "store, the same place QUILL's AI Hub keeps it, so a key saved in either "
        "program works in both."
    )


class OwnKeyDialog(wx.Dialog):
    """Choose the provider, store the key and the model, or switch own-key AI off."""

    def __init__(
        self, parent: Any, settings: Any, announce: Callable[[str], None] | None = None
    ) -> None:
        super().__init__(parent, title="Use My Own AI Key")
        self._announce = announce or (lambda _message: None)
        self._provider = normalize_provider(getattr(settings, "ai_own_key_provider", ""))
        self._chosen = str(getattr(settings, "ai_own_key_model", "") or "").strip()
        self._listed = False
        root = wx.BoxSizer(wx.VERTICAL)

        provider_label = wx.StaticText(self, label="&Provider:")
        self.provider = wx.Choice(self, choices=list(_PROVIDER_LABELS))
        self.provider.SetSelection(OWN_KEY_PROVIDERS.index(self._provider))
        self.provider.SetHelpText(
            "Which company your key belongs to: OpenAI, or Google Gemini. Everything "
            "below follows the choice -- where the text goes, which key, which models "
            "and whose prices. AI help uses the key saved for the provider chosen here, "
            "never the other one."
        )
        self.provider.Bind(wx.EVT_CHOICE, self._on_provider)
        root.Add(provider_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.provider, 0, wx.EXPAND | wx.ALL, _PAD)

        about_label = wx.StaticText(self, label="&About this:")
        self.about = wx.TextCtrl(
            self,
            value=_explanation(self._provider),
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
            size=(-1, 150),
        )
        self.about.SetHelpText(
            "Where your text goes with your own key, and where to make one. Read "
            "with the arrow keys."
        )
        root.Add(about_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.about, 0, wx.EXPAND | wx.ALL, _PAD)

        saved = has_own_key(self._provider)
        self.key_label = wx.StaticText(self, label=self._key_label(saved))
        self.key = wx.TextCtrl(self, style=wx.TE_PASSWORD)
        self.key.SetHelpText(
            "Paste the API key for the provider chosen above. It is stored securely "
            "and never shown again; leave this empty to keep the key already saved."
        )
        root.Add(self.key_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.key, 0, wx.EXPAND | wx.ALL, _PAD)

        model_label = wx.StaticText(self, label="&Model:")
        self._models: list[str] = [self._chosen or default_model(self._provider)]
        self.model = wx.Choice(self, choices=[self._label(name) for name in self._models])
        self.model.SetSelection(0)
        self.model.SetHelpText(
            "Which model answers, with an estimate of what each might cost at the "
            "chosen provider's prices. Every model your key can use for text is "
            "listed once the key is checked, the current flagship first. You can "
            "change it here at any time."
        )
        self.model.Bind(wx.EVT_CHOICE, lambda _event: self._show_estimate())
        root.Add(model_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.model, 0, wx.EXPAND | wx.ALL, _PAD)

        cost_label = wx.StaticText(self, label="&Cost estimate:")
        self.cost = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2, size=(-1, 80)
        )
        self.cost.SetHelpText(
            "What the chosen model might cost for a typical request, and where the "
            "provider's real prices are. An estimate, not a price."
        )
        root.Add(cost_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.cost, 0, wx.EXPAND | wx.ALL, _PAD)
        self._show_estimate()

        status_label = wx.StaticText(self, label="S&tatus:")
        self.status = wx.TextCtrl(self, value=self._saved_status(saved), style=wx.TE_READONLY)
        self.status.SetHelpText("What the last test said, or whether a key is saved.")
        root.Add(status_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.status, 0, wx.EXPAND | wx.ALL, _PAD)

        actions = wx.BoxSizer(wx.HORIZONTAL)
        test = wx.Button(self, label="Test the Ke&y")
        test.SetHelpText(
            "Checks the key with the chosen provider, lists every model it can use, "
            "then sends one tiny request to the chosen model and says whether it "
            "answered. The request costs a fraction of a cent on your account."
        )
        test.Bind(wx.EVT_BUTTON, self._on_test)
        self.remove = wx.Button(self, label="&Remove the Saved Key")
        self.remove.SetHelpText(
            "Forgets the saved key for the chosen provider now, and puts AI help "
            "back on QUILL's free service with its free allowance."
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

    # -- the provider ------------------------------------------------------ #

    def _selected_provider(self) -> str:
        index = self.provider.GetSelection()
        if 0 <= index < len(OWN_KEY_PROVIDERS):
            return OWN_KEY_PROVIDERS[index]
        return self._provider

    def _on_provider(self, _event: Any) -> None:
        """Everything under the list follows it; the typed key is for the new one."""
        chosen = self._selected_provider()
        if chosen == self._provider:
            return
        self._provider = chosen
        self._listed = False
        saved = has_own_key(chosen)
        self.about.SetValue(_explanation(chosen))
        self.key.SetValue("")
        self.key_label.SetLabel(self._key_label(saved))
        self._models = [self._chosen if self._chosen and self._listed else default_model(chosen)]
        self.model.Set([self._label(name) for name in self._models])
        self.model.SetSelection(0)
        self._show_estimate()
        self.remove.Enable(saved)
        self._set_status(self._saved_status(saved))
        if saved:
            self._list_saved_key_models()

    def _key_label(self, saved: bool) -> str:
        name = provider_name(self._provider)
        if saved:
            return f"{name} API &key (a key is saved; leave empty to keep it):"
        return f"{name} API &key:"

    def _saved_status(self, saved: bool) -> str:
        name = provider_name(self._provider)
        other = next(p for p in OWN_KEY_PROVIDERS if p != self._provider)
        other_note = (
            f" A {provider_name(other)} key is saved too; choose {provider_name(other)} "
            "above to use it instead."
            if has_own_key(other)
            else ""
        )
        if saved:
            return (
                f"A {name} key is saved, so AI help uses your {name} account with no "
                f"limits.{other_note}"
            )
        return f"No {name} key is saved, so AI help uses QUILL's free service.{other_note}"

    def _label(self, model: str) -> str:
        return choice_label(model, self._provider)

    # -- buttons ---------------------------------------------------------- #

    def _key_to_use(self) -> str:
        typed = self.key.GetValue().strip()
        if typed:
            return typed
        from quill.core.assistant_ai import load_provider_api_key

        return load_provider_api_key(self._provider)

    def _set_status(self, text: str) -> None:
        if not self:
            return
        self.status.SetValue(text)
        self._announce(text)

    # -- the model list ---------------------------------------------------- #

    def _selected_model(self) -> str:
        row = self.model.GetSelection()
        if 0 <= row < len(self._models):
            return self._models[row]
        return default_model(self._provider)

    def _show_estimate(self) -> None:
        self.cost.SetValue(
            f"{describe_estimate(self._selected_model(), self._provider)}\n\n"
            f"{estimate_note(self._provider)}"
        )

    def _preferred(self, models: list[str], current: str = "") -> str:
        """The row to select: what is selected now, else what was saved, else the first."""
        for name in (current, self._chosen):
            if name and name in models:
                return name
        return models[0]

    def _fill_models(self, models: list[str], select: str) -> None:
        if not self or not models:
            return
        self._models = list(models)
        self._listed = True
        self.model.Set([self._label(name) for name in self._models])
        self.model.SetSelection(self._models.index(select) if select in self._models else 0)
        self._show_estimate()

    def _list_saved_key_models(self) -> None:
        """Fill the list for a key already saved, so the model can be changed any time.

        Quiet on success -- the list is there when the person reaches it, and a
        sentence spoken over the window's own title would be noise (GATE-13).
        """
        from quill.ui.update_download import thread_submit

        key = self._key_to_use()
        if not key:
            return
        provider = self._provider
        self.status.SetValue("Listing the models your key can use...")

        def work(**_kwargs: Any) -> tuple[list[str], str]:
            return list_models(key, provider)

        def done(_name: str, result: Any) -> None:
            models, error = result
            wx.CallAfter(self._after_quiet_listing, provider, models, error)

        thread_submit("quill-ai-own-key-models", work, on_success=done, on_failure=_ignore)

    def _after_quiet_listing(self, provider: str, models: list[str], error: str) -> None:
        if not self or provider != self._provider:
            return  # the list changed under the listing; it is for the old provider
        if error:
            self.status.SetValue(f"The models could not be listed. {error}")
            return
        self._fill_models(models, self._preferred(models, self._selected_model()))
        self.status.SetValue(
            f"A {provider_name(provider)} key is saved. {len(models)} models are listed."
        )

    def _on_test(self, _event: Any) -> None:
        provider = self._provider
        name = provider_name(provider)
        key = self._key_to_use()
        if not key:
            self._set_status(f"Enter your {name} key first.")
            return
        from quill.core.assistant_ai import (
            AssistantConnectionSettings,
            default_host_for_provider,
            test_chat,
        )
        from quill.ui.update_download import thread_submit

        current = self._selected_model() if self._listed else ""
        self._set_status(f"Checking the key with {name}...")

        def work(**_kwargs: Any) -> tuple[list[str], str, str]:
            models, error = list_models(key, provider)
            if error:
                return [], "", f"The key did not work. {error}"
            model = self._preferred(models, current)
            connection = AssistantConnectionSettings(
                provider=provider, host=default_host_for_provider(provider), model=model
            )
            ok, message = test_chat(connection, key)
            listed = f"The key works with {name}. {len(models)} models are listed"
            if ok:
                return models, model, f"{listed}, and {model} answered."
            return models, model, f"{listed}, but {model} did not answer. {message}"

        def done(_name: str, result: Any) -> None:
            models, model, sentence = result
            wx.CallAfter(self._after_test, provider, models, model, sentence)

        def failed(_name: str, error: BaseException) -> None:
            wx.CallAfter(self._set_status, f"The test could not run: {error}")

        thread_submit("quill-ai-own-key-test", work, on_success=done, on_failure=failed)

    def _after_test(self, provider: str, models: list[str], model: str, sentence: str) -> None:
        if not self or provider != self._provider:
            return
        self._fill_models(models, model)
        self._set_status(sentence)

    def _on_remove(self, _event: Any) -> None:
        """Forget the chosen provider's key now: the free service is back before OK."""
        from quill.core.assistant_ai import clear_provider_api_key

        name = provider_name(self._provider)
        clear_provider_api_key(self._provider)
        self.key.SetValue("")
        saved = has_own_key(self._provider)  # a key in the environment outlives the store
        self.key_label.SetLabel(self._key_label(saved))
        self.remove.Enable(saved)
        self.key.SetFocus()  # the button just disabled itself; focus must land somewhere
        if saved:
            self._set_status(
                f"The saved key was removed, but a {name} key is still set in the "
                "environment, so AI help keeps using it until that is removed."
            )
            return
        self._set_status(f"The {name} key was removed. AI help is back on QUILL's free service.")

    # -- after OK -------------------------------------------------------- #

    def apply(self, settings: Any) -> str:
        """Store the provider, a typed key and the model into *settings*. Returns what to say.

        The caller saves *settings*. A key that cannot be stored securely is not
        stored at all -- a key kept in plain text would be a worse outcome than
        asking again.
        """
        from quill.core.assistant_ai import save_provider_api_key

        provider = self._provider
        name = provider_name(provider)
        typed = self.key.GetValue().strip()
        settings.ai_own_key_provider = provider
        settings.ai_own_key_model = self._selected_model()
        if typed and not save_provider_api_key(provider, typed):
            return (
                "The key could not be stored securely on this computer, so it was not "
                "saved. AI help stays on QUILL's free service."
            )
        if has_own_key(provider):
            return f"AI help uses your own {name} key, with no limits."
        return "AI help uses QUILL's free service."


# --------------------------------------------------------------------------- #
# Usage and About, when AI help is on the user's own key
# --------------------------------------------------------------------------- #


def _ignore(_name: str, _error: BaseException) -> None:
    """A background listing that failed: the status line already says what to try."""


def _usage_text(model: str, provider: str = "openai") -> str:
    name = provider_name(provider)
    return (
        f"AI help is using your own {name} key.\n\n"
        f"Model: {model}\n\n"
        f"{describe_estimate(model, provider)} {estimate_note(provider)}\n\n"
        "To change the provider or the model, press Alt+F2 or choose Use My Own AI "
        "Key in the AI menu.\n\n"
        "There is no QUILL allowance and no size limit beyond the model's own. "
        f"Requests go straight from this computer to {name}; nothing goes through "
        "QUILL's servers, so QUILL keeps no count of them.\n\n"
        f"Your usage and charges are on your {name} account. Open My Usage opens "
        "that page in your browser.\n\n"
        "To go back to QUILL's free AI, choose Use My Own AI Key in the AI menu "
        "and press Remove the Saved Key."
    )


def own_key_about_text(model: str, provider: str = "openai") -> str:
    """What the About windows add when AI help is on the user's own key.

    In place of the free service's support ID and allowance, which do not apply:
    showing an allowance here would tell somebody paying per request that a
    limit they do not have is running out.
    """
    name = provider_name(provider)
    return (
        "\n\nAI help\n"
        f"Using your own {name} key, with the model {model}. No QUILL allowance "
        "or size limit applies, and nothing goes through QUILL's servers. Your "
        f"usage and charges are on your {name} account: {usage_url(provider)}"
    )


class OwnKeyUsageFrame(wx.Frame):
    """AI Usage with the user's own key: what is in use, and where the bill is.

    A different window from the free service's rather than the same one with
    fields hidden: no allowance to fetch, no sign-out, no support ID -- and so
    nothing is fetched, and the text is there the moment the window opens.
    """

    def __init__(self, parent: Any, service: Any, announce: Callable[[str], None]) -> None:
        from quill.ui.hosted_ai_dialogs import _close_row, _read_only, focus_on

        super().__init__(parent, title="AI Usage")
        self._announce = announce
        self._provider = normalize_provider(getattr(service, "own_key_provider", "openai"))
        name = provider_name(self._provider)
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(sizer)
        self.body = _read_only(
            panel,
            sizer,
            f"Your own {name} key",
            _usage_text(service.own_key_model, self._provider),
            f"Which model AI help is using with your own {name} key, and where your "
            "usage and charges are. Read with the arrow keys.",
        )
        usage = wx.Button(panel, label="Open My &Usage")
        usage.SetHelpText(
            f"Opens your {name} account's usage page in your browser, where your "
            "requests and charges are."
        )
        usage.Bind(wx.EVT_BUTTON, self._on_usage)
        _close_row(self, sizer, usage)
        focus_on(self, self.body)
        self.SetInitialSize((520, 380))
        self.Centre()

    def _on_usage(self, _event: Any) -> None:
        # The browser taking focus is what the reader announces; only a failure
        # is ours to say.
        url = usage_url(self._provider)
        if not wx.LaunchDefaultBrowser(url):
            self._announce(f"Could not open a browser. Go to {url}.")
