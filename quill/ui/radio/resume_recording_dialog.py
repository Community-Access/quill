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
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._result: tuple[str, bool] | None = None
        self._resume_id = int(wx.NewIdRef())

        self.dialog = wx.Dialog(parent, title="Resume Recording")
        root = wx.BoxSizer(wx.VERTICAL)

        end_label = scheduled_end.replace("T", " ") if scheduled_end else ""
        when_part = f" until {end_label}." if end_label else "."
        message = (
            f"A recording of {station_name} was in progress{when_part}\n\n"
            f"Resume it for the remaining {remaining_minutes} minute(s)?"
        )
        intro = wx.StaticText(self.dialog, label=message)
        intro.SetName("Resume recording prompt")
        intro.Wrap(380)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        self._remember_check = wx.CheckBox(self.dialog, label="&Don't ask me again")
        self._remember_check.SetName(
            "Don't ask me again -- remembers this choice; change it later in Preferences"
        )
        self._remember_check.SetValue(False)
        root.Add(self._remember_check, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        resume_btn = wx.Button(self.dialog, self._resume_id, "&Resume")
        resume_btn.SetName("Resume the recording for the remaining time")
        skip_btn = wx.Button(self.dialog, wx.ID_CANCEL, "&Skip")
        skip_btn.SetName("Skip resuming; leave the recording as it is")
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
    single "Resume all / Skip all" choice listing each station -- friendlier for
    a screen-reader user than N sequential prompts. Returns ``(action,
    remember)`` where ``action`` is ``"resume"`` (resume every one) or ``"skip"``
    (discard every one), or ``None`` if dismissed (treated as skip). The station
    list is a read-only, arrow-reviewable field so the names can be checked
    before choosing.
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
        self._resume_id = int(wx.NewIdRef())

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
        listing.SetMinSize((420, min(200, 24 * max(1, count) + 16)))
        root.Add(listing, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        prompt = wx.StaticText(
            self.dialog, label="Resume all of them for their remaining time?"
        )
        prompt.SetName("Resume prompt")
        root.Add(prompt, 0, wx.EXPAND | wx.ALL, 10)

        self._remember_check = wx.CheckBox(self.dialog, label="&Don't ask me again")
        self._remember_check.SetName(
            "Don't ask me again -- remembers this choice; change it later in Preferences"
        )
        self._remember_check.SetValue(False)
        root.Add(self._remember_check, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        resume_btn = wx.Button(self.dialog, self._resume_id, "&Resume All")
        resume_btn.SetName("Resume every interrupted recording for its remaining time")
        skip_btn = wx.Button(self.dialog, wx.ID_CANCEL, "&Skip All")
        skip_btn.SetName("Skip resuming; leave the recordings as they are")
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
