"""Make a group of check boxes or radio buttons say which group it is.

A ``wx.StaticBox`` (or the box of a ``wx.StaticBoxSizer``) draws a frame and a
caption round a set of controls, the desktop form of an HTML ``fieldset`` and
its ``legend``. On Windows NVDA and JAWS do not reliably speak that caption
when focus moves into a check box inside the box, so a listener hears "Word,
check box, not checked" and is left to guess what Word is for. Jeff found it in
Scribe Options' "Default formats" (2026-11-23).

``wx.RadioBox`` loses its title the same way, and worse: its items are raw
native buttons, not wx windows, so nothing can be attached to them. This module
therefore offers two things:

* :func:`describe_group` gives each control a ``wx.Accessible`` whose
  ``accDescription`` starts with the group's caption, followed by the help
  text wxMSW already put there. Its ``accName`` is not touched: it stays the
  control's own visible label, so a check box reads "Word, check box, not
  checked, Default formats. Checked in the convert dialog...": the name
  first, the group after, the way a reader announces a field inside a
  fieldset.
* :class:`GroupedRadioBox` is a drop-in for ``wx.RadioBox``: the same caption
  and choices, built as real ``wx.RadioButton`` windows inside a static box, so
  each one can carry the caption too. It answers the ``wx.RadioBox`` calls the
  family uses and sends ``EVT_RADIOBOX``, so handlers need no change.

Both are no-ops for the accessible part off Windows, or where wxPython was
built without ``wx.Accessible``: the controls are still built and work, they
just carry no description. Never raises: a description is never worth a
broken dialog.

``SetAccessible`` does not keep a Python reference, so each helper is kept on
its control *and* on the control's top-level window. Without a live reference
the helper is collected and the description tests as present and speaks as
absent (the same lesson as :mod:`quill.ui.spoken_name` and
:mod:`quill.ui.audio_studio.pages_base`).

What a screen reader actually says can only be proved with NVDA and JAWS
running; the unit tests prove what the accessible object answers.
"""

from __future__ import annotations

import math
import sys
from typing import Any

try:  # wx is optional for the fakes-based tests that import this module.
    import wx
except Exception:  # noqa: BLE001 - no wx at all: every call is a no-op
    wx = None  # type: ignore[assignment]

__all__ = ["GroupedRadioBox", "describe_group", "group_description", "group_name"]

#: Where the helper is kept on its control.
_HELPER_ATTR = "_quill_group_helper"
#: Where every helper of a window is also kept, on its top-level window.
_ANCHOR_ATTR = "_quill_group_helpers"

#: The ``wx.Accessible`` subclass once built; ``False`` once known unavailable.
_MEMBER_CLASS: Any = None


def _clean(label: object) -> str:
    from quill.ui.accessible_names import accessible_label

    return accessible_label(label)


def group_name(group: object) -> str:
    """The speakable caption of *group*: a string, a static box or its sizer."""
    if isinstance(group, str):
        return _clean(group)
    box = group
    get_box = getattr(group, "GetStaticBox", None)
    if callable(get_box):
        try:
            box = get_box()
        except Exception:  # noqa: BLE001
            return ""
    get_label = getattr(box, "GetLabel", None)
    if not callable(get_label):
        return ""
    try:
        return _clean(get_label())
    except Exception:  # noqa: BLE001
        return ""


