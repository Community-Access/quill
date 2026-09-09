"""Building a settings control from a catalogue entry, once.

Twenty-five per-podcast settings arrived together, and hand-building
twenty-five controls would have meant twenty-five chances to forget a label, a
help string, an access key or the "follows the shared default" state -- and a
twenty-sixth setting next month needing all five again.

So the controls are **generated from the catalogue**
(:mod:`quill.core.podcasts.settings_catalog`). One function per kind, each
producing a control that is correctly labelled, correctly helped, and reads and
writes through the resolver. A setting added to the catalogue appears here with
no code at all, which is the only way a settings surface this size stays
honest.

Three things this does that a hand-built form kept forgetting:

* **Every control says where its value came from.** "Every 60 minutes, from the
  folder News" is an answer; "60" is a reading of a box. It is in the help, so
  F1 answers it, and it is refreshed when the value changes.
* **Following and setting are different states.** A control shows the value in
  force whatever level answered, and a *Follow* button beside it clears this
  level's opinion rather than writing the default over it -- which is the
  distinction the whole four-level model exists to preserve.
* **Label before control, always.** A screen reader associates a label with the
  control created after it, so this builds them in that order and never in the
  other (the z-order contract).

This module builds; it does not own a window. The windows are
``show_settings_dialog`` (one podcast) and ``settings_search_dialog`` (any
setting, found by name).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from quill.core.podcasts.settings_resolver import (
    Resolved,
    clear_value,
    describe_provenance,
    has_override,
    resolve,
    set_value,
)
from quill.core.podcasts.settings_types import (
    KIND_BOOL,
    KIND_CHOICE,
    KIND_FLOAT,
    KIND_INT,
    KIND_OPAQUE,
    KIND_TEXT,
    LEVEL_SHOW,
    SettingDef,
)

__all__ = ["SettingControl", "build_control"]


@dataclass
class SettingControl:
    """One built control, and everything the window needs to work with it."""

    definition: SettingDef
    control: Any
    follow_button: Any = None
    #: What the value was when the window opened, so Save writes only changes.
    original: object = None
    #: The level that answered when the window opened.
    resolved: Resolved | None = None

    def read(self) -> object:
        """What the control currently says, coerced to the setting's kind."""
        definition = self.definition
        if definition.kind == KIND_CHOICE:
            index = max(0, self.control.GetSelection())
            values = [choice.value for choice in definition.choices]
            return values[index] if index < len(values) else definition.default
        if definition.kind == KIND_BOOL:
            return bool(self.control.GetValue())
        if definition.kind in (KIND_INT, KIND_FLOAT):
            return definition.coerce(self.control.GetValue())
        if definition.kind == KIND_TEXT:
            return str(self.control.GetValue())
        return self.original

    @property
    def editable(self) -> bool:
        """Whether this control writes a value at all.

        An opaque setting -- a rule list, a set of labels -- has its own window
        and a button here rather than a value, so Save must not try to write it.
        """
        return self.definition.kind != KIND_OPAQUE


