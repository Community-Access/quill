"""Weather Settings ends with what is now true (FUX-04).

A Save whose file could not be written used to raise out of the button with
nothing said: the window stayed open and the listener heard silence. Now it
says the settings were not saved and keeps the choices in the window; a Save
that lands still says "saved", once, after the write.
"""

from __future__ import annotations

import pytest

from quill.core.weather import settings as settings_mod


def _dialog(tmp_path, said):
    from quill.ui.weather.settings_dialog import WeatherSettingsDialog

    return WeatherSettingsDialog(
        None,
        settings=settings_mod.load_settings(tmp_path),
        data_dir=tmp_path,
        announce_cb=said.append,
    )


def test_a_save_that_could_not_be_written_says_so_and_keeps_the_window(
    wx_session_app, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(*_a, **_k):
        raise PermissionError("read only")

    monkeypatch.setattr(settings_mod, "save_settings", refuse)
    said: list[str] = []
    dialog = _dialog(tmp_path, said)
    try:
        dialog._save()
        assert dialog._saved is False
        assert said == [
            "Weather settings were not saved: the data folder could not be written. "
            "Your choices are still in this window."
        ]
    finally:
        dialog.dialog.Destroy()


def test_a_save_that_lands_says_saved_once(wx_session_app, tmp_path) -> None:
    said: list[str] = []
    dialog = _dialog(tmp_path, said)
    try:
        dialog._temp.SetSelection(settings_mod.TEMPERATURE_UNITS.index("C"))
        dialog._save()
    finally:
        dialog.dialog.Destroy()
    assert said == ["Weather settings saved."]
    assert settings_mod.load_settings(tmp_path).temperature_unit == "C"
