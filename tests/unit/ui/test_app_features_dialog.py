"""Customize Features dialog: builds a checkbox per area reflecting current
state, and _save writes the toggles back into the settings model."""

from __future__ import annotations

import pytest
import wx

from quill.core.app_features import AppArea, AppFeatureSettings
from quill.ui.app_features_dialog import AppFeaturesDialog

_AREAS = (
    AppArea("recording", "Recording", "The Record menu."),
    AppArea("weather", "Weather", "The Weather menu."),
)


@pytest.fixture
def app():
    a = wx.App(False)
    yield a
    a.Destroy()


def test_builds_a_checkbox_per_area_reflecting_state(app) -> None:
    settings = AppFeatureSettings(app_id="radio", disabled={"weather"})
    dlg = AppFeaturesDialog(None, app_title="Quill Radio", areas=_AREAS, settings=settings)
    try:
        assert dlg._checks["recording"].GetValue() is True
        assert dlg._checks["weather"].GetValue() is False  # disabled -> unchecked
    finally:
        dlg.dialog.Destroy()


def test_save_writes_toggles_back(app) -> None:
    settings = AppFeatureSettings(app_id="radio")
    dlg = AppFeaturesDialog(None, app_title="Quill Radio", areas=_AREAS, settings=settings)
    try:
        dlg._checks["weather"].SetValue(False)  # user turns Weather off
        dlg._save()
        assert settings.is_enabled("weather") is False
        assert settings.is_enabled("recording") is True
        assert dlg._saved is True
    finally:
        dlg.dialog.Destroy()