def build_control(
    parent: Any,
    sizer: Any,
    definition: SettingDef,
    *,
    library: Any,
    show: Any,
    wx: Any,
    on_edit: Callable[[SettingDef], None] | None = None,
) -> SettingControl:
    """Build one setting's label, control and Follow button into *sizer*.

    Reads the value in force through the resolver, so a control shows what the
    podcast actually does -- inherited from its folder or from the shared
    default included. An editor that opens on a blank misreports the setting it
    exists to change, which is the failure this whole surface is built to avoid.
    """
    answer = resolve(library, definition, show=show)
    label_text = definition.label
    if definition.kind == KIND_BOOL:
        # A checkbox carries its own label, so a separate one would be read
        # twice. The grid still gets a spacer, to keep the two columns aligned.
        sizer.Add(wx.StaticText(parent, label=""), 0)
        control = wx.CheckBox(parent, label=label_text)
        control.SetValue(bool(answer.value))
        control.SetHelpText(_help_for(definition, answer))
        sizer.Add(control, 1, wx.EXPAND)
        return _finish(definition, control, answer, parent, sizer, library, show, wx)

    sizer.Add(wx.StaticText(parent, label=label_text), 0, wx.ALIGN_CENTER_VERTICAL)

    if definition.kind == KIND_CHOICE:
        control = wx.Choice(parent, choices=[choice.label for choice in definition.choices])
        values = [choice.value for choice in definition.choices]
        control.SetSelection(values.index(answer.value) if answer.value in values else 0)
    elif definition.kind == KIND_INT:
        control = wx.SpinCtrl(
            parent, min=int(definition.minimum), max=int(definition.maximum or 999999)
        )
        control.SetValue(int(answer.value))  # type: ignore[arg-type]
    elif definition.kind == KIND_FLOAT:
        control = wx.SpinCtrlDouble(
            parent,
            min=definition.minimum,
            max=definition.maximum or 100.0,
            inc=0.1,
            initial=float(answer.value),  # type: ignore[arg-type]
        )
        control.SetDigits(1)
    elif definition.kind == KIND_OPAQUE:
        control = wx.Button(parent, label=definition.label)
        if on_edit is not None:
            control.Bind(wx.EVT_BUTTON, lambda _event, d=definition: on_edit(d))
    else:
        control = wx.TextCtrl(parent)
        control.SetValue(str(answer.value or ""))

    control.SetName(definition.label_text().rstrip(":"))
    control.SetHelpText(_help_for(definition, answer))
    sizer.Add(control, 1, wx.EXPAND)
    return _finish(definition, control, answer, parent, sizer, library, show, wx)


def _help_for(definition: SettingDef, answer: Resolved) -> str:
    """The setting's help, plus where its current value came from.

    Both, in that order: what it does is the durable half and belongs first,
    and where this podcast's value came from is the half that answers "why is
    this one different?" without opening three windows.
    """
    return f"{definition.help} {describe_provenance(definition, answer)}"


def _finish(
    definition: SettingDef,
    control: Any,
    answer: Resolved,
    parent: Any,
    sizer: Any,
    library: Any,
    show: Any,
    wx: Any,
) -> SettingControl:
    """Add the Follow button for a setting this podcast has an opinion about.

    Present only when there is something to clear, because a button that is
    always there and usually does nothing is a button somebody stops reading.
    Its label names what it would fall back to, so pressing it is never a
    surprise.
    """
    built = SettingControl(
        definition=definition,
        control=control,
        original=answer.value,
        resolved=answer,
    )
    if definition.kind == KIND_OPAQUE or not has_override(
        library, definition, level=LEVEL_SHOW, scope_id=show.id
    ):
        return built
    button = wx.Button(parent, label="Follow")
    button.SetName(f"Stop overriding {definition.label_text().rstrip(':')} for this podcast")
    button.SetHelpText(
        "Drops this podcast's own answer for this setting, so it follows its "
        "folder or the shared default again. It changes this setting only, and "
        "no episode, download or queue entry is touched."
    )
    sizer.Add(wx.StaticText(parent, label=""), 0)
    sizer.Add(button, 0)
    built.follow_button = button
    return built


def apply_controls(library: Any, show: Any, controls: list[SettingControl]) -> list[SettingDef]:
    """Write back every control whose value changed; returns which changed.

    Only what changed, and only as *this podcast's* opinion -- a control left
    alone writes nothing at all, so opening this window and pressing Save does
    not silently freeze ninety-three settings at today's shared defaults. That
    was the old dialog's actual behaviour and the reason the four-level model
    exists.
    """
    changed: list[SettingDef] = []
    for built in controls:
        if not built.editable:
            continue
        value = built.read()
        if value == built.original:
            continue
        if set_value(library, built.definition, value, level=LEVEL_SHOW, scope_id=show.id):
            changed.append(built.definition)
    return changed


def follow_again(library: Any, show: Any, definition: SettingDef) -> bool:
    """Clear this podcast's opinion about one setting."""
    return clear_value(library, definition, level=LEVEL_SHOW, scope_id=show.id)
