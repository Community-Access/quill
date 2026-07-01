from __future__ import annotations

from quill.core.story.frontmatter import join_front_matter, split_front_matter


def test_split_returns_empty_fields_when_absent() -> None:
    fields, body = split_front_matter("Just prose, no front matter.\n")
    assert fields == {}
    assert body == "Just prose, no front matter.\n"


def test_split_parses_leading_yaml_block() -> None:
    text = "---\ntype: character\nrole: protagonist\n---\nElena is brave.\n"
    fields, body = split_front_matter(text)
    assert fields == {"type": "character", "role": "protagonist"}
    assert body == "Elena is brave.\n"


def test_split_preserves_unknown_keys_and_lists() -> None:
    text = "---\ntype: character\ntags:\n  - pov\n  - act-one\nmood: wistful\n---\nBody\n"
    fields, _body = split_front_matter(text)
    assert fields["tags"] == ["pov", "act-one"]
    assert fields["mood"] == "wistful"


def test_join_empty_fields_leaves_body_unchanged() -> None:
    assert join_front_matter({}, "Body text\n") == "Body text\n"


def test_join_emits_fenced_yaml_then_body() -> None:
    out = join_front_matter({"type": "character", "role": "protagonist"}, "Elena is brave.\n")
    assert out.startswith("---\n")
    assert "type: character" in out
    assert out.endswith("Elena is brave.\n")


def test_round_trip_preserves_fields_and_body() -> None:
    text = "---\ntype: plot\nstatus: unresolved\ntags:\n- a\n- b\n---\nThe betrayal unfolds.\n"
    fields, body = split_front_matter(text)
    again_fields, again_body = split_front_matter(join_front_matter(fields, body))
    assert again_fields == fields
    assert again_body == body


def test_field_order_is_preserved_on_serialize() -> None:
    out = join_front_matter({"z": "1", "a": "2", "m": "3"}, "body\n")
    assert out.index("z:") < out.index("a:") < out.index("m:")
