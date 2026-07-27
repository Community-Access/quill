"""An arrow-navigable status bar for the standalone QUILL Audio Studio window.

QUILL's editor has a rich, focusable status bar whose cells you can arrow
across, activate with Enter, and right-click for actions. Quill Radio grows its
own small, self-contained version of that idea (``quill.ui.radio.status_bar``);
the Audio Studio needs the same thing -- a place a screen-reader user can review
"what is going on" without hunting the window, and above all a **Progress** cell
that reads the live state of a long narration or build run (including while the
window is tucked away in the system tray). This is that bar, kept self-contained
here so ``apps/studio.py`` stays small.

The bar is a row of buttons -- one per cell -- along the bottom of the main
window. Focus lands on it with F6, moves cell to cell with the arrow keys
(Home/End jump to the ends), activates with Enter or Space, offers a right-click
context menu, and Escape (or a second F6) returns to the library.

The class takes a *host* -- the ``StudioAppFrame`` -- and reads live state and
calls actions through it (``studio_activity_text``, ``studio_progress_text``,
``studio_progress_details``, ``studio_sleep_timer_text``, ``studio_library_text``,
``_on_sleep_timer``, ``_focus_library``, ``_announce``). Everything that decides
a cell's text or action lives in ``_build_specs`` so the wiring stays in one
readable place and a test can drive the text functions with a fake host.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class CellSpec:
    """One status-bar cell: its stable key, spoken name, and behaviour.

    ``text`` returns the live value (``""`` for "nothing to say"), ``activate``
    is what Enter/Space does, and ``help`` is the one-line hint.
    """

    key: str
    name: str
    text: Callable[[], str]
    activate: Callable[[], None]
    help: str


@dataclass
class _Cell:
    spec: CellSpec
    button: Any


def clamp_index(index: int, count: int) -> int:
    """Clamp *index* into ``[0, count - 1]`` (or 0 when the bar is empty)."""
    if count <= 0:
        return 0
    return max(0, min(index, count - 1))


class StudioStatusBar:
    """The focusable, arrow-navigable status bar for the Studio main window."""

    def __init__(self, host: object) -> None:
        self._host = host
        self._wx: Any = getattr(host, "_wx", None)
        self._panel: Any = None
        self._sizer: Any = None
        self._cells: list[_Cell] = []
        self._active_index = 0
        #: Where focus was before F6 jumped into the bar, so Escape (or a second
        #: F6) can hand it straight back rather than guessing.
        self._return_focus: Any = None
        self._entering = False
        self._specs: list[CellSpec] = self._build_specs()

    # -- construction ---------------------------------------------------------

    def build(self, parent: Any) -> Any:
        """Build (or rebuild) the bar as a child panel of *parent* and return it.

        The panel is a thin horizontal strip of buttons. It is created hidden
        when the setting is off; the caller adds it to the window's sizer.
        """
        wx = self._wx
        panel = wx.Panel(parent, style=wx.TAB_TRAVERSAL)
        panel.SetName("Status bar")
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._panel = panel
        self._sizer = sizer
        self._cells = []
        context_event = getattr(wx, "EVT_CONTEXT_MENU", None)
        for spec in self._specs:
            button = wx.Button(panel, label=self._button_label(spec), style=wx.BU_EXACTFIT)
            button.SetName(self._button_name(spec))
            button.SetHelpText(spec.help)
            button.Bind(wx.EVT_BUTTON, lambda _e, s=spec: self._activate(s))
            button.Bind(wx.EVT_KEY_DOWN, lambda e, s=spec: self._on_key_down(e, s))
            button.Bind(wx.EVT_SET_FOCUS, lambda e, s=spec: self._on_cell_focus(e, s))
            if context_event is not None:
                button.Bind(context_event, lambda e, s=spec: self._on_context_menu(e, s))
            sizer.Add(button, 0, wx.EXPAND | wx.ALL, 2)
            self._cells.append(_Cell(spec=spec, button=button))
        panel.SetSizer(sizer)
        return panel

    # -- cell definitions -----------------------------------------------------

    def _build_specs(self) -> list[CellSpec]:
        host = self._host
        return [
            CellSpec(
                key="activity",
                name="Activity",
                text=lambda: _call_value(host, "studio_activity_text", "Ready"),
                activate=lambda: _call(
                    host, "_announce", _call_value(host, "studio_activity_text", "Ready")
                ),
                help="What the Studio is doing right now. Press Enter to hear it again.",
            ),
            CellSpec(
                key="progress",
                name="Progress",
                text=lambda: _call_value(host, "studio_progress_text", "Idle"),
                activate=lambda: _call(
                    host,
                    "_announce",
                    _call_value(host, "studio_progress_details", "No task is running."),
                ),
                help=(
                    "Progress of a running narration or build. Press Enter for the "
                    "full detail -- percent, how many files, and the current step."
                ),
            ),
            CellSpec(
                key="sleep_timer",
                name="Sleep timer",
                text=lambda: _call_value(host, "studio_sleep_timer_text", "Off"),
                activate=lambda: _call(host, "_on_sleep_timer"),
                help="Sleep timer. Press Enter to set or cancel it.",
            ),
            CellSpec(
                key="library",
                name="Your books",
                text=lambda: _call_value(host, "studio_library_text", ""),
                activate=lambda: _call(host, "_focus_library"),
                help="How many books are in your library. Press Enter to jump to the list.",
            ),
            CellSpec(
                key="clock",
                name="Time",
                text=self._text_clock,
                activate=self._announce_clock,
                help="The current time. Press Enter to hear the full date and time.",
            ),
        ]

    # -- cell text ------------------------------------------------------------

    def _text_clock(self) -> str:
        try:
            return datetime.now().strftime("%I:%M %p").lstrip("0")
        except Exception:  # noqa: BLE001 - a status cell must never raise
            return ""

    # -- navigation and activation --------------------------------------------

    def _button_label(self, spec: CellSpec) -> str:
        value = spec.text()
        return f"{spec.name}: {value}" if value else spec.name

    def _button_name(self, spec: CellSpec) -> str:
        value = spec.text()
        return f"{spec.name}, {value}" if value else spec.name

    def refresh(self) -> None:
        """Repaint every cell's label from live state (dead-widget safe)."""
        for cell in self._cells:
            try:
                cell.button.SetLabel(self._button_label(cell.spec))
                cell.button.SetName(self._button_name(cell.spec))
            except RuntimeError:
                continue
        panel = self._panel
        if panel is not None:
            try:
                panel.Layout()
            except RuntimeError:
                pass

    def is_shown(self) -> bool:
        panel = self._panel
        return bool(panel is not None and panel.IsShown())

    def set_visible(self, shown: bool) -> None:
        panel = self._panel
        if panel is None:
            return
        panel.Show(shown)
        parent = panel.GetParent()
        if parent is not None:
            parent.Layout()

    def set_font(self, font: Any) -> None:
        """Apply *font* to the bar and every cell (text-scaling parity)."""
        panel = self._panel
        if panel is not None:
            try:
                panel.SetFont(font)
            except RuntimeError:
                pass
        for cell in self._cells:
            try:
                cell.button.SetFont(font)
            except RuntimeError:
                continue
        if panel is not None:
            try:
                panel.Layout()
            except RuntimeError:
                pass

    def has_focus(self) -> bool:
        """True when keyboard focus is on one of this bar's cells."""
        wx = self._wx
        if wx is None or not self._cells:
            return False
        focused = wx.Window.FindFocus()
        return any(cell.button is focused for cell in self._cells)

    def focus_bar(self, return_focus: object | None = None) -> None:
        """Move focus into the bar, remembering where to hand it back."""
        if not self._cells or not self.is_shown():
            return
        self._return_focus = return_focus
        self._entering = True
        self._focus_cell(self._active_index)

    def _focus_cell(self, index: int) -> None:
        if not self._cells:
            return
        self._active_index = clamp_index(index, len(self._cells))
        self._cells[self._active_index].button.SetFocus()

    def _cell_index(self, spec: CellSpec) -> int:
        for index, cell in enumerate(self._cells):
            if cell.spec.key == spec.key:
                return index
        return 0

    def _on_cell_focus(self, event: Any, spec: CellSpec) -> None:
        self._active_index = self._cell_index(spec)
        entering = self._entering
        self._entering = False
        self._announce_cell(spec, with_region=entering)
        event.Skip()

    def _announce_cell(self, spec: CellSpec, *, with_region: bool) -> None:
        value = spec.text()
        prefix = "Status bar, " if with_region else ""
        message = f"{prefix}{spec.name}, {value}" if value else f"{prefix}{spec.name}"
        _call(self._host, "_announce", message)

    def _on_key_down(self, event: Any, spec: CellSpec) -> None:
        wx = self._wx
        code = event.GetKeyCode()
        index = self._cell_index(spec)
        if code == wx.WXK_LEFT:
            self._focus_cell(index - 1)
            return
        if code == wx.WXK_RIGHT:
            self._focus_cell(index + 1)
            return
        if code == wx.WXK_HOME:
            self._focus_cell(0)
            return
        if code == wx.WXK_END:
            self._focus_cell(len(self._cells) - 1)
            return
        if code == wx.WXK_TAB:
            # The whole status bar is one stop in the window's Tab order, not one
            # stop per cell -- Tab / Shift+Tab hand off to the next / previous
            # control (the arrow keys above are what move cell to cell).
            forward = not event.ShiftDown()
            flag = wx.NavigationKeyEvent.IsForward if forward else wx.NavigationKeyEvent.IsBackward
            self._panel.Navigate(flag)
            return
        if code == wx.WXK_ESCAPE:
            self._leave_bar()
            return
        if code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_SPACE):
            self._activate(spec)
            return
        event.Skip()

    def _leave_bar(self) -> None:
        target = self._return_focus
        if target is not None:
            try:
                target.SetFocus()
                _call(self._host, "_announce", "Returned to your books")
                return
            except RuntimeError:
                pass
        _call(self._host, "_focus_library")

    def _activate(self, spec: CellSpec) -> None:
        try:
            spec.activate()
        except Exception:  # noqa: BLE001 - a bad cell action must not crash the bar
            _call(self._host, "_announce", f"Could not open {spec.name}")

    def _announce_clock(self) -> None:
        try:
            stamp = datetime.now().strftime("%A, %B %d, %I:%M %p")
        except Exception:  # noqa: BLE001
            return
        _call(self._host, "_announce", stamp)

    def _on_context_menu(self, event: Any, spec: CellSpec) -> None:
        wx = self._wx
        menu = wx.Menu()
        activate_id = wx.NewIdRef()
        menu.Append(activate_id, "Activate")
        menu.Bind(wx.EVT_MENU, lambda _e: self._activate(spec), id=activate_id)
        menu.AppendSeparator()
        hide_id = wx.NewIdRef()
        menu.Append(hide_id, "Hide Status Bar")
        menu.Bind(wx.EVT_MENU, lambda _e: _call(self._host, "_toggle_show_status_bar"), id=hide_id)
        target = None
        for cell in self._cells:
            if cell.spec.key == spec.key:
                target = cell.button
                break
        (target or self._panel).PopupMenu(menu)
        menu.Destroy()


def _call(host: object, name: str, *args: object) -> None:
    method = getattr(host, name, None)
    if callable(method):
        method(*args)


def _call_value(host: object, name: str, default: str) -> str:
    method = getattr(host, name, None)
    if callable(method):
        try:
            value = method()
        except Exception:  # noqa: BLE001
            return default
        return value if isinstance(value, str) else default
    return default
