"""Quill Converter's Auphonic windows: Process with Auphonic, the confirmation,
and Auphonic Work Waiting.

**Process with Auphonic** gathers every choice on one page: the files (in
queue order, which is also the multitrack track order), separate productions
or one multitrack production and its title, the API token (shared with the
Audio Studio through the system's credential store), an explicit account
check that loads the presets and never uploads anything, the preset, Quick
cleanup and its noise switch (or Custom processing), and one output format.
Two buttons open the post-MVP options (PRD section 14) in their own windows,
:mod:`quill.ui.converter_auphonic_options_dialog`: Tags, Cover and Chapter
Marks, and More Options. Nothing is contacted when any of them opens.

**Send to Auphonic?** is the one confirmation for the whole submission: a
read-only text naming the service, every file sent and skipped, the mode, the
preset, the processing and the destination, with Upload and Process and
Cancel. Cancel uploads nothing.

**Auphonic Work Waiting** lists the productions Auphonic accepted that have
not been fetched, read from the local pending-work file without contacting
anybody, with Resume (which does contact Auphonic) and Dismiss.

Access keys are unique within each window (GATE-14); OK, Cancel and Close
carry none. Every control has its F1 sentence inline (GATE-CONVERTER-HELP).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import wx

from quill.core.publish.auphonic import OUTPUT_FORMATS
from quill.core.publish.auphonic_plan import (
    CUSTOM,
    MULTITRACK,
    QUICK_CLEANUP,
    SEPARATE,
    USE_PRESET,
    AuphonicChoices,
    PendingProduction,
)
from quill.ui.accessible_names import set_accessible_name
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button

PROCESS_TITLE = "Process with Auphonic"
CONFIRM_TITLE = "Send to Auphonic?"
WAITING_TITLE = "Auphonic Work Waiting"

_DEFAULT_PRESET = "Your account's default preset"
_FORMATS: tuple[tuple[str, str], ...] = (("", "Use the preset's outputs"),) + tuple(
    OUTPUT_FORMATS.items()
)


class AuphonicDialog(wx.Dialog):
    """Every Auphonic choice on one page. :meth:`choices` reads it back."""

    def __init__(
        self,
        parent: Any,
        files: list[Path],
        *,
        skipped: int,
        initial: AuphonicChoices,
        token: str,
        check: Callable[[str, Callable[[list[Any] | None, Any, str], None]], None],
        announce: Callable[[str], None],
        problem: Callable[[AuphonicChoices, str], str] = lambda _c, _t: "",
        refuse: Callable[[str], None] = lambda _text: None,
        show_modal: Callable[[wx.Dialog, str], int] | None = None,
        source_chapters: tuple[tuple[float, str], ...] = (),
    ) -> None:
        super().__init__(
            parent,
            title=PROCESS_TITLE,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            name="converter.auphonic",
        )
        self._files = files
        # The post-MVP options live in two smaller windows (Tags, Cover and
        # Chapter Marks; More Options) and come back here as one choices value.
        self._extras = initial
        self._show_modal = show_modal
        self._source_chapters = source_chapters
        self._check = check
        self._announce = announce
        self._problem = problem
        self._refuse = refuse
        self._presets: list[Any] = []
        self._account = ""
        self._checking = False
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(wx.StaticText(self, label="Files to &send, in queue order:"), 0, wx.ALL, 8)
        self._list = wx.ListBox(self, choices=[path.name for path in files], size=(-1, 110))
        set_accessible_name(self._list, "Files to send")
        self._list.SetHelpText(
            "The sound files that will be sent, in the order they are in the queue. "
            "In a multitrack production each one is a track, in this order; to "
            "change it, close this window and use Alt+Up and Alt+Down in the queue."
            + (
                f" {skipped} queued item(s) cannot be sent; the confirmation says why."
                if skipped
                else ""
            )
        )
        if files:
            self._list.SetSelection(0)
        root.Add(self._list, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        self._mode = wx.RadioBox(
            self,
            label="&How to send them",
            choices=[
                "Separate productions, one for each file",
                "One multitrack production, one track for each file",
            ],
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS,
        )
        self._mode.SetSelection(1 if initial.mode == MULTITRACK else 0)
        self._mode.SetHelpText(
            "Separate productions process each file on its own with the same preset, "
            "one after another. A multitrack production mixes the files together as "
            "tracks -- several microphones of one conversation, say -- into one result."
        )
        root.Add(self._mode, 0, wx.EXPAND | wx.ALL, 8)

        root.Add(wx.StaticText(self, label="Production &title:"), 0, wx.LEFT, 8)
        self._title = wx.TextCtrl(self, value=initial.title or (files[0].stem if files else ""))
        set_accessible_name(self._title, "Production title")
        self._title.SetHelpText(
            "The multitrack production's title, which also names the folder its "
            "result is saved in. It starts as the first file's name. Separate "
            "productions use each file's own title instead."
        )
        root.Add(self._title, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        root.Add(wx.StaticText(self, label="Auphonic API to&ken:"), 0, wx.LEFT | wx.TOP, 8)
        self._token = wx.TextCtrl(self, value=token, style=wx.TE_PASSWORD)
        set_accessible_name(self._token, "Auphonic API token")
        self._token.SetHelpText(
            "Your Auphonic API token, from the account settings page on auphonic.com. "
            "It is the same token the Audio Studio uses, kept in Windows Credential "
            "Manager and never in Quill Converter's settings."
        )
        root.Add(self._token, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._remember = wx.CheckBox(self, label="&Remember the token on this computer")
        self._remember.SetValue(True)
        self._remember.SetHelpText(
            "When checked, sending stores the token in Windows Credential Manager, "
            "where the Audio Studio and QUILL find it too. Clear it to use the token "
            "for this time only; a token already stored stays stored."
        )
        root.Add(self._remember, 0, wx.ALL, 8)

        check_row = wx.BoxSizer(wx.HORIZONTAL)
        self._check_btn = wx.Button(self, label="Check &Account and Load Presets")
        self._check_btn.SetHelpText(
            "Asks Auphonic who the token belongs to, how many credits are left, and "
            "which presets you have saved. Nothing is uploaded."
        )
        check_row.Add(self._check_btn, 0)
        root.Add(check_row, 0, wx.LEFT | wx.RIGHT, 8)
        root.Add(wx.StaticText(self, label="Account:"), 0, wx.LEFT | wx.TOP, 8)
        self._status = wx.TextCtrl(
            self, value="Not checked yet.", style=wx.TE_READONLY | wx.TE_MULTILINE, size=(-1, 44)
        )
        set_accessible_name(self._status, "Account")
        self._status.SetHelpText(
            "What the last account check found: the account name and its credits, "
            "or what went wrong. Read-only."
        )
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        root.Add(wx.StaticText(self, label="&Preset:"), 0, wx.LEFT | wx.TOP, 8)
        self._preset = wx.Choice(self)
        set_accessible_name(self._preset, "Preset")
        self._preset.SetHelpText(
            "Which of your saved Auphonic presets every production uses, or your "
            "account's default. Check Account and Load Presets fills the list; the "
            "preset you used last time is offered until then."
        )
        self._preset_ids: list[str] = []
        self._fill_presets([], initial.preset_uuid, initial.preset_label)
        root.Add(self._preset, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        self._processing = wx.RadioBox(
            self,
            label="Processin&g",
            choices=[
                "Use the preset's settings",
                "Quick cleanup: filter the sound, even out the levels, standard loudness",
                "Custom processing, set in More Options",
            ],
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS,
        )
        self._processing.SetSelection({QUICK_CLEANUP: 1, CUSTOM: 2}.get(initial.processing, 0))
        self._processing.SetHelpText(
            "Keep whatever the preset does, use Quick cleanup instead (Auphonic's "
            "filtering, leveling and loudness normalization at its usual settings), or "
            "use Custom processing: your own loudness target, peak limit and noise "
            "reduction, chosen with the More Options button."
        )
        root.Add(self._processing, 0, wx.EXPAND | wx.ALL, 8)
        self._denoise = wx.CheckBox(self, label="Reduce background &noise")
        self._denoise.SetValue(initial.denoise)
        self._denoise.SetHelpText(
            "Quick cleanup only. Lets Auphonic take out steady background noise. It "
            "can also change quiet background sounds you wanted to keep, so it is "
            "off unless you turn it on."
        )
        root.Add(self._denoise, 0, wx.LEFT | wx.RIGHT, 8)

        root.Add(wx.StaticText(self, label="Output &format:"), 0, wx.LEFT | wx.TOP, 8)
        self._format = wx.Choice(self, choices=[label for _key, label in _FORMATS])
        keys = [key for key, _label in _FORMATS]
        self._format.SetSelection(
            keys.index(initial.output_format) if initial.output_format in keys else 0
        )
        set_accessible_name(self._format, "Output format")
        self._format.SetHelpText(
            "The format the results come back in: whatever the preset says, or one "
            "format for every production. A multitrack production saves only the "
            "final mix."
        )
        root.Add(self._format, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        extra_row = wx.BoxSizer(wx.HORIZONTAL)
        self._tags_btn = wx.Button(self, label="Tags, Cover and Chapter &Marks...")
        self._tags_btn.SetHelpText(
            "Opens a window for an artist and album to tag every production with, a "
            "cover image to upload with it, and, for one production, its chapter "
            "marks. Nothing is sent from there."
        )
        self._more_btn = wx.Button(self, label="M&ore Options...")
        self._more_btn.SetHelpText(
            "Opens a window for Custom processing's loudness target, peak limit and "
            "noise reduction, a second output format, and captions with a transcript. "
            "Nothing is sent from there."
        )
        extra_row.Add(self._tags_btn, 0, wx.RIGHT, 6)
        extra_row.Add(self._more_btn, 0)
        root.Add(extra_row, 0, wx.ALL, 8)

        buttons = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        root.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)
        apply_modal_ids(
            self,
            affirmative_id=wx.ID_OK,
            affirmative_label="Review",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Cancel",
        )
        ok = self.FindWindow(wx.ID_OK)
        if ok is not None:
            ok.SetHelpText(
                "Shows everything that will be sent, and where the results go, before "
                "anything is uploaded."
            )
        self.SetSizerAndFit(root)

        self._check_btn.Bind(wx.EVT_BUTTON, lambda _e: self.check_account())
        self._tags_btn.Bind(wx.EVT_BUTTON, lambda _e: self.edit_tags())
        self._more_btn.Bind(wx.EVT_BUTTON, lambda _e: self.edit_more())
        self.Bind(wx.EVT_BUTTON, self._on_review, id=wx.ID_OK)
        self._mode.Bind(wx.EVT_RADIOBOX, lambda _e: self._sync())
        self._processing.Bind(wx.EVT_RADIOBOX, lambda _e: self._sync())
        self._sync()
        (self._token if not token else self._list).SetFocus()

    # -- state -----------------------------------------------------------------------

    def _sync(self) -> None:
        self._title.Enable(self._mode.GetSelection() == 1)
        self._denoise.Enable(self._processing.GetSelection() == 1)

    # -- the option windows (post-MVP; converter_auphonic_options_dialog) -----------

    def edit_tags(self) -> None:
        """Tags, Cover and Chapter Marks; OK keeps them for this submission."""
        from quill.ui.converter_auphonic_options_dialog import edit_tags

        single = len(self._files) == 1 or self._mode.GetSelection() == 1
        source = self._source_chapters if len(self._files) == 1 else ()
        self._extras = edit_tags(self, self._extras, single, source, self._show_modal, self._refuse)

    def edit_more(self) -> None:
        """More Auphonic Options; OK keeps them for this submission."""
        from quill.ui.converter_auphonic_options_dialog import edit_more

        self._extras = edit_more(self, self._extras, self._show_modal)

    def _fill_presets(self, presets: list[Any], wanted: str, wanted_label: str = "") -> None:
        labels = [_DEFAULT_PRESET]
        self._preset_ids = [""]
        for preset in presets:
            self._preset_ids.append(str(getattr(preset, "uuid", "")))
            labels.append(str(getattr(preset, "name", "") or getattr(preset, "uuid", "")))
        if wanted and wanted not in self._preset_ids and wanted_label:
            self._preset_ids.append(wanted)  # last time's choice, until a check
            labels.append(wanted_label)
        self._preset.Set(labels)
        self._preset.SetSelection(
            self._preset_ids.index(wanted) if wanted in self._preset_ids else 0
        )

    def token(self) -> str:
        return self._token.GetValue().strip()

    def remember_token(self) -> bool:
        return self._remember.GetValue()

    def account(self) -> str:
        return self._account

    def choices(self) -> AuphonicChoices:
        index = max(0, self._preset.GetSelection())
        uuid = self._preset_ids[index] if index < len(self._preset_ids) else ""
        processing = (USE_PRESET, QUICK_CLEANUP, CUSTOM)[max(0, self._processing.GetSelection())]
        return replace(
            self._extras,
            mode=MULTITRACK if self._mode.GetSelection() == 1 else SEPARATE,
            preset_uuid=uuid,
            preset_label=self._preset.GetString(index) if uuid else "",
            processing=processing,
            denoise=processing == QUICK_CLEANUP and self._denoise.GetValue(),
            output_format=_FORMATS[max(0, self._format.GetSelection())][0],
            title=self._title.GetValue().strip(),
        )

    def _on_review(self, event: Any) -> None:
        """Review stays here, saying why, when the choices cannot be sent."""
        reason = self._problem(self.choices(), self.token())
        if reason:
            self._refuse(reason)
            return
        event.Skip()

    # -- the account check -----------------------------------------------------------

    def check_account(self) -> None:
        """One explicit request: who, how many credits, which presets. No upload."""
        token = self.token()
        if not token:
            self._show_status("Type or paste your Auphonic API token first.")
            self._token.SetFocus()
            return
        if self._checking:
            self._announce("Still checking your Auphonic account.")
            return
        # Not disabled while it works: disabling the focused button would drop
        # focus out of the window for a screen-reader user.
        self._checking = True
        self._show_status("Checking your Auphonic account...")
        # The host runs it off the UI thread and delivers on it.
        self._check(token, self.account_checked)

    def account_checked(self, presets: list[Any] | None, info: Any, error: str) -> None:
        """The check's answer, on the UI thread (also called directly by tests)."""
        if not self:  # the window closed while Auphonic answered
            return
        self._checking = False
        if error or info is None:
            # A failed lookup never falls back to a preset silently.
            self._show_status(f"The account check failed: {error or 'no answer'}")
            return
        wanted = self._preset_ids[max(0, self._preset.GetSelection())]
        self._presets = list(presets or [])
        self._fill_presets(self._presets, wanted)
        user = getattr(info, "username", "") or "(no name)"
        credits = float(getattr(info, "credits", 0.0) or 0.0)
        self._account = f"account {user}, {credits:g} credit hours left"
        count = len(self._presets)
        self._show_status(
            f"Auphonic account {user}: {credits:g} credit hours left, "
            f"{count} saved preset{'s' if count != 1 else ''} loaded."
        )

    def _show_status(self, text: str) -> None:
        self._status.SetValue(text)
        self._announce(text)


