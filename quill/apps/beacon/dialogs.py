"""Accessible dialogs: quick capture and Build Search (PRD 14.3, 15.4).

Every control gets an accessible name via ``SetName`` (wx exposes this to UI
Automation on Windows). Tab order is direct and logical; no token controls;
tag entry is a plain editable field plus an autocomplete-less list. No
drag-and-drop anywhere.
"""

from __future__ import annotations

import wx

from quill.apps.beacon.model import ALL_TYPES
from quill.ui.dialog_contract import apply_modal_ids, show_message_box


def _name(ctrl: wx.Control, name: str) -> None:
    """Set the accessible name wx exposes to platform accessibility APIs."""
    ctrl.SetName(name)


class QuickCaptureDialog(wx.Dialog):
    """The quick capture form (PRD 14.3). Returns a dict, or None on cancel."""

    def __init__(
        self,
        parent,
        *,
        prefill_url: str = "",
        prefill_title: str = "",
        collections: list[str] | None = None,
    ):
        super().__init__(
            parent,
            title="Add Bookmark to QuillBeacon",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._collections = list(collections or [])
        self._result: dict | None = None

        sizer = wx.BoxSizer(wx.VERTICAL)
        form = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
        form.AddGrowableCol(1, proportion=1)

        self.title = self._row(form, "&Title:", prefill_title)
        self.resource = self._row(form, "&Resource (URL or path):", prefill_url)
        self.note = self._row(
            form, "&Note:", "", style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER, size=(320, 60)
        )
        self.collection = self._row(form, "&Collection:", "")
        if self._collections:
            self.collection.AppendText("/".join(self._collections[:5]))
        self.tags = self._row(form, "&Tags (comma separated):", "")

        sizer.Add(form, 1, wx.EXPAND | wx.ALL, 10)

        self.favorite = wx.CheckBox(self, label="&Favorite")
        _name(self.favorite, "Favorite")
        sizer.Add(self.favorite, 0, wx.LEFT | wx.BOTTOM, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.save = wx.Button(self, label="&Save")
        self.save_open = wx.Button(self, label="Save and &Open")
        cancel = wx.Button(self, label="Cancel", id=wx.ID_CANCEL)
        for b in (self.save, self.save_open, cancel):
            _name(b, b.GetLabel().replace("&", ""))
        self.save.SetDefault()
        buttons.Add(self.save, 0, wx.RIGHT, 8)
        buttons.Add(self.save_open, 0, wx.RIGHT, 8)
        buttons.Add(cancel, 0)
        sizer.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.resource.SetFocus()

        self.save.Bind(wx.EVT_BUTTON, lambda _e: self._done(open_it=False))
        self.save_open.Bind(wx.EVT_BUTTON, lambda _e: self._done(open_it=True))
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL)

    def _row(self, sizer, label, value, *, style=0, size=None) -> wx.TextCtrl:
        lbl = wx.StaticText(self, label=label)
        ctrl = wx.TextCtrl(self, value=value, style=style, size=size or (320, -1))
        _name(ctrl, label.replace("&", "").replace(":", "").strip())
        sizer.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(ctrl, 1, wx.EXPAND)
        return ctrl

    def _done(self, *, open_it: bool) -> None:
        if not self.resource.GetValue().strip():
            show_message_box(
                "Enter a URL or path to capture.", "QuillBeacon", style=wx.ICON_WARNING
            )
            self.resource.SetFocus()
            return
        tags = [t.strip() for t in self.tags.GetValue().split(",") if t.strip()]
        self._result = {
            "url": self.resource.GetValue().strip(),
            "title": self.title.GetValue().strip(),
            "note": self.note.GetValue().strip(),
            "collection": self.collection.GetValue().strip(),
            "tags": tags,
            "favorite": self.favorite.IsChecked(),
            "open": open_it,
        }
        self.EndModal(wx.ID_OK)

    def result(self) -> dict | None:
        return self._result


class BuildSearchDialog(wx.Dialog):
    """Structured search builder (PRD 15.4). Generates a query string."""

    def __init__(self, parent):
        super().__init__(
            parent, title="Build Search", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._result: str | None = None

        sizer = wx.BoxSizer(wx.VERTICAL)
        form = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
        form.AddGrowableCol(1, proportion=1)

        self.all_words = self._row(form, "Contains &all words:", "")
        self.phrase = self._row(form, "Contains exact &phrase:", "")
        self.exclude = self._row(form, "&Excludes words:", "")
        self.type_combo = self._combo(form, "Resource &type:", ["(any)", *ALL_TYPES])
        self.collection = self._row(form, "&Collection:", "")
        self.tag = self._row(form, "&Tag:", "")
        self.health_combo = self._combo(
            form, "&Health:", ["(any)", "available", "broken", "moved", "changed"]
        )
        self.domain = self._row(form, "&Domain:", "")
        self.has_note = wx.CheckBox(self, label="Has &note")
        _name(self.has_note, "Has note")
        form.Add(self.has_note, 0, wx.ALIGN_CENTER_VERTICAL)
        form.AddSpacer(0)

        sizer.Add(form, 1, wx.EXPAND | wx.ALL, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        save_smart = wx.Button(self, label="Save as &Smart Collection")
        ok = wx.Button(self, label="&Search", id=wx.ID_OK)
        cancel = wx.Button(self, label="Cancel", id=wx.ID_CANCEL)
        for b in (save_smart, ok, cancel):
            _name(b, b.GetLabel().replace("&", ""))
        ok.SetDefault()
        buttons.Add(save_smart, 0, wx.RIGHT, 8)
        buttons.AddStretchSpacer(1)
        buttons.Add(ok, 0, wx.RIGHT, 8)
        buttons.Add(cancel, 0)
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.all_words.SetFocus()

        ok.Bind(wx.EVT_BUTTON, lambda _e: self._build(save_smart=False))
        save_smart.Bind(wx.EVT_BUTTON, lambda _e: self._build(save_smart=True))
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)

    def _row(self, sizer, label, value) -> wx.TextCtrl:
        lbl = wx.StaticText(self, label=label)
        ctrl = wx.TextCtrl(self, value=value, size=(320, -1))
        _name(ctrl, label.replace("&", "").replace(":", "").strip())
        sizer.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(ctrl, 1, wx.EXPAND)
        return ctrl

    def _combo(self, sizer, label, choices) -> wx.ComboBox:
        lbl = wx.StaticText(self, label=label)
        combo = wx.ComboBox(self, choices=choices, style=wx.CB_READONLY)
        combo.SetSelection(0)
        _name(combo, label.replace("&", "").replace(":", "").strip())
        sizer.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(combo, 1, wx.EXPAND)
        return combo

    def _build(self, *, save_smart: bool) -> None:
        parts: list[str] = []
        if self.all_words.GetValue().strip():
            parts.append(self.all_words.GetValue().strip())
        if self.phrase.GetValue().strip():
            parts.append(f'"{self.phrase.GetValue().strip()}"')
        if self.exclude.GetValue().strip():
            for w in self.exclude.GetValue().split():
                parts.append(f"not:{w}")
        t = self.type_combo.GetValue()
        if t and t != "(any)":
            parts.append(f"type:{t}")
        if self.collection.GetValue().strip():
            parts.append(f'collection:"{self.collection.GetValue().strip()}"')
        if self.tag.GetValue().strip():
            parts.append(f"tag:{self.tag.GetValue().strip()}")
        h = self.health_combo.GetValue()
        if h and h != "(any)":
            parts.append(f"health:{h}")
        if self.domain.GetValue().strip():
            parts.append(f"domain:{self.domain.GetValue().strip()}")
        if self.has_note.IsChecked():
            parts.append("has:note")
        self._result = " ".join(parts)
        self.EndModal(wx.ID_OK if not save_smart else wx.ID_YES)

    def result(self) -> str | None:
        return self._result


class CollectionEditorDialog(wx.Dialog):
    """Create or edit a Collection (PRD 16.1).

    Accessible form: name, description, parent (optional), sharing, color.
    Returns a dict of fields, or None on cancel. When ``collection`` is given
    the form is pre-filled for editing.
    """

    def __init__(self, parent, *, collection=None, existing_names: list[str] | None = None):
        super().__init__(
            parent, title="Collection Editor", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._result: dict | None = None
        self._existing = set(existing_names or [])
        editing = collection is not None
        self._editing_id = collection.collection_id if editing else None
        if editing:
            self._existing.discard(collection.name)

        sizer = wx.BoxSizer(wx.VERTICAL)
        form = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
        form.AddGrowableCol(1, proportion=1)

        self.name = self._row(form, "&Name:", collection.name if editing else "")
        self.description = self._row(
            form,
            "&Description:",
            collection.description if editing else "",
            style=wx.TE_MULTILINE,
            size=(320, 60),
        )
        self.parent = self._row(
            form, "&Parent collection (optional):", (collection.parent_id or "") if editing else ""
        )
        self.sharing = self._combo(
            form, "&Sharing:", ["private", "shared"], (collection.sharing if editing else "private")
        )
        self.color = self._row(
            form, "&Color (name or hex, optional):", collection.color if editing else ""
        )

        sizer.Add(form, 1, wx.EXPAND | wx.ALL, 10)

        buttons = self._buttons("&Save", cancel=True)
        sizer.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.name.SetFocus()
        self.FindWindowByName("Save").Bind(wx.EVT_BUTTON, self._done)
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL)

    def _done(self, _e) -> None:
        name = self.name.GetValue().strip()
        if not name:
            show_message_box("Enter a collection name.", "QuillBeacon", style=wx.ICON_WARNING)
            self.name.SetFocus()
            return
        if name in self._existing:
            show_message_box(
                f"A collection named {name} already exists.", "QuillBeacon", style=wx.ICON_WARNING
            )
            self.name.SetFocus()
            return
        self._result = {
            "collection_id": self._editing_id,
            "name": name,
            "description": self.description.GetValue().strip(),
            "parent_id": self.parent.GetValue().strip() or None,
            "sharing": self.sharing.GetValue(),
            "color": self.color.GetValue().strip(),
        }
        if self.IsModal():
            self.EndModal(wx.ID_OK)

    def result(self) -> dict | None:
        return self._result

    # shared row/combo/button helpers (same shape as BuildSearchDialog)
    def _row(self, sizer, label, value, *, style=0, size=None) -> wx.TextCtrl:
        lbl = wx.StaticText(self, label=label)
        ctrl = wx.TextCtrl(self, value=value, style=style, size=size or (320, -1))
        _name(ctrl, label.replace("&", "").replace(":", "").strip())
        sizer.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(ctrl, 1, wx.EXPAND)
        return ctrl

    def _combo(self, sizer, label, choices, value) -> wx.ComboBox:
        lbl = wx.StaticText(self, label=label)
        combo = wx.ComboBox(self, choices=choices, style=wx.CB_READONLY)
        if value in choices:
            combo.SetValue(value)
        _name(combo, label.replace("&", "").replace(":", "").strip())
        sizer.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(combo, 1, wx.EXPAND)
        return combo

    def _buttons(self, save_label, *, cancel=False) -> wx.Sizer:
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        save = wx.Button(self, label=save_label)
        save.SetName("Save")
        _name(save, save_label.replace("&", ""))
        save.SetDefault()
        buttons.Add(save, 0, wx.RIGHT, 8)
        if cancel:
            c = wx.Button(self, label="Cancel", id=wx.ID_CANCEL)
            _name(c, "Cancel")
            buttons.Add(c, 0)
        return buttons


class PublishDialog(wx.Dialog):
    """Publish a collection as a read-only web page (plan section 12).

    Shows the published state and preview URL for one collection, with
    Publish / Unpublish / Copy URL / Close buttons. The dialog performs the
    publish and unpublish actions itself through the supplied manager so the
    preview URL updates in place after publishing. Every control has an
    accessible name; the URL field is a read-only TextCtrl with an associated
    label so screen readers announce it.
    """

    def __init__(self, parent, *, publisher, collection_name: str, port: int | None):
        super().__init__(
            parent, title="Publish Collection", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._publisher = publisher
        self._name = collection_name
        self._port = port

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Collection name (read-only label).
        name_lbl = wx.StaticText(self, label=f"Collection: {collection_name}")
        _name(name_lbl, "Collection name")
        sizer.Add(name_lbl, 0, wx.ALL, 10)

        # Status line.
        self.status = wx.StaticText(self, label="")
        _name(self.status, "Publish status")
        sizer.Add(self.status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Preview URL field with an associated label.
        url_box = wx.BoxSizer(wx.HORIZONTAL)
        url_lbl = wx.StaticText(self, label="Preview &URL:")
        _name(url_lbl, "Preview URL")
        self.url = wx.TextCtrl(self, value="", style=wx.TE_READONLY, size=(420, -1))
        self.url.SetName("Preview URL")
        url_box.Add(url_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        url_box.Add(self.url, 1, wx.EXPAND)
        sizer.Add(url_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        # Buttons.
        btns = wx.BoxSizer(wx.HORIZONTAL)
        self.publish_btn = wx.Button(self, label="&Publish")
        _name(self.publish_btn, "Publish")
        self.unpublish_btn = wx.Button(self, label="&Unpublish")
        _name(self.unpublish_btn, "Unpublish")
        self.copy_btn = wx.Button(self, label="Copy &URL")
        _name(self.copy_btn, "Copy URL")
        close_btn = wx.Button(self, label="&Close", id=wx.ID_CANCEL)
        _name(close_btn, "Close")
        btns.Add(self.publish_btn, 0, wx.RIGHT, 8)
        btns.Add(self.unpublish_btn, 0, wx.RIGHT, 8)
        btns.Add(self.copy_btn, 0, wx.RIGHT, 8)
        btns.Add(close_btn, 0)
        sizer.Add(btns, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.SetSizer(sizer)
        sizer.Fit(self)

        self.publish_btn.Bind(wx.EVT_BUTTON, self._on_publish)
        self.unpublish_btn.Bind(wx.EVT_BUTTON, self._on_unpublish)
        self.copy_btn.Bind(wx.EVT_BUTTON, self._on_copy)
        self._refresh_state()
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL)

    def _current_manifest(self) -> dict | None:
        for item in self._publisher.list_published():
            if item.get("name") == self._name:
                return item
        return None

    def _refresh_state(self) -> None:
        m = self._current_manifest()
        if m:
            count = m.get("count", 0)
            self.status.SetLabel(f"Published. {count} item{'s' if count != 1 else ''}.")
            token = m.get("token", "")
            if self._port and token:
                self.url.SetValue(f"http://127.0.0.1:{self._port}/published/{token}/")
            else:
                self.url.SetValue("(start the capture bridge to preview)")
            self.publish_btn.Enable()
            self.unpublish_btn.Enable()
            self.copy_btn.Enable(bool(self._port and token))
        else:
            self.status.SetLabel("Not published.")
            self.url.SetValue("")
            self.publish_btn.Enable()
            self.unpublish_btn.Disable()
            self.copy_btn.Disable()

    def _on_publish(self, _e) -> None:
        res = self._publisher.publish(self._name, port=self._port)
        if res.get("ok"):
            self._refresh_state()
            show_message_box(
                f"Published {res['count']} item(s).\n\n"
                f"Preview: {res.get('preview_url') or '(start the capture bridge)'}",
                "QuillBeacon",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
        else:
            show_message_box(
                res.get("error", "publish failed"), "QuillBeacon", wx.OK | wx.ICON_WARNING, self
            )

    def _on_unpublish(self, _e) -> None:
        res = self._publisher.unpublish(self._name)
        if res.get("ok"):
            self._refresh_state()
        else:
            show_message_box(
                res.get("error", "unpublish failed"), "QuillBeacon", wx.OK | wx.ICON_WARNING, self
            )

    def _on_copy(self, _e) -> None:
        url = self.url.GetValue()
        if not url or url.startswith("("):
            return
        if wx.TheClipboard and wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(url))
            wx.TheClipboard.Close()


class TrailEditorDialog(wx.Dialog):
    """Create or edit a Trail -- an ordered learning path (PRD 16.3).

    A trail is a title, description, and an ordered list of steps. Each step
    references a beacon by id with a note and a completed flag. The editor
    presents steps as an editable list (add/remove/reorder) plus a note field.
    """

    def __init__(self, parent, store, *, trail=None):
        super().__init__(
            parent, title="Trail Editor", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._store = store
        self._result: dict | None = None
        editing = trail is not None
        # steps: list of {beacon_id, note, completed}
        self._steps = list(trail.steps) if editing else []
        self._trail_id = trail.trail_id if editing else None

        sizer = wx.BoxSizer(wx.VERTICAL)
        form = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
        form.AddGrowableCol(1, proportion=1)
        self.title = self._row(form, "&Title:", trail.title if editing else "")
        self.description = self._row(
            form,
            "&Description:",
            trail.description if editing else "",
            style=wx.TE_MULTILINE,
            size=(360, 60),
        )
        sizer.Add(form, 1, wx.EXPAND | wx.ALL, 10)

        steps_box = wx.StaticBoxSizer(wx.VERTICAL, self, "&Steps")
        self.step_list = wx.ListBox(steps_box.GetStaticBox(), style=wx.LB_SINGLE)
        _name(self.step_list, "Trail steps. Select to edit note or remove.")
        steps_box.Add(self.step_list, 1, wx.EXPAND | wx.ALL, 6)
        self._refresh_step_list()
        sizer.Add(steps_box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        step_row = wx.BoxSizer(wx.HORIZONTAL)
        self.step_note = wx.TextCtrl(self, size=(240, -1))
        _name(self.step_note, "Note for the selected step")
        step_row.Add(self.step_note, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        add_btn = wx.Button(self, label="&Add Selected Beacon")
        _name(add_btn, "Add selected beacon as a step")
        step_row.Add(add_btn, 0, wx.RIGHT, 6)
        up_btn = wx.Button(self, label="&Up")
        _name(up_btn, "Move step up")
        down_btn = wx.Button(self, label="&Down")
        _name(down_btn, "Move step down")
        rm_btn = wx.Button(self, label="&Remove")
        _name(rm_btn, "Remove selected step")
        for b in (up_btn, down_btn, rm_btn):
            step_row.Add(b, 0, wx.RIGHT, 6)
        sizer.Add(step_row, 0, wx.EXPAND | wx.ALL, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        save = wx.Button(self, label="&Save")
        _name(save, "Save")
        save.SetDefault()
        cancel = wx.Button(self, label="Cancel", id=wx.ID_CANCEL)
        _name(cancel, "Cancel")
        buttons.Add(save, 0, wx.RIGHT, 8)
        buttons.Add(cancel, 0)
        sizer.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.title.SetFocus()

        add_btn.Bind(wx.EVT_BUTTON, self._on_add_step)
        up_btn.Bind(wx.EVT_BUTTON, lambda _e: self._move(-1))
        down_btn.Bind(wx.EVT_BUTTON, lambda _e: self._move(1))
        rm_btn.Bind(wx.EVT_BUTTON, self._on_remove_step)
        save.Bind(wx.EVT_BUTTON, self._done)
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL)

    def _row(self, sizer, label, value, *, style=0, size=None) -> wx.TextCtrl:
        lbl = wx.StaticText(self, label=label)
        ctrl = wx.TextCtrl(self, value=value, style=style, size=size or (320, -1))
        _name(ctrl, label.replace("&", "").replace(":", "").strip())
        sizer.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(ctrl, 1, wx.EXPAND)
        return ctrl

    def _refresh_step_list(self) -> None:
        self.step_list.Clear()
        for i, st in enumerate(self._steps):
            b = self._store.get_beacon(st.get("beacon_id", ""))
            label = b.title if b else st.get("beacon_id", "?")
            mark = "[done] " if st.get("completed") else ""
            self.step_list.Append(f"{i + 1}. {mark}{label}")

    def _on_add_step(self, _e) -> None:
        # Use the parent shell's currently selected beacon, if reachable.
        parent = self.GetParent()
        sel = getattr(parent, "_selected_beacon", lambda: None)()
        if sel is None:
            show_message_box(
                "Select a beacon in the main list first, then Add.",
                "QuillBeacon",
                style=wx.ICON_INFORMATION,
            )
            return
        self._steps.append({
            "beacon_id": sel.beacon_id,
            "note": self.step_note.GetValue().strip(),
            "completed": False,
        })
        self.step_note.Clear()
        self._refresh_step_list()

    def _move(self, delta: int) -> None:
        i = self.step_list.GetSelection()
        if i < 0:
            return
        j = i + delta
        if 0 <= j < len(self._steps):
            self._steps[i], self._steps[j] = self._steps[j], self._steps[i]
            self._refresh_step_list()
            self.step_list.SetSelection(j)

    def _on_remove_step(self, _e) -> None:
        i = self.step_list.GetSelection()
        if i < 0:
            return
        del self._steps[i]
        self._refresh_step_list()

    def _done(self, _e) -> None:
        title = self.title.GetValue().strip()
        if not title:
            show_message_box("Enter a trail title.", "QuillBeacon", style=wx.ICON_WARNING)
            self.title.SetFocus()
            return
        self._result = {
            "trail_id": self._trail_id,
            "title": title,
            "description": self.description.GetValue().strip(),
            "steps": list(self._steps),
        }
        self.EndModal(wx.ID_OK)

    def result(self) -> dict | None:
        return self._result


class RepairReviewDialog(wx.Dialog):
    """Broken-location repair review (PRD 17.4).

    When a ULD resolves at low confidence or not at all, this dialog shows the
    user the previous saved location versus the proposed repair and asks them
    to choose: accept the repair, keep the old location, or mark the beacon
    broken for later. It never silently rewrites an exact bookmark.
    """

    ACCEPT_REPAIR = "accept"
    KEEP_OLD = "keep"
    MARK_BROKEN = "broken"

    def __init__(self, parent, *, beacon_title: str, suggestion: dict):
        super().__init__(
            parent, title="Review Location Repair", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._choice: str | None = None
        self._suggestion = suggestion

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label=f"Beacon: {beacon_title}"), 0, wx.ALL, 10)

        info = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2, size=(420, 160)
        )
        _name(info, "Repair details. Previous location and proposed repair.")
        info.SetValue(self._format(suggestion))
        sizer.Add(info, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        accept = wx.Button(self, label="&Accept Repair")
        keep = wx.Button(self, label="&Keep Old Location")
        broken = wx.Button(self, label="Mark &Broken for Later")
        cancel = wx.Button(self, label="Cancel", id=wx.ID_CANCEL)
        for b in (accept, keep, broken, cancel):
            _name(b, b.GetLabel().replace("&", ""))
        accept.SetDefault()
        for b in (accept, keep, broken):
            buttons.Add(b, 0, wx.RIGHT, 8)
        buttons.Add(cancel, 0)
        sizer.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        self.SetSizer(sizer)
        sizer.Fit(self)
        accept.Bind(wx.EVT_BUTTON, lambda _e: self._choose(self.ACCEPT_REPAIR))
        keep.Bind(wx.EVT_BUTTON, lambda _e: self._choose(self.KEEP_OLD))
        broken.Bind(wx.EVT_BUTTON, lambda _e: self._choose(self.MARK_BROKEN))
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL)

    def _format(self, s: dict) -> str:
        lines = [
            f"Resolution layer: {s.get('layer', 'none')}",
            f"Confidence: {s.get('confidence', 0):.2f}",
            f"Status: {s.get('message', '')}",
            "",
            f"Previous summary: {s.get('previous_summary', '(none)')}",
            f"Previous heading path: {' > '.join(s.get('previous_heading_path') or [])}",
            f"Previous quote: {s.get('previous_quote', '') or '(none)'}",
            "",
            "Proposed position: " + str(s.get("position", {})),
        ]
        return "\n".join(lines)

    def _choose(self, choice: str) -> None:
        self._choice = choice
        self.EndModal(wx.ID_OK)

    def choice(self) -> str | None:
        return self._choice


class RadioProgramDialog(wx.Dialog):
    """Capture a radio program with schedule metadata (PRD 9.1, 44.3).

    Collects station, program, host, start/end times (HH:MM, 24h, optional),
    and an optional stream URL. Returns a dict, or None on cancel.
    """

    def __init__(self, parent):
        super().__init__(
            parent, title="Add Radio Program", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._result: dict | None = None

        sizer = wx.BoxSizer(wx.VERTICAL)
        form = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
        form.AddGrowableCol(1, proportion=1)
        self.station = self._row(form, "&Station:", "")
        self.program = self._row(form, "&Program:", "")
        self.host = self._row(form, "&Host (optional):", "")
        self.start = self._row(form, "&Start time (HH:MM, optional):", "")
        self.end = self._row(form, "&End time (HH:MM, optional):", "")
        self.url = self._row(form, "Stream &URL (optional):", "")
        sizer.Add(form, 1, wx.EXPAND | wx.ALL, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        save = wx.Button(self, label="&Save")
        _name(save, "Save")
        save.SetDefault()
        cancel = wx.Button(self, label="Cancel", id=wx.ID_CANCEL)
        _name(cancel, "Cancel")
        buttons.Add(save, 0, wx.RIGHT, 8)
        buttons.Add(cancel, 0)
        sizer.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.station.SetFocus()
        save.Bind(wx.EVT_BUTTON, self._done)
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL)

    def _row(self, sizer, label, value) -> wx.TextCtrl:
        lbl = wx.StaticText(self, label=label)
        ctrl = wx.TextCtrl(self, value=value, size=(320, -1))
        _name(ctrl, label.replace("&", "").replace(":", "").strip())
        sizer.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(ctrl, 1, wx.EXPAND)
        return ctrl

    def _done(self, _e) -> None:
        if not self.station.GetValue().strip() and not self.program.GetValue().strip():
            show_message_box(
                "Enter a station or program name.", "QuillBeacon", style=wx.ICON_WARNING
            )
            self.station.SetFocus()
            return
        self._result = {
            "station": self.station.GetValue().strip(),
            "program": self.program.GetValue().strip(),
            "host": self.host.GetValue().strip(),
            "start": self.start.GetValue().strip(),
            "end": self.end.GetValue().strip(),
            "url": self.url.GetValue().strip(),
        }
        self.EndModal(wx.ID_OK)

    def result(self) -> dict | None:
        return self._result


def parse_hhmm(value: str) -> int | None:
    """Parse HH:MM (24h) to epoch-ms-of-day. Returns None if blank/invalid."""
    if not value:
        return None
    parts = value.split(":")
    if len(parts) != 2:
        return None
    try:
        h, m = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if not (0 <= h < 24 and 0 <= m < 60):
        return None
    return (h * 3600 + m * 60) * 1000


class StatusCenterDialog(wx.Dialog):
    """Status center: one place to hear how capture, sync, and health are (PRD 13.4).

    Pulls current status from the shell via a small ``status()`` callable that
    returns a list of (label, value) pairs, so the dialog stays a view. Every
    line is also announced via the parent's announcer for screen-reader users.
    """

    def __init__(self, parent, *, status_provider, announcer=None):
        super().__init__(
            parent, title="Status Center", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._provider = status_provider
        self._announcer = announcer

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.text = wx.TextCtrl(
            self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2, size=(420, 240)
        )
        _name(self.text, "Status center. Capture bridge, sync, and library health.")
        sizer.Add(self.text, 1, wx.EXPAND | wx.ALL, 10)

        refresh = wx.Button(self, label="&Refresh")
        _name(refresh, "Refresh status")
        close = wx.Button(self, label="&Close", id=wx.ID_CLOSE)
        _name(close, "Close")
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.Add(refresh, 0, wx.RIGHT, 8)
        buttons.AddStretchSpacer(1)
        buttons.Add(close, 0)
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(sizer)
        sizer.Fit(self)
        refresh.Bind(wx.EVT_BUTTON, lambda _e: self._refresh())
        self._refresh()
        apply_modal_ids(self, escape_id=wx.ID_CLOSE)

    def _refresh(self) -> None:
        try:
            rows = self._provider() or []
        except Exception as ex:
            rows = [("error", str(ex))]
        lines = [f"{label}: {value}" for label, value in rows]
        body = "\n".join(lines) or "No status available."
        self.text.SetValue(body)
        if self._announcer:
            self._announcer(body, "verbose")


class PreferencesDialog(wx.Dialog):
    """Unified Preferences hub (Ctrl+Comma).

    A left list of sections selects one of four right-hand panels:
    Accessibility, Sync, Capture Bridge, and Published Pages. Inline-editable
    settings (accessibility fields and the auto-sync interval) are collected
    and returned on Apply; heavier actions (Sync Settings, Sync Now, copy
    bridge token, unpublish a page) delegate to the parent frame immediately.

    Every control has an accessible name; the section list and each panel are
    named regions. Tab order runs section list -> panel controls -> Apply/Cancel.
    """

    SECTIONS = ["Accessibility", "Sync", "Capture Bridge", "Published Pages", "Routing Rules"]

    def __init__(self, parent, frame):
        super().__init__(
            parent, title="Preferences", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._frame = frame
        self._result = None
        from quill.apps.beacon.a11y import SCALE_STEPS

        self._scale_steps = SCALE_STEPS

        outer = wx.BoxSizer(wx.VERTICAL)
        body = wx.BoxSizer(wx.HORIZONTAL)

        # Left: section list.
        self.sections = wx.ListBox(self, choices=self.SECTIONS, size=(160, -1))
        _name(self.sections, "Preferences sections")
        self.sections.SetSelection(0)
        body.Add(self.sections, 0, wx.EXPAND | wx.ALL, 10)

        # Right: a stack of panels; only the selected one is shown.
        self._panels = {}
        right = wx.BoxSizer(wx.VERTICAL)
        self._panels["Accessibility"] = self._build_a11y_panel()
        self._panels["Sync"] = self._build_sync_panel()
        self._panels["Capture Bridge"] = self._build_bridge_panel()
        self._panels["Published Pages"] = self._build_publish_panel()
        self._panels["Routing Rules"] = self._build_routing_panel()
        for name in self.SECTIONS:
            panel = self._panels[name]
            right.Add(panel, 1, wx.EXPAND | wx.ALL, 10)
            panel.Show(name == self.SECTIONS[0])
            panel.SetName(f"{name} preferences")
        body.Add(right, 1, wx.EXPAND | wx.TOP | wx.RIGHT | wx.BOTTOM, 10)
        outer.Add(body, 1, wx.EXPAND)

        # Bottom: Apply / Cancel.
        btns = wx.BoxSizer(wx.HORIZONTAL)
        apply_btn = wx.Button(self, label="&Apply")
        _name(apply_btn, "Apply")
        apply_btn.SetDefault()
        cancel_btn = wx.Button(self, label="&Cancel", id=wx.ID_CANCEL)
        _name(cancel_btn, "Cancel")
        btns.Add(apply_btn, 0, wx.RIGHT, 8)
        btns.Add(cancel_btn, 0)
        outer.Add(btns, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.SetSizer(outer)
        outer.Fit(self)
        self.sections.SetFocus()
        self.sections.Bind(wx.EVT_LISTBOX, self._on_section)
        apply_btn.Bind(wx.EVT_BUTTON, self._on_apply)
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL)

    # -- panels ---------------------------------------------------------------

    def _label(self, parent, text):
        lbl = wx.StaticText(parent, label=text)
        _name(lbl, text.replace("&", "").replace(":", "").strip())
        return lbl

    def _build_a11y_panel(self):
        from quill.apps.beacon.a11y import SCALE_STEPS

        s = self._frame.a11y
        p = wx.Panel(self)
        v = wx.BoxSizer(wx.VERTICAL)
        form = wx.FlexGridSizer(cols=2, vgap=8, hgap=8)
        form.AddGrowableCol(1, proportion=1)

        form.Add(self._label(p, "Announcement &verbosity:"))
        self.verbosity = wx.ComboBox(
            p, choices=["minimal", "normal", "verbose"], style=wx.CB_READONLY
        )
        self.verbosity.SetValue(s.verbosity)
        _name(self.verbosity, "Announcement verbosity")
        form.Add(self.verbosity, 1, wx.EXPAND)

        form.Add(self._label(p, "&High contrast:"))
        self.high_contrast = wx.CheckBox(p)
        self.high_contrast.SetValue(s.high_contrast)
        _name(self.high_contrast, "High contrast")
        form.Add(self.high_contrast, 1, wx.EXPAND)

        form.Add(self._label(p, "&Text scale:"))
        self.scale = wx.ComboBox(
            p, choices=[f"{int(x * 100)}%" for x in SCALE_STEPS], style=wx.CB_READONLY
        )
        self.scale.SetSelection(s.scale_index)
        _name(self.scale, "Text scale")
        form.Add(self.scale, 1, wx.EXPAND)

        form.Add(self._label(p, "&Reduced motion:"))
        self.reduced_motion = wx.CheckBox(p)
        self.reduced_motion.SetValue(s.reduced_motion)
        _name(self.reduced_motion, "Reduced motion")
        form.Add(self.reduced_motion, 1, wx.EXPAND)

        v.Add(form, 1, wx.EXPAND)
        p.SetSizer(v)
        return p

    def _build_sync_panel(self):
        p = wx.Panel(self)
        v = wx.BoxSizer(wx.VERTICAL)
        cfg = self._frame.sync.config
        summary = (
            f"Transport: {cfg.transport}\n"
            f"Folder: {cfg.folder or '(not set)'}\n"
            f"Server: {cfg.server_url or '(not set)'}\n"
            f"Device: {cfg.device or '(not set)'}\n"
            f"Vault: {'unlocked' if self._frame.sync.is_unlocked() else 'locked'}"
        )
        self._sync_summary = wx.StaticText(p, label=summary)
        _name(self._sync_summary, "Sync status summary")
        v.Add(self._sync_summary, 0, wx.BOTTOM, 10)

        form = wx.FlexGridSizer(cols=2, vgap=8, hgap=8)
        form.AddGrowableCol(1, proportion=1)
        form.Add(self._label(p, "&Auto-sync interval:"))
        self.auto_sync = wx.ComboBox(
            p, choices=[label for label, _ in self._frame.AUTO_SYNC_CHOICES], style=wx.CB_READONLY
        )
        _name(self.auto_sync, "Auto-sync interval")
        for i, (_label, secs) in enumerate(self._frame.AUTO_SYNC_CHOICES):
            if secs == cfg.auto_sync_seconds:
                self.auto_sync.SetSelection(i)
                break
        if self.auto_sync.GetSelection() == wx.NOT_FOUND:
            self.auto_sync.SetSelection(0)
        form.Add(self.auto_sync, 1, wx.EXPAND)
        v.Add(form, 0, wx.EXPAND | wx.BOTTOM, 10)

        row = wx.BoxSizer(wx.HORIZONTAL)
        sync_settings_btn = wx.Button(p, label="Sync &Settings...")
        _name(sync_settings_btn, "Sync Settings")
        sync_now_btn = wx.Button(p, label="Sync &Now")
        _name(sync_now_btn, "Sync Now")
        sync_settings_btn.Bind(wx.EVT_BUTTON, self._on_sync_settings)
        sync_now_btn.Bind(wx.EVT_BUTTON, self._on_sync_now)
        row.Add(sync_settings_btn, 0, wx.RIGHT, 8)
        row.Add(sync_now_btn, 0)
        v.Add(row, 0)
        p.SetSizer(v)
        return p

    def _build_bridge_panel(self):
        p = wx.Panel(self)
        v = wx.BoxSizer(wx.VERTICAL)
        bridge = getattr(self._frame, "bridge", None)
        if bridge:
            url = bridge.base_url
            token = bridge.token
            status = "running"
        else:
            url = "(not running)"
            token = ""
            status = "not running"
        self._bridge_status = wx.StaticText(p, label=f"Capture bridge: {status}")
        _name(self._bridge_status, "Capture bridge status")
        v.Add(self._bridge_status, 0, wx.BOTTOM, 8)

        form = wx.FlexGridSizer(cols=2, vgap=8, hgap=8)
        form.AddGrowableCol(1, proportion=1)
        form.Add(self._label(p, "&Base URL:"))
        self.bridge_url = wx.TextCtrl(p, value=url, style=wx.TE_READONLY)
        _name(self.bridge_url, "Capture bridge base URL")
        form.Add(self.bridge_url, 1, wx.EXPAND)
        form.Add(self._label(p, "&Token:"))
        self.bridge_token = wx.TextCtrl(p, value=token, style=wx.TE_READONLY)
        _name(self.bridge_token, "Capture bridge token")
        form.Add(self.bridge_token, 1, wx.EXPAND)
        v.Add(form, 0, wx.EXPAND | wx.BOTTOM, 10)

        copy_btn = wx.Button(p, label="Copy &Token")
        _name(copy_btn, "Copy bridge token")
        copy_btn.Bind(wx.EVT_BUTTON, self._on_copy_token)
        v.Add(copy_btn, 0)
        p.SetSizer(v)
        return p

    def _build_publish_panel(self):
        p = wx.Panel(self)
        v = wx.BoxSizer(wx.VERTICAL)
        info = wx.StaticText(
            p,
            label="Publish a collection via Tools > Publish Collection "
            "(Ctrl+Shift+W). Unpublish a page here:",
        )
        _name(info, "Published pages info")
        v.Add(info, 0, wx.BOTTOM, 8)
        self._pub_list = wx.ListBox(p, size=(-1, 120))
        _name(self._pub_list, "Published pages list")
        v.Add(self._pub_list, 1, wx.EXPAND | wx.BOTTOM, 8)
        self._refresh_publish_list()
        unpublish_btn = wx.Button(p, label="&Unpublish Selected")
        _name(unpublish_btn, "Unpublish selected page")
        unpublish_btn.Bind(wx.EVT_BUTTON, self._on_unpublish)
        v.Add(unpublish_btn, 0)
        p.SetSizer(v)
        return p

    def _build_routing_panel(self):
        from quill.apps.beacon import routing

        p = wx.Panel(self)
        v = wx.BoxSizer(wx.VERTICAL)
        info = wx.StaticText(
            p,
            label="File new web bookmarks into a folder when their URL "
            "contains a keyword. The first matching rule in the list "
            "wins; each keyword can be used only once.",
        )
        info.Wrap(420)
        _name(info, "Routing rules info")
        v.Add(info, 0, wx.BOTTOM, 8)
        self._routing_list = wx.ListBox(p, size=(-1, 140))
        _name(self._routing_list, "Routing rules, ordered by priority")
        v.Add(self._routing_list, 1, wx.EXPAND | wx.BOTTOM, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        for label, name, handler in (
            ("A&dd Rule...", "Add routing rule", self._on_routing_add),
            ("Ed&it Rule...", "Edit routing rule", self._on_routing_edit),
            ("Re&move Rule", "Remove routing rule", self._on_routing_remove),
            ("Move U&p", "Move routing rule up", self._on_routing_up),
            ("Move Do&wn", "Move routing rule down", self._on_routing_down),
        ):
            btn = wx.Button(p, label=label)
            _name(btn, name)
            btn.Bind(wx.EVT_BUTTON, handler)
            row.Add(btn, 0, wx.RIGHT, 8)
        v.Add(row, 0)
        self._routing_rules = routing.load_rules(self._frame.data_dir)
        self._refresh_routing_list()
        p.SetSizer(v)
        return p

    # -- actions --------------------------------------------------------------

    def _on_section(self, _e) -> None:
        name = self.sections.GetStringSelection()
        for key, panel in self._panels.items():
            panel.Show(key == name)
        self.Layout()

    def _refresh_sync_summary(self) -> None:
        cfg = self._frame.sync.config
        self._sync_summary.SetLabel(
            f"Transport: {cfg.transport}\n"
            f"Folder: {cfg.folder or '(not set)'}\n"
            f"Server: {cfg.server_url or '(not set)'}\n"
            f"Device: {cfg.device or '(not set)'}\n"
            f"Vault: {'unlocked' if self._frame.sync.is_unlocked() else 'locked'}"
        )

    def _on_sync_settings(self, _e) -> None:
        self._frame._on_sync_settings(None)
        self._refresh_sync_summary()

    def _on_sync_now(self, _e) -> None:
        self._frame._on_sync_now(None)
        self._refresh_sync_summary()

    def _on_copy_token(self, _e) -> None:
        token = self.bridge_token.GetValue()
        if not token:
            return
        if wx.TheClipboard and wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(token))
            wx.TheClipboard.Close()

    def _refresh_publish_list(self) -> None:
        self._pub_list.Clear()
        self._pub_items = list(self._frame.publisher.list_published())
        for item in self._pub_items:
            self._pub_list.Append(f"{item.get('name', '?')} ({item.get('count', 0)})")

    def _on_unpublish(self, _e) -> None:
        sel = self._pub_list.GetSelection()
        if sel == wx.NOT_FOUND or sel >= len(self._pub_items):
            return
        name = self._pub_items[sel].get("name", "")
        self._frame.publisher.unpublish(name)
        self._refresh_publish_list()

    # -- routing rules ---------------------------------------------------------

    def _refresh_routing_list(self, select: int = -1) -> None:
        self._routing_list.Clear()
        for r in self._routing_rules:
            self._routing_list.Append(f"{r.keyword} files into {r.collection}")
        if 0 <= select < len(self._routing_rules):
            self._routing_list.SetSelection(select)

    def _commit_routing(self, rules, select: int) -> bool:
        """Validate + persist a candidate rule list; announce errors."""
        from quill.apps.beacon import routing

        error = routing.validate(rules)
        if error:
            show_message_box(error, "Routing Rules", style=wx.ICON_ERROR)
            return False
        routing.save_rules(self._frame.data_dir, rules)
        self._routing_rules = rules
        self._refresh_routing_list(select)
        return True

    def _routing_collections(self) -> list[str]:
        try:
            return [c.name for c in self._frame.store.list_collections()]
        except Exception:
            return []

    def _on_routing_add(self, _e) -> None:
        from quill.apps.beacon import routing

        dlg = RoutingRuleDialog(self, collections=self._routing_collections())
        if dlg.ShowModal() == wx.ID_OK and dlg.result():
            r = dlg.result()
            self._commit_routing(
                self._routing_rules + [routing.Rule(r["keyword"], r["collection"])],
                len(self._routing_rules),
            )
        dlg.Destroy()

    def _on_routing_edit(self, _e) -> None:
        from quill.apps.beacon import routing

        sel = self._routing_list.GetSelection()
        if sel == wx.NOT_FOUND or sel >= len(self._routing_rules):
            return
        rule = self._routing_rules[sel]
        dlg = RoutingRuleDialog(
            self,
            collections=self._routing_collections(),
            keyword=rule.keyword,
            collection=rule.collection,
        )
        if dlg.ShowModal() == wx.ID_OK and dlg.result():
            r = dlg.result()
            rules = list(self._routing_rules)
            rules[sel] = routing.Rule(r["keyword"], r["collection"])
            self._commit_routing(rules, sel)
        dlg.Destroy()

    def _on_routing_remove(self, _e) -> None:
        sel = self._routing_list.GetSelection()
        if sel == wx.NOT_FOUND or sel >= len(self._routing_rules):
            return
        rules = [r for i, r in enumerate(self._routing_rules) if i != sel]
        self._commit_routing(rules, min(sel, len(rules) - 1))

    def _on_routing_up(self, _e) -> None:
        self._routing_move(-1)

    def _on_routing_down(self, _e) -> None:
        self._routing_move(1)

    def _routing_move(self, delta: int) -> None:
        sel = self._routing_list.GetSelection()
        if sel == wx.NOT_FOUND or sel >= len(self._routing_rules):
            return
        target = sel + delta
        if not 0 <= target < len(self._routing_rules):
            return
        rules = list(self._routing_rules)
        rules[sel], rules[target] = rules[target], rules[sel]
        self._commit_routing(rules, target)

    def _on_apply(self, _e) -> None:
        secs = self._frame.AUTO_SYNC_CHOICES[self.auto_sync.GetSelection()][1]
        self._result = {
            "verbosity": self.verbosity.GetValue(),
            "high_contrast": self.high_contrast.IsChecked(),
            "scale_index": self.scale.GetSelection(),
            "reduced_motion": self.reduced_motion.IsChecked(),
            "auto_sync_seconds": secs,
        }
        if self.IsModal():
            self.EndModal(wx.ID_OK)

    def result(self) -> dict | None:
        return self._result


class RoutingRuleDialog(wx.Dialog):
    """Edit one routing rule: URL keyword and target folder (PRD 14.5)."""

    def __init__(
        self,
        parent,
        *,
        collections: list[str] | None = None,
        keyword: str = "",
        collection: str = "",
    ):
        super().__init__(
            parent, title="Routing Rule", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._result: dict | None = None

        sizer = wx.BoxSizer(wx.VERTICAL)
        form = wx.FlexGridSizer(cols=2, vgap=8, hgap=8)
        form.AddGrowableCol(1, proportion=1)

        lbl = wx.StaticText(self, label="URL &keyword (domain or text):")
        _name(lbl, "URL keyword")
        form.Add(lbl)
        self.keyword = wx.TextCtrl(self, value=keyword, size=(280, -1))
        _name(self.keyword, "URL keyword, a domain or any text the URL contains")
        form.Add(self.keyword, 1, wx.EXPAND)

        lbl = wx.StaticText(self, label="&Folder:")
        _name(lbl, "Folder")
        form.Add(lbl)
        self.collection = wx.ComboBox(self, value=collection, choices=list(collections or []))
        _name(self.collection, "Folder to file matching bookmarks into")
        form.Add(self.collection, 1, wx.EXPAND)

        sizer.Add(form, 1, wx.EXPAND | wx.ALL, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        ok = wx.Button(self, label="&Save")
        _name(ok, "Save rule")
        ok.SetDefault()
        cancel = wx.Button(self, label="&Cancel", id=wx.ID_CANCEL)
        _name(cancel, "Cancel")
        buttons.Add(ok, 0, wx.RIGHT, 8)
        buttons.Add(cancel, 0)
        sizer.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.keyword.SetFocus()
        ok.Bind(wx.EVT_BUTTON, self._on_ok)
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL)

    def _on_ok(self, _e) -> None:
        keyword = self.keyword.GetValue().strip()
        collection = self.collection.GetValue().strip()
        if not keyword or not collection:
            show_message_box(
                "Both a keyword and a folder are required.", "Routing Rule", style=wx.ICON_ERROR
            )
            return
        self._result = {"keyword": keyword, "collection": collection}
        if self.IsModal():
            self.EndModal(wx.ID_OK)

    def result(self) -> dict | None:
        return self._result


class A11ySettingsDialog(wx.Dialog):
    """Accessibility settings: verbosity, contrast, text scale, motion (PRD 29)."""

    def __init__(self, parent, settings):
        super().__init__(
            parent, title="Accessibility Settings", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        from quill.apps.beacon.a11y import SCALE_STEPS

        self._scale_steps = SCALE_STEPS
        self._result = None

        sizer = wx.BoxSizer(wx.VERTICAL)
        form = wx.FlexGridSizer(cols=2, vgap=8, hgap=8)
        form.AddGrowableCol(1, proportion=1)

        # Verbosity.
        form.Add(wx.StaticText(self, label="Announcement &verbosity:"))
        self.verbosity = wx.ComboBox(
            self, choices=["minimal", "normal", "verbose"], style=wx.CB_READONLY
        )
        self.verbosity.SetValue(settings.verbosity)
        _name(self.verbosity, "Announcement verbosity")
        form.Add(self.verbosity, 1, wx.EXPAND)

        # High contrast.
        form.Add(wx.StaticText(self, label="&High contrast:"))
        self.high_contrast = wx.CheckBox(self)
        self.high_contrast.SetValue(settings.high_contrast)
        _name(self.high_contrast, "High contrast")
        form.Add(self.high_contrast, 1, wx.EXPAND)

        # Text scale.
        form.Add(wx.StaticText(self, label="&Text scale:"))
        self.scale = wx.ComboBox(
            self, choices=[f"{int(s * 100)}%" for s in SCALE_STEPS], style=wx.CB_READONLY
        )
        self.scale.SetSelection(settings.scale_index)
        _name(self.scale, "Text scale")
        form.Add(self.scale, 1, wx.EXPAND)

        # Reduced motion.
        form.Add(wx.StaticText(self, label="&Reduced motion:"))
        self.reduced_motion = wx.CheckBox(self)
        self.reduced_motion.SetValue(settings.reduced_motion)
        _name(self.reduced_motion, "Reduced motion")
        form.Add(self.reduced_motion, 1, wx.EXPAND)

        sizer.Add(form, 1, wx.EXPAND | wx.ALL, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        save = wx.Button(self, label="&Apply")
        _name(save, "Apply")
        save.SetDefault()
        cancel = wx.Button(self, label="Cancel", id=wx.ID_CANCEL)
        _name(cancel, "Cancel")
        buttons.Add(save, 0, wx.RIGHT, 8)
        buttons.Add(cancel, 0)
        sizer.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.verbosity.SetFocus()
        save.Bind(wx.EVT_BUTTON, self._on_apply)
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL)

    def _on_apply(self, _e) -> None:
        self._result = {
            "verbosity": self.verbosity.GetValue(),
            "high_contrast": self.high_contrast.IsChecked(),
            "scale_index": self.scale.GetSelection(),
            "reduced_motion": self.reduced_motion.IsChecked(),
        }
        self.EndModal(wx.ID_OK)

    def result(self) -> dict | None:
        return self._result


class SmartCollectionsDialog(wx.Dialog):
    """Manage Smart Collections: edit or delete saved searches (PRD 15.6).

    A listbox of saved searches is the focal control; Edit opens an editor for
    the selected one, Delete removes it after confirmation. The dialog reads
    and writes through the store, so the shell sidebar can refresh on close.
    """

    def __init__(self, parent, store):
        super().__init__(
            parent, title="Smart Collections", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.store = store

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.list = wx.ListBox(self, size=(440, 200))
        _name(self.list, "Smart collections. Enter to edit, Delete to remove.")
        sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 10)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self.edit_btn = wx.Button(self, label="&Edit...")
        self.delete_btn = wx.Button(self, label="&Delete")
        close = wx.Button(self, label="&Close", id=wx.ID_CLOSE)
        for b in (self.edit_btn, self.delete_btn, close):
            _name(b, b.GetLabel().replace("&", ""))
        row.Add(self.edit_btn, 0, wx.RIGHT, 6)
        row.Add(self.delete_btn, 0, wx.RIGHT, 6)
        row.AddStretchSpacer(1)
        row.Add(close, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.edit_btn.Bind(wx.EVT_BUTTON, self._on_edit)
        self.delete_btn.Bind(wx.EVT_BUTTON, self._on_delete)
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self._on_edit(None))
        self._refresh()
        apply_modal_ids(self, escape_id=wx.ID_CLOSE)

    def _refresh(self) -> None:
        self.list.Clear()
        self._searches = self.store.list_saved_searches()
        for ss in self._searches:
            self.list.Append(f"{ss.name}  --  {ss.query}")
        if self._searches:
            self.list.SetSelection(0)

    def _selected(self):
        i = self.list.GetSelection()
        if i < 0 or i >= len(self._searches):
            return None
        return self._searches[i]

    def _on_edit(self, _e) -> None:
        ss = self._selected()
        if ss is None:
            show_message_box(
                "Select a smart collection first.", "Smart Collections", style=wx.ICON_INFORMATION
            )
            return
        dlg = SmartCollectionEditorDialog(self, saved_search=ss)
        if dlg.ShowModal() == wx.ID_OK and dlg.result():
            r = dlg.result()
            ss.name = r["name"]
            ss.query = r["query"]
            ss.sort = r["sort"]
            ss.scope_collection = r["scope_collection"]
            self.store.put_saved_search(ss)
            self._refresh()
        dlg.Destroy()

    def _on_delete(self, _e) -> None:
        ss = self._selected()
        if ss is None:
            show_message_box(
                "Select a smart collection first.", "Smart Collections", style=wx.ICON_INFORMATION
            )
            return
        confirm = show_message_box(
            f"Delete the smart collection '{ss.name}'? The bookmarks it matched are not affected.",
            "Smart Collections",
            style=wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
        )
        if confirm != wx.YES:
            return
        self.store.delete_saved_search(ss.search_id)
        self._refresh()


class SmartCollectionEditorDialog(wx.Dialog):
    """Edit a saved search's name, query, sort, and scope (PRD 15.6)."""

    SORTS = ["added", "title", "opened", "mostOpened", "type", "health", "relevance"]

    def __init__(self, parent, *, saved_search=None):
        super().__init__(
            parent,
            title="Smart Collection Editor",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._result: dict | None = None
        ss = saved_search

        sizer = wx.BoxSizer(wx.VERTICAL)
        form = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
        form.AddGrowableCol(1, proportion=1)

        form.Add(wx.StaticText(self, label="&Name:"))
        self.name = wx.TextCtrl(self, value=ss.name if ss else "", size=(320, -1))
        _name(self.name, "Smart collection name")
        form.Add(self.name, 1, wx.EXPAND)

        form.Add(wx.StaticText(self, label="&Query:"))
        self.query = wx.TextCtrl(self, value=ss.query if ss else "", size=(320, -1))
        _name(self.query, "Search query (Section 15 grammar)")
        form.Add(self.query, 1, wx.EXPAND)

        form.Add(wx.StaticText(self, label="&Sort:"))
        self.sort = wx.ComboBox(
            self, choices=self.SORTS, value=(ss.sort if ss else "added"), style=wx.CB_READONLY
        )
        _name(self.sort, "Sort order")
        form.Add(self.sort, 1, wx.EXPAND)

        form.Add(wx.StaticText(self, label="&Scope collection (optional):"))
        self.scope = wx.TextCtrl(self, value=ss.scope_collection if ss else "", size=(320, -1))
        _name(self.scope, "Scope collection")
        form.Add(self.scope, 1, wx.EXPAND)

        sizer.Add(form, 1, wx.EXPAND | wx.ALL, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        ok = wx.Button(self, label="&Save", id=wx.ID_OK)
        _name(ok, "Save")
        ok.SetDefault()
        cancel = wx.Button(self, label="Cancel", id=wx.ID_CANCEL)
        _name(cancel, "Cancel")
        buttons.AddStretchSpacer(1)
        buttons.Add(ok, 0, wx.RIGHT, 8)
        buttons.Add(cancel, 0)
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.name.SetFocus()
        ok.Bind(wx.EVT_BUTTON, self._on_save)
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)

    def _on_save(self, _e) -> None:
        name = self.name.GetValue().strip()
        query = self.query.GetValue().strip()
        if not name:
            show_message_box("Enter a name.", "Smart Collection", style=wx.ICON_WARNING)
            return
        if not query:
            show_message_box("Enter a query.", "Smart Collection", style=wx.ICON_WARNING)
            return
        self._result = {
            "name": name,
            "query": query,
            "sort": self.sort.GetValue() or "added",
            "scope_collection": self.scope.GetValue().strip(),
        }
        self.EndModal(wx.ID_OK)

    def result(self) -> dict | None:
        return self._result


class TrailStepDialog(wx.Dialog):
    """Step through a learning trail one beacon at a time (PRD 17.4).

    The listbox is the focal control: each step shows its order, completion,
    beacon title, and note. Previous/Next move the current step (persisted to
    the trail), Mark Complete toggles a step's completion, and Open Current
    hands the beacon back to the shell via a callback so the user can read it
    in place. Progress is announced for screen-reader users.
    """

    def __init__(self, parent, store, trail, *, on_open_beacon=None, announcer=None):
        super().__init__(
            parent,
            title=f"Trail -- {trail.title or trail.trail_id}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.store = store
        self.trail = trail
        self._on_open = on_open_beacon
        self._announcer = announcer

        sizer = wx.BoxSizer(wx.VERTICAL)
        if trail.description:
            desc = wx.StaticText(self, label=trail.description)
            _name(desc, "Trail description")
            sizer.Add(desc, 0, wx.EXPAND | wx.ALL, 10)

        self.progress = wx.StaticText(self, label=self._progress_label())
        _name(self.progress, "Trail progress")
        sizer.Add(self.progress, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        self.list = wx.ListBox(self, size=(440, 200))
        _name(self.list, "Trail steps. Enter to open the current step.")
        sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 10)

        note_box = wx.StaticBoxSizer(wx.VERTICAL, self, "Current step &note")
        self.note = wx.TextCtrl(
            note_box.GetStaticBox(),
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
            size=(440, 90),
        )
        _name(self.note, "Note for the current step")
        note_box.Add(self.note, 1, wx.EXPAND | wx.ALL, 4)
        sizer.Add(note_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self.prev_btn = wx.Button(self, label="&Previous")
        self.next_btn = wx.Button(self, label="&Next")
        self.complete_btn = wx.Button(self, label="&Mark Complete")
        self.open_btn = wx.Button(self, label="&Open Current")
        close = wx.Button(self, label="&Close", id=wx.ID_CLOSE)
        for b in (self.prev_btn, self.next_btn, self.complete_btn, self.open_btn, close):
            _name(b, b.GetLabel().replace("&", ""))
        row.Add(self.prev_btn, 0, wx.RIGHT, 6)
        row.Add(self.next_btn, 0, wx.RIGHT, 6)
        row.Add(self.complete_btn, 0, wx.RIGHT, 6)
        row.Add(self.open_btn, 0, wx.RIGHT, 6)
        row.AddStretchSpacer(1)
        row.Add(close, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.prev_btn.Bind(wx.EVT_BUTTON, lambda _e: self._step(-1))
        self.next_btn.Bind(wx.EVT_BUTTON, lambda _e: self._step(1))
        self.complete_btn.Bind(wx.EVT_BUTTON, self._on_toggle_complete)
        self.open_btn.Bind(wx.EVT_BUTTON, self._on_open_current)
        self.list.Bind(wx.EVT_LISTBOX, lambda _e: self._on_list_select())
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self._on_open_current(None))
        self._refresh()
        apply_modal_ids(self, escape_id=wx.ID_CLOSE)

    # -- helpers -------------------------------------------------------------

    def _completed_count(self) -> int:
        return sum(1 for s in self.trail.steps if s.get("completed"))

    def _progress_label(self) -> str:
        n = len(self.trail.steps)
        done = self._completed_count()
        cur = self.trail.current_step
        return f"Step {cur + 1} of {n}  |  {done} of {n} completed"

    def _step_label(self, idx: int) -> str:
        s = self.trail.steps[idx]
        b = self.store.get_beacon(s.get("beacon_id", "")) if s.get("beacon_id") else None
        title = b.title if b else "(missing beacon)"
        mark = "x" if s.get("completed") else " "
        cur = "*" if idx == self.trail.current_step else " "
        note = s.get("note") or ""
        if note and len(note) > 50:
            note = note[:50] + "..."
        return f"{cur}[{mark}] {idx + 1}. {title}" + (f" -- {note}" if note else "")

    def _refresh(self) -> None:
        self.list.Clear()
        for i in range(len(self.trail.steps)):
            self.list.Append(self._step_label(i))
        if self.trail.steps:
            self.list.SetSelection(self.trail.current_step)
        self.progress.SetLabel(self._progress_label())
        self._show_note()
        has = bool(self.trail.steps)
        self.prev_btn.Enable(has and self.trail.current_step > 0)
        self.next_btn.Enable(has and self.trail.current_step < len(self.trail.steps) - 1)
        self.complete_btn.Enable(has)
        self.open_btn.Enable(has)

    def _show_note(self) -> None:
        if not self.trail.steps:
            self.note.SetValue("")
            return
        s = self.trail.steps[self.trail.current_step]
        self.note.SetValue(s.get("note") or "(no note for this step)")

    def _announce(self, msg: str) -> None:
        if self._announcer:
            try:
                self._announcer(msg)
            except Exception:
                pass

    # -- actions -------------------------------------------------------------

    def _step(self, delta: int) -> None:
        if not self.trail.steps:
            return
        new = max(0, min(len(self.trail.steps) - 1, self.trail.current_step + delta))
        if new == self.trail.current_step:
            return
        self.trail.current_step = new
        self.store.put_trail(self.trail)
        self._refresh()
        self._announce(self._progress_label())

    def _on_list_select(self) -> None:
        i = self.list.GetSelection()
        if i < 0 or not self.trail.steps:
            return
        if i != self.trail.current_step:
            self.trail.current_step = i
            self.store.put_trail(self.trail)
        self._refresh()

    def _on_toggle_complete(self, _e) -> None:
        if not self.trail.steps:
            return
        s = self.trail.steps[self.trail.current_step]
        s["completed"] = not s.get("completed", False)
        self.store.put_trail(self.trail)
        self._refresh()
        self._announce(
            f"Step {self.trail.current_step + 1} "
            f"{'completed' if s['completed'] else 'not completed'}"
        )

    def _on_open_current(self, _e) -> None:
        if not self.trail.steps or not self._on_open:
            return
        s = self.trail.steps[self.trail.current_step]
        bid = s.get("beacon_id")
        if not bid:
            return
        self._on_open(bid)


class AttachmentsDialog(wx.Dialog):
    """List, add, view, and remove attachments on a beacon (PRD 24.1, 44.3).

    Attachments are local-only (never synced as blobs). Three kinds: a file on
    disk, a URL, or an inline note. The listbox is the focal control; every
    button has an accessible name and a clear keyboard path. Opening a file or
    URL uses the shell's default handler and is fail-safe (errors land in a
    message box, never a crash).
    """

    def __init__(self, parent, store, beacon_id: str, beacon_title: str = ""):
        super().__init__(
            parent,
            title=f"Attachments -- {beacon_title or beacon_id}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.store = store
        self.beacon_id = beacon_id

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.list = wx.ListBox(self, size=(420, 180))
        _name(self.list, "Attachments list")
        sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 10)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self.add_btn = wx.Button(self, label="&Add...")
        self.view_btn = wx.Button(self, label="&View")
        self.remove_btn = wx.Button(self, label="&Remove")
        close = wx.Button(self, label="&Close", id=wx.ID_CLOSE)
        for b in (self.add_btn, self.view_btn, self.remove_btn, close):
            _name(b, b.GetLabel().replace("&", ""))
        row.Add(self.add_btn, 0, wx.RIGHT, 6)
        row.Add(self.view_btn, 0, wx.RIGHT, 6)
        row.Add(self.remove_btn, 0, wx.RIGHT, 6)
        row.AddStretchSpacer(1)
        row.Add(close, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.add_btn.Bind(wx.EVT_BUTTON, self._on_add)
        self.view_btn.Bind(wx.EVT_BUTTON, self._on_view)
        self.remove_btn.Bind(wx.EVT_BUTTON, self._on_remove)
        self.list.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self._on_view(None))
        self._refresh()
        apply_modal_ids(self, escape_id=wx.ID_CLOSE)

    def _refresh(self) -> None:
        self.list.Clear()
        self._attachments = self.store.attachments_for(self.beacon_id)
        for att in self._attachments:
            self.list.Append(self._label(att))
        if self._attachments:
            self.list.SetSelection(0)

    @staticmethod
    def _label(att) -> str:
        kind = att.kind
        if kind == "note":
            preview = (att.content or "").replace("\n", " ")
            if len(preview) > 60:
                preview = preview[:60] + "..."
            return f"[note] {att.name or preview}"
        if kind == "url":
            return f"[url] {att.name or att.uri}"
        return f"[file] {att.name or att.uri}"

    def _selected(self):
        i = self.list.GetSelection()
        if i < 0 or i >= len(self._attachments):
            return None
        return self._attachments[i]

    def _on_add(self, _e) -> None:
        dlg = AttachmentAddDialog(self)
        if dlg.ShowModal() != wx.ID_OK or not dlg.result():
            dlg.Destroy()
            return
        r = dlg.result()
        dlg.Destroy()
        from quill.apps.beacon.model import Attachment

        att = Attachment(
            beacon_id=self.beacon_id,
            name=r["name"],
            kind=r["kind"],
            uri=r.get("uri", ""),
            content=r.get("content", ""),
            mime=r.get("mime", ""),
            size=r.get("size", 0),
        )
        self.store.put_attachment(att)
        self._refresh()

    def _on_view(self, _e) -> None:
        att = self._selected()
        if att is None:
            show_message_box(
                "Select an attachment first.", "Attachments", style=wx.ICON_INFORMATION
            )
            return
        if att.kind == "note":
            dlg = wx.MessageDialog(
                self, att.content or "(empty note)", att.name or "Note", style=wx.OK | wx.CENTRE
            )
            _name(dlg, "Attachment note contents")
            dlg.ShowModal()
            dlg.Destroy()
            return
        # file or url -> hand to the OS default handler, fail-safe.
        target = att.uri
        if not target:
            show_message_box(
                "This attachment has no path or URL.", "Attachments", style=wx.ICON_WARNING
            )
            return
        try:
            import webbrowser

            if att.kind == "url":
                webbrowser.open(target)
            else:
                # local file
                import os

                if os.name == "nt":
                    os.startfile(target)  # type: ignore[attr-defined]
                else:
                    webbrowser.open(f"file:///{target}")
        except Exception as ex:
            show_message_box(f"Could not open: {ex}", "Attachments", style=wx.ICON_ERROR)

    def _on_remove(self, _e) -> None:
        att = self._selected()
        if att is None:
            show_message_box(
                "Select an attachment first.", "Attachments", style=wx.ICON_INFORMATION
            )
            return
        confirm = show_message_box(
            f"Remove '{att.name or att.kind}'?",
            "Attachments",
            style=wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
        )
        if confirm != wx.YES:
            return
        self.store.delete_attachment(att.attachment_id)
        self._refresh()


class AttachmentAddDialog(wx.Dialog):
    """Add one attachment: choose kind, then fill the relevant field."""

    def __init__(self, parent):
        super().__init__(
            parent, title="Add Attachment", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._result: dict | None = None

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.kind_file = wx.RadioButton(self, label="&File on disk", style=wx.RB_GROUP)
        self.kind_url = wx.RadioButton(self, label="&URL")
        self.kind_note = wx.RadioButton(self, label="&Note (inline text)")
        for r in (self.kind_file, self.kind_url, self.kind_note):
            _name(r, r.GetLabel().replace("&", ""))
            sizer.Add(r, 0, wx.ALL, 4)

        form = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
        form.AddGrowableCol(1, proportion=1)
        form.Add(wx.StaticText(self, label="&Name:"))
        self.name = wx.TextCtrl(self, size=(300, -1))
        _name(self.name, "Attachment name")
        form.Add(self.name, 1, wx.EXPAND)
        sizer.Add(form, 0, wx.EXPAND | wx.ALL, 8)

        self.path_label = wx.StaticText(self, label="&Path:")
        self.path = wx.TextCtrl(self, size=(360, -1))
        _name(self.path, "File path")
        self.browse = wx.Button(self, label="&Browse...")
        _name(self.browse, "Browse for file")
        prow = wx.BoxSizer(wx.HORIZONTAL)
        prow.Add(self.path, 1, wx.EXPAND | wx.RIGHT, 6)
        prow.Add(self.browse, 0)
        sizer.Add(self.path_label, 0, wx.LEFT | wx.TOP, 8)
        sizer.Add(prow, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        self.url_label = wx.StaticText(self, label="&URL:")
        self.url = wx.TextCtrl(self, size=(360, -1))
        _name(self.url, "Attachment URL")
        sizer.Add(self.url_label, 0, wx.LEFT | wx.TOP, 8)
        sizer.Add(self.url, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        self.note_label = wx.StaticText(self, label="&Note text:")
        self.note = wx.TextCtrl(self, size=(360, 120), style=wx.TE_MULTILINE)
        _name(self.note, "Attachment note text")
        sizer.Add(self.note_label, 0, wx.LEFT | wx.TOP, 8)
        sizer.Add(self.note, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        ok = wx.Button(self, label="&OK", id=wx.ID_OK)
        _name(ok, "OK")
        ok.SetDefault()
        cancel = wx.Button(self, label="Cancel", id=wx.ID_CANCEL)
        _name(cancel, "Cancel")
        buttons.AddStretchSpacer(1)
        buttons.Add(ok, 0, wx.RIGHT, 8)
        buttons.Add(cancel, 0)
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self._update_visibility()
        for r in (self.kind_file, self.kind_url, self.kind_note):
            r.Bind(wx.EVT_RADIOBUTTON, lambda _e: self._update_visibility())
        self.browse.Bind(wx.EVT_BUTTON, self._on_browse)
        ok.Bind(wx.EVT_BUTTON, self._on_ok)
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)

    def _update_visibility(self) -> None:
        show_file = self.kind_file.GetValue()
        show_url = self.kind_url.GetValue()
        show_note = self.kind_note.GetValue()
        self.path_label.Show(show_file)
        self.path.Show(show_file)
        self.browse.Show(show_file)
        self.url_label.Show(show_url)
        self.url.Show(show_url)
        self.note_label.Show(show_note)
        self.note.Show(show_note)
        self.Layout()

    def _on_browse(self, _e) -> None:
        dlg = wx.FileDialog(self, "Choose a file")
        if dlg.ShowModal() == wx.ID_OK:
            self.path.SetValue(dlg.GetPath())
        dlg.Destroy()

    def _on_ok(self, _e) -> None:
        name = self.name.GetValue().strip()
        if self.kind_file.GetValue():
            uri = self.path.GetValue().strip()
            if not uri:
                show_message_box("Choose a file.", "Add Attachment", style=wx.ICON_WARNING)
                return
            self._result = {"kind": "file", "name": name, "uri": uri}
        elif self.kind_url.GetValue():
            uri = self.url.GetValue().strip()
            if not uri:
                show_message_box("Enter a URL.", "Add Attachment", style=wx.ICON_WARNING)
                return
            self._result = {"kind": "url", "name": name, "uri": uri}
        else:
            content = self.note.GetValue()
            if not content.strip():
                show_message_box("Enter some note text.", "Add Attachment", style=wx.ICON_WARNING)
                return
            self._result = {"kind": "note", "name": name, "content": content}
        self.EndModal(wx.ID_OK)

    def result(self) -> dict | None:
        return self._result


class SyncSettingsDialog(wx.Dialog):
    """Configure and run sync (PRD 45, 45.9).

    One dialog covers transport choice (off/folder/server), folder path, server
    URL + device name, the client-based magic-link sign-in, and vault
    unlock/setup. Every operation is fail-safe: errors land in the status line,
    never as crashes. The passphrase is held in memory only for this session.
    """

    def __init__(self, parent, controller):
        super().__init__(
            parent, title="Sync Settings", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.ctrl = controller
        cfg = controller.config

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Transport choice.
        tbox = wx.StaticBoxSizer(wx.VERTICAL, self, "&Transport")
        self.t_off = wx.RadioButton(
            tbox.GetStaticBox(), label="&Off (this machine only)", style=wx.RB_GROUP
        )
        self.t_folder = wx.RadioButton(
            tbox.GetStaticBox(), label="&Folder (iCloud, OneDrive, Dropbox...)"
        )
        self.t_server = wx.RadioButton(tbox.GetStaticBox(), label="&Hosted server")
        for r in (self.t_off, self.t_folder, self.t_server):
            _name(r, r.GetLabel().replace("&", ""))
            tbox.Add(r, 0, wx.ALL, 4)
        {"off": self.t_off, "folder": self.t_folder, "server": self.t_server}.get(
            cfg.transport, self.t_off
        ).SetValue(True)
        sizer.Add(tbox, 0, wx.EXPAND | wx.ALL, 8)

        # Folder row.
        fbox = wx.StaticBoxSizer(wx.HORIZONTAL, self, "Folder &path")
        self.folder = wx.TextCtrl(fbox.GetStaticBox(), value=cfg.folder, size=(300, -1))
        _name(self.folder, "Folder path for folder transport")
        fbox.Add(self.folder, 1, wx.EXPAND | wx.ALL, 4)
        self.browse = wx.Button(fbox.GetStaticBox(), label="&Browse...")
        _name(self.browse, "Browse for folder")
        fbox.Add(self.browse, 0, wx.ALL, 4)
        sizer.Add(fbox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Server / device.
        sbox = wx.StaticBoxSizer(wx.VERTICAL, self, "&Server")
        sform = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
        sform.AddGrowableCol(1, proportion=1)
        self.server_url = self._row(sbox.GetStaticBox(), sform, "Server &URL:", cfg.server_url)
        self.device = self._row(sbox.GetStaticBox(), sform, "&Device name:", cfg.device or "beacon")
        sbox.Add(sform, 1, wx.EXPAND | wx.ALL, 4)
        sizer.Add(sbox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Magic-link sign-in.
        mbox = wx.StaticBoxSizer(wx.VERTICAL, self, "&Sign in (magic link)")
        mform = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
        mform.AddGrowableCol(1, proportion=1)
        self.email = self._row(mbox.GetStaticBox(), mform, "&Email:", cfg.account)
        mbox.Add(mform, 1, wx.EXPAND | wx.ALL, 4)
        link_row = wx.BoxSizer(wx.HORIZONTAL)
        self.send_link = wx.Button(mbox.GetStaticBox(), label="&Send sign-in link")
        _name(self.send_link, "Send sign-in link")
        link_row.Add(self.send_link, 0, wx.RIGHT, 6)
        self.token = wx.TextCtrl(mbox.GetStaticBox(), size=(220, -1))
        _name(self.token, "Paste the link or token you received")
        link_row.Add(self.token, 1, wx.RIGHT, 6)
        self.verify = wx.Button(mbox.GetStaticBox(), label="&Verify")
        _name(self.verify, "Verify the pasted link or token")
        link_row.Add(self.verify, 0)
        mbox.Add(link_row, 0, wx.EXPAND | wx.ALL, 4)
        sizer.Add(mbox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Vault.
        vbox = wx.StaticBoxSizer(wx.VERTICAL, self, "&Vault (end-to-end encryption)")
        vform = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
        vform.AddGrowableCol(1, proportion=1)
        self.passphrase = self._row(
            vbox.GetStaticBox(), vform, "&Passphrase:", "", style=wx.TE_PASSWORD
        )
        vbox.Add(vform, 1, wx.EXPAND | wx.ALL, 4)
        vrow = wx.BoxSizer(wx.HORIZONTAL)
        self.unlock_btn = wx.Button(vbox.GetStaticBox(), label="&Unlock")
        self.setup_btn = wx.Button(vbox.GetStaticBox(), label="&Set Up / Re-key")
        self.pair_btn = wx.Button(vbox.GetStaticBox(), label="&Pair Device...")
        for b in (self.unlock_btn, self.setup_btn, self.pair_btn):
            _name(b, b.GetLabel().replace("&", ""))
            vrow.Add(b, 0, wx.RIGHT, 6)
        vbox.Add(vrow, 0, wx.ALL, 4)
        sizer.Add(vbox, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Status + buttons.
        self.status = wx.StaticText(self, label=self._status_label())
        _name(self.status, "Sync status")
        sizer.Add(self.status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.sync_now = wx.Button(self, label="Sync &Now")
        _name(self.sync_now, "Sync now")
        close = wx.Button(self, label="&Close", id=wx.ID_CLOSE)
        _name(close, "Close")
        buttons.Add(self.sync_now, 0, wx.RIGHT, 8)
        buttons.AddStretchSpacer(1)
        buttons.Add(close, 0)
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.server_url.SetFocus()

        self.browse.Bind(wx.EVT_BUTTON, self._on_browse)
        self.send_link.Bind(wx.EVT_BUTTON, self._on_send_link)
        self.verify.Bind(wx.EVT_BUTTON, self._on_verify)
        self.unlock_btn.Bind(wx.EVT_BUTTON, self._on_unlock)
        self.setup_btn.Bind(wx.EVT_BUTTON, self._on_setup)
        self.pair_btn.Bind(wx.EVT_BUTTON, self._on_pair)
        self.sync_now.Bind(wx.EVT_BUTTON, self._on_sync_now)
        apply_modal_ids(self, escape_id=wx.ID_CLOSE)

    def _row(self, parent, sizer, label, value, *, style=0) -> wx.TextCtrl:
        lbl = wx.StaticText(parent, label=label)
        ctrl = wx.TextCtrl(parent, value=value, style=style, size=(300, -1))
        _name(ctrl, label.replace("&", "").replace(":", "").strip())
        sizer.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(ctrl, 1, wx.EXPAND)
        return ctrl

    def _status_label(self) -> str:
        cfg = self.ctrl.config
        bits = [f"Transport: {cfg.transport}"]
        if cfg.transport == "folder":
            bits.append(f"Folder: {cfg.folder or '(unset)'}")
        elif cfg.transport == "server":
            bits.append(f"Server: {cfg.server_url or '(unset)'}")
            bits.append(f"Signed in: {'yes' if cfg.device_token else 'no'}")
        bits.append(f"Vault: {'unlocked' if self.ctrl.is_unlocked() else 'locked'}")
        bits.append(f"Configured: {'yes' if cfg.is_configured() else 'no'}")
        return "  |  ".join(bits)

    def _refresh_status(self) -> None:
        self.status.SetLabel(self._status_label())

    def _gather_config(self):
        cfg = self.ctrl.config
        if self.t_off.GetValue():
            cfg.transport = "off"
        elif self.t_folder.GetValue():
            cfg.transport = "folder"
        else:
            cfg.transport = "server"
        cfg.folder = self.folder.GetValue().strip()
        cfg.server_url = self.server_url.GetValue().strip()
        cfg.device = self.device.GetValue().strip() or "beacon"
        cfg.account = self.email.GetValue().strip()
        return cfg

    def _on_browse(self, _e) -> None:
        dlg = wx.DirDialog(self, "Choose sync folder", defaultPath=self.folder.GetValue() or "")
        if dlg.ShowModal() == wx.ID_OK:
            self.folder.SetValue(dlg.GetPath())
        dlg.Destroy()

    def _on_send_link(self, _e) -> None:
        self._gather_config()
        self.ctrl.save_config(self.ctrl.config)
        email = self.email.GetValue().strip()
        if not email:
            show_message_box("Enter your email first.", "QuillBeacon", style=wx.ICON_WARNING)
            return
        res = self.ctrl.request_magic_link(email)
        if "error" in res:
            show_message_box(res["error"], "Sign-in", style=wx.ICON_ERROR)
        else:
            show_message_box(
                "A sign-in link was sent. In development the link is also "
                "printed by the server; paste it (or just the token) into the "
                "field and press Verify.",
                "Sign-in",
                style=wx.ICON_INFORMATION,
            )

    def _on_verify(self, _e) -> None:
        self._gather_config()
        self.ctrl.save_config(self.ctrl.config)
        raw = self.token.GetValue().strip()
        token = self._extract_token(raw)
        if not token:
            show_message_box(
                "Paste the link or token you received.", "QuillBeacon", style=wx.ICON_WARNING
            )
            return
        res = self.ctrl.verify_magic_link(token, self.device.GetValue().strip() or "beacon")
        if "error" in res:
            show_message_box(res["error"], "Verify", style=wx.ICON_ERROR)
        else:
            self._refresh_status()
            show_message_box("Signed in. This device is now registered.", "Verify", wx.OK)

    @staticmethod
    def _extract_token(raw: str) -> str:
        """Accept a full quillsync://verify?token=... link or a bare token."""
        if "token=" in raw:
            from urllib.parse import parse_qs, urlparse

            q = parse_qs(urlparse(raw).query)
            return (q.get("token") or [""])[0]
        return raw

    def _on_unlock(self, _e) -> None:
        self._gather_config()
        self.ctrl.save_config(self.ctrl.config)
        pp = self.passphrase.GetValue()
        if not pp:
            show_message_box("Enter your passphrase.", "QuillBeacon", style=wx.ICON_WARNING)
            return
        try:
            self.ctrl.unlock(pp)
        except Exception as ex:
            show_message_box(str(ex), "Unlock", style=wx.ICON_ERROR)
            return
        self.passphrase.Clear()
        self._refresh_status()
        show_message_box("Vault unlocked for this session.", "Unlock", wx.OK)

    def _on_setup(self, _e) -> None:
        self._gather_config()
        self.ctrl.save_config(self.ctrl.config)
        pp = self.passphrase.GetValue()
        if not pp:
            show_message_box(
                "Enter a passphrase to set up the vault.", "QuillBeacon", style=wx.ICON_WARNING
            )
            return
        if not self.ctrl.has_vault():
            confirm = wx.GetPasswordFromUser("Confirm passphrase:", "Set Up Vault", "")
            if confirm != pp:
                show_message_box("Passphrases did not match.", "QuillBeacon", style=wx.ICON_WARNING)
                return
        try:
            self.ctrl.setup_vault(pp)
        except Exception as ex:
            show_message_box(str(ex), "Vault", style=wx.ICON_ERROR)
            return
        self.passphrase.Clear()
        self._refresh_status()
        show_message_box(
            "Vault set up. Keep your passphrase safe -- it cannot be recovered.",
            "Vault",
            wx.OK,
        )

    def _on_pair(self, _e) -> None:
        """Export this device's vault salt, or import one from another device.

        The salt is the only shareable part; the passphrase is entered on each
        device and never transferred. Export shows the code to type/paste on the
        other device; Import adopts a code pasted here.
        """
        choice = show_message_box(
            "Choose:\n\n  Yes = Export this device's pairing code\n"
            "  No  = Import a pairing code from another device\n",
            "Pair Device",
            style=wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
        )
        if choice == wx.YES:
            res = self.ctrl.export_vault_pairing()
            if "error" in res:
                show_message_box(res["error"], "Pair Device", style=wx.ICON_ERROR)
                return
            code = res["pairing_code"]
            dlg = wx.TextEntryDialog(
                self,
                "This is your vault pairing code. Enter it on the other "
                "device, then unlock there with the same passphrase you used "
                "here:",
                "Export Pairing Code",
                code,
            )
            _name(dlg, "Export pairing code dialog")
            dlg.ShowModal()
            dlg.Destroy()
            return
        # Import path.
        dlg = wx.TextEntryDialog(
            self, "Paste the pairing code from the other device:", "Import Pairing Code", ""
        )
        _name(dlg, "Import pairing code dialog")
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return
        code = dlg.GetValue().strip()
        dlg.Destroy()
        if not code:
            return
        if self.ctrl.has_vault():
            confirm = show_message_box(
                "Importing replaces this device's vault. Records encrypted under "
                "the old key will no longer decrypt. Continue?",
                "Pair Device",
                style=wx.ICON_WARNING | wx.YES_NO,
            )
            if confirm != wx.YES:
                return
        res = self.ctrl.import_vault_pairing(code)
        if "error" in res:
            show_message_box(res["error"], "Pair Device", style=wx.ICON_ERROR)
            return
        self._refresh_status()
        show_message_box(
            "Pairing code imported. Unlock with the passphrase from the other "
            "device to share the vault.",
            "Pair Device",
            wx.OK,
        )

    def _on_sync_now(self, _e) -> None:
        self._gather_config()
        self.ctrl.save_config(self.ctrl.config)
        res = self.ctrl.sync_now()
        if "error" in res:
            show_message_box(res["error"], "Sync", style=wx.ICON_ERROR)
            return
        msg = f"Synced. Pushed {res.get('pushed', 0)} commit(s), pulled {res.get('pulled', 0)}."
        conflicts = res.get("conflicts") or []
        if conflicts:
            msg += f"\n\n{len(conflicts)} conflict(s) need review (see Sync History)."
        self._refresh_status()
        show_message_box(msg, "Sync", wx.OK)
        self._sync_result = res

    @property
    def last_sync_result(self) -> dict | None:
        return getattr(self, "_sync_result", None)


class SyncHistoryDialog(wx.Dialog):
    """Show the sync commit log and let the user roll back (PRD 18.5)."""

    def __init__(self, parent, controller, *, on_rollback=None):
        super().__init__(
            parent, title="Sync History", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.ctrl = controller
        self._on_rollback = on_rollback

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label="&Commits (what synced):"), 0, wx.ALL, 8)
        self.commit_list = wx.ListBox(self, style=wx.LB_SINGLE)
        _name(self.commit_list, "Sync commits. Select to inspect.")
        for c in controller.history():
            self.commit_list.Append(f"{c['message']} -- {c['entries']} entries -- {c['device']}")
        sizer.Add(self.commit_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        conflicts = self._collect_conflicts()
        sizer.Add(
            wx.StaticText(self, label="&Conflicts needing review:"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            8,
        )
        self.conflict_list = wx.ListBox(self, style=wx.LB_SINGLE)
        _name(
            self.conflict_list,
            "Conflicts needing review. Select, then choose Local, Remote, or Merged.",
        )
        self._conflicts = conflicts
        for cf in conflicts:
            self.conflict_list.Append(self._conflict_label(cf))
        sizer.Add(self.conflict_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        resolve_row = wx.BoxSizer(wx.HORIZONTAL)
        self.r_local = wx.Button(self, label="Use &Local")
        self.r_remote = wx.Button(self, label="Use &Remote")
        self.r_merged = wx.Button(self, label="Use &Merged")
        for b in (self.r_local, self.r_remote, self.r_merged):
            _name(b, b.GetLabel().replace("&", ""))
            resolve_row.Add(b, 0, wx.RIGHT, 6)
        sizer.Add(resolve_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        sizer.Add(
            wx.StaticText(self, label="&Pre-sync snapshots (rollback):"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            8,
        )
        self.backup_list = wx.ListBox(self, style=wx.LB_SINGLE)
        _name(self.backup_list, "Pre-sync snapshots. Select and Roll Back to restore.")
        for b in controller.list_backups():
            self.backup_list.Append(b["name"])
        sizer.Add(self.backup_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.rollback = wx.Button(self, label="&Roll Back to Selected Snapshot")
        _name(self.rollback, "Roll back to selected snapshot")
        close = wx.Button(self, label="&Close", id=wx.ID_CLOSE)
        _name(close, "Close")
        buttons.Add(self.rollback, 0, wx.RIGHT, 8)
        buttons.AddStretchSpacer(1)
        buttons.Add(close, 0)
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.rollback.Bind(wx.EVT_BUTTON, self._on_rollback)
        self.r_local.Bind(wx.EVT_BUTTON, lambda _e: self._resolve("local"))
        self.r_remote.Bind(wx.EVT_BUTTON, lambda _e: self._resolve("remote"))
        self.r_merged.Bind(wx.EVT_BUTTON, lambda _e: self._resolve("merged"))
        apply_modal_ids(self, escape_id=wx.ID_CLOSE)

    def _collect_conflicts(self) -> list[dict]:
        return self.ctrl.list_conflicts(resolved=False)

    @staticmethod
    def _conflict_label(cf: dict) -> str:
        b = cf.get("entity_id", "?")
        return f"{b} -- {cf.get('field', 'note')} -- {cf.get('message', '')}"

    def _resolve(self, choice: str) -> None:
        sel = self.conflict_list.GetSelection()
        if sel < 0 or sel >= len(self._conflicts):
            show_message_box("Select a conflict first.", "QuillBeacon", style=wx.ICON_WARNING)
            return
        cf = self._conflicts[sel]
        res = self.ctrl.resolve_conflict(cf["id"], choice)
        if "error" in res:
            show_message_box(res["error"], "Resolve", style=wx.ICON_ERROR)
            return
        # Refresh the list.
        self._conflicts = self._collect_conflicts()
        self.conflict_list.Clear()
        for c in self._conflicts:
            self.conflict_list.Append(self._conflict_label(c))
        show_message_box(f"Resolved using {choice} version.", "Resolve", wx.OK)

    def _on_rollback(self, _e) -> None:
        sel = self.backup_list.GetSelection()
        if sel < 0:
            show_message_box(
                "Select a snapshot to roll back to.", "QuillBeacon", style=wx.ICON_WARNING
            )
            return
        name = self.backup_list.GetString(sel)
        if (
            show_message_box(
                f"Restore the library to the snapshot {name}? This overwrites the "
                "current database with the pre-sync copy. The commit log is kept.",
                "Roll Back",
                wx.YES_NO | wx.ICON_WARNING,
                self,
            )
            != wx.YES
        ):
            return
        if self._on_rollback:
            self._on_rollback(name)
        self.EndModal(wx.ID_OK)


class PlayerSettingsDialog(wx.Dialog):
    """Configure the external media player (PRD 11.5, 44.3).

    Sets a default player, an optional custom executable path per player (for
    installs not on PATH), and a per-resource-type player override so radio and
    podcasts can open in different players. Returns a
    :class:`external_player.PlayerSettings` via ``result()``.
    """

    # Media types that benefit from a per-type player override.
    MEDIA_TYPES = (
        "radioStream",
        "radioStation",
        "podcastEpisode",
        "podcastChapter",
        "video",
        "timePoint",
    )

    def __init__(self, parent, *, settings):
        from quill.apps.beacon import external_player

        self._ep = external_player
        super().__init__(
            parent, title="External Player", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._settings = settings
        self._type_combos: dict[str, wx.ComboBox] = {}

        sizer = wx.BoxSizer(wx.VERTICAL)
        form = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
        form.AddGrowableCol(1, proportion=1)

        choices = list(external_player.PLAYERS)
        self.default_combo = self._combo(form, "&Default player:", choices, settings.default_player)
        self.vlc_path = self._row(form, "&VLC path:", settings.custom_path.get("vlc", ""))
        self.mpv_path = self._row(form, "&mpv path:", settings.custom_path.get("mpv", ""))

        sizer.Add(form, 0, wx.EXPAND | wx.ALL, 10)

        note = wx.StaticText(
            self,
            label="Per-type players override the default for that media "
            "type. Leave a path blank to use the player on PATH.",
        )
        _name(note, "Player settings help")
        sizer.Add(note, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        type_box = wx.StaticBox(self, label="Per-type player")
        _name(type_box, "Per-type player")
        ts = wx.StaticBoxSizer(type_box, wx.VERTICAL)
        tform = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
        tform.AddGrowableCol(1, proportion=1)
        for t in self.MEDIA_TYPES:
            self._type_combos[t] = self._combo(
                tform, f"{t}:", choices, settings.per_type.get(t, "")
            )
        ts.Add(tform, 1, wx.EXPAND | wx.ALL, 8)
        sizer.Add(ts, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        btns = wx.BoxSizer(wx.HORIZONTAL)
        self._save_btn = wx.Button(self, label="&Save")
        _name(self._save_btn, "Save")
        self._save_btn.SetDefault()
        cancel_btn = wx.Button(self, label="Cancel", id=wx.ID_CANCEL)
        _name(cancel_btn, "Cancel")
        btns.Add(self._save_btn, 0, wx.RIGHT, 8)
        btns.Add(cancel_btn, 0)
        sizer.Add(btns, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.SetSizer(sizer)
        sizer.Fit(self)

        self._save_btn.Bind(wx.EVT_BUTTON, self._on_save)
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL)

    def _row(self, sizer, label, value) -> wx.TextCtrl:
        lbl = wx.StaticText(self, label=label)
        ctrl = wx.TextCtrl(self, value=value, size=(320, -1))
        _name(ctrl, label.replace("&", "").replace(":", "").strip())
        sizer.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(ctrl, 1, wx.EXPAND)
        return ctrl

    def _combo(self, sizer, label, choices, value) -> wx.ComboBox:
        lbl = wx.StaticText(self, label=label)
        combo = wx.ComboBox(self, choices=choices, style=wx.CB_READONLY)
        if value in choices:
            combo.SetValue(value)
        _name(combo, label.replace("&", "").replace(":", "").strip())
        sizer.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(combo, 1, wx.EXPAND)
        return combo

    def _on_save(self, _e) -> None:
        if self.IsModal():
            self.EndModal(wx.ID_OK)

    def result(self):
        """Return a PlayerSettings built from the dialog, or None on cancel."""
        ep = self._ep
        custom = {}
        vlc = self.vlc_path.GetValue().strip()
        mpv = self.mpv_path.GetValue().strip()
        if vlc:
            custom["vlc"] = vlc
        if mpv:
            custom["mpv"] = mpv
        per_type = {
            t: c.GetValue()
            for t, c in self._type_combos.items()
            if c.GetValue() and c.GetValue() != ep.PLAYER_DEFAULT
        }
        return ep.PlayerSettings(
            default_player=self.default_combo.GetValue() or ep.PLAYER_DEFAULT,
            custom_path=custom,
            per_type=per_type,
        )
