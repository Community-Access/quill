"""Unit tests for quill.core.spelling.context_builder."""

from quill.core.spelling.context_builder import build_context


def test_word_selected_in_context():
    text = "The cat sat. I like teh dog. He ran away."
    ws, we = text.index("teh"), text.index("teh") + 3
    ctx, cws, cwe = build_context(text, ws, we)
    assert ctx[cws:cwe] == "teh"


def test_context_contains_word():
    text = "Hello world. This is a bligtest sentence. End here."
    ws = text.index("bligtest")
    we = ws + len("bligtest")
    ctx, cws, cwe = build_context(text, ws, we)
    assert "bligtest" in ctx
    assert ctx[cws:cwe] == "bligtest"


def test_short_document():
    text = "bligtest"
    ctx, cws, cwe = build_context(text, 0, 8)
    assert ctx[cws:cwe] == "bligtest"


def test_empty_text():
    ctx, cws, cwe = build_context("", 0, 0)
    assert ctx == ""


def test_offsets_valid():
    text = "First sentence. Second sentense here. Third sentence."
    ws = text.index("sentense")
    we = ws + len("sentense")
    ctx, cws, cwe = build_context(text, ws, we)
    assert 0 <= cws <= cwe <= len(ctx)


def test_max_chars_respected():
    long_text = ("x " * 600) + "bligtest " + ("y " * 600)
    ws = long_text.index("bligtest")
    we = ws + len("bligtest")
    ctx, cws, cwe = build_context(long_text, ws, we, max_chars=200)
    assert len(ctx) <= 200
    assert ctx[cws:cwe] == "bligtest"


def test_word_at_start():
    text = "Bligtest is here. More text."
    ctx, cws, cwe = build_context(text, 0, 8)
    assert ctx[cws:cwe] == "Bligtest"


def test_word_at_end():
    text = "Start here. End with bligtest"
    ws = text.index("bligtest")
    we = ws + len("bligtest")
    ctx, cws, cwe = build_context(text, ws, we)
    assert ctx[cws:cwe] == "bligtest"
