"""Crash Report submit dialog (#622).

When QUILL hits an unhandled exception, the excepthook in
:mod:`quill.__main__` saves a local traceback file and then offers
the user a chance to send a redacted report to the developers. This
dialog is the wx half of that flow: it shows the user the report
that :func:`quill.stability.crash_submit.build_crash_report_payload`
built, lets them add free-text context, and returns a
:class:`CrashReportDialogResult` so the excepthook can decide what
to do next.

The dialog is intentionally read-only with respect to the payload --
the user can type into the three description fields, but the
preview panel is a static rendering of the redacted body. Three
buttons cover the three outcomes:

- **Send report** -- submit the report to the developers via
  :func:`quill.core.issue_submit.submit_crash_issue` (the excepthook
  hands the dialog's result to that function).
- **Copy to clipboard** -- leave the local crash file in place but
  put the redacted report on the system clipboard so the user can
  paste it into a manual report-bug form.
- **Don't send** -- cancel; the local crash file is preserved.

The default button is **Don't send** so a user who opens the dialog
by accident does not accidentally send anything. Escape is wired to
the same button via :func:`apply_modal_ids`.

The parent is the real ``wx.Frame`` (``MainFrame.frame``), not the
``MainFrame`` mixin, per the pattern set by the #624 fix in
:mod:`quill.ui.main_frame_hygiene`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import wx

from quill.core.i18n import _
from quill.stability.crash_submit import (
    CrashReportPayload,
    redact_user_description,
    render_crash_report_preview,
)
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

Act = Literal["send", "copy", "cancel"]


@dataclass(frozen=True)
class CrashReportDialogResult:
    """The dialog's outcome plus the user-supplied context fields.

    Exactly one of ``act`` is set:

    - ``"send"`` -- the user clicked **Send report**. The excepthook
      passes the merged body and metadata to
      :func:`quill.core.issue_submit.submit_crash_issue`.
    - ``"copy"`` -- the user clicked **Copy to clipboard**. The
      excepthook copies the body to the system clipboard.
    - ``"cancel"`` -- the user clicked **Don't send** or pressed
      Escape. The local crash file is preserved; no network call
      happens.

    The three ``*_text`` fields hold the redacted, length-bounded
    versions of the dialog's three text inputs. They are empty
    strings when the user did not type anything in that field.
    """

    act: Act
    what_doing_text: str = ""
    triggering_command_text: str = ""
    expected_behaviour_text: str = ""


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------


class CrashReportDialog:
    """Modal crash-report dialog with a redacted preview and three buttons.

    The dialog is parented to ``parent`` (the real ``wx.Frame``). The
    caller supplies the :class:`CrashReportPayload` produced by
    :func:`quill.stability.crash_submit.build_crash_report_payload`.
    The dialog never modifies the payload -- the user-supplied
    description fields are merged into a fresh body at submit time by
    the excepthook, not by the dialog.
    """

    # Custom wx id for the "Copy to clipboard" button. We don't reuse
    # a stock id because the user-action semantics are different
    # (this is a parallel action, not an affirmative or cancel).
    _ID_COPY: int = wx.ID_HIGHEST + 1

    def __init__(
        self,
        parent: wx.Window,
        *,
        payload: CrashReportPayload,
        announce: Callable[[str], None] | None = None,
    ) -> None:
        self._wx = wx
        self._parent = parent
        self._payload = payload
        self._announce = announce or (lambda _msg: None)
        self._result: CrashReportDialogResult = CrashReportDialogResult(act="cancel")

        # --- Dialog window -------------------------------------------------
        self.dialog: wx.Dialog = wx.Dialog(
            parent,
            title=_("Report Crash"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetName("crash_report_dialog")
        self.dialog.SetSize((720, 620))
        self.dialog.SetMinSize((560, 480))

        root = wx.BoxSizer(wx.VERTICAL)

        # --- Header / explanation -----------------------------------------
        intro = wx.StaticText(
            self.dialog,
            label=_(
                "QUILL encountered an unexpected error and closed. "
                "You can review a redacted summary below and choose "
                "whether to send it to the developers. Nothing is sent "
                "unless you click 'Send report'."
            ),
        )
        intro.SetName("Introduction")
        intro.Wrap(680)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 8)

        # --- What-we-will-send preview ------------------------------------
        preview_label = wx.StaticText(self.dialog, label=_("What we will send:"))
        preview_label.SetName("Preview label")
        root.Add(preview_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # Read-only TextCtrl: behaves like a static text panel but
        # scrollable and selectable. We use a multiline TextCtrl with
        # the TE_READONLY style rather than a StaticText so the user
        # can scroll the preview if the report is long.
        preview_text = render_crash_report_preview(payload)
        self._preview = wx.TextCtrl(
            self.dialog,
            value=preview_text,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
        )
        self._preview.SetName("Report preview")
        self._preview.SetMinSize((560, 200))
        root.Add(self._preview, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # --- User-supplied context fields ---------------------------------
        what_label = wx.StaticText(self.dialog, label=_("What were you doing when this happened?"))
        what_label.SetName("What were you doing label")
        root.Add(what_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._what_ctrl = wx.TextCtrl(self.dialog, style=wx.TE_MULTILINE)
        self._what_ctrl.SetName("What were you doing")
        self._what_ctrl.SetMinSize((560, 60))
        root.Add(self._what_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        trigger_label = wx.StaticText(
            self.dialog, label=_("What command do you think triggered it?")
        )
        trigger_label.SetName("Triggering command label")
        root.Add(trigger_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._trigger_ctrl = wx.TextCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
        self._trigger_ctrl.SetName("Triggering command")
        root.Add(self._trigger_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        expect_label = wx.StaticText(self.dialog, label=_("Expected behaviour"))
        expect_label.SetName("Expected behaviour label")
        root.Add(expect_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._expect_ctrl = wx.TextCtrl(self.dialog, style=wx.TE_MULTILINE)
        self._expect_ctrl.SetName("Expected behaviour")
        self._expect_ctrl.SetMinSize((560, 60))
        root.Add(self._expect_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # --- Buttons row --------------------------------------------------
        # Don't send is the default (Enter cancels) so a user who
        # opens the dialog by accident does not accidentally send
        # anything. See plan: "default = Don't send (recommended)".
        self._btn_send = wx.Button(self.dialog, wx.ID_OK, label=_("&Send report"))
        self._btn_send.SetName("Send report")

        self._btn_copy = wx.Button(self.dialog, self._ID_COPY, label=_("&Copy to clipboard"))
        self._btn_copy.SetName("Copy to clipboard")

        self._btn_cancel = wx.Button(self.dialog, wx.ID_CANCEL, label=_("Don't &send"))
        self._btn_cancel.SetName("Don't send")
        self._btn_cancel.SetDefault()

        btn_sizer = wx.StdDialogButtonSizer()
        btn_sizer.AddButton(self._btn_send)
        btn_sizer.AddButton(self._btn_copy)
        btn_sizer.AddButton(self._btn_cancel)
        btn_sizer.Realize()
        root.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 8)

        # --- Local crash file footer --------------------------------------
        if payload.local_crash_file is not None:
            footer = wx.StaticText(
                self.dialog,
                label=_("Local crash file: ") + str(payload.local_crash_file),
            )
            footer.SetName("Local crash file path")
            root.Add(footer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.dialog.SetSizer(root)

        # Wire modal ids so Enter triggers Send, Escape triggers Cancel.
        # Note: we want Escape -> Don't send (not Send), so the
        # escape_id is wx.ID_CANCEL. The Send button is the
        # affirmative (Enter) so the user can confirm a Send
        # explicitly.
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            cancel_id=wx.ID_CANCEL,
            escape_id=wx.ID_CANCEL,
        )

        # --- Events -------------------------------------------------------
        self._btn_send.Bind(wx.EVT_BUTTON, self._on_send)
        self._btn_copy.Bind(wx.EVT_BUTTON, self._on_copy)
        self._btn_cancel.Bind(wx.EVT_BUTTON, self._on_cancel)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show(self) -> CrashReportDialogResult:
        """Show the dialog modally and return the user's choice.

        Always destroys the dialog, even on exception. Initial focus
        lands on the "What were you doing" field so the screen reader
        announces the first input first, not the buttons.
        """
        try:
            self.dialog.CentreOnParent()
            # Initial focus on the "what were you doing" field, not
            # the default button -- this matches the design intent of
            # "default button cancels, primary input gets focus".
            self._what_ctrl.SetFocus()
            show_modal_dialog(
                self.dialog,
                _("Report Crash"),
                announce=self._announce,
            )
            return self._result
        finally:
            self.dialog.Destroy()

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_send(self, _event: wx.Event) -> None:
        self._capture_result("send")
        self.dialog.EndModal(wx.ID_OK)

    def _on_copy(self, _event: wx.Event) -> None:
        self._capture_result("copy")
        # The Copy button has a custom id, so EndModal is optional --
        # we still need it so the modal loop returns cleanly. Use
        # wx.ID_OK so show_modal_dialog sees a "non-cancel" outcome.
        self.dialog.EndModal(self._ID_COPY)

    def _on_cancel(self, _event: wx.Event) -> None:
        self._result = CrashReportDialogResult(act="cancel")
        self.dialog.EndModal(wx.ID_CANCEL)

    def _capture_result(self, act: Act) -> None:
        """Build a result from the current field values.

        Split out from the button handlers so unit tests can drive
        the result-building path without entering a real modal loop.
        The handlers themselves still call ``EndModal`` so the
        dialog closes for the live user.
        """
        self._result = CrashReportDialogResult(
            act=act,
            what_doing_text=redact_user_description(self._what_ctrl.GetValue()),
            triggering_command_text=redact_user_description(self._trigger_ctrl.GetValue()),
            expected_behaviour_text=redact_user_description(self._expect_ctrl.GetValue()),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def merge_user_context_into_body(
    body: str,
    result: CrashReportDialogResult,
) -> str:
    """Append the user's three text fields to a payload body.

    Called by the excepthook after the dialog returns. The fields are
    already redacted by :func:`redact_user_description`; this helper
    only handles the formatting (skip empty fields, add a "What
    happened" header when any field is non-empty).
    """
    parts: list[str] = []
    if result.what_doing_text:
        parts.append("What were you doing:")
        parts.append(result.what_doing_text)
    if result.triggering_command_text:
        parts.append("")
        parts.append("Triggering command:")
        parts.append(result.triggering_command_text)
    if result.expected_behaviour_text:
        parts.append("")
        parts.append("Expected behaviour:")
        parts.append(result.expected_behaviour_text)
    if not parts:
        return body
    return body.rstrip() + "\n\nUser context\n" + "\n".join(parts) + "\n"
