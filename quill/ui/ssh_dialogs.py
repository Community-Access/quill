"""Dialogs for edit-over-SSH (issue #139): quick connect, site manager, browser.

All native wx surfaces (no WebView) so the screen reader stays in focus mode.
The dialogs only collect input and return plain data; the connection, transfer,
and open/save side effects live in ``MainFrame`` (``SshEditingMixin``).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from quill.core.ssh.sites import (
    AUTH_AGENT,
    AUTH_KEY,
    AUTH_PASSWORD,
    DEFAULT_PORT,
    SiteConfig,
    delete_site,
    load_sites,
    upsert_site,
)
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

_AUTH_LABELS = [
    ("Password", AUTH_PASSWORD),
    ("Private key file", AUTH_KEY),
    ("SSH agent", AUTH_AGENT),
]


@dataclass(slots=True)
class ConnectionRequest:
    """Everything needed to open a connection. ``password`` is held in memory only."""

    host: str
    port: int
    username: str
    auth: str
    password: str
    key_path: str
    default_dir: str


def _auth_index(auth: str) -> int:
    return next((i for i, (_label, value) in enumerate(_AUTH_LABELS) if value == auth), 0)


class QuickConnectDialog:
    """One-time connection (host, port, user, auth) without saving a site."""

    def __init__(self, parent: object, *, site: SiteConfig | None = None) -> None:
        import wx

        self._wx = wx
        self.request: ConnectionRequest | None = None
        site = site or SiteConfig(name="", host="", port=DEFAULT_PORT)

        self.dialog = wx.Dialog(
            parent, title="Connect to SSH Server", style=wx.DEFAULT_DIALOG_STYLE
        )
        grid = wx.FlexGridSizer(0, 2, 8, 8)
        grid.AddGrowableCol(1, 1)

        def row(label_text: str, make_ctrl) -> object:
            grid.Add(wx.StaticText(self.dialog, label=label_text), 0, wx.ALIGN_CENTER_VERTICAL)
            ctrl = make_ctrl()
            grid.Add(ctrl, 1, wx.EXPAND)
            return ctrl

        self.host = row("Host or IP address", lambda: wx.TextCtrl(self.dialog, value=site.host))
        self.host.SetName("Host or IP address")
        self.port = row(
            "Port",
            lambda: wx.SpinCtrl(self.dialog, min=1, max=65535, initial=site.port or DEFAULT_PORT),
        )
        self.port.SetName("Port")
        self.username = row("Username", lambda: wx.TextCtrl(self.dialog, value=site.username))
        self.username.SetName("Username")
        self.auth = row(
            "Authentication",
            lambda: wx.Choice(self.dialog, choices=[lbl for lbl, _v in _AUTH_LABELS]),
        )
        self.auth.SetName("Authentication")
        self.auth.SetSelection(_auth_index(site.auth))
        self.password = row(
            "Password / key passphrase",
            lambda: wx.TextCtrl(self.dialog, style=wx.TE_PASSWORD),
        )
        self.password.SetName("Password or key passphrase")
        key_picker = wx.BoxSizer(wx.HORIZONTAL)
        self.key_path = wx.TextCtrl(self.dialog, value=site.key_path)
        self.key_path.SetName("Private key file path")
        self.key_path.SetToolTip(
            "Path to your SSH private key file on disk. OpenSSH, PEM, and PuTTY "
            "(.ppk) formats are supported. The file itself is not opened until "
            "you click Connect."
        )
        key_picker.Add(self.key_path, 1, wx.ALIGN_CENTER_VERTICAL)
        self.key_browse = wx.Button(self.dialog, label="Browse...")
        self.key_browse.SetName("Browse for private key file")
        self.key_browse.SetToolTip("Pick the SSH private key file on disk")
        self.key_browse.Bind(wx.EVT_BUTTON, self._on_browse_key)
        key_picker.Add(self.key_browse, 0, wx.LEFT, 6)
        grid.Add(
            wx.StaticText(self.dialog, label="Private key file (path on disk)"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        grid.Add(key_picker, 1, wx.EXPAND)
        self.default_dir = row(
            "Start directory",
            lambda: wx.TextCtrl(self.dialog, value=site.default_dir or "/"),
        )
        self.default_dir.SetName("Start directory")

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(grid, 1, wx.EXPAND | wx.ALL, 12)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer(1)
        buttons.Add(wx.Button(self.dialog, wx.ID_OK, label="Connect"), 0, wx.RIGHT, 8)
        buttons.Add(wx.Button(self.dialog, wx.ID_CANCEL, label="Cancel"), 0)
        root.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        self.dialog.SetSizerAndFit(root)

    def _on_browse_key(self, _event: object) -> None:
        wx = self._wx
        style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        with wx.FileDialog(
            self.dialog,
            "Choose SSH private key file",
            wildcard=(
                "All private keys (*.ppk;*.pem;*.key;id_*)|*.ppk;*.pem;*.key;id_*|"
                "PuTTY (*.ppk)|*.ppk|"
                "OpenSSH / PEM (*.pem;*.key;id_*)|*.pem;*.key;id_*|"
                "All files (*.*)|*.*"
            ),
            style=style,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.key_path.SetValue(dialog.GetPath())

    def show(self) -> ConnectionRequest | None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            if show_modal_dialog(self.dialog, "Connect to SSH Server") != wx.ID_OK:
                return None
            host = self.host.GetValue().strip()
            if not host:
                return None
            self.request = ConnectionRequest(
                host=host,
                port=int(self.port.GetValue()),
                username=self.username.GetValue().strip(),
                auth=_AUTH_LABELS[self.auth.GetSelection()][1],
                password=self.password.GetValue(),
                key_path=self.key_path.GetValue().strip(),
                default_dir=self.default_dir.GetValue().strip() or "/",
            )
            return self.request
        finally:
            self.dialog.Destroy()


class SiteEditDialog:
    """Add or edit a saved site (no password is stored)."""

    def __init__(self, parent: object, *, site: SiteConfig | None = None) -> None:
        import wx

        self._wx = wx
        self.site: SiteConfig | None = None
        site = site or SiteConfig(name="", host="", port=DEFAULT_PORT)

        self.dialog = wx.Dialog(parent, title="Site", style=wx.DEFAULT_DIALOG_STYLE)
        grid = wx.FlexGridSizer(0, 2, 8, 8)
        grid.AddGrowableCol(1, 1)

        def row(label_text: str, make_ctrl) -> object:
            grid.Add(wx.StaticText(self.dialog, label=label_text), 0, wx.ALIGN_CENTER_VERTICAL)
            ctrl = make_ctrl()
            grid.Add(ctrl, 1, wx.EXPAND)
            return ctrl

        self.name = row("Friendly name", lambda: wx.TextCtrl(self.dialog, value=site.name))
        self.name.SetName("Friendly name")
        self.host = row("Host or IP address", lambda: wx.TextCtrl(self.dialog, value=site.host))
        self.host.SetName("Host or IP address")
        self.port = row(
            "Port",
            lambda: wx.SpinCtrl(self.dialog, min=1, max=65535, initial=site.port or DEFAULT_PORT),
        )
        self.port.SetName("Port")
        self.username = row("Username", lambda: wx.TextCtrl(self.dialog, value=site.username))
        self.username.SetName("Username")
        self.auth = row(
            "Authentication",
            lambda: wx.Choice(self.dialog, choices=[lbl for lbl, _v in _AUTH_LABELS]),
        )
        self.auth.SetName("Authentication")
        self.auth.SetSelection(_auth_index(site.auth))
        self.key_path_picker = wx.BoxSizer(wx.HORIZONTAL)
        self.key_path = wx.TextCtrl(self.dialog, value=site.key_path)
        self.key_path.SetName("Private key file path")
        self.key_path.SetToolTip(
            "Path to your SSH private key file on disk. OpenSSH, PEM, and PuTTY "
            "(.ppk) formats are supported. The file itself is not opened until "
            "you click Connect from the site manager."
        )
        self.key_path_picker.Add(self.key_path, 1, wx.ALIGN_CENTER_VERTICAL)
        self.key_browse = wx.Button(self.dialog, label="Browse...")
        self.key_browse.SetName("Browse for private key file")
        self.key_browse.SetToolTip("Pick the SSH private key file on disk")
        self.key_browse.Bind(wx.EVT_BUTTON, self._on_browse_key)
        self.key_path_picker.Add(self.key_browse, 0, wx.LEFT, 6)
        grid.Add(
            wx.StaticText(self.dialog, label="Private key file (path on disk)"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        grid.Add(self.key_path_picker, 1, wx.EXPAND)
        self.default_dir = row(
            "Default directory", lambda: wx.TextCtrl(self.dialog, value=site.default_dir)
        )
        self.default_dir.SetName("Default directory")

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                self.dialog,
                label="The password is never saved; you are asked for it when connecting.",
            ),
            0,
            wx.ALL,
            12,
        )
        root.Add(grid, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer(1)
        buttons.Add(wx.Button(self.dialog, wx.ID_OK, label="Save"), 0, wx.RIGHT, 8)
        buttons.Add(wx.Button(self.dialog, wx.ID_CANCEL, label="Cancel"), 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 12)
        self.dialog.SetSizerAndFit(root)

    def _on_browse_key(self, _event: object) -> None:
        wx = self._wx
        style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        with wx.FileDialog(
            self.dialog,
            "Choose SSH private key file",
            wildcard=(
                "All private keys (*.ppk;*.pem;*.key;id_*)|*.ppk;*.pem;*.key;id_*|"
                "PuTTY (*.ppk)|*.ppk|"
                "OpenSSH / PEM (*.pem;*.key;id_*)|*.pem;*.key;id_*|"
                "All files (*.*)|*.*"
            ),
            style=style,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.key_path.SetValue(dialog.GetPath())

    def show(self) -> SiteConfig | None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            if show_modal_dialog(self.dialog, "Site") != wx.ID_OK:
                return None
            name = self.name.GetValue().strip()
            host = self.host.GetValue().strip()
            if not name or not host:
                return None
            self.site = SiteConfig(
                name=name,
                host=host,
                port=int(self.port.GetValue()),
                username=self.username.GetValue().strip(),
                auth=_AUTH_LABELS[self.auth.GetSelection()][1],
                key_path=self.key_path.GetValue().strip(),
                default_dir=self.default_dir.GetValue().strip(),
            )
            return self.site
        finally:
            self.dialog.Destroy()


class SiteManagerDialog:
    """List, add, edit, delete saved sites; return one to connect to."""

    def __init__(self, parent: object) -> None:
        import wx

        self._wx = wx
        self._parent = parent
        self.chosen: SiteConfig | None = None
        self._sites: list[SiteConfig] = load_sites()

        self.dialog = wx.Dialog(
            parent, title="SSH Site Manager", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetSize((520, 460))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(self.dialog, label="Saved sites"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 12
        )
        self.listbox = wx.ListBox(self.dialog, choices=[s.name for s in self._sites])
        self.listbox.SetName("Saved sites")
        if self._sites:
            self.listbox.SetSelection(0)
        root.Add(self.listbox, 1, wx.EXPAND | wx.ALL, 12)

        actions = wx.BoxSizer(wx.HORIZONTAL)
        self.new_button = wx.Button(self.dialog, label="New")
        self.edit_button = wx.Button(self.dialog, label="Edit")
        self.delete_button = wx.Button(self.dialog, label="Delete")
        for button in (self.new_button, self.edit_button, self.delete_button):
            actions.Add(button, 0, wx.RIGHT, 8)
        root.Add(actions, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer(1)
        buttons.Add(wx.Button(self.dialog, wx.ID_OK, label="Connect"), 0, wx.RIGHT, 8)
        buttons.Add(wx.Button(self.dialog, wx.ID_CANCEL, label="Close"), 0)
        root.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        self.dialog.SetSizer(root)

        self.new_button.Bind(wx.EVT_BUTTON, self._on_new)
        self.edit_button.Bind(wx.EVT_BUTTON, self._on_edit)
        self.delete_button.Bind(wx.EVT_BUTTON, self._on_delete)

    def _refresh(self, select_name: str | None = None) -> None:
        self._sites = load_sites()
        self.listbox.Set([s.name for s in self._sites])
        if not self._sites:
            return
        index = next(
            (i for i, s in enumerate(self._sites) if s.name == select_name),
            0,
        )
        self.listbox.SetSelection(index)

    def _selected_site(self) -> SiteConfig | None:
        index = self.listbox.GetSelection()
        if index == self._wx.NOT_FOUND or index < 0 or index >= len(self._sites):
            return None
        return self._sites[index]

    def _on_new(self, _event: object) -> None:
        site = SiteEditDialog(self.dialog).show()
        if site is not None:
            upsert_site(site)
            self._refresh(site.name)

    def _on_edit(self, _event: object) -> None:
        current = self._selected_site()
        if current is None:
            return
        site = SiteEditDialog(self.dialog, site=current).show()
        if site is not None:
            upsert_site(site)
            self._refresh(site.name)

    def _on_delete(self, _event: object) -> None:
        wx = self._wx
        current = self._selected_site()
        if current is None:
            return
        with wx.MessageDialog(
            self.dialog,
            f'Delete the saved site "{current.name}"?',
            "Delete Site",
            wx.YES_NO | wx.ICON_QUESTION,
        ) as confirm:
            if confirm.ShowModal() != wx.ID_YES:
                return
        delete_site(current.name)
        self._refresh()

    def show(self) -> SiteConfig | None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            if show_modal_dialog(self.dialog, "SSH Site Manager") != wx.ID_OK:
                return None
            self.chosen = self._selected_site()
            return self.chosen
        finally:
            self.dialog.Destroy()


class RemoteBrowserDialog:
    """Browse remote directories and pick a file to edit.

    ``list_dir`` is a callable ``path -> list[RemoteEntry]`` (entries expose
    ``name`` and ``is_dir``); the dialog keeps no SFTP knowledge of its own.
    """

    def __init__(
        self,
        parent: object,
        *,
        list_dir,
        start_dir: str = "/",
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._list_dir = list_dir
        self._cwd = start_dir or "/"
        self._rows: list[tuple[str, bool]] = []  # (path, is_dir); "" path == parent
        self.selected_path: str | None = None
        self._announce = announce_cb or (lambda _: None)

        self.dialog = wx.Dialog(
            parent, title="Open Remote File", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetSize((620, 520))
        root = wx.BoxSizer(wx.VERTICAL)
        self.path_label = wx.StaticText(self.dialog, label=self._cwd)
        root.Add(self.path_label, 0, wx.ALL, 10)
        self.listbox = wx.ListBox(self.dialog, style=wx.LB_SINGLE)
        self.listbox.SetName("Remote files")
        root.Add(self.listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer(1)
        buttons.Add(wx.Button(self.dialog, wx.ID_OK, label="Open"), 0, wx.RIGHT, 8)
        buttons.Add(wx.Button(self.dialog, wx.ID_CANCEL, label="Cancel"), 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        self.dialog.SetSizer(root)

        self.listbox.Bind(wx.EVT_LISTBOX_DCLICK, self._on_activate)
        self._populate()

    def _join(self, name: str) -> str:
        base = self._cwd.rstrip("/")
        return f"{base}/{name}" if base else f"/{name}"

    def _populate(self) -> None:
        self.path_label.SetLabel(self._cwd)
        self._announce(self._cwd)
        labels: list[str] = []
        self._rows = []
        if self._cwd not in ("", "/"):
            labels.append(".. (parent directory)")
            self._rows.append(("", True))
        try:
            entries = self._list_dir(self._cwd)
        except Exception as error:  # noqa: BLE001 - surface listing errors in the list
            labels.append(f"[error] {error}")
            self._rows.append(("", False))
            entries = []
        for entry in entries:
            prefix = "[dir] " if entry.is_dir else "      "
            labels.append(f"{prefix}{entry.name}")
            self._rows.append((self._join(entry.name), entry.is_dir))
        self.listbox.Set(labels)
        if labels:
            self.listbox.SetSelection(0)

    def _on_activate(self, _event: object) -> None:
        index = self.listbox.GetSelection()
        if index == self._wx.NOT_FOUND or index < 0 or index >= len(self._rows):
            return
        path, is_dir = self._rows[index]
        if is_dir:
            if path == "":  # parent
                self._cwd = self._cwd.rstrip("/").rsplit("/", 1)[0] or "/"
            else:
                self._cwd = path
            self._populate()
            return
        if path:
            self.selected_path = path
            self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> str | None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            if show_modal_dialog(self.dialog, "Open Remote File") != wx.ID_OK:
                return None
            if self.selected_path is None:
                index = self.listbox.GetSelection()
                if 0 <= index < len(self._rows):
                    path, is_dir = self._rows[index]
                    if path and not is_dir:
                        self.selected_path = path
            return self.selected_path
        finally:
            self.dialog.Destroy()
