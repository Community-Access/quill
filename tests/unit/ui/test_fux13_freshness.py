"""FUX-13 in GitHub Workbench, Weather and Beacon: old data is not called current."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from quill.apps.beacon import health_words
from quill.apps.beacon import model as beacon_model
from quill.core.workbench import freshness

# -- Workbench -----------------------------------------------------------------


def test_loading_cell_is_not_up_to_date_after_a_failed_refresh() -> None:
    assert freshness.loading_cell(loading=False, loaded_at="10:42", failed=False) == (
        "Up to date, 10:42"
    )
    assert freshness.loading_cell(loading=False, loaded_at="10:42", failed=True) == (
        "Not up to date, from 10:42; the refresh failed"
    )
    assert freshness.loading_cell(loading=False, loaded_at="", failed=True) == "Load failed"
    assert freshness.loading_cell(loading=True, loaded_at="10:42", failed=True) == "Loading"


def test_failure_sentence_says_what_is_shown_and_how_to_retry() -> None:
    said = freshness.failure_sentence(
        "Issues", OSError("No connection."), loaded_at="10:42", refresh_key="F5"
    )
    assert said == (
        "Could not load Issues: No connection. The list shown is from 10:42. "
        "Refresh (F5) tries again."
    )
    bare = freshness.failure_sentence("Issues", OSError("timed out"), loaded_at="", refresh_key="")
    assert bare == "Could not load Issues: timed out. Refresh tries again."


def test_local_clock_reads_a_stored_utc_time() -> None:
    moment = datetime(2026, 11, 24, 17, 42, tzinfo=UTC)
    assert freshness.local_clock("2026-11-24T17:42:00Z") == moment.astimezone().strftime("%H:%M")
    assert freshness.local_clock("") == ""


def _frame(rows: list[object]) -> SimpleNamespace:
    said: list[str] = []
    details = SimpleNamespace(value="")
    frame = SimpleNamespace(
        _generation=3,
        loading=True,
        load_failed=False,
        loaded_at="10:42",
        rows=rows,
        _keys={"github.workbench.refresh": "F5"},
        status=SimpleNamespace(refresh=lambda: None),
        details=SimpleNamespace(ChangeValue=lambda text: setattr(details, "value", text)),
        _say=said.append,
        list=SimpleNamespace(SetFocus=lambda: None),
        filter=SimpleNamespace(SetFocus=lambda: None),
        reload=lambda: None,
    )
    frame.said, frame.detail_box = said, details
    return frame


def test_frame_failed_load_keeps_the_time_of_the_rows_shown() -> None:
    from quill.ui.github_workbench_status import github_status_cells
    from quill.ui.workbench_frame import WorkbenchFrame
    from quill.ui.workbench_frame_commands import WorkbenchCommandsMixin

    frame = _frame(rows=["row"])
    frame.failure_words = lambda label, error: WorkbenchCommandsMixin.failure_words(
        frame, label, error
    )
    WorkbenchFrame._load_failed(frame, 3, SimpleNamespace(label="Issues"), OSError("offline"))
    assert frame.load_failed is True
    assert frame.said == [
        "Could not load Issues: offline. The list shown is from 10:42. Refresh (F5) tries again."
    ]
    provider = SimpleNamespace(signed_in=True, local_note="")
    cell = next(c for c in github_status_cells(provider, frame) if c.key == "loading")
    assert cell.text() == "Not up to date, from 10:42; the refresh failed"
    assert WorkbenchCommandsMixin.loading_words(frame).startswith("Not up to date")


def test_frame_failed_load_with_nothing_shown_has_no_time() -> None:
    from quill.ui.workbench_frame import WorkbenchFrame
    from quill.ui.workbench_frame_commands import WorkbenchCommandsMixin

    frame = _frame(rows=[])
    frame.failure_words = lambda label, error: WorkbenchCommandsMixin.failure_words(
        frame, label, error
    )
    WorkbenchFrame._load_failed(frame, 3, SimpleNamespace(label="Pulls"), OSError("offline"))
    assert frame.loaded_at == ""
    assert "The list shown" not in frame.said[0]


# -- Weather ---------------------------------------------------------------------


def test_weather_time_line_names_the_time_of_an_older_reading() -> None:
    from quill.ui.weather.center_text import local_time_line

    settings = SimpleNamespace(show_local_time=True)
    report = SimpleNamespace(time_zone="America/Denver")
    fresh = local_time_line(settings, report, "Denver", datetime.now(UTC))
    assert fresh.endswith("This reading was checked just now.")
    older = local_time_line(settings, report, "Denver", datetime.now(UTC) - timedelta(hours=2))
    assert "This reading was checked at " in older
    assert "just now" not in older


def test_weather_failed_refresh_says_the_old_reading_is_still_shown() -> None:
    from quill.core.weather import nws
    from quill.ui.weather.weather_center_dialog import WeatherCenterDialog

    said: list[str] = []
    status = SimpleNamespace(value="")
    host = SimpleNamespace(
        _report=object(),
        _shown_location=("a", "Boise"),
        _checked_at=datetime(2026, 11, 24, 15, 5, tzinfo=UTC),
        _status=SimpleNamespace(SetValue=lambda text: setattr(status, "value", text)),
        _announce=said.append,
    )
    location = SimpleNamespace(label="Denver")
    WeatherCenterDialog._render_report(host, location, nws.WeatherError("Network down"))
    assert said == [status.value]
    assert status.value.startswith("Could not load weather for Denver: ")
    assert "Network down. Still showing" in status.value
    assert "Still showing the earlier reading for Boise, checked at " in status.value
    assert status.value.endswith("Refresh (Alt+R) tries again.")


# -- Beacon ----------------------------------------------------------------------


def test_beacon_health_is_said_in_words() -> None:
    assert health_words.column(beacon_model.HEALTH_OFFLINE) == "Available offline"
    assert health_words.column(beacon_model.HEALTH_UNAVAILABLE) == "Unavailable for now"
    assert health_words.detail(beacon_model.HEALTH_BROKEN) == (
        "Health: Broken link. It could not be found last time. "
        "Revalidate Health (Ctrl+Alt+H) checks it again."
    )
    assert health_words.column("somethingNew") == "somethingNew"
    for code in health_words.COLUMN:
        assert code != health_words.column(code) or code == "Archived"


def test_beacon_sync_detail() -> None:
    assert health_words.sync_detail(True, True) == (
        "Sync: changed on this computer, not synced yet."
    )
    assert health_words.sync_detail(False, True) == "Sync: synced."
    assert health_words.sync_detail(True, False) == ""


def test_beacon_health_column_reads_words() -> None:
    from quill.apps.beacon.app import BeaconFrame

    bookmark = SimpleNamespace(resource_id="", health=beacon_model.HEALTH_ONLINE_ONLY)
    host = SimpleNamespace(
        _results_cache=[bookmark], store=SimpleNamespace(get_resource=lambda _id: None)
    )
    assert BeaconFrame.OnGetItemText(host, 0, 6) == "Online only"
