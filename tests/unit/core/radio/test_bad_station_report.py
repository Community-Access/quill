"""The pre-filled bad-station report builder (#1218)."""

from __future__ import annotations

from quill.core.radio.bad_station_report import build_bad_station_report
from quill.core.radio.models import RadioStation


def _station(**kw: object) -> RadioStation:
    base: dict[str, object] = {"name": "WAAI 100.9", "stream_url": "http://x/waai"}
    base.update(kw)
    return RadioStation(**base)  # type: ignore[arg-type]


def test_summary_names_the_station() -> None:
    summary, _ = build_bad_station_report(_station(country="United States"))
    assert summary == "Bad station: WAAI 100.9 (United States)"


def test_body_leads_with_the_problem_and_names_the_station() -> None:
    _, body = build_bad_station_report(_station())
    assert body.startswith("This station would not play.")
    assert "Station: WAAI 100.9" in body
    assert "will not play" in body


def test_body_includes_stream_url_and_identifying_fields() -> None:
    _, body = build_bad_station_report(
        _station(
            station_uuid="abc-123",
            source="Radio Browser",
            codec="MP3",
            bitrate_kbps=128,
            homepage="http://waai.example",
        )
    )
    assert "Stream URL: http://x/waai" in body
    assert "Station UUID: abc-123" in body
    assert "Source: Radio Browser" in body
    assert "Format: MP3 128 kbps" in body
    assert "Homepage: http://waai.example" in body


def test_sparse_station_omits_empty_fields() -> None:
    _, body = build_bad_station_report(_station())
    # No UUID/source/format/homepage lines when the station lacks them.
    assert "Station UUID" not in body
    assert "Source:" not in body
    assert "Format:" not in body
    assert "Homepage:" not in body


def test_unresolved_stream_url_is_flagged_not_blank() -> None:
    _, body = build_bad_station_report(_station(stream_url=""))
    assert "Stream URL: (none resolved)" in body


def test_body_carries_no_pii() -> None:
    # The block is clipboard/URL-safe: station metadata only, nothing about the
    # user or their machine (that is added downstream by the report flow).
    _, body = build_bad_station_report(_station(station_uuid="abc-123"))
    lowered = body.lower()
    assert "email" not in lowered
    assert "appdata" not in lowered
