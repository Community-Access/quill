"""Help > Get Help from Support...: one door, in every app.

What a person wants when something is wrong is *an answer*, and until now no
app in the family could give them one. Report a Bug filed a GitHub issue --
public, permanent, and unreadable-by-reply to anybody without an account -- and
six of the nine apps had no reporting item at all, only an address printed in
the About box for you to copy by hand.

This is the replacement, and it is deliberately plain: the same few fields
everywhere, one Send button, and then **your own mail program opens with the
whole message already written**. Nothing is sent until you press Send there,
which is said out loud, because a form that claims to have sent something it
has not is worse than a form that asks for one more keypress.

One transport: **the reader's own mail program**, addressed to
``support@community-access.org``. No credential, no server, no account.
Until 2026-09-26 a feedback-hub dialog was tried first, for a submission
server that never shipped; with every message now going to the help desk by
email it was a second door to the same room, and it is gone.

What there is *no* fallback to is GitHub. ``Community-Access/quill`` is
public and a support message is somebody's own words about their own machine;
``docs/design/2026-08-26-feedback-redesign-for-freescout.md`` is the reasoning
and this module is where it is enforced.
"""

from __future__ import annotations

from typing import Any

from quill.core.support_message import (
    SUPPORT_EMAIL,
    SUPPORT_MENU_TITLE,
    SupportMessage,
    build_body,
    build_mailto_url,
    build_subject,
    validate,
)
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button

TITLE = SUPPORT_MENU_TITLE

_SCREEN_READERS = (
    "Not using a screen reader",
    "JAWS",
    "NVDA",
    "Narrator",
    "VoiceOver",
    "Other",
)

_CATEGORIES = (
    "Something is broken",
    "A question",
    "An accessibility problem",
    "An idea or request",
)


def open_support_message(
    host: Any,
    *,
    source_app: str,
    app_version: str = "",
    prefill_summary: str = "",
    prefill_body: str = "",
    extra: dict[str, str] | None = None,
) -> None:
    """Open the support surface for *host*. Never raises into a menu handler.

    *extra* is facts the app knows and the person should not have to look up,
    written into the message under "About this report" -- the QUILL AI support
    ID, when this computer is connected, is the one support asks for first.
    """
    product = f"{source_app} {app_version}".strip()
    if extra is None:
        # An editor with QUILL's free AI knows its own support ID; asking the
        # host here is what puts it in every app's message without every call
        # site having to pass it.
        facts_of = getattr(host, "ai_support_facts", None)
        try:
            extra = facts_of() if callable(facts_of) else {}
        except Exception:  # noqa: BLE001 - a missing fact must not block writing to support
            extra = {}
    if not isinstance(extra, dict):
        extra = {}
    facts = {key: value for key, value in (extra or {}).items() if value}
    import wx

    _SupportDialog(
        host,
        wx,
        product=product,
        prefill_summary=prefill_summary,
        prefill_body=prefill_body,
        extra=facts,
    ).show()


