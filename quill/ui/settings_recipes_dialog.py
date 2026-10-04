"""Preferences > Task Recipes and Working Modes (qc.md X-02, X-03).

A "working mode" is what qc.md X-03 calls a profile; it is named apart from
QUILL's feature profiles (Profiles and Features), which are a different thing.

One list: the recipes first, then the profiles, each row saying which it is
and, for a profile, whether it is on. Below it, a read-only preview of exactly
which settings the highlighted row would change, from what to what, so nothing
is a hidden mode. Apply (a recipe) or Turn On / Turn Off (a profile) does it,
saves the settings, and says how many changed; a save that fails says so and
keeps the change for this session, as every QUILL settings write does. Put
Back undoes the last recipe applied in this window.
"""

from __future__ import annotations

from typing import Any

from quill.core import settings_recipes as sr

__all__ = ["TITLE", "open_settings_recipes"]

TITLE = "Task Recipes and Working Modes"


def _rows(state: dict[str, Any]) -> list[tuple[sr.Bundle, str]]:
    rows = [(bundle, f"Recipe: {bundle.title}") for bundle in sr.RECIPES]
    for bundle in sr.PROFILES:
        on = bundle.id in state
        session = on and state[bundle.id].get("session")
        status = "on for this session" if session else ("on" if on else "off")
        rows.append((bundle, f"Working mode: {bundle.title} ({status})"))
    return rows


def _save(host: Any) -> bool:
    from quill.core.settings import save_settings

    try:
        save_settings(host.settings)
    except Exception:  # noqa: BLE001 - reported, and the change holds for this session
        return False
    return True


def _apply_effects(host: Any, changed: set[str]) -> None:
    """The settings that need more than a stored value to take effect now."""
    if "theme" in changed:
        apply_theme = getattr(host, "_apply_theme", None)
        if callable(apply_theme):
            apply_theme(host.settings.theme)
    if "font_size" in changed:
        for name in ("_apply_editor_font", "_apply_font_size", "_refresh_editor_font"):
            method = getattr(host, name, None)
            if callable(method):
                method()
                break