def _member_class() -> type | None:
    """The ``wx.Accessible`` subclass, built once; ``None`` where unavailable."""
    global _MEMBER_CLASS
    if _MEMBER_CLASS is not None:
        return _MEMBER_CLASS or None
    accessible = getattr(wx, "Accessible", None) if wx is not None else None
    if accessible is None or sys.platform != "win32":
        _MEMBER_CLASS = False
        return None
    acc_ok = wx.ACC_OK
    not_implemented = wx.ACC_NOT_IMPLEMENTED

    class _GroupMember(accessible):  # type: ignore[misc, valid-type]
        """Adds the group to the description; defers on everything else.

        Name, role, state and default action all fall through to the standard
        object Windows builds for the control (``ACC_NOT_IMPLEMENTED``), so the
        name stays the visible label with its ``&`` removed, and the checked
        state and its change events are the control's own. The name is
        answered only when one was given on purpose (:mod:`quill.ui.
        spoken_name`), which this helper would otherwise hide.
        """

        def __init__(self, window: Any, group: str) -> None:
            super().__init__(window)
            self.group = group
            #: A name set by quill.ui.spoken_name on the fallback path.
            self.spoken_name = ""

        def _window(self) -> Any:
            try:
                return self.GetWindow()
            except Exception:  # noqa: BLE001
                return None

        def GetName(self, childId: int) -> tuple[int, str]:  # noqa: N802,N803 - wx API casing
            if childId != 0:
                return (not_implemented, "")
            window = self._window()
            native = getattr(window, "_quill_native_spoken_name", "") if window else ""
            name = self.spoken_name or native
            return (acc_ok, str(name)) if name else (not_implemented, "")

        def _help(self) -> str:
            window = self._window()
            try:
                return str(window.GetHelpText() or "").strip() if window else ""
            except Exception:  # noqa: BLE001
                return ""

        def GetDescription(self, childId: int) -> tuple[int, str]:  # noqa: N802,N803
            if childId != 0 or not self.group:
                return (not_implemented, "")
            # wxMSW's own accessible answered the help text here, and NVDA reads
            # it after the state; it stays, after the group, so nothing is lost.
            help_text = self._help()
            if help_text:
                return (acc_ok, f"{self.group}. {help_text}")
            return (acc_ok, self.group)

        def GetHelpText(self, childId: int) -> tuple[int, str]:  # noqa: N802,N803
            help_text = self._help() if childId == 0 else ""
            return (acc_ok, help_text) if help_text else (not_implemented, "")

    _MEMBER_CLASS = _GroupMember
    return _GroupMember


def _anchor(control: Any, helper: Any) -> None:
    try:
        setattr(control, _HELPER_ATTR, helper)
    except Exception:  # noqa: BLE001
        pass
    top = None
    try:
        top = wx.GetTopLevelParent(control)
    except Exception:  # noqa: BLE001
        top = None
    if top is None or top is control:
        return
    try:
        helpers = getattr(top, _ANCHOR_ATTR, None)
        if helpers is None:
            helpers = []
            setattr(top, _ANCHOR_ATTR, helpers)
        helpers.append(helper)
    except Exception:  # noqa: BLE001
        pass


def describe_group(group: object, *controls: Any) -> int:
    """Give each of *controls* the caption of *group* as its description.

    *group* is the ``wx.StaticBoxSizer``, the ``wx.StaticBox`` or the caption
    itself; its ``&`` mnemonic and trailing colon are not spoken. Each control
    keeps its own label as its name. Calling it again updates the description
    rather than stacking a second helper. Returns how many controls now carry
    the description: 0 off Windows, without ``wx.Accessible``, or for an empty
    caption.
    """
    name = group_name(group)
    cls = _member_class()
    if cls is None or not name:
        return 0
    done = 0
    for control in controls:
        if control is None:
            continue
        existing = getattr(control, _HELPER_ATTR, None)
        if existing is not None:
            existing.group = name
            done += 1
            continue
        try:
            helper = cls(control, name)
            earlier = getattr(control, "_spoken_name_helper", None)
            if earlier is not None:
                helper.spoken_name = str(getattr(earlier, "spoken_name", "") or "")
            control.SetAccessible(helper)
        except (AttributeError, NotImplementedError, TypeError, RuntimeError):
            continue
        _anchor(control, helper)
        done += 1
    return done


def group_description(control: Any) -> str:
    """The group caption :func:`describe_group` gave *control*, or ``""``.

    For tests and diagnostics. The description a reader hears is this, then the
    control's help text when it has one.
    """
    helper = getattr(control, _HELPER_ATTR, None)
    return str(helper.group) if helper is not None else ""


def _access_key(label: object) -> str:
    """The lower-case ``&`` access key of *label*, or ``""`` (``&&`` is a literal)."""
    text = str(label or "").replace("&&", "")
    at = text.find("&")
    if at < 0 or at + 1 >= len(text):
        return ""
    return text[at + 1].lower()


_PanelBase: Any = wx.Panel if wx is not None else object


