"""Use My ChatGPT Subscription: one window for the sign-in and the choices.

Shared by QUILL, QUILL Lite and Quill Radio, like every hosted-AI window
(:mod:`quill.ui.hosted_ai_dialogs` says why they live in ``quill/ui``). It is
built on a :class:`~quill.core.ai.chatgpt_account.ChatGptAccount` and nothing
else, so an app that has no AI service of its own -- Quill Radio -- opens the
same window as the editors, with its own agent name and its own sign-in.

**One window, three states, rebuilt in place.** Not signed in: what this does,
where the text goes, and Continue with ChatGPT. Waiting: the browser is open,
and a way to stop waiting. Signed in: the account, the model list read from the
account, whether web search is allowed, and the way out. Replacing the content
means focus never jumps to a window nobody opened, and each change is spoken,
because a label changing under an unfocused control is exactly what a screen
reader does not say (GATE-13).

**Sign Out and Forget exist only while signed in.** A button that could only
say "you are not signed in" is a stop on every Tab cycle for nothing, so
neither is built until there is something to sign out of. They differ, and the
help text says how: Sign Out asks OpenAI to revoke this computer's sign-in and
forgets it here; Forget only forgets it here, for a machine that is offline or
an account somebody has already revoked from ChatGPT's own settings.

**Choices take effect at once.** The model and the web-search switch are saved
as they change and spoken as they are saved -- there is no OK to press and no
Cancel to lose them to, because the window is modeless and a person may leave
it open behind the editor for the rest of the afternoon.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core.ai.chatgpt_account import USAGE_URL, ChatGptAccount
from quill.ui.accessible_names import set_accessible_name
from quill.ui.hosted_ai_dialogs import (
    _PAD,
    _close_row,
    _read_only,
    focus_on,
    show_problem,
    take_focus,
)

__all__ = ["TITLE", "ChatGptFrame", "chatgpt_about_text"]

TITLE = "Use My ChatGPT Subscription"


def _explanation(agent: str) -> str:
    return (
        f"If you pay for ChatGPT, {agent} can use that plan instead of QUILL's free AI "
        "or an API key. Choose Continue with ChatGPT: your browser opens on "
        f"OpenAI's sign-in page, you allow {agent} to use your plan, and you come "
        "back here. There is no key to paste and nothing to pay per request; what "
        "you use counts toward your ChatGPT plan's own usage, which OpenAI "
        "enforces and shows in ChatGPT's settings. "
        "While you are signed in, every AI request goes straight from this "
        "computer to OpenAI on your account, under OpenAI's terms and privacy "
        "policy. Nothing goes through QUILL's servers, and QUILL keeps no copy. "
        "A ChatGPT sign-in is used ahead of a saved OpenAI key. "
        f"The sign-in is kept in Windows' credential store, for {agent} alone; each "
        "QUILL app signs in on its own, and Sign Out here is how you undo it."
    )


def chatgpt_about_text(account: ChatGptAccount) -> str:
    """What the About windows add when AI help is on a ChatGPT plan."""
    model = account.model or "no model chosen yet"
    return (
        "\n\nAI help\n"
        f"Using your ChatGPT subscription ({account.state.account_label}), with the "
        f"model {model}. No QUILL allowance or size limit applies, and nothing goes "
        f"through QUILL's servers. Your plan's usage is at {USAGE_URL}"
    )


class ChatGptFrame(wx.Frame):
    """Sign in with ChatGPT, choose the model, and sign out again."""

    def __init__(
        self,
        parent: wx.Window | None,
        account: ChatGptAccount,
        announce: Callable[[str], None],
        *,
        on_change: Callable[[], None] | None = None,
        list_models: Callable[[], list[Any]] | None = None,
    ) -> None:
        super().__init__(parent, title=TITLE)
        self._account = account
        self._announce = announce
        self._on_change = on_change or (lambda: None)
        self._list_models = list_models or self._default_list_models
        self._models: list[Any] = []
        self._confirming_sign_out = False
        self._busy = False

        panel = wx.Panel(self)
        self._sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(self._sizer)
        self._panel = panel
        self.SetInitialSize((620, 520))
        self.Centre()
        if account.signed_in:
            self._show_signed_in()
        else:
            self._show_signed_out()

    # -- plumbing ---------------------------------------------------------- #

    @property
    def agent(self) -> str:
        return self._account.agent_name

    def _clear(self) -> None:
        self._sizer.Clear(delete_windows=True)
        self._confirming_sign_out = False

    def _default_list_models(self) -> list[Any]:
        from quill.core.ai.chatgpt_client import list_models

        return list_models(self._account.access_token())

    def _changed(self) -> None:
        try:
            self._on_change()
        except Exception:  # noqa: BLE001 - a host refresh must not break the window
            pass

    def _say(self, message: str) -> None:
        if not self:
            return
        show_problem(self, self._status, message, self._announce)

    # -- state 1: not signed in ------------------------------------------------ #

    def _show_signed_out(self, said: str = "") -> None:
        if not self:
            return
        self._clear()
        panel = self._panel
        about = _read_only(
            panel,
            self._sizer,
            "About this",
            _explanation(self.agent),
            "Where your text goes with a ChatGPT subscription, and what it costs. "
            "Read with the arrow keys.",
        )
        self._status = _read_only(
            panel,
            self._sizer,
            "Status",
            said or f"{self.agent} is not signed in with ChatGPT.",
            "Whether this app is signed in, and what the last step said.",
            grow=False,
        )
        cont = wx.Button(panel, label="&Continue with ChatGPT")
        cont.SetHelpText(
            "Opens OpenAI's sign-in page in your browser. Sign in, allow this app "
            "to use your plan, and come back here; this window says when it is done."
        )
        cont.Bind(wx.EVT_BUTTON, lambda _e: self._on_continue())
        _close_row(self, self._sizer, cont)
        panel.Layout()
        focus_on(self, about if not said else self._status)
        take_focus(self)

    def _on_continue(self) -> None:
        if self._busy:
            return
        self._busy = True
        self._show_waiting()
        from quill.ui.update_download import thread_submit

        account = self._account

        def waiting(url: str) -> None:
            wx.CallAfter(self._browser_state, url)

        def work(**_kwargs: Any) -> Any:
            return account.sign_in(on_waiting=waiting)

        def done(_name: str, _state: Any) -> None:
            wx.CallAfter(self._after_sign_in)

        def failed(_name: str, error: BaseException) -> None:
            wx.CallAfter(self._sign_in_failed, _sentence(error))

        thread_submit("quill-ai-chatgpt-sign-in", work, on_success=done, on_failure=failed)

    # -- state 2: waiting for the browser -------------------------------------- #

    def _show_waiting(self) -> None:
        self._clear()
        panel = self._panel
        self._status = _read_only(
            panel,
            self._sizer,
            "Status",
            "Opening your browser on OpenAI's sign-in page...",
            "What is happening. This window says when the sign-in is done.",
        )
        cancel = wx.Button(panel, label="&Stop Waiting")
        cancel.SetHelpText("Stops waiting for the browser. Nothing is changed; you can try again.")
        cancel.Bind(wx.EVT_BUTTON, lambda _e: self._account.cancel_sign_in())
        self._copy_url = wx.Button(panel, label="Copy the Sign-In &Address")
        self._copy_url.SetHelpText(
            "Puts the sign-in address on the clipboard, for a browser that did not open on its own."
        )
        self._copy_url.Hide()
        _close_row(self, self._sizer, cancel, self._copy_url)
        panel.Layout()
        focus_on(self, self._status)
        take_focus(self)

    def _browser_state(self, url: str) -> None:
        """The browser has been asked to open; *url* is set only when it could not be."""
        if not self or self._account.signed_in and not self._busy:
            return
        if url:
            self._status.SetValue(
                "Your browser did not open. Choose Copy the Sign-In Address, paste "
                "it into any browser on this computer, and finish there."
            )
            self._copy_url.Bind(wx.EVT_BUTTON, lambda _e, u=url: self._copy(u))
            self._copy_url.Show()
            self._panel.Layout()
            self._announce("Your browser did not open. Copy the Sign-In Address is available.")
            return
        self._status.SetValue(
            "Waiting for you to finish in your browser. Sign in to ChatGPT, allow "
            f"{self.agent} to use your plan, and come back here."
        )
        self._announce("Waiting for your browser.")

    def _copy(self, text: str) -> None:
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(text))
            finally:
                wx.TheClipboard.Close()
            self._announce("Address copied.")

    def _sign_in_failed(self, message: str) -> None:
        self._busy = False
        if not self:
            self._announce(message)
            return
        self._show_signed_out(said=message)
        self._announce(message)

    def _after_sign_in(self) -> None:
        self._busy = False
        self._changed()
        if not self:
            self._announce(f"Signed in with ChatGPT as {self._account.state.account_label}.")
            return
        self._show_signed_in(fresh=True)

    # -- state 3: signed in ---------------------------------------------------- #

    def _show_signed_in(self, fresh: bool = False) -> None:
        if not self:
            return
        self._clear()
        panel = self._panel
        state = self._account.state
        account = _read_only(
            panel,
            self._sizer,
            "Account",
            f"{self.agent} is signed in with ChatGPT as {state.account_label}. "
            "AI requests go straight from this computer to OpenAI on your plan, "
            "and count toward your plan's own usage.",
            "Which ChatGPT account this app is signed in with, and what that means.",
            grow=False,
        )

        model_label = wx.StaticText(panel, label="&Model")
        self._model = wx.Choice(panel, choices=[])
        set_accessible_name(self._model, "Model")
        self._model.SetHelpText(
            "Which model answers, from the list your ChatGPT plan offers. The "
            "choice is saved as soon as you make it."
        )
        self._model.Bind(wx.EVT_CHOICE, lambda _e: self._on_model_chosen())
        self._sizer.Add(model_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        self._sizer.Add(self._model, 0, wx.EXPAND | wx.ALL, _PAD)

        self._web = wx.CheckBox(panel, label="Allow &web search")
        self._web.SetValue(bool(state.web_search))
        self._web.SetHelpText(
            "When checked, the model may search the web through OpenAI to answer "
            "a question. Off, only what you send is used. Saved as soon as you change it."
        )
        self._web.Bind(wx.EVT_CHECKBOX, lambda _e: self._on_web_changed())
        self._sizer.Add(self._web, 0, wx.ALL, _PAD)

        self._status = _read_only(
            panel,
            self._sizer,
            "Status",
            "Listing the models your plan offers...",
            "What the last step said: the models listed, a choice saved, or what went wrong.",
            grow=False,
        )

        usage = wx.Button(panel, label="Open ChatGPT &Usage")
        usage.SetHelpText(
            "Opens ChatGPT's own usage page in your browser, where your plan's "
            "limits and what is left are shown."
        )
        usage.Bind(wx.EVT_BUTTON, lambda _e: self._open_usage())
        refresh = wx.Button(panel, label="&Refresh Models")
        refresh.SetHelpText("Asks your ChatGPT plan for its model list again.")
        refresh.Bind(wx.EVT_BUTTON, lambda _e: self._refresh_models())
        self._sign_out = wx.Button(panel, label="Sign &Out")
        self._sign_out.SetHelpText(
            f"Asks OpenAI to revoke {self.agent}'s sign-in and forgets it on this "
            "computer. AI help goes back to QUILL's free service, or to a saved "
            "OpenAI key if you have one. Press twice."
        )
        self._sign_out.Bind(wx.EVT_BUTTON, lambda _e: self._on_sign_out())
        forget = wx.Button(panel, label="&Forget on This Computer")
        forget.SetHelpText(
            "Forgets the sign-in here without telling OpenAI, for a computer that "
            f"is offline or a sign-in you already removed in ChatGPT's settings. "
            f"{self.agent} stays listed there until you remove it."
        )
        forget.Bind(wx.EVT_BUTTON, lambda _e: self._on_forget())
        _close_row(self, self._sizer, usage, refresh, self._sign_out, forget)
        panel.Layout()
        focus_on(self, account if not fresh else self._model)
        take_focus(self)
        if fresh:
            self._announce(f"Signed in with ChatGPT as {state.account_label}.")
        self._refresh_models(quiet=not fresh)

    def _on_model_chosen(self) -> None:
        row = self._model.GetSelection()
        if not 0 <= row < len(self._models):
            return
        model = self._models[row]
        self._account.set_model(model.slug)
        self._changed()
        self._status.SetValue(f"{model.label} is the model AI help will use.")

    def _on_web_changed(self) -> None:
        allowed = bool(self._web.GetValue())
        self._account.set_web_search(allowed)
        self._changed()
        if allowed:
            self._status.SetValue("Web search is allowed.")
        else:
            self._status.SetValue("Web search is off; only what you send is used.")

    def _open_usage(self) -> None:
        # The browser taking focus is what the reader announces; only a failure is ours to say.
        if not wx.LaunchDefaultBrowser(USAGE_URL):
            self._announce(f"Could not open a browser. Go to {USAGE_URL}.")

    # -- the model list ---------------------------------------------------------- #

    def _refresh_models(self, quiet: bool = False) -> None:
        from quill.ui.update_download import thread_submit

        def work(**_kwargs: Any) -> list[Any]:
            return list(self._list_models())

        def done(_name: str, models: Any) -> None:
            wx.CallAfter(self._fill_models, list(models), quiet)

        def failed(_name: str, error: BaseException) -> None:
            wx.CallAfter(self._models_failed, _sentence(error))

        thread_submit("quill-ai-chatgpt-models", work, on_success=done, on_failure=failed)

    def _fill_models(self, models: list[Any], quiet: bool) -> None:
        if not self or not hasattr(self, "_model") or not self._model:
            return
        self._models = models
        self._model.Set([_choice_label(m) for m in models])
        if not models:
            self._status.SetValue("Your plan listed no models that can answer text.")
            return
        chosen = self._account.model
        slugs = [m.slug for m in models]
        if chosen not in slugs:
            # No choice yet, or a model the plan no longer offers: the first
            # listed is the plan's own best, and saving it means the first
            # request needs no visit here.
            chosen = slugs[0]
            self._account.set_model(chosen)
            self._changed()
        self._model.SetSelection(slugs.index(chosen))
        sentence = f"{len(models)} models are listed; {chosen} is chosen."
        self._status.SetValue(sentence)
        if not quiet:
            self._announce(sentence)

    def _models_failed(self, message: str) -> None:
        if not self or not hasattr(self, "_status"):
            return
        if not self._account.signed_in:
            # The refresh found the sign-in gone: say so, and show the way back in.
            self._changed()
            self._show_signed_out(said=message)
            self._announce(message)
            return
        self._say(f"The models could not be listed. {message}")

    # -- the way out ------------------------------------------------------------- #

    def _on_sign_out(self) -> None:
        """Confirm in place with a second press -- never a modal over a modeless frame."""
        if not self._confirming_sign_out:
            self._confirming_sign_out = True
            self._sign_out.SetLabel("Yes, Sign &Out")
            self._announce("Press again to sign out of ChatGPT.")
            return
        from quill.ui.update_download import thread_submit

        account = self._account
        self._sign_out.Disable()
        self._status.SetValue("Signing out...")

        def work(**_kwargs: Any) -> bool:
            return account.sign_out()

        def done(_name: str, confirmed: Any) -> None:
            wx.CallAfter(self._after_sign_out, bool(confirmed))

        def failed(_name: str, _error: BaseException) -> None:
            wx.CallAfter(self._after_sign_out, False)

        thread_submit("quill-ai-chatgpt-sign-out", work, on_success=done, on_failure=failed)

    def _after_sign_out(self, confirmed: bool) -> None:
        self._changed()
        said = (
            "Signed out of ChatGPT."
            if confirmed
            else (
                "Signed out on this computer. ChatGPT could not be told, so you may "
                f"also want to remove {self.agent} under Apps in ChatGPT's settings."
            )
        )
        if not self:
            self._announce(said)
            return
        self._show_signed_out(said=said)
        self._announce(said)

    def _on_forget(self) -> None:
        self._account.forget()
        self._changed()
        said = (
            f"Forgotten on this computer. {self.agent} stays listed under Apps in "
            "ChatGPT's settings until you remove it there."
        )
        self._show_signed_out(said=said)
        self._announce(said)


def _choice_label(model: Any) -> str:
    slug = str(getattr(model, "slug", model))
    label = str(getattr(model, "label", slug))
    return label if label == slug else f"{label} ({slug})"


def _sentence(error: BaseException) -> str:
    from quill.ui.hosted_ai_service import _sentence as sentence

    return sentence(error)
