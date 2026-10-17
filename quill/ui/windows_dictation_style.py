"""Dictation Settings' named style, filler removal and self-repair (D-20).

Three names for choices that already exist
(:mod:`quill.core.windows_dictation.self_repair`): **Verbatim**, **Clean** and,
only when the host says AI is on, **Polished**. Choosing one sets the two check
boxes built here and, for Polished, two of More Dictation Settings' fields
(kept in the dialog's ``_more`` until OK). Changing a box by hand moves the
chooser to **Your own mix**, which changes nothing when chosen.

Mixed into :class:`~quill.ui.windows_dictation_dialog.WindowsDictationDialog`,
which supplies ``_settings``, ``_more`` and ``_ai_on``. Every control carries
its F1 help inline (GATE-<APP>-HELP).
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.windows_dictation.self_repair import (
    CUSTOM_STYLE,
    STYLE_FIELDS,
    style_choices,
    style_of,
)

__all__ = ["DictationStyleMixin"]


class DictationStyleMixin:
    """The style chooser and its two check boxes, and keeping them in step."""

    _settings: Any
    _more: dict[str, object]
    _ai_on: bool

    def _add_style_controls(self, root: wx.Sizer, settings: Any, pad: int) -> None:
        # Label and chooser on one row: the left column has no height to spare
        # on a 768-pixel screen.
        parent: Any = self
        style_row = wx.BoxSizer(wx.HORIZONTAL)
        style_label = wx.StaticText(parent, label="Dictation st&yle:")
        rows = style_choices(ai_on=self._ai_on)
        self._styles = [value for value, _label in rows]
        self.style = wx.Choice(parent, choices=[label for _value, label in rows])
        self.style.SetHelpText(
            "A name for how your words are written. Verbatim: every word as you say "
            "it. Clean: filler words left out, and when you correct yourself, like "
            "Thursday, no, Friday, only Friday is written. Polished, offered when AI "
            "is on: Clean, and your dictation goes to Review Dictation first, where "
            "QUILL polish that asks the AI to tidy punctuation and small slips, only "
            "when you ask and only after you agree to send. Choosing a style sets the "
            "check boxes below; changing them shows Your own mix."
        )
        style_row.Add(style_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, pad)
        style_row.Add(self.style, 1)
        root.Add(style_row, 0, wx.EXPAND | wx.ALL, pad)

        self.remove_fillers = wx.CheckBox(parent, label="Remove filler words li&ke um and uh")
        self.remove_fillers.SetValue(
            bool(getattr(settings, "windows_dictation_remove_fillers", False))
        )
        self.remove_fillers.SetHelpText(
            "Leave out hesitations -- um, uh, erm, hmm -- instead of writing them. "
            "Real words are never removed."
        )
        root.Add(self.remove_fillers, 0, wx.ALL, pad)

        self.self_repair = wx.CheckBox(
            parent, label="Fi&x it when I correct myself, like Thursday, no, Friday"
        )
        self.self_repair.SetValue(bool(getattr(settings, "windows_dictation_self_repair", False)))
        self.self_repair.SetHelpText(
            "When you say no, I mean, or sorry between two days, months, numbers or "
            "names from My Words, only the second is written: Thursday, no, Friday "
            "writes Friday. Everything else is written as you said it, so no, I do "
            "not think so stays as it is. Off by default."
        )
        root.Add(self.self_repair, 0, wx.ALL, pad)
        self._show_style()
        self.style.Bind(wx.EVT_CHOICE, self._on_style)
        for box in (self.remove_fillers, self.self_repair):
            box.Bind(wx.EVT_CHECKBOX, lambda _e: self._show_style())

    def _style_values(self) -> dict[str, object]:
        def more(name: str) -> object:
            return self._more.get(name, getattr(self._settings, name, False))

        return {
            "windows_dictation_remove_fillers": self.remove_fillers.GetValue(),
            "windows_dictation_self_repair": self.self_repair.GetValue(),
            "windows_dictation_polish": more("windows_dictation_polish"),
            "windows_dictation_review_first": more("windows_dictation_review_first"),
        }

    def _show_style(self) -> None:
        """The chooser follows the check boxes: a named style, or Your own mix."""
        style = style_of(self._style_values())
        if style not in self._styles:
            style = CUSTOM_STYLE  # Polished, with AI off here
        self.style.SetSelection(self._styles.index(style))

    def _on_style(self, _event: Any) -> None:
        row = self.style.GetSelection()
        style = self._styles[row] if 0 <= row < len(self._styles) else CUSTOM_STYLE
        wanted = STYLE_FIELDS.get(style)
        if not wanted:
            self._show_style()  # Your own mix changes nothing
            return
        for name, on in wanted.items():
            if name == "windows_dictation_remove_fillers":
                self.remove_fillers.SetValue(on)
            elif name == "windows_dictation_self_repair":
                self.self_repair.SetValue(on)
            else:
                self._more[name] = on  # More Dictation Settings' fields, kept until OK
