"""Quill Weather -- the accessible weather watcher as a standalone tray app.

Reuses ``WeatherMixin`` (the same class the main app and Quill Radio use)
unchanged. Its whole reason to exist: run Weather Guardian's US-alert watch
*persistently*, independent of any other app. Close the window and it tucks
into the system tray and keeps polling; turn on "start with Windows" and it
watches from login with no window ever shown. That is the "alerts even when the
main app is closed" piece -- delivered as its own lightweight process rather
than a background service.

See docs/planning/apps.md for why the standalone apps reuse the mixins as-is.
"""

from __future__ import annotations

import os
import sys

import wx

from quill.core import http_client
from quill.core.app_features import AppArea, load_app_features
from quill.ui.app_shell import AppShellFrame
from quill.ui.dialog_contract import set_accessible_name
from quill.ui.main_frame_adp import AdpMixin
from quill.ui.main_frame_weather import WeatherMixin

_TITLE = "Quill Weather"
#: Shared a version line with Quill Radio up to 2.2.0, when the two shipped the
#: same weather feature code and were released together. **That lockstep ended
#: at Radio 3.0.0**, which is a Radio release: nothing in it changes what Quill
#: Weather does, and moving this to 3.0.0 to match would tell Weather's users
#: they had missed a major release that does not exist. The two update
#: independently (each resolves its own release asset), so nothing requires the
#: numbers to agree.
_VERSION = "2.2.0"
#: Every QuillVille app now updates from the one shared repo, each resolving its
#: own release asset (Quill-Weather-*), so they update and maintain independently.
_REPO = "Community-Access/quill"
#: Single-instance slot -- distinct from QUILL (""), Radio, and Cast so the
#: sibling apps sharing one data dir never block each other (#1152).
_IPC_SLOT = "weather"
http_client.set_product_identity(_TITLE, _VERSION)

#: Quill Weather's switchable areas (Options > Customize Features...), turned off
#: by omitting their Weather-menu items on the next launch. Uses the same shared
#: model and dialog as Quill Radio's feature customization.
WEATHER_AREAS: tuple[AppArea, ...] = (
    AppArea(
        "monitoring",
        "Alert Monitoring",
        "Weather Guardian: background monitoring that speaks new alerts, the "
        "severe-weather fast poll, and Pause/Resume.",
    ),
    AppArea(
        "noaa_radio",
        "NOAA Weather Radio",
        "Listen to your local NOAA Weather Radio transmitter and update the "
        "transmitter directory. (Playback needs Quill Radio.)",
    ),
)


