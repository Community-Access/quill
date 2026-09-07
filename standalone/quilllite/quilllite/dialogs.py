"""Small dialogs: find, replace, go to line, headings list, shortcuts, about.

House rules (from Steven's wx notes and QUILL's dialog contract):
  - a text field or list gets a wx.StaticText with an & mnemonic created
    immediately before it, so NVDA and JAWS take the field's name from it;
  - checkboxes carry their own label;
  - OK and Cancel have no mnemonic (Enter and Escape already serve them);
  - Escape always closes.
"""

from __future__ import annotations

import wx


def _labelled_text(
    parent: wx.Window, sizer: wx.Sizer, label: str, value: str = "", multiline: bool = False
) -> wx.TextCtrl:
    static = wx.StaticText(parent, label=label)
    style = wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 if multiline else 0
    field = wx.TextCtrl(parent, value=value, style=style)
    sizer.Add(static, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
    sizer.Add(field, 1 if multiline else 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
    return field


class FindDialog(wx.Dialog):
    """Modeless find. Enter finds next; Shift+Enter finds previous."""

    def __init__(self, parent: wx.Window, initial: str, on_find) -> None:
        super().__init__(parent, title="Find", style=wx.DEFAULT_DIALOG_STYLE)
        self._on_find = on_find
        root = wx.BoxSizer(wx.VERTICAL)
        self.text = _labelled_text(self, root, "Find &what:", initial)
        self.match_case = wx.CheckBox(self, label="Match &case")
        self.whole_word = wx.CheckBox(self, label="Whole wor&d only")
        root.Add(self.match_case, 0, wx.LEFT | wx.RIGHT, 8)
        root.Add(self.whole_word, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.next_btn = wx.Button(self, wx.ID_OK, "Find &next")
        self.prev_btn = wx.Button(self, label="Find &previous")
        close_btn = wx.Button(self, wx.ID_CANCEL, "Close")
        buttons.Add(self.next_btn, 0, wx.RIGHT, 8)
        buttons.Add(self.prev_btn, 0, wx.RIGHT, 8)
        buttons.Add(close_btn, 0)
        root.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizerAndFit(root)
        self.SetAffirmativeId(wx.ID_OK)
        self.SetEscapeId(wx.ID_CANCEL)
        self.next_btn.Bind(wx.EVT_BUTTON, lambda e: self._find(False))
        self.prev_btn.Bind(wx.EVT_BUTTON, lambda e: self._find(True))
        close_btn.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        self.Bind(wx.EVT_CLOSE, lambda e: self.Destroy())
        self.text.Bind(wx.EVT_KEY_DOWN, self._on_key)
        self.text.SetFocus()
        self.text.SelectAll()

    def _on_key(self, event: wx.KeyEvent) -> None:
        if event.GetKeyCode() == wx.WXK_RETURN and event.ShiftDown():
            self._find(True)
            return
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.Close()
            return
        event.Skip()

    def options(self) -> dict:
        return {
            "needle": self.text.GetValue(),
            "match_case": self.match_case.GetValue(),
            "whole_word": self.whole_word.GetValue(),
        }

    def _find(self, reverse: bool) -> None:
        self._on_find(self.options(), reverse)


class ReplaceDialog(wx.Dialog):
    def __init__(
        self, parent: wx.Window, initial: str, on_find, on_replace, on_replace_all
    ) -> None:
        super().__init__(parent, title="Replace", style=wx.DEFAULT_DIALOG_STYLE)
        root = wx.BoxSizer(wx.VERTICAL)
        self.text = _labelled_text(self, root, "Find &what:", initial)
        self.replacement = _labelled_text(self, root, "Replace w&ith:")
        self.match_case = wx.CheckBox(self, label="Match &case")
        self.whole_word = wx.CheckBox(self, label="Whole wor&d only")
        root.Add(self.match_case, 0, wx.LEFT | wx.RIGHT, 8)
        root.Add(self.whole_word, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        find_btn = wx.Button(self, wx.ID_OK, "Find &next")
        replace_btn = wx.Button(self, label="&Replace")
        all_btn = wx.Button(self, label="Replace &all")
        close_btn = wx.Button(self, wx.ID_CANCEL, "Close")
        for btn in (find_btn, replace_btn, all_btn):
            buttons.Add(btn, 0, wx.RIGHT, 8)
        buttons.Add(close_btn, 0)
        root.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizerAndFit(root)
        self.SetAffirmativeId(wx.ID_OK)
        self.SetEscapeId(wx.ID_CANCEL)
        find_btn.Bind(wx.EVT_BUTTON, lambda e: on_find(self.options(), False))
        replace_btn.Bind(wx.EVT_BUTTON, lambda e: on_replace(self.options()))
        all_btn.Bind(wx.EVT_BUTTON, lambda e: on_replace_all(self.options()))
        close_btn.Bind(wx.EVT_BUTTON, lambda e: self.Close())
        self.Bind(wx.EVT_CLOSE, lambda e: self.Destroy())
        self.text.SetFocus()
        self.text.SelectAll()

    def options(self) -> dict:
        return {
            "needle": self.text.GetValue(),
            "replacement": self.replacement.GetValue(),
            "match_case": self.match_case.GetValue(),
            "whole_word": self.whole_word.GetValue(),
        }


def ask_line_number(parent: wx.Window, current: int, maximum: int) -> int | None:
    dialog = wx.Dialog(parent, title="Go to line")
    root = wx.BoxSizer(wx.VERTICAL)
    field = _labelled_text(dialog, root, f"&Line number (1 to {maximum}):", str(current))
    buttons = dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
    root.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
    dialog.SetSizerAndFit(root)
    field.SetFocus()
    field.SelectAll()
    try:
        if dialog.ShowModal() != wx.ID_OK:
            return None
        try:
            return max(1, min(maximum, int(field.GetValue().strip())))
        except ValueError:
            return None
    finally:
        dialog.Destroy()


def choose_heading(parent: wx.Window, headings: list[tuple[int, int, str]]) -> int | None:
    """List every heading; returns the chosen start offset."""
    dialog = wx.Dialog(parent, title="Headings", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    root = wx.BoxSizer(wx.VERTICAL)
    static = wx.StaticText(dialog, label="&Headings in this document:")
    listbox = wx.ListBox(
        dialog, choices=[f"Heading {level}: {text}" for _, level, text in headings]
    )
    root.Add(static, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
    root.Add(listbox, 1, wx.EXPAND | wx.ALL, 8)
    buttons = dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
    root.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
    dialog.SetSizerAndFit(root)
    dialog.SetSize((520, 400))
    listbox.Bind(wx.EVT_LISTBOX_DCLICK, lambda e: dialog.EndModal(wx.ID_OK))

    def on_key(event: wx.KeyEvent) -> None:
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            dialog.EndModal(wx.ID_OK)
            return
        event.Skip()

    listbox.Bind(wx.EVT_KEY_DOWN, on_key)
    if headings:
        listbox.SetSelection(0)
    listbox.SetFocus()
    try:
        if dialog.ShowModal() != wx.ID_OK:
            return None
        index = listbox.GetSelection()
        if index == wx.NOT_FOUND:
            return None
        return headings[index][0]
    finally:
        dialog.Destroy()


def show_text_window(parent: wx.Window, title: str, body: str) -> None:
    """A read-only text dialog (shortcuts, about). RICH2 so the value is read."""
    dialog = wx.Dialog(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    root = wx.BoxSizer(wx.VERTICAL)
    field = _labelled_text(dialog, root, "&Text:", body, multiline=True)
    close_btn = wx.Button(dialog, wx.ID_CANCEL, "Close")
    root.Add(close_btn, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
    dialog.SetSizerAndFit(root)
    dialog.SetSize((640, 480))
    dialog.SetEscapeId(wx.ID_CANCEL)
    close_btn.Bind(wx.EVT_BUTTON, lambda e: dialog.EndModal(wx.ID_CANCEL))
    field.SetFocus()
    field.SetInsertionPoint(0)
    try:
        dialog.ShowModal()
    finally:
        dialog.Destroy()
