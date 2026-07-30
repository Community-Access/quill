"""Tests for the Quillin station-directory registry and its use by the search."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from quill.core.radio import directory_registry, directory_search


@pytest.fixture(autouse=True)
def _clear() -> Iterator[None]:
    directory_registry.clear_providers()
    yield
    directory_registry.clear_providers()


def test_provider_rows_returned_and_badged() -> None:
    directory_registry.register_provider(
        "ext.p", "My Dir", lambda _q: [{"name": "A", "url": "http://a"}]
    )
    rows = directory_registry.stations_from_providers("a")
    assert rows == [{"name": "A", "url": "http://a", "source": "My Dir"}]


def test_row_source_override_kept() -> None:
    directory_registry.register_provider(
        "ext.p", "My Dir", lambda _q: [{"name": "A", "url": "http://a", "source": "Custom"}]
    )
    assert directory_registry.stations_from_providers("a")[0]["source"] == "Custom"


def test_rows_without_name_or_url_dropped() -> None:
    directory_registry.register_provider(
        "ext.p",
        "My Dir",
        lambda _q: [{"name": "", "url": "http://a"}, {"name": "B", "url": ""}],
    )
    assert directory_registry.stations_from_providers("a") == []


def test_faulty_provider_skipped() -> None:
    def _boom(_q: str) -> list[dict[str, str]]:
        raise RuntimeError("boom")

    directory_registry.register_provider("ext.bad", "Bad", _boom)
    directory_registry.register_provider(
        "ext.good", "Good", lambda _q: [{"name": "A", "url": "http://a"}]
    )
    rows = directory_registry.stations_from_providers("a")
    assert [r["name"] for r in rows] == ["A"]


def test_register_replaces_by_id() -> None:
    directory_registry.register_provider("ext.p", "One", lambda _q: [])
    directory_registry.register_provider("ext.p", "Two", lambda _q: [])
    assert directory_registry.registered_provider_ids() == ("ext.p",)


def test_search_seam_builds_radio_stations() -> None:
    directory_registry.register_provider(
        "ext.p", "Comm", lambda _q: [{"name": "Voices", "url": "http://v"}]
    )
    stations = directory_search.directory_provider_stations("voices")
    assert len(stations) == 1
    assert stations[0].name == "Voices"
    assert stations[0].stream_url == "http://v"
    assert stations[0].source == "Comm"


def test_search_seam_empty_in_safe_mode() -> None:
    directory_registry.register_provider(
        "ext.p", "Comm", lambda _q: [{"name": "Voices", "url": "http://v"}]
    )
    assert directory_search.directory_provider_stations("voices", safe_mode=True) == []


def test_search_seam_empty_query() -> None:
    assert directory_search.directory_provider_stations("   ") == []