class WeatherAppFrame(AppShellFrame, WeatherMixin, AdpMixin):
    """A tray-resident window whose job is to keep the alert watch running."""

    def __init__(self, *, safe_mode: bool = False) -> None:
        self._init_app_shell(_TITLE, safe_mode=safe_mode, size=(460, 300))
        from quill.core.paths import app_data_dir
        from quill.ui.window_menu import WindowManager

        self._app_features = load_app_features(app_data_dir(), "weather")
        self._windows = WindowManager(wx)
        self._build_menu_bar()
        self._build_main_panel()
        self._register_adp_commands()  # palette/keybinding parity for Ask ADP
        self._ensure_tray_icon(self._build_weather_tray_menu, tooltip=_TITLE)
        self._register_tray_hotkey("Ctrl+Alt+Shift+W")  # show/hide Weather to the tray
        self._refresh_statusbar()
        self.frame.Bind(wx.EVT_CLOSE, self._on_weather_app_close)
        # Resume/start the alert watch once the frame and task manager are up
        # (deferred: it touches the network).
        wx.CallAfter(self._weather_app_startup_monitoring)
        # Watch for a second launch asking us to come forward (#1152).
        self._start_ipc_poll()

    # -- menu bar ---------------------------------------------------------------

    def _build_menu_bar(self) -> None:
        from quill.core.weather import settings as settings_mod
        from quill.platform.windows import weather_startup

        settings = settings_mod.load_settings(self._weather_data_dir())
        menu_bar = wx.MenuBar()

        file_menu = wx.Menu()
        tray_id, exit_id = wx.NewIdRef(), wx.NewIdRef()
        file_menu.Append(tray_id, "Minimize to &Tray\tCtrl+W")
        file_menu.Append(exit_id, "E&xit\tCtrl+Q")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._send_to_tray(), id=tray_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._exit_application(), id=exit_id)
        menu_bar.Append(file_menu, "&File")

        # The shared Weather menu (Weather Now, Quick Weather, Active Alerts,
        # Add Location, Settings, NOAA radio, and the Monitoring toggle).
        self._append_weather_menu(menu_bar)

        options_menu = wx.Menu()
        self._startup_item_id = wx.NewIdRef()
        options_menu.AppendCheckItem(
            self._startup_item_id, "Start Quill Weather with &Windows\tCtrl+Alt+W"
        )
        options_menu.Check(self._startup_item_id, weather_startup.is_launch_at_startup_enabled())
        self.frame.Bind(
            wx.EVT_MENU,
            lambda e: self._set_launch_at_startup(e.IsChecked()),
            id=self._startup_item_id,
        )
        self._start_tray_item_id = wx.NewIdRef()
        options_menu.AppendCheckItem(
            self._start_tray_item_id, "Start &minimized to the tray\tCtrl+Alt+M"
        )
        options_menu.Check(self._start_tray_item_id, settings.app_start_in_tray)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda e: self._set_app_pref("app_start_in_tray", e.IsChecked()),
            id=self._start_tray_item_id,
        )
        self._close_tray_item_id = wx.NewIdRef()
        options_menu.AppendCheckItem(
            self._close_tray_item_id, "&Close button keeps monitoring in the tray\tCtrl+Alt+C"
        )
        options_menu.Check(self._close_tray_item_id, settings.app_close_to_tray)
        self.frame.Bind(
            wx.EVT_MENU,
            lambda e: self._set_app_pref("app_close_to_tray", e.IsChecked()),
            id=self._close_tray_item_id,
        )
        options_menu.AppendSeparator()
        self._background_item_id = wx.NewIdRef()
        options_menu.AppendCheckItem(
            self._background_item_id,
            "Check for alerts in the &background (even when Quill Weather is closed)\tCtrl+Alt+B",
        )
        from quill.platform.windows import scheduled_task

        options_menu.Check(self._background_item_id, scheduled_task.is_registered())
        self.frame.Bind(
            wx.EVT_MENU,
            lambda e: self._set_background_check(e.IsChecked()),
            id=self._background_item_id,
        )
        options_menu.AppendSeparator()
        self._features_item_id = wx.NewIdRef()
        options_menu.Append(self._features_item_id, "&Customize Features...\tCtrl+Alt+F")
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._open_app_features(), id=self._features_item_id
        )
        menu_bar.Append(options_menu, "&Options")

        # Pre-release top-level Audio Description Project menu, shared with QUILL,
        # Radio, and Cast. Present by default (future.adp_assistant is on); the
        # hands-free conversational mode (future.adp_voice_mode) stays locked
        # until a signed unlock code is redeemed. Undocumented until launch.
        adp_menu = self._build_adp_menu()
        if adp_menu is not None:
            menu_bar.Append(adp_menu, "&Community")

        from quill.ui.quillville_menu import build_quillville_menu

        menu_bar.Append(
            build_quillville_menu(
                wx,
                self.frame,
                self._launch_sibling,
                exclude="weather",
                retain=self._keep_menu_ids,
            ),
            "&QuillVille",
        )

        help_menu = wx.Menu()
        # The build ships docs\ next to the exe, but until now nothing opened
        # them: Quill Weather's Help menu offered only Check for Updates and
        # About, so its user guide and release notes were installed and
        # unreachable.
        guide_id, notes_id = wx.NewIdRef(), wx.NewIdRef()
        help_menu.Append(guide_id, "&User Guide...\tCtrl+Alt+G")
        help_menu.Append(notes_id, "&Release Notes...\tCtrl+Alt+R")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._open_weather_doc("userguide"), id=guide_id)
        self.frame.Bind(
            wx.EVT_MENU, lambda _e: self._open_weather_doc("release-notes-2.2"), id=notes_id
        )
        help_menu.AppendSeparator()
        updates_id = wx.NewIdRef()
        help_menu.Append(updates_id, "Check for &Updates...\tCtrl+Alt+U")
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.check_for_app_updates(
                repo_slug=_REPO, current_version=_VERSION, app_key="weather"
            ),
            id=updates_id,
        )
        about_id = wx.NewIdRef()
        help_menu.Append(about_id, "&About Quill Weather\tCtrl+Alt+A")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self._show_about(), id=about_id)
        menu_bar.Append(help_menu, "&Help")

        self._windows.install(self.frame, menu_bar)
        self.frame.SetMenuBar(menu_bar)
        self._windows.register(self.frame, _TITLE)
        self._keep_menu_ids(
            tray_id,
            exit_id,
            self._startup_item_id,
            self._start_tray_item_id,
            self._close_tray_item_id,
            self._background_item_id,
            self._features_item_id,
            updates_id,
            about_id,
        )

    # -- main panel -------------------------------------------------------------

    def _build_main_panel(self) -> None:
        panel = wx.Panel(self.frame, style=wx.TAB_TRAVERSAL)
        root = wx.BoxSizer(wx.VERTICAL)
        self._status_text = wx.StaticText(panel, label="Quill Weather")
        set_accessible_name(self._status_text, "Weather monitoring status")
        root.Add(self._status_text, 0, wx.ALL, 12)

        self._open_center_btn = wx.Button(panel, label="Open Weather &Center...")
        self._toggle_monitor_btn = wx.Button(panel, label="Start/Stop &Monitoring")
        self._add_location_btn = wx.Button(panel, label="&Add Location...")
        for btn in (self._open_center_btn, self._toggle_monitor_btn, self._add_location_btn):
            root.Add(btn, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        self._open_center_btn.Bind(wx.EVT_BUTTON, lambda _e: self.open_weather_center())
        self._toggle_monitor_btn.Bind(wx.EVT_BUTTON, lambda _e: self._toggle_and_refresh())
        self._add_location_btn.Bind(wx.EVT_BUTTON, lambda _e: self.open_weather_add_location())

        panel.SetSizer(root)
        self._main_panel = panel

    def _focus_initial_control(self) -> None:
        btn = getattr(self, "_open_center_btn", None)
        if btn is not None:
            try:
                btn.SetFocus()
            except Exception:  # noqa: BLE001 - initial focus is best-effort
                pass

    def _refresh_statusbar(self) -> None:
        active = self._weather_monitoring_active()
        locations = getattr(self, "_weather_monitor_locations", [])
        if len(locations) == 1:
            where = f" for {locations[0].label}"
        elif locations:
            where = f" for {len(locations)} places"
        else:
            where = ""
        text = f"Monitoring {'on' if active else 'off'}{where}."
        self._set_status(text)
        status_ctrl = getattr(self, "_status_text", None)
        if status_ctrl is not None:
            status_ctrl.SetLabel(
                f"Quill Weather -- monitoring is {'on' if active else 'off'}{where}."
            )
        toggle_btn = getattr(self, "_toggle_monitor_btn", None)
        if toggle_btn is not None:
            toggle_btn.SetLabel("Stop &Monitoring" if active else "Start &Monitoring")

    def _toggle_and_refresh(self) -> None:
        self.toggle_weather_monitoring()
        self._refresh_statusbar()

    # -- tray -------------------------------------------------------------------

    def _build_weather_tray_menu(self, menu: object) -> None:
        active = self._weather_monitoring_active()
        status_id, center_id, quick_id, toggle_id = (wx.NewIdRef() for _ in range(4))
        menu.Append(status_id, f"Monitoring: {'on' if active else 'off'}")
        menu.Enable(status_id, False)
        menu.Append(center_id, "Open Weather Center")
        menu.Bind(wx.EVT_MENU, lambda _e: self._open_center_from_tray(), id=center_id)
        menu.Append(quick_id, "Quick Weather")
        menu.Bind(wx.EVT_MENU, lambda _e: self.weather_quick(), id=quick_id)
        if self._app_area_enabled("monitoring"):
            menu.Append(toggle_id, "Stop Monitoring" if active else "Start Monitoring")
            menu.Bind(wx.EVT_MENU, lambda _e: self._toggle_and_refresh(), id=toggle_id)
        self._keep_menu_ids(status_id, center_id, quick_id, toggle_id)
        # Reach the sibling apps from the tray, each in its own window.
        menu.AppendSeparator()
        self._append_sibling_app_tray_items(menu, exclude="weather")

    def _open_center_from_tray(self) -> None:
        self._restore_from_tray()
        self.open_weather_center()

    def _send_to_tray(self) -> None:
        self.frame.Hide()
        self._announce("Quill Weather is monitoring in the system tray.")

    # -- single instance (#1152) ------------------------------------------------

    def _start_ipc_poll(self) -> None:
        timer = wx.Timer(self.frame)
        self.frame.Bind(wx.EVT_TIMER, self._on_ipc_timer, timer)
        timer.Start(800)
        self._ipc_timer = timer

    def _on_ipc_timer(self, _event: object) -> None:
        from quill.core.ipc import drain_open_requests

        if drain_open_requests(slot=_IPC_SLOT):
            self._foreground_window()

    def _foreground_window(self) -> None:
        frame = self.frame
        if not frame.IsShown():
            frame.Show(True)
        if frame.IsIconized():
            frame.Iconize(False)
        frame.Raise()
        frame.RequestUserAttention()

    # -- options ----------------------------------------------------------------

    def _set_launch_at_startup(self, enabled: bool) -> None:
        from quill.platform.windows import weather_startup

        weather_startup.set_launch_at_startup(enabled)
        # Reflect what actually took (a locked-down registry may refuse silently).
        actual = weather_startup.is_launch_at_startup_enabled()
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is not None:
            item = menu_bar.FindItemById(self._startup_item_id)
            if item is not None:
                item.Check(actual)
        self._announce(
            "Quill Weather will start with Windows."
            if actual
            else "Quill Weather will not start with Windows."
        )

    def _set_app_pref(self, field: str, value: bool) -> None:
        from quill.core.weather import settings as settings_mod

        data_dir = self._weather_data_dir()
        settings = settings_mod.load_settings(data_dir)
        setattr(settings, field, value)
        settings_mod.save_settings(data_dir, settings)
        labels = {
            "app_start_in_tray": (
                "Quill Weather will start minimized to the tray.",
                "Quill Weather will start with its window open.",
            ),
            "app_close_to_tray": (
                "Closing the window will keep monitoring in the tray.",
                "Closing the window will exit Quill Weather.",
            ),
        }
        on, off = labels.get(field, ("Setting saved.", "Setting saved."))
        self._announce(on if value else off)

    def _set_background_check(self, enabled: bool) -> None:
        """Register or remove the OS Scheduled Task that checks alerts even when
        Quill Weather is not running. The cadence follows the monitor interval."""
        from quill.core.weather import monitor
        from quill.platform.windows import scheduled_task

        if not scheduled_task.is_windows():
            self._announce("Background alert checks need Windows.")
            self._reflect_background_check_item()
            return
        if enabled:
            interval = monitor.load_config(self._weather_data_dir()).interval_minutes
            scheduled_task.register(interval)
        else:
            scheduled_task.unregister()
        actual = scheduled_task.is_registered()
        self._reflect_background_check_item(actual)
        self._announce(
            "Quill Weather will check for alerts in the background, even when closed."
            if actual
            else "Background alert checks are off."
        )

    def _reflect_background_check_item(self, checked: bool | None = None) -> None:
        from quill.platform.windows import scheduled_task

        state = scheduled_task.is_registered() if checked is None else checked
        menu_bar = self.frame.GetMenuBar()
        if menu_bar is not None:
            item = menu_bar.FindItemById(self._background_item_id)
            if item is not None:
                item.Check(state)

    def _app_area_enabled(self, area_id: str) -> bool:
        features = getattr(self, "_app_features", None)
        return True if features is None else features.is_enabled(area_id)

    def _open_app_features(self) -> None:
        """Options > Customize Features...: turn Quill Weather's areas on or off,
        using the same shared customization as Quill Radio. Menu changes take
        effect at the next launch."""
        from quill.core.app_features import save_app_features
        from quill.core.paths import app_data_dir
        from quill.ui.app_features_dialog import AppFeaturesDialog

        dlg = AppFeaturesDialog(
            self.frame,
            app_title=_TITLE,
            areas=WEATHER_AREAS,
            settings=self._app_features,
            announce_cb=self._announce,
        )
        if dlg.show():
            save_app_features(app_data_dir(), self._app_features)
            self._announce(
                "Feature settings saved. Menu changes take effect the next time "
                "you open Quill Weather."
            )

    def _open_weather_doc(self, stem: str) -> None:
        """Open a bundled doc (docs\\ beside the exe, or a dev checkout)."""
        titles = {
            "userguide": "Quill Weather User Guide",
            "release-notes-2.2": "Quill Weather Release Notes",
        }
        self.open_app_document(
            self._doc_candidates("quill-weather", stem),
            title=titles.get(stem, stem),
            cache_name="app-docs",
        )

    def _show_about(self) -> None:
        self._show_message_box(
            f"{_TITLE} {_VERSION}\n"
            "The accessible weather watcher from Quill.\n\n"
            "Keeps an eye on official National Weather Service alerts for your "
            "location and speaks new warnings as they are issued -- even while "
            "minimized to the system tray.\n\nSupport: support@community-access.org",
            f"About {_TITLE}",
            wx.OK | wx.ICON_INFORMATION,
        )

    # -- monitoring lifecycle ---------------------------------------------------

    def _weather_app_startup_monitoring(self) -> None:
        """Start the alert watch on launch. Resumes when it was left on; on a
        first run (no config yet) it defaults to on for the primary location --
        a dedicated weather watcher should watch. A user who deliberately turned
        it off (config present, disabled) is respected."""
        if self._safe_mode:
            self._announce("Weather monitoring is off in Safe Mode.")
            return
        from quill.core.weather import locations as loc_store
        from quill.core.weather import monitor

        data_dir = self._weather_data_dir()
        store = loc_store.load_locations(data_dir)
        if store.primary() is None:
            self._announce("Add a weather location to begin monitoring.")
            self._refresh_statusbar()
            return
        config = monitor.load_config(data_dir)
        if config.enabled or not monitor.config_exists(data_dir):
            self.start_weather_monitoring(announce=False)
        self._refresh_statusbar()

    def _on_weather_app_close(self, event: object) -> None:
        from quill.core.weather import settings as settings_mod

        # Default: closing the window tucks to the tray and keeps monitoring;
        # an explicit Exit (menu/tray) always quits. Read the pref fresh so an
        # Options change mid-session takes effect immediately.
        close_to_tray = settings_mod.load_settings(self._weather_data_dir()).app_close_to_tray
        self.handle_app_close(
            event,
            close_action="minimize" if close_to_tray else "exit",
            protected=False,
            confirm=lambda: None,
            shutdown=self._weather_app_shutdown,
        )

    def _weather_app_shutdown(self) -> None:
        """Teardown just before the window truly closes: stop the watch without
        persisting it off (so a clean exit resumes next launch), stop the IPC
        timer, and shut the task manager and tray down."""
        self.stop_weather_monitoring(announce=False, persist=False)
        timer = getattr(self, "_ipc_timer", None)
        if timer is not None:
            try:
                timer.Stop()
            except Exception:  # noqa: BLE001 - shutdown must never block exit
                pass
        self._task_manager.shutdown(wait=False)
        self._remove_tray_icon()


def _run_headless_check() -> int:
    """The OS-scheduled ``--check-once`` path: one short-lived alert check with
    no window. Fetches the watched location's NWS alerts, and toasts any that
    are newly issued. Never raises -- a scheduled task must fail quietly."""
    from quill.stability.safe_mode import should_enable_safe_mode

    safe_mode = should_enable_safe_mode(sys.argv[1:], os.environ)
    from quill.core.paths import app_data_dir
    from quill.core.weather import headless_check, nws

    data_dir = app_data_dir()

    def _fetch(latitude: float, longitude: float) -> list:
        return nws.active_alerts(latitude, longitude, safe_mode=safe_mode)

    try:
        result = headless_check.run_check(data_dir, fetch_alerts=_fetch, safe_mode=safe_mode)
    except Exception:  # noqa: BLE001 - offline / transient: try again next tick
        return 0
    if result.new_alerts:
        from quill.core.weather import locations as loc_store
        from quill.core.weather import settings as settings_mod

        settings = settings_mod.load_settings(data_dir)
        if settings.alert_sound_enabled:
            from quill.platform import alert_sound

            alert_sound.play_alert_sound(settings.alert_sound_path, settings.alert_sound_repeat)
        store = loc_store.load_locations(data_dir)
        primary = store.primary()
        label = primary.label if primary is not None else "your area"
        title, body = headless_check.toast_content(result.new_alerts, label)
        _show_alert_toast(title, body)
    return 0


def _show_alert_toast(title: str, body: str) -> None:
    """Show a Windows toast for a new weather alert from the headless check.
    Uses a throwaway wx.App (no window); screen readers announce the toast.
    Degrades to a log line if the notification cannot be shown."""
    try:
        import wx.adv

        from quill.ui.toast import show_toast

        # The App and the pump below are this call site's own concern -- a
        # headless check has no window and no loop -- but the notification
        # itself is the shared one (quill/ui/toast.py).
        app = wx.App(False)
        show_toast(title, body, icon=wx.ICON_WARNING)
        # Give the OS a moment to hand the toast off before the process exits.
        wx.CallLater(1500, app.ExitMainLoop)
        app.MainLoop()
    except Exception:  # noqa: BLE001 - never let a toast failure crash the task
        import logging

        logging.getLogger(__name__).info("Weather alert (toast unavailable): %s -- %s", title, body)


def main() -> int:
    from quill.core.data_location import apply_pending_at_launch

    apply_pending_at_launch()  # queued Data Folder move, before any data read
    if "--check-once" in sys.argv:
        return _run_headless_check()
    safe_mode = bool(os.environ.get("QUILL_SAFE_MODE"))
    start_in_tray = "--tray" in sys.argv
    from quill.core.ipc import (
        enqueue_open_request,
        release_primary_instance,
        try_claim_primary_instance,
    )

    # Single instance (#1152): a second launch just asks the running copy --
    # including one sitting in the tray -- to come forward, then exits.
    if not try_claim_primary_instance(slot=_IPC_SLOT):
        enqueue_open_request(None, slot=_IPC_SLOT)
        return 0

    from quill.core.paths import app_data_dir
    from quill.core.weather import settings as settings_mod
    from quill.stability.logging_config import configure_logging

    log_listener = configure_logging(app_data_dir() / "logs")
    app = wx.App()
    frame = WeatherAppFrame(safe_mode=safe_mode)
    frame._log_listener = log_listener
    if start_in_tray or settings_mod.load_settings(app_data_dir()).app_start_in_tray:
        frame._send_to_tray()  # come up hidden; the watch still runs
    else:
        frame.frame.Show()
        frame.frame.Raise()
        wx.CallAfter(frame._focus_initial_control)
    try:
        app.MainLoop()
    finally:
        release_primary_instance(slot=_IPC_SLOT)
        log_listener.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
