from __future__ import annotations

from quill.core.reveal_codes import (
    CodeToken,
    TokenKind,
    build_code_stream,
    describe_token,
    pair_distance,
    token_at_markup_offset,
)


def _labels(tokens: list[CodeToken]) -> list[str]:
    return [t.label for t in tokens]


def test_plain_text_is_a_single_text_run() -> None:
    tokens = build_code_stream("Plain text only")
    assert len(tokens) == 1
    assert tokens[0].kind is TokenKind.TEXT
    assert tokens[0].label == "Plain text only"
    assert tokens[0].markup_start == 0
    assert tokens[0].visible_end == len("Plain text only")


def test_empty_markup_yields_no_tokens() -> None:
    assert build_code_stream("") == []


def test_bold_span_pairs_on_and_off() -> None:
    tokens = build_code_stream("**Hello** world")
    kinds = [t.kind for t in tokens]
    assert kinds == [
        TokenKind.FORMAT_ON,
        TokenKind.TEXT,
        TokenKind.FORMAT_OFF,
        TokenKind.TEXT,
    ]
    on, _, off, _ = tokens
    assert on.label == "Bold On" and off.label == "Bold Off"
    # The pair links both ways.
    assert on.pair_index == 2
    assert off.pair_index == 0
    # Reach is the visible length of the bolded text ("Hello").
    assert pair_distance(tokens, 0) == 5


def test_heading_becomes_a_block_code() -> None:
    tokens = build_code_stream("# Title")
    assert tokens[0].kind is TokenKind.BLOCK
    assert tokens[0].label == "Heading 1"
    assert tokens[1].kind is TokenKind.TEXT
    assert tokens[1].label == "Title"


def test_paragraph_break_emits_hard_returns() -> None:
    tokens = build_code_stream("a\n\nb")
    structures = [t for t in tokens if t.kind is TokenKind.STRUCTURE]
    # A blank line between the two paragraphs is two line breaks.
    assert [t.label for t in structures] == ["¶ Hard Return", "¶ Hard Return"]


def test_tab_is_a_structure_token() -> None:
    tokens = build_code_stream("a\tb")
    tab = [t for t in tokens if t.label == "Tab"]
    assert len(tab) == 1
    assert tab[0].kind is TokenKind.STRUCTURE
    assert tab[0].markup_end == tab[0].markup_start + 1


def test_invisible_no_break_space_token() -> None:
    tokens = build_code_stream("a b")
    nbsp = [t for t in tokens if t.kind is TokenKind.INVISIBLE]
    assert nbsp and nbsp[0].label == "No-Break Space"


def test_valued_inline_code_font() -> None:
    tokens = build_code_stream('[hi]{font-family="Arial"}')
    on = next(t for t in tokens if t.kind is TokenKind.FORMAT_ON)
    assert on.label == "Font: Arial On"
    assert on.spoken == "font Arial on"
    assert on.attrs.get("font_family") == "Arial"


def test_token_at_markup_offset_tracks_position() -> None:
    tokens = build_code_stream("**Hello** world")
    # Offset inside the bolded text lands on the text run, not the codes.
    idx = token_at_markup_offset(tokens, 4)
    assert tokens[idx].kind is TokenKind.TEXT
    assert tokens[idx].label == "Hello"


def test_describe_token_verbosity() -> None:
    tokens = build_code_stream("**Hi** there")
    on_index = next(i for i, t in enumerate(tokens) if t.kind is TokenKind.FORMAT_ON)
    assert describe_token(tokens, on_index, "quiet") == "bold on"
    # Balanced adds the reach.
    assert "character" in describe_token(tokens, on_index, "balanced")


def test_markup_offsets_are_consistent_for_sync() -> None:
    md = "**Hello** world"
    tokens = build_code_stream(md)
    # Every markup offset is within the buffer and non-decreasing across the stream.
    last = -1
    for token in tokens:
        assert 0 <= token.markup_start <= len(md)
        assert token.markup_start >= last
        last = token.markup_start
