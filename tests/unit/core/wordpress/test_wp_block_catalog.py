# ruff: noqa: E501 -- fixtures are exact WordPress markup, kept whole.
"""Insert Block's list, forms and markup (wordpress.md 8.2)."""

from __future__ import annotations

import pytest

from quill.core.wordpress import block_catalog as bc
from quill.core.wordpress.blocks import parse, serialize
from quill.core.wordpress.fences import blocks_to_markdown, convert_markdown

TYPES = [
    {"name": "core/paragraph", "title": "Absatz", "description": "Text.", "is_dynamic": False},
    {"name": "core/latest-posts", "title": "Latest Posts", "is_dynamic": True,
     "attributes": {"postsToShow": {"type": "number", "default": 5},
                    "displayPostDate": {"type": "boolean", "default": False},
                    "order": {"type": "string", "enum": ["asc", "desc"], "default": "desc"},
                    "className": {"type": "string"},
                    "content": {"type": "string", "source": "html"}}},
    {"name": "core/gallery", "title": "Gallery", "is_dynamic": False},
    {"name": "core/comment-author-name", "title": "Comment Author", "is_dynamic": True,
     "ancestor": ["core/comment-template"]},
    {"name": "acme/hidden", "title": "Hidden", "is_dynamic": True,
     "supports": {"inserter": False}},
    {"name": "acme/events", "title": "Events", "is_dynamic": True, "attributes": {}},
]  # fmt: skip
PATTERNS = [
    {"name": "radio/staff", "title": "Staff profile", "content": "<!-- wp:paragraph -->\n<p>Name</p>\n<!-- /wp:paragraph -->"},
    {"name": "radio/none", "title": "Empty", "content": ""},
]  # fmt: skip
SYNCED = [
    {"id": 12, "title": {"raw": "Footer note"}, "content": {"raw": "<p>x</p>"}},
    {"id": 13, "title": {"raw": "Banner"}, "content": {"raw": "<!-- wp:separator -->\n<hr class=\"wp-block-separator has-alpha-channel-opacity\"/>\n<!-- /wp:separator -->"},
     "wp_pattern_sync_status": "unsynced"},
]  # fmt: skip


def test_core_blocks_come_first_and_use_the_sites_words() -> None:
    choices = bc.build_choices(TYPES, PATTERNS, SYNCED)
    assert choices[0].title == "Absatz"
    assert [c.name for c in choices[: len(bc.CORE_CHOICES)]] == [c.name for c in bc.CORE_CHOICES]
    rest = choices[len(bc.CORE_CHOICES) :]
    assert [c.title for c in rest] == [
        "Events",
        "Latest Posts",
        "Banner",
        "Staff profile",
        "Footer note",
    ]
    assert rest[2].row() == "Banner, pattern"
    assert rest[4].row() == "Footer note, synced pattern"


def test_nothing_from_the_site_still_offers_the_core_blocks() -> None:
    assert [c.name for c in bc.build_choices(None, None, None)] == [c.name for c in bc.CORE_CHOICES]


def test_filter_finds_by_the_start_of_a_word() -> None:
    choices = bc.build_choices(TYPES, PATTERNS, SYNCED)
    assert [c.title for c in bc.filter_choices(choices, "but")] == ["Buttons"]
    assert [c.title for c in bc.filter_choices(choices, "staff")] == ["Staff profile"]
    assert len(bc.filter_choices(choices, "")) == len(choices)


def test_access_keys_never_repeat() -> None:
    labels = bc.assign_access_keys(["&Text:", "&Title:", "Tea", "T", "&Alt text:"])
    letters = [lab[lab.index("&") + 1].lower() for lab in labels if "&" in lab]
    assert len(letters) == len(set(letters))
    assert labels[0] == "&Text:"
    assert labels[3] == "T"


def test_generated_form_comes_from_the_attribute_schema() -> None:
    latest = next(c for c in bc.build_choices(TYPES, [], []) if c.name == "core/latest-posts")
    fields = bc.fields_for(latest)
    assert [f.key for f in fields] == ["postsToShow", "displayPostDate", "order"]
    assert [f.kind for f in fields] == ["text", "check", "choice"]
    markup = bc.build_markup(
        latest, {"postsToShow": "3", "displayPostDate": False, "order": "desc"}
    )
    assert markup == '<!-- wp:latest-posts {"postsToShow":3} /-->'


def test_synced_and_pattern_markup() -> None:
    choices = bc.build_choices([], PATTERNS, SYNCED)
    synced = next(c for c in choices if c.kind == "synced")
    assert bc.build_markup(synced) == '<!-- wp:block {"ref":12} /-->'
    staff = next(c for c in choices if c.title == "Staff profile")
    assert bc.build_markup(staff) == PATTERNS[0]["content"]


CORE_ANSWERS = {
    "core/paragraph": {"text": "Hello **there**"},
    "core/heading": {"text": "Times", "level": 3},
    "core/list": {"items": "tea\ncake", "ordered": True},
    "core/image": {"src": "https://example.org/a.jpg", "alt": "A cat"},
    "core/buttons": {"text": "Book", "url": "https://example.org/book", "new_tab": False},
    "core/quote": {"text": "Words", "cite": "Someone"},
    "core/columns": {"count": 3},
    "core/group": {},
    "core/details": {"summary": "Cost?", "text": "Free."},
    "core/table": {"header": "Day, Show", "rows": "1"},
    "core/embed": {"url": "https://example.org/video"},
    "core/separator": {},
    "core/spacer": {"height": "50px"},
    "core/code": {"text": "print('<hi>')"},
    "core/preformatted": {"text": "a  <b>"},
}


@pytest.mark.parametrize("name", sorted(CORE_ANSWERS))
def test_core_blocks_written_in_markdown_come_back_identical(name: str) -> None:
    """A block QUILL builds is one the fence writer can say in Markdown exactly."""
    choice = next(c for c in bc.CORE_CHOICES if c.name == name)
    markup = bc.build_markup(choice, CORE_ANSWERS[name])
    blocks = parse(markup)
    assert serialize(blocks) == markup
    assert [b.name for b in blocks] == [name]
    markdown, islands = blocks_to_markdown(blocks)
    assert islands == {}, markdown
    assert convert_markdown(markdown).html == markup


def test_button_in_a_new_tab_is_written_the_block_editors_way() -> None:
    choice = next(c for c in bc.CORE_CHOICES if c.name == "core/buttons")
    markup = bc.build_markup(choice, {"text": "Map", "url": "https://x.example", "new_tab": True})
    assert '<!-- wp:button {"linkTarget":"_blank","rel":"noreferrer noopener"} -->' in markup
    assert 'href="https://x.example" target="_blank" rel="noreferrer noopener">Map</a>' in markup


def test_cover_has_its_picture_and_words() -> None:
    choice = next(c for c in bc.CORE_CHOICES if c.name == "core/cover")
    markup = bc.build_markup(choice, {"src": "https://x.example/a.jpg", "text": "On air"})
    assert markup.startswith('<!-- wp:cover {"url":"https://x.example/a.jpg","dimRatio":50,')
    assert 'class="wp-block-cover__image-background" alt="" src="https://x.example/a.jpg"' in markup
    assert "On air</p>" in markup
    assert serialize(parse(markup)) == markup


def test_every_core_choice_has_a_form_or_needs_none() -> None:
    for choice in bc.CORE_CHOICES:
        fields = bc.fields_for(choice)
        keys = [f.key for f in fields]
        assert len(keys) == len(set(keys))
        assert bc.build_markup(choice, {f.key: f.value for f in fields}).startswith("<!-- wp:")
