"""Validation + model tests for the Part-3 per-app contribution types.

Covers the four new host-mediated contributions -- ``directory_providers``
(radio), ``alert_sources`` (weather), ``pipeline_steps`` (studio), and
``location_resolvers`` (beacon): a well-formed manifest is accepted and parsed
into the expected model, and malformed shapes (missing capability, missing main,
bad id, unknown key, out-of-range values) are rejected.
"""

from __future__ import annotations

import json
from pathlib import Path

from quill.core.quillins.model import CAPABILITIES
from quill.core.quillins.validation import parse_manifest, validate_manifest

_BUNDLED = Path(__file__).resolve().parents[3] / "quill" / "quillins_bundled"


def _base(**extra: object) -> dict[str, object]:
    manifest: dict[str, object] = {
        "schema": "quill.extension/1",
        "id": "com.example.q",
        "name": "Q",
        "version": "1.0.0",
    }
    manifest.update(extra)
    return manifest


# -- capability catalogue ----------------------------------------------------


def test_new_capabilities_registered() -> None:
    for cap in ("radio.directory", "weather.alerts", "studio.pipeline", "beacon.resolver"):
        assert cap in CAPABILITIES


def test_schema_and_model_capabilities_agree() -> None:
    schema = json.loads(
        (
            Path(__file__).resolve().parents[3] / "quill" / "core" / "schemas" / "extension.json"
        ).read_text(encoding="utf-8")
    )
    enum = set(schema["properties"]["capabilities"]["items"]["enum"])
    assert enum == CAPABILITIES


# -- radio.directory ---------------------------------------------------------


def test_directory_provider_valid() -> None:
    manifest = _base(
        targets=["radio"],
        capabilities=["radio.directory", "storage"],
        main="ext.py",
        contributes={
            "directory_providers": [{"id": "ext.q.dir", "display_name": "Dir", "handler": "search"}]
        },
    )
    assert validate_manifest(manifest) == []
    parsed = parse_manifest(manifest)
    provider = parsed.contributes.directory_providers[0]
    assert provider.id == "ext.q.dir"
    assert provider.display_name == "Dir"
    assert provider.handler == "search"


def test_directory_provider_requires_capability_and_main() -> None:
    manifest = _base(
        targets=["radio"],
        contributes={
            "directory_providers": [{"id": "ext.q.dir", "display_name": "Dir", "handler": "search"}]
        },
    )
    errors = validate_manifest(manifest)
    assert any("radio.directory" in e for e in errors)
    assert any("main" in e for e in errors)


def test_directory_provider_bad_id_rejected() -> None:
    manifest = _base(
        targets=["radio"],
        capabilities=["radio.directory", "storage"],
        main="ext.py",
        contributes={
            "directory_providers": [{"id": "nope", "display_name": "Dir", "handler": "s"}]
        },
    )
    errors = validate_manifest(manifest)
    assert any("ext." in e for e in errors)


# -- weather.alerts ----------------------------------------------------------


def test_alert_source_valid() -> None:
    manifest = _base(
        targets=["weather"],
        capabilities=["weather.alerts", "storage"],
        main="ext.py",
        contributes={
            "alert_sources": [{"id": "ext.q.src", "handler": "alerts", "interval_seconds": 600}]
        },
    )
    assert validate_manifest(manifest) == []
    src = parse_manifest(manifest).contributes.alert_sources[0]
    assert src.id == "ext.q.src"
    assert src.interval_seconds == 600


def test_alert_source_requires_capability() -> None:
    manifest = _base(
        targets=["weather"],
        main="ext.py",
        contributes={"alert_sources": [{"id": "ext.q.src", "handler": "alerts"}]},
    )
    assert any("weather.alerts" in e for e in validate_manifest(manifest))


def test_alert_source_bad_interval_rejected() -> None:
    manifest = _base(
        targets=["weather"],
        capabilities=["weather.alerts", "storage"],
        main="ext.py",
        contributes={"alert_sources": [{"id": "ext.q.src", "handler": "a", "interval_seconds": 5}]},
    )
    assert any("interval_seconds" in e for e in validate_manifest(manifest))


# -- studio.pipeline ---------------------------------------------------------


def test_pipeline_step_valid() -> None:
    manifest = _base(
        targets=["studio"],
        capabilities=["studio.pipeline", "storage"],
        main="ext.py",
        contributes={
            "pipeline_steps": [
                {"id": "ext.q.n", "stage": "master", "display_name": "N", "handler": "f"}
            ]
        },
    )
    assert validate_manifest(manifest) == []
    step = parse_manifest(manifest).contributes.pipeline_steps[0]
    assert step.stage == "master"
    assert step.display_name == "N"


def test_pipeline_step_bad_stage_rejected() -> None:
    manifest = _base(
        targets=["studio"],
        capabilities=["studio.pipeline", "storage"],
        main="ext.py",
        contributes={
            "pipeline_steps": [
                {"id": "ext.q.n", "stage": "nope", "display_name": "N", "handler": "f"}
            ]
        },
    )
    assert any("stage" in e for e in validate_manifest(manifest))


def test_pipeline_step_requires_capability_and_main() -> None:
    manifest = _base(
        targets=["studio"],
        contributes={
            "pipeline_steps": [
                {"id": "ext.q.n", "stage": "pre", "display_name": "N", "handler": "f"}
            ]
        },
    )
    errors = validate_manifest(manifest)
    assert any("studio.pipeline" in e for e in errors)
    assert any("main" in e for e in errors)


# -- beacon.resolver ---------------------------------------------------------


def test_location_resolver_valid() -> None:
    manifest = _base(
        targets=["beacon"],
        capabilities=["beacon.resolver", "storage"],
        main="ext.py",
        contributes={
            "location_resolvers": [
                {"id": "ext.q.r", "handler": "resolve", "content_types": ["web", "epub"]}
            ]
        },
    )
    assert validate_manifest(manifest) == []
    resolver = parse_manifest(manifest).contributes.location_resolvers[0]
    assert resolver.content_types == ("web", "epub")


def test_location_resolver_requires_capability() -> None:
    manifest = _base(
        targets=["beacon"],
        main="ext.py",
        contributes={"location_resolvers": [{"id": "ext.q.r", "handler": "resolve"}]},
    )
    assert any("beacon.resolver" in e for e in validate_manifest(manifest))


def test_location_resolver_unknown_key_rejected() -> None:
    manifest = _base(
        targets=["beacon"],
        capabilities=["beacon.resolver", "storage"],
        main="ext.py",
        contributes={"location_resolvers": [{"id": "ext.q.r", "handler": "resolve", "bogus": 1}]},
    )
    assert any("unknown property" in e for e in validate_manifest(manifest))


# -- bundled samples validate ------------------------------------------------


def test_bundled_part3_samples_validate() -> None:
    for name in (
        "radio-community-directory",
        "weather-extra-alerts",
        "studio-normalizer",
        "beacon-transit-resolver",
        "daily-stamp",
    ):
        raw = json.loads((_BUNDLED / name / "manifest.json").read_text(encoding="utf-8"))
        assert validate_manifest(raw) == [], name
        parse_manifest(raw)  # must not raise


def test_daily_stamp_targets_editor_and_beacon() -> None:
    raw = json.loads((_BUNDLED / "daily-stamp" / "manifest.json").read_text(encoding="utf-8"))
    manifest = parse_manifest(raw)
    assert manifest.target_apps == ("quill", "beacon")
    # Layer-1: no capabilities, no main module.
    assert manifest.capabilities == ()
    assert manifest.main is None
