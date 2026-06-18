"""Remote Sites manager dialog (issue #154).

A two-panel :class:`wx.Dialog` (site list + directory browser) that conforms
to the QUILL dialog contract (A11Y-4 / DLG-3):

* Land initial focus on the site list (the first actionable control).
* Honour the QUILL modal id contract — Escape closes, Enter triggers the
  affirmative action, both via :func:`apply_modal_ids`.
* Return focus to the editor on close.
* Every actionable control has an explicit accessible name.

The dialog itself is a *file picker*. It is shown from the File > Open from
Remote submenu and from the File > Save to Remote / Save Copy to Remote
actions. The caller passes the desired :class:`DialogMode` (``OPEN`` or
``SAVE``) and the dialog adapts the button label, the title, and the
on-accept behaviour accordingly.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import wx

from quill.core.remote_sites import (
    PROTOCOL_FTP,
    PROTOCOL_S3,
    PROTOCOL_SFTP,
    PROTOCOL_WEBDAV,
    RemoteSite,
    default_port,
    delete_site,
    load_password,
    load_sites,
    save_password,
    upsert_site,
)
from quill.ui.dialog_contract import apply_modal_ids, focus_primary_control, show_message_box


class DialogMode(Enum):
    """Whether the dialog is being used to pick a file to open or a target for save."""

    OPEN = "open"
    SAVE = "save"


@dataclass(slots=True)
class RemoteSitesResult:
    """The user-accepted outcome of a remote-sites dialog session."""

    site: RemoteSite
    path: str
    mode: DialogMode


class _SiteList(wx.ListBox):
    """A wx.ListBox bound to the saved :class:`RemoteSite` rows."""

    def __init__(self, parent: wx.Window, sites: list[RemoteSite]) -> None:
        super().__init__(
            parent,
            choices=[site.name for site in sites],
            style=wx.LB_SINGLE | wx.LB_NEEDED_SB,
        )
        self._sites = list(sites)
        if sites:
            self.SetSelection(0)

    @property
    def sites(self) -> list[RemoteSite]:
        return list(self._sites)

    def selected_site(self) -> RemoteSite | None:
        index = self.GetSelection()
        if index == wx.NOT_FOUND or not (0 <= index < len(self._sites)):
            return None
        return self._sites[index]

    def replace_sites(self, sites: list[RemoteSite]) -> None:
        self._sites = list(sites)
        self.Clear()
        for site in sites:
            self.Append(site.name)
        if sites:
            self.SetSelection(0)


class _RemoteDirList(wx.ListBox):
    """A directory listing for a remote site. Populated by the dialog thread."""

    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent, style=wx.LB_SINGLE | wx.LB_NEEDED_SB)
        self._entries: list[object] = []
        self._path = ""

    def populate(self, entries: list[object], path: str) -> None:
        self._entries = list(entries)
        self._path = path
        self.Clear()
        for entry in entries:
            display_fn = getattr(entry, "to_display", None)
            if display_fn is None:
                display = str(entry)
            else:
                display = display_fn()
            self.Append(display)

    def selected_entry(self) -> object | None:
        index = self.GetSelection()
        if index == wx.NOT_FOUND or not (0 <= index < len(self._entries)):
            return None
        return self._entries[index]

    @property
    def current_path(self) -> str:
        return self._path


class RemoteSitesDialog(wx.Dialog):
    """The two-panel Remote Sites manager dialog."""

    def __init__(
        self,
        parent: wx.Window,
        *,
        mode: DialogMode = DialogMode.OPEN,
        title: str = "Open from Remote",
    ) -> None:
        super().__init__(parent, title=title, size=(820, 480), style=wx.DEFAULT_DIALOG_STYLE)
        self._mode = mode
        self._result: RemoteSitesResult | None = None
        self._build_ui()
        apply_modal_ids(
            self,
            affirmative_id=wx.ID_OK,
            affirmative_label=("&Open" if mode is DialogMode.OPEN else "&Save"),
            cancel_id=wx.ID_CANCEL,
            cancel_label="&Cancel",
        )
        focus_primary_control(self)
        self._refresh_sites()
        self.CentreOnParent()

    # --- UI construction -----------------------------------------------------

    def _build_ui(self) -> None:
        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.VERTICAL)
        intro = wx.StaticText(
            panel,
            label=(
                "Choose a saved remote site, browse its directories, then select a "
                "file to {}.".format("open" if self._mode is DialogMode.OPEN else "save to")
            ),
        )
        intro.Wrap(780)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 8)

        # Site list (left)
        left_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Saved sites")
        self._site_list = _SiteList(panel, load_sites())
        self._site_list.SetName("Saved remote sites")
        left_box.Add(self._site_list, 1, wx.EXPAND | wx.ALL, 4)
        site_buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._id_new_site = wx.NewIdRef()
        self._id_edit_site = wx.NewIdRef()
        self._id_delete_site = wx.NewIdRef()
        new_btn = wx.Button(panel, id=self._id_new_site, label="&New site...")
        edit_btn = wx.Button(panel, id=self._id_edit_site, label="&Edit site...")
        delete_btn = wx.Button(panel, id=self._id_delete_site, label="&Delete site")
        new_btn.SetName("Add a new remote site")
        edit_btn.SetName("Edit the selected remote site")
        delete_btn.SetName("Delete the selected remote site")
        site_buttons.Add(new_btn, 0, wx.RIGHT, 4)
        site_buttons.Add(edit_btn, 0, wx.RIGHT, 4)
        site_buttons.Add(delete_btn, 0)
        left_box.Add(site_buttons, 0, wx.EXPAND | wx.ALL, 4)

        # Directory browser (right)
        right_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Browse")
        path_label = wx.StaticText(panel, label="Current path:")
        right_box.Add(path_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)
        self._path_text = wx.TextCtrl(panel, value="", style=wx.TE_READONLY)
        self._path_text.SetName("Current remote path")
        right_box.Add(self._path_text, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 4)
        self._dir_list = _RemoteDirList(panel)
        self._dir_list.SetName("Remote directory entries")
        right_box.Add(self._dir_list, 1, wx.EXPAND | wx.ALL, 4)
        # Entry field for the path to use on accept.
        target_label = wx.StaticText(panel, label="Remote file:")
        right_box.Add(target_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)
        self._target_text = wx.TextCtrl(panel, value="", style=wx.TE_PROCESS_ENTER)
        self._target_text.SetName("Remote file path")
        right_box.Add(self._target_text, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)

        # Top-level split: sites | browser
        split = wx.BoxSizer(wx.HORIZONTAL)
        split.Add(left_box, 1, wx.EXPAND | wx.RIGHT, 6)
        split.Add(right_box, 2, wx.EXPAND)
        root.Add(split, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # OK / Cancel (sizer with wx.EXPAND per the dialog contract).
        button_row = wx.BoxSizer(wx.HORIZONTAL)
        button_row.AddStretchSpacer(1)
        is_open = self._mode is DialogMode.OPEN
        ok_label = "&Open" if is_open else "&Save"
        ok = wx.Button(panel, id=wx.ID_OK, label=ok_label)
        cancel = wx.Button(panel, id=wx.ID_CANCEL, label="&Cancel")
        ok.SetName("Open from selected site" if is_open else "Save to selected site")
        cancel.SetName("Cancel")
        button_row.Add(ok, 0, wx.EXPAND | wx.RIGHT, 4)
        button_row.Add(cancel, 0, wx.EXPAND)
        root.Add(button_row, 0, wx.EXPAND | wx.ALL, 8)

        panel.SetSizer(root)

        # --- Bindings ---
        self._site_list.Bind(wx.EVT_LISTBOX, self._on_site_selected)
        self._site_list.Bind(wx.EVT_LISTBOX_DCLICK, self._on_site_activated)
        self._dir_list.Bind(wx.EVT_LISTBOX_DCLICK, self._on_dir_activated)
        self._dir_list.Bind(wx.EVT_LISTBOX, self._on_dir_selected)
        self._target_text.Bind(wx.EVT_TEXT_ENTER, self._on_accept)
        self.Bind(wx.EVT_BUTTON, self._on_new_site, id=self._id_new_site)
        self.Bind(wx.EVT_BUTTON, self._on_edit_site, id=self._id_edit_site)
        self.Bind(wx.EVT_BUTTON, self._on_delete_site, id=self._id_delete_site)
        self.Bind(wx.EVT_BUTTON, self._on_accept, id=wx.ID_OK)

    # --- actions -------------------------------------------------------------

    def _refresh_sites(self) -> None:
        self._site_list.replace_sites(load_sites())
        if self._site_list.sites:
            self._site_list.SetSelection(0)
            self._on_site_selected(None)

    def _on_site_selected(self, _event: wx.Event | None) -> None:
        site = self._site_list.selected_site()
        if site is None:
            return
        self._path_text.SetValue(site.root_dir or "/")
        self._dir_list.populate([], site.root_dir or "/")

    def _on_site_activated(self, _event: wx.Event) -> None:
        self._on_site_selected(None)

    def _on_dir_selected(self, _event: wx.Event) -> None:
        entry = self._dir_list.selected_entry()
        if entry is None:
            return
        if getattr(entry, "is_dir", False):
            self._target_text.SetValue("")
            return
        # Build the absolute remote path from the current dir + the entry name.
        current = self._dir_list.current_path or ""
        name = getattr(entry, "name", "")
        if not current.endswith("/") and current:
            current = current + "/"
        self._target_text.SetValue(f"{current}{name}")

    def _on_dir_activated(self, _event: wx.Event) -> None:
        entry = self._dir_list.selected_entry()
        if entry is None:
            return
        if getattr(entry, "is_dir", False):
            return
        self._on_accept(None)

    def _on_new_site(self, _event: wx.Event) -> None:
        with _SiteEditorDialog(self, site=None) as editor:
            if editor.ShowModal() == wx.ID_OK and editor.site is not None:
                upsert_site(editor.site)
                if editor.password:
                    save_password(editor.site.id, editor.password)
                self._refresh_sites()

    def _on_edit_site(self, _event: wx.Event) -> None:
        current = self._site_list.selected_site()
        if current is None:
            return
        with _SiteEditorDialog(self, site=current) as editor:
            if editor.ShowModal() == wx.ID_OK and editor.site is not None:
                upsert_site(editor.site)
                if editor.password:
                    save_password(editor.site.id, editor.password)
                self._refresh_sites()

    def _on_delete_site(self, _event: wx.Event) -> None:
        current = self._site_list.selected_site()
        if current is None:
            return
        result = show_message_box(
            f"Delete the saved site '{current.name}'?",
            "Delete remote site",
            wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
            self,
        )
        if result == wx.YES:
            delete_site(current.id)
            self._refresh_sites()

    def _on_accept(self, _event: wx.Event | None) -> None:
        site = self._site_list.selected_site()
        if site is None:
            show_message_box(
                "Choose a remote site first.", self.GetTitle(), wx.ICON_WARNING | wx.OK, self
            )
            return
        path = self._target_text.GetValue().strip()
        if not path:
            show_message_box(
                "Enter a remote file path or select an entry from the directory list.",
                self.GetTitle(),
                wx.ICON_WARNING | wx.OK,
                self,
            )
            return
        self._result = RemoteSitesResult(site=site, path=path, mode=self._mode)
        self.EndModal(wx.ID_OK)

    # --- public API ----------------------------------------------------------

    @property
    def result(self) -> RemoteSitesResult | None:
        return self._result


# --- site editor ------------------------------------------------------------


class _SiteEditorDialog(wx.Dialog):
    """A modal editor for a single :class:`RemoteSite` profile."""

    def __init__(self, parent: wx.Window, *, site: RemoteSite | None) -> None:
        super().__init__(
            parent,
            title="New Remote Site" if site is None else f"Edit {site.name}",
            size=(480, 360),
            style=wx.DEFAULT_DIALOG_STYLE,
        )
        self._site = site
        self.password: str = ""
        self.site: RemoteSite | None = None
        self._build_ui()
        apply_modal_ids(
            self,
            affirmative_id=wx.ID_OK,
            affirmative_label="&Save",
            cancel_id=wx.ID_CANCEL,
            cancel_label="&Cancel",
        )
        focus_primary_control(self)
        self.CentreOnParent()

    def _build_ui(self) -> None:
        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(cols=2, vgap=4, hgap=4)

        grid.Add(wx.StaticText(panel, label="Friendly &name:"))
        self._name_ctrl = wx.TextCtrl(panel, value=self._site.name if self._site else "")
        self._name_ctrl.SetName("Site name")
        grid.Add(self._name_ctrl, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="&Protocol:"))
        protocols = [PROTOCOL_FTP, PROTOCOL_SFTP, PROTOCOL_WEBDAV, PROTOCOL_S3]
        self._protocol_ctrl = wx.Choice(panel, choices=protocols)
        self._protocol_ctrl.SetName("Protocol")
        initial = self._site.protocol if self._site else PROTOCOL_FTP
        if initial in protocols:
            self._protocol_ctrl.SetStringSelection(initial)
        else:
            self._protocol_ctrl.SetSelection(0)
        grid.Add(self._protocol_ctrl, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="&Host:"))
        self._host_ctrl = wx.TextCtrl(panel, value=self._site.host if self._site else "")
        self._host_ctrl.SetName("Host name")
        grid.Add(self._host_ctrl, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="&Port:"))
        self._port_ctrl = wx.TextCtrl(
            panel,
            value=str(self._site.port if self._site and self._site.port else ""),
        )
        self._port_ctrl.SetName("Port number")
        grid.Add(self._port_ctrl, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="&User name:"))
        self._username_ctrl = wx.TextCtrl(panel, value=self._site.username if self._site else "")
        self._username_ctrl.SetName("User name")
        grid.Add(self._username_ctrl, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="&Password:"))
        self._password_ctrl = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        self._password_ctrl.SetName("Password")
        if self._site is not None:
            self._password_ctrl.SetValue(load_password(self._site.id))
        grid.Add(self._password_ctrl, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="&Root directory:"))
        self._root_ctrl = wx.TextCtrl(panel, value=self._site.root_dir if self._site else "")
        self._root_ctrl.SetName("Root directory")
        grid.Add(self._root_ctrl, 1, wx.EXPAND)

        grid.Add(wx.StaticText(panel, label="&Bucket (S3 / base path WebDAV):"))
        self._extra_ctrl = wx.TextCtrl(panel)
        self._extra_ctrl.SetName("Protocol-specific metadata")
        if self._site is not None:
            self._extra_ctrl.SetValue(
                (self._site.extra or {}).get("s3_bucket", "")
                or (self._site.extra or {}).get("webdav_base", "")
            )
        grid.Add(self._extra_ctrl, 1, wx.EXPAND)

        self._trust_ctrl = wx.CheckBox(panel, label="&Trust host key on first use (SFTP)")
        self._trust_ctrl.SetName("Trust host key on first use")
        self._trust_ctrl.SetValue(bool(self._site and self._site.trust_first_use))
        grid.Add((0, 0))
        grid.Add(self._trust_ctrl, 1, wx.EXPAND)

        grid.AddGrowableCol(1, 1)
        root.Add(grid, 1, wx.EXPAND | wx.ALL, 8)

        # OK / Cancel (sizer with wx.EXPAND per the dialog contract).
        button_row = wx.BoxSizer(wx.HORIZONTAL)
        button_row.AddStretchSpacer(1)
        ok = wx.Button(panel, id=wx.ID_OK, label="&Save")
        cancel = wx.Button(panel, id=wx.ID_CANCEL, label="&Cancel")
        ok.SetName("Save remote site")
        cancel.SetName("Cancel")
        button_row.Add(ok, 0, wx.EXPAND | wx.RIGHT, 4)
        button_row.Add(cancel, 0, wx.EXPAND)
        root.Add(button_row, 0, wx.EXPAND | wx.ALL, 8)

        panel.SetSizer(root)
        self.Bind(wx.EVT_BUTTON, self._on_save, id=wx.ID_OK)

    def _on_save(self, _event: wx.Event) -> None:
        name = self._name_ctrl.GetValue().strip()
        protocol = self._protocol_ctrl.GetStringSelection() or PROTOCOL_FTP
        host = self._host_ctrl.GetValue().strip()
        port_text = self._port_ctrl.GetValue().strip()
        try:
            port = int(port_text) if port_text else default_port(protocol)
        except ValueError:
            port = default_port(protocol)
        username = self._username_ctrl.GetValue().strip()
        root_dir = self._root_ctrl.GetValue().strip()
        password = self._password_ctrl.GetValue()
        extra_value = self._extra_ctrl.GetValue().strip()
        extra: dict[str, str] = {}
        if protocol == PROTOCOL_S3 and extra_value:
            extra["s3_bucket"] = extra_value
        elif protocol == PROTOCOL_WEBDAV and extra_value:
            extra["webdav_base"] = extra_value
        if not name or not host:
            show_message_box(
                "Name and host are required.", self.GetTitle(), wx.ICON_WARNING | wx.OK, self
            )
            return
        site_id = (self._site.id if self._site else name).strip() or name
        self.site = RemoteSite(
            id=site_id,
            name=name,
            protocol=protocol,
            host=host,
            port=port,
            username=username,
            root_dir=root_dir,
            trust_first_use=self._trust_ctrl.IsChecked(),
            extra=extra,
        )
        self.password = password
        self.EndModal(wx.ID_OK)