def ask_choices(
    host: Any,
    files: list[Path],
    *,
    skipped: int,
    initial: AuphonicChoices,
    token: str,
    check: Callable[[str, Callable[[list[Any] | None, Any, str], None]], None],
    problem: Callable[[AuphonicChoices, str], str],
    source_chapters: tuple[tuple[float, str], ...] = (),
) -> tuple[AuphonicChoices, str, bool, str] | None:
    """``(choices, token, remember, account)``, or ``None`` when cancelled."""
    dialog = AuphonicDialog(
        host.frame,
        files,
        skipped=skipped,
        initial=initial,
        token=token,
        check=check,
        announce=lambda text: host._announce(text),
        problem=problem,
        refuse=lambda text: host._show_message_box(text, PROCESS_TITLE),
        show_modal=host._show_modal_dialog,
        source_chapters=source_chapters,
    )
    try:
        if (
            host._show_modal_dialog(dialog, PROCESS_TITLE) != wx.ID_OK
        ):  # dialog_button_contract: exempt
            return None
        return dialog.choices(), dialog.token(), dialog.remember_token(), dialog.account()
    finally:
        dialog.Destroy()


class AuphonicConfirmDialog(wx.Dialog):
    """The one confirmation before anything is uploaded."""

    def __init__(self, parent: Any, text: str) -> None:
        super().__init__(
            parent,
            title=CONFIRM_TITLE,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            name="converter.auphonic_confirm",
        )
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(wx.StaticText(self, label="&What will happen:"), 0, wx.LEFT | wx.TOP, 8)
        self._body = wx.TextCtrl(
            self, value=text, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2, size=(560, 300)
        )
        set_accessible_name(self._body, "What will happen")
        self._body.SetHelpText(
            "Everything this submission does, read-only: the service, every file sent "
            "and every file left out, the preset and processing, and where the results "
            "are saved. Nothing has been uploaded yet."
        )
        root.Add(self._body, 1, wx.EXPAND | wx.ALL, 8)
        buttons = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        root.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)
        apply_modal_ids(
            self,
            affirmative_id=wx.ID_OK,
            affirmative_label="Upload and Process",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Cancel",
        )
        for button_id, help_text in (
            (wx.ID_OK, "Uploads the files to Auphonic and starts processing them."),
            (wx.ID_CANCEL, "Sends nothing and goes back to the queue."),
        ):
            button = self.FindWindow(button_id)
            if button is not None:
                button.SetHelpText(help_text)
        self.SetSizerAndFit(root)
        self._body.SetFocus()


