"""Tests for the capability registry (PRD 6.3, 11.4)."""

from quill_social.capabilities import (
    Capabilities,
    CapabilityRegistry,
    default_for,
)


def test_network_defaults_differ():
    m = default_for("mastodon")
    b = default_for("bluesky")
    assert m.char_limit == 500
    assert b.char_limit == 300
    assert m.supports_polls and not b.supports_polls
    assert b.supports_quote  # bluesky quotes; conservative mastodon default off
    assert m.supports_native_scheduling and not b.supports_native_scheduling


def test_bluesky_visibility_restricted():
    b = default_for("bluesky")
    assert b.allows_visibility("public")
    assert not b.allows_visibility("followers")


def test_merge_is_immutable_copy():
    base = default_for("mastodon")
    refined = base.merge(char_limit=5000)
    assert base.char_limit == 500
    assert refined.char_limit == 5000


def test_merge_ignores_unknown_fields():
    base = default_for("mock")
    refined = base.merge(not_a_field=123, char_limit=99)
    assert refined.char_limit == 99


def test_registry_seed_and_get():
    reg = CapabilityRegistry()
    reg.seed_from_network("acct1", "bluesky")
    assert reg.get("acct1").char_limit == 300
    # unknown account falls back to network default
    assert reg.get("acct2", "mastodon").char_limit == 500


def test_registry_refine():
    reg = CapabilityRegistry()
    reg.seed_from_network("acct1", "mastodon")
    reg.refine("acct1", char_limit=11000)
    assert reg.get("acct1").char_limit == 11000


def test_capabilities_dict_roundtrip():
    c = default_for("bluesky")
    back = Capabilities.from_dict(c.to_dict())
    assert back == c
