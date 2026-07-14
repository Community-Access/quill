from __future__ import annotations

import sys
from types import SimpleNamespace

from quill.core.commands import CommandRegistry
from quill.ui.palette import CommandPaletteDialog


class _Event:
    def __init__(self, key_code: int) -> None:
        self._key_code = key_code
        self.skipped = False

    def GetKeyCode(self) -> int:
        return self._key_code

    def Skip(self) -> None:
        self.skipped = True


class _Dialog:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self._result = 0
        self.ended_with: int | None = None

    def SetName(self, _name: str) -> None:
        return

    def SetSize(self, _size: tuple[int, int]) -> None:
        return

    def SetSizer(self, _sizer: object) -> None:
        return

    def Bind(self, *_args: object, **_kwargs: object) -> None:
        return

    def CentreOnParent(self) -> None:
        return

    def ShowModal(self) -> int:
        return self._result

    def EndModal(self, result: int) -> None:
        self._result = result
        self.ended_with = result

    def Destroy(self) -> None:
        return


class _BoxSizer:
    def __init__(self, *_args: object) -> None:
        return

    def Add(self, *_args: object, **_kwargs: object) -> None:
        return


class _SearchCtrl:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self._value = ""

    def SetName(self, _name: str) -> None:
        return

    def ShowSearchButton(self, _enabled: bool) -> None:
        return

    def ShowCancelButton(self, _enabled: bool) -> None:
        return

    def SetDescriptiveText(self, _text: str) -> None:
        return

    def SetHint(self, _text: str) -> None:
        return

    def Bind(self, *_args: object, **_kwargs: object) -> None:
        return

    def GetValue(self) -> str:
        return self._value

    def SetValue(self, value: str) -> None:
        self._value = value

    def Clear(self) -> None:
        self._value = ""


class _StaticText:
    def __init__(self, *_args: object, label: str = "", **_kwargs: object) -> None:
        self.label = label

    def SetName(self, _name: str) -> None:
        return

    def SetLabel(self, value: str) -> None:
        self.label = value


class _ListBox:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self._items: list[str] = []
        self._selection = -1
        self.focused = False

    def SetName(self, _name: str) -> None:
        return

    def Bind(self, *_args: object, **_kwargs: object) -> None:
        return

    def Set(self, items: list[str]) -> None:
        self._items = list(items)
        self._selection = -1 if not items else 0

    def SetSelection(self, selection: int) -> None:
        self._selection = selection

    def GetSelection(self) -> int:
        return self._selection

    def GetCount(self) -> int:
        return len(self._items)

    def SetFocus(self) -> None:
        self.focused = True


def _install_fake_wx() -> None:
    fake = SimpleNamespace(
        Dialog=_Dialog,
        BoxSizer=_BoxSizer,
        SearchCtrl=_SearchCtrl,
        StaticText=_StaticText,
        ListBox=_ListBox,
        DEFAULT_DIALOG_STYLE=0,
        RESIZE_BORDER=0,
        TE_PROCESS_ENTER=0,
        VERTICAL=0,
        EXPAND=0,
        ALL=0,
        LEFT=0,
        RIGHT=0,
        BOTTOM=0,
        ID_OK=1,
        ID_CANCEL=0,
        NOT_FOUND=-1,
        WXK_ESCAPE=27,
        WXK_RETURN=13,
        WXK_NUMPAD_ENTER=13,
        WXK_DOWN=40,
        WXK_UP=38,
        EVT_TEXT=object(),
        EVT_TEXT_ENTER=object(),
        EVT_SEARCHCTRL_CANCEL_BTN=object(),
        EVT_LISTBOX_DCLICK=object(),
        EVT_LISTBOX=object(),
        EVT_CHAR_HOOK=object(),
    )
    sys.modules["wx"] = fake


def _build_dialog() -> CommandPaletteDialog:
    _install_fake_wx()
    registry = CommandRegistry()
    registry.register("edit.find", "Find", lambda: None, "Ctrl+F")
    registry.register("edit.replace", "Replace", lambda: None, "Ctrl+H")
    return CommandPaletteDialog(parent=object(), command_registry=registry)


def test_palette_reports_count_and_top_match() -> None:
    dialog = _build_dialog()

    assert "Top match:" in dialog.status.label
    assert dialog.results.GetCount() == 2


def test_palette_arrow_keys_move_from_search_to_results() -> None:
    dialog = _build_dialog()

    # _refresh_results auto-selects the first item on init.
    assert dialog.results.GetSelection() == 0

    down = _Event(dialog._wx.WXK_DOWN)  # noqa: SLF001
    dialog._on_char_hook(down)  # noqa: SLF001
    assert dialog.results.GetSelection() == 1
    assert dialog.results.focused is True
    # _announce_at() sets status.label to command.title (no "Selected:" prefix)
    assert dialog.status.label == "Replace"

    up = _Event(dialog._wx.WXK_UP)  # noqa: SLF001
    dialog._on_char_hook(up)  # noqa: SLF001
    assert dialog.results.GetSelection() == 0
    assert dialog.status.label == "Find"


def test_palette_escape_closes_buttonless_dialog() -> None:
    # The palette has no buttons by design. Per the wxWidgets SetEscapeId
    # contract, native Escape handling maps Escape to the *click* of a Cancel
    # (or affirmative) button; with no such button there is nothing to activate,
    # so Escape is inert and the dialog becomes a keyboard trap (WCAG 2.1.2,
    # the #124 bug class). The palette therefore intercepts Escape and ends the
    # modal itself rather than skipping to native handling.
    dialog = _build_dialog()

    escape = _Event(dialog._wx.WXK_ESCAPE)  # noqa: SLF001
    dialog._on_char_hook(escape)  # noqa: SLF001

    assert escape.skipped is False
    assert dialog.dialog.ended_with == dialog._wx.ID_CANCEL  # noqa: SLF001
