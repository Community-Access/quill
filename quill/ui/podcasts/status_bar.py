"""An arrow-navigable status bar for the QUILL Cast main window.

The last app in the family to get one: QUILL, QUILL Lite, Quill Radio and
Audio Studio all have a status bar a listener can walk with the arrow keys,
and Cast -- the app somebody leaves running all evening -- had none. Jeff,
2026-09-30, after using it: "Status bar like in quill/quill lite/radio... We
need that also."

Modelled on :mod:`quill.ui.radio.status_bar`, deliberately and closely. The
editor's own ``StatusBarMixin`` is welded to a text buffer (caret position,
word counts, encoding) and means nothing here, so each listening app grows its
own small, self-contained bar -- but the *shape* is shared, because the whole
value of a family key is that it behaves the same everywhere. F6 gets in,
arrows move cell to cell, Home and End jump to the ends, Enter or Space
activates, Shift+F10 or a right-click opens the cell's own menu, Escape hands
focus back, and Tab leaves the bar rather than walking through nine cells.

This module is the *widget*: a panel of buttons, focus, keys and popup menus,
and it knows nothing about podcasts. What each cell says and does lives in
:mod:`quill.ui.podcasts.status_bar_cells`, which knows nothing about wx. The
split is what keeps both halves inside GATE-11's cap, and it is also the seam
a test wants: every readout is a function of a host and needs no window.

**No access keys on any cell** (GATE-14). Cast's menu bar already claims most
of the alphabet, and a duplicate ``&`` mnemonic is worse than none: Windows
cycles focus between the duplicates instead of pressing, so one of the pair
silently cannot be reached and nothing announces the loss. The cells are
reached by F6 and the arrows, a route that cannot collide with anything.

**What the bar says out loud** (GATE-13). Entering it announces the region --
"Status bar" -- and nothing else, ever. Moving between cells is silent,
because a focus move, a control's name, its role and its state are exactly
what every screen reader narrates by itself, and saying them again is the
over-announcing nobody files a bug about and everybody pays for on every
press. Leaving the bar is silent for the same reason: the library tree
announces itself and the row focus lands on. The cells carry their full
accessible names, so the reader has the words -- this bar simply does not
repeat them. Where Radio's bar speaks each cell's name on arrival, this one
does not, and that is the one place the two deliberately differ.

The class takes a *host* -- the ``PodcastsAppFrame`` -- and reads live state
and calls actions through it (``_podcast_controller``, ``_podcast_library``,
``_podcast_download_queue``, ``_sleep_timer_controller``, the ``podcast_*``
commands, ``_announce``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from quill.ui.podcasts.status_bar_cells import CellSpec, build_specs, call_host


@dataclass
class _Cell:
    spec: CellSpec
    button: Any


def clamp_index(index: int, count: int) -> int:
    """Clamp *index* into ``[0, count - 1]`` (or 0 when the bar is empty)."""
    if count <= 0:
        return 0
    return max(0, min(index, count - 1))


class CastStatusBar:
    """The focusable, arrow-navigable status bar for the Cast main window."""

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
        #: True while somebody is visiting the bar (F6, or a mouse click on a
        #: cell). Gates keyboard focusability: False keeps Tab traversal out of
        #: the bar entirely; True lets SetFocus land while arrowing inside.
        self._inside_bar = False
        self._specs: list[CellSpec] = self._build_specs()

    def _build_specs(self) -> list[CellSpec]:
        """The nine cells. A method rather than an inline call so a subclass or
        a test can narrow the bar without rebuilding the navigation."""
        return build_specs(self._host, self._wx)

    # -- construction ---------------------------------------------------------

    def build(self, parent: Any) -> Any:
        """Build (or rebuild) the bar as a child panel of *parent* and return it.

        The panel is a thin horizontal strip of buttons; the caller adds it to
        the window's sizer and hides it when the setting is off.

        **Why focusability is dynamic.** The bar must be out of the main
        window's Tab order -- nine extra stops on the way to the buttons is a
        cost paid on every pass -- but a control that *statically* refuses
        keyboard focus on wxMSW also refuses ``SetFocus``, which is what broke
        Radio's F6 entry and its cell-to-cell arrowing the day that bar
        shipped. Measured there, not assumed: with the override returning a
        constant False, ``cell.SetFocus()`` left focus where it was. So the
        cells (and the panel) refuse keyboard focus only while focus is
        *outside* the bar.
        """
        wx = self._wx
        bar = self

        class _CellButton(wx.Button):
            """A cell you visit (F6, click), never a Tab stop on the way by."""

            def AcceptsFocusFromKeyboard(self) -> bool:  # noqa: N802 - wx override
                return bar._inside_bar

        class _BarPanel(wx.Panel):
            """Skipped whole by Tab while nobody is visiting the bar."""

            def AcceptsFocusFromKeyboard(self) -> bool:  # noqa: N802 - wx override
                return bar._inside_bar

        panel = _BarPanel(parent, style=wx.TAB_TRAVERSAL)
        panel.SetName("Status bar")
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._panel = panel
        self._sizer = sizer
        self._cells = []
        context_event = getattr(wx, "EVT_CONTEXT_MENU", None)
        right_event = getattr(wx, "EVT_RIGHT_UP", None)
        for spec in self._specs:
            button = _CellButton(panel, label=self._button_label(spec), style=wx.BU_EXACTFIT)
            button.SetName(self._button_name(spec))
            button.SetHelpText(self._cell_help(spec))
            button.Bind(wx.EVT_BUTTON, lambda _e, s=spec: self._activate(s))
            button.Bind(wx.EVT_KEY_DOWN, lambda e, s=spec: self._on_key_down(e, s))
            button.Bind(wx.EVT_SET_FOCUS, lambda e, s=spec: self._on_cell_focus(e, s))
            button.Bind(wx.EVT_KILL_FOCUS, self._on_cell_blur)
            # Both events, because neither alone is the whole menu key. The
            # Applications key and Shift+F10 arrive as EVT_CONTEXT_MENU; a
            # wxMSW push button eats the right-click itself and does not always
            # synthesise one, so the mouse needs EVT_RIGHT_UP. Binding one of
            # the pair is how a cell menu ends up reachable by exactly half the
            # people who go looking for it.
            if context_event is not None:
                button.Bind(context_event, lambda e, s=spec: self._on_context_menu(e, s))
            if right_event is not None:
                button.Bind(right_event, lambda e, s=spec: self._on_context_menu(e, s))
            sizer.Add(button, 0, wx.EXPAND | wx.ALL, 2)
            self._cells.append(_Cell(spec=spec, button=button))
        panel.SetSizer(sizer)
        return panel

    def _on_cell_blur(self, event: Any) -> None:
        """Focus left a cell: if it left the bar entirely, close the visit so
        Tab traversal skips the bar again."""
        gaining = None
        get_window = getattr(event, "GetWindow", None)
        if callable(get_window):
            gaining = get_window()
        if gaining is None or not self._is_bar_window(gaining):
            self._inside_bar = False
        event.Skip()

    def _is_bar_window(self, window: Any) -> bool:
        return window is self._panel or any(cell.button is window for cell in self._cells)

    # -- labels, names and hints ----------------------------------------------

    def _button_label(self, spec: CellSpec) -> str:
        if spec.action_label is not None:
            return spec.action_label()
        value = spec.text()
        return f"{spec.name}: {value}" if value else spec.name

    def _button_name(self, spec: CellSpec) -> str:
        if spec.action_label is not None:
            label = spec.action_label()
            return f"{label} ({spec.key_hint})" if spec.key_hint else label
        value = spec.text()
        return f"{spec.name}, {value}" if value else spec.name

    def _cell_help(self, spec: CellSpec) -> str:
        """A cell's current hint: its live one where it has one, else the fixed
        text. A ``live_help`` that raises falls back rather than losing the hint
        entirely -- a cell with no help is worse than a cell with general help.
        """
        if spec.live_help is None:
            return spec.help
        try:
            return spec.live_help() or spec.help
        except Exception:  # noqa: BLE001 - a status cell must never raise
            return spec.help

    # -- visibility, font and refresh -----------------------------------------

    def refresh(self) -> None:
        """Repaint every cell's label from live state (dead-widget safe)."""
        for cell in self._cells:
            try:
                cell.button.SetLabel(self._button_label(cell.spec))
                cell.button.SetName(self._button_name(cell.spec))
                if cell.spec.live_help is not None:
                    cell.button.SetHelpText(self._cell_help(cell.spec))
            except RuntimeError:
                continue
        self._layout()

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
        """Apply *font* to the bar and every cell (text-size scaling)."""
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
        self._layout()

    def _layout(self) -> None:
        """Re-lay the strip, tolerating a panel already on its way out: both
        callers run from timers, and a dead widget must not raise past them."""
        panel = self._panel
        if panel is None:
            return
        try:
            panel.Layout()
        except RuntimeError:
            pass

    # -- navigation and activation --------------------------------------------

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
        # Open the visit BEFORE asking for focus: wxMSW refuses SetFocus on a
        # window whose AcceptsFocusFromKeyboard answers False (measured in
        # Radio, and the reason that bar's F6 did nothing for a day).
        self._inside_bar = True
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
        # Any arrival -- F6, or a mouse click -- opens the visit, so the arrows'
        # SetFocus is accepted for as long as focus stays inside.
        self._inside_bar = True
        self._active_index = self._cell_index(spec)
        entering = self._entering
        self._entering = False
        if entering:
            # The region, and only on the way in. Where focus has landed
            # *within* the bar is the cell's own name, role and state, which is
            # precisely what the screen reader says by itself (GATE-13);
            # repeating it on every arrow press is the chattiness nobody
            # reports and everybody hears. "Status bar" is the one fact a jump
            # from the other side of the window leaves unanswered.
            call_host(self._host, "_announce", "Status bar")
        event.Skip()

    def _on_key_down(self, event: Any, spec: CellSpec) -> None:
        wx = self._wx
        code = event.GetKeyCode()
        index = self._cell_index(spec)
        # All four arrows stay inside the bar. Up and Down matter as much as
        # Left and Right: an unhandled arrow in a TAB_TRAVERSAL panel is a
        # NAVIGATION key on wxMSW, and in Radio it walked focus clean out of the
        # bar into the window behind it until those two were consumed too.
        if code in (wx.WXK_LEFT, wx.WXK_UP):
            self._focus_cell(index - 1)
            return
        if code in (wx.WXK_RIGHT, wx.WXK_DOWN):
            self._focus_cell(index + 1)
            return
        if code == wx.WXK_HOME:
            self._focus_cell(0)
            return
        if code == wx.WXK_END:
            self._focus_cell(len(self._cells) - 1)
            return
        if code == wx.WXK_TAB:
            # Tab leaves the bar (arrows move cell to cell): close the visit
            # first so traversal does not consider the bar's own cells, then
            # navigate from the panel to its sibling.
            self._inside_bar = False
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
        """Escape: hand focus back where it came from, and say nothing.

        The library tree announces itself and the row focus lands on, so a
        sentence here would be the third time the listener is told where they
        are. The tree is the fallback target because it is where Cast puts
        focus at launch -- landing somewhere arbitrary would be worse than
        landing somewhere familiar.
        """
        self._inside_bar = False
        target = self._return_focus or getattr(self._host, "_shows_tree", None)
        if target is not None:
            try:
                target.SetFocus()
                return
            except RuntimeError:
                pass
        call_host(self._host, "_focus_initial_control")

    def _activate(self, spec: CellSpec) -> None:
        try:
            spec.activate()
        except Exception:  # noqa: BLE001 - a bad cell action must not crash the bar
            call_host(self._host, "_announce", f"Could not open {spec.name}")

    def _on_context_menu(self, event: Any, spec: CellSpec) -> None:
        """The cell's own menu: Activate, whatever that cell offers, and the
        switch that takes the whole bar away again.

        Activate leads because the cell is a button and the menu must not hide
        what pressing it would do -- the readout cells in particular, where
        "open the Inbox" is not guessable from a number.
        """
        wx = self._wx
        menu = wx.Menu()
        activate_id = wx.NewIdRef()
        menu.Append(activate_id, "Activate")
        menu.Bind(wx.EVT_MENU, lambda _e: self._activate(spec), id=activate_id)
        if spec.build_menu is not None:
            menu.AppendSeparator()
            spec.build_menu(menu)
        menu.AppendSeparator()
        hide_id = wx.NewIdRef()
        menu.Append(hide_id, "Hide Status Bar")
        menu.Bind(
            wx.EVT_MENU,
            lambda _e: call_host(self._host, "_toggle_cast_status_bar"),
            id=hide_id,
        )
        target = None
        for cell in self._cells:
            if cell.spec.key == spec.key:
                target = cell.button
                break
        (target or self._panel).PopupMenu(menu)
        menu.Destroy()
