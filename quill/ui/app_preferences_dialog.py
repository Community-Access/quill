"""A small, generic Preferences dialog (Ctrl+,) for the standalone companion
apps (Quill Radio, QUILL Cast) -- a short list of app-level startup toggles
(Resume on Launch, Check for Updates on Startup, ...). Each app supplies its
own checkbox specs and applies the returned values back to its own settings
store; this dialog holds no app-specific knowledge.

**Specs can name a group** (list.md 8.1). Anything that names one is drawn
inside a labelled ``wx.StaticBox``, in first-appearance order, after the
ungrouped run. That is what stops twenty toggles reading as twenty unrelated
facts -- and a static box is a real grouping control, so a screen reader
announces the group on entering it rather than leaving somebody to infer it
from the order. An app that names no group gets exactly the layout it had
before groups existed, control for control.

**The returned lists stay in spec order regardless of the layout.** Callers
unpack by position, so a grouped arrangement that reordered its results would
silently and completely corrupt somebody's settings.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class PreferenceCheckbox:
    """One checkbox: the visible label, its accessible name, and the
    starting value. ``name`` carries the ``&`` mnemonic; ``help_text`` is the
    fuller accessible description set via ``SetName`` and ``SetHelpText``."""

    name: str
    help_text: str
    value: bool
    #: Which labelled box this belongs in; empty for the ungrouped
    #: run at the top of the dialog.
    group: str = ""


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
    #: Which labelled box this belongs in; empty for the ungrouped
    #: run at the top of the dialog.
    group: str = ""


@dataclass(slots=True)
class PreferenceText:
    """One labeled single-line text field: for a free-form value a checkbox or
    a closed choice can't hold (e.g. Quill Radio's "What's Playing"
    announcement template). ``name`` is the field's label (with its ``&``
    mnemonic), ``help_text`` the fuller accessible description, ``value`` the
    starting text."""

    name: str
    help_text: str
    value: str
    #: Which labelled box this belongs in; empty for the ungrouped
    #: run at the top of the dialog.
    group: str = ""


@dataclass(slots=True)
class PreferenceChoice:
    """One labeled combo box row: for a small closed set of options a
    checkbox can't represent (e.g. Radio's "When closing the window").
    ``name`` is the row's own label (no mnemonic collision with the
    checkboxes since it labels a Choice, not a button); ``help_text`` is the
    fuller accessible description."""

    name: str
    help_text: str
    options: list[str]
    selected_index: int
    #: Which labelled box this belongs in; empty for the ungrouped
    #: run at the top of the dialog.
    group: str = ""


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
        self._action_buttons: list[Any] = []

        self.dialog = wx.Dialog(
            parent, title=f"{app_title} Preferences", style=wx.DEFAULT_DIALOG_STYLE
        )
        root = wx.BoxSizer(wx.VERTICAL)

        # Slots, so every returned list stays in *spec* order however the boxes
        # are arranged on screen. A caller unpacks by position.
        self._choice_controls: list[Any] = [None] * len(choices or [])
        self._checks: list[Any] = [None] * len(checkboxes)
        self._text_controls: list[Any] = [None] * len(texts or [])

        for group in self._group_order(choices, checkboxes, texts, actions):
            sizer, parent_window = self._container(root, group)
            for index, choice_spec in enumerate(choices or []):
                if choice_spec.group == group:
                    self._choice_controls[index] = self._add_choice(
                        sizer, parent_window, choice_spec
                    )
            for index, check_spec in enumerate(checkboxes):
                if check_spec.group == group:
                    self._checks[index] = self._add_check(sizer, parent_window, check_spec)
            for index, text_spec in enumerate(texts or []):
                if text_spec.group == group:
                    self._text_controls[index] = self._add_text(sizer, parent_window, text_spec)
            for action_spec in actions or []:
                if action_spec.group == group:
                    self._action_buttons.append(self._add_action(sizer, parent_window, action_spec))

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

    # -- layout ---------------------------------------------------------------

    @staticmethod
    def _group_order(*spec_lists: Any) -> list[str]:
        """Group names in first-appearance order, ungrouped always first.

        First appearance rather than alphabetical: the caller wrote them in an
        order, and that order is a judgement about what somebody looks for
        first. Sorting would replace it with the alphabet.
        """
        seen: list[str] = [""]
        for specs in spec_lists:
            for spec in specs or []:
                group = str(getattr(spec, "group", "") or "")
                if group and group not in seen:
                    seen.append(group)
        return seen

    def _container(self, root: Any, group: str) -> tuple[Any, Any]:
        """``(sizer to add into, window to parent controls to)`` for *group*.

        An ungrouped run goes straight onto the dialog, exactly as it did
        before groups existed, so an app that names no group is unaffected.
        Controls in a group are parented to the box itself rather than to the
        dialog: wxMSW walks the real parent chain when it reports a control's
        grouping, so parenting to the dialog would draw a box the screen
        reader never mentions.
        """
        wx = self._wx
        if not group:
            return (root, self.dialog)
        box = wx.StaticBox(self.dialog, label=group)
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        root.Add(sizer, 0, wx.EXPAND | wx.ALL, 8)
        return (sizer, box)

    def _describe(self, control: Any, help_text: str) -> None:
        """One sentence, said two ways.

        ``SetName`` is what focus announces; ``SetHelpText`` is what F1
        answers. Different mechanisms, so both -- a control that names itself
        and then has nothing to say when asked is half a control.
        """
        control.SetName(help_text)
        control.SetHelpText(help_text)

    def _add_choice(self, sizer: Any, parent: Any, spec: PreferenceChoice) -> Any:
        wx = self._wx
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(parent, label=spec.name), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        choice = wx.Choice(parent, choices=list(spec.options))
        self._describe(choice, spec.help_text)
        choice.SetSelection(spec.selected_index)
        row.Add(choice, 1, wx.EXPAND)
        sizer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)
        return choice

    def _add_check(self, sizer: Any, parent: Any, spec: PreferenceCheckbox) -> Any:
        check = self._wx.CheckBox(parent, label=spec.name)
        self._describe(check, spec.help_text)
        check.SetValue(spec.value)
        sizer.Add(check, 0, self._wx.ALL, 8)
        return check

    def _add_text(self, sizer: Any, parent: Any, spec: PreferenceText) -> Any:
        wx = self._wx
        sizer.Add(wx.StaticText(parent, label=spec.name), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        text_ctrl = wx.TextCtrl(parent, value=spec.value)
        self._describe(text_ctrl, spec.help_text)
        sizer.Add(text_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        return text_ctrl

    def _add_action(self, sizer: Any, parent: Any, spec: PreferenceAction) -> Any:
        wx = self._wx
        button = wx.Button(parent, label=spec.name)
        self._describe(button, spec.help_text)
        button.Bind(wx.EVT_BUTTON, lambda _e, cb=spec.on_click: cb())
        sizer.Add(button, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        return button

    # -- results --------------------------------------------------------------

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
