"""Tests for :class:`quill.core.quillins.app_host.QuillinAppHost` (wx-free).

Discovery, contribution collection, event firing, Safe-Mode no-op, and
feed-auth provider registration are exercised with fake ``HostServices`` and
``AppFrameAdapter`` collaborators -- no ``wx``, and (except the one explicit
end-to-end test) no out-of-process worker.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from quill.core.podcasts import feed_auth, feed_auth_registry
from quill.core.podcasts.models import PodcastShow
from quill.core.quillins import app_host as app_host_module
from quill.core.quillins.app_host import QuillinAppHost
from quill.core.quillins.loader import InstalledExtension
from quill.core.quillins.validation import parse_manifest

_BUNDLED_ROOT = Path(__file__).resolve().parents[3] / "quill" / "quillins_bundled"
_SAMPLE_DIR = _BUNDLED_ROOT / "cast-premium-auth"


class _FakeFeatures:
    def __init__(self, *, bundled: bool = True, third_party: bool = False) -> None:
        self._bundled = bundled
        self._third_party = third_party

    def is_enabled(self, feature_id: str) -> bool:
        if feature_id == "core.bundled_quillins":
            return self._bundled
        if feature_id == "core.third_party_plugins":
            return self._third_party
        return False


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
    def __init__(self) -> None:
        self.commands: list[tuple[str, str, object, object]] = []
        self.menu: list[tuple[str, str]] = []
        self.announced: list[str] = []

    def register_command(self, command_id, title, handler, binding) -> None:  # noqa: ANN001
        self.commands.append((command_id, title, handler, binding))

    def add_menu_command(self, command_id: str, title: str) -> None:
        self.menu.append((command_id, title))

    def announce(self, message: str) -> None:
        self.announced.append(message)


@pytest.fixture(autouse=True)
def _clear_registry() -> Iterator[None]:
    feed_auth_registry.clear_providers()
    yield
    feed_auth_registry.clear_providers()


def _make_host(app_id: str = "cast", *, safe_mode: bool = False, root: Path | None = None):
    services = _FakeServices()
    adapter = _FakeAdapter()
    host = QuillinAppHost(
        app_id=app_id,
        services=services,
        consent=lambda _c, _d: False,
        frame_adapter=adapter,
        features=_FakeFeatures(),
        keymap={},
        safe_mode=safe_mode,
        root=root,
    )
    return host, services, adapter


def _patch_bundled(monkeypatch: pytest.MonkeyPatch, manifests, installed) -> None:
    monkeypatch.setattr(
        app_host_module, "load_enabled_bundled_manifests", lambda *a, **k: list(manifests)
    )
    monkeypatch.setattr(app_host_module, "load_enabled_manifests", lambda *a, **k: [])
    monkeypatch.setattr(
        app_host_module, "discover_bundled_extensions", lambda *a, **k: list(installed)
    )
    monkeypatch.setattr(app_host_module, "discover_extensions", lambda *a, **k: [])


def _snippet_manifest():
    return parse_manifest({
        "schema": "quill.extension/1",
        "id": "com.example.snip",
        "name": "Snip",
        "version": "1.0.0",
        "targets": ["cast"],
        "contributes": {
            "commands": [{"id": "ext.snip.hi", "title": "Say Hi", "run": {"snippet": "hi there"}}]
        },
    })


# -- Safe Mode ---------------------------------------------------------------


def test_safe_mode_registers_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _snippet_manifest()
    installed = InstalledExtension(
        id=manifest.id, directory=_SAMPLE_DIR, manifest=manifest, enabled=True
    )
    _patch_bundled(monkeypatch, [manifest], [installed])
    host, _services, adapter = _make_host(safe_mode=True)
    host.load()
    assert adapter.commands == []
    assert adapter.menu == []
    assert any("Safe Mode" in m for m in adapter.announced)


# -- contribution collection -------------------------------------------------


def test_load_collects_and_registers_contributions(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _snippet_manifest()
    installed = InstalledExtension(
        id=manifest.id, directory=_SAMPLE_DIR, manifest=manifest, enabled=True
    )
    _patch_bundled(monkeypatch, [manifest], [installed])
    host, _services, adapter = _make_host()
    host.load()
    assert host.registry is not None
    assert ("ext.snip.hi", "Say Hi") in adapter.menu
    registered_ids = {c[0] for c in adapter.commands}
    assert "ext.snip.hi" in registered_ids


def test_run_snippet_command_uses_clipboard(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _snippet_manifest()
    installed = InstalledExtension(
        id=manifest.id, directory=_SAMPLE_DIR, manifest=manifest, enabled=True
    )
    _patch_bundled(monkeypatch, [manifest], [installed])
    host, services, _adapter = _make_host()
    host.load()
    host.run_command("ext.snip.hi")
    assert services.clipboard == "hi there"


# -- event firing ------------------------------------------------------------


def test_fire_event_dispatches_to_subscribed_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = parse_manifest({
        "schema": "quill.extension/1",
        "id": "com.example.events",
        "name": "Events",
        "version": "1.0.0",
        "capabilities": ["document.events"],
        "main": "ext.py",
        "contributes": {
            "document_events": [
                {
                    "event": "document.after_save",
                    "handler": "on_save",
                    "title": "On save",
                    "description": "runs on save",
                }
            ]
        },
    })
    installed = InstalledExtension(
        id=manifest.id, directory=_SAMPLE_DIR, manifest=manifest, enabled=True
    )
    _patch_bundled(monkeypatch, [manifest], [installed])
    host, _services, _adapter = _make_host(app_id="quill")

    calls: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        host,
        "_run_event_handler_async",
        lambda _m, _d, handler, ctx: calls.append((handler, ctx)),
    )
    host.load()
    host.fire_event("document.after_save", {"path": "x.txt"})
    assert ("on_save", {"path": "x.txt"}) in calls


# -- feed-auth provider registration ----------------------------------------


def test_load_registers_feed_auth_provider_from_contribution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = parse_manifest({
        "schema": "quill.extension/1",
        "id": "com.example.premium",
        "name": "Premium",
        "version": "1.0.0",
        "targets": ["cast"],
        "capabilities": ["podcast.feed.auth", "storage"],
        "main": "extension.py",
        "contributes": {
            "feed_auth_providers": [
                {
                    "id": "ext.premium.provider",
                    "match_hosts": ["premium.example.com"],
                    "handler": "feed_auth_header",
                }
            ]
        },
    })
    installed = InstalledExtension(
        id=manifest.id, directory=_SAMPLE_DIR, manifest=manifest, enabled=True
    )
    _patch_bundled(monkeypatch, [manifest], [installed])
    host, _services, _adapter = _make_host()
    host.load()
    assert "ext.premium.provider" in feed_auth_registry.registered_provider_ids()
    # A full teardown clears the provider it registered.
    host.shutdown()
    assert "ext.premium.provider" not in feed_auth_registry.registered_provider_ids()


# -- end-to-end (real out-of-process worker, real bundled sample) ------------


def test_bundled_cast_premium_auth_supplies_header_end_to_end() -> None:
    """The real bundled ``cast-premium-auth`` Quillin, loaded by QuillinAppHost
    for the ``cast`` app, supplies a Bearer header that feed_auth returns."""

    host, _services, _adapter = _make_host(app_id="cast", root=None)
    host.load()
    try:
        assert "ext.castpremiumauth.provider" in feed_auth_registry.registered_provider_ids()
        show = PodcastShow(
            id="premium-show",
            title="Premium",
            feed_url="https://premium.example.com/feed.xml",
        )
        header = feed_auth.auth_header_for_url(show, "https://premium.example.com/ep.mp3")
        assert header == "Bearer demo-premium-token"
    finally:
        host.shutdown()
