"""Use My Own OpenAI Key: AI help on the user's own account, with no allowance.

One window, shared by QUILL and QUILL Lite (Tools > AI in both, Alt+F2). It
says plainly where the text goes -- straight to OpenAI, on the user's account,
with no QUILL server in between -- then takes the key and the model. There is no
separate switch: **a saved key lifts every limit**, and **Remove the Saved Key**
puts AI help straight back on QUILL's free service. Saving a key here *is* the
consent for this route: the free service's agreement is about QUILL's servers,
which this route never touches.

The key is stored where QUILL's AI Hub keeps its OpenAI key (Windows Credential
Manager, or an encrypted file in a portable copy), and it is never shown again
once saved -- the box stays empty and says a key is saved. Leaving it empty
keeps the saved key. Removing takes effect at once, not at OK, and is spoken, so
nobody is left wondering which service their next request will use.

**The model is a list, filled from the account.** Once the key is known to be
good -- Test the Key, or simply opening this window with a key already saved --
every model the key can use for text is listed, Luna 6 and GPT-6 models first
(:mod:`quill.core.ai.own_key_models`). Each row carries an *estimated* cost, so
arrowing through the list is enough to compare them, and the Cost estimate box
says plainly that the figures are estimates and where OpenAI's real prices are.
Because opening the window lists the models, the model can be changed at any
time: Alt+F2, pick another, OK.

**Test the Key** checks the key by listing the models (which costs nothing),
then sends one tiny request ("reply with the word pong") to the chosen model.
Both run on a worker thread; the result arrives in the status line and is
spoken, because a label changing under an unfocused control is exactly what a
screen reader does not announce.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core.ai.own_key import OWN_KEY_PROVIDER, default_model, has_own_key
from quill.core.ai.own_key_models import (
    ESTIMATE_NOTE,
    choice_label,
    describe_estimate,
    list_models,
)
from quill.ui.dialog_contract import apply_modal_ids

__all__ = ["OPENAI_USAGE_URL", "OwnKeyDialog", "OwnKeyUsageFrame", "own_key_about_text"]

#: Where an OpenAI account's usage and charges are. QUILL keeps no count of
#: own-key requests -- they never reach it -- so this is the only true answer.
OPENAI_USAGE_URL = "https://platform.openai.com/usage"

_PAD = 8

_EXPLANATION = (
    "With your own OpenAI key, the AI help commands -- Summarize, Rewrite, "
    "Proofread, Explain and questions about a document -- send the passage "
    "straight from this computer to OpenAI, on your own OpenAI account. "
    "Nothing goes through QUILL's servers, there is no QUILL allowance and no "
    "size limit beyond the model's own, and OpenAI bills your account for each "
    "request under its own terms and privacy policy. "
    "Create a key at platform.openai.com, under API keys. "
    "While a key is saved, every limit is lifted. Remove the saved key to go "
    "back to QUILL's free AI help, with its free allowance. "
    "The key is stored on this computer in Windows' credential store, the same "
    "place QUILL's AI Hub keeps it, so a key saved in either program works in both."
)


class OwnKeyDialog(wx.Dialog):
    """Switch own-key AI on or off, and store the key and the model."""

    def __init__(
        self, parent: Any, settings: Any, announce: Callable[[str], None] | None = None
    ) -> None:
        super().__init__(parent, title="Use My Own OpenAI Key")
        self._announce = announce or (lambda _message: None)
        root = wx.BoxSizer(wx.VERTICAL)

        about_label = wx.StaticText(self, label="&About this:")
        about = wx.TextCtrl(
            self,
            value=_EXPLANATION,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
            size=(-1, 140),
        )
        about.SetHelpText("Where your text goes with your own key. Read with the arrow keys.")
        root.Add(about_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(about, 0, wx.EXPAND | wx.ALL, _PAD)

        saved = has_own_key()
        self.key_label = wx.StaticText(self, label=self._key_label(saved))
        self.key = wx.TextCtrl(self, style=wx.TE_PASSWORD)
        self.key.SetHelpText(
            "Paste your OpenAI API key. It starts with sk-. It is stored securely "
            "and never shown again; leave this empty to keep the key already saved."
        )
        root.Add(self.key_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.key, 0, wx.EXPAND | wx.ALL, _PAD)

        model_label = wx.StaticText(self, label="&Model:")
        self._chosen = str(getattr(settings, "ai_own_key_model", "") or "").strip()
        self._models: list[str] = [self._chosen or default_model()]
        self._listed = False
        self.model = wx.Choice(self, choices=[choice_label(name) for name in self._models])
        self.model.SetSelection(0)
        self.model.SetHelpText(
            "Which OpenAI model answers, with an estimate of what each might cost. "
            "Every model your key can use for text is listed once the key is "
            "checked, Luna 6 and GPT-6 models first. You can change it here at "
            "any time."
        )
        self.model.Bind(wx.EVT_CHOICE, lambda _event: self._show_estimate())
        root.Add(model_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.model, 0, wx.EXPAND | wx.ALL, _PAD)

        cost_label = wx.StaticText(self, label="&Cost estimate:")
        self.cost = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2, size=(-1, 80)
        )
        self.cost.SetHelpText(
            "What the chosen model might cost for a typical request, and where "
            "OpenAI's real prices are. An estimate, not OpenAI's price."
        )
        root.Add(cost_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.cost, 0, wx.EXPAND | wx.ALL, _PAD)
        self._show_estimate()

        status_label = wx.StaticText(self, label="S&tatus:")
        self.status = wx.TextCtrl(
            self,
            value=self._saved_status(saved),
            style=wx.TE_READONLY,
        )
        self.status.SetHelpText("What the last test said, or whether a key is saved.")
        root.Add(status_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.status, 0, wx.EXPAND | wx.ALL, _PAD)

        actions = wx.BoxSizer(wx.HORIZONTAL)
        test = wx.Button(self, label="Test the Ke&y")
        test.SetHelpText(
            "Checks the key with OpenAI, lists every model it can use, then sends "
            "one tiny request to the chosen model and says whether it answered. "
            "The request costs a fraction of a cent on your account."
        )
        test.Bind(wx.EVT_BUTTON, self._on_test)
        self.remove = wx.Button(self, label="&Remove the Saved Key")
        self.remove.SetHelpText(
            "Forgets the saved OpenAI key now, and puts AI help back on QUILL's "
            "free service with its free allowance."
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

    @staticmethod
    def _key_label(saved: bool) -> str:
        if saved:
            return "OpenAI API &key (a key is saved; leave empty to keep it):"
        return "OpenAI API &key:"

    @staticmethod
    def _saved_status(saved: bool) -> str:
        if saved:
            return "A key is saved, so AI help uses your OpenAI account with no limits."
        return "No key is saved, so AI help uses QUILL's free service."

    # -- buttons ---------------------------------------------------------- #

    def _key_to_use(self) -> str:
        typed = self.key.GetValue().strip()
        if typed:
            return typed
        from quill.core.assistant_ai import load_provider_api_key

        return load_provider_api_key(OWN_KEY_PROVIDER)

    def _set_status(self, text: str) -> None:
        if not self:
            return
        self.status.SetValue(text)
        self._announce(text)

    # -- the model list ---------------------------------------------------- #

    def _selected_model(self) -> str:
        row = self.model.GetSelection()
        return self._models[row] if 0 <= row < len(self._models) else default_model()

    def _show_estimate(self) -> None:
        self.cost.SetValue(f"{describe_estimate(self._selected_model())}\n\n{ESTIMATE_NOTE}")

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
        self.model.Set([choice_label(name) for name in self._models])
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
        self.status.SetValue("Listing the models your key can use...")

        def work(**_kwargs: Any) -> tuple[list[str], str]:
            return list_models(key)

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
        self.status.SetValue(f"A key is saved. {len(models)} models are listed.")

    def _on_test(self, _event: Any) -> None:
        key = self._key_to_use()
        if not key:
            self._set_status("Enter your OpenAI key first.")
            return
        from quill.core.assistant_ai import (
            AssistantConnectionSettings,
            default_host_for_provider,
            test_chat,
        )
        from quill.ui.update_download import thread_submit

        current = self._selected_model() if self._listed else ""
        self._set_status("Checking the key with OpenAI...")

        def work(**_kwargs: Any) -> tuple[list[str], str, str]:
            models, error = list_models(key)
            if error:
                return [], "", f"The key did not work. {error}"
            model = self._preferred(models, current)
            connection = AssistantConnectionSettings(
                provider=OWN_KEY_PROVIDER,
                host=default_host_for_provider(OWN_KEY_PROVIDER),
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
        """Forget the key now: the free service is back before the window closes."""
        from quill.core.assistant_ai import clear_provider_api_key

        clear_provider_api_key(OWN_KEY_PROVIDER)
        self.key.SetValue("")
        saved = has_own_key()  # an OPENAI_API_KEY in the environment outlives the store
        self.key_label.SetLabel(self._key_label(saved))
        self.remove.Enable(saved)
        self.key.SetFocus()  # the button just disabled itself; focus must land somewhere
        if saved:
            self._set_status(
                "The saved key was removed, but an OPENAI_API_KEY environment variable "
                "is still set, so AI help keeps using it until that is removed."
            )
            return
        self._set_status("The key was removed. AI help is back on QUILL's free service.")

    # -- after OK -------------------------------------------------------- #

    def apply(self, settings: Any) -> str:
        """Store a typed key and the model into *settings*. Returns what to say.

        The caller saves *settings*. A key that cannot be stored securely is not
        stored at all -- a key kept in plain text would be a worse outcome than
        asking again.
        """
        from quill.core.assistant_ai import save_provider_api_key

        typed = self.key.GetValue().strip()
        settings.ai_own_key_model = self._selected_model()
        if typed and not save_provider_api_key(OWN_KEY_PROVIDER, typed):
            return (
                "The key could not be stored securely on this computer, so it was not "
                "saved. AI help stays on QUILL's free service."
            )
        if has_own_key():
            return "AI help uses your own OpenAI key, with no limits."
        return "AI help uses QUILL's free service."


# --------------------------------------------------------------------------- #
# Usage and About, when AI help is on the user's own key
# --------------------------------------------------------------------------- #


def _ignore(_name: str, _error: BaseException) -> None:
    """A background listing that failed: the status line already says what to try."""


def _usage_text(model: str) -> str:
    return (
        "AI help is using your own OpenAI key.\n\n"
        f"Model: {model}\n\n"
        f"{describe_estimate(model)} {ESTIMATE_NOTE}\n\n"
        "To change the model, press Alt+F2 or choose Use My Own OpenAI Key in the "
        "AI menu.\n\n"
        "There is no QUILL allowance and no size limit beyond the model's own. "
        "Requests go straight from this computer to OpenAI; nothing goes through "
        "QUILL's servers, so QUILL keeps no count of them.\n\n"
        "Your usage and charges are on your OpenAI account. Open My OpenAI Usage "
        "opens that page in your browser.\n\n"
        "To go back to QUILL's free AI, choose Use My Own OpenAI Key in the AI "
        "menu and press Remove the Saved Key."
    )


def own_key_about_text(model: str) -> str:
    """What the About windows add when AI help is on the user's own key.

    In place of the free service's support ID and allowance, which do not apply:
    showing an allowance here would tell somebody paying per request that a
    limit they do not have is running out.
    """
    return (
        "\n\nAI help\n"
        f"Using your own OpenAI key, with the model {model}. No QUILL allowance "
        "or size limit applies, and nothing goes through QUILL's servers. Your "
        f"usage and charges are on your OpenAI account: {OPENAI_USAGE_URL}"
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
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(sizer)
        self.body = _read_only(
            panel,
            sizer,
            "Your own OpenAI key",
            _usage_text(service.own_key_model),
            "Which model AI help is using with your own OpenAI key, and where your "
            "usage and charges are. Read with the arrow keys.",
        )
        usage = wx.Button(panel, label="Open My OpenAI &Usage")
        usage.SetHelpText(
            "Opens your OpenAI account's usage page in your browser, where your "
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
        if not wx.LaunchDefaultBrowser(OPENAI_USAGE_URL):
            self._announce(f"Could not open a browser. Go to {OPENAI_USAGE_URL}.")
