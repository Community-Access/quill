"""The Scribe Status dialog: account, pages, pace and the queue, in one place.

Scribe Status (QUILL's Tools > Scribe for Documents, QUILL Lite's File >
Scribe for Documents, and every other app's Scribe for Documents submenu)
opens this through the dialog contract. Everything is in one read-only
multi-line field built by :func:`quill.core.scribe.status.build_status`, so a
screen reader arrows through it and a braille display pans it; the first line
is the most important fact.

* What is on this computer (the queue, the sign-in) shows at once; the account
  is read from Scribe on the controller's background pool, so the dialog never
  waits on the network. When the account arrives after the dialog is showing,
  the new first line is said once, because a focused field whose text changes
  is not read again by NVDA, JAWS or Narrator (GATE-13 allows exactly this).
* **Refresh** reads everything again and says once that it did, with the
  first line. **Sign In...** shows only when there is no sign-in.
* **Conversions on This Computer** closes this and opens that window (a modal
  dialog would block it). **Close** and Escape close; focus goes back where
  it was (the controller restores it).
* The field wraps inside the dialog at any size and font scale: it has no
  horizontal scrolling, expands with the dialog, and its minimum width is capped
  to the display, so it is never wider than the dialog's client area; the
  buttons sit in a wrap sizer so a long row at 200 percent moves to a second
  line instead of widening the dialog (``test_scribe_status_dialog.py``).
"""

from __future__ import annotations

import time
from typing import Any

import wx

from quill.core.scribe import CONVERSIONS_TITLE, STATUS_TITLE
from quill.core.scribe.status import StatusInputs, StatusReport, build_status
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button, readable_min_size

#: The field's starting height in lines, before the dialog is resized.
_LINES = 16

#: How long after opening an arriving account is drawn silently (milliseconds).
_GRACE_MS = 500


def gather_local(controller: Any, **account: Any) -> StatusInputs:
    """Everything on this computer, now; *account* adds what Scribe said."""
    session = controller.session
    signed_in = bool(session.is_signed_in())
    bundle = session.bundle() if signed_in and hasattr(session, "bundle") else None
    queue = controller.queue
    try:
        jobs = tuple(queue.jobs())
        actions, paused = queue.pace()
        holder = queue.holder() or {}
    except (OSError, TimeoutError):
        jobs, actions, paused, holder = (), 0, 0.0, {}
    return StatusInputs(
        app_name=controller.app_name,
        signed_in=signed_in,
        renews=bool(bundle.refresh_token) if bundle is not None else True,
        sign_in_ends=float(bundle.expires_at) if bundle is not None else 0.0,
        jobs=jobs,
        runner_app=str(holder.get("app") or ""),
        actions_this_minute=actions,
        paused_until=paused,
        now=time.time(),
        **account,
    )


