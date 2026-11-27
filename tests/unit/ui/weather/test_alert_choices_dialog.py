"""Build and drive the Alert Choices and Alert Feed Status windows without ever
showing a modal: the controls exist, are named, collect what was chosen, and the
Preview asks the same ``decide`` the live watch uses."""

from __future__ import annotations

from pathlib import Path

import pytest
import wx

from quill.core.weather import alert_rules_store as store
from quill.core.weather import monitor
from quill.ui.weather.alert_choices_dialog import AlertChoicesDialog
from quill.ui.weather.feed_status_dialog import FeedStatusDialog
from tests.wx_session import shared_wx_app

PLACES = [("home", "Home"), ("work", "Work"), ("cabin", "Cabin")]


@pytest.fixture
def app():
    a = shared_wx_app()
    yield a
    a.Destroy()


def _make(tmp_path: Path, said: list[str] | None = None) -> AlertChoicesDialog:
    said = said if said is not None else []
    return AlertChoicesDialog(None, data_dir=tmp_path, places=PLACES, announce_cb=said.append)


def test_defaults_collect_to_the_default_choices(app, tmp_path: Path) -> None:
    dlg = _make(tmp_path)
    try:
        assert dlg.collect().is_default()
        assert dlg._place_list.GetStrings() == [
            "Home, watched",
            "Work, watched",
            "Cabin, watched",
        ]
    finally:
        dlg.dialog.Destroy()


def test_choices_chosen_in_the_window_are_collected_and_saved(app, tmp_path: Path) -> None:
    said: list[str] = []
    dlg = _make(tmp_path, said)
    try:
        dlg._preset.SetSelection(1)  # Essentials
        dlg._sync_preset()
        dlg._place_list.SetSelection(1)
        dlg._place_selected()
        dlg._toggle_place()  # switch Work off
        dlg._quiet_on.SetValue(True)
        dlg._quiet_start.SetValue("21:00")
        dlg._save()
    finally:
        dlg.dialog.Destroy()
    saved = store.load_choices(tmp_path)
    assert saved.general.selection.preset == "essentials"
    assert saved.quiet.enabled and saved.quiet.start == "21:00"
    assert monitor.load_config(tmp_path).muted_ids == ["work"]
    assert said[-1].startswith(
        "Watching 2 of 3 places. Work is not watched, switched off. "
        "Telling you about tornado, severe thunderstorm"
    )


def test_bad_quiet_time_is_refused_and_nothing_is_saved(app, tmp_path: Path) -> None:
    said: list[str] = []
    dlg = _make(tmp_path, said)
    try:
        dlg._quiet_start.SetValue("late")
        dlg._save()
    finally:
        dlg.dialog.Destroy()
    assert "like 22:00" in said[-1]
    assert not store.store_path(tmp_path).exists()


def test_custom_lists_and_severity_shortcut(app, tmp_path: Path) -> None:
    dlg = _make(tmp_path)
    try:
        dlg._preset.SetSelection(3)  # Custom
        dlg._cat_add.SetStringSelection("Winter weather")
        dlg._add_category()
        dlg._evt_cat.SetStringSelection("Tornado")
        dlg._fill_events()
        dlg._evt.SetSelection(0)
        dlg._include_event()
        dlg._shortcut.SetSelection(2)  # Severe and above
        dlg._apply_shortcut()
        clause = dlg.collect().general.selection.custom
        assert clause.categories == ["Winter weather"]
        assert clause.events == ["Tornado Warning"]
        assert clause.severities == ["Extreme", "Severe"]
    finally:
        dlg.dialog.Destroy()


def test_preview_says_what_would_happen(app, tmp_path: Path) -> None:
    said: list[str] = []
    dlg = _make(tmp_path, said)
    try:
        dlg._preset.SetSelection(1)  # Essentials
        dlg._sample.SetSelection(4)  # Heat Advisory (Moderate)
        dlg._preview()
        assert "would not be spoken" in dlg._preview_text.GetValue()
        dlg._sample.SetSelection(0)  # Tornado Warning (Extreme)
        dlg._preview()
        assert "interrupting" in dlg._preview_text.GetValue()
        assert said[-1] == dlg._preview_text.GetValue()
    finally:
        dlg.dialog.Destroy()


def test_every_interactive_control_has_an_accessible_name(app, tmp_path: Path) -> None:
    dlg = _make(tmp_path)
    try:
        unnamed: list[str] = []

        def walk(window: wx.Window) -> None:
            for child in window.GetChildren():
                if isinstance(
                    child,
                    wx.Choice | wx.ListBox | wx.ListCtrl | wx.TextCtrl | wx.CheckBox | wx.Button,
                ):
                    named = bool(child.GetName() and child.GetName() not in ("button", "text"))
                    named = named or bool(
                        child.GetLabel() if isinstance(child, wx.Button | wx.CheckBox) else False
                    )
                    if not named:
                        unnamed.append(type(child).__name__)
                walk(child)

        walk(dlg.dialog)
        assert unnamed == []
    finally:
        dlg.dialog.Destroy()


def test_feed_status_dialog_holds_the_text_read_only(app) -> None:
    said: list[str] = []
    dlg = FeedStatusDialog(
        None, text="Alert feed status\nOverall: Working.", announce_cb=said.append
    )
    try:
        assert "Working" in dlg._box.GetValue()
        assert not dlg._box.IsEditable()
    finally:
        dlg.dialog.Destroy()


def test_places_page_bulk_snooze_schedule_groups_and_until(app, tmp_path: Path) -> None:
    said: list[str] = []
    dlg = _make(tmp_path, said)
    try:
        dlg._watch_none()
        assert dlg._place_list.GetStrings()[2] == "Cabin, not watched, switched off"
        assert said[-1].startswith("Watching 0 of 3 places.")
        dlg._invert()
        assert dlg._muted == set()
        dlg._place_list.SetSelection(2)
        dlg._place_selected()
        dlg._snooze.SetStringSelection("4 hours")
        dlg._apply_snooze()
        assert "Cabin, snoozed until" in dlg._place_list.GetStrings()[2]
        dlg._schedule.SetValue("Mon-Fri 08:00-18:00")
        dlg._apply_schedule()
        dlg._schedule.SetValue("whenever")
        dlg._apply_schedule()
        assert "Mon-Fri 08:00-18:00 -> " not in said[-1] and "Use days and hours" in said[-1]
        dlg._until.SetValue("2020-01-01 10:00")
        dlg._apply_until()
        assert "already passed" in said[-1]
        dlg._groups.SetValue("Family, Travel")
        dlg._apply_groups()
        assert dlg._watches.members("travel") == ["cabin"]
        dlg._group_pick.SetStringSelection("Family")
        dlg._group_watch(False)
        assert "cabin" in dlg._muted
    finally:
        dlg.dialog.Destroy()
