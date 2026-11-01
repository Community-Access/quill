"""Choose Your AI: one window for where AI comes from (codex.md 10A.3).

Shared by QUILL and QUILL Lite like every hosted-AI window, and built from the
same furniture (:mod:`quill.ui.hosted_ai_dialogs`). Opened by Ctrl+4, by Which
AI Am I Using pressed twice, by the AI status cell, and by the three older
account commands -- Use My Own AI Key, Use My ChatGPT Subscription and Connect
or Sign Out -- each on its own row with its sign-in step ready.

**Five controls, nothing else.** The Connections list, the About line, the
Model choice, one action button whose label follows the row, and Close. Focus
lands on the list, on the row in use. Enter does the button's job; Delete on a
signed-in row signs it out after a Yes/No whose default is No.

**What is spoken (GATE-13).** Nothing on open, on a selection change or on
focus: the reader already says the title, the row and its state. Only outcomes
the app alone knows -- "Now using My ChatGPT plan.", "Signed in to My ChatGPT
plan. It is now in use.", "Signed out. No AI is in use until you choose one."
-- through the host's announcement service, so they are brailled too
(GATE-BRAILLE). When an action changes a row, the row's text changes with it,
so arrowing away and back reads the truth.

**Sign-in reuses what exists.** The ChatGPT plan uses the loopback sign-in in
one small modal step (:class:`SignInStep`); the own key uses ``OwnKeyDialog``;
the free AI uses its Connect step, which never happens on its own (decision
23). Copilot and Codex say "not available yet" until their phases ship.

The sentences are :mod:`quill.core.ai.connection_words`; this module composes
none of its own beyond the help text.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import wx

from quill.core.ai import connection_words as words
from quill.core.ai.connection_caps import CHATGPT, CODEX, CONNECTION_NAMES, FREE, OWN_KEY
from quill.core.ai.connection_choice import IN_USE, NOT_AVAILABLE_YET, SIGNED_IN
from quill.ui.accessible_names import set_accessible_name
from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids, show_modal_dialog
from quill.ui.dpi import dip_size
from quill.ui.hosted_ai_dialogs import _PAD, _close_row, _read_only, focus_on

__all__ = ["SIGN_IN_TITLE", "TITLE", "ChooseAiFrame", "ChooseAiHooks", "SignInStep", "ask_yes_no"]

TITLE = "Choose Your AI"
SIGN_IN_TITLE = "Sign In to Your AI"
_READING_MODELS = "Reading the model list..."


@dataclass
class ChooseAiHooks:
    """What the window needs from the editor, and nothing more."""

    announce: Callable[[str], None]
    #: The free AI's Connect step (agreement first, then the code).
    connect_free: Callable[[], None]
    #: Use My Own AI Key's dialog; returns the sentence to say, or "" on Cancel.
    own_key: Callable[[], str]
    #: The connection changed: menus and the status cell follow.
    changed: Callable[[], None]
    app_name: str = "QUILL"
    safe_mode: bool = False
    #: ``connection -> ([(id, label), ...], error)``; blocking, run off the UI thread.
    list_models: Callable[[str], tuple[list[tuple[str, str]], str]] | None = None


def ask_yes_no(parent: Any, sentence: str, *, default_yes: bool) -> bool:
    """A Yes/No question through the dialog contract. True for Yes."""
    style = wx.YES_NO | wx.ICON_QUESTION | (wx.YES_DEFAULT if default_yes else wx.NO_DEFAULT)
    dialog = wx.MessageDialog(parent, sentence, TITLE, style)
    try:
        return show_modal_dialog(dialog, TITLE) == wx.ID_YES
    finally:
        dialog.Destroy()


class SignInStep(wx.Dialog):
    """The one small sign-in step: one sentence, Open the Page, Cancel.

    The same layout for every connection; only the nouns change. On success
    the step closes itself and the window says what happened.
    """

    def __init__(self, parent: Any, sentence: str, on_open: Callable[[SignInStep], None]) -> None:
        super().__init__(parent, title=SIGN_IN_TITLE)
        self._on_open = on_open
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        self.status = _read_only(
            self,
            sizer,
            "What to do",
            sentence,
            "What this step is for, and what is happening now. If your browser does "
            "not open, the address to use appears here.",
            grow=False,
        )
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.AddStretchSpacer(1)
        self.open_button = wx.Button(self, label="&Open the Page")
        self.open_button.SetHelpText(
            "Opens the sign-in page in your web browser. Approve there and come back; "
            "this step closes itself when the sign-in is done."
        )
        self.open_button.SetDefault()
        self.open_button.Bind(wx.EVT_BUTTON, lambda _e: self._open())
        cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Stops the sign-in. Nothing changes.")
        row.Add(self.open_button, 0, wx.RIGHT, _PAD)
        row.Add(cancel, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, _PAD)
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL, cancel_label="Cancel")
        self.SetInitialSize(dip_size(self, 520, 240))
        self.Centre()
        self.open_button.SetFocus()

    def _open(self) -> None:
        self.open_button.Disable()
        self.status.SetValue("Waiting for you to finish in your browser...")
        self._on_open(self)

    def succeeded(self) -> None:
        if self and self.IsModal():
            self.EndModal(wx.ID_OK)

    def failed(self, message: str) -> None:
        if not self:
            return
        self.status.SetValue(message)
        self.open_button.Enable()
        self.status.SetFocus()  # the reader says a field's text as it takes focus


def _chatgpt_sign_in(parent: Any, account: Any, connection: str, app_name: str) -> bool:
    """The plan's loopback sign-in, in the one sign-in step. True when signed in."""
    from quill.ui.hosted_ai_connection_route import plain_sentence
    from quill.ui.update_download import thread_submit

    def start(step: SignInStep) -> None:
        def waiting(url: str) -> None:
            if url:  # set only when the browser did not open on its own
                wx.CallAfter(
                    step.failed,
                    f"Your browser did not open. Paste this address into a browser: {url}",
                )

        thread_submit(
            "quill-ai-choose-sign-in",
            lambda **_k: account.sign_in(on_waiting=waiting),
            on_success=lambda _n, _s: wx.CallAfter(step.succeeded),
            on_failure=lambda _n, error: wx.CallAfter(step.failed, plain_sentence(error)),
        )

    step = SignInStep(parent, words.sign_in_sentence(connection, app_name), start)
    try:
        result = show_modal_dialog(step, SIGN_IN_TITLE)
    finally:
        step.Destroy()
    if result != wx.ID_OK:
        try:
            account.cancel_sign_in()
        except Exception:  # noqa: BLE001 - nothing was waiting
            pass
        return False
    return bool(getattr(account, "signed_in", False))


