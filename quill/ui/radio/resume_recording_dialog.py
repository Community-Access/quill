"""Resume an in-progress radio recording after a restart (R3).

Shown at launch when an active-recording marker is found and the user's
remembered choice is ``"ask"`` (``RadioHistory.recording_resume_choice``).
Offers Resume (restart the recording for the remaining minutes) or Skip, with a
"Don't ask me again" checkbox that persists the choice as ``"always"`` or
``"never"`` -- the same remembered-default pattern the close-confirm dialog uses.

Keyboard-first and announced: Resume is the affirmative (Enter), Skip/Cancel is
the escape, and every control has an accessible name. Goes through the shared
dialog contract so the modal-id / apply_modal_ids keyboard rules hold.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog
from quill.ui.dpi import dip


class ResumeRecordingDialog:
    """Returns ``(action, remember)`` where ``action`` is ``"resume"`` or
    ``"skip"``, or ``None`` if the user dismissed/cancelled (treated as skip,
    leaving the marker to age out past the grace window)."""

    def __init__(
        self,
        parent: object,
        *,
        station_name: str,
        remaining_minutes: int,
        scheduled_end: str,
        message: str = "",
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._result: tuple[str, bool] | None = None
        # Hold the IdRef: int(wx.NewIdRef()) frees the id at once, and the Resume
        # button then asserts "id count already 0" -- the dialog could not be
        # built at all, so no resume offer was ever shown (found 2026-09-25).
        self._resume_ref = wx.NewIdRef()
        self._resume_id = int(self._resume_ref)

        self.dialog = wx.Dialog(parent, title="Resume Recording")
        root = wx.BoxSizer(wx.VERTICAL)

        if not message:
            # Callers pass the full sentence (quill.core.radio.resume_words):
            # what was recorded, where it is kept, what each button does.
            # This fallback still never shows a raw ISO timestamp.
            from quill.core.radio.recording_resume import ActiveRecordingMarker
            from quill.core.radio.resume_words import offer_sentence

            marker = ActiveRecordingMarker(
                station_name, "-", "", "", "", scheduled_end, remaining_minutes
            )
            message = offer_sentence(marker, left=remaining_minutes, seconds=None, where="")
        intro = wx.StaticText(self.dialog, label=message)
        intro.SetName("Resume recording prompt")
        intro.Wrap(380)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        self._remember_check = wx.CheckBox(self.dialog, label="&Don't ask me again")
        self._remember_check.SetName(
            "Don't ask me again -- remembers this choice; Preferences can change it"
        )
        self._remember_check.SetValue(False)
        root.Add(self._remember_check, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        resume_btn = wx.Button(self.dialog, self._resume_id, "&Resume")
        resume_btn.SetName("Resume the recording for the remaining time")
        skip_btn = wx.Button(self.dialog, wx.ID_CANCEL, "&Skip")
        skip_btn.SetName("Skip resuming; record nothing more and delete nothing")
        buttons.Add(resume_btn, 0, wx.RIGHT, 6)
        buttons.Add(skip_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        self.dialog.SetSizerAndFit(root)

        resume_btn.Bind(wx.EVT_BUTTON, lambda _e: self._choose("resume"))
        skip_btn.Bind(wx.EVT_BUTTON, lambda _e: self._choose("skip"))
        # Escape (via SetEscapeId) and the system X both synthesize an
        # ID_CANCEL/OnCancel -> EndModal(ID_CANCEL) with _result still None,
        # which show() returns as None (treated as a skip, marker left to age).

    def _choose(self, action: str) -> None:
        self._result = (action, bool(self._remember_check.GetValue()))
        self.dialog.EndModal(self._resume_id if action == "resume" else self._wx.ID_CANCEL)

    def show(self) -> tuple[str, bool] | None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._resume_id,
            affirmative_label="Resume",
            cancel_id=wx.ID_CANCEL,
            escape_id=wx.ID_CANCEL,
        )
        try:
            show_modal_dialog(self.dialog, "Resume Recording", announce=self._announce)
        finally:
            self.dialog.Destroy()
        # _result is set when Resume/Skip was clicked; None when dismissed
        # without a choice (Escape/X) -- the caller treats None as skip.
        return self._result


class ResumeRecordingsBatchDialog:
    """Resume *several* interrupted recordings at once (concurrent recording).

    When more than one recording was in progress at a crash, this offers a
    single "Resume all / Skip all" choice listing each recording -- its station,
    start, how much was recorded and how much is left -- friendlier for a
    screen-reader user than N sequential prompts. Returns ``(action, remember)``
    where ``action`` is ``"resume"`` (resume every one) or ``"skip"`` (resume
    none; what each recorded is kept, nothing is deleted), or ``None`` if
    dismissed (offered again while inside the grace window). The list is a
    read-only, arrow-reviewable field so the recordings can be checked before
    choosing.
    """

    def __init__(
        self,
        parent: object,
        *,
        lines: list[str],
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._result: tuple[str, bool] | None = None
        # Hold the IdRef: int(wx.NewIdRef()) frees the id at once, and the Resume
        # button then asserts "id count already 0" -- the dialog could not be
        # built at all, so no resume offer was ever shown (found 2026-09-25).
        self._resume_ref = wx.NewIdRef()
        self._resume_id = int(self._resume_ref)

        count = len(lines)
        self.dialog = wx.Dialog(parent, title="Resume Recordings")
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            self.dialog,
            label=f"{count} recordings were in progress when Quill Radio last closed.",
        )
        intro.SetName("Resume recordings prompt")
        intro.Wrap(420)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        listing = wx.TextCtrl(
            self.dialog,
            value="\n".join(lines),
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
        )
        listing.SetName("Interrupted recordings; review with the arrow keys")
        listing.SetMinSize((dip(listing, 420), min(200, 24 * max(1, count) + 16)))
        root.Add(listing, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        prompt = wx.StaticText(
            self.dialog,
            label=(
                "Resume All records the remaining time of each as a separate file. "
                "Skip All records nothing more. Either way, nothing already recorded "
                "is deleted."
            ),
        )
        prompt.SetName("Resume prompt")
        root.Add(prompt, 0, wx.EXPAND | wx.ALL, 10)

        self._remember_check = wx.CheckBox(self.dialog, label="&Don't ask me again")
        self._remember_check.SetName(
            "Don't ask me again -- remembers this choice; Preferences can change it"
        )
        self._remember_check.SetValue(False)
        root.Add(self._remember_check, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        resume_btn = wx.Button(self.dialog, self._resume_id, "&Resume All")
        resume_btn.SetName("Resume every interrupted recording for its remaining time")
        skip_btn = wx.Button(self.dialog, wx.ID_CANCEL, "&Skip All")
        skip_btn.SetName("Skip resuming; record nothing more and delete nothing")
        buttons.Add(resume_btn, 0, wx.RIGHT, 6)
        buttons.Add(skip_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        self.dialog.SetSizerAndFit(root)

        resume_btn.Bind(wx.EVT_BUTTON, lambda _e: self._choose("resume"))
        skip_btn.Bind(wx.EVT_BUTTON, lambda _e: self._choose("skip"))

    def _choose(self, action: str) -> None:
        self._result = (action, bool(self._remember_check.GetValue()))
        self.dialog.EndModal(self._resume_id if action == "resume" else self._wx.ID_CANCEL)

    def show(self) -> tuple[str, bool] | None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._resume_id,
            affirmative_label="Resume All",
            cancel_id=wx.ID_CANCEL,
            escape_id=wx.ID_CANCEL,
        )
        try:
            show_modal_dialog(self.dialog, "Resume Recordings", announce=self._announce)
        finally:
            self.dialog.Destroy()
        return self._result
