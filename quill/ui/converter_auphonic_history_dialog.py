"""Quill Converter's Auphonic Production History and Auphonic Account windows.

Post-MVP (``docs/planning/QUILL-Converter-Auphonic-Integration-PRD.md``,
section 14). Neither contacts Auphonic by opening.

**Auphonic Production History** lists every production Quill Converter has
sent, newest first, from a file on this computer: its title, its last known
status and when it was sent, with the whole record in a read-only details box.
**Refresh from Auphonic** reads the account's recent productions to bring the
statuses up to date (and adds ones sent from elsewhere); **Download Again**
(the default button) fetches a production's results once more, into its own
folder, never over an existing file; **Open Folder** opens where its results
went; **Remove from List** forgets it here only.

**Auphonic Account** says whether a token is stored (signed in) and, after
an explicit **Check Account**, who it belongs to, the credits left and the
plan. **Sign In** checks a typed token and stores it only when Auphonic
accepts it; **Sign Out** removes the stored token, after asking.

Access keys are unique within each window (GATE-14); the default button,
Close and Cancel carry none. Every control has its F1 sentence inline
(GATE-CONVERTER-HELP). Background answers arrive through the callbacks and
change only unfocused text, which is then spoken (GATE-12/13).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core.publish.auphonic_history import HistoryEntry
from quill.ui.accessible_names import set_accessible_name
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button

HISTORY_TITLE = "Auphonic Production History"
ACCOUNT_TITLE = "Auphonic Account"
_EMPTY = (
    "No productions yet. Productions you send with Process with Auphonic are listed "
    "here; Refresh from Auphonic adds the ones already in your account."
)


class AuphonicHistoryDialog(wx.Dialog):
    """Past productions; :meth:`selected` is the one Download Again fetches."""

    def __init__(
        self,
        parent: Any,
        entries: list[HistoryEntry],
        *,
        refresh: Callable[[Callable[[list[HistoryEntry] | None, str], None]], None],
        open_folder: Callable[[HistoryEntry], str],
        remove: Callable[[HistoryEntry], None],
        announce: Callable[[str], None],
    ) -> None:
        super().__init__(
            parent,
            title=HISTORY_TITLE,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            name="converter.auphonic_history",
        )
        self._entries = list(entries)
        self._refresh = refresh
        self._open_folder = open_folder
        self._remove = remove
        self._announce = announce
        self._refreshing = False
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(wx.StaticText(self, label="&Productions, newest first:"), 0, wx.ALL, 8)
        self._list = wx.ListBox(self, size=(600, 160))
        set_accessible_name(self._list, "Productions")
        self._list.SetHelpText(
            "Every production Quill Converter sent to Auphonic, newest first: its "
            "title, its last known status and when it was sent. The list is kept on "
            "this computer; nothing contacted Auphonic to show it."
        )
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        root.Add(wx.StaticText(self, label="D&etails:"), 0, wx.LEFT | wx.TOP, 8)
        self._details = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2, size=(600, 140)
        )
        set_accessible_name(self._details, "Details")
        self._details.SetHelpText(
            "Everything known about the highlighted production, one fact a line: its "
            "status, the files sent, the preset, the results folder, each file saved, "
            "the last outcome and its Auphonic id. Read-only."
        )
        root.Add(self._details, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self._refresh_btn = wx.Button(self, label="&Refresh from Auphonic")
        self._refresh_btn.SetHelpText(
            "Asks Auphonic for your account's recent productions and brings every "
            "status here up to date; productions sent from elsewhere are added. "
            "Nothing is uploaded and no credits are used."
        )
        download = wx.Button(self, wx.ID_OK, label="Download Again")
        download.SetHelpText(
            "Fetches the highlighted production's results from Auphonic again, into "
            "its results folder. A file already there is never replaced; the new one "
            "gets a number. If it is still processing, this waits for it."
        )
        self._folder_btn = wx.Button(self, label="&Open Folder")
        self._folder_btn.SetHelpText(
            "Opens the highlighted production's results folder in File Explorer."
        )
        self._remove_btn = wx.Button(self, label="Re&move from List")
        self._remove_btn.SetHelpText(
            "Forgets the highlighted production on this computer. It stays in your "
            "Auphonic account and its saved files stay where they are."
        )
        close = wx.Button(self, wx.ID_CANCEL, label="Close")
        close.SetHelpText("Closes this window; the history is kept for next time.")
        for button in (self._refresh_btn, download, self._folder_btn, self._remove_btn, close):
            row.Add(button, 0, wx.RIGHT, 6)
        root.Add(row, 0, wx.ALL, 8)
        bind_close_button(self, close, modeless=False)
        apply_modal_ids(
            self,
            affirmative_id=wx.ID_OK,
            affirmative_label="Download Again",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Close",
        )
        self.SetSizerAndFit(root)
        self._list.Bind(wx.EVT_LISTBOX, lambda _e: self._show_details())
        self._refresh_btn.Bind(wx.EVT_BUTTON, lambda _e: self.refresh())
        self._folder_btn.Bind(wx.EVT_BUTTON, lambda _e: self.open_folder())
        self._remove_btn.Bind(wx.EVT_BUTTON, lambda _e: self.remove_selected())
        self._reload()
        (self._list if self._entries else self._refresh_btn).SetFocus()

    # -- state -----------------------------------------------------------------------

    def _reload(self, keep: str = "") -> None:
        self._list.Set([entry.describe() for entry in self._entries])
        if self._entries:
            uuids = [entry.uuid for entry in self._entries]
            self._list.SetSelection(uuids.index(keep) if keep in uuids else 0)
        has = bool(self._entries)
        ok = self.FindWindow(wx.ID_OK)
        if ok is not None:
            ok.Enable(has)
        self._folder_btn.Enable(has)
        self._remove_btn.Enable(has)
        self._show_details()

    def _show_details(self) -> None:
        entry = self.selected()
        self._details.SetValue(entry.details() if entry is not None else _EMPTY)

    def selected(self) -> HistoryEntry | None:
        index = self._list.GetSelection()
        if index == wx.NOT_FOUND or not 0 <= index < len(self._entries):
            return None
        return self._entries[index]

    def entries(self) -> list[HistoryEntry]:
        return list(self._entries)

    # -- the buttons -------------------------------------------------------------------

    def refresh(self) -> None:
        """One explicit read of the account's productions; the host runs it off the UI thread."""
        if self._refreshing:
            self._announce("Still asking Auphonic.")
            return
        self._refreshing = True
        self._announce("Asking Auphonic for your recent productions...")
        self._refresh(self.refreshed)

    def refreshed(self, entries: list[HistoryEntry] | None, message: str) -> None:
        """The refresh's answer, on the UI thread (also called directly by tests)."""
        if not self:  # the window closed while Auphonic answered
            return
        self._refreshing = False
        if entries is not None:
            current = self.selected()
            self._entries = list(entries)
            self._reload(current.uuid if current is not None else "")
        self._announce(message)

    def open_folder(self) -> None:
        entry = self.selected()
        if entry is None:
            return
        problem = self._open_folder(entry)
        if problem:
            self._announce(problem)

    def remove_selected(self) -> None:
        entry = self.selected()
        if entry is None:
            return
        index = self._list.GetSelection()
        self._entries.remove(entry)
        self._remove(entry)
        self._reload()
        if self._entries:
            self._list.SetSelection(min(index, len(self._entries) - 1))
            self._show_details()
            self._list.SetFocus()
        else:
            self._refresh_btn.SetFocus()  # the disabled buttons would drop focus
        self._announce(
            f"Removed {entry.title} from the list. It is still in your Auphonic account."
        )


