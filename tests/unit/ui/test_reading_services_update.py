"""Radio Reading Services refresh summary used by the Station menu's "Update
Radio Reading Services..." command (task 13): a pure, wx-free wrapper over
``reading_services.refresh_reading_services``, testable with no wx and no
network. Mirrors ``test_weather_noaa_menu.py``'s approach for the sibling
NOAA Weather Radio directory-update command (task 8)."""

from __future__ import annotations

from quill.apps import radio as radio_app
from quill.core.radio.radio_browser import RadioBrowserError
from quill.core.radio.reading_services import RrsRefreshResult


def test_reading_services_refresh_summary_reports_count(monkeypatch):
    monkeypatch.setattr(
        radio_app.reading_services,
        "refresh_reading_services",
        lambda *, safe_mode=False: RrsRefreshResult(count=3, generated_at="2026-07-19T00:00:00Z"),
    )
    summary = radio_app.reading_services_refresh_summary(safe_mode=False)
    assert "3" in summary
    assert "Radio Reading Services" in summary


def test_reading_services_refresh_summary_reports_failure_without_raising(monkeypatch):
    def _raise(*, safe_mode=False):
        raise RadioBrowserError("Radio Reading Services is disabled in Safe Mode.")

    monkeypatch.setattr(radio_app.reading_services, "refresh_reading_services", _raise)
    summary = radio_app.reading_services_refresh_summary(safe_mode=True)
    assert "Could not update Radio Reading Services" in summary
