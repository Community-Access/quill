"""Sign In to Scribe for Documents (PRD 7.2), the small waiting dialog.

QUILL binds a loopback port, opens Scribe's own sign-in page in the person's
browser (SCR-POL-2: never embedded, nothing typed there is seen), and waits
here with Copy Sign-in Link and Cancel. On success the text changes to
"Signed in to Scribe for Documents as <name>. <n> pages left." and focus
moves to Continue, then that one sentence is announced (a SetValue on a
focused edit is not re-read, so the announcement is what carries it; the
accessibility review of 2026-11-20). The person is usually in the browser
then, so the dialog asks for attention rather than stealing focus.

A timeout says "Sign-in timed out. Try again?" with Try Again focused.
"""

from __future__ import annotations

import webbrowser
from typing import Any

import wx

from quill.core.scribe import PRODUCT_NAME
from quill.core.scribe.errors import ScribeError, ScribeSignInLocalError
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button

WAITING = "Your browser is open at Scribe for Documents. Sign in there, then come back to {app}."
TIMED_OUT = "Sign-in timed out. Try again?"
NO_BROWSER = (
    "{app} could not open your browser. Use Copy Sign-in Link, paste the link into any "
    "browser and sign in there; {app} is waiting for it."
)


class ScribeSignInDialog(wx.Dialog):
    def __init__(self, parent: Any, controller: Any, *, app_name: str = "QUILL") -> None:
        super().__init__(parent, title="Sign In to Scribe for Documents")
        self.SetName("scribe_signin_dialog")  # F1 finds its topic by this name (topics.json)
        self._controller = controller
        self._app = app_name
        self._attempt: Any = None
        self._alive = True
        self._url = ""

        sizer = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self, label="&Sign-in:")
        sizer.Add(label, 0, wx.ALL, 6)
        self.text = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_NO_VSCROLL, size=wx.Size(-1, -1)
        )
        self.text.SetMinSize(self.FromDIP(wx.Size(420, 80)))
        self.text.SetHelpText(
            "What is happening with the sign-in. Scribe's own page is in your browser; "
            f"{app_name} never sees what you type there."
        )
        sizer.Add(self.text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.copy_button = wx.Button(self, label="Copy Sign-in &Link")
        self.copy_button.SetHelpText(
            "Copies Scribe's sign-in address, for when the browser did not open or you use "
            "another browser. Paste it there and sign in."
        )
        self.retry_button = wx.Button(self, label="&Try Again")
        self.retry_button.SetHelpText("Starts the sign-in again in your browser.")
        self.continue_button = wx.Button(self, wx.ID_OK, label="Continue")
        self.continue_button.SetHelpText("Closes this and carries on with what you were doing.")
        self.cancel_button = wx.Button(self, wx.ID_CANCEL, label="Cancel")
        self.cancel_button.SetHelpText(f"Stops waiting. You are not signed in to {PRODUCT_NAME}.")
        for button in (
            self.copy_button,
            self.retry_button,
            self.continue_button,
            self.cancel_button,
        ):
            buttons.Add(button, 0, wx.ALL, 6)
        sizer.Add(buttons, 0, wx.EXPAND)
        self.SetSizerAndFit(sizer)

        self.copy_button.Bind(wx.EVT_BUTTON, self._on_copy)
        self.retry_button.Bind(wx.EVT_BUTTON, lambda _e: self._start())
        bind_close_button(self, self.cancel_button, modeless=False)
        self.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)
        self.Bind(wx.EVT_ACTIVATE, self._on_activate)
        self._signed_in_sentence = ""
        self._heard_in_background = False
        # Escape is wx.ID_ANY: Cancel while waiting, Continue once signed in.
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL, escape_id=wx.ID_ANY)
        self._start()

    # ---------------------------------------------------------------- flow

    def _set_text(self, text: str) -> None:
        self.text.SetValue(text)
        self.text.SetInsertionPoint(0)
        self.text.ShowPosition(0)

    def _start(self) -> None:
        self.continue_button.Hide()
        self.retry_button.Hide()
        self.copy_button.Show()
        self.cancel_button.Show()
        try:
            self._attempt = self._controller.session.begin_sign_in(app_name=self._app)
        except ScribeSignInLocalError as error:
            self._set_text(error.message)
            self._show_retry()
            return
        except ScribeError as error:
            self._set_text(error.message)
            self.text.SetFocus()
            wx.CallLater(200, self._controller.host.scribe_announce, error.message)
            return
        self._url = self._attempt.url
        opened = False
        try:
            opened = bool(webbrowser.open(self._url))
        except Exception:  # noqa: BLE001 - no browser is a case we explain
            opened = False
        self._set_text((WAITING if opened else NO_BROWSER).format(app=self._app))
        self.Layout()
        self.text.SetFocus()
        attempt = self._attempt
        self._controller._background(
            lambda: self._wait(attempt),
            lambda sentence: self._finished(attempt, sentence, ""),
            lambda error: self._finished(
                attempt, None, error.message if isinstance(error, ScribeError) else str(error)
            ),
        )

    def _wait(self, attempt: Any) -> str | None:
        """On the task pool: wait for the redirect, then read who signed in."""
        if attempt.wait() is None:
            return None
        try:
            account = self._controller.client().account()
            return f"Signed in to {PRODUCT_NAME} as {account.name}. {account.pages_phrase()}"
        except Exception:  # noqa: BLE001 - signed in even if the account call failed
            return f"Signed in to {PRODUCT_NAME}."

    def _finished(self, attempt: Any, sentence: str | None, error: str) -> None:
        if not self._alive or attempt is not self._attempt:
            return
        if sentence:
            self._set_text(sentence)
            self.continue_button.Show()
            self.Layout()
            self.continue_button.SetDefault()
            self.continue_button.SetFocus()
            self.copy_button.Hide()
            self.cancel_button.Hide()
            self.Layout()
            self._signed_in_sentence = sentence
            if not self.IsActive():
                self._heard_in_background = True
                self.RequestUserAttention()
            else:
                wx.CallLater(200, self._controller.host.scribe_announce, sentence)
            return
        text = error or TIMED_OUT
        self._set_text(text)
        self._show_retry()
        wx.CallLater(200, self._controller.host.scribe_announce, text)

    def _show_retry(self) -> None:
        self.retry_button.Show()
        self.Layout()
        self.retry_button.SetFocus()
        self.copy_button.Hide()
        self.Layout()

    def _on_activate(self, event: wx.ActivateEvent) -> None:
        event.Skip()
        if event.GetActive() and self._heard_in_background and self._signed_in_sentence:
            self._heard_in_background = False
            wx.CallLater(250, self._controller.host.scribe_announce, self._signed_in_sentence)

    def _on_copy(self, _event: wx.CommandEvent) -> None:
        if not self._url:
            return
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(self._url))
            finally:
                wx.TheClipboard.Close()
            self._controller.host.scribe_announce("Sign-in link copied.")

    def _on_destroy(self, event: wx.WindowDestroyEvent) -> None:
        if event.GetEventObject() is self:
            self._alive = False
            if self._attempt is not None:
                self._attempt.close()
        event.Skip()


__all__ = ["ScribeSignInDialog"]
