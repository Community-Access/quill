"""The shared filter's query syntax (quill/core/list_search.py) and every list it reaches."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.file_search import search_files, uses_file_pattern_query
from quill.core.list_search import (
    QueryTerm,
    SearchTerms,
    has_query_syntax,
    matches_search,
    parse_query,
)
from quill.core.tagging import search_html_tag_choices, search_markdown_tag_choices


def _found(query: str, row: str) -> bool:
    return matches_search(query, [row])


# -- what counts as a query ------------------------------------------------


@pytest.mark.parametrize("query", ["a*", "a?", "a & b", "a | b", "!a", '"a b"'])
def test_any_syntax_character_makes_a_query(query: str) -> None:
    assert has_query_syntax(query)


@pytest.mark.parametrize("query", ["", "meeting notes", "re: invoice", ";sig", "c++ (draft)"])
def test_plain_text_is_not_a_query(query: str) -> None:
    assert not has_query_syntax(query)
    assert SearchTerms(query).query is None


def test_plain_searches_are_unchanged() -> None:
    # The whole text anywhere, or every word in any order -- as before.
    assert _found("notes meeting", "Notes from the meeting")
    assert _found("meeting notes", "Meeting notes for Tuesday")
    assert not _found("meetings", "Meeting")


# -- terms -----------------------------------------------------------------


def test_words_match_anywhere_and_ignore_case() -> None:
    assert _found("MEET & tues", "Meeting notes for Tuesday")


def test_star_is_any_run_of_letters_within_a_word() -> None:
    assert _found("c*t", "a cart")
    assert _found("c*t", "cat")
    assert not _found("c*t", "cool hat")  # never crosses a space
    assert _found("*", "anything")


def test_question_mark_is_exactly_one_letter() -> None:
    assert _found("c?t", "cut")
    assert not _found("c?t", "cart")
    assert not _found("c?t", "c t")


def test_quotes_match_exact_text_with_operators_taken_literally() -> None:
    assert _found('"meeting notes"', "Meeting notes for Tuesday")
    assert not _found('"meeting notes"', "Notes from the meeting")
    assert _found('"a | b"', "choose a | b here")
    assert not _found('"a | b"', "a or b")
    assert _found('"c*t"', "c*t literally")
    assert not _found('"c*t"', "cart")


def test_an_unclosed_quote_runs_to_the_end() -> None:
    assert parse_query('"to do') == parse_query('"to do"')
    assert _found('"to do', "a to do list")


# -- operators and precedence ----------------------------------------------


def test_and_or_not() -> None:
    row = "Bread rolls, level 2"
    assert _found("bread & rolls", row)
    assert _found("bread rolls !cake", row)
    assert not _found("bread & cake", row)
    assert _found("cake | rolls", row)
    assert not _found("cake | pie", row)
    assert _found("!cake", row)
    assert not _found("!bread", row)


def test_adjacent_words_mean_and() -> None:
    assert parse_query("a b") == parse_query("a & b")


def test_not_binds_tighter_than_and_which_binds_tighter_than_or() -> None:
    # draft | notes !old  ==  draft | (notes & (!old))
    tree = parse_query("draft | notes !old")
    assert tree is not None and tree.kind == "any"
    left, right = tree.children
    assert left.term == QueryTerm("draft")
    assert right.kind == "all"
    assert right.children[1].kind == "not"
    assert _found("draft | notes !old", "old draft")
    assert _found("draft | notes !old", "new notes")
    assert not _found("draft | notes !old", "old notes")


def test_double_not_and_operators_without_spaces() -> None:
    assert _found("!!bread", "bread")
    assert _found("bread&rolls", "rolls of bread")
    assert _found("cake|bread", "bread")


@pytest.mark.parametrize("query", ["!", "&", "|", "& |", '""', "!|&"])
def test_a_query_of_only_operators_matches_everything(query: str) -> None:
    assert parse_query(query) is None
    assert _found(query, "anything at all")


def test_dangling_operators_are_read_as_far_as_they_go() -> None:
    assert parse_query("notes |") == parse_query("notes")
    assert parse_query("| notes") == parse_query("notes")
    assert parse_query("notes &") == parse_query("notes")
    assert parse_query("notes !") == parse_query("notes")


def test_fields_are_searched_together() -> None:
    assert matches_search("thanks & reply", ["Thanks", "a reply to a kind note"])


# -- the lists that use it -------------------------------------------------


def test_html_tag_picker_takes_a_query_and_keeps_its_order() -> None:
    plain = search_html_tag_choices("dropdown")
    assert plain  # unchanged plain ranking still finds the select
    either = search_html_tag_choices("h1 | h2")
    assert {"h1", "h2"} <= set(either)
    assert all(row in {"h1", "h2"} or "h1" in row or "h2" in row for row in either)
    assert "h1" not in search_html_tag_choices("h? !h1")
    assert "h2" in search_html_tag_choices("h? !h1")


def test_markdown_tag_picker_takes_a_query() -> None:
    rows = search_markdown_tag_choices("link | image")
    assert "Link" in rows and "Image" in rows


def test_section_pickers_take_a_query() -> None:
    from quill.apps.lite_window_sections import _matching_rows
    from quill.ui.main_frame_section_move import _matching

    rows = ["1 of 3, level 1 - Bread", "2 of 3, level 2 - Rolls", "3 of 3, level 2 - Cake"]
    for matcher in (_matching, _matching_rows):
        assert matcher(rows, "bread 1") == [rows[0]]  # plain: every word
        assert matcher(rows, "rolls | cake") == rows[1:]
        assert matcher(rows, '"level 2" !cake') == [rows[1]]


def test_go_to_anything_headings() -> None:
    from quill.ui.palette import heading_filter

    headings = ["Introduction", "Summary of results", "Draft chapter", "Chapter two"]
    plain = heading_filter("chapter")
    assert [h for h in headings if plain(h)] == ["Draft chapter", "Chapter two"]
    # A plain multi-word heading search is still the whole text, as before.
    assert [h for h in headings if heading_filter("chapter two")(h)] == ["Chapter two"]
    assert [h for h in headings if heading_filter("intro | summary")(h)] == headings[:2]
    assert [h for h in headings if heading_filter("chapter !draft")(h)] == ["Chapter two"]
    assert all(heading_filter("")(h) for h in headings)


def test_go_to_anything_commands_keep_palette_mode_prefixes() -> None:
    from quill.core.commands import Command
    from quill.ui.palette import go_to_commands

    commands = [
        Command("table.insert", "Insert Table", None, lambda: None, "core"),
        Command("file.save", "Save", "Ctrl+S", lambda: None, "core"),
    ]
    assert [c.id for c in go_to_commands(commands, "table & insert", {})] == ["table.insert"]
    assert [c.id for c in go_to_commands(commands, "!table", {})] == ["file.save"]
    # "?" at the start is still the palette's bound-commands mode.
    assert [c.id for c in go_to_commands(commands, "?save", {})] == ["file.save"]


def _tree(tmp_path: Path) -> Path:
    for name in ("a.md", "b.txt", "c.bak", "sub/d.md", "sub/e.MD"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("needle\n", encoding="utf-8")
    return tmp_path


def _names(root: Path, pattern: str) -> list[str]:
    report = search_files(root, pattern, "needle")
    return sorted(entry.path.relative_to(root).as_posix() for entry in report.entries)


def test_file_patterns_without_operators_are_plain_globs(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    assert not uses_file_pattern_query("*.md")
    assert not uses_file_pattern_query("report?.txt")
    assert _names(root, "*.txt") == ["b.txt"]
    assert len(_names(root, "*")) == 5


def test_file_patterns_combine_globs(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    assert _names(root, "*.md | *.txt") == ["a.md", "b.txt", "sub/d.md", "sub/e.MD"]
    assert _names(root, "* !*.bak") == ["a.md", "b.txt", "sub/d.md", "sub/e.MD"]
    assert _names(root, "*.md & !sub/*") == ["a.md"]
    assert _names(root, '"b.txt"') == ["b.txt"]
    assert _names(root, "!") == _names(root, "*")