class ChooseAiFrame(wx.Frame):
    """The Connections list, About, Model, the action button and Close."""

    def __init__(
        self, parent: Any, service: Any, hooks: ChooseAiHooks, *, select: str = ""
    ) -> None:
        super().__init__(parent, title=TITLE)
        self._service = service
        self._hooks = hooks
        self._rows: list[Any] = []
        self._models: dict[str, tuple[list[tuple[str, str]], str]] = {}
        self._shown_models: list[tuple[str, str]] = []
        #: Connections whose model list has been asked for in this window.
        self._asked: set[str] = set()

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(sizer)

        label = wx.StaticText(panel, label="&Connections")
        self._list = wx.ListBox(panel, style=wx.LB_SINGLE)
        set_accessible_name(self._list, "Connections")
        self._list.SetHelpText(
            "Where your AI comes from. Each row says its name and whether it is in "
            "use, signed in or not set up. Enter uses the row, or signs in to it; "
            "Delete on a signed-in row signs it out after asking."
        )
        self._list.Bind(wx.EVT_LISTBOX, lambda _e: self._follow_row())
        apply_listbox_activation(self._list, lambda _e: self.do_action())
        self._list.Bind(wx.EVT_KEY_DOWN, self._on_list_key)
        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        sizer.Add(self._list, 1, wx.EXPAND | wx.ALL, _PAD)

        self._about = _read_only(
            panel,
            sizer,
            "About this connection",
            "",
            "Who receives your text, what it costs and what it can do, for the row "
            "selected in the list.",
            grow=False,
        )

        model_label = wx.StaticText(panel, label="&Model")
        self._model = wx.Choice(panel)
        set_accessible_name(self._model, "Model")
        self._model.SetHelpText(
            "The model this connection answers with, from the service's own list. "
            "The first is the service's recommendation. Your choice is saved at once."
        )
        self._model.Bind(wx.EVT_CHOICE, lambda _e: self._on_model_chosen())
        sizer.Add(model_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        sizer.Add(self._model, 0, wx.EXPAND | wx.ALL, _PAD)

        self._action = wx.Button(panel, label=words.ACTION_LABELS[words.USE])
        self._action.SetHelpText(
            "Does what the selected row needs: Use This makes a signed-in row the one "
            "in use, Sign In opens its sign-in step, and Sign Out signs out of the row "
            "in use."
        )
        self._action.Bind(wx.EVT_BUTTON, lambda _e: self.do_action())
        _close_row(self, sizer, self._action)

        self.Bind(wx.EVT_ACTIVATE, self._on_activate)
        self.SetInitialSize(dip_size(self, 560, 460))
        self.Centre()
        self.refresh(select=select)
        focus_on(self, self._list)

    # -- reading the rows ------------------------------------------------- #

    def _selected_row(self) -> Any:
        index = self._list.GetSelection()
        return self._rows[index] if 0 <= index < len(self._rows) else None

    def refresh(self, *, select: str = "") -> None:
        """Re-read every row. Only changed text is written, so the reader is not
        made to say a row that did not change."""
        current = self._selected_row()
        keep = select or (current.connection if current is not None else "")
        self._rows = list(self._service.connection_rows())
        texts = [row.text for row in self._rows]
        if self._list.GetCount() != len(texts):
            self._list.Set(texts)
        else:
            for index, text in enumerate(texts):
                if self._list.GetString(index) != text:
                    self._list.SetString(index, text)
        wanted = keep or next((r.connection for r in self._rows if r.state == IN_USE), FREE)
        index = next((i for i, r in enumerate(self._rows) if r.connection == wanted), 0)
        if self._rows:
            self._list.SetSelection(index)
        self._follow_row()

    def select(self, connection: str) -> None:
        """Put the selection on *connection*'s row (a command opened the window on it)."""
        self.refresh(select=connection)

    def _on_activate(self, event: Any) -> None:
        # A Connect step elsewhere may have finished: the rows read the truth
        # when the window comes back. Silent; the reader says the focused row.
        if event.GetActive() and self:
            self.refresh()
        event.Skip()

    def _follow_row(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        if self._hooks.safe_mode:
            self._about.SetValue(words.SAFE_MODE_ABOUT)
        else:
            record = self._service.capability_record(row.connection)
            provider = getattr(self._service, "own_key_provider", "openai") or "openai"
            self._about.SetValue(words.about_line(record, own_key_provider=provider))
        action = words.row_action(row, free_connected=bool(self._service.signed_in))
        self._action.SetLabel(words.ACTION_LABELS[action])
        self._fill_models(row)

    # -- the model choice -------------------------------------------------- #

    def _disabled_model(self, text: str) -> None:
        self._shown_models = []
        self._model.Set([text])
        self._model.SetSelection(0)
        self._model.Disable()

    def _fill_models(self, row: Any) -> None:
        connection = row.connection
        if self._hooks.safe_mode or row.state == NOT_AVAILABLE_YET:
            self._disabled_model(words.NOT_AVAILABLE_MODELS)
            return
        if connection == FREE:
            self._disabled_model(words.FREE_MODEL)
            return
        if row.state not in (IN_USE, SIGNED_IN) or connection not in (CHATGPT, OWN_KEY):
            self._disabled_model(words.SIGN_IN_FOR_MODELS)
            return
        listed = self._models.get(connection)
        if listed is None:
            self._disabled_model(_READING_MODELS)
            self._discover(connection)
            return
        models, error = listed
        if error or not models:
            self._disabled_model(words.MODELS_FAILED)
            return
        self._shown_models = models
        self._model.Set(words.model_items([label for _id, label in models]))
        chosen = self._service.connection_model(connection)
        ids = [model_id for model_id, _label in models]
        self._model.SetSelection(ids.index(chosen) if chosen in ids else 0)
        self._model.Enable()

    def _discover(self, connection: str) -> None:
        """Ask the connection for its models, off the UI thread, once per window."""
        from quill.ui.update_download import thread_submit

        if connection in self._asked:
            return  # asked already; the answer is on its way
        self._asked.add(connection)
        lister = self._hooks.list_models or self._list_models

        def done(_name: str, result: Any) -> None:
            wx.CallAfter(self._models_arrived, connection, result)

        def failed(_name: str, error: BaseException) -> None:
            wx.CallAfter(self._models_arrived, connection, ([], str(error) or "failed"))

        thread_submit(
            "quill-ai-choose-models",
            lambda **_k: lister(connection),
            on_success=done,
            on_failure=failed,
        )

    def _models_arrived(self, connection: str, result: Any) -> None:
        if not self:
            return
        models, error = result
        self._models[connection] = (list(models), str(error or ""))
        row = self._selected_row()
        if row is not None and row.connection == connection:
            self._fill_models(row)  # silent: the Model choice does not have focus

    def _list_models(self, connection: str) -> tuple[list[tuple[str, str]], str]:
        if connection == CHATGPT:
            from quill.core.ai.chatgpt_client import list_models

            listed = list_models(self._service.chatgpt.access_token())
            return [(str(m.slug), str(getattr(m, "label", m.slug))) for m in listed], ""
        from quill.core.ai.own_key_models import choice_label
        from quill.core.ai.own_key_models import list_models as own_models
        from quill.core.assistant_ai import load_provider_api_key

        provider = self._service.own_key_provider or "openai"
        names, error = own_models(load_provider_api_key(provider), provider)
        return [(name, choice_label(name, provider)) for name in names], error

    def _on_model_chosen(self) -> None:
        row = self._selected_row()
        index = self._model.GetSelection()
        if row is None or not 0 <= index < len(self._shown_models):
            return
        model_id = self._shown_models[index][0]
        if row.connection == CHATGPT:
            self._service.chatgpt.set_model(model_id)
        elif row.connection == OWN_KEY:
            self._service._settings().ai_own_key_model = model_id
            self._service._save_settings()
        self._hooks.changed()  # the reader says the new choice; nothing to add

    # -- the action button -------------------------------------------------- #

    def _on_list_key(self, event: Any) -> None:
        if event.GetKeyCode() in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            self._ask_sign_out()
            return
        event.Skip()

    def _signed_in(self, row: Any) -> bool:
        if row.connection == FREE:
            return bool(self._service.signed_in)
        return row.state in (IN_USE, SIGNED_IN)

    def _ask_sign_out(self) -> None:
        row = self._selected_row()
        if row is None or self._hooks.safe_mode or not self._signed_in(row):
            return
        name = CONNECTION_NAMES.get(row.connection, row.connection)
        if ask_yes_no(self, f"Sign out of {name}?", default_yes=False):
            self.sign_out(row)

    def do_action(self) -> None:
        """Enter on the list, or the button: use, sign in or sign out."""
        row = self._selected_row()
        if row is None:
            return
        say = self._hooks.announce
        if self._hooks.safe_mode:
            say(words.SAFE_MODE_ABOUT)
            return
        if row.state == NOT_AVAILABLE_YET:
            say(words.not_available_sentence(row.connection))
            return
        action = words.row_action(row, free_connected=bool(self._service.signed_in))
        if action == words.USE:
            if self._service.choose(row.connection):
                self._after_change(row.connection)
                say(words.now_using(row.connection))
            return
        if action == words.SIGN_OUT:
            self.sign_out(row)
            return
        self.start_sign_in(row.connection)

    def start_sign_in(self, connection: str) -> None:
        """The row's sign-in step. A command that opened the window on its row calls this."""
        say = self._hooks.announce
        if self._hooks.safe_mode:
            say(words.SAFE_MODE_ABOUT)
            return
        if connection == FREE:
            # Choosing the free AI needs no sign-in; connecting this computer is
            # its one human step, opened only because somebody asked (decision 23).
            self._service.choose(FREE)
            self._after_change(FREE)
            self._hooks.connect_free()
            return
        if connection not in (CHATGPT, OWN_KEY):
            say(words.not_available_sentence(connection))
            return
        before = self._service.connection_in_use
        self._service.note_readiness()
        if connection == OWN_KEY:
            outcome = self._hooks.own_key()
            if not outcome:
                return  # Cancel changes nothing, and says nothing
        elif not _chatgpt_sign_in(self, self._service.chatgpt, connection, self._hooks.app_name):
            return
        else:
            outcome = words.signed_in_sentence(connection)
        self._service.connection_changed(connection)
        self._after_change(connection)
        now = self._service.connection_in_use
        say(words.signed_in_sentence(connection) if now == connection != before else outcome)

    def sign_out(self, row: Any) -> None:
        """Sign out of *row*. Out of the row in use, nothing is in use (decision 15)."""
        connection = row.connection
        was_in_use = row.state == IN_USE
        if connection == FREE:
            self._service.sign_out()
        elif connection == OWN_KEY:
            from quill.core.assistant_ai import clear_provider_api_key

            clear_provider_api_key(self._service.own_key_provider or "openai")
        elif connection in (CHATGPT, CODEX):
            self._sign_out_of_plan(connection, was_in_use)
            return
        self._finish_sign_out(connection, was_in_use, "")

    def _sign_out_of_plan(self, connection: str, was_in_use: bool) -> None:
        """OpenAI is asked to revoke the sign-in, off the UI thread."""
        from quill.ui.update_download import thread_submit

        account = self._service.chatgpt
        agent = self._hooks.app_name

        def done(_name: str, confirmed: Any) -> None:
            note = (
                ""
                if confirmed
                else f" OpenAI could not be told; you may also want to remove {agent} "
                "under Apps in ChatGPT's settings."
            )
            wx.CallAfter(self._finish_sign_out, connection, was_in_use, note)

        thread_submit(
            "quill-ai-choose-sign-out",
            lambda **_k: account.sign_out(),
            on_success=done,
            on_failure=lambda n, _e: done(n, False),
        )

    def _finish_sign_out(self, connection: str, was_in_use: bool, note: str) -> None:
        self._service.connection_changed(connection)
        if self:
            self._after_change(connection)
        else:
            self._hooks.changed()
        self._hooks.announce(words.signed_out_sentence(connection, was_in_use=was_in_use) + note)

    def _after_change(self, connection: str) -> None:
        self._models.pop(connection, None)
        self._asked.discard(connection)
        self._hooks.changed()
        self.refresh(select=connection)
