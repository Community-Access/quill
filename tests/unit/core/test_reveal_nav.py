from __future__ import annotations

from quill.core.reveal_codes import build_code_stream
from quill.core.reveal_nav import (
    announce_cell,
    announce_line,
    build_flow_view,
    cell_for_markup_offset,
    enclosing_region,
    line_end,
    line_home,
    move_char,
    move_line,
    move_word,
    region_source,
    splice_region,
    word_at,
)


def _view(markup: str):
    return build_flow_view(build_code_stream(markup))


def test_text_run_becomes_one_cell_per_character() -> None:
    view = _view("Hi")
    assert view.text == "Hi"
    assert [c.char for c in view.cells] == ["H", "i"]
    assert [c.is_code for c in view.cells] == [False, False]
    # Cells map straight onto flow offsets and the editor buffer.
    assert [c.flow_start for c in view.cells] == [0, 1]
    assert [c.markup_offset for c in view.cells] == [0, 1]


def test_code_is_a_single_atomic_cell() -> None:
    view = _view("**Hi** x")
    # Bold On | H | i | Bold Off | (space) | x
    kinds = [(c.is_code, c.char) for c in view.cells]
    assert kinds[0] == (True, None)  # [Bold On]
    assert kinds[1:3] == [(False, "H"), (False, "i")]
    assert kinds[3] == (True, None)  # [Bold Off]
    # One Right off the On code lands on the first character, not inside "[Bold On]".
    assert move_char(view.cells, 0, +1) == 1


def test_left_right_step_over_a_code_atomically() -> None:
    view = _view("a**b**c")
    # a | Bold On | b | Bold Off | c
    assert [c.label for c in view.cells] == ["a", "[Bold On]", "b", "[Bold Off]", "c"]
    idx = 0
    idx = move_char(view.cells, idx, +1)  # -> Bold On
    assert view.cells[idx].is_code
    idx = move_char(view.cells, idx, +1)  # -> b
    assert view.cells[idx].char == "b"


def test_char_announcement_speaks_letter_or_code_phrase() -> None:
    view = _view("**Hi**")
    tokens = build_code_stream("**Hi**")
    assert announce_cell(tokens, view.cells, 1) == "H"  # the character
    assert "bold on" in announce_cell(tokens, view.cells, 0)  # the code phrase


def test_space_is_spoken_by_name() -> None:
    view = _view("a b")
    space = next(c for c in view.cells if c.char == " ")
    assert space.spoken == "space"


def test_word_motion_lands_on_word_starts_and_stops_at_codes() -> None:
    view = _view("one two")
    # "one two" -> start on 'o', Ctrl+Right lands on 't' of "two".
    idx = move_word(view.cells, 0, +1)
    assert view.cells[idx].char == "t"
    assert word_at(view.cells, idx) == "two"
    # Backward from inside "two" returns to its start.
    back = move_word(view.cells, idx + 1, -1)
    assert view.cells[back].char == "t"


def test_down_arrow_moves_by_logical_line() -> None:
    view = _view("first\n\nsecond")
    assert view.line_count >= 2
    first_cell = 0
    assert view.cells[first_cell].char == "f"
    down = move_line(view.cells, first_cell, +1)
    # We moved to a later line, and reading it announces the next line's text.
    assert view.cells[down].line > view.cells[first_cell].line
    assert (
        "second" in announce_line(view.cells, down)
        or announce_line(view.cells, down) == "blank line"
    )


def test_line_home_and_end() -> None:
    view = _view("hello")
    assert line_home(view.cells, 3) == 0
    assert line_end(view.cells, 0) == len(view.cells) - 1


def test_cell_for_markup_offset_round_trips() -> None:
    markup = "**Hello** world"
    view = _view(markup)
    # An offset inside the bolded word maps to one of its character cells.
    idx = cell_for_markup_offset(view.cells, 4)
    assert view.cells[idx].char in set("Hello")


def test_enclosing_region_finds_the_bounding_pair() -> None:
    markup = "**Hello** world"
    tokens = build_code_stream(markup)
    text_ti = next(i for i, t in enumerate(tokens) if t.label == "Hello")
    region = enclosing_region(tokens, text_ti)
    assert region is not None
    assert region.on_label == "Bold"
    assert region_source(markup, region) == "Hello"


def test_region_spans_a_whole_bold_run_with_a_tab() -> None:
    # F2 anywhere inside the bold run edits the whole span, tab included.
    markup = "**Hello\tworld**"
    tokens = build_code_stream(markup)
    tab_ti = next(i for i, t in enumerate(tokens) if t.label == "Tab")
    region = enclosing_region(tokens, tab_ti)
    assert region is not None
    assert region_source(markup, region) == "Hello\tworld"
    assert splice_region(markup, region, "Hi\tthere") == "**Hi\tthere**"


def test_region_targets_innermost_pair_for_nested_codes() -> None:
    # Caret on the inner italic text edits only the italic region, not the bold.
    markup = "**a *b* c**"
    tokens = build_code_stream(markup)
    b_ti = next(i for i, t in enumerate(tokens) if t.label == "b")
    inner = enclosing_region(tokens, b_ti)
    assert inner is not None
    assert inner.on_label == "Italic"
    assert region_source(markup, inner) == "b"
    # Caret on the outer text edits the whole bold span, nested code and all.
    a_ti = next(i for i, t in enumerate(tokens) if t.label == "a ")
    outer = enclosing_region(tokens, a_ti)
    assert outer is not None
    assert outer.on_label == "Bold"
    assert region_source(markup, outer) == "a *b* c"


def test_plain_text_has_no_enclosing_region() -> None:
    tokens = build_code_stream("just words")
    text_ti = next(i for i, t in enumerate(tokens) if t.label == "just words")
    assert enclosing_region(tokens, text_ti) is None


def test_splice_region_replaces_only_the_run() -> None:
    markup = "**Hello** world"
    tokens = build_code_stream(markup)
    text_ti = next(i for i, t in enumerate(tokens) if t.label == "Hello")
    region = enclosing_region(tokens, text_ti)
    assert region is not None
    assert splice_region(markup, region, "Goodbye") == "**Goodbye** world"


def test_caret_on_a_code_has_no_editable_region() -> None:
    tokens = build_code_stream("**Hello**")
    on_ti = next(i for i, t in enumerate(tokens) if t.label == "Bold On")
    assert enclosing_region(tokens, on_ti) is None


def test_movers_never_raise_on_empty() -> None:
    view = _view("")
    assert view.cells == ()
    assert move_char(view.cells, 0, +1) == 0
    assert move_word(view.cells, 0, -1) == 0
    assert move_line(view.cells, 0, +1) == 0
    assert announce_cell([], view.cells, 0) == ""
