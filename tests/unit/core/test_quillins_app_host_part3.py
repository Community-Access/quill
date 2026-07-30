"""QuillinAppHost registration tests for the Part-3 per-app contributions.

Each capability's provider is registered into its per-app registry when an app
host for the right app loads, cleared on shutdown, and skipped in Safe Mode. The
end-to-end tests load the real bundled samples through the out-of-process worker
and assert the contributed data flows through the consumption seam.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from quill.apps.beacon import resolver_registry
from quill.core.audio_studio import pipeline_registry
from quill.core.quillins import app_host as app_host_module
from quill.core.quillins.app_host import QuillinAppHost
from quill.core.quillins.loader import InstalledExtension
from quill.core.quillins.validation import parse_manifest
from quill.core.radio import directory_registry, directory_search
from quill.core.weather import alert_source_registry

_BUNDLED = Path(__file__).resolve().parents[3] / "quill" / "quillins_bundled"


@pytest.fixture(autouse=True)
def _clear_registries() -> Iterator[None]:
    for clear in (
        directory_registry.clear_providers,
        alert_source_registry.clear_sources,
        pipeline_registry.clear_steps,
        resolver_registry.clear_resolvers,
    ):
        clear()
    yield
    for clear in (
        directory_registry.clear_providers,
        alert_source_registry.clear_sources,
        pipeline_registry.clear_steps,
        resolver_registry.clear_resolvers,
    ):
        clear()


class _FakeFeatures:
    def is_enabled(self, feature_id: str) -> bool:
        return feature_id == "core.bundled_quillins"


class _FakeServices:
    def __init__(self) -> None:
        self.clipboard = ""

    def set_clipboard(self, text: str) -> None:
        self.clipboard = text

    def get_clipboard(self) -> str:
        return self.clipboard

    def is_verbosity_speech_enabled(self) -> bool:
        return True


class _FakeAdapter:
    def register_command(self, *args: object) -> None:  # noqa: D401
        pass

    def add_menu_command(self, *args: object) -> None:
        pass

    def announce(self, message: str) -> None:
        pass


def _make_host(app_id: str, *, safe_mode: bool = False, root: Path | None = None) -> QuillinAppHost:
    return QuillinAppHost(
        app_id=app_id,
        services=_FakeServices(),
        consent=lambda _c, _d: False,
        frame_adapter=_FakeAdapter(),
        features=_FakeFeatures(),
        keymap={},
        safe_mode=safe_mode,
        root=root,
    )


def _patch(monkeypatch: pytest.MonkeyPatch, manifests: list, installed: list) -> None:
    monkeypatch.setattr(
        app_host_module, "load_enabled_bundled_manifests", lambda *a, **k: list(manifests)
    )
    monkeypatch.setattr(app_host_module, "load_enabled_manifests", lambda *a, **k: [])
    monkeypatch.setattr(
        app_host_module, "discover_bundled_extensions", lambda *a, **k: list(installed)
    )
    monkeypatch.setattr(app_host_module, "discover_extensions", lambda *a, **k: [])


def _install(manifest: object) -> InstalledExtension:
    return InstalledExtension(
        id=manifest.id,  # type: ignore[attr-defined]
        directory=_BUNDLED / "cast-premium-auth",
        manifest=manifest,
        enabled=True,
    )


# -- registration from a contribution (no worker; ids only) ------------------


def _directory_manifest() -> object:
    return parse_manifest({
        "schema": "quill.extension/1",
        "id": "com.example.dir",
        "name": "Dir",
        "version": "1.0.0",
        "targets": ["radio"],
        "capabilities": ["radio.directory", "storage"],
        "main": "extension.py",
        "contributes": {
            "directory_providers": [{"id": "ext.dir.p", "display_name": "P", "handler": "search"}]
        },
    })


def test_directory_provider_registered_and_cleared(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _directory_manifest()
    _patch(monkeypatch, [manifest], [_install(manifest)])
    host = _make_host("radio")
    host.load()
    assert "ext.dir.p" in directory_registry.registered_provider_ids()
    host.shutdown()
    assert "ext.dir.p" not in directory_registry.registered_provider_ids()


def test_directory_provider_safe_mode_registers_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _directory_manifest()
    _patch(monkeypatch, [manifest], [_install(manifest)])
    host = _make_host("radio", safe_mode=True)
    host.load()
    assert directory_registry.registered_provider_ids() == ()


def test_alert_source_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = parse_manifest({
        "schema": "quill.extension/1",
        "id": "com.example.alerts",
        "name": "Alerts",
        "version": "1.0.0",
        "targets": ["weather"],
        "capabilities": ["weather.alerts", "storage"],
        "main": "extension.py",
        "contributes": {"alert_sources": [{"id": "ext.al.s", "handler": "alerts"}]},
    })
    _patch(monkeypatch, [manifest], [_install(manifest)])
    host = _make_host("weather")
    host.load()
    assert "ext.al.s" in alert_source_registry.registered_source_ids()
    host.shutdown()
    assert alert_source_registry.registered_source_ids() == ()


def test_pipeline_step_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = parse_manifest({
        "schema": "quill.extension/1",
        "id": "com.example.pipe",
        "name": "Pipe",
        "version": "1.0.0",
        "targets": ["studio"],
        "capabilities": ["studio.pipeline", "storage"],
        "main": "extension.py",
        "contributes": {
            "pipeline_steps": [
                {"id": "ext.p.s", "stage": "master", "display_name": "S", "handler": "f"}
            ]
        },
    })
    _patch(monkeypatch, [manifest], [_install(manifest)])
    host = _make_host("studio")
    host.load()
    assert "ext.p.s" in pipeline_registry.registered_step_ids()
    host.shutdown()
    assert pipeline_registry.registered_step_ids() == ()


def test_location_resolver_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = parse_manifest({
        "schema": "quill.extension/1",
        "id": "com.example.res",
        "name": "Res",
        "version": "1.0.0",
        "targets": ["beacon"],
        "capabilities": ["beacon.resolver", "storage"],
        "main": "extension.py",
        "contributes": {"location_resolvers": [{"id": "ext.r.r", "handler": "resolve"}]},
    })
    _patch(monkeypatch, [manifest], [_install(manifest)])
    host = _make_host("beacon")
    host.load()
    assert "ext.r.r" in resolver_registry.registered_resolver_ids()
    host.shutdown()
    assert resolver_registry.registered_resolver_ids() == ()


# -- end-to-end with the real bundled samples (real worker) ------------------


def test_bundled_radio_directory_end_to_end() -> None:
    host = _make_host("radio", root=None)
    host.load()
    try:
        assert "ext.radiocommunitydirectory.provider" in (
            directory_registry.registered_provider_ids()
        )
        stations = directory_search.directory_provider_stations("community")
        assert any(s.name == "Community Voices FM" for s in stations)
        assert all(s.source == "Community Directory" for s in stations)
    finally:
        host.shutdown()


def test_bundled_weather_alerts_end_to_end() -> None:
    host = _make_host("weather", root=None)
    host.load()
    try:
        assert "ext.weatherextraalerts.source" in alert_source_registry.registered_source_ids()
        alerts = alert_source_registry.alerts_from_sources()
        assert any(a.event == "Community Advisory" for a in alerts)
    finally:
        host.shutdown()


def test_bundled_studio_pipeline_end_to_end() -> None:
    from quill.core.audio_enhance import build_filter_graph

    host = _make_host("studio", root=None)
    host.load()
    try:
        assert "ext.studionormalizer.loudnorm" in pipeline_registry.registered_step_ids()
        graph = build_filter_graph(0, 0, 0, compressor_enabled=False, pipeline_stage="master")
        assert "loudnorm" in graph
        # A radio-style caller (no stage) is unaffected.
        assert build_filter_graph(0, 0, 0, compressor_enabled=False) == ""
    finally:
        host.shutdown()


def test_bundled_beacon_resolver_end_to_end() -> None:
    host = _make_host("beacon", root=None)
    host.load()
    try:
        assert "ext.beacontransitresolver.resolver" in (resolver_registry.registered_resolver_ids())
        # Drive the real out-of-process handler through the registry seam: the
        # bundled resolver does a case-insensitive quote search and returns a
        # low-confidence (needs-review) match.
        resolution = resolver_registry.resolve_from_providers(
            {"text_quote": {"exact": "Chapter Seven begins"}},
            "intro ... CHAPTER SEVEN BEGINS ... outro",
            content_type="web",
        )
        assert resolution is not None
        assert resolution["matched"] is True
        assert resolution["layer"] == "quillin"
    finally:
        host.shutdown()
