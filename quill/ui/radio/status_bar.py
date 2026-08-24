"""An arrow-navigable status bar for the standalone Quill Radio window.

QUILL's editor has a rich, focusable status bar (``StatusBarMixin``) whose
cells you can arrow across, activate with Enter, and right-click for actions.
That mixin is welded to the text editor (caret position, word counts, document
encoding), so Radio grows its own small, self-contained version here rather
than inheriting a bar full of cells that mean nothing to a radio.

The bar is a row of buttons -- one per cell -- along the bottom of the main
window. Redesigned 2026-08-23 on live feedback: a status bar of *buttons*
should lead with actions, because a button whose label is a bare readout ("a
button that says stopped", "Favorites 1") promises an action it does not
perform. The action cells' labels ARE their actions and flip with the state --
Play/Stop, Mute/Unmute, Record Now/Stop Recording -- and the readouts that
remain (Volume, Sleep timer, Time) each answer Enter with something useful.
Every cell that has more to offer carries a rich right-click menu: the Play
cell offers your favorites and recent stations, the volume pair offers boost
and the output device, Record offers scheduling and the Recordings window.

The now-playing readout came *off* the bar the same day: the main window's own
Now playing field (top of the window) and Ctrl+T already answer it, and here
it was one more button that was not a button.

Focus lands on the bar with F6 -- and only F6: the cells refuse Tab focus, so
tabbing around the main window never detours through six extra stops. Inside,
arrow keys move cell to cell (Home/End jump to the ends), Enter or Space
activates, right-click (or the Applications key) opens the cell's menu, and
Escape returns to the favorites list.

The class takes a *host* -- the ``RadioAppFrame`` -- and reads live state and
calls actions through it (``_radio_controller``, ``_radio_recorder``,
``_sleep_timer_controller``, ``_radio_favorites``, ``radio_*`` actions,
``_announce``). Everything that decides a cell's text or action lives in
``_build_specs`` so the wiring stays in one readable place and a test can drive
the text functions with a fake host.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from quill.core.radio.recording_progress import (
    RecordingProgress,
    recording_cell_help,
    recording_cell_text,
)


@dataclass(frozen=True)
class CellSpec:
    """One status-bar cell: its stable key, spoken name, and behaviour.

    ``text`` returns the live value (``""`` for "nothing to say"), ``activate``
    is what Enter/Space does, ``help`` is the one-line hint, and ``build_menu``
    (if set) populates a right-click context menu with extra actions.
    """

    key: str
    name: str
    text: Callable[[], str]
    activate: Callable[[], None]
    help: str
    build_menu: Callable[[Any], None] | None = None
    #: An *action* cell supplies its live button label here -- "Play"/"Stop",
    #: "Mute"/"Unmute" -- and leaves ``text`` returning "". The label is the
    #: action because the control is a button, and a button whose label is a
    #: readout promises an action it does not perform.
    action_label: Callable[[], str] | None = None
    #: The keyboard shortcut an action cell teaches ("Ctrl+P"), folded into
    #: its accessible name so the bar quietly teaches the key.
    key_hint: str = ""
    #: A cell whose hint depends on live state supplies it here, and ``refresh``
    #: keeps it current. The Recording cell needs this because "12 min left" and
    #: "18 min so far" are two different measurements sharing one cell, and
    #: which one is on screen depends on how the capture was started -- a
    #: distinction the number alone cannot carry. A cell with a fixed hint
    #: leaves this ``None`` and ``help`` stands.
    live_help: Callable[[], str] | None = None


@dataclass
class _Cell:
    spec: CellSpec
    button: Any


def clamp_index(index: int, count: int) -> int:
    """Clamp *index* into ``[0, count - 1]`` (or 0 when the bar is empty)."""
    if count <= 0:
        return 0
    return max(0, min(index, count - 1))


class RadioStatusBar:
    """The focusable, arrow-navigable status bar for the Radio main window."""

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
        #: cell). Gates keyboard focusability: False keeps Tab traversal out
        #: of the bar entirely; True lets SetFocus land while arrowing inside.
        self._inside_bar = False
        self._specs: list[CellSpec] = self._build_specs()

    # -- construction ---------------------------------------------------------

    def build(self, parent: Any) -> Any:
        """Build (or rebuild) the bar as a child panel of *parent* and return it.

        The panel is a thin horizontal strip of buttons. It is created hidden
        when the setting is off; the caller adds it to the window's sizer.

        **Why focusability is dynamic.** The bar must be out of the main
        window's Tab order (F6 is the door in, reported 2026-08-23) -- but a
        control that *statically* refuses keyboard focus on wxMSW also refuses
        ``SetFocus``, which broke F6 entry and cell-to-cell arrowing the same
        day it shipped ("F6 is not letting me arrow across the status bar").
        Measured, not assumed: with the override returning a constant False,
        ``cell.SetFocus()`` left focus where it was. So the cells (and the
        panel) refuse keyboard focus only while focus is *outside* the bar:
        Tab never wanders in, and the moment F6 (or a mouse click) opens a
        visit, everything focuses normally until focus leaves again.
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
        for spec in self._specs:
            button = _CellButton(panel, label=self._button_label(spec), style=wx.BU_EXACTFIT)
            button.SetName(self._button_name(spec))
            button.SetHelpText(self._cell_help(spec))
            button.Bind(wx.EVT_BUTTON, lambda _e, s=spec: self._activate(s))
            button.Bind(wx.EVT_KEY_DOWN, lambda e, s=spec: self._on_key_down(e, s))
            button.Bind(wx.EVT_SET_FOCUS, lambda e, s=spec: self._on_cell_focus(e, s))
            button.Bind(wx.EVT_KILL_FOCUS, self._on_cell_blur)
            if context_event is not None:
                button.Bind(context_event, lambda e, s=spec: self._on_context_menu(e, s))
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

    # -- cell definitions -----------------------------------------------------

    def _build_specs(self) -> list[CellSpec]:
        host = self._host
        return [
            CellSpec(
                key="play_stop",
                name="Play or stop",
                text=lambda: "",
                action_label=self._label_play_stop,
                key_hint="Ctrl+P",
                activate=lambda: _call(host, "radio_play_stop_toggle"),
                help=(
                    "Play the selected station, or stop what is playing. "
                    "Right-click for your favorites, recent stations, "
                    "recording, and Browse Stations."
                ),
                build_menu=self._menu_play,
            ),
            CellSpec(
                key="mute",
                name="Mute or unmute",
                text=lambda: "",
                action_label=self._label_mute,
                key_hint="Ctrl+M",
                activate=lambda: _call(host, "radio_mute_toggle"),
                help=(
                    "Silence the radio without stopping it. Right-click for "
                    "Volume Up, Volume Down, Volume Boost, the output device, "
                    "and Sound Enhancements."
                ),
                build_menu=self._menu_volume,
            ),
            CellSpec(
                key="volume",
                name="Volume",
                text=self._text_volume,
                activate=lambda: _call(host, "radio_mute_toggle"),
                help=(
                    "Volume level. Press Enter to mute or unmute; right-click "
                    "for Volume Up, Volume Down, Volume Boost, the output "
                    "device, and Sound Enhancements."
                ),
                build_menu=self._menu_volume,
            ),
            CellSpec(
                key="recording",
                name="Record",
                text=lambda: "",
                action_label=self._label_record,
                key_hint="Ctrl+R",
                activate=lambda: _call(host, "radio_record_toggle"),
                help=(
                    "Record the playing station, or stop the recording being "
                    "made. Right-click for scheduling, the Recordings window, "
                    "and recording settings."
                ),
                build_menu=self._menu_recording,
                live_help=self._help_recording,
            ),
            CellSpec(
                key="sleep_timer",
                name="Sleep timer",
                text=self._text_sleep_timer,
                activate=lambda: _call(host, "open_sleep_timer_dialog"),
                help=(
                    "Sleep timer. Press Enter to set or cancel it; "
                    "right-click for the wake-up timer too."
                ),
                build_menu=self._menu_sleep_timer,
            ),
            CellSpec(
                key="clock",
                name="Time",
                text=self._text_clock,
                activate=self._announce_clock,
                help="The current time. Press Enter to hear the full date and time.",
            ),
        ]

    # -- action labels --------------------------------------------------------

    def _label_play_stop(self) -> str:
        from quill.ui.radio.playback_state import ACTIVE_STATES

        state = self._controller_state()
        playing = state is not None and getattr(state, "state", None) in ACTIVE_STATES
        return "Stop" if playing else "Play"

    def _label_mute(self) -> str:
        state = self._controller_state()
        return "Unmute" if state is not None and getattr(state, "muted", False) else "Mute"

    def _label_record(self) -> str:
        """The verb pressing it performs, wearing the live progress when on.

        "Record Now" idle; "Stop Recording (42 min left)" while a capture runs
        -- the action first, because this is a button, with the one number
        worth knowing folded in rather than shown as a separate readout.
        """
        progress = self._recording_progress()
        if not progress:
            return "Record Now"
        return f"Stop Recording ({recording_cell_text(progress, datetime.now())})"

    # -- cell text ------------------------------------------------------------

    def _text_volume(self) -> str:
        state = self._controller_state()
        if state is None:
            return ""
        if getattr(state, "muted", False):
            return "Muted"
        percent = int(getattr(state, "volume_percent", 100) or 0)
        boosted = bool(getattr(getattr(self._host, "_radio_history", None), "volume_boost", False))
        return f"{percent}% (boosted)" if boosted else f"{percent}%"

    def _recording_progress(self) -> list[RecordingProgress]:
        """Every running capture, reduced to what the cell needs.

        Defensive by design: this feeds a status cell that repaints on a timer,
        so a recorder mid-teardown (or a fake host in a test) must produce an
        empty list rather than an exception that takes the whole bar down.
        """
        recorder = getattr(self._host, "_radio_recorder", None)
        if recorder is None:
            return []
        try:
            jobs = list(recorder.active_jobs())
        except Exception:  # noqa: BLE001 - a status cell must never raise
            return []
        progress: list[RecordingProgress] = []
        for job in jobs:
            started = getattr(job, "started_at", None)
            if not isinstance(started, datetime):
                continue
            progress.append(
                RecordingProgress(
                    started_at=started,
                    minutes=int(getattr(job, "minutes", 0) or 0),
                    duration_requested=bool(getattr(job, "duration_requested", False)),
                )
            )
        return progress

    def _help_recording(self) -> str:
        return recording_cell_help(self._recording_progress(), datetime.now())

    def _text_sleep_timer(self) -> str:
        timer = getattr(self._host, "_sleep_timer_controller", None)
        if timer is None or not getattr(timer, "is_active", False):
            return "Off"
        seconds = int(getattr(timer, "remaining_seconds", 0) or 0)
        minutes = (seconds + 59) // 60
        return f"{minutes} min left" if minutes != 1 else "1 min left"

    def _text_clock(self) -> str:
        try:
            return datetime.now().strftime("%I:%M %p").lstrip("0")
        except Exception:  # noqa: BLE001 - a status cell must never raise
            return ""

    def _controller_state(self) -> object | None:
        controller = getattr(self._host, "_radio_controller", None)
        return getattr(controller, "state", None) if controller is not None else None

    # -- context menus --------------------------------------------------------

    def _menu_play(self, menu: Any) -> None:
        """The rich transport menu the host already builds: Play/Stop, Mute,
        the favorites and recent-stations submenus, the record group, and
        Browse Stations -- everything "play something" might mean."""
        builder = getattr(self._host, "_build_radio_status_bar_menu", None)
        if builder is not None:
            builder(menu)

    def _menu_volume(self, menu: Any) -> None:
        wx = self._wx
        host = self._host
        up_id, down_id, mute_id, boost_id = (
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
            wx.NewIdRef(),
        )
        menu.Append(up_id, "Volume Up")
        menu.Append(down_id, "Volume Down")
        menu.Append(mute_id, "Mute/Unmute")
        boosted = bool(getattr(getattr(host, "_radio_history", None), "volume_boost", False))
        menu.AppendCheckItem(boost_id, "Volume Boost")
        menu.Check(boost_id, boosted)
        menu.Bind(wx.EVT_MENU, lambda _e: _call(host, "radio_volume_up"), id=up_id)
        menu.Bind(wx.EVT_MENU, lambda _e: _call(host, "radio_volume_down"), id=down_id)
        menu.Bind(wx.EVT_MENU, lambda _e: _call(host, "radio_mute_toggle"), id=mute_id)
        menu.Bind(wx.EVT_MENU, lambda _e: _call(host, "radio_toggle_volume_boost"), id=boost_id)
        menu.AppendSeparator()
        device_id, enhance_id = wx.NewIdRef(), wx.NewIdRef()
        menu.Append(device_id, "Output Device...")
        menu.Append(enhance_id, "Sound Enhancements...")
        menu.Bind(wx.EVT_MENU, lambda _e: self._open_output_device(), id=device_id)
        menu.Bind(wx.EVT_MENU, lambda _e: _call(host, "open_sound_enhancements"), id=enhance_id)

    def _open_output_device(self) -> None:
        from quill.ui.radio.output_device_ui import choose_output_device

        choose_output_device(self._host)

    def _menu_recording(self, menu: Any) -> None:
        wx = self._wx
        host = self._host
        record_id, stop_all_id = wx.NewIdRef(), wx.NewIdRef()
        recorder = getattr(host, "_radio_recorder", None)
        active = int(getattr(recorder, "active_count", 0) or 0)
        menu.Append(record_id, "Stop Recording" if active else "Record Now")
        menu.Bind(wx.EVT_MENU, lambda _e: _call(host, "radio_record_toggle"), id=record_id)
        if active >= 2:
            menu.Append(stop_all_id, "Stop All Recordings")
            menu.Bind(
                wx.EVT_MENU,
                lambda _e: _call(host, "radio_stop_all_recordings"),
                id=stop_all_id,
            )
        menu.AppendSeparator()
        schedule_id, list_id, settings_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
        menu.Append(schedule_id, "Schedule Recording...")
        menu.Append(list_id, "Recordings...")
        menu.Append(settings_id, "Recording Settings...")
        menu.Bind(
            wx.EVT_MENU, lambda _e: _call(host, "_radio_open_schedule_recording"), id=schedule_id
        )
        menu.Bind(wx.EVT_MENU, lambda _e: _call(host, "open_radio_recordings"), id=list_id)
        menu.Bind(
            wx.EVT_MENU, lambda _e: _call(host, "_radio_open_recording_settings"), id=settings_id
        )

    def _menu_sleep_timer(self, menu: Any) -> None:
        wx = self._wx
        host = self._host
        sleep_id, wake_id = wx.NewIdRef(), wx.NewIdRef()
        timer = getattr(host, "_sleep_timer_controller", None)
        active = bool(getattr(timer, "is_active", False))
        menu.Append(sleep_id, "Change Sleep Timer..." if active else "Sleep Timer...")
        menu.Append(wake_id, "Wake-Up Timer...")
        menu.Bind(wx.EVT_MENU, lambda _e: _call(host, "open_sleep_timer_dialog"), id=sleep_id)
        menu.Bind(wx.EVT_MENU, lambda _e: _call(host, "open_wake_timer_dialog"), id=wake_id)

    # -- navigation and activation --------------------------------------------

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
        """Apply *font* to the bar and every cell (View > Text Size scaling)."""
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
        # Open the visit BEFORE asking for focus: wxMSW refuses SetFocus on a
        # window whose AcceptsFocusFromKeyboard answers False (measured).
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
        # Any arrival -- F6, or a mouse click -- opens the visit, so the
        # arrows' SetFocus is accepted for as long as focus stays inside.
        self._inside_bar = True
        self._active_index = self._cell_index(spec)
        entering = self._entering
        self._entering = False
        self._announce_cell(spec, with_region=entering)
        event.Skip()

    def _announce_cell(self, spec: CellSpec, *, with_region: bool) -> None:
        # The same words the button's accessible name carries, so what focus
        # announces and what a screen reader reads off the control agree.
        prefix = "Status bar, " if with_region else ""
        _call(self._host, "_announce", f"{prefix}{self._button_name(spec)}")

    def _on_key_down(self, event: Any, spec: CellSpec) -> None:
        wx = self._wx
        code = event.GetKeyCode()
        index = self._cell_index(spec)
        # All four arrows stay inside the bar. Up and Down matter as much as
        # Left and Right: an unhandled arrow in a TAB_TRAVERSAL panel is a
        # NAVIGATION key on wxMSW, and it walked focus clean out of the bar
        # into the main window's now-playing readout (reported 2026-08-23,
        # "are we leaking with keyboard navigation here?"). They were.
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
        self._inside_bar = False
        target = self._return_focus
        if target is not None:
            try:
                target.SetFocus()
                _call(self._host, "_announce", "Returned to favorite stations")
                return
            except RuntimeError:
                pass
        _call(self._host, "_focus_initial_control")

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
        if spec.build_menu is not None:
            menu.AppendSeparator()
            spec.build_menu(menu)
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
