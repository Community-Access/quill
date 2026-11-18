"""Keyboard-first compare mode dialog for QUILL (issues #193/#194).

Provides a keyboard-first interface: F8/Shift+F8 navigate differences,
Ctrl+F8 re-speaks the current one, Alt+F8 reads the inline changed text,
Ctrl+Shift+F8 toggles whitespace ignoring. All speech goes via the
parent frame's _announce() path so the active SR hears it.

The dialog is modal; when it closes, the caller discards the
CompareService state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from quill.ui.dpi import dip_size

if TYPE_CHECKING:
    from quill.core.compare_service import CompareService, DifferenceGroup


class CompareDialog:
    """Modal compare-navigation dialog.

    Wraps the wx.Dialog lifecycle without subclassing it so this file
    stays importable even in headless test runs (wx is imported lazily).
    """

    def __init__(self, parent: object, svc: CompareService) -> None:
        import wx

        from quill.ui.spoken_name import set_spoken_name

        self._svc = svc
        self._wx = wx
        g0 = svc.first()

        self.dialog = wx.Dialog(
            parent,
            title="Compare",
            size=dip_size(parent, 820, 560),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        # Status line at top.
        total = svc.group_count
        left = svc.left_label
        right = svc.right_label
        self._status_label = wx.StaticText(
            panel,
            label=f"Comparing {left!r} and {right!r}. {total} difference(s). "
            f"Press F8 for next, Shift+F8 for previous, Escape to close.",
        )
        self._status_label.Wrap(780)
        root.Add(self._status_label, 0, wx.ALL | wx.EXPAND, 8)

        # Difference list (stock wx.ListBox — accessible by construction).
        self._diff_list = wx.ListBox(panel, style=wx.LB_SINGLE)
        self._diff_list.SetName("Differences")
        for g in svc._groups:
            self._diff_list.Append(g.summary_short)
        if total > 0:
            self._diff_list.SetSelection(0)
        root.Add(self._diff_list, 1, wx.ALL | wx.EXPAND, 8)

        # Detail area for current difference.
        self._detail = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
        )
        self._detail.SetName("Difference detail")
        set_spoken_name(self._detail, "Difference detail")
        root.Add(self._detail, 1, wx.ALL | wx.EXPAND, 8)

        # Whitespace toggle checkbox.
        self._ws_check = wx.CheckBox(panel, label="Ignore trailing whitespace")
        root.Add(self._ws_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # How each changed line is marked: Kelly Ford's four styles
        # (quill.core.diff_marks), the one Diff Line Marks choice every diff
        # view in QUILL shares, so it is remembered here and there alike.
        from quill.core import diff_marks
        from quill.core.github.review_preferences import load_line_marks

        self._marks = diff_marks
        self._line_style = load_line_marks()
        marks_row = wx.BoxSizer(wx.HORIZONTAL)
        marks_row.Add(
            wx.StaticText(panel, label="&Mark lines as:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6
        )
        self._marks_choice = wx.Choice(
            panel, choices=[diff_marks.LABELS[style] for style in diff_marks.STYLES]
        )
        self._marks_choice.SetSelection(diff_marks.STYLES.index(self._line_style))
        self._marks_choice.SetName("Mark lines as")
        set_spoken_name(self._marks_choice, "Mark lines as")
        self._marks_choice.SetHelpText(
            "How each line of a difference is marked: words, short words, diff symbols, or "
            "diff symbols with each changed line read old then new. Remembered for every diff."
        )
        marks_row.Add(self._marks_choice, 0)
        root.Add(marks_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        self._marks_note = wx.StaticText(
            panel,
            label=diff_marks.SYMBOLS_NOTE if diff_marks.is_symbol_style(self._line_style) else "",
        )
        root.Add(self._marks_note, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Buttons.
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._btn_prev = wx.Button(panel, label="Previous (Shift+F8)")
        self._btn_next = wx.Button(panel, label="Next (F8)")
        self._btn_summary = wx.Button(panel, label="Read Current (Ctrl+F8)")
        self._btn_close = wx.Button(panel, id=wx.ID_CANCEL, label="Close (Escape)")
        btn_sizer.Add(self._btn_prev, 0, wx.RIGHT, 6)
        btn_sizer.Add(self._btn_next, 0, wx.RIGHT, 6)
        btn_sizer.Add(self._btn_summary, 0, wx.RIGHT, 6)
        btn_sizer.AddStretchSpacer(1)
        btn_sizer.Add(self._btn_close, 0)
        root.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 8)

        panel.SetSizer(root)

        from quill.ui.dialog_contract import apply_modal_ids

        apply_modal_ids(self.dialog, affirmative_id=wx.ID_CANCEL, escape_id=wx.ID_CANCEL)

        # Bind events.
        self._btn_next.Bind(wx.EVT_BUTTON, lambda _e: self._navigate(1))
        self._btn_prev.Bind(wx.EVT_BUTTON, lambda _e: self._navigate(-1))
        self._btn_summary.Bind(wx.EVT_BUTTON, lambda _e: self._speak_current())
        self._btn_close.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CANCEL))
        self._diff_list.Bind(wx.EVT_LISTBOX, self._on_list_select)
        self._marks_choice.Bind(wx.EVT_CHOICE, self._on_marks_changed)
        self.dialog.Bind(wx.EVT_CHAR_HOOK, self._on_key)

        if g0 is not None:
            self._show_group(g0)

        self._post_sound("compare_enter_mode")
        wx.CallAfter(self._diff_list.SetFocus)

    @staticmethod
    def _post_sound(event_id: str) -> None:
        """Post a compare earcon. Never raises; no-op if sound is off/uninit."""
        try:
            from quill.ui import sound_manager

            sound_manager.post_sound(event_id)
        except Exception:
            pass

    def ShowModal(self) -> int:
        result = self.dialog.ShowModal()
        self._post_sound("compare_exit_mode")
        return result

    def __enter__(self) -> CompareDialog:
        return self

    def __exit__(self, *_: object) -> None:
        self.Destroy()

    def Destroy(self) -> None:
        try:
            self.dialog.Destroy()
        except Exception:
            pass

    # ------------------------------------------------------------------

    def _navigate(self, direction: int) -> None:
        before = self._svc._cursor
        g = self._svc.next() if direction > 0 else self._svc.previous()
        if g is None:
            self._post_sound("compare_no_more_differences")
            return
        if self._svc._cursor == before:
            # Cursor clamped at the first/last difference: nothing further this way.
            self._post_sound("compare_no_more_differences")
        else:
            self._post_sound(
                "compare_next_difference" if direction > 0 else "compare_previous_difference"
            )
        self._show_group(g)
        # Sync the list selection.
        sel = g.index - 1
        if 0 <= sel < self._diff_list.GetCount():
            self._diff_list.SetSelection(sel)
            self._diff_list.EnsureVisible(sel)

    def _on_list_select(self, _event: object) -> None:
        sel = self._diff_list.GetSelection()
        if sel < 0:
            return
        # Drive the service cursor to match the list selection.
        groups = self._svc._groups
        if 0 <= sel < len(groups):
            self._svc._cursor = sel
            self._show_group(groups[sel])

    def _show_group(self, g: DifferenceGroup) -> None:
        self._status_label.SetLabel(
            f"Difference {g.index} of {g.total}. Press F8 / Shift+F8 to navigate."
        )
        self._detail.SetValue(self._detail_text(g))

    def _detail_text(self, g: DifferenceGroup) -> str:
        """The difference described, then its lines, each marked first."""
        lines = self._marks.render_replacement(g.left_text, g.right_text, self._line_style)
        return "\n".join([g.summary_verbose, "", *lines])

    def _on_marks_changed(self, _event: object) -> None:
        from quill.core.github.review_preferences import save_line_marks

        index = self._marks_choice.GetSelection()
        if not 0 <= index < len(self._marks.STYLES):
            return
        self._line_style = self._marks.STYLES[index]
        save_line_marks(self._line_style)
        symbols = self._marks.is_symbol_style(self._line_style)
        self._marks_note.SetLabel(self._marks.SYMBOLS_NOTE if symbols else "")
        g = self._svc.current()
        if g is not None:
            self._detail.SetValue(self._detail_text(g))

    def _speak_current(self) -> None:
        g = self._svc.current()
        if g is None:
            return
        self._detail.SetValue(self._detail_text(g))
        # Re-set focus to detail so SR re-reads it.
        self._wx.CallAfter(self._detail.SetFocus)

    def _on_key(self, event: object) -> None:
        wx = self._wx
        code = event.GetKeyCode()
        ctrl = event.ControlDown()
        shift = event.ShiftDown()
        alt = event.AltDown()

        if code == wx.WXK_F8:
            if ctrl and shift:
                self._toggle_whitespace()
            elif ctrl and not shift and not alt:
                self._speak_current()
            elif alt and not ctrl and not shift:
                self._read_inline_change()
            elif shift and not ctrl and not alt:
                self._navigate(-1)
            elif not ctrl and not shift and not alt:
                self._navigate(1)
            else:
                event.Skip()
            return
        if code == wx.WXK_ESCAPE:
            self.dialog.EndModal(wx.ID_CANCEL)
            return
        event.Skip()

    def _toggle_whitespace(self) -> None:
        current = self._ws_check.GetValue()
        self._ws_check.SetValue(not current)
        state = "on" if not current else "off"
        self._status_label.SetLabel(f"Ignore trailing whitespace: {state}")

    def _read_inline_change(self) -> None:
        g = self._svc.current()
        if g is None:
            return
        if not g.inline_spans:
            self._detail.SetValue(g.summary_verbose)
            return
        from quill.core.compare_service import _word_diff_label

        if g.left_text and g.right_text:
            label = _word_diff_label(g.left_text[0], g.right_text[0])
            self._detail.SetValue(f"Word-level change: {label}")
        self._wx.CallAfter(self._detail.SetFocus)
