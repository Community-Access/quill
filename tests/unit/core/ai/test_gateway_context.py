"""What gets sent, and what never does.

Every test here is about one of two promises the feature makes to somebody who
cannot see the screen: that QUILL Lite sends what they meant, and that it never
quietly sends their whole document.
"""

from __future__ import annotations

import pytest

from quill.core.ai import gateway_context as ctx

DOC = """# Background

The committee first met in March. Attendance was poor.

# Method

Three sites were sampled weekly. The sampling used a standard grid.

# Results

Yields rose by eleven percent. The increase held across all three sites.
"""


# --- What the command acts on -------------------------------------------------


def test_a_selection_wins_over_everything_else():
    scope, text = ctx.resolve_scope(DOC, "Attendance was poor.", 40)
    assert scope == ctx.SCOPE_SELECTION
    assert text == "Attendance was poor."


def test_with_no_selection_it_uses_the_paragraph_not_the_document():
    """The whole point. A summary of an entire file is rarely what somebody
    pressing Summarize on a paragraph wanted, and it is the expensive answer as
    well as the wrong one."""
    position = DOC.index("Three sites")
    scope, text = ctx.resolve_scope(DOC, "", position)
    assert scope == ctx.SCOPE_PARAGRAPH
    assert "Three sites were sampled" in text
    assert "committee" not in text
    assert len(text) < len(DOC) / 2


def test_a_section_is_offered_when_the_document_has_headings():
    position = DOC.index("Three sites")
    assert ctx.SCOPE_SECTION in ctx.scopes_available(DOC, "", position)

    _scope, text = ctx.resolve_scope(DOC, "", position, ctx.SCOPE_SECTION)
    assert text.startswith("# Method")
    assert "Three sites" in text
    # It stops at the next heading rather than running to the end of the file.
    assert "Yields rose" not in text


def test_a_document_with_no_headings_does_not_offer_a_section():
    """Which is what stops the pad showing a chooser with a dead option in it."""
    plain = "One paragraph.\n\nAnother paragraph."
    assert ctx.SCOPE_SECTION not in ctx.scopes_available(plain, "", 5)


def test_a_single_option_is_still_reported_so_the_chooser_can_be_hidden():
    plain = "Just the one paragraph here."
    assert ctx.scopes_available(plain, "", 3) == [ctx.SCOPE_PARAGRAPH]


def test_an_empty_document_resolves_to_nothing_rather_than_raising():
    assert ctx.resolve_scope("", "", 0) == ("", "")


def test_a_stale_scope_falls_back_instead_of_sending_nothing():
    """The chooser can name a scope that has since become empty -- the caret
    moved while the pad was open. Falling back is right; sending an empty
    request and spending an allowance on it is not."""
    plain = "One paragraph, no headings."
    scope, text = ctx.resolve_scope(plain, "", 3, ctx.SCOPE_SECTION)
    assert scope == ctx.SCOPE_PARAGRAPH
    assert text


# --- Finding the parts that answer a question ---------------------------------


def test_it_finds_the_section_that_answers_the_question():
    picked = ctx.pick_excerpts(DOC, "how much did yields rise?", limit=1).excerpts
    assert len(picked) == 1
    assert "eleven percent" in picked[0].text


def test_excerpts_carry_the_heading_they_came_from():
    """Not decoration. It is the only way somebody can tell "the AI got it
    wrong" apart from "it never saw the right paragraph", and that decides
    whether they rephrase or give up on the feature."""
    picked = ctx.pick_excerpts(DOC, "how were the sites sampled?", limit=1).excerpts
    assert picked[0].heading == "Method"


def test_it_never_returns_more_than_asked_for():
    """Three is the server's limit, checked there independently of the size
    limit so many small excerpts cannot be used to get around it."""
    assert len(ctx.pick_excerpts(DOC, "sites sampling yields committee", limit=3).excerpts) <= 3
    assert len(ctx.pick_excerpts(DOC, "sites", limit=1).excerpts) == 1


def test_a_question_of_only_common_words_still_sends_something_sensible():
    """ "What is it" has nothing left after stop-words. The top of the document
    is a better guess than nothing, and the pad shows what was chosen before
    anything is sent."""
    picked = ctx.pick_excerpts(DOC, "what is it", limit=2).excerpts
    assert picked
    assert picked[0].text.startswith("# Background")