class ScribeStatusDialog(wx.Dialog):
    def __init__(self, parent: Any, controller: Any) -> None:
        super().__init__(
            parent, title=STATUS_TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.SetName("scribe_status_dialog")  # F1 finds its topic by this name (topics.json)
        self._controller = controller
        self._account: dict[str, Any] = {}
        self._shown = False
        self._fetching = 0  # the generation of the newest account read
        #: What the Conversions button asks the controller to open after Close.
        self.then_open = ""
        self.report: StatusReport | None = None

        sizer = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self, label="&Status:")
        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        # No wx.HSCROLL: the field wraps to its own width, which the sizer keeps
        # inside the dialog. TE_RICH2 is not used: a plain edit is what every
        # screen reader and braille display reads best.
        self.text = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.text.SetName("Scribe Status")
        self.text.SetHelpText(
            "Who is signed in to Scribe for Documents, the pages left, and every "
            "conversion on this computer. Arrow through it; Refresh reads it again."
        )
        width, height = readable_min_size(self, lines=_LINES)
        self.text.SetMinSize(wx.Size(self._capped_width(width), height))
        sizer.Add(self.text, 1, wx.EXPAND | wx.ALL, 6)

        buttons = wx.WrapSizer(wx.HORIZONTAL)
        self.refresh_button = wx.Button(self, label="&Refresh")
        self.refresh_button.SetHelpText(
            "Reads your Scribe account and this computer's conversions again."
        )
        self.sign_in_button = wx.Button(self, label="Sign &In...")
        self.sign_in_button.SetHelpText(
            "Signs in to Scribe for Documents on Scribe's own page in your browser."
        )
        self.account_button = wx.Button(self, label="Open My Scribe &Account in Browser")
        self.account_button.SetHelpText(
            "Opens your Scribe account in your browser, already signed in: purchases, "
            "retention and settings."
        )
        self.conversions_button = wx.Button(self, label="&Conversions on This Computer")
        self.conversions_button.SetHelpText(
            f"Closes Scribe Status and opens {CONVERSIONS_TITLE}, where each job has its commands."
        )
        close = wx.Button(self, wx.ID_CANCEL, label="Close")
        close.SetHelpText("Closes Scribe Status.")
        for button in (
            self.refresh_button,
            self.sign_in_button,
            self.account_button,
            self.conversions_button,
            close,
        ):
            buttons.Add(button, 0, wx.ALL, 6)
        sizer.Add(buttons, 0, wx.EXPAND)
        self.SetSizer(sizer)
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL)
        bind_close_button(self, close, modeless=False)

        self.refresh_button.Bind(wx.EVT_BUTTON, lambda _e: self.refresh(announce=True))
        self.sign_in_button.Bind(wx.EVT_BUTTON, self._sign_in)
        self.account_button.Bind(wx.EVT_BUTTON, lambda _e: controller.open_account_in_browser())
        self.conversions_button.Bind(wx.EVT_BUTTON, self._conversions)
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

        self.refresh(announce=False)
        self.Fit()
        self._fit_to_display()
        self.text.SetFocus()
        # An account that arrives within the grace period is drawn before the
        # screen reader has finished reading the dialog, and is read with it;
        # one that arrives later is said (review, 2026-11-23: a fast answer said
        # at once talked over the dialog's own focus speech).
        self._grace = wx.CallLater(_GRACE_MS, self._mark_shown)

    # ------------------------------------------------------------ layout

    def _capped_width(self, width: int) -> int:
        """Never wider than the display, whatever the font scale."""
        area = wx.Display(max(0, wx.Display.GetFromWindow(self))).GetClientArea()
        return max(1, min(width, int(area.width * 0.9)))

    def _fit_to_display(self) -> None:
        area = wx.Display(max(0, wx.Display.GetFromWindow(self))).GetClientArea()
        size = self.GetSize()
        fitted = wx.Size(min(size.width, area.width), min(size.height, area.height))
        if fitted != size:
            self.SetSize(fitted)
        self.Layout()

    def _mark_shown(self) -> None:
        try:
            self._shown = True
        except RuntimeError:  # the dialog closed first
            pass

    def Destroy(self) -> bool:  # noqa: N802 - wx API
        try:
            self._grace.Stop()
        except (AttributeError, RuntimeError):
            pass
        return bool(super().Destroy())

    # ------------------------------------------------------------ content

    def _alive(self) -> bool:
        try:
            return bool(self) and not self.IsBeingDeleted()
        except RuntimeError:
            return False

    def render(self) -> StatusReport:
        """Rebuild the text from this computer's facts and the last account read."""
        report = build_status(gather_local(self._controller, **self._account))
        self.report = report
        where = self._caret_place()
        self.text.ChangeValue(report.text)
        position = self._position_of(report.text, where)
        self.text.SetInsertionPoint(position)
        self.text.ShowPosition(position)
        self.sign_in_button.Show(report.offer_sign_in)
        self.Layout()
        return report

    # The caret stays where the person is reading: in the same section, on the
    # same line of it, when the text is rebuilt (review, 2026-11-23). Positions
    # count a line break as two on Windows, so offsets go through GetRange.

    def _caret_place(self) -> tuple[str, int, int] | None:
        """(section heading, line within it, column), or None for the top."""
        if wx.Window.FindFocus() is not self.text:
            return None
        before = self.text.GetRange(0, self.text.GetInsertionPoint())
        if not before:
            return None
        lines = before.split("\n")
        index, column = len(lines) - 1, len(lines[-1])
        all_lines = self.text.GetValue().split("\n")
        start = index
        while start > 0 and all_lines[start - 1] != "":
            start -= 1
        return all_lines[start], index - start, column

    def _position_of(self, text: str, where: tuple[str, int, int] | None) -> int:
        if where is None:
            return 0
        heading, offset, column = where
        lines = text.split("\n")
        key = heading.split(" (")[0]
        starts = [
            i
            for i, line in enumerate(lines)
            if line.split(" (")[0] == key and (i == 0 or not lines[i - 1])
        ]
        if not starts:
            return 0
        start = starts[0]
        end = start
        while end + 1 < len(lines) and lines[end + 1] != "":
            end += 1
        line = min(start + offset, end)
        chars = sum(len(item) + 1 for item in lines[:line]) + min(column, len(lines[line]))
        breaks = line if wx.Platform == "__WXMSW__" else 0
        return chars + breaks

    def at_top(self) -> bool:
        return self.text.GetInsertionPoint() == 0

    def refresh(self, *, announce: bool) -> None:
        """Show what is known now, then read the account in the background."""
        controller = self._controller
        signed_in = bool(controller.session.is_signed_in())
        if signed_in:
            # Keep the last account while the new one is read: the person may be
            # reading it, and "checking" would take away what they had.
            self._account = {**self._account, "checking": True}
        else:
            self._account = {}
        self.render()
        if not signed_in:
            if announce:
                self._say(f"Scribe Status updated. {self.report.first_line}")
            return
        self._fetching += 1
        generation = self._fetching
        controller._background(  # noqa: SLF001 - the controller's own pool
            lambda: controller.client().account(),
            lambda account: self._account_read(generation, announce, account=account),
            lambda error: self._account_failed(generation, announce, error),
        )

    def _account_read(self, generation: int, announce: bool, *, account: Any) -> None:
        if generation != self._fetching or not self._alive():
            return
        self._account = {"account": account}
        report = self.render()
        # The first line is said only when the caret is on it; somebody reading
        # further down hears that it changed, and stays where they were.
        first = f" {report.first_line}" if self.at_top() else ""
        if announce:
            self._say(f"Scribe Status updated.{first}")
        elif self._shown and first:
            self._say(report.first_line)

    def _account_failed(self, generation: int, announce: bool, error: BaseException) -> None:
        if generation != self._fetching or not self._alive():
            return
        from quill.core.scribe.errors import ScribeError, ScribeSignInError

        message = error.message if isinstance(error, ScribeError) else str(error)
        code = str(getattr(error, "code", "") or "")
        self._account = {
            # The last good account stays readable below the error.
            "account": self._account.get("account"),
            "error_message": message,
            "error_code": code,
            "sign_in_ended": isinstance(error, ScribeSignInError),
        }
        self.render()
        # Said once, the server's sentence; the code is in the text for Copy
        # and braille, never spoken (quill.core.scribe.errors).
        if announce or self._shown:
            self._say(f"Your Scribe account could not be read: {message}")

    def _say(self, text: str) -> None:
        self._controller.host.scribe_announce(text)

    # ------------------------------------------------------------ buttons

    def _sign_in(self, _event: Any) -> None:
        self._controller.sign_in()
        if not self._alive():
            return
        self.refresh(announce=False)
        target = self.text if self._controller.session.is_signed_in() else self.sign_in_button
        target.SetFocus()

    def _conversions(self, _event: Any) -> None:
        self.then_open = "conversions"
        self.EndModal(wx.ID_CANCEL)

    def _on_char_hook(self, event: Any) -> None:
        # A multi-line edit may keep Escape for itself; the dialog closes on it.
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
            return
        event.Skip()


__all__ = ["ScribeStatusDialog", "gather_local"]
