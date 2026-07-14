"""Tests for print pagination and page-set selection (#891)."""

from __future__ import annotations

import pytest

from quill.core.print_pagination import (
    PageSetOption,
    PrintPreview,
    describe_preview,
    margins_text,
    paginate_lines,
    paper_name,
    select_pages,
)


def test_paginate_lines_splits_evenly() -> None:
    lines = [f"line {i}" for i in range(10)]
    pages = paginate_lines(lines, lines_per_page=4)
    assert len(pages) == 3
    assert pages[0] == ["line 0", "line 1", "line 2", "line 3"]
    assert pages[2] == ["line 8", "line 9"]


def test_paginate_lines_empty_document_is_one_blank_page() -> None:
    assert paginate_lines([], lines_per_page=40) == [[]]


def test_paginate_lines_exact_multiple_has_no_trailing_empty_page() -> None:
    lines = [f"line {i}" for i in range(8)]
    pages = paginate_lines(lines, lines_per_page=4)
    assert len(pages) == 2


def test_paginate_lines_rejects_non_positive_lines_per_page() -> None:
    with pytest.raises(ValueError):
        paginate_lines(["a"], lines_per_page=0)


def test_select_pages_all_in_order() -> None:
    assert select_pages(5) == [1, 2, 3, 4, 5]


def test_select_pages_odd_only() -> None:
    assert select_pages(6, page_set=PageSetOption.ODD) == [1, 3, 5]


def test_select_pages_even_only() -> None:
    assert select_pages(6, page_set=PageSetOption.EVEN) == [2, 4, 6]


def test_select_pages_reverse_order() -> None:
    assert select_pages(4, reverse=True) == [4, 3, 2, 1]


def test_select_pages_skip_first_page() -> None:
    assert select_pages(5, skip_first_page=True) == [2, 3, 4, 5]


def test_select_pages_skip_first_then_odd_only() -> None:
    # Odd is computed on the *original* page numbers, not renumbered after the skip.
    assert select_pages(7, page_set=PageSetOption.ODD, skip_first_page=True) == [3, 5, 7]


def test_select_pages_skip_first_and_reverse() -> None:
    assert select_pages(5, skip_first_page=True, reverse=True) == [5, 4, 3, 2]


def test_select_pages_single_page_skip_first_is_empty() -> None:
    assert select_pages(1, skip_first_page=True) == []


def test_describe_preview_singular_page() -> None:
    preview = PrintPreview(page_count=1, paper_name="Letter", margins_text="1-inch margins")
    assert describe_preview(preview) == "1 page, Letter, 1-inch margins"


def test_describe_preview_plural_pages() -> None:
    preview = PrintPreview(page_count=3, paper_name="A4", margins_text="0.5-inch margins")
    assert describe_preview(preview) == "3 pages, A4, 0.5-inch margins"


def test_paper_name_known_sizes() -> None:
    assert paper_name(1) == "Letter"
    assert paper_name(3) == "A4"


def test_paper_name_unknown_id_falls_back() -> None:
    assert paper_name(0) == "the selected paper size"
    assert paper_name(999) == "the selected paper size"


def test_margins_text_all_zero_is_default() -> None:
    assert margins_text((0, 0), (0, 0)) == "default margins"


def test_margins_text_uniform_margins() -> None:
    assert margins_text((25, 25), (25, 25)) == "25mm margins"


def test_margins_text_asymmetric_margins() -> None:
    assert margins_text((10, 20), (30, 40)) == "margins 10/20/30/40mm (left/top/right/bottom)"
