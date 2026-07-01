from __future__ import annotations

from quill.core.vault.links import parse_links


def test_simple_link() -> None:
    (link,) = parse_links("See [[My Note]] here.")
    assert link.target == "My Note"
    assert link.heading is None and link.block is None and link.alias is None
    assert link.embed is False
    assert link.start == 4 and link.end == len("See [[My Note]]")


def test_alias_link() -> None:
    (link,) = parse_links("[[Target Note|shown text]]")
    assert link.target == "Target Note"
    assert link.alias == "shown text"


def test_heading_link() -> None:
    (link,) = parse_links("[[Note#Chapter One]]")
    assert link.target == "Note"
    assert link.heading == "Chapter One"
    assert link.block is None


def test_block_reference_link() -> None:
    (link,) = parse_links("[[Note#^abc123]]")
    assert link.target == "Note"
    assert link.block == "abc123"
    assert link.heading is None


def test_same_note_heading_link_has_empty_target() -> None:
    (link,) = parse_links("[[#Section]]")
    assert link.target == ""
    assert link.heading == "Section"


def test_embed_link() -> None:
    (link,) = parse_links("![[Diagram]]")
    assert link.embed is True
    assert link.target == "Diagram"


def test_multiple_links_in_order() -> None:
    links = parse_links("[[A]] and [[B|bee]] and ![[C#Top]]")
    assert [link.target for link in links] == ["A", "B", "C"]
    assert links[1].alias == "bee"
    assert links[2].embed is True and links[2].heading == "Top"


def test_markdown_link_is_not_a_wikilink() -> None:
    assert parse_links("[label](https://example.com)") == []


def test_links_inside_inline_code_are_ignored() -> None:
    links = parse_links("`[[Not A Link]]` but [[Real]] counts")
    assert [link.target for link in links] == ["Real"]
    # The kept link's span points at the real occurrence, not the code one.
    text = "`[[Not A Link]]` but [[Real]] counts"
    assert text[links[0].start : links[0].end] == "[[Real]]"


def test_links_inside_fenced_code_are_ignored() -> None:
    text = "```\n[[Ignored]]\n```\n[[Kept]]\n"
    assert [link.target for link in parse_links(text)] == ["Kept"]


def test_alias_and_heading_together() -> None:
    (link,) = parse_links("[[Note#Heading|Display]]")
    assert link.target == "Note"
    assert link.heading == "Heading"
    assert link.alias == "Display"


def test_link_at_offset_inside_the_link() -> None:
    from quill.core.vault.links import link_at_offset

    text = "See [[My Note]] here"
    link = link_at_offset(text, 8)
    assert link is not None and link.target == "My Note"


def test_link_at_offset_none_when_outside() -> None:
    from quill.core.vault.links import link_at_offset

    assert link_at_offset("See [[X]] here", 1) is None
    assert link_at_offset("See [[X]] here", 12) is None


def test_link_at_offset_at_the_brackets() -> None:
    from quill.core.vault.links import link_at_offset

    assert link_at_offset("[[X]]", 0) is not None
    assert link_at_offset("[[X]]", 5) is not None