class _SupportDialog:
    """The mail-client path: collect the message, hand it to the mail program."""

    def __init__(
        self,
        host: Any,
        wx: Any,
        *,
        product: str,
        prefill_summary: str = "",
        prefill_body: str = "",
        extra: dict[str, str] | None = None,
    ) -> None:
        self._host = host
        self._extra = dict(extra or {})
        self._wx = wx
        self._product = product
        self._prefill_summary = prefill_summary
        self._prefill_body = prefill_body

    def show(self) -> None:
        wx = self._wx
        self.dialog = wx.Dialog(_parent(self._host), title=TITLE, style=wx.DEFAULT_DIALOG_STYLE)
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                self.dialog,
                label=(
                    f"Write to {SUPPORT_EMAIL}. Your own mail program opens with "
                    "this message ready; nothing is sent until you send it there."
                ),
            ),
            0,
            wx.ALL,
            8,
        )

        grid = wx.FlexGridSizer(0, 2, 6, 8)
        grid.AddGrowableCol(1, 1)
        self._kind = self._choice(
            grid,
            "&What kind of message:",
            list(_CATEGORIES),
            "Whether this is a fault, a question, an accessibility problem or an idea. "
            "It only helps us route it; say anything you like below.",
        )
        self._summary = self._field(
            grid,
            "S&ubject:",
            "A short line saying what this is about, the way an email subject does.",
        )
        self._message = self._field(
            grid,
            "What &happened:",
            "Describe it in as much or as little detail as you like. "
            "This is the part a person reads first.",
            multiline=True,
        )
        self._expected = self._field(
            grid,
            "What you e&xpected:",
            "What you thought would happen instead. Optional.",
            multiline=True,
        )
        self._steps = self._field(
            grid,
            "Steps to &reproduce:",
            "How somebody else could make it happen. Optional, and worth more than "
            "anything else when you can give it.",
            multiline=True,
        )
        self._email = self._field(
            grid,
            "Your &email address:",
            # Reworded 2026-09-26: this form always sends from the reader's own
            # mail account, so "nobody will be able to answer you" was untrue.
            "Where support should reply. Optional -- the message goes from your own "
            "mail account, so support can answer that; fill this in only if you "
            "want the answer somewhere else.",
        )
        self._reader = self._choice(
            grid,
            "Screen re&ader:",
            list(_SCREEN_READERS),
            "Which screen reader you use, if any. Filled in from what is running.",
        )
        root.Add(grid, 1, wx.EXPAND | wx.ALL, 8)

        included = wx.StaticText(
            self.dialog,
            label="Also included: "
            + ", ".join([
                self._product or "this app",
                *(f"your {key} ({value})" for key, value in self._extra.items()),
            ])
            + ", and your Windows version.",
        )
        root.Add(included, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        # No mnemonic on either: Enter and Escape already reach them, and every
        # letter they give up is one fewer collision in a dense dialog (GATE-14).
        self._send = wx.Button(self.dialog, wx.ID_OK, "Send")
        self._send.SetHelpText(
            "Opens your mail program with this message written out. "
            "Nothing leaves your machine until you send it there."
        )
        cancel = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Closes without writing anything.")
        buttons.AddStretchSpacer()
        buttons.Add(self._send, 0, wx.RIGHT, 6)
        buttons.Add(cancel, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)

        self._prefill()
        self.dialog.SetSizerAndFit(root)
        self._send.Bind(wx.EVT_BUTTON, lambda _e: self._submit())
        bind_close_button(self.dialog, cancel, modeless=False)
        apply_modal_ids(self.dialog, affirmative_id=self._send.GetId(), escape_id=cancel.GetId())
        try:
            _show_modal_dialog(self._host, self.dialog, TITLE)
        finally:
            self.dialog.Destroy()

    # -- fields -----------------------------------------------------------------

    def _field(self, grid: Any, label: str, help_text: str, *, multiline: bool = False) -> Any:
        wx = self._wx
        # Label before field, always: the dialog z-order gate reads tab order,
        # and a screen reader names a field from the static text before it.
        grid.Add(wx.StaticText(self.dialog, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
        style = wx.TE_MULTILINE if multiline else 0
        control = wx.TextCtrl(self.dialog, style=style, size=(360, 72 if multiline else -1))
        control.SetName(label.replace("&", "").rstrip(":"))
        control.SetHelpText(help_text)
        grid.Add(control, 1, wx.EXPAND)
        return control

    def _choice(self, grid: Any, label: str, options: list[str], help_text: str) -> Any:
        wx = self._wx
        grid.Add(wx.StaticText(self.dialog, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
        control = wx.Choice(self.dialog, choices=options)
        control.SetSelection(0)
        control.SetName(label.replace("&", "").rstrip(":"))
        control.SetHelpText(help_text)
        grid.Add(control, 1, wx.EXPAND)
        return control

    def _prefill(self) -> None:
        if self._prefill_summary:
            self._summary.SetValue(self._prefill_summary)
        if self._prefill_body:
            self._message.SetValue(self._prefill_body)
        detected = _detected_screen_reader()
        if detected:
            for index, name in enumerate(_SCREEN_READERS):
                if name.lower() == detected.lower():
                    self._reader.SetSelection(index)
                    break

    # -- sending ----------------------------------------------------------------

    def _message_from_fields(self) -> SupportMessage:
        reader = self._reader.GetStringSelection()
        from quill.core.support_screen_reader import screen_reader_support_facts

        facts = dict(getattr(self, "_extra", {}))
        facts.update(screen_reader_support_facts(reader))
        return SupportMessage(
            product=self._product,
            summary=self._summary.GetValue().strip(),
            message=self._message.GetValue().strip(),
            category=self._kind.GetStringSelection(),
            expected=self._expected.GetValue().strip(),
            steps=self._steps.GetValue().strip(),
            reply_email=self._email.GetValue().strip(),
            platform=_platform_label(),
            screen_reader="" if reader == _SCREEN_READERS[0] else reader,
            extra=facts,
        )

    def _submit(self) -> None:
        message = self._message_from_fields()
        problems = validate(message)
        if problems:
            # Spoken and shown: the first problem is the one to fix, and a list
            # read out at once is a list nobody retains.
            _announce(self._host, problems[0])
            _message_box(self._host, "\n".join(problems))
            return
        if send_by_mail(self._host, message):
            self.dialog.EndModal(self._wx.ID_OK)


# -- the mail handoff -----------------------------------------------------------


def send_by_mail(
    host: Any,
    message: SupportMessage,
    *,
    title: str = TITLE,
    opened: str = (
        "Your mail program is opening with the message ready. "
        "Nothing is sent until you send it there."
    ),
) -> bool:
    """Hand *message* to the mail program. True when one answered.

    Shared since 2026-09-26 so Suggest a Station or Podcast reaches support by
    exactly this route -- the same length cut, the same clipboard copy, the
    same "no mail program" answer -- rather than a second copy of it that
    drifts. *opened* is what is said when the mail program opens; *title*
    captions the message box when none does. False leaves the caller's window
    open, so what was typed is still there to copy.
    """
    url, shortened = build_mailto_url(message)
    full_text = f"To: {SUPPORT_EMAIL}\nSubject: {build_subject(message)}\n\n{build_body(message)}"
    if shortened:
        _copy(host, full_text)
    if _launch(url):
        tail = (
            " It was too long for your mail program, so the complete text is on "
            "your clipboard -- paste it in with Control V."
            if shortened
            else ""
        )
        _announce(host, opened + tail)
        return True
    _offer_clipboard(host, full_text, title=title)
    return False


def _offer_clipboard(host: Any, full_text: str, *, title: str = TITLE) -> None:
    """No mail program answered. Say so, and hand over the whole message."""
    copied = _copy(host, full_text)
    where = (
        "The whole message is on your clipboard."
        if copied
        else "Copy what you typed before closing this."
    )
    _message_box(
        host,
        "This machine has no mail program set up to answer, so nothing was "
        f"opened.\n\nWrite to {SUPPORT_EMAIL} however you normally send "
        f"email -- webmail is fine. {where}",
        title=title,
    )
    _announce(host, f"No mail program answered. Write to {SUPPORT_EMAIL}. {where}")


# -- host plumbing --------------------------------------------------------------
#
# Every app reaches this surface, and they do not all have the same shell:
# QUILL and the AppShellFrame apps carry _show_modal_dialog/_announce, while
# QuillBeacon and QUILL Lite are plain frames. So each helper asks the host for
# the method and falls back to the shared contract rather than requiring one
# shape -- which is what lets one dialog serve all ten surfaces.


def _parent(host: Any) -> Any:
    return getattr(host, "frame", host)


def _announce(host: Any, text: str) -> None:
    speak = getattr(host, "_announce", None)
    if not callable(speak):
        # QuillBeacon speaks through an Announcer rather than the shell's
        # method name. Without this branch its support form would show every
        # message and say none of them -- silent exactly where the app is
        # telling you something the screen reader cannot know.
        announcer = getattr(host, "announcer", None)
        say = getattr(announcer, "say", None)
        speak = (lambda message: say(message, "normal")) if callable(say) else None
    if callable(speak):
        try:
            speak(text)
        except Exception:  # noqa: BLE001 - speech must never break the flow
            pass


def _show_modal_dialog(host: Any, dialog: Any, label: str) -> int:
    """Show through the host's announcing path, or the shared contract.

    Named for the contract rather than for brevity: the dialog-hardening gate
    reads the showing scope and looks for this name, and a helper called
    something shorter would have made the scope read as though it showed the
    dialog raw -- which is exactly the drift the gate exists to catch.
    """
    show = getattr(host, "_show_modal_dialog", None)
    if callable(show):
        return int(show(dialog, label))
    from quill.ui.dialog_contract import show_modal_dialog

    return int(show_modal_dialog(dialog, label, announce=getattr(host, "_announce", None)))


def _message_box(host: Any, text: str, *, title: str = TITLE) -> None:
    import wx

    box = getattr(host, "_show_message_box", None)
    if callable(box):
        box(text, title, wx.OK | wx.ICON_INFORMATION)
        return
    from quill.ui.dialog_contract import show_message_box

    show_message_box(
        text,
        title,
        wx.OK | wx.ICON_INFORMATION,
        _parent(host),
        announce=getattr(host, "_announce", None),
    )


def _copy(host: Any, text: str) -> bool:
    copy = getattr(host, "_copy_to_clipboard", None)
    if callable(copy):
        try:
            return bool(copy(text))
        except Exception:  # noqa: BLE001 - a clipboard failure is never fatal
            return False
    import wx

    try:
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(text))
            finally:
                wx.TheClipboard.Close()
            return True
    except Exception:  # noqa: BLE001 - a clipboard failure is never fatal
        pass
    return False


def _launch(url: str) -> bool:
    """Hand *url* to the OS. False when nothing answered.

    The stdlib goes first on purpose. ``webbrowser.open`` reaches
    ``os.startfile`` on Windows, which is ShellExecute -- the call that knows
    what a ``mailto:`` is. ``wx.LaunchDefaultBrowser`` is documented for web
    addresses, and a wx build that quietly hands a mailto to a browser would
    look like it worked while the message went nowhere.
    """
    try:
        import webbrowser

        if bool(webbrowser.open(url)):
            return True
    except Exception:  # noqa: BLE001 - fall through to wx
        pass
    try:
        import wx

        return bool(wx.LaunchDefaultBrowser(url))
    except Exception:  # noqa: BLE001 - no handler is a normal outcome here
        return False


def _platform_label() -> str:
    import platform

    try:
        return platform.platform()
    except Exception:  # noqa: BLE001 - never block a report on an OS query
        return ""


def _detected_screen_reader() -> str:
    try:
        from quill.core.support_screen_reader import detected_reader_name

        return detected_reader_name()
    except Exception:  # noqa: BLE001 - detection is a convenience, not a requirement
        return ""
