"""The WordPress windows, shared by QUILL and QUILL Lite (wordpress.md 4 to 9).

Every window here is an ordinary dialog of standard controls -- edit fields,
lists, combo boxes, check boxes and buttons -- so a screen reader meets nothing
it has not met a thousand times. Nothing is dragged, nothing floats, and every
control carries its own F1 help at the line that builds it.

None of these windows touches the network. Each one either returns what the
person chose (the ``ask_*`` functions) or calls back into the commands for an
action (the windows with several buttons), and the commands do the sending on
a background task. That keeps every window testable without a site and keeps
the UI thread free while a slow host answers.

*show_modal* is the host's own modal runner -- ``MainFrame._show_modal_dialog``
in QUILL, ``dialog_contract.show_modal_dialog`` in QUILL Lite -- so the dialog
contract and the dialog inventory see these the way they see every other
window.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

import wx

from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.dpi import dip_size
from quill.ui.spoken_name import set_spoken_name

ShowModal = Callable[[Any, str], int]

# a11y: needs manual verification -- screen-reader/braille announcements,
# keyboard focus order, high contrast, and layout at increased Windows scaling.


def labelled_row(sizer: wx.Sizer, parent: wx.Window, label: str, control: wx.Window) -> None:
    """Lay out *label* above *control*, and make *label* the control's spoken name.

    The control is built before its label here, so on its own the label would
    sit after it in z-order, where Windows would read it as the *next*
    control's name (GATE-CTLLABEL). Moving the label in front of the control
    puts the z-order right, and ``set_spoken_name`` names it outright, so the
    name is right even where a screen reader ignores z-order.
    """
    text = wx.StaticText(parent, label=label)
    text.MoveBeforeInTabOrder(control)
    set_spoken_name(control, label)
    sizer.Add(text, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
    sizer.Add(control, 0, wx.EXPAND | wx.ALL, 8)


def _buttons(dialog: wx.Dialog, ok_label: str = "OK") -> wx.Sizer:
    # OK and Cancel carry no access key: Enter and Escape already serve them
    # (GATE-14), and every letter they give up is free for the fields.
    sizer = wx.StdDialogButtonSizer()
    ok = wx.Button(dialog, wx.ID_OK, ok_label)
    ok.SetHelpText("Accept and close this window. Enter does the same.")
    ok.SetDefault()
    cancel = wx.Button(dialog, wx.ID_CANCEL, "Cancel")
    cancel.SetHelpText("Close this window without changing anything. Escape does the same.")
    sizer.AddButton(ok)
    sizer.AddButton(cancel)
    sizer.Realize()
    return sizer


# --------------------------------------------------------------------------- #
# Connect a site (4.1, 4.2, 4.3)


@dataclass
class ConnectAnswer:
    kind: str  # "self_hosted" or "wpcom"
    site_url: str
    username: str
    password: str = field(repr=False, default="")
    name: str = ""
    use_browser: bool = False


class ConnectSiteDialog(wx.Dialog):
    """Three fields, or a browser sign-in. Connect verifies before it saves."""

    def __init__(
        self, parent: wx.Window, *, answer: ConnectAnswer | None = None, error: str = ""
    ) -> None:
        super().__init__(
            parent,
            title="Connect a WordPress Site",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.SetHelpText(
            "Connect QUILL to a WordPress site so you can write, open and publish its pages and "
            "posts. "
            "You can connect as many sites as you like."
        )
        self.answer: ConnectAnswer | None = None
        self._use_browser = False
        sizer = wx.BoxSizer(wx.VERTICAL)
        if error:
            self.error = wx.TextCtrl(
                self, value=error, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_NO_VSCROLL
            )
            self.error.SetHelpText("Why the last attempt to connect did not work, and what to try.")
            labelled_row(sizer, self, "&Problem:", self.error)
        self.kind = wx.Choice(
            self, choices=["My own WordPress site (self-hosted)", "A WordPress.com site"]
        )
        self.kind.SetHelpText(
            "Self-hosted means the site runs on its own web address and hosting. Choose "
            "WordPress.com "
            "for a site hosted by WordPress.com; you will sign in with your browser."
        )
        self.kind.SetSelection(1 if answer and answer.kind == "wpcom" else 0)
        labelled_row(sizer, self, "&Kind of site:", self.kind)
        self.site_url = wx.TextCtrl(self, value=answer.site_url if answer else "")
        self.site_url.SetHelpText(
            "The site's web address, for example https://example.org. QUILL only connects over "
            "HTTPS, "
            "so your password is never sent in the clear."
        )
        labelled_row(sizer, self, "Site &address:", self.site_url)
        self.username = wx.TextCtrl(self, value=answer.username if answer else "")
        self.username.SetHelpText("The username or email you sign in to WordPress with.")
        labelled_row(sizer, self, "&Username:", self.username)
        self.password = wx.TextCtrl(self, style=wx.TE_PASSWORD)
        self.password.SetHelpText(
            "An application password: a separate password WordPress makes for one app. It is not "
            "the "
            "password you sign in to the site with. Press Get Password with My Browser and QUILL "
            "fetches one for you; or make one in your WordPress profile and paste it here."
        )
        labelled_row(sizer, self, "Application &password:", self.password)
        self.name = wx.TextCtrl(self, value=answer.name if answer else "")
        self.name.SetHelpText(
            "What QUILL calls this site in lists and confirmations. Leave it empty to use the "
            "site's own title."
        )
        labelled_row(sizer, self, "&Name for this site (optional):", self.name)
        self.browser = wx.Button(self, label="Get Password with My &Browser")
        self.browser.SetHelpText(
            "Opens the site's own Authorize Application page in your browser. Approve QUILL there"
            " and "
            "the password comes back to QUILL by itself; on an older site, WordPress shows it to "
            "you to "
            "copy and paste here. For WordPress.com this is how you sign in."
        )
        self.browser.Bind(wx.EVT_BUTTON, self._on_browser)
        sizer.Add(self.browser, 0, wx.ALL, 8)
        sizer.Add(_buttons(self, "Connect"), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        self.SetMinSize(dip_size(self, 460, -1))
        apply_modal_ids(self)
        self.Bind(wx.EVT_BUTTON, self._on_ok, id=wx.ID_OK)
        self.kind.Bind(wx.EVT_CHOICE, lambda _e: self._sync_kind())
        self._sync_kind()

    def _sync_kind(self) -> None:
        wpcom = self.kind.GetSelection() == 1
        self.username.Enable(not wpcom)
        self.password.Enable(not wpcom)

    def _collect(self) -> ConnectAnswer:
        return ConnectAnswer(
            kind="wpcom" if self.kind.GetSelection() == 1 else "self_hosted",
            site_url=self.site_url.GetValue().strip(),
            username=self.username.GetValue().strip(),
            password=self.password.GetValue().strip(),
            name=self.name.GetValue().strip(),
            use_browser=self._use_browser,
        )

    def _on_browser(self, _event: object) -> None:
        if not self.site_url.GetValue().strip() and self.kind.GetSelection() == 0:
            self.site_url.SetFocus()
            wx.Bell()
            return
        self._use_browser = True
        self.answer = self._collect()
        self.EndModal(wx.ID_OK)

    def _on_ok(self, event: wx.CommandEvent) -> None:
        answer = self._collect()
        if not answer.site_url and answer.kind == "self_hosted":
            self.site_url.SetFocus()
            wx.Bell()
            return
        self.answer = answer
        event.Skip()


def ask_connect(
    parent: wx.Window,
    show_modal: ShowModal,
    *,
    answer: ConnectAnswer | None = None,
    error: str = "",
) -> ConnectAnswer | None:
    dialog = ConnectSiteDialog(parent, answer=answer, error=error)
    try:
        if show_modal(dialog, "Connect a WordPress Site") != wx.ID_OK:
            return None
        return dialog.answer
    finally:
        dialog.Destroy()


class PastePasswordDialog(wx.Dialog):
    """Tier 2: WordPress shows the password; the person copies it here (4.2)."""

    def __init__(self, parent: wx.Window, *, offered: str = "") -> None:
        super().__init__(parent, title="Paste the Application Password")
        self.SetHelpText(
            "WordPress is showing a new application password in your browser. Copy it there, come"
            " back, "
            "and paste it here."
        )
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.password = wx.TextCtrl(self, value=offered, style=wx.TE_PASSWORD)
        self.password.SetHelpText(
            "Paste the application password WordPress showed you. It is 24 letters and numbers, "
            "often in "
            "groups of four."
        )
        labelled_row(sizer, self, "Application &password:", self.password)
        sizer.Add(_buttons(self, "Connect"), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        apply_modal_ids(self)


def ask_paste_password(
    parent: wx.Window, show_modal: ShowModal, *, offered: str = ""
) -> str | None:
    dialog = PastePasswordDialog(parent, offered=offered)
    try:
        if show_modal(dialog, "Paste the Application Password") != wx.ID_OK:
            return None
        return dialog.password.GetValue().strip() or None
    finally:
        dialog.Destroy()


# --------------------------------------------------------------------------- #
# Lists: choose one, and windows of rows with actions


class ChooseDialog(wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        *,
        title: str,
        prompt: str,
        rows: Sequence[str],
        initial: int,
        help_text: str,
    ) -> None:
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.SetHelpText(help_text)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.rows = wx.ListBox(self, choices=list(rows), style=wx.LB_SINGLE)
        self.rows.SetHelpText(help_text + " Press Enter to choose the selected one.")
        self.rows.SetMinSize(dip_size(self, 420, 220))
        if rows:
            self.rows.SetSelection(max(0, min(initial, len(rows) - 1)))
        self.rows.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self.EndModal(wx.ID_OK))
        labelled_row(sizer, self, prompt, self.rows)
        sizer.Add(_buttons(self), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        apply_modal_ids(self)


def ask_choice(
    parent: wx.Window,
    show_modal: ShowModal,
    *,
    title: str,
    prompt: str,
    rows: Sequence[str],
    initial: int = 0,
    help_text: str,
) -> int | None:
    dialog = ChooseDialog(
        parent, title=title, prompt=prompt, rows=rows, initial=initial, help_text=help_text
    )
    try:
        if show_modal(dialog, title) != wx.ID_OK:
            return None
        index = dialog.rows.GetSelection()
        return None if index == wx.NOT_FOUND else index
    finally:
        dialog.Destroy()


@dataclass(frozen=True)
class Action:
    """A button in a list window: its label (with access key), help, and what it runs.

    *run* receives the selected row's index (or ``None`` when there are no
    rows) and returns the new rows to show, or ``None`` to leave them; it may
    also close the window by returning ``CLOSE``.
    """

    label: str
    help: str
    run: Callable[[int | None], object]
    needs_row: bool = True


CLOSE = object()


@dataclass(frozen=True)
class Rows:
    """An action's answer that also moves the selection: a row moved down follows the row."""

    rows: Sequence[str]
    select: int | None = None


