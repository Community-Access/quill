"""Tools > Global Hotkeys... -- assign system-wide keys to safe commands.

A list of the allowlisted commands (the ONLY ones that can go global; see
``main_frame_hotkeys.GLOBAL_HOTKEY_SAFE_COMMANDS``) with each one's current
binding. Assign... captures the next key combination you press -- it must
include Ctrl, Alt, or Win, since a bare letter would swallow normal typing
system-wide -- and Clear removes one. Nothing takes effect until Save;
registration conflicts (another app owns the key) are reported by name
after saving, and that binding simply stays inactive until changed.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name

#: Keys we can format back into the "Ctrl+Alt+X" strings _parse_keybinding
#: reads. Letters, digits, and function keys cover the practical space.
_MODIFIER_ORDER = ("Ctrl", "Shift", "Alt")


class _CaptureDialog:
    """Reads exactly one key combination and returns it as a binding string."""

    def __init__(self, parent: object, *, label: str) -> None:
        import wx

        self._wx = wx
        self.result: str | None = None
        self.dialog = wx.Dialog(parent, title=f"Assign hotkey: {label}")
        root = wx.BoxSizer(wx.VERTICAL)
        prompt = wx.StaticText(
            self.dialog,
            label=(
                "Press the key combination now. Include Ctrl or Alt (a bare "
                "key would be swallowed everywhere). Escape cancels."
            ),
        )
        prompt.Wrap(360)
        root.Add(prompt, 0, self._wx.ALL, 12)
        self._sink = wx.TextCtrl(self.dialog, style=wx.TE_READONLY)
        set_accessible_name(self._sink, "Press the key combination to assign")
        root.Add(self._sink, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        self.dialog.SetSizerAndFit(root)
        apply_modal_ids(self.dialog, escape_id=wx.ID_CANCEL)
        self._sink.Bind(wx.EVT_KEY_DOWN, self._on_key)
        self._sink.SetFocus()

    def _on_key(self, event: object) -> None:
        wx = self._wx
        code = event.GetKeyCode()
        if code == wx.WXK_ESCAPE:
            self.dialog.EndModal(wx.ID_CANCEL)
            return
        if code in (wx.WXK_CONTROL, wx.WXK_SHIFT, wx.WXK_ALT, wx.WXK_WINDOWS_LEFT):
            return  # a bare modifier press: keep waiting for the full chord
        key_name = self._key_name(code)
        if key_name is None:
            return
        modifiers = []
        if event.ControlDown():
            modifiers.append("Ctrl")
        if event.ShiftDown():
            modifiers.append("Shift")
        if event.AltDown():
            modifiers.append("Alt")
        if not any(m in ("Ctrl", "Alt") for m in modifiers):
            self._sink.SetValue("Include Ctrl or Alt...")
            return
        self.result = "+".join([*modifiers, key_name])
        self.dialog.EndModal(wx.ID_OK)

    def _key_name(self, code: int) -> str | None:
        wx = self._wx
        if wx.WXK_F1 <= code <= wx.WXK_F24:
            return f"F{code - wx.WXK_F1 + 1}"
        if 32 < code < 127:
            return chr(code).upper()
        return None

    def show(self) -> str | None:
        """Capture one combination; None when cancelled."""
        from quill.ui.dialog_contract import show_modal_dialog

        self.dialog.CentreOnParent()
        result = show_modal_dialog(self.dialog, "Assign Hotkey")
        binding = self.result if result == self._wx.ID_OK else None
        self.dialog.Destroy()
        return binding


class GlobalHotkeysDialog:
    """The manager; ``show()`` returns the new bindings dict, or None."""

    def __init__(
        self,
        parent: object,
        *,
        commands: tuple[tuple[str, str, bool], ...],
        current: dict[str, str],
        show_modal_fn: Callable[..., int] | None = None,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._commands = commands
        self._bindings = dict(current)
        self._show_modal_fn = show_modal_fn
        self._announce = announce_cb or (lambda _m: None)
        self._result: dict[str, str] | None = None

        self.dialog = wx.Dialog(
            parent, title="Global Hotkeys", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((620, 440))
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            self.dialog,
            label=(
                "These commands can be triggered from anywhere in Windows. "
                "Only this safe list can go global; nothing here edits a "
                "document or deletes anything."
            ),
        )
        intro.Wrap(580)
        root.Add(intro, 0, wx.ALL, 10)

        self._list = wx.ListBox(self.dialog)
        set_accessible_name(self._list, "Commands and their global hotkeys")
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        assign_btn = wx.Button(self.dialog, label="&Assign...")
        clear_btn = wx.Button(self.dialog, label="C&lear")
        buttons.Add(assign_btn, 0, wx.RIGHT, 6)
        buttons.Add(clear_btn, 0)
        buttons.AddStretchSpacer()
        save_btn = wx.Button(self.dialog, id=wx.ID_OK, label="&Save")
        cancel_btn = wx.Button(self.dialog, id=wx.ID_CANCEL, label="Cancel")
        buttons.Add(save_btn, 0, wx.RIGHT, 6)
        buttons.Add(cancel_btn, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)
        assign_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_assign())
        clear_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_clear())
        save_btn.Bind(wx.EVT_BUTTON, self._on_save)
        self._list.Bind(wx.EVT_LISTBOX_DCLICK, lambda _e: self._on_assign())
        self._reload()

    def _row_label(self, index: int) -> str:
        command_id, label, _needs = self._commands[index]
        binding = self._bindings.get(command_id, "").strip()
        return f"{label} — {binding}" if binding else f"{label} — (not assigned)"

    def _reload(self, select: int | None = None) -> None:
        current = self._list.GetSelection() if select is None else select
        self._list.Set([self._row_label(i) for i in range(len(self._commands))])
        if self._commands:
            self._list.SetSelection(max(0, min(current, len(self._commands) - 1)))

    def _on_assign(self) -> None:
        index = self._list.GetSelection()
        if index < 0:
            return
        command_id, label, _needs = self._commands[index]
        capture = _CaptureDialog(self.dialog, label=label)
        binding = capture.show()
        if not binding:
            return
        taken = [cid for cid, b in self._bindings.items() if b == binding and cid != command_id]
        for cid in taken:
            self._bindings.pop(cid, None)
        self._bindings[command_id] = binding
        self._reload(select=index)
        suffix = " (reassigned from another command)" if taken else ""
        self._announce(f"{label} set to {binding}{suffix}")

    def _on_clear(self) -> None:
        index = self._list.GetSelection()
        if index < 0:
            return
        command_id, label, _needs = self._commands[index]
        if self._bindings.pop(command_id, None) is not None:
            self._reload(select=index)
            self._announce(f"{label}: hotkey cleared")

    def _on_save(self, _event: object) -> None:
        self._result = dict(self._bindings)
        self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> dict[str, str] | None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        self._list.SetFocus()
        if self._show_modal_fn is not None:
            self._show_modal_fn(self.dialog, "Global Hotkeys")
        else:
            from quill.ui.dialog_contract import show_modal_dialog

            show_modal_dialog(self.dialog)
        result = self._result
        self.dialog.Destroy()
        return result
