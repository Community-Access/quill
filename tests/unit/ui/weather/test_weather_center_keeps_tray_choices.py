"""Weather Center's Settings never puts back a tray choice made while it was open.

The family settings audit (2026-11-20): Weather Center reads the settings
once, when it opens, and its Settings button saved that copy -- every field
of it. A choice made from the tray in the meantime (Close to Tray, Start in
Tray) was quietly turned back the next time Settings was saved there.

The test does what the person does: open Weather Center, change a choice from
the tray, change units in Weather Center's Settings and save, then reload
from disk as the next launch would. Both choices must be there.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.core.weather import settings as settings_mod


class _NoTasks:
    def submit(self, *_a, **_k):
        return None


def test_saving_weather_center_settings_keeps_a_tray_choice_made_meanwhile(
    wx_session_app, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.apps import weather_options
    from quill.ui.weather.settings_dialog import WeatherSettingsDialog
    from quill.ui.weather.weather_center_dialog import WeatherCenterDialog

    assert settings_mod.load_settings(tmp_path).app_close_to_tray is True
    center = WeatherCenterDialog(None, data_dir=tmp_path, task_manager=_NoTasks(), safe_mode=False)
    try:
        # From the tray, while Weather Center is open: stop closing to the tray.
        said: list[str] = []
        tray = SimpleNamespace(_weather_data_dir=lambda: tmp_path, _announce=said.append)
        weather_options.set_app_pref(tray, "app_close_to_tray", False)
        assert settings_mod.load_settings(tmp_path).app_close_to_tray is False

        # In Weather Center: Settings, Celsius, Save.
        def press_save(dialog: WeatherSettingsDialog) -> bool:
            dialog._temp.SetSelection(settings_mod.TEMPERATURE_UNITS.index("C"))
            dialog._save()
            dialog.dialog.Destroy()
            return dialog._saved

        monkeypatch.setattr(WeatherSettingsDialog, "show", press_save)
        center._open_settings()
    finally:
        center.dialog.Destroy()

    # The next launch: the units changed, and the tray choice is still the latest.
    reloaded = settings_mod.load_settings(tmp_path)
    assert reloaded.temperature_unit == "C"
    assert reloaded.app_close_to_tray is False, "Weather Center put the tray choice back"
    # And Weather Center itself now shows both.
    assert center._settings.temperature_unit == "C"
    assert center._settings.app_close_to_tray is False
