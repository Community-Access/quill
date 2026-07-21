"""Tests for AI understanding features that lead back to sources (PRD 21.3, 12.6)."""

from quill_social.model import SocialItem
from quill_social.services.ai import understand
from quill_social.services.ai.gateway import AIGateway, ProviderMode


def _items():
    return [
        SocialItem(
            item_id="a",
            author_display="Ada",
            text="Should we ship on Friday? We decided to go with plan B. "
            "Details at https://example.com/plan.",
        ),
        SocialItem(
            item_id="b",
            author_display="Grace",
            text="Please review the pull request. TODO: add regression tests.",
        ),
    ]


def test_summary_lists_its_sources():
    s = understand.summarize(_items())
    assert s.sources == ["a", "b"]
    assert "Ada" in s.text
    assert s.text  # non-empty


def test_summary_empty_input():
    s = understand.summarize([])
    assert s.sources == []


def test_extract_questions():
    q = understand.extract_questions(_items())
    assert any(f.text.endswith("?") for f in q)
    assert all(f.source_id == "a" for f in q)  # only item a has a question


def test_extract_actions():
    actions = understand.extract_actions(_items())
    texts = [f.text for f in actions]
    assert any("review" in t.lower() for t in texts)
    assert any("todo" in t.lower() for t in texts)
    assert all(f.source_id == "b" for f in actions)


def test_extract_decisions():
    decisions = understand.extract_decisions(_items())
    assert any("plan B" in f.text for f in decisions)
    assert all(f.source_id == "a" for f in decisions)


def test_extract_links_ties_to_source():
    links = understand.extract_links(_items())
    assert len(links) == 1
    assert links[0].text == "https://example.com/plan"
    assert links[0].source_id == "a"


def test_detect_duplicates_positive_and_clean():
    dups = understand.detect_duplicates(
        [
            SocialItem(item_id="x", text="Hello there, world"),
            SocialItem(item_id="y", text="hello   THERE, world"),
            SocialItem(item_id="z", text="Something else entirely"),
        ]
    )
    assert dups == [["x", "y"]]
    # A clean set produces no groups.
    assert understand.detect_duplicates(
        [SocialItem(item_id="1", text="alpha"), SocialItem(item_id="2", text="beta")]
    ) == []


def test_translate_is_a_documented_boundary():
    # With only the mock provider, translate honestly returns the input.
    assert understand.translate("hola", "en") == "hola"
    # A disabled gateway also returns the input rather than raising.
    gw = AIGateway(mode=ProviderMode.disabled)
    assert understand.translate("hola", "en", gateway=gw) == "hola"
