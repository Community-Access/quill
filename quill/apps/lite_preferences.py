"""The Preferences window: every setting QuillLite has, in one place.

Split from :mod:`quill.apps.lite_dialogs` because it is the only dialog that
edits state rather than answering a question, and because it is the one window
whose *contents* are the product's settings model -- it grows when the model
does, and the other dialogs do not.

Everything on the View menu is here too -- theme, wrap, the editor font -- because
a Preferences window that answers half the question is a Preferences window
people stop opening. But three settings live *only* here, and they are the reason
it exists: what Control N creates, how often unsaved work is copied aside,
whether last session's documents reopen, whether spelling is checked as you
type, and whether abbreviations and taught words come from QuillLite's own
lists or QUILL's shared ones.
Before this they could be changed only by hand-editing ``settings.json``, which
is not a setting anyone has.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.apps.lite_dialogs import _stack
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name, show_modal_dialog

__all__ = ["edit_preferences"]

#: Uniform padding, matching the other dialogs. One number, so nothing drifts.
_PAD = 8


def edit_preferences(
    parent: wx.Window,
    settings: Any,
    *,
    announce: Callable[[str], None] | None = None,
) -> bool:
    """Edit the settings that have no menu item of their own. ``True`` if changed.

    Everything on the View menu -- theme, wrap, text size -- is here too, because
    a Preferences window that answers half the question is a Preferences window
    people stop opening. But two settings live *only* here, and they are the
    reason it exists: what Ctrl+N creates, and how often unsaved work is copied
    aside. Before this they could be changed only by hand-editing settings.json,
    which is not a setting anyone has.

    The dialog mutates *settings* in place and reports whether anything moved, so
    the caller saves and re-applies exactly once.
    """
    dialog = wx.Dialog(parent, title="Preferences", style=wx.DEFAULT_DIALOG_STYLE)
    root = wx.BoxSizer(wx.VERTICAL)

    mode_label = wx.StaticText(dialog, label="&New documents are:")
    mode_choice = wx.Choice(dialog, choices=["Plain text", "Rich text"])
    set_accessible_name(mode_choice, "New documents are")
    mode_choice.SetHelpText("What Control N creates. New Plain Text and New Rich Text ignore this.")
    mode_choice.SetSelection(1 if settings.default_mode == "rich" else 0)
    _stack(root, mode_label, mode_choice)

    theme_label = wx.StaticText(dialog, label="&Theme:")
    theme_choice = wx.Choice(dialog, choices=["Dark", "Follow the system"])
    set_accessible_name(theme_choice, "Theme")
    theme_choice.SetHelpText(
        "Dark is the default. It changes the view only and is never saved into your documents."
    )
    theme_choice.SetSelection(0 if settings.theme == "dark" else 1)
    _stack(root, theme_label, theme_choice)

    restore = wx.CheckBox(dialog, label="Reopen the documents I had open last &time")
    restore.SetHelpText(
        "Reopen last session's files, in the same numbered order. Different from "
        "recovering unsaved work, which happens whether this is on or not."
    )
    restore.SetValue(bool(settings.restore_session))
    root.Add(restore, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)

    share = wx.CheckBox(dialog, label="Share QUILL's abbre&viation library")
    share.SetHelpText(
        "Off: abbreviations are QuillLite's own. On: read and write the same "
        "library QUILL and Quill Inkwell use, so an abbreviation added in any of "
        "them works in all of them. Turning this on creates a QUILL data folder "
        "if you do not already have one."
    )
    share.SetValue(bool(settings.share_quill_abbreviations))
    root.Add(share, 0, wx.LEFT | wx.RIGHT, _PAD)

    # Beside the abbreviation switch on purpose: they are the same decision
    # asked twice, and two switches that behave differently would be two
    # switches to remember.
    share_dict = wx.CheckBox(dialog, label="Share QUILL's &dictionary of taught words")
    share_dict.SetHelpText(
        "Off: words you teach the spell checker are QuillLite's own. On: read "
        "and write the same dictionary QUILL uses, so a word taught in either "
        "is known to both. Turning this on creates a QUILL data folder if you "
        "do not already have one."
    )
    share_dict.SetValue(bool(settings.share_quill_dictionary))
    root.Add(share_dict, 0, wx.LEFT | wx.RIGHT, _PAD)

    spell_typing = wx.CheckBox(dialog, label="Check &spelling as I type")
    spell_typing.SetHelpText(
        "Report a misspelling in the status bar shortly after you finish a "
        "word. Never in a source or configuration file, whatever this says: "
        "every identifier in one would be a false alarm. F7 reviews the whole "
        "document either way."
    )
    spell_typing.SetValue(bool(settings.spell_check_while_typing))
    root.Add(spell_typing, 0, wx.LEFT | wx.RIGHT, _PAD)

    wrap = wx.CheckBox(dialog, label="&Wrap long lines to the window")
    wrap.SetHelpText("When off, long lines run past the right edge and scroll instead.")
    wrap.SetValue(bool(settings.word_wrap))
    root.Add(wrap, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)

    autosave_label = wx.StaticText(dialog, label="&Copy unsaved work aside every (seconds):")
    autosave = wx.SpinCtrl(dialog, min=15, max=600, initial=int(settings.autosave_seconds))
    set_accessible_name(autosave, "Copy unsaved work aside every, seconds")
    autosave.SetHelpText(
        "How often a modified document is copied to the recovery folder. The copy "
        "is beside your file, never over it, and is removed when you save."
    )
    _stack(root, autosave_label, autosave)

    font_row = wx.BoxSizer(wx.HORIZONTAL)
    font_label = wx.StaticText(dialog, label="Editor &font:")
    chosen = {"name": settings.font_name, "size": int(settings.font_size)}
    font_field = wx.TextCtrl(dialog, value=_font_summary(chosen), style=wx.TE_READONLY)
    set_accessible_name(font_field, "Editor font")
    font_field.SetHelpText("The face and size the editor uses. Choose changes it.")
    choose_btn = wx.Button(dialog, label="&Choose...")
    choose_btn.SetHelpText("Open the font chooser and pick a face and size.")
    font_row.Add(font_field, 1, wx.RIGHT | wx.ALIGN_CENTRE_VERTICAL, _PAD)
    font_row.Add(choose_btn, 0)
    root.Add(font_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
    root.Add(font_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, _PAD)

    def _pick_font(_event: wx.CommandEvent) -> None:
        data = wx.FontData()
        data.SetInitialFont(
            wx.Font(
                chosen["size"],
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
                faceName=str(chosen["name"]),
            )
        )
        with wx.FontDialog(dialog, data) as picker:
            if picker.ShowModal() != wx.ID_OK:
                return
            font = picker.GetFontData().GetChosenFont()
        chosen["name"], chosen["size"] = font.GetFaceName(), font.GetPointSize()
        # The read-out is an unfocused label change, which is exactly what a
        # screen reader does *not* announce -- so the caller's announce hook
        # says it instead (GATE-12's cure, not GATE-13's fault).
        font_field.SetValue(_font_summary(chosen))
        if announce is not None:
            announce(_font_summary(chosen))

    choose_btn.Bind(wx.EVT_BUTTON, _pick_font)

    buttons = dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
    root.Add(buttons, 0, wx.ALIGN_RIGHT | wx.ALL, _PAD)
    dialog.SetSizerAndFit(root)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
    mode_choice.SetFocus()
    try:
        if show_modal_dialog(dialog, "Preferences") != wx.ID_OK:
            return False
        before = (
            settings.default_mode,
            settings.theme,
            settings.word_wrap,
            settings.autosave_seconds,
            settings.font_name,
            settings.font_size,
            settings.restore_session,
            settings.share_quill_abbreviations,
            settings.share_quill_dictionary,
            settings.spell_check_while_typing,
        )
        settings.default_mode = "rich" if mode_choice.GetSelection() == 1 else "plain"
        settings.theme = "dark" if theme_choice.GetSelection() == 0 else "system"
        settings.word_wrap = bool(wrap.GetValue())
        settings.restore_session = bool(restore.GetValue())
        settings.share_quill_abbreviations = bool(share.GetValue())
        settings.share_quill_dictionary = bool(share_dict.GetValue())
        settings.spell_check_while_typing = bool(spell_typing.GetValue())
        settings.autosave_seconds = int(autosave.GetValue())
        settings.font_name = str(chosen["name"])
        settings.font_size = int(chosen["size"])
        settings.normalized()
        return before != (
            settings.default_mode,
            settings.theme,
            settings.word_wrap,
            settings.autosave_seconds,
            settings.font_name,
            settings.font_size,
            settings.restore_session,
            settings.share_quill_abbreviations,
            settings.share_quill_dictionary,
            settings.spell_check_while_typing,
        )
    finally:
        dialog.Destroy()


def _font_summary(chosen: dict[str, Any]) -> str:
    """How the font read-out reads: "Consolas, 12 point" or "System default, 12 point"."""
    name = str(chosen["name"]).strip() or "System default"
    return f"{name}, {int(chosen['size'])} point"
