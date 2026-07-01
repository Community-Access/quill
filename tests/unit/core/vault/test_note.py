from __future__ import annotations

from quill.core.vault.note import parse_note


def test_title_prefers_front_matter() -> None:
    info = parse_note("---\ntitle: Real Title\n---\n# Heading\nBody", "file")
    assert info.title == "Real Title"


def test_title_falls_back_to_h1_then_stem() -> None:
    assert parse_note("# The Heading\n\nBody", "myfile").title == "The Heading"
    assert parse_note("just body, no heading", "myfile").title == "myfile"


def test_aliases_from_front_matter_list() -> None:
    info = parse_note("---\naliases:\n- AKA\n- Nickname\n---\nBody", "f")
    assert info.aliases == ("AKA", "Nickname")


def test_aliases_single_string() -> None:
    info = parse_note("---\naliases: OnlyOne\n---\nBody", "f")
    assert info.aliases == ("OnlyOne",)


def test_tags_from_front_matter_and_inline() -> None:
    info = parse_note("---\ntags:\n- fromfm\n---\nBody with #inline and #nested/tag", "f")
    assert "fromfm" in info.tags
    assert "inline" in info.tags
    assert "nested/tag" in info.tags


def test_headings_carry_level_title_offset() -> None:
    info = parse_note("# One\n\n## Two\n", "f")
    assert [(h.level, h.title) for h in info.headings] == [(1, "One"), (2, "Two")]


def test_block_ids_indexed() -> None:
    info = parse_note("A paragraph. ^para1\n\nAnother line ^b2\n", "f")
    assert set(info.block_ids) == {"para1", "b2"}


def test_links_collected_in_order() -> None:
    info = parse_note("See [[Other]] and [[Third|3]]", "f")
    assert [link.target for link in info.links] == ["Other", "Third"]


def test_atx_heading_text_is_not_a_tag() -> None:
    info = parse_note("# Heading Not A Tag\n\n#realtag", "f")
    assert "realtag" in info.tags
    assert "Heading" not in info.tags


def test_tags_are_deduped_and_ordered() -> None:
    info = parse_note("#a #b #a", "f")
    assert info.tags == ("a", "b")
