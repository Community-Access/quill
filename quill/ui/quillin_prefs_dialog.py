"""Render Quillin ``contributes.preferences`` pages as wxPython dialogs.

Each Quillin preference page is a declarative dict (pages -> tabs -> sections ->
settings).  This module turns that structure into a live wx.Dialog, reads
current values from ``quill.core.quillin_settings``, and atomically persists
any changes on Save.

StaticText labels are always created *before* their associated input control so
JAWS finds the correct label buddy via Windows Z-order (issue #249).
wx.CheckBox is exempt — it carries its own label text.
"""

from __future__ import annotations

from typing import Any


class _Ref:
    """Slim bundle that tracks one rendered setting control."""

    __slots__ = ("key", "ctrl", "label", "kind", "choice_values", "visible_when", "enabled_when")

    def __init__(
        self,
        key: str,
        ctrl: Any,
        label: Any,
        kind: str,
        choice_values: list[str] | None,
        visible_when: dict | None,
        enabled_when: dict | None,
    ) -> None:
        self.key = key
        self.ctrl = ctrl
        self.label = label
        self.kind = kind
        self.choice_values = choice_values
        self.visible_when = visible_when
        self.enabled_when = enabled_when


def _get_ctrl_value(ref: _Ref) -> Any:
    if ref.kind == "boolean":
        return ref.ctrl.GetValue()
    if ref.kind == "integer":
        return ref.ctrl.GetValue()
    if ref.kind == "string":
        return ref.ctrl.GetValue()
    # choice
    idx = ref.ctrl.GetSelection()
    if ref.choice_values and 0 <= idx < len(ref.choice_values):
        return ref.choice_values[idx]
    return ""


def _collect_values(refs: list[_Ref]) -> dict[str, Any]:
    return {ref.key: _get_ctrl_value(ref) for ref in refs}