class ListWindow(wx.Dialog):
    """A list, a details box, and action buttons: Sites, Media Library, Comments...

    One shape for every "manage" window, so learning one teaches them all.
    """

    def __init__(
        self,
        parent: wx.Window,
        *,
        title: str,
        purpose: str,
        list_label: str,
        list_help: str,
        rows: Sequence[str],
        actions: Sequence[Action],
        details: Callable[[int], str] | None = None,
        filter_label: str = "",
        filter_help: str = "",
        on_filter: Callable[[str], Sequence[str] | None] | None = None,
        on_enter: Callable[[int | None], object] | None = None,
    ) -> None:
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        # Enter or a double-click on a row runs the window's main action (Open,
        # Play...), as Enter does in Explorer; the buttons stay for the rest.
        self._enter = Action("", "", on_enter) if on_enter is not None else None
        self.SetHelpText(purpose)
        self._details = details
        self._on_filter = on_filter
        self._actions = list(actions)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.search: wx.TextCtrl | None = None
        if on_filter is not None:
            self.search = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
            self.search.SetHelpText(filter_help or "Type words and press Enter to narrow the list.")
            self.search.Bind(wx.EVT_TEXT_ENTER, self._on_search)
            labelled_row(sizer, self, filter_label or "&Search:", self.search)
        self.rows = wx.ListBox(self, choices=list(rows), style=wx.LB_SINGLE)
        self.rows.SetHelpText(list_help)
        self.rows.SetMinSize(dip_size(self, 520, 260))
        self.rows.Bind(wx.EVT_LISTBOX, lambda _e: self._show_details())
        self.rows.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self._run_enter())
        self.rows.Bind(wx.EVT_KEY_DOWN, self._on_row_key)
        labelled_row(sizer, self, list_label, self.rows)
        self.info: wx.TextCtrl | None = None
        if details is not None:
            self.info = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
            self.info.SetHelpText(
                "More about the selected row. Read it line by line; it never changes anything."
            )
            self.info.SetMinSize(dip_size(self, 520, 100))
            labelled_row(sizer, self, "&Details:", self.info)
        bar = wx.WrapSizer(wx.HORIZONTAL)
        self.buttons: list[wx.Button] = []
        for action in self._actions:
            button = wx.Button(self, label=action.label)
            button.SetHelpText(action.help)
            button.Bind(wx.EVT_BUTTON, lambda _e, a=action: self._run(a))
            bar.Add(button, 0, wx.ALL, 4)
            self.buttons.append(button)
        close = wx.Button(self, wx.ID_CANCEL, "Close")
        close.SetHelpText("Close this window. Escape does the same.")
        bar.Add(close, 0, wx.ALL, 4)
        sizer.Add(bar, 0, wx.EXPAND | wx.ALL, 4)
        self.SetSizerAndFit(sizer)
        apply_modal_ids(self)
        if rows:
            self.rows.SetSelection(0)
        self._show_details()
        self._sync_buttons()

    def set_rows(self, rows: Sequence[str], keep: int | None = None) -> None:
        self.rows.Set(list(rows))
        if rows:
            index = keep if keep is not None else 0
            self.rows.SetSelection(max(0, min(index, len(rows) - 1)))
        self._show_details()
        self._sync_buttons()

    def selected(self) -> int | None:
        index = self.rows.GetSelection()
        return None if index == wx.NOT_FOUND else index

    def _run(self, action: Action) -> None:
        index = self.selected()
        if action.needs_row and index is None:
            wx.Bell()
            return
        result = action.run(index)
        if result is CLOSE:
            self.EndModal(wx.ID_OK)
            return
        if isinstance(result, Rows):
            self.set_rows([str(r) for r in result.rows], keep=result.select)
        elif isinstance(result, (list, tuple)):
            self.set_rows([str(r) for r in result], keep=index)
        self.rows.SetFocus()

    def _run_enter(self) -> None:
        if self._enter is not None and self.selected() is not None:
            self._run(self._enter)

    def _on_row_key(self, event: wx.KeyEvent) -> None:
        if self._enter is not None and event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self._run_enter()
            return
        event.Skip()

    def _on_search(self, _event: object) -> None:
        if self._on_filter is None or self.search is None:
            return
        rows = self._on_filter(self.search.GetValue())
        if rows is not None:
            self.set_rows(rows)

    def _show_details(self) -> None:
        if self.info is None or self._details is None:
            return
        index = self.selected()
        self.info.SetValue(self._details(index) if index is not None else "")

    def _sync_buttons(self) -> None:
        has_rows = self.rows.GetCount() > 0
        for action, button in zip(self._actions, self.buttons, strict=True):
            button.Enable(has_rows or not action.needs_row)