class GroupedRadioBox(_PanelBase):  # type: ignore[misc, valid-type]
    """A ``wx.RadioBox`` whose choices say which question they answer.

    Built as a static box of ``wx.RadioButton`` windows (the first starts the
    group, so the arrow keys move between them and Tab leaves), each described
    with the caption by :func:`describe_group`. Construct it exactly as a
    ``wx.RadioBox``. The caption keeps its ``&`` access key, which moves focus
    to the chosen button.
    """

    def __init__(
        self,
        parent: Any,
        id: int = -1,  # noqa: A002 - wx.RadioBox's own parameter name
        label: str = "",
        pos: Any = None,
        size: Any = None,
        choices: Any = (),
        majorDimension: int = 0,  # noqa: N803 - wx.RadioBox's own parameter name
        style: int = 0,
        validator: Any = None,
        name: str = "radioBox",
    ) -> None:
        del validator  # accepted for the wx.RadioBox signature; never used here
        super().__init__(
            parent,
            id,
            pos if pos is not None else wx.DefaultPosition,
            size if size is not None else wx.DefaultSize,
            style=wx.TAB_TRAVERSAL,
            name=name,
        )
        self._sizer = wx.StaticBoxSizer(wx.VERTICAL, self, label)
        box = self._sizer.GetStaticBox()
        self._box = box
        self._buttons: list[Any] = []
        self._item_help: dict[int, str] = {}
        labels = [str(choice) for choice in choices]
        count = len(labels)
        major = majorDimension if majorDimension > 0 else max(count, 1)
        by_rows = bool(style & getattr(wx, "RA_SPECIFY_ROWS", 0))
        if by_rows:
            rows, cols = major, max(1, math.ceil(count / major))
        else:
            cols = major
            rows = max(1, math.ceil(count / cols))
        self._rows, self._cols = rows, cols
        grid = wx.GridBagSizer(2, 8)
        for index, text in enumerate(labels):
            button = wx.RadioButton(box, label=text, style=wx.RB_GROUP if index == 0 else 0)
            button.Bind(wx.EVT_RADIOBUTTON, self._on_button)
            if by_rows:
                where = (index % rows, index // rows)
            else:
                where = (index // cols, index % cols)
            grid.Add(button, wx.GBPosition(*where), flag=wx.ALL, border=2)
            self._buttons.append(button)
        self._sizer.Add(grid, 0, wx.ALL, 2)
        if self._buttons:
            self._buttons[0].SetValue(True)
        describe_group(self._sizer, *self._buttons)
        self.SetSizer(self._sizer)
        self.Fit()
        self._access_key = _access_key(label)
        self._hooked: Any = None
        top = wx.GetTopLevelParent(self)
        if isinstance(top, wx.Dialog):
            # Neither a wx.RadioBox caption nor a static box caption moves
            # focus on its access key in wxMSW (checked 2026-11-23), so the key
            # the caption advertises is honoured here. Only in a dialog: in a
            # frame the hook would run before the menu bar and take its Alt
            # keys. GATE-14 keeps the letter unique within the dialog.
            top.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
            self._hooked = top
            self.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)

    # ------------------------------------------------------------ events

    def _on_destroy(self, event: Any) -> None:
        event.Skip()
        if event.GetEventObject() is not self or self._hooked is None:
            return
        try:
            self._hooked.Unbind(wx.EVT_CHAR_HOOK, handler=self._on_char_hook)
        except Exception:  # noqa: BLE001 - the dialog may be going too
            pass
        self._hooked = None

    def _on_char_hook(self, event: Any) -> None:
        try:
            alive = bool(self)
        except Exception:  # noqa: BLE001
            alive = False
        if (
            not alive
            or not self._access_key
            or not event.AltDown()
            or event.ControlDown()
            or event.ShiftDown()
            or not self.IsShownOnScreen()
            or not self.IsEnabled()
        ):
            event.Skip()
            return
        key = event.GetUnicodeKey()
        if key in (0, getattr(wx, "WXK_NONE", 0)) or chr(key).lower() != self._access_key:
            event.Skip()
            return
        self.SetFocus()

    def _on_button(self, event: Any) -> None:
        button = event.GetEventObject()
        if button not in self._buttons:
            event.Skip()
            return
        index = self._buttons.index(button)
        out = wx.CommandEvent(wx.wxEVT_RADIOBOX, self.GetId())
        out.SetEventObject(self)
        out.SetInt(index)
        out.SetString(self._buttons[index].GetLabel())
        # Stands in for the button's own event, as a wx.RadioBox does.
        self.GetEventHandler().ProcessEvent(out)

    # ------------------------------------------------------- wx.RadioBox

    def GetSelection(self) -> int:  # noqa: N802 - wx.RadioBox API
        for index, button in enumerate(self._buttons):
            if button.GetValue():
                return index
        return wx.NOT_FOUND

    def SetSelection(self, n: int) -> None:  # noqa: N802
        if 0 <= n < len(self._buttons):
            self._buttons[n].SetValue(True)

    def GetStringSelection(self) -> str:  # noqa: N802
        index = self.GetSelection()
        return self.GetString(index) if index != wx.NOT_FOUND else ""

    def SetStringSelection(self, string: str) -> bool:  # noqa: N802
        index = self.FindString(string)
        if index == wx.NOT_FOUND:
            return False
        self.SetSelection(index)
        return True

    def FindString(self, string: str, bCase: bool = False) -> int:  # noqa: N802,N803
        for index, button in enumerate(self._buttons):
            text = button.GetLabel()
            if text == string or (not bCase and text.lower() == str(string).lower()):
                return index
        return wx.NOT_FOUND

    def GetCount(self) -> int:  # noqa: N802
        return len(self._buttons)

    def GetString(self, n: int) -> str:  # noqa: N802
        if 0 <= n < len(self._buttons):
            return str(self._buttons[n].GetLabel())
        return ""

    def SetString(self, n: int, string: str) -> None:  # noqa: N802
        if 0 <= n < len(self._buttons):
            self._buttons[n].SetLabel(string)

    def GetItemLabel(self, n: int) -> str:  # noqa: N802
        return self.GetString(n)

    def SetItemLabel(self, n: int, string: str) -> None:  # noqa: N802
        self.SetString(n, string)

    def EnableItem(self, n: int, enable: bool = True) -> bool:  # noqa: N802
        if 0 <= n < len(self._buttons):
            return bool(self._buttons[n].Enable(enable))
        return False

    def IsItemEnabled(self, n: int) -> bool:  # noqa: N802
        return 0 <= n < len(self._buttons) and bool(self._buttons[n].IsEnabled())

    def ShowItem(self, item: int, show: bool = True) -> bool:  # noqa: N802
        if 0 <= item < len(self._buttons):
            changed = bool(self._buttons[item].Show(show))
            self.Layout()
            return changed
        return False

    def IsItemShown(self, n: int) -> bool:  # noqa: N802
        return 0 <= n < len(self._buttons) and bool(self._buttons[n].IsShown())

    def SetItemToolTip(self, item: int, text: str) -> None:  # noqa: N802
        if 0 <= item < len(self._buttons):
            self._buttons[item].SetToolTip(text)

    def SetItemHelpText(self, n: int, helpText: str) -> None:  # noqa: N802,N803
        if 0 <= n < len(self._buttons):
            self._item_help[n] = helpText
            self._buttons[n].SetHelpText(helpText)

    def GetItemHelpText(self, n: int) -> str:  # noqa: N802
        if 0 <= n < len(self._buttons):
            return str(self._buttons[n].GetHelpText())
        return ""

    def GetItemFromPoint(self, pt: Any) -> int:  # noqa: N802
        for index, button in enumerate(self._buttons):
            if button.GetScreenRect().Contains(self.ClientToScreen(pt)):
                return index
        return wx.NOT_FOUND

    def GetColumnCount(self) -> int:  # noqa: N802
        return self._cols

    def GetRowCount(self) -> int:  # noqa: N802
        return self._rows

    # ------------------------------------------------ wx.Window overrides

    def SetHelpText(self, helpText: str) -> None:  # noqa: N802,N803
        """F1 answers from the focused button, so every button carries it."""
        super().SetHelpText(helpText)
        for index, button in enumerate(self._buttons):
            if index not in self._item_help:
                button.SetHelpText(helpText)

    def SetToolTip(self, tip: Any) -> None:  # noqa: N802
        super().SetToolTip(tip)
        for button in self._buttons:
            button.SetToolTip(tip)

    def GetLabel(self) -> str:  # noqa: N802
        return str(self._box.GetLabel())

    def SetLabel(self, label: str) -> None:  # noqa: N802
        self._box.SetLabel(label)
        self._access_key = _access_key(label)
        describe_group(label, *self._buttons)

    def SetFocus(self) -> None:  # noqa: N802
        """Focus lands on the chosen button, as it does in a ``wx.RadioBox``."""
        index = self.GetSelection()
        if self._buttons:
            self._buttons[index if index != wx.NOT_FOUND else 0].SetFocus()
        else:
            super().SetFocus()

    def buttons(self) -> list[Any]:
        """The radio buttons, in order (for tests and for focus code)."""
        return list(self._buttons)