def test_a_word_that_is_everywhere_does_not_decide_the_answer():
    """A term appearing in every passage is evidence about none of them."""
    doc = (
        "# One\n\nThe report mentions apples.\n\n"
        "# Two\n\nThe report mentions oranges.\n\n"
        "# Three\n\nThe report mentions pears.\n"
    )
    picked = ctx.pick_excerpts(doc, "what does the report say about oranges?", limit=1).excerpts
    assert "oranges" in picked[0].text


def test_an_empty_document_yields_no_excerpts():
    assert ctx.pick_excerpts("", "anything").excerpts == []


def test_chunking_keeps_all_the_text():
    """Nothing is silently dropped on the way in."""
    chunks = ctx.chunk_document(DOC)
    joined = " ".join(c.text for c in chunks)
    for phrase in ("committee first met", "sampled weekly", "eleven percent"):
        assert phrase in joined


# --- Refusing too much, before it costs anything ------------------------------


def test_a_passage_within_the_limit_is_allowed():
    oversized, _words, _allowed = ctx.too_large("a short passage", 1500)
    assert oversized is False


def test_an_oversized_passage_is_refused_in_words_not_tokens():
    """Nobody thinks in tokens. The refusal has to quote a number somebody can
    act on -- "select less than about 1,100 words" -- not one they have to look
    up."""
    oversized, words, allowed = ctx.too_large("word " * 5000, 1500)
    assert oversized is True
    assert words == 5000
    assert 1000 <= allowed <= 1200


def test_the_token_estimate_leans_high():
    """Being conservative can only refuse a borderline passage slightly early.
    The opposite error sends something too big and wastes the round trip."""
    text = "a" * 400
    assert ctx.estimate_tokens(text) >= len(text) // 5


@pytest.mark.parametrize(
    ("tokens", "lower", "upper"),
    [(1500, 1000, 1200), (500, 300, 450), (100, 60, 90)],
)
def test_word_limits_are_rounded_to_something_speakable(tokens, lower, upper):
    words = ctx.words_for_tokens(tokens)
    assert lower <= words <= upper
    assert words % 10 == 0


def test_every_scope_has_a_label_a_person_would_read():
    for scope in (ctx.SCOPE_SELECTION, ctx.SCOPE_PARAGRAPH, ctx.SCOPE_SECTION):
        label = ctx.SCOPE_LABELS[scope]
        assert label and label[0].isupper()
        assert "scope" not in label.lower()


# --- The bound that keeps the editor responsive --------------------------------


def test_retrieval_does_not_freeze_the_editor_on_a_large_document():
    """The reason this is a stream rather than a list.

    Scoring a 1 MB document by materialising every chunk took three seconds --
    on the UI thread, on every refresh of the pad's preview, in an editor whose
    whole promise is that it never stops accepting keystrokes.
    """
    import time

    joiner = chr(10) * 2
    doc = joiner.join(
        f"# Section {i}{joiner}Some body text about topic {i} here." for i in range(20_000)
    )
    start = time.perf_counter()
    found = ctx.pick_excerpts(doc, "topic 500", limit=3)
    elapsed = time.perf_counter() - start

    assert found.excerpts
    assert elapsed < 1.5, f"retrieval took {elapsed:.2f}s on a {len(doc) // 1024} KB document"


def test_a_capped_scan_says_so_rather_than_pretending_it_looked_everywhere():
    """A silent truncation reads as "the AI could not find it" when the truth is
    "nobody looked there" -- which sends somebody rewording a question that was
    fine."""
    doc = "x " * (ctx.MAX_SCAN_CHARS)
    found = ctx.pick_excerpts(doc, "anything", limit=3)
    assert found.scanned_all is False
    assert "searched the first" in found.note()
    assert "selection instead" in found.note()


def test_an_ordinary_document_is_searched_all_the_way_through():
    """The cap must never touch a document anybody actually has open."""
    found = ctx.pick_excerpts(DOC, "yields", limit=3)
    assert found.scanned_all is True
    assert found.note() == ""
