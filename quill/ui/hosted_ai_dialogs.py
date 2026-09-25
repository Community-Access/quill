"""The four windows the family's hosted AI is reached through.

Shared by **both** editors, which is why these modules live in ``quill/ui``
rather than beside QuillLite's. The hosted service shipped in QuillLite first,
and a feature the small product has and the big one does not is backwards and
invisible -- nobody opens QUILL and notices the absence of a thing they have
only ever seen elsewhere. So the windows moved here and QUILL reaches them on
the same day, which is the standing family rule rather than a favour.

All four are **modeless** ``wx.Frame``s, and that is the decision the rest of
this module follows from. A modal dialog blocks the editor, and an editor that
stops accepting keystrokes because a server is thinking has lost the thing it is
for. So somebody can ask for a summary and keep typing, save, switch documents,
or close the pad while the answer is on its way.

Being a frame rather than a dialog costs two things that have to be paid back by
hand, and both have bitten this family before:

* **A frame does not answer ``ID_CANCEL``.** A Close button wired to nothing
  still *works* in a ``wx.Dialog`` and silently does nothing in a ``wx.Frame`` --
  which is exactly how four of Quill Radio's converted windows shipped with a
  button that looked like the way out and was not. Every Close here goes through
  :func:`~quill.ui.dialog_contract.bind_close_button`.
* **Nothing may be shown modally from a close handler.** ``ShowModal`` inside
  ``EVT_CLOSE`` on wxMSW is what made Alt+F4 do nothing in Radio while playing.
  So closing the pad discards whatever was in it. No "are you sure", ever.

What each window announces, and what it deliberately does not, is GATE-13
applied one surface at a time: the screen reader already says a window's title,
the control that has focus and the text of a field that just received it, so
none of that is repeated here. What is announced is what the reader cannot
know -- an outcome, a state change on something that does not have focus, and a
result that arrived while the person was somewhere else entirely.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.ui.accessible_names import set_accessible_name
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button

__all__ = [
    "AiSignInFrame",
    "AiUsageFrame",
    "ask_ai_privacy_agreement",
    "focus_on",
    "take_focus",
]

_PAD = 8


def focus_on(frame: wx.Frame, control: wx.Window) -> None:
    """Remember which control should have focus once *frame* is on screen.

    Setting it now would not stick. On wxMSW focus given to a control in a
    window that has not been shown yet is discarded when the window finally is,
    so every ``SetFocus()`` in a constructor here was silently doing nothing --
    which is exactly what "the Sign In window did not take focus" looked like
    from the outside.

    The other windows in this family get away with the same mistake because
    they are ``wx.Dialog``s, and showing a dialog activates it. These are
    ``wx.Frame``s parented to an MDI child, and a child frame is not activated
    by ``Show()``.
    """
    frame._focus_target = control  # noqa: SLF001 - one family, one attribute


def take_focus(frame: wx.Frame) -> None:
    """Bring *frame* forward and put focus where :func:`focus_on` asked.

    Called through ``wx.CallAfter`` once the window is shown, so it runs after
    wx has finished realising it. Guarded throughout: the user can close a
    window between ``Show()`` and the next idle cycle, and a focus call into a
    destroyed control is a crash rather than a missed focus.
    """
    try:
        if not frame:
            return
        frame.Raise()
        frame.SetFocus()
        target = getattr(frame, "_focus_target", None) or _first_focusable(frame)
        if target:
            target.SetFocus()
    except RuntimeError:  # the wx object went away while we waited
        pass


def _first_focusable(frame: wx.Frame) -> wx.Window | None:
    """The first control Tab would reach, for a window that named none.

    Focus left on the frame itself is focus on nothing: on wxMSW the keys go to
    a window with no controls of its own, so neither the arrows nor Tab do
    anything -- which is how AI Usage opened (reported 2026-09-25).
    """
    children = getattr(frame, "GetChildren", None)
    pending = list(children()) if callable(children) else []
    while pending:
        window = pending.pop(0)
        if isinstance(window, wx.TopLevelWindow):
            continue
        # Into a container before asking it: a panel answers yes to
        # AcceptsFocus, and focus on the panel is focus on nothing.
        inner = list(window.GetChildren())
        if inner:
            pending[0:0] = inner
            continue
        if window.AcceptsFocus() and window.IsShown() and window.IsEnabled():
            return window
    return None


def _read_only(parent: wx.Window, sizer: wx.Sizer, label: str, value: str, help_text: str):
    """A labelled, read-only, multi-line field.

    Read-only but **not** a static label, and the difference matters: a text
    control can be arrowed through character by character, selected and copied.
    A ``StaticText`` can be read once, as a lump, and nothing else -- which is
    no way to check an eight-character code you are about to type into a phone.
    """
    static = wx.StaticText(parent, label=label)
    field = wx.TextCtrl(parent, value=value, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
    set_accessible_name(field, label.replace("&", "").rstrip(": "))
    field.SetHelpText(help_text)
    sizer.Add(static, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
    sizer.Add(field, 1, wx.EXPAND | wx.ALL, _PAD)
    return field


def _close_row(frame: wx.Frame, sizer: wx.Sizer, *extra: wx.Button) -> wx.Button:
    """The button row, with Close last and carrying no access key.

    Close, OK and Cancel never take a mnemonic anywhere in this family: Escape
    already reaches them, and every letter they give up resolves a collision
    somewhere else in a window that has run out (GATE-14).
    """
    row = wx.BoxSizer(wx.HORIZONTAL)
    # A stretch spacer pushes the row right, rather than wx.ALIGN_RIGHT doing it.
    # The two look identical until the window is narrow, at which point
    # ALIGN_RIGHT inside an EXPAND-less sizer lets wxMSW *clip* the row instead
    # of moving it -- and a clipped button is one nothing can reach. Banned in
    # quill/ui for exactly that reason (A11Y-4 dialog contract); these two lines
    # were invisible to the gate while this module lived under quill/apps.
    row.AddStretchSpacer(1)
    for button in extra:
        row.Add(button, 0, wx.RIGHT, _PAD)
    # Parented to whatever window owns *sizer* (the panel), never the frame:
    # wx asserts when a sizer manages a window that is not its container's
    # child, and that assertion aborted both windows' constructors -- so
    # Connect or Sign Out and Usage opened nothing and left focus in the editor.
    owner = sizer.GetContainingWindow() or frame
    close = wx.Button(owner, wx.ID_CLOSE, "Close")
    close.SetHelpText("Closes this window. Nothing is sent, and nothing in your document changes.")
    row.Add(close, 0)
    sizer.Add(row, 0, wx.EXPAND | wx.ALL, _PAD)
    bind_close_button(frame, close, modeless=True)
    _bind_escape(frame)
    return close


def _bind_escape(frame: wx.Frame) -> None:
    """Escape closes the window, as it would a dialog.

    A ``wx.Dialog`` turns Escape into ``ID_CANCEL`` for free; a ``wx.Frame``
    does nothing with it, so every one of these windows ignored the key a
    listener reaches for first (reported 2026-09-25). Bound once per frame:
    :func:`_close_row` runs again each time the sign-in window changes state.
    """
    if getattr(frame, "_escape_bound", False):
        return
    frame._escape_bound = True  # noqa: SLF001 - one family, one attribute

    def _on_char_hook(event: wx.KeyEvent) -> None:
        if event.GetKeyCode() == wx.WXK_ESCAPE and not event.HasAnyModifiers():
            frame.Close()
            return
        event.Skip()

    frame.Bind(wx.EVT_CHAR_HOOK, _on_char_hook)


# --------------------------------------------------------------------------- #
# Sign in
# --------------------------------------------------------------------------- #


class AiSignInFrame(wx.Frame):
    """Connect this computer. No account, no password, no email address.

    **The code is on the first screen.** This window used to open on an
    explanation and a Show My Code button, so connecting took a keystroke
    whose only job was to reveal the thing the window is for. Nobody reaches
    this window without having accepted the agreement, which already says what
    is sent and where -- so it asks for the code as it opens, and offers Open
    the Connect Page beside it with the code already filled in.

    Three states in one window rather than three windows: waiting for the code,
    the code, and the confirmation. Replacing the content in place means
    focus never jumps to a window somebody did not open, and the status line
    changing is a label change on unfocused text -- exactly the case a screen
    reader does *not* announce, and therefore exactly the case QuillLite should.
    """

    def __init__(self, parent: wx.Window, service: Any, announce: Callable[[str], None]) -> None:
        super().__init__(parent, title="QUILL AI Sign-In")
        self._service = service
        self._announce = announce

        panel = wx.Panel(self)
        self._sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(self._sizer)
        self._panel = panel

        self.SetInitialSize((560, 440))
        self.Centre()
        if service.signed_in:
            self._show_connected(service.support_id, already=True)
        else:
            self._on_show_code(None)

    def _clear(self) -> None:
        self._sizer.Clear(delete_windows=True)

    # -- step 1: the code -------------------------------------------------- #

    def _on_show_code(self, _event: wx.CommandEvent) -> None:
        self._clear()
        self._status = wx.StaticText(self._panel, label="Asking QUILL for a code...")
        self._sizer.Add(self._status, 0, wx.ALL, _PAD)
        close = _close_row(self, self._sizer)
        self._panel.Layout()
        focus_on(self, close)
        self._service.start_sign_in(
            on_code=self._show_code, on_done=self._show_connected, on_error=self._show_error
        )

    def _show_code(self, code: Any) -> None:
        if not self:
            return
        self._clear()
        panel = self._panel
        field = _read_only(
            panel,
            self._sizer,
            "Your code",
            code.user_code,
            "The code to type into the web page. Use the arrow keys to hear it "
            "one character at a time.",
        )
        where = wx.StaticText(
            panel,
            label="Choose Open the Connect Page and press Confirm, or type the code at "
            f"{code.verification_uri} on any device. There is no account and no "
            "password. QUILL is waiting; this window will say when you are connected.",
        )
        self._sizer.Add(where, 0, wx.ALL, _PAD)

        page = getattr(code, "verification_uri_complete", "") or code.verification_uri
        browse = wx.Button(panel, label="&Open the Connect Page")
        browse.SetHelpText(
            "Opens the connect page in your web browser with this code already "
            "filled in. Press Confirm there, then come back here."
        )
        browse.Bind(wx.EVT_BUTTON, lambda _e: self._open_page(page))
        say = wx.Button(panel, label="Say the Code &Again")
        say.SetHelpText("Reads the code out one character at a time.")
        say.Bind(wx.EVT_BUTTON, lambda _e: self._announce(code.spoken))
        copy = wx.Button(panel, label="&Copy the Code")
        copy.SetHelpText("Puts the code on the clipboard.")
        copy.Bind(wx.EVT_BUTTON, lambda _e: self._copy(code.user_code))
        _close_row(self, self._sizer, browse, say, copy)
        panel.Layout()
        focus_on(self, field)
        take_focus(self)
        # The content changed under a window that is already open, which the
        # reader does not announce. Say the code rather than "ready": the code
        # is the thing they need, and they are about to type it elsewhere.
        self._announce(f"Your code is {code.spoken}. Go to {code.verification_uri}.")

    def _open_page(self, url: str) -> None:
        # The browser taking focus is what the reader announces; a sentence here
        # would talk over it. Only a failure is ours to say.
        if not wx.LaunchDefaultBrowser(url):
            self._announce(f"Could not open a browser. Go to {url} and type the code.")

    def _copy(self, text: str) -> None:
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(text))
            finally:
                wx.TheClipboard.Close()
            self._announce("Code copied.")

    # -- step 2: connected, or not --------------------------------------- #

    def _show_connected(self, support_id: str, already: bool = False) -> None:
        if not self:
            return
        self._clear()
        panel = self._panel
        lead = "This computer is already connected to QUILL's free AI." if already else "Connected."
        _read_only(
            panel,
            self._sizer,
            "Connected",
            f"{lead}\n\nYour support ID is {support_id}. QUILL support will ask "
            "for this if you ever need help.\n\n"
            "Choose Usage in the AI menu to see how much of this month's allowance "
            "is left, or to sign this computer out again.",
            "Confirms this computer is connected, and gives the support ID to "
            "quote if you ever contact support.",
        )
        close = _close_row(self, self._sizer)
        panel.Layout()
        focus_on(self, close)
        take_focus(self)
        if not already:
            self._announce(f"Connected. Your support ID is {support_id}.")

    def _show_error(self, message: str) -> None:
        if not self:
            return
        self._clear()
        field = _read_only(
            self._panel,
            self._sizer,
            "Could not connect",
            message,
            "What went wrong, and what to do about it.",
        )
        retry = wx.Button(self._panel, label="&Get a New Code")
        retry.SetHelpText("Asks QUILL for a fresh code and tries again.")
        retry.Bind(wx.EVT_BUTTON, self._on_show_code)
        _close_row(self, self._sizer, retry)
        self._panel.Layout()
        # Focus on the message rather than announcing it: the control that was
        # focused has just been destroyed, and the reader says a field's text
        # when it takes focus -- so an announcement as well said it twice.
        focus_on(self, field)
        take_focus(self)


# --------------------------------------------------------------------------- #
# Usage
# --------------------------------------------------------------------------- #


class AiUsageFrame(wx.Frame):
    """How much is left, and the way to sign this computer out."""

    def __init__(self, parent: wx.Window, service: Any, announce: Callable[[str], None]) -> None:
        super().__init__(parent, title="AI Usage")
        self._service = service
        self._announce = announce
        self._confirming = False

        panel = wx.Panel(self)
        self._sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(self._sizer)
        self._panel = panel

        self._body = _read_only(
            panel,
            self._sizer,
            "Your allowance",
            "Asking QUILL how much is left...",
            "How many free AI requests you have left this month and today, when "
            "the count starts again, and this computer's support ID.",
        )
        self._buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._sign_out = wx.Button(panel, label="Sign &Out This Computer")
        self._sign_out.SetHelpText(
            "Disconnects this computer from QUILL's free AI. You can connect it again at any time."
        )
        self._sign_out.Bind(wx.EVT_BUTTON, self._on_sign_out)
        copy = wx.Button(panel, label="Copy Support &ID")
        copy.SetHelpText("Puts this computer's support ID on the clipboard.")
        copy.Bind(wx.EVT_BUTTON, self._on_copy)
        _close_row(self, self._sizer, self._sign_out, copy)
        focus_on(self, self._body)

        self.SetInitialSize((520, 380))
        self.Centre()
        service.fetch_quota(on_done=self._show, on_error=self._failed)

    def _show(self, quota: Any) -> None:
        if not self:
            return
        reset = (quota.reset_at or "")[:10] or "the 1st"
        self._body.SetValue(
            f"This month\n"
            f"{quota.monthly_left} of {quota.monthly_cap} requests left. "
            f"Starts again {reset}.\n\n"
            # No cap here: today's is the smaller of the two the server sent,
            # so "of 20" beside a month with 15 left would contradict itself.
            f"Today\n{quota.daily_left} left.\n\n"
            f"This computer\nSupport ID {self._service.support_id}."
        )
        # A label change on an unfocused control, which the reader does not say.
        self._announce(f"{quota.monthly_left} of {quota.monthly_cap} requests left this month.")

    def _failed(self, message: str) -> None:
        if not self:
            return
        self._body.SetValue(message)
        self._announce(message)

    def _on_copy(self, _event: wx.CommandEvent) -> None:
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(self._service.support_id))
            finally:
                wx.TheClipboard.Close()
            self._announce("Support ID copied.")

    def _on_sign_out(self, _event: wx.CommandEvent) -> None:
        """Confirm in place, with a second press -- never a modal.

        A message box raised from this window would be a modal over a modeless
        frame, and the family already knows where that road goes on wxMSW. Two
        presses of one button is the whole confirmation, and the label says
        which press you are on.
        """
        if not self._confirming:
            self._confirming = True
            self._sign_out.SetLabel("Yes, Sign &Out")
            self._announce("Press again to sign this computer out.")
            return
        self._service.sign_out()
        self._body.SetValue(
            "This computer is signed out of QUILL's free AI.\n\n"
            "Choose Connect or Sign Out in the AI menu to connect it again whenever you like."
        )
        self._sign_out.Disable()
        self._announce("Signed out.")


# --------------------------------------------------------------------------- #
# The agreement
# --------------------------------------------------------------------------- #


def ask_ai_privacy_agreement(parent: wx.Window) -> bool:
    """Show the agreement and return whether it was accepted.

    **Announces nothing, either way.** The agreement is reached through three
    doors and on the way to two commands, and what happens next differs at every
    one of them -- so the caller says it, or says nothing. Speaking here told
    somebody who had just chosen Sign In to "choose Connect or Sign Out",
    said the same sentence twice when the Privacy door accepted it, and spoke on
    a plain Escape that had changed nothing at all.

    **Modal, unlike every other window here**, and for the opposite reason to
    the rest: those are modeless because work is happening and the editor must
    stay live. Nothing is happening yet here. This is a question that has to be
    answered before anything can, and a consent prompt somebody can leave open
    behind the editor and forget is a consent prompt that gets clicked through
    later without being read.

    Declining leaves the feature **present and unusable** rather than switching
    the area back off. A switch that flips itself back is a switch somebody will
    fight, and they would be right to: they did turn it on, and what they
    declined was the sending, not the menu.
    """
    from quill.core.ai.gateway_privacy import AGREEMENT_TITLE, agreement_text

    dialog = wx.Dialog(
        parent, title=AGREEMENT_TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
    )
    sizer = wx.BoxSizer(wx.VERTICAL)

    body = _read_only(
        dialog,
        sizer,
        "What you are agreeing to",
        agreement_text(),
        "The whole agreement. Read it with the arrow keys; nothing is sent unless you accept.",
    )

    # No mnemonics on either: Enter and Escape already reach them, and GATE-14
    # would rather those letters went to something that needs them. The labels
    # say which is which, and the reader announces the default.
    buttons = wx.BoxSizer(wx.HORIZONTAL)
    agree = wx.Button(dialog, wx.ID_OK, "I Agree")
    agree.SetHelpText(
        "Turns on AI help. You can withdraw this later in the AI menu, or in Preferences."
    )
    decline = wx.Button(dialog, wx.ID_CANCEL, "No Thanks")
    decline.SetHelpText("Leaves AI help switched off. Everything else in QuillLite is unchanged.")
    # A stretch spacer, not wx.ALIGN_RIGHT -- see _close_row for why.
    buttons.AddStretchSpacer(1)
    buttons.Add(agree, 0, wx.RIGHT, _PAD)
    buttons.Add(decline, 0)
    sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, _PAD)

    dialog.SetSizer(sizer)
    dialog.SetInitialSize((620, 520))
    dialog.Centre()
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
    # Focus the text, not the button: the reader then reads the agreement rather
    # than announcing "I Agree" to somebody who has not heard it yet. Deferred,
    # because ShowModal is what puts the dialog on screen -- setting focus before
    # it is the same mistake focus_on() exists to prevent.
    wx.CallAfter(body.SetFocus)

    try:
        return dialog.ShowModal() == wx.ID_OK
    finally:
        dialog.Destroy()
