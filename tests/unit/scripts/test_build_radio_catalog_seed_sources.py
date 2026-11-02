"""The radio seed leaves out sources whose data has no redistribution terms.

Xiph's directory publishes no terms for its data (2026-11-01 licensing
review), so the seed a release ships must not carry Xiph rows; the app still
refreshes Xiph live. This drives ``_build_stations`` with fake sources, so it
runs offline.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import quill.core.radio.catalog.sources as sources

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "build_radio_catalog.py"
_spec = importlib.util.spec_from_file_location("build_radio_catalog", _SCRIPT)
assert _spec is not None and _spec.loader is not None
builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(builder)


class _Writer:
    def __init__(self) -> None:
        self.upserted: list[str] = []
        self.recorded: list[str] = []

    def upsert_stations(self, source_id: str, page: list[object], *, now: float) -> None:
        self.upserted.append(source_id)

    def record_source(self, source_id: str, **_kwargs: object) -> None:
        self.recorded.append(source_id)


def test_xiph_is_excluded_from_the_seed() -> None:
    assert "xiph" in builder.SEED_EXCLUDED_SOURCES


def test_excluded_sources_are_never_fetched_or_written(monkeypatch) -> None:
    fetched: list[str] = []

    def spec(source_id: str) -> SimpleNamespace:
        def pages():
            fetched.append(source_id)
            yield [object()]

        return SimpleNamespace(id=source_id, fetch_pages=pages)

    monkeypatch.setattr(sources, "station_specs", lambda: [spec("radio_browser"), spec("xiph")])
    writer = _Writer()

    counts = builder._build_stations(writer, from_cache=None)

    assert counts == {"radio_browser": 1}
    assert fetched == ["radio_browser"]
    assert writer.upserted == ["radio_browser"]
    assert writer.recorded == ["radio_browser"]


def test_the_real_xiph_source_id_matches_the_exclusion() -> None:
    """A renamed source id would silently put Xiph back in the seed."""
    assert "xiph" in {item.id for item in sources.station_specs()}
