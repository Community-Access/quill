"""A small, generic Preferences dialog (Ctrl+,) for the standalone companion
apps (Quill Radio, QUILL Cast) -- a short list of app-level startup toggles
(Resume on Launch, Check for Updates on Startup, ...). Each app supplies its
own checkbox specs and applies the returned values back to its own settings
store; this dialog holds no app-specific knowledge.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(slots=True)
class PreferenceCheckbox:
    """One checkbox: the visible label, its accessible name, and the
    starting value. ``name`` carries the ``&`` mnemonic; ``help_text`` is the
    fuller accessible description set via ``SetName``."""

    name: str
    help_text: str
    value: bool


@dataclass(slots=True)
class PreferenceAction:
    """One utility button (e.g. Quill Radio's "Reset All Stations' Sound
    Enhancements..."): ``name`` carries the ``&`` mnemonic and is the visible
    label, ``help_text`` is the accessible description, ``on_click`` fires
    immediately on click -- independent of Save/Cancel, so it neither waits
    on nor is bundled with whatever else this Preferences visit is editing."""

    name: str
    help_text: str
    on_click: Callable[[], None]


@dataclass(slots=True)
class PreferenceText:
    """One labeled single-line text field: for a free-form value a checkbox or
    a closed choice can't hold (e.g. Quill Radio's "What's Playing"
    announcement template). ``name`` is the field's label (with its ``&``
    mnemonic), ``help_text`` the fuller accessible description set via
    ``SetName``, ``value`` the starting text."""

    name: str
    help_text: str
    value: str


@dataclass(slots=True)
class PreferenceChoice:
    """One labeled combo box row: for a small closed set of options a
    checkbox can't represent (e.g. Radio's "When closing the window").
    ``name`` is the row's own label (no mnemonic collision with the
    checkboxes since it labels a Choice, not a button); ``help_text`` is the
    fuller accessible description set via ``SetName``."""

    name: str
    help_text: str
    options: list[str]
    selected_index: int


class PreferencesDialog:
    """Returns ``(checkbox_values, choice_indices, text_values)`` -- each a
    list in the same order as the input specs (``text_values`` is empty when no
    text fields were supplied) -- or ``None`` on Cancel."""

    def __init__(
        self,
        parent: object,
        *,
        app_title: str,
        checkboxes: list[PreferenceCheckbox],
        choices: list[PreferenceChoice] | None = None,
        texts: list[PreferenceText] | None = None,
        actions: list[PreferenceAction] | None = None,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce_cb or (lambda _m: None)
        self._result: tuple[list[bool], list[int], list[str]] | None = None
        self._checks: list[wx.CheckBox] = []
        self._choice_controls: list[wx.Choice] = []
        self._text_controls: list[wx.TextCtrl] = []
        self._action_buttons: list[wx.Button] = []

        self.dialog = wx.Dialog(
            parent, title=f"{app_title} Preferences", style=wx.DEFAULT_DIALOG_STYLE
        )
        root = wx.BoxSizer(wx.VERTICAL)

        for spec in choices or []:
            row = wx.BoxSizer(wx.HORIZONTAL)
            row.Add(
                wx.StaticText(self.dialog, label=spec.name),
                0,
                wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
                6,
            )
            choice = wx.Choice(self.dialog, choices=list(spec.options))
            choice.SetName(spec.help_text)
            choice.SetSelection(spec.selected_index)
            row.Add(choice, 1, wx.EXPAND)
            root.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
            self._choice_controls.append(choice)

        for spec in checkboxes:
            check = wx.CheckBox(self.dialog, label=spec.name)
            check.SetName(spec.help_text)
            check.SetValue(spec.value)
            root.Add(check, 0, wx.ALL, 8)
            self._checks.append(check)

        for text_spec in texts or []:
            root.Add(
                wx.StaticText(self.dialog, label=text_spec.name),
                0,
                wx.LEFT | wx.RIGHT | wx.TOP,
                8,
            )
            text_ctrl = wx.TextCtrl(self.dialog, value=text_spec.value)
            text_ctrl.SetName(text_spec.help_text)
            root.Add(text_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
            self._text_controls.append(text_ctrl)

        for action_spec in actions or []:
            action_btn = wx.Button(self.dialog, label=action_spec.name)
            action_btn.SetName(action_spec.help_text)
            action_btn.Bind(wx.EVT_BUTTON, lambda _e, cb=action_spec.on_click: cb())
            root.Add(action_btn, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
            self._action_buttons.append(action_btn)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        save_btn = wx.Button(self.dialog, wx.ID_OK, "&OK")
        cancel_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        btn_row.AddStretchSpacer()
        btn_row.Add(save_btn, 0, wx.RIGHT, 6)
        btn_row.Add(cancel_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)
        root.Fit(self.dialog)
        save_btn.Bind(wx.EVT_BUTTON, self._on_save)

    def _capture_result(self) -> None:
        """Snapshot every control's value into ``self._result`` (the returned
        tuple). Split from :meth:`_on_save` so the capture is unit-testable
        without a live modal loop."""
        self._result = (
            [check.GetValue() for check in self._checks],
            [choice.GetSelection() for choice in self._choice_controls],
            [text.GetValue() for text in self._text_controls],
        )

    def _on_save(self, _event: object) -> None:
        self._capture_result()
        self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> tuple[list[bool], list[int], list[str]] | None:
        from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            affirmative_label="OK",
            cancel_id=self._wx.ID_CANCEL,
            escape_id=self._wx.ID_CANCEL,
        )
        try:
            answer = show_modal_dialog(
                self.dialog, f"{self.dialog.GetTitle()}", announce=self._announce
            )
            return self._result if answer == self._wx.ID_OK else None
        finally:
            self.dialog.Destroy()