def _build_setting(
    panel: Any,
    sizer: Any,
    s: dict,
    current: dict[str, Any],
    refs: list[_Ref],
    wx: Any,
) -> None:
    key = s.get("key", "")
    label_text = s.get("label", key)
    kind = s.get("type", "string")
    default = s.get("default")
    raw = current.get(key, default)
    visible_when = s.get("visible_when")
    enabled_when = s.get("enabled_when")

    label_widget = None
    ctrl = None
    choice_values: list[str] | None = None

    if kind == "boolean":
        ctrl = wx.CheckBox(panel, label=label_text)
        ctrl.SetValue(bool(raw))
        ctrl.SetName(label_text)
        sizer.Add(ctrl, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

    elif kind == "integer":
        # Label created first — JAWS buddy requirement.
        label_widget = wx.StaticText(panel, label=f"{label_text}:")
        sizer.Add(label_widget, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        lo = int(s.get("minimum", 0))
        hi = int(s.get("maximum", 100))
        try:
            initial = int(raw)
        except (TypeError, ValueError):
            initial = int(default) if default is not None else lo
        initial = max(lo, min(hi, initial))
        ctrl = wx.SpinCtrl(panel, min=lo, max=hi, value=str(initial))
        ctrl.SetName(label_text)
        sizer.Add(ctrl, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

    elif kind == "choice":
        choices_list = s.get("choices", [])
        choice_values = [c.get("value", "") for c in choices_list]
        display_labels = [c.get("label", c.get("value", "")) for c in choices_list]
        # Label created first — JAWS buddy requirement.
        label_widget = wx.StaticText(panel, label=f"{label_text}:")
        sizer.Add(label_widget, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        ctrl = wx.Choice(panel, choices=display_labels)
        ctrl.SetName(label_text)
        sel = 0
        if raw in choice_values:
            sel = choice_values.index(raw)
        elif default in choice_values:
            sel = choice_values.index(default)
        ctrl.SetSelection(sel)
        sizer.Add(ctrl, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.EXPAND, 8)

    else:  # "string"
        # Label created first — JAWS buddy requirement.
        label_widget = wx.StaticText(panel, label=f"{label_text}:")
        sizer.Add(label_widget, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        ctrl = wx.TextCtrl(panel, value=str(raw) if raw is not None else "")
        ctrl.SetName(label_text)
        sizer.Add(ctrl, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.EXPAND, 8)

    if ctrl is None:
        return

    desc = s.get("description")
    if desc:
        hint = wx.StaticText(panel, label=desc)
        hint.Wrap(440)
        hint.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        sizer.Add(hint, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    refs.append(
        _Ref(
            key=key,
            ctrl=ctrl,
            label=label_widget,
            kind=kind,
            choice_values=choice_values,
            visible_when=visible_when,
            enabled_when=enabled_when,
        )
    )


def _build_tab_content(
    panel: Any,
    sizer: Any,
    tab: dict,
    current: dict[str, Any],
    refs: list[_Ref],
    wx: Any,
) -> None:
    desc = tab.get("description", "")
    if desc:
        intro = wx.StaticText(panel, label=desc)
        intro.Wrap(460)
        sizer.Add(intro, 0, wx.ALL, 8)
    for section in tab.get("sections", []):
        title = section.get("title", "")
        if title:
            heading = wx.StaticText(panel, label=title)
            font = heading.GetFont()
            font.MakeBold()
            heading.SetFont(font)
            sizer.Add(heading, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        for s in section.get("settings", []):
            _build_setting(panel, sizer, s, current, refs, wx)


def _wire_conditions(refs: list[_Ref], wx: Any) -> None:
    """Bind change events so conditional controls reflect their state on open and on change."""
    ctrl_map = {ref.key: ref for ref in refs}
    for dep_ref in refs:
        cond = dep_ref.visible_when or dep_ref.enabled_when
        if cond is None:
            continue
        controller_key = cond.get("setting", "")
        equals_value = cond.get("equals")
        is_visible = dep_ref.visible_when is not None
        controller_ref = ctrl_map.get(controller_key)
        if controller_ref is None:
            continue

        def _make_updater(
            _dep: _Ref = dep_ref,
            _ctl: _Ref = controller_ref,
            _eq: Any = equals_value,
            _vis: bool = is_visible,
        ) -> Any:
            def _update(_evt: Any = None) -> None:
                active = _get_ctrl_value(_ctl) == _eq
                if _vis:
                    _dep.ctrl.Show(active)
                    if _dep.label is not None:
                        _dep.label.Show(active)
                    _dep.ctrl.GetParent().Layout()
                else:
                    _dep.ctrl.Enable(active)
                    if _dep.label is not None:
                        _dep.label.Enable(active)
                if _evt is not None:
                    _evt.Skip()

            return _update

        updater = _make_updater()
        if controller_ref.kind == "boolean":
            controller_ref.ctrl.Bind(wx.EVT_CHECKBOX, updater)
        elif controller_ref.kind == "choice":
            controller_ref.ctrl.Bind(wx.EVT_CHOICE, updater)
        elif controller_ref.kind == "integer":
            controller_ref.ctrl.Bind(wx.EVT_SPINCTRL, updater)
        else:
            controller_ref.ctrl.Bind(wx.EVT_TEXT, updater)
        updater()


def build_quillin_pref_dialog(
    parent: Any,
    manifest: Any,
    announce_fn: Any = None,
) -> None:
    """Open the preference dialog for *manifest* and save changes on OK."""
    import wx as _wx

    from quill.core import quillin_settings
    from quill.ui.dialog_contract import apply_modal_ids, focus_primary_control, show_modal_dialog

    wx = _wx
    page_dicts = manifest.contributes.preferences
    if not page_dicts:
        return
    page = page_dicts[0]
    quillin_id = manifest.id
    current = quillin_settings.load_settings(quillin_id)
    title = page.get("title") or manifest.name
    dialog = wx.Dialog(
        parent,
        title=f"{title} Settings",
        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
    )
    dialog.SetSize((520, 560))
    root = wx.BoxSizer(wx.VERTICAL)
    tabs = sorted(page.get("tabs", []), key=lambda t: t.get("order", 0))
    refs: list[_Ref] = []

    if len(tabs) == 1:
        scroll = wx.ScrolledWindow(dialog, style=wx.TAB_TRAVERSAL)
        scroll.SetScrollRate(0, 12)
        psizer = wx.BoxSizer(wx.VERTICAL)
        _build_tab_content(scroll, psizer, tabs[0], current, refs, wx)
        psizer.AddSpacer(8)
        scroll.SetSizer(psizer)
        root.Add(scroll, 1, wx.EXPAND | wx.ALL, 8)
    else:
        notebook = wx.Notebook(dialog)
        notebook.SetName(f"{title} settings tabs")
        for tab in tabs:
            scroll = wx.ScrolledWindow(notebook, style=wx.TAB_TRAVERSAL)
            scroll.SetScrollRate(0, 12)
            psizer = wx.BoxSizer(wx.VERTICAL)
            _build_tab_content(scroll, psizer, tab, current, refs, wx)
            psizer.AddSpacer(8)
            scroll.SetSizer(psizer)
            notebook.AddPage(scroll, tab.get("title", tab.get("id", "")))
        root.Add(notebook, 1, wx.EXPAND | wx.ALL, 8)

    _wire_conditions(refs, wx)

    btn_row = wx.BoxSizer(wx.HORIZONTAL)
    btn_row.AddStretchSpacer()
    btn_row.Add(wx.Button(dialog, wx.ID_OK, label="Save"), 0, wx.RIGHT, 8)
    btn_row.Add(wx.Button(dialog, wx.ID_CANCEL, label="Cancel"), 0)
    root.Add(btn_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    dialog.SetSizer(root)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
    # Land focus on the first field of the visible tab, not the tab strip or the
    # default Save button (shown via the module-level show_modal_dialog, which
    # has no MainFrame focus seam).
    focus_primary_control(dialog)

    try:
        if show_modal_dialog(dialog, f"{title} Settings") == wx.ID_OK:
            new_values = _collect_values(refs)
            all_values = dict(current)
            all_values.update(new_values)
            quillin_settings.save_settings(quillin_id, all_values)
            if announce_fn is not None:
                announce_fn(f"{manifest.name} preferences saved")
    finally:
        dialog.Destroy()
