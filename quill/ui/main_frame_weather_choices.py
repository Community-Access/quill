"""WeatherChoicesMixin -- the Alert Choices command, the quick place toggles, and
the live watch's use of the user's choices.

Thin wx glue over ``alert_rules``, ``alert_delivery`` and ``place_watch`` (all
wx-free and tested without a window). The window edits the choices; the watch asks
``plan_poll`` what to do with each poll's result. Mixed into ``WeatherMixin`` so
every host with the Weather menu has these commands.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


class WeatherChoicesMixin:
    frame: Any
    _wx: Any

    def _announce(  # provided by host
        self, message: str, *, force: bool = False, sound: str = ""
    ) -> None: ...
    @staticmethod
    def _weather_data_dir() -> Any: ...
    def weather_test_alert(self) -> None: ...

    # -- the menu rows -------------------------------------------------------------

    def _append_weather_choice_items(self, menu: Any) -> None:
        """Alert Choices..., and a check item for the current place."""
        wx = self._wx
        choices_id, watch_id = wx.NewIdRef(), wx.NewIdRef()
        menu.Append(choices_id, "Alert C&hoices...\tCtrl+Alt+Shift+C")
        self._weather_watch_item = menu.AppendCheckItem(
            watch_id, "Watch This &Place\tCtrl+Alt+Shift+U"
        )
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.open_weather_alert_choices(), id=choices_id)
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.toggle_weather_current_place(), id=watch_id)
        self._weather_watch_item.Check(self._weather_current_place_watched())

    # -- state ---------------------------------------------------------------------

    def _weather_alert_choices(self) -> Any:
        """The saved choices, read fresh so a change made in the window applies to
        the very next poll without restarting the watch."""
        from quill.core.weather import alert_rules_store

        return alert_rules_store.load_choices(self._weather_data_dir())

    def _weather_watch_setup(self) -> tuple[Any, set[str], Any, datetime]:
        """(store, muted ids, place watches, now) as they are on disk right now."""
        from quill.core.weather import locations as loc_store
        from quill.core.weather import monitor, place_watch

        data_dir = self._weather_data_dir()
        return (
            loc_store.load_locations(data_dir),
            set(monitor.load_config(data_dir).muted_ids),
            place_watch.load_watches(data_dir),
            datetime.now().astimezone(),
        )

    def _weather_places_to_watch(self, config: Any, store: Any) -> list[Any]:
        """The saved places the watch should poll now: every one that is not off."""
        from quill.core.weather import place_watch

        watches = place_watch.load_watches(self._weather_data_dir())
        muted, now = set(config.muted_ids), datetime.now().astimezone()
        return [
            loc
            for loc in store.locations
            if place_watch.state_of(loc.id, muted, watches, now).checked
        ]

    def _weather_nothing_to_watch(self, store: Any) -> None:
        if store.locations:
            self._announce(
                "None of your places is being watched. Open Alert Choices to switch one on."
            )
            return
        self._announce("No weather location to monitor yet. Opening Add Location.")
        self.open_weather_add_location()  # type: ignore[attr-defined]

    def _weather_locations_to_poll(self, locations: list[Any]) -> list[Any]:
        """Before each round: say what ended (a snooze, a temporary watch), and drop
        the places that are no longer checked."""
        from quill.core.weather import place_watch

        store, muted, watches, now = self._weather_watch_setup()
        labels = {loc.id: loc.label for loc in store.locations}
        for line in place_watch.due_notices(muted, watches, labels, now):
            self._announce(line)
            place_watch.save_watches(self._weather_data_dir(), watches)
        return [
            loc for loc in locations if place_watch.state_of(loc.id, muted, watches, now).checked
        ]

    def _weather_silenced_reason(self, place_id: str) -> str:
        from quill.core.weather import place_watch

        _store, muted, watches, now = self._weather_watch_setup()
        state = place_watch.state_of(place_id, muted, watches, now)
        if state is place_watch.WatchState.SNOOZED:
            return "a snooze"
        return "its schedule" if state is place_watch.WatchState.OUTSIDE_SCHEDULE else ""

    def _weather_not_watched_note(self) -> str:
        """For the start summary: which places are not watched, and why."""
        from quill.core.weather import place_watch

        store, muted, watches, now = self._weather_watch_setup()
        places = [(loc.id, loc.label) for loc in store.locations]
        lines = place_watch.not_watched_lines(places, muted, watches, now)
        return (" Not watching: " + "; ".join(lines) + ".") if lines else ""

    # -- one poll ---------------------------------------------------------------------

    def _weather_handle_poll(self, location: Any, result: object, state: Any) -> Any:
        """Record one place's result, then decide what to do with it.

        Returns ``(update, plan)`` for a successful check and None for a failed one;
        a failure is recorded as a failure (never an empty answer) and changes
        nothing else: no alert is cleared and no all-clear is spoken."""
        from quill.core.weather import alert_delivery, monitor

        silenced = self._weather_silenced_reason(location.id)
        choices, at = self._weather_alert_choices(), datetime.now().time()
        hidden = (
            alert_delivery.hidden_ids(result, location.id, choices, at, silenced)
            if isinstance(result, list)
            else ()
        )
        if not self._weather_health_record(location, result, hidden):  # type: ignore[attr-defined]
            if not state.primed:
                self._weather_monitor_unchecked[location.id] = location.label  # type: ignore[attr-defined]
            return None
        self._weather_monitor_unchecked.pop(location.id, None)  # type: ignore[attr-defined]
        update = monitor.apply_poll(state, result)  # type: ignore[arg-type]
        plan = alert_delivery.plan_poll(update, result, state, location.id, choices, at, silenced)  # type: ignore[arg-type]
        return update, plan

    def _weather_deliver(self, location: Any, update: Any, plan: Any) -> None:
        """Speak, sound and toast what the plan says; nothing else."""
        from quill.core.sound_events import SoundEvent
        from quill.core.weather import monitor

        if update.is_baseline:
            return
        cue = ""
        if plan.sounds:
            top = plan.sounds[0].alert
            self._play_weather_alert_sound(top.severity)  # type: ignore[attr-defined]
            cue = SoundEvent.WEATHER_ALERT
        if plan.speak:
            top = plan.speak[0].alert
            self._show_weather_toast(  # type: ignore[attr-defined]
                f"Weather alert: {top.event}",
                top.headline or f"A {top.event} is in effect for {location.label}.",
            )
        message = monitor.update_announcement(plan.spoken_update(False), location.label)
        if message and (plan.speak or plan.cleared):
            self._announce(message, force=plan.interrupt, sound=cue)

    # -- commands ----------------------------------------------------------------------

    def open_weather_alert_choices(self) -> None:
        """Weather > Alert Choices: which places to watch, which alerts to hear
        about, how, and when."""
        from quill.ui.weather.alert_choices_dialog import AlertChoicesDialog

        data_dir = self._weather_data_dir()
        store, _muted, _watches, _now = self._weather_watch_setup()
        places = [(loc.id, loc.label) for loc in store.locations]
        if not places:
            self._announce("No weather location yet. Opening Add Location.")
            self.open_weather_add_location()  # type: ignore[attr-defined]
            return
        saved = AlertChoicesDialog(
            self.frame,
            data_dir=data_dir,
            places=places,
            announce_cb=self._announce,
            test_alert_cb=self.weather_test_alert,
        ).show()
        if saved:
            self._weather_choices_saved()

    def _weather_current_place(self) -> Any:
        store, _m, _w, _n = self._weather_watch_setup()
        return store.primary()

    def _weather_current_place_watched(self) -> bool:
        place = self._weather_current_place()
        if place is None:
            return False
        from quill.core.weather import place_watch

        _s, muted, watches, now = self._weather_watch_setup()
        return place_watch.state_of(place.id, muted, watches, now).checked

    def toggle_weather_current_place(self) -> None:
        """Weather > Watch This Place (and the command palette): switch the current
        place on or off without opening a window."""
        from quill.core.weather import monitor

        place = self._weather_current_place()
        if place is None:
            self._announce("No weather location yet. Opening Add Location.")
            self.open_weather_add_location()  # type: ignore[attr-defined]
            return
        data_dir = self._weather_data_dir()
        config = monitor.load_config(data_dir)
        if place.id in config.muted_ids:
            config.muted_ids.remove(place.id)
        else:
            config.muted_ids.append(place.id)
        monitor.save_config(data_dir, config)
        self._weather_choices_saved(announce=True)

    def _weather_choices_saved(self, *, announce: bool = False) -> None:
        """A change to who is watched takes effect now, not at the next launch."""
        from quill.core.weather import place_watch

        store, muted, watches, now = self._weather_watch_setup()
        item = getattr(self, "_weather_watch_item", None)
        place = store.primary()
        if item is not None and place is not None:
            item.Check(place_watch.state_of(place.id, muted, watches, now).checked)
        if announce:
            places = [(loc.id, loc.label) for loc in store.locations]
            self._announce(place_watch.summary_sentence(places, muted, watches, now))
        if getattr(self, "_weather_monitor_timer", None) is None:
            return
        self.stop_weather_monitoring(announce=False, persist=False)  # type: ignore[attr-defined]
        self.start_weather_monitoring(announce=False)  # type: ignore[attr-defined]

    def weather_place_label_states(self) -> list[tuple[str, bool]]:
        """(label, watched) for every saved place -- for a tray submenu."""
        from quill.core.weather import place_watch

        store, muted, watches, now = self._weather_watch_setup()
        return [
            (loc.label, place_watch.state_of(loc.id, muted, watches, now).checked)
            for loc in store.locations
        ]

    def toggle_weather_place_by_index(self, index: int) -> None:
        """A tray submenu row: switch the place at this position on or off."""
        from quill.core.weather import monitor

        store, _m, _w, _n = self._weather_watch_setup()
        if not 0 <= index < len(store.locations):
            return
        pid = store.locations[index].id
        data_dir = self._weather_data_dir()
        config = monitor.load_config(data_dir)
        if pid in config.muted_ids:
            config.muted_ids.remove(pid)
        else:
            config.muted_ids.append(pid)
        monitor.save_config(data_dir, config)
        self._weather_choices_saved(announce=True)

    def _append_weather_tray_places(self, menu: Any) -> None:
        """A tray submenu of the saved places, a check mark on each watched one."""
        wx = self._wx
        rows = self.weather_place_label_states()
        if not rows:
            return
        sub = wx.Menu()
        ids = []
        for i, (label, watched) in enumerate(rows):
            item_id = wx.NewIdRef()
            ids.append(item_id)
            sub.AppendCheckItem(item_id, label).Check(watched)
            menu.Bind(
                wx.EVT_MENU, lambda _e, i=i: self.toggle_weather_place_by_index(i), id=item_id
            )
        menu.AppendSubMenu(sub, "Watched Places")
        keep = getattr(self, "_keep_menu_ids", None)
        if keep is not None:
            keep(*ids)