def ask_history(
    host: Any,
    entries: list[HistoryEntry],
    *,
    refresh: Callable[[Callable[[list[HistoryEntry] | None, str], None]], None],
    open_folder: Callable[[HistoryEntry], str],
    remove: Callable[[HistoryEntry], None],
) -> HistoryEntry | None:
    """The production to download again, or ``None`` when closed."""
    dialog = AuphonicHistoryDialog(
        host.frame,
        entries,
        refresh=refresh,
        open_folder=open_folder,
        remove=remove,
        announce=lambda text: host._announce(text),
    )
    try:
        if (
            host._show_modal_dialog(dialog, HISTORY_TITLE) != wx.ID_OK
        ):  # dialog_button_contract: exempt
            return None
        return dialog.selected()
    finally:
        dialog.Destroy()


class AuphonicAccountDialog(wx.Dialog):
    """Sign-in state, the account check, Sign In and Sign Out."""

    def __init__(
        self,
        parent: Any,
        *,
        stored_token: Callable[[], str],
        check: Callable[[str, Callable[[Any, str], None]], None],
        save: Callable[[str], None],
        forget: Callable[[], None],
        confirm_sign_out: Callable[[], bool],
        announce: Callable[[str], None],
    ) -> None:
        super().__init__(
            parent,
            title=ACCOUNT_TITLE,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            name="converter.auphonic_account",
        )
        self._stored_token = stored_token
        self._check = check
        self._save = save
        self._forget = forget
        self._confirm_sign_out = confirm_sign_out
        self._announce = announce
        self._busy = False
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(wx.StaticText(self, label="Account &details:"), 0, wx.ALL, 8)
        self._details = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2, size=(520, 150)
        )
        set_accessible_name(self._details, "Account details")
        self._details.SetHelpText(
            "Whether you are signed in, and after Check Account, the account name, "
            "the credits left in hours, split into one-time and recurring credits "
            "when Auphonic says, and the plan. Read-only."
        )
        root.Add(self._details, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self._check_btn = wx.Button(self, label="&Check Account")
        self._check_btn.SetHelpText(
            "Asks Auphonic, with the stored token, who the account is, how many "
            "credits are left and which plan it has. Nothing is uploaded."
        )
        root.Add(self._check_btn, 0, wx.ALL, 8)
        root.Add(wx.StaticText(self, label="API to&ken to sign in with:"), 0, wx.LEFT, 8)
        self._token = wx.TextCtrl(self, style=wx.TE_PASSWORD)
        set_accessible_name(self._token, "API token to sign in with")
        self._token.SetHelpText(
            "Your Auphonic API token, from the account settings page on auphonic.com. "
            "Sign In checks it with Auphonic before storing it in Windows Credential "
            "Manager, where the Audio Studio and QUILL find it too."
        )
        root.Add(self._token, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self._sign_in = wx.Button(self, label="&Sign In")
        self._sign_in.SetHelpText(
            "Checks the token you typed with Auphonic and, only if Auphonic accepts "
            "it, stores it on this computer in place of any token stored before."
        )
        self._sign_out = wx.Button(self, label="Sign &Out")
        self._sign_out.SetHelpText(
            "Removes the stored Auphonic token from this computer, after asking. "
            "The Audio Studio uses the same token, so it is signed out too. Your "
            "Auphonic account and its productions are not touched."
        )
        close = wx.Button(self, wx.ID_CANCEL, label="Close")
        close.SetHelpText("Closes this window.")
        for button in (self._sign_in, self._sign_out, close):
            row.Add(button, 0, wx.RIGHT, 6)
        root.Add(row, 0, wx.ALL, 8)
        bind_close_button(self, close, modeless=False)
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL, cancel_label="Close")
        self.SetSizerAndFit(root)
        self._check_btn.Bind(wx.EVT_BUTTON, lambda _e: self.check_account())
        self._sign_in.Bind(wx.EVT_BUTTON, lambda _e: self.sign_in())
        self._sign_out.Bind(wx.EVT_BUTTON, lambda _e: self.sign_out())
        self._details.SetValue(self._state() + "\nNot checked yet.")
        (self._check_btn if self._stored_token() else self._token).SetFocus()

    def _state(self) -> str:
        if self._stored_token():
            return "Signed in: an Auphonic token is stored on this computer."
        return "Not signed in: no Auphonic token is stored on this computer."

    def _show(self, text: str, *, speak: str = "") -> None:
        self._details.SetValue(text)
        self._announce(speak or text.splitlines()[0])

    def check_account(self) -> None:
        token = self._stored_token()
        if not token:
            self._show(
                self._state() + "\nType your API token and choose Sign In first.",
                speak="Not signed in. Type your API token and choose Sign In first.",
            )
            self._token.SetFocus()
            return
        self._ask(token, store=False)

    def sign_in(self) -> None:
        token = self._token.GetValue().strip()
        if not token:
            self._show(self._state() + "\nType or paste your Auphonic API token first.",
                       speak="Type or paste your Auphonic API token first.")  # fmt: skip
            self._token.SetFocus()
            return
        self._ask(token, store=True)

    def _ask(self, token: str, *, store: bool) -> None:
        if self._busy:
            self._announce("Still asking Auphonic.")
            return
        # Not disabled while it works: disabling the focused button would drop
        # focus out of the window for a screen-reader user.
        self._busy = True
        self._announce("Asking Auphonic...")
        self._check(token, lambda info, error: self.answered(info, error, token, store))

    def answered(self, info: Any, error: str, token: str = "", store: bool = False) -> None:
        """Auphonic's answer, on the UI thread (also called directly by tests)."""
        if not self:  # the window closed while Auphonic answered
            return
        self._busy = False
        if error or info is None:
            what = "Sign-in failed; nothing was stored" if store else "The account check failed"
            self._show(f"{what}: {error or 'no answer'}\n{self._state()}")
            return
        lines = info.lines()
        if store:
            self._save(token)
            self._token.SetValue("")
            heading = "Signed in. The token is stored on this computer."
        else:
            heading = self._state()
        self._show("\n".join([heading, *lines]), speak=f"{heading} {lines[0]}. {lines[-1]}")

    def sign_out(self) -> None:
        if not self._stored_token():
            self._show(self._state(), speak="Not signed in; there is no token to remove.")
            return
        if not self._confirm_sign_out():
            return
        self._forget()
        self._show(
            "Signed out. The Auphonic token was removed from this computer; the Audio "
            "Studio is signed out too. Your Auphonic account is not touched.\n" + self._state()
        )
        self._token.SetFocus()


def show_account(
    host: Any,
    *,
    stored_token: Callable[[], str],
    check: Callable[[str, Callable[[Any, str], None]], None],
    save: Callable[[str], None],
    forget: Callable[[], None],
) -> None:
    """Show the account window until it is closed."""

    def confirm() -> bool:
        answer = host._show_message_box(
            "Remove the stored Auphonic token from this computer? The Audio Studio "
            "uses the same token. You can sign in again with the token from your "
            "Auphonic account settings.",
            ACCOUNT_TITLE,
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        )
        return answer == wx.YES

    dialog = AuphonicAccountDialog(
        host.frame,
        stored_token=stored_token,
        check=check,
        save=save,
        forget=forget,
        confirm_sign_out=confirm,
        announce=lambda text: host._announce(text),
    )
    try:
        host._show_modal_dialog(dialog, ACCOUNT_TITLE)  # dialog_button_contract: exempt
    finally:
        dialog.Destroy()
