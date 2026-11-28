"""The Weather Around Me window: the report and its credit are what Copy takes,
and the caret starts on the first line."""

from __future__ import annotations

import pytest

from quill.ui.weather.text_report_dialog import TextReportDialog
from tests.wx_session import shared_wx_app


@pytest.fixture
def app():
    a = shared_wx_app()
    yield a
    a.Destroy()


def test_the_report_carries_its_credit(app) -> None:
    dlg = TextReportDialog(
        None,
        intro="Around you.",
        text="Dry here now.\nRain 25 miles west, moving toward you.",
        box_name="Weather around you",
        box_help="Read it.",
        credits="Weather data by Open-Meteo.com.",
    )
    try:
        assert dlg.text.endswith("\n\nSources: Weather data by Open-Meteo.com.")
        assert dlg.dialog.GetTitle() == "Weather Around Me"
        assert dlg._box.GetInsertionPoint() == 0
    finally:
        dlg.dialog.Destroy()
