"""Use My Own AI Key: AI help on the user's own account with the provider they chose.

One window, shared by QUILL and QUILL Lite (Tools > AI in both, Alt+F2). It
opens on a **Provider** list -- OpenAI, Google Gemini, Anthropic Claude,
OpenRouter, Ollama Cloud, a custom OpenAI-compatible service, or Ollama on this
computer (:mod:`quill.core.ai.own_key_providers`; the last five were the AI
Hub's list until decision 20 folded it in here) -- and everything under it
follows the choice: the About text says plainly where the text goes
for *that* company and where a key is made, the key field names the company,
the model list is that account's own models with that company's prices, and
Test the Key tests against that company. The provider is an explicit choice
saved with the settings (``ai_own_key_provider``); nothing is ever inferred
from a key that happens to be saved or from a model's name, because a request
that quietly went to a company the person did not choose is the one outcome
this window exists to prevent (qc.md X-07). Several keys may be saved; the
Provider list says which one runs, and the status line says when another
company's key is there too.

**Ollama on this computer needs no key**: the key box is off, the About text
starts "Runs on this computer. Nothing is sent.", and the Server address box
says where Ollama is listening. A custom service has a Server address too. The
model list for Ollama is whatever ``/api/tags`` reports, never a list kept here.

**One choice for every AI feature.** OK also makes the provider the one QUILL's
advanced features use, which the AI Hub's Provider list used to set
(:func:`~quill.core.ai.own_key_providers.use_for_advanced_features`).

There is no separate switch: **a saved key for the chosen provider lifts every
limit**, and **Remove the Saved Key** forgets it; if this route was the AI in use,
no AI is in use until the person chooses one (decision 15, never a silent
fall-back). Saving a key here *is* the consent for this route: the free service's
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

With an OpenAI, Gemini or Anthropic Claude key, **Ask About an Image** and the
media apps' picture commands work too: those providers' models read pictures,
which the free service does not (``connection_caps``, each claim with its source).
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
from quill.core.ai.own_key_providers import (
    HOST_PROVIDERS,
    LOCAL_ABOUT,
    host_for,
    is_local,
    needs_key,
    save_host,
    use_for_advanced_features,
)
from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.dpi import dip_size

__all__ = ["OPENAI_USAGE_URL", "OwnKeyDialog", "own_key_about_text"]

#: Where an OpenAI account's usage and charges are. QUILL keeps no count of
#: own-key requests -- they never reach it -- so this is the only true answer.
OPENAI_USAGE_URL = usage_url("openai")

_PAD = 8

#: The Provider list, in the order it reads.
_PROVIDER_LABELS = tuple(provider_name(p) for p in OWN_KEY_PROVIDERS)


def _local_explanation(provider: str) -> str:
    name = provider_name(provider)
    return (
        f"{LOCAL_ABOUT} With {name}, the AI help commands -- Summarize, Rewrite, "
        "Proofread, Explain, the dictionary and questions about a document -- are "
        "answered by a model running on this computer. No key is needed, nothing "
        "is billed, and there is no allowance and no size limit beyond the model's "
        "own. Install Ollama from ollama.com and pull a model first; the Model list "
        "shows every model Ollama has, and the Server address says where it listens. "
        "A model that reads pictures, as Ollama reports it, also answers Ask About "
        "an Image."
    )


def _explanation(provider: str) -> str:
    if is_local(provider):
        return _local_explanation(provider)
    name = provider_name(provider)
    address = (
        "Type the service's address in Server address below. " if provider in HOST_PROVIDERS else ""
    )
    pictures = (
        f" {name}'s models also read pictures, so Ask About an Image works with this key."
        if provider in ("openai", "gemini", "claude")
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
        f"Create a key at {key_url(provider)}. {address}"
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
            "Which provider answers: OpenAI, Google Gemini, Anthropic Claude, "
            "OpenRouter, Ollama Cloud, a custom service, or Ollama on this computer, "
            "which needs no key. Everything below follows the choice -- where the text "
            "goes, which key, which models and whose prices. AI help uses the key "
            "saved for the provider chosen here, never another one."
        )
        self.provider.Bind(wx.EVT_CHOICE, self._on_provider)
        root.Add(provider_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.provider, 0, wx.EXPAND | wx.ALL, _PAD)

        about_label = wx.StaticText(self, label="&About this:")
        self.about = wx.TextCtrl(
            self,
            value=_explanation(self._provider),
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
            size=dip_size(self, -1, 150),
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

        host_label = wx.StaticText(self, label="Ser&ver address:")
        self.host = wx.TextCtrl(self, value=host_for(self._provider))
        self.host.SetHelpText(
            "Where a custom service or Ollama on this computer is listening, for "
            "example http://localhost:11434 for Ollama. The other providers have a "
            "fixed address, so this box is off for them."
        )
        root.Add(host_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.host, 0, wx.EXPAND | wx.ALL, _PAD)

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
            self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2, size=dip_size(self, -1, 80)
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
        test = self.test = wx.Button(self, label="Test the Ke&y")
        test.SetHelpText(
            "Checks the key with the chosen provider, lists every model it can use, "
            "then sends one tiny request to the chosen model and says whether it "
            "answered. The request costs a fraction of a cent on your account; with "
            "Ollama on this computer it checks Ollama is running and costs nothing."
        )
        test.Bind(wx.EVT_BUTTON, self._on_test)
        self.remove = wx.Button(self, label="&Remove the Saved Key")
        self.remove.SetHelpText(
            "Forgets the saved key for the chosen provider now. If that key was the "
            "AI in use, no AI is in use until you choose one in Choose Your AI."
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
        self._follow_provider_fields()
        (self.key if needs_key(self._provider) else self.provider).SetFocus()
        if saved:
            self._list_saved_key_models()

    # -- the provider ------------------------------------------------------ #

    def _selected_provider(self) -> str:
        index = self.provider.GetSelection()
        if 0 <= index < len(OWN_KEY_PROVIDERS):
            return OWN_KEY_PROVIDERS[index]
        return self._provider

    def _follow_provider_fields(self) -> None:
        """The key box, the address box, Remove and Test follow the provider."""
        keyed = needs_key(self._provider)
        self.key.Enable(keyed)
        self.host.Enable(self._provider in HOST_PROVIDERS)
        self.host.SetValue(host_for(self._provider))
        self.remove.Enable(keyed and has_own_key(self._provider))
        self.test.SetLabel("Test the Ke&y" if keyed else "Test the Connectio&n")

    def _host(self) -> str:
        """The address typed for a provider that has one, else ""."""
        return self.host.GetValue().strip() if self._provider in HOST_PROVIDERS else ""

    def _list(self, key: str, provider: str) -> tuple[list[str], str]:
        """The provider's model list, at the typed address when it has one."""
        host = self._host()
        return list_models(key, provider, host=host) if host else list_models(key, provider)

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
        self._follow_provider_fields()
        self._set_status(self._saved_status(saved))
        if saved:
            self._list_saved_key_models()

    def _key_label(self, saved: bool) -> str:
        name = provider_name(self._provider)
        if not needs_key(self._provider):
            return f"API &key (none is needed for {name}):"
        if saved:
            return f"{name} API &key (a key is saved; leave empty to keep it):"
        return f"{name} API &key:"

    def _saved_status(self, saved: bool) -> str:
        name = provider_name(self._provider)
        if is_local(self._provider):
            return f"AI help uses {name}. {LOCAL_ABOUT}"
        other = next(
            (
                p
                for p in OWN_KEY_PROVIDERS
                if p != self._provider and needs_key(p) and has_own_key(p)
            ),
            "",
        )
        other_note = (
            f" A {provider_name(other)} key is saved too; choose {provider_name(other)} "
            "above to use it instead."
            if other
            else ""
        )
        if saved:
            return (
                f"A {name} key is saved, so AI help uses your {name} account with no "
                f"limits.{other_note}"
            )
        return f"No {name} key is saved, so this route cannot be used until one is.{other_note}"

    def _label(self, model: str) -> str:
        return choice_label(model, self._provider)

    # -- buttons ---------------------------------------------------------- #

    def _key_to_use(self) -> str:
        if not needs_key(self._provider):
            return ""
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
        if not key and needs_key(self._provider):
            return
        provider = self._provider
        self.status.SetValue("Listing the models your key can use...")

        def work(**_kwargs: Any) -> tuple[list[str], str]:
            return self._list(key, provider)

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
        found = f"{len(models)} models are listed."
        self.status.SetValue(
            f"{provider_name(provider)} is ready. {found}"
            if is_local(provider)
            else f"A {provider_name(provider)} key is saved. {found}"
        )

    def _on_test(self, _event: Any) -> None:
        provider = self._provider
        name = provider_name(provider)
        key = self._key_to_use()
        keyed = needs_key(provider)
        if not key and keyed:
            self._set_status(f"Enter your {name} key first.")
            return
        from quill.core.assistant_ai import AssistantConnectionSettings, test_chat
        from quill.ui.update_download import thread_submit

        current = self._selected_model() if self._listed else ""
        host = self._host() or host_for(provider)
        self._set_status(f"Checking the key with {name}..." if keyed else f"Checking {name}...")

        def work(**_kwargs: Any) -> tuple[list[str], str, str]:
            models, error = self._list(key, provider)
            if error:
                failed = "The key did not work." if keyed else f"{name} did not answer."
                return [], "", f"{failed} {error}"
            model = self._preferred(models, current)
            connection = AssistantConnectionSettings(provider=provider, host=host, model=model)
            ok, message = test_chat(connection, key)
            works = f"The key works with {name}." if keyed else f"{name} is running."
            listed = f"{works} {len(models)} models are listed"
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
        """Forget the chosen provider's key now, before OK (no fall-back, decision 15)."""
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
        self._set_status(f"The {name} key was removed.")

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
        typed = self.key.GetValue().strip() if needs_key(provider) else ""
        settings.ai_own_key_provider = provider
        settings.ai_own_key_model = self._selected_model()
        if provider in HOST_PROVIDERS:
            try:
                save_host(provider, self.host.GetValue())
            except OSError:
                return f"The server address could not be saved, so {name} keeps the old one."
        if typed and not save_provider_api_key(provider, typed):
            return "The key could not be stored securely on this computer, so it was not saved."
        if not has_own_key(provider):
            return f"No {name} key is saved, so this route cannot be used until one is."
        try:  # the advanced AI features follow the same choice (decision 20)
            use_for_advanced_features(provider, settings.ai_own_key_model)
        except Exception:  # noqa: BLE001 - the basic AI is saved either way
            pass
        if is_local(provider):
            return f"AI help uses {name}. {LOCAL_ABOUT}"
        return f"AI help uses your own {name} key, with no limits."


# --------------------------------------------------------------------------- #
# Usage and About, when AI help is on the user's own key
# --------------------------------------------------------------------------- #


def _ignore(_name: str, _error: BaseException) -> None:
    """A background listing that failed: the status line already says what to try."""


def own_key_about_text(model: str, provider: str = "openai") -> str:
    """What the About windows add when AI help is on the user's own key.

    In place of the free service's support ID and allowance, which do not apply:
    showing an allowance here would tell somebody paying per request that a
    limit they do not have is running out.
    """
    name = provider_name(provider)
    if is_local(provider):
        return f"\n\nAI help\nUsing {name}, with the model {model}. {LOCAL_ABOUT}"
    return (
        "\n\nAI help\n"
        f"Using your own {name} key, with the model {model}. No QUILL allowance "
        "or size limit applies, and nothing goes through QUILL's servers. Your "
        f"usage and charges are on your {name} account: {usage_url(provider)}"
    )
