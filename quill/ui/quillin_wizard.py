"""In-app Quillin Snippet Wizard.

Opens a native wxPython dialog that collects extension identity and snippet
commands, validates the result with :func:`quill.core.quillins.validation.validate_manifest`,
and writes ``manifest.json`` directly to the user's extensions folder.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from quill.core.quillins.loader import extensions_root, set_enabled
from quill.core.quillins.model import MENU_PARENTS
from quill.core.quillins.validation import validate_manifest
from quill.ui.dialog_contract import apply_modal_ids

_ALL_MENU_PARENTS: list[str] = list(MENU_PARENTS)
_QUILLINS_WIZARD_COMMAND = "tools.quillin_wizard"


@dataclass
class _CommandDraft:
    title: str = ""
    cmd_id: str = ""
    cmd_id_edited: bool = False
    snippet: str = ""
    menu_parents: set[str] = field(default_factory=set)
    context_menu: bool = False
    hotkey: str = ""


def _slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "ext"


def _auto_ext_id(name: str) -> str:
    return _slugify(name)


def _auto_cmd_id(ext_id: str, title: str) -> str:
    base = ext_id.rsplit(".", 1)[-1] if "." in ext_id else (ext_id or "ext")
    slug = _slugify(title)
    if not slug or slug == "ext":
        return f"ext.{base}.command"
    return f"ext.{base}.{slug}"


def _build_manifest(
    name: str,
    ext_id: str,
    version: str,
    author: str,
    license_str: str,
    desc: str,
    drafts: list[_CommandDraft],
) -> dict:
    has_clipboard = any("${clipboard}" in d.snippet for d in drafts)
    caps = ["clipboard.read"] if has_clipboard else []

    commands = [
        {"id": d.cmd_id, "title": d.title, "run": {"snippet": d.snippet}}
        for d in drafts
        if d.cmd_id and d.title
    ]
    menus = [
        {"parent": p, "command": d.cmd_id}
        for d in drafts
        for p in sorted(d.menu_parents)
        if d.cmd_id
    ]
    ctx = [{"command": d.cmd_id} for d in drafts if d.context_menu and d.cmd_id]
    hotkeys = [
        {"command": d.cmd_id, "binding": d.hotkey.strip()}
        for d in drafts
        if d.hotkey.strip() and d.cmd_id
    ]

    contrib: dict = {"commands": commands}
    if menus:
        contrib["menus"] = menus
    if ctx:
        contrib["context_menu"] = ctx
    if hotkeys:
        contrib["hotkeys"] = hotkeys

    raw: dict = {
        "schema": "quill.extension/1",
        "id": ext_id,
        "name": name,
        "version": version or "1.0.0",
        "capabilities": caps,
        "contributes": contrib,
    }
    if author.strip():
        raw["author"] = author.strip()
    if desc.strip():
        raw["description"] = desc.strip()
    if license_str.strip():
        raw["license"] = license_str.strip()
    return raw


def open_quillin_wizard(
    frame: object,
    wx: object,
    *,
    announce: object,
    show_modal: object,
    reload_callback: object,
    third_party_locked: bool = True,
) -> None:
    """Open the New Quillin wizard dialog."""

    # -- State ----------------------------------------------------------------

    drafts: list[_CommandDraft] = [_CommandDraft()]
    _current = [0]
    _updating = [False]
    _ext_id_manual = [False]

    # -- Dialog shell ---------------------------------------------------------

    dialog = wx.Dialog(
        frame,
        title="New Quillin",
        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
    )

    try:
        import wx.lib.scrolledpanel as sp

        scrolled = sp.ScrolledPanel(dialog)
        scrolled.SetupScrolling(scroll_x=False, scroll_y=True)
    except Exception:
        scrolled = wx.Panel(dialog)

    body = wx.BoxSizer(wx.VERTICAL)

    # -- SEC-8 note -----------------------------------------------------------

    if third_party_locked:
        note = wx.StaticText(
            scrolled,
            label=(
                "Note: Third-party Quillins are saved to your extensions folder "
                "but will not run until third-party support is enabled in this build."
            ),
        )
        note.Wrap(660)
        body.Add(note, 0, wx.ALL | wx.EXPAND, 8)

    # -- Section 1: Extension identity ----------------------------------------

    id_box = wx.StaticBoxSizer(wx.StaticBox(scrolled, label="Extension identity"), wx.VERTICAL)
    grid = wx.FlexGridSizer(rows=0, cols=2, vgap=6, hgap=8)
    grid.AddGrowableCol(1, 1)

    def _add_field(label_text: str, make_ctrl) -> object:
        grid.Add(wx.StaticText(scrolled, label=label_text), 0, wx.ALIGN_CENTER_VERTICAL)
        ctrl = make_ctrl()
        grid.Add(ctrl, 1, wx.EXPAND)
        return ctrl

    name_ctrl = _add_field("Display &name *", lambda: wx.TextCtrl(scrolled))
    name_ctrl.SetName("Display name")

    ext_id_ctrl = _add_field("Extension &ID *", lambda: wx.TextCtrl(scrolled))
    ext_id_ctrl.SetName("Extension ID")

    version_ctrl = _add_field("&Version *", lambda: wx.TextCtrl(scrolled, value="1.0.0"))
    version_ctrl.SetName("Version")

    author_ctrl = _add_field("&Author", lambda: wx.TextCtrl(scrolled))
    author_ctrl.SetName("Author")

    license_ctrl = _add_field("&License", lambda: wx.TextCtrl(scrolled, value="MIT"))
    license_ctrl.SetName("License")

    id_box.Add(grid, 0, wx.ALL | wx.EXPAND, 8)
    id_box.Add(wx.StaticText(scrolled, label="&Description"), 0, wx.LEFT | wx.RIGHT, 8)
    desc_ctrl = wx.TextCtrl(scrolled, style=wx.TE_MULTILINE, size=(-1, 56))
    desc_ctrl.SetName("Description")
    id_box.Add(desc_ctrl, 0, wx.ALL | wx.EXPAND, 8)
    body.Add(id_box, 0, wx.ALL | wx.EXPAND, 8)

    # -- Section 2: Commands --------------------------------------------------

    cmd_box = wx.StaticBoxSizer(wx.StaticBox(scrolled, label="Commands"), wx.VERTICAL)

    cmd_box.Add(wx.StaticText(scrolled, label="Commands &list:"), 0, wx.LEFT | wx.TOP, 8)
    chooser = wx.ListBox(scrolled, choices=["(untitled 1)"], size=(-1, 76))
    chooser.SetName("Commands list")
    chooser.SetSelection(0)
    cmd_box.Add(chooser, 0, wx.ALL | wx.EXPAND, 8)

    cmd_btn_row = wx.BoxSizer(wx.HORIZONTAL)
    add_btn = wx.Button(scrolled, label="&Add command")
    remove_btn = wx.Button(scrolled, label="&Remove command")
    cmd_btn_row.Add(add_btn, 0, wx.RIGHT, 6)
    cmd_btn_row.Add(remove_btn, 0)
    cmd_box.Add(cmd_btn_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    # Command detail sub-box
    detail_box = wx.StaticBoxSizer(wx.StaticBox(scrolled, label="Command details"), wx.VERTICAL)
    detail_grid = wx.FlexGridSizer(rows=0, cols=2, vgap=6, hgap=8)
    detail_grid.AddGrowableCol(1, 1)

    def _add_detail_field(label_text: str, make_ctrl) -> object:
        detail_grid.Add(wx.StaticText(scrolled, label=label_text), 0, wx.ALIGN_CENTER_VERTICAL)
        ctrl = make_ctrl()
        detail_grid.Add(ctrl, 1, wx.EXPAND)
        return ctrl

    cmd_title_ctrl = _add_detail_field("Menu &title *", lambda: wx.TextCtrl(scrolled))
    cmd_title_ctrl.SetName("Menu title")

    cmd_id_ctrl = _add_detail_field("Command &ID *", lambda: wx.TextCtrl(scrolled))
    cmd_id_ctrl.SetName("Command ID")

    detail_box.Add(detail_grid, 0, wx.ALL | wx.EXPAND, 8)
    detail_box.Add(
        wx.StaticText(
            scrolled,
            label=(
                "&Snippet body * "
                "(tokens: ${selection} ${clipboard} ${date} ${time} "
                "${filename} ${title} ${line_number} ${word_at_cursor} ${uuid} ${cursor})"
            ),
        ),
        0,
        wx.LEFT | wx.RIGHT,
        8,
    )
    snippet_ctrl = wx.TextCtrl(scrolled, style=wx.TE_MULTILINE, size=(-1, 70))
    snippet_ctrl.SetName("Snippet body")
    detail_box.Add(snippet_ctrl, 0, wx.ALL | wx.EXPAND, 8)

    detail_box.Add(
        wx.StaticText(scrolled, label="Add to &menus (check to include):"),
        0,
        wx.LEFT | wx.RIGHT,
        8,
    )
    menu_chooser = wx.CheckListBox(
        scrolled, choices=_ALL_MENU_PARENTS, size=(-1, 110)
    )  # A11Y-SR-1-OK: Quillin menu parent picker; convert to CheckBox list in follow-up
    menu_chooser.SetName("Parent menus")
    detail_box.Add(menu_chooser, 0, wx.ALL | wx.EXPAND, 8)

    ctx_cb = wx.CheckBox(scrolled, label="Add to &context menu (right-click)")
    detail_box.Add(ctx_cb, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    detail_box.Add(
        wx.StaticText(scrolled, label="&Hotkey (optional, e.g. Ctrl+Shift+D):"),
        0,
        wx.LEFT | wx.RIGHT,
        8,
    )
    hotkey_ctrl = wx.TextCtrl(scrolled)
    hotkey_ctrl.SetName("Hotkey binding")
    detail_box.Add(hotkey_ctrl, 0, wx.ALL | wx.EXPAND, 8)

    cmd_box.Add(detail_box, 0, wx.ALL | wx.EXPAND, 8)
    body.Add(cmd_box, 0, wx.ALL | wx.EXPAND, 8)

    # -- Auto-derived capabilities --------------------------------------------

    caps_text = wx.StaticText(scrolled, label="Auto-derived capabilities: (none)")
    body.Add(caps_text, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    # -- Validation errors ----------------------------------------------------

    error_text = wx.StaticText(scrolled, label="")
    body.Add(error_text, 0, wx.LEFT | wx.RIGHT, 8)

    # -- JSON preview ---------------------------------------------------------

    body.Add(wx.StaticText(scrolled, label="JSON &preview:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
    preview_ctrl = wx.TextCtrl(
        scrolled,
        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
        size=(-1, 120),
    )
    preview_ctrl.SetName("JSON preview")
    body.Add(preview_ctrl, 0, wx.ALL | wx.EXPAND, 8)

    scrolled.SetSizer(body)

    # -- Action buttons (outside scroll area) ---------------------------------

    outer = wx.BoxSizer(wx.VERTICAL)
    outer.Add(scrolled, 1, wx.EXPAND)

    action_row = wx.BoxSizer(wx.HORIZONTAL)
    save_btn = wx.Button(dialog, id=wx.ID_OK, label="&Save Quillin")
    copy_btn = wx.Button(dialog, label="Cop&y JSON")
    cancel_btn = wx.Button(dialog, id=wx.ID_CANCEL, label="Cancel")
    action_row.AddStretchSpacer(1)
    action_row.Add(save_btn, 0, wx.RIGHT, 6)
    action_row.Add(copy_btn, 0, wx.RIGHT, 6)
    action_row.Add(cancel_btn, 0)
    outer.Add(action_row, 0, wx.ALL | wx.EXPAND, 8)

    dialog.SetSizer(outer)
    dialog.SetSize((740, 720))
    if hasattr(dialog, "CentreOnParent"):
        dialog.CentreOnParent()

    # -- Logic helpers --------------------------------------------------------

    def _save_current_detail() -> None:
        idx = _current[0]
        if 0 <= idx < len(drafts):
            d = drafts[idx]
            d.title = cmd_title_ctrl.GetValue()
            d.cmd_id = cmd_id_ctrl.GetValue()
            d.snippet = snippet_ctrl.GetValue()
            d.menu_parents = {
                _ALL_MENU_PARENTS[i]
                for i in range(menu_chooser.GetCount())
                if menu_chooser.IsChecked(i)
            }
            d.context_menu = ctx_cb.IsChecked()
            d.hotkey = hotkey_ctrl.GetValue()

    def _load_command(idx: int) -> None:
        if not (0 <= idx < len(drafts)):
            return
        d = drafts[idx]
        _updating[0] = True
        try:
            cmd_title_ctrl.SetValue(d.title)
            cmd_id_ctrl.SetValue(d.cmd_id)
            snippet_ctrl.SetValue(d.snippet)
            for i, parent in enumerate(_ALL_MENU_PARENTS):
                menu_chooser.Check(i, parent in d.menu_parents)
            ctx_cb.SetValue(d.context_menu)
            hotkey_ctrl.SetValue(d.hotkey)
        finally:
            _updating[0] = False

    def _refresh_cmd_list() -> None:
        _updating[0] = True
        try:
            labels = [d.title or f"(untitled {i + 1})" for i, d in enumerate(drafts)]
            chooser.Set(labels)
            idx = min(_current[0], len(drafts) - 1)
            if idx >= 0:
                chooser.SetSelection(idx)
        finally:
            _updating[0] = False

    def _current_manifest() -> dict:
        _save_current_detail()
        return _build_manifest(
            name=name_ctrl.GetValue(),
            ext_id=ext_id_ctrl.GetValue(),
            version=version_ctrl.GetValue(),
            author=author_ctrl.GetValue(),
            license_str=license_ctrl.GetValue(),
            desc=desc_ctrl.GetValue(),
            drafts=drafts,
        )

    def _refresh_preview() -> None:
        raw = _current_manifest()
        caps = raw.get("capabilities", [])
        caps_text.SetLabel("Auto-derived capabilities: " + (", ".join(caps) if caps else "(none)"))
        try:
            preview_ctrl.SetValue(json.dumps(raw, indent=2))
        except Exception:
            pass
        errors = validate_manifest(raw)
        error_text.SetLabel(("Problems: " + "; ".join(errors)) if errors else "")
        fit = getattr(scrolled, "FitInside", None)
        if callable(fit):
            fit()

    # -- Event handlers -------------------------------------------------------

    def on_name_change(_event: object) -> None:
        if _updating[0]:
            return
        if not _ext_id_manual[0]:
            _updating[0] = True
            ext_id_ctrl.SetValue(_auto_ext_id(name_ctrl.GetValue()))
            _updating[0] = False
        _refresh_preview()

    def on_ext_id_change(_event: object) -> None:
        if _updating[0]:
            return
        _ext_id_manual[0] = True
        _refresh_preview()

    def on_cmd_title_change(_event: object) -> None:
        if _updating[0]:
            return
        idx = _current[0]
        if 0 <= idx < len(drafts):
            d = drafts[idx]
            title_val = cmd_title_ctrl.GetValue()
            d.title = title_val
            if not d.cmd_id_edited:
                _updating[0] = True
                new_id = _auto_cmd_id(ext_id_ctrl.GetValue(), title_val)
                cmd_id_ctrl.SetValue(new_id)
                d.cmd_id = new_id
                _updating[0] = False
            _refresh_cmd_list()
        _refresh_preview()

    def on_cmd_id_change(_event: object) -> None:
        if _updating[0]:
            return
        idx = _current[0]
        if 0 <= idx < len(drafts):
            drafts[idx].cmd_id_edited = True
        _refresh_preview()

    def on_detail_change(_event: object) -> None:
        if _updating[0]:
            return
        _refresh_preview()

    def on_cmd_select(_event: object) -> None:
        if _updating[0]:
            return
        _save_current_detail()
        sel = chooser.GetSelection()
        if sel != wx.NOT_FOUND:
            _current[0] = sel
            _load_command(sel)
        _refresh_preview()

    def on_add_cmd(_event: object) -> None:
        _save_current_detail()
        n = len(drafts) + 1
        ext_id = ext_id_ctrl.GetValue()
        drafts.append(
            _CommandDraft(
                title=f"Command {n}",
                cmd_id=_auto_cmd_id(ext_id, f"command {n}"),
            )
        )
        _current[0] = len(drafts) - 1
        _refresh_cmd_list()
        _load_command(_current[0])
        chooser.SetFocus()
        _refresh_preview()

    def on_remove_cmd(_event: object) -> None:
        if len(drafts) <= 1:
            announce("Cannot remove the last command.")
            return
        idx = _current[0]
        drafts.pop(idx)
        _current[0] = min(idx, len(drafts) - 1)
        _refresh_cmd_list()
        _load_command(_current[0])
        _refresh_preview()

    def on_save(_event: object) -> None:
        _save_current_detail()
        raw = _current_manifest()
        errors = validate_manifest(raw)
        if errors:
            error_text.SetLabel("Cannot save: " + "; ".join(errors))
            announce("Cannot save: " + errors[0])
            return

        ext_id = str(raw["id"])
        target_dir = extensions_root() / ext_id
        if target_dir.exists():
            confirm = wx.MessageDialog(
                dialog,
                f"A Quillin with ID '{ext_id}' already exists. Overwrite it?",
                "Overwrite Quillin?",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
            )
            try:
                approved = confirm.ShowModal() == wx.ID_YES
            finally:
                confirm.Destroy()
            if not approved:
                return

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            (target_dir / "manifest.json").write_text(json.dumps(raw, indent=2), encoding="utf-8")
            set_enabled(ext_id, True)
        except OSError as exc:
            error_text.SetLabel(f"Save failed: {exc}")
            announce(f"Save failed: {exc}")
            return

        reload_callback()
        announce(f"Quillin '{raw['name']}' saved and enabled.")
        dialog.EndModal(wx.ID_OK)

    def on_copy(_event: object) -> None:
        _save_current_detail()
        raw = _current_manifest()
        try:
            text = json.dumps(raw, indent=2)
        except Exception:
            # The user pressed Copy; tell them why nothing was copied.
            announce("Could not copy: the manifest could not be turned into JSON.")
            return
        clipboard = getattr(wx, "TheClipboard", None)
        copied = False
        if clipboard is not None and clipboard.Open():
            try:
                # SetData reports success; announcing "copied" on a False
                # return would be a lie to a screen-reader user (#790 review).
                copied = bool(clipboard.SetData(wx.TextDataObject(text)))
            finally:
                clipboard.Close()
        # Only claim success when the clipboard actually took the data.
        announce("JSON copied to clipboard." if copied else "Could not copy to the clipboard.")

    # -- Bind events ----------------------------------------------------------

    name_ctrl.Bind(wx.EVT_TEXT, on_name_change)
    ext_id_ctrl.Bind(wx.EVT_TEXT, on_ext_id_change)
    cmd_title_ctrl.Bind(wx.EVT_TEXT, on_cmd_title_change)
    cmd_id_ctrl.Bind(wx.EVT_TEXT, on_cmd_id_change)
    snippet_ctrl.Bind(wx.EVT_TEXT, on_detail_change)
    menu_chooser.Bind(wx.EVT_CHECKLISTBOX, on_detail_change)
    ctx_cb.Bind(wx.EVT_CHECKBOX, on_detail_change)
    hotkey_ctrl.Bind(wx.EVT_TEXT, on_detail_change)
    for _ctrl in (version_ctrl, author_ctrl, license_ctrl, desc_ctrl):
        _ctrl.Bind(wx.EVT_TEXT, lambda _e: _refresh_preview())

    chooser.Bind(wx.EVT_LISTBOX, on_cmd_select)
    add_btn.Bind(wx.EVT_BUTTON, on_add_cmd)
    remove_btn.Bind(wx.EVT_BUTTON, on_remove_cmd)
    save_btn.Bind(wx.EVT_BUTTON, on_save)
    copy_btn.Bind(wx.EVT_BUTTON, on_copy)

    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)

    # -- Show -----------------------------------------------------------------

    _refresh_preview()

    call_after = getattr(wx, "CallAfter", None)
    if callable(call_after):
        call_after(name_ctrl.SetFocus)
    else:
        name_ctrl.SetFocus()

    launcher = frame.FindFocus() if hasattr(frame, "FindFocus") else None
    try:
        show_modal(dialog, "New Quillin")
    finally:
        dialog.Destroy()
        if launcher is not None and hasattr(launcher, "SetFocus"):
            launcher.SetFocus()