def confirm(host: Any, text: str) -> bool:
    """True only when the person chose Upload and Process."""
    dialog = AuphonicConfirmDialog(host.frame, text)
    try:
        return (
            host._show_modal_dialog(dialog, CONFIRM_TITLE) == wx.ID_OK
        )  # dialog_button_contract: exempt
    finally:
        dialog.Destroy()


class AuphonicWaitingDialog(wx.Dialog):
    """Pending productions, read locally; Resume contacts Auphonic, Dismiss forgets one."""

    def __init__(
        self,
        parent: Any,
        records: list[PendingProduction],
        *,
        dismiss: Callable[[PendingProduction], None],
    ) -> None:
        super().__init__(
            parent,
            title=WAITING_TITLE,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            name="converter.auphonic_waiting",
        )
        self._records = list(records)
        self._dismiss = dismiss
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(wx.StaticText(self, label="&Productions not fetched yet:"), 0, wx.ALL, 8)
        self._list = wx.ListBox(self, size=(560, 140))
        set_accessible_name(self._list, "Productions not fetched yet")
        self._list.SetHelpText(
            "Productions Auphonic accepted whose results have not been saved yet, "
            "remembered on this computer. Nothing has contacted Auphonic to make this list."
        )
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        resume = wx.Button(self, wx.ID_OK, label="Resume")
        resume.SetHelpText(
            "Contacts Auphonic for every production listed, waits for any still "
            "processing, and saves the results where each one was going."
        )
        self._dismiss_btn = wx.Button(self, label="&Dismiss")
        self._dismiss_btn.SetHelpText(
            "Forgets the highlighted production on this computer. It stays in your "
            "Auphonic account, and nothing is deleted there."
        )
        close = wx.Button(self, wx.ID_CANCEL, label="Close")
        close.SetHelpText("Closes this window; the list is kept for next time.")
        for button in (resume, self._dismiss_btn, close):
            row.Add(button, 0, wx.RIGHT, 6)
        root.Add(row, 0, wx.ALL, 8)
        self._dismiss_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dismiss_selected())
        bind_close_button(self, close, modeless=False)
        apply_modal_ids(
            self,
            affirmative_id=wx.ID_OK,
            affirmative_label="Resume",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Close",
        )
        self.SetSizerAndFit(root)
        self._reload()
        self._list.SetFocus()

    def _reload(self) -> None:
        self._list.Set([record.describe() for record in self._records])
        if self._records:
            self._list.SetSelection(0)
        ok = self.FindWindow(wx.ID_OK)
        if ok is not None:
            ok.Enable(bool(self._records))
        self._dismiss_btn.Enable(bool(self._records))

    def records(self) -> list[PendingProduction]:
        return list(self._records)

    def dismiss_selected(self) -> None:
        index = self._list.GetSelection()
        if index == wx.NOT_FOUND or not 0 <= index < len(self._records):
            return
        record = self._records.pop(index)
        self._dismiss(record)
        self._reload()
        if self._records:
            self._list.SetSelection(min(index, len(self._records) - 1))
        self._list.SetFocus()


def ask_resume(
    host: Any, records: list[PendingProduction], *, dismiss: Callable[[PendingProduction], None]
) -> list[PendingProduction] | None:
    """The records to resume, or ``None`` when closed."""
    dialog = AuphonicWaitingDialog(host.frame, records, dismiss=dismiss)
    try:
        if (
            host._show_modal_dialog(dialog, WAITING_TITLE) != wx.ID_OK
        ):  # dialog_button_contract: exempt
            return None
        return dialog.records()
    finally:
        dialog.Destroy()
