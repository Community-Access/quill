"""Tests for the plugin system (PRD 34)."""

import pytest

from quill_social.services.plugins import (
    PluginError,
    PluginManifest,
    PluginRegistry,
)


def _manifest(**over):
    base = {
        "id": "acme.tool",
        "name": "Acme Tool",
        "version": "1.0.0",
        "kind": "composer_tool",
        "declared_permissions": ["compose"],
        "entry": "acme:main",
    }
    base.update(over)
    return base


def test_validation_rejects_missing_fields():
    for missing in ("id", "name", "version", "kind", "entry"):
        d = _manifest()
        d.pop(missing)
        with pytest.raises(PluginError):
            PluginManifest.validate(d)


def test_validation_rejects_unknown_kind():
    with pytest.raises(PluginError):
        PluginManifest.validate(_manifest(kind="not_a_kind"))


def test_manifest_roundtrip():
    m = PluginManifest.validate(_manifest())
    assert PluginManifest.from_dict(m.to_dict()) == m


def test_permission_enforcement(store):
    reg = PluginRegistry(store)
    m = reg.load(_manifest(declared_permissions=["compose"]))
    assert reg.check_permission(m, "compose")
    assert not reg.check_permission(m, "network")
    # Credentials are never granted by default (PRD 34).
    assert not reg.can_access_credentials(m)
    with pytest.raises(PluginError):
        reg.require_permission(m, "network")


def test_credentials_permission_when_declared(store):
    reg = PluginRegistry(store)
    m = reg.load(_manifest(id="acme.creds", declared_permissions=["credentials"]))
    assert reg.can_access_credentials(m)


def test_safe_mode_disables_third_party(store):
    reg = PluginRegistry(store, safe_mode=True)
    third = reg.load(_manifest(id="third.party", first_party=False))
    first = reg.load(_manifest(id="bundled.tool", first_party=True))
    assert not reg.is_enabled(third)
    assert reg.is_enabled(first)


def test_safe_call_isolates_crashing_plugin(store):
    reg = PluginRegistry(store)
    m = reg.load(_manifest())

    def boom():
        raise RuntimeError("plugin exploded")

    ok, result = reg.safe_call(m, boom)
    assert ok is False
    assert result is None
    assert reg.is_degraded(m)
    assert not reg.is_enabled(m)
    # A healthy call still returns its value.
    ok2, result2 = reg.safe_call(m, lambda: 42)
    assert ok2 and result2 == 42


def test_persistence_across_registries(store):
    reg = PluginRegistry(store)
    m = reg.load(_manifest())
    assert reg.is_enabled(m)
    reg.disable(m)
    # A fresh registry backed by the same store must remember the choice.
    reg2 = PluginRegistry(store)
    reg2.load(_manifest())
    assert not reg2.is_enabled(m.id)


def test_recover_re_enables(store):
    reg = PluginRegistry(store)
    m = reg.load(_manifest())
    reg.safe_call(m, lambda: (_ for _ in ()).throw(ValueError("x")))
    assert reg.is_degraded(m)
    reg.recover(m)
    assert reg.is_enabled(m)
    assert not reg.is_degraded(m)