def show_list_window(parent: wx.Window, show_modal: ShowModal, **kwargs: Any) -> ListWindow:
    """Build and run a :class:`ListWindow`; the caller destroys it when done."""
    window = ListWindow(parent, **kwargs)
    show_modal(window, str(kwargs.get("title", "")))
    return window


# --------------------------------------------------------------------------- #
# Read-only reports and simple text questions


class ReportDialog(wx.Dialog):
    def __init__(self, parent: wx.Window, *, title: str, text: str, help_text: str) -> None:
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.SetHelpText(help_text)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.text = wx.TextCtrl(
            self, value=text, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2
        )
        self.text.SetHelpText(help_text + " Read it line by line; copy any part with Ctrl+C.")
        self.text.SetMinSize(dip_size(self, 560, 320))
        labelled_row(sizer, self, "&Report:", self.text)
        bar = wx.BoxSizer(wx.HORIZONTAL)
        copy = wx.Button(self, label="Copy &All")
        copy.SetHelpText("Copy the whole report to the clipboard.")
        copy.Bind(wx.EVT_BUTTON, self._on_copy)
        bar.Add(copy, 0, wx.ALL, 4)
        close = wx.Button(self, wx.ID_CANCEL, "Close")
        close.SetHelpText("Close the report. Escape does the same.")
        bar.Add(close, 0, wx.ALL, 4)
        sizer.Add(bar, 0, wx.ALL, 4)
        self.SetSizerAndFit(sizer)
        apply_modal_ids(self)

    def _on_copy(self, _event: object) -> None:
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(self.text.GetValue()))
            finally:
                wx.TheClipboard.Close()


