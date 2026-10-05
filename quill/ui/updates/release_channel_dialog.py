"""Help > Release Channel...: choose Stable, Beta or Dev (plan 7.2).

**Choosing never happens on a selection change.** Arrowing through Stable,
Beta and Dev only rewrites the "What this means" box; nothing is asked and
nothing changes until Switch. A chooser that opened a warning per arrow press
would be hostile to exactly the people this family is for.

Tab order: the three choices (one radio group, announced with its label), the
read-only "What this means" box, the "Also move my other QuillVille apps"
checkboxes (every one unchecked), Update History, Switch, Close. Escape is
Close. Focus starts on the current choice.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import wx

from quill.core.updater.channels import CHANNELS, ChannelState, channel_label, channel_meaning
from quill.core.updater.switch import SwitchPlan
from quill.core.updater.wording import chooser_title
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button

__all__ = ["ReleaseChannelDialog", "SiblingRow"]

#: (app key, display name, current state) for each sibling that can move too.
SiblingRow = tuple[str, str, ChannelState]


class ReleaseChannelDialog(wx.Dialog):  # type: ignore[misc]
    """The chooser. Read :meth:`chosen` and :meth:`also_move` after ``wx.ID_OK``."""

    def __init__(
        self,
        parent: Any,
        *,
        app_name: str,
        state: ChannelState,
        siblings: Sequence[SiblingRow],
        describe: Callable[[str, tuple[str, ...]], SwitchPlan],
        show_history: Callable[[], None],
    ) -> None:
        super().__init__(
            parent,
            title=chooser_title(app_name),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._describe = describe
        self._show_history = show_history
        self._sibling_keys: list[str] = []
        self._sibling_boxes: list[Any] = []
        sizer = wx.BoxSizer(wx.VERTICAL)

        labels = [channel_label(channel) for channel in CHANNELS]
        self._choices = wx.RadioBox(
            self,
            label="&Choose a release channel",
            choices=labels,
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS,
        )
        self._choices.SetHelpText(
            "Stable, Beta or Dev. Arrowing through them only explains each one in "
            "the box below; nothing changes until you choose Switch."
        )
        for index, channel in enumerate(CHANNELS):
            self._choices.SetItemHelpText(index, channel_meaning(channel))
        self._choices.SetSelection(CHANNELS.index(state.channel))
        sizer.Add(self._choices, 0, wx.EXPAND | wx.ALL, 12)

        meaning_label = wx.StaticText(self, label="&What this means:")
        sizer.Add(meaning_label, 0, wx.LEFT | wx.RIGHT, 12)
        self._meaning = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
            size=(-1, 150),
        )
        self._meaning.SetName("What this means")
        self._meaning.SetHelpText(
            "What the selected channel means, and exactly what choosing Switch "
            "would do for this app. Read-only."
        )
        sizer.Add(self._meaning, 1, wx.EXPAND | wx.ALL, 12)

        if siblings:
            group = wx.StaticBoxSizer(
                wx.VERTICAL, self, "Also move my other QuillVille apps on this computer"
            )
            for key, name, sibling_state in siblings:
                box = wx.CheckBox(
                    group.GetStaticBox(),
                    label=f"{name}, now on {channel_label(sibling_state.channel)}",
                )
                box.SetHelpText(
                    f"Check to move {name} to the same channel in the same step. "
                    "Apps that share the QuillVille engine are safest moved together."
                )
                box.Bind(wx.EVT_CHECKBOX, self._refresh)
                group.Add(box, 0, wx.ALL, 4)
                self._sibling_keys.append(key)
                self._sibling_boxes.append(box)
            sizer.Add(group, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        history = wx.Button(self, label="Update &History...")
        history.SetHelpText("What the updater has done for this app, newest first. Read-only.")
        history.Bind(wx.EVT_BUTTON, lambda _e: self._show_history())
        buttons.Add(history, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer()
        self._switch = wx.Button(self, wx.ID_OK, label="&Switch")
        self._switch.SetHelpText(
            "Move to the selected channel. Moving to Beta or Dev asks first and "
            "saves a copy of your settings before anything changes."
        )
        buttons.Add(self._switch, 0, wx.RIGHT, 6)
        close = wx.Button(self, wx.ID_CANCEL, label="Close")
        close.SetHelpText("Close without changing anything.")
        bind_close_button(self, close, modeless=False)
        buttons.Add(close, 0)
        sizer.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        self.SetSizerAndFit(sizer)
        self.SetSize((560, -1))
        apply_modal_ids(self, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        self._choices.Bind(wx.EVT_RADIOBOX, self._refresh)
        self._refresh(None)
        self._choices.SetFocus()

    # -- answers -----------------------------------------------------------

    def chosen(self) -> str:
        return CHANNELS[max(0, self._choices.GetSelection())]

    def also_move(self) -> tuple[str, ...]:
        return tuple(
            key
            for key, box in zip(self._sibling_keys, self._sibling_boxes, strict=True)
            if box.GetValue()
        )

    # -- the explanation box -----------------------------------------------

    def _refresh(self, _event: object) -> None:
        channel = self.chosen()
        plan = self._describe(channel, self.also_move())
        text = f"{channel_label(channel)}: {channel_meaning(channel)}\n\n{plan.summary()}"
        self._meaning.SetValue(text)
        # Switch is the default only when it cannot raise the risk: Enter on a
        # riskier choice should not be the way somebody moves to Dev.
        if plan.kind in ("join",):
            self.SetDefaultItem(None)
        else:
            self._switch.SetDefault()
