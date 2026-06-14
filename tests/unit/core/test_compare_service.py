"""Unit tests for quill.core.compare_service (issues #193/#194)."""

from __future__ import annotations

from quill.core.compare_service import (
    CompareOptions,
    CompareService,
    _whitespace_description,
    _word_diff_label,
)


def _svc() -> CompareService:
    return CompareService()


class TestCompareBasic:
    def test_identical_texts_no_groups(self) -> None:
        svc = _svc()
        groups = svc.compare("hello\nworld\n", "hello\nworld\n")
        assert groups == []
        assert svc.group_count == 0
        assert not svc.has_differences

    def test_single_line_replace(self) -> None:
        svc = _svc()
        groups = svc.compare("foo\n", "bar\n")
        assert len(groups) == 1
        assert groups[0].kind == "replace"
        assert groups[0].left_text == ["foo"]
        assert groups[0].right_text == ["bar"]

    def test_insert(self) -> None:
        svc = _svc()
        groups = svc.compare("a\nb\n", "a\nnew\nb\n")
        assert any(g.kind == "insert" for g in groups)

    def test_delete(self) -> None:
        svc = _svc()
        groups = svc.compare("a\nremove_me\nb\n", "a\nb\n")
        assert any(g.kind == "delete" for g in groups)

    def test_index_and_total(self) -> None:
        svc = _svc()
        groups = svc.compare("a\nb\nc\n", "a\nX\nY\n")
        for i, g in enumerate(groups):
            assert g.index == i + 1
            assert g.total == len(groups)


class TestWhitespaceClassification:
    def test_whitespace_only_classified(self) -> None:
        svc = _svc()
        groups = svc.compare("  hello\n", "\thello\n")
        assert any(g.kind == "whitespace" for g in groups)

    def test_ignore_trailing_whitespace(self) -> None:
        opts = CompareOptions(ignore_trailing_whitespace=True)
        svc = _svc()
        groups = svc.compare("hello   \n", "hello\n", options=opts)
        assert groups == []

    def test_ignore_all_whitespace(self) -> None:
        opts = CompareOptions(ignore_all_whitespace=True)
        svc = _svc()
        groups = svc.compare("hello world\n", "helloworld\n", options=opts)
        assert groups == []

    def test_exact_comparison_catches_whitespace(self) -> None:
        svc = _svc()
        groups = svc.compare("hello \n", "hello\n")
        assert len(groups) == 1


class TestNavigation:
    def test_next_advances(self) -> None:
        svc = _svc()
        svc.compare("a\nb\n", "X\nY\n")
        g = svc.next()
        assert g is not None
        assert g.index == 1

    def test_previous_at_start_returns_first(self) -> None:
        svc = _svc()
        svc.compare("a\nb\nc\n", "X\nb\nY\n")
        svc.next()
        svc.next()
        svc.previous()
        g = svc.previous()
        assert g is not None
        assert g.index == 1

    def test_first_last(self) -> None:
        svc = _svc()
        svc.compare("a\nb\nc\n", "X\nb\nY\n")
        first = svc.first()
        last = svc.last()
        assert first is not None
        assert last is not None
        assert first.index < last.index

    def test_no_groups_returns_none(self) -> None:
        svc = _svc()
        svc.compare("same\n", "same\n")
        assert svc.next() is None
        assert svc.previous() is None
        assert svc.first() is None
        assert svc.last() is None

    def test_at_end(self) -> None:
        svc = _svc()
        svc.compare("a\n", "b\n")
        svc.first()
        assert svc.at_end()


class TestInlineSpans:
    def test_single_line_replace_has_spans(self) -> None:
        svc = _svc()
        groups = svc.compare("private fun load()\n", "private suspend fun load()\n")
        assert len(groups) == 1
        g = groups[0]
        assert g.kind == "replace"
        assert len(g.inline_spans) > 0

    def test_multiline_replace_no_spans(self) -> None:
        svc = _svc()
        groups = svc.compare("a\nb\n", "x\ny\n")
        for g in groups:
            if g.kind == "replace" and (len(g.left_text) > 1 or len(g.right_text) > 1):
                assert g.inline_spans == []


class TestSummaries:
    def test_short_summary_contains_index(self) -> None:
        svc = _svc()
        groups = svc.compare("foo\n", "bar\n")
        assert "1 of 1" in groups[0].summary_short

    def test_verbose_summary_contains_left_right(self) -> None:
        svc = _svc()
        svc.left_label = "Original"
        svc.right_label = "Modified"
        svc.compare("hello\n", "world\n")
        svc.compare("hello\n", "world\n", left_label="Original", right_label="Modified")
        g = svc._groups[0]
        assert "Original" in g.summary_verbose or "Modified" in g.summary_verbose

    def test_whitespace_summary_describes_leading(self) -> None:
        svc = _svc()
        groups = svc.compare("    hello\n", "\thello\n")
        assert len(groups) == 1
        assert "whitespace" in groups[0].summary_short.lower()


class TestWordDiffLabel:
    def test_added_word(self) -> None:
        label = _word_diff_label("private fun load()", "private suspend fun load()")
        assert "suspend" in label

    def test_removed_word(self) -> None:
        label = _word_diff_label("val x = foo()", "val x = ()")
        assert "foo" in label

    def test_changed_word(self) -> None:
        label = _word_diff_label("val result = load()", "val result = loadAsync()")
        assert "load" in label or "loadAsync" in label


class TestWhitespaceDescription:
    def test_leading_spaces(self) -> None:
        desc = _whitespace_description("    hello")
        assert "leading" in desc

    def test_blank_line(self) -> None:
        desc = _whitespace_description("")
        assert "blank" in desc