def show_report(
    parent: wx.Window, show_modal: ShowModal, *, title: str, text: str, help_text: str
) -> None:
    dialog = ReportDialog(parent, title=title, text=text, help_text=help_text)
    try:
        show_modal(dialog, title)
    finally:
        dialog.Destroy()


class TextQuestionDialog(wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        *,
        title: str,
        prompt: str,
        value: str,
        help_text: str,
        multiline: bool,
    ) -> None:
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.SetHelpText(help_text)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.value = wx.TextCtrl(self, value=value, style=wx.TE_MULTILINE if multiline else 0)
        self.value.SetHelpText(help_text)
        if multiline:
            self.value.SetMinSize(dip_size(self, 460, 140))
        labelled_row(sizer, self, prompt, self.value)
        sizer.Add(_buttons(self), 0, wx.EXPAND | wx.ALL, 8)
        self.SetSizerAndFit(sizer)
        apply_modal_ids(self)


def ask_text(
    parent: wx.Window,
    show_modal: ShowModal,
    *,
    title: str,
    prompt: str,
    value: str = "",
    help_text: str,
    multiline: bool = False,
) -> str | None:
    dialog = TextQuestionDialog(
        parent, title=title, prompt=prompt, value=value, help_text=help_text, multiline=multiline
    )
    try:
        if show_modal(dialog, title) != wx.ID_OK:
            return None
        return dialog.value.GetValue()
    finally:
        dialog.Destroy()


def confirm(
    parent: wx.Window, show_modal: ShowModal, *, title: str, message: str, yes_label: str
) -> bool:
    """A named confirmation: the sentence says the site and the item (4.4)."""
    dialog = wx.MessageDialog(
        parent, message, title, style=wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION
    )
    dialog.SetYesNoLabels(yes_label, "Cancel")
    try:
        return show_modal(dialog, title) == wx.ID_YES
    finally:
        dialog.Destroy()