def open_settings_recipes(host: Any) -> None:
    import wx

    from quill.core.paths import app_data_dir
    from quill.ui.dialog_contract import apply_modal_ids

    data_dir = app_data_dir()
    state = sr.load_state(data_dir)
    rows = _rows(state)
    undo: dict[str, object] = {}
    dialog = wx.Dialog(host.frame, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    root = wx.BoxSizer(wx.VERTICAL)
    root.Add(wx.StaticText(dialog, label="&Recipes and working modes:"), 0, wx.LEFT | wx.TOP, 8)
    listbox = wx.ListBox(dialog, choices=[label for _b, label in rows])
    listbox.SetHelpText(
        "A recipe changes several settings once, for a task. A working mode is one you "
        "turn on and off; turning it off puts every setting back. The preview below "
        "says exactly what the highlighted one changes."
    )
    root.Add(listbox, 1, wx.EXPAND | wx.ALL, 8)
    root.Add(wx.StaticText(dialog, label="What it &changes:"), 0, wx.LEFT, 8)
    preview = wx.TextCtrl(dialog, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 140))
    preview.SetHelpText("The settings the highlighted row would change, from what to what.")
    root.Add(preview, 0, wx.EXPAND | wx.ALL, 8)
    session = wx.CheckBox(dialog, label="Turn a working mode on for this &session only")
    session.SetHelpText(
        "A working mode turned on this way is turned off the next time QUILL starts, so a "
        "mode for one evening never quietly becomes how QUILL always is."
    )
    root.Add(session, 0, wx.LEFT | wx.RIGHT, 8)
    buttons = wx.BoxSizer(wx.HORIZONTAL)
    act = wx.Button(dialog, label="&Apply")
    act.SetHelpText("Applies the highlighted recipe, or turns the working mode on or off.")
    put_back = wx.Button(dialog, label="&Put Back")
    put_back.SetHelpText("Undoes the last recipe applied in this window.")
    put_back.Enable(False)
    close = wx.Button(dialog, wx.ID_CANCEL, label="Close")
    close.SetHelpText("Closes this window. What you applied stays applied.")
    buttons.Add(act, 0, wx.RIGHT, 6)
    buttons.Add(put_back, 0, wx.RIGHT, 6)
    buttons.AddStretchSpacer(1)
    buttons.Add(close, 0)
    root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
    dialog.SetSizer(root)
    dialog.SetSize((640, 520))
    apply_modal_ids(dialog, cancel_id=wx.ID_CANCEL, escape_id=wx.ID_CANCEL)

    def _current() -> sr.Bundle | None:
        index = listbox.GetSelection()
        return rows[index][0] if 0 <= index < len(rows) else None

    def _refresh_preview(_event: Any = None) -> None:
        bundle = _current()
        if bundle is None:
            preview.SetValue("")
            return
        if bundle.is_profile and bundle.id in state:
            previous = state[bundle.id].get("previous", {})
            lines = [f"Turning it off puts back {len(previous)} setting(s)."]
            act.SetLabel("Turn O&ff")
        else:
            lines = sr.preview(bundle, host.settings) or [
                "Nothing would change: every setting is already that way."
            ]
            act.SetLabel("Turn &On" if bundle.is_profile else "&Apply")
        preview.SetValue(bundle.purpose + "\n\n" + "\n".join(lines))
        session.Enable(bundle.is_profile and bundle.id not in state)

    def _relist(keep: int) -> None:
        rows[:] = _rows(state)
        listbox.Set([label for _b, label in rows])
        listbox.SetSelection(max(0, min(keep, len(rows) - 1)))
        _refresh_preview()

    def _finish(changed: set[str], sentence: str) -> None:
        _apply_effects(host, changed)
        saved = _save(host)
        if not saved:
            sentence += " The settings file could not be written; this holds until QUILL closes."
        host._announce(sentence)

    def _act(_event: Any) -> None:
        bundle = _current()
        if bundle is None:
            return
        keep = listbox.GetSelection()
        if bundle.is_profile and bundle.id in state:
            previous = state.pop(bundle.id).get("previous", {})
            moved = sr.restore(host.settings, previous)
            sr.save_state(data_dir, state)
            _finish(set(previous), f"{bundle.title} is off. Put back {moved} setting(s).")
        else:
            previous = sr.apply(bundle, host.settings)
            if not previous:
                host._announce("Nothing changed: every setting was already that way.")
                return
            if bundle.is_profile:
                state[bundle.id] = {"previous": previous, "session": session.GetValue()}
                sr.save_state(data_dir, state)
                when = " for this session" if session.GetValue() else ""
                _finish(
                    set(previous),
                    f"{bundle.title} is on{when}. {len(previous)} setting(s) changed.",
                )
            else:
                undo.clear()
                undo.update(previous)
                put_back.Enable(True)
                _finish(
                    set(previous),
                    f"{bundle.title}: {len(previous)} setting(s) changed. Put Back undoes it.",
                )
        _relist(keep)

    def _put_back(_event: Any) -> None:
        if not undo:
            return
        moved = sr.restore(host.settings, dict(undo))
        changed = set(undo)
        undo.clear()
        put_back.Enable(False)
        _finish(changed, f"Put back {moved} setting(s).")
        _refresh_preview()

    listbox.Bind(wx.EVT_LISTBOX, _refresh_preview)
    act.Bind(wx.EVT_BUTTON, _act)
    put_back.Bind(wx.EVT_BUTTON, _put_back)
    listbox.SetSelection(0)
    _refresh_preview()
    listbox.SetFocus()
    try:
        host._show_modal_dialog(dialog, TITLE)
    finally:
        dialog.Destroy()
