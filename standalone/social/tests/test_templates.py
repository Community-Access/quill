"""Tests for saved replies and templates (PRD 13.5)."""

from quill_social.services import templates as tpl


def test_variable_substitution():
    t = tpl.Template(body="Hi {name}, thanks!", variables=["name"])
    assert tpl.render(t, {"name": "Ada"}) == "Hi Ada, thanks!"


def test_unknown_placeholder_left_flagged():
    t = tpl.Template(body="Hi {name}, from {who}", variables=["name", "who"])
    out = tpl.render(t, {"name": "Ada"})
    assert out == "Hi Ada, from {who}"


def test_missing_variables():
    t = tpl.Template(body="Hi {name} re {topic}", variables=["name", "topic"])
    assert tpl.missing_variables(t, {"name": "Ada"}) == ["topic"]
    assert tpl.missing_variables(t, {"name": "Ada", "topic": "x"}) == []


def test_network_variant_selected():
    t = tpl.Template(
        body="Long default body {name}",
        network_variants={"bluesky": "Short {name}"},
        variables=["name"],
    )
    assert tpl.render(t, {"name": "Ada"}, network="bluesky") == "Short Ada"
    assert tpl.render(t, {"name": "Ada"}, network="mastodon") == "Long default body Ada"


def test_signature_appended():
    t = tpl.Template(body="Hello", signature="- Ada")
    assert tpl.render(t, {}) == "Hello\n\n- Ada"


def test_no_signature_no_trailer():
    t = tpl.Template(body="Hello")
    assert tpl.render(t, {}) == "Hello"


def test_library_roundtrip(store):
    lib = tpl.TemplateLibrary(store)
    t = tpl.Template(
        name="thanks",
        body="Thanks {name}",
        variables=["name"],
        campaign_tags=["launch"],
        accessibility_reminder="Add alt text",
    )
    lib.add(t)
    got = lib.get(t.template_id)
    assert got is not None
    assert got.body == "Thanks {name}"
    assert got.campaign_tags == ["launch"]
    assert got.accessibility_reminder == "Add alt text"
    assert len(lib.list()) == 1
    lib.delete(t.template_id)
    assert lib.get(t.template_id) is None
    assert lib.list() == []
