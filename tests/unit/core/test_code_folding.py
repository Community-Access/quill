from quill.core.code_folding import (
    extract_foldable_regions,
    next_region_boundary,
    previous_region_boundary,
    region_line_count,
    smallest_region_containing,
)


def test_empty_document_has_no_regions() -> None:
    assert extract_foldable_regions("", "markdown") == []


def test_single_heading_region_runs_to_end_of_document() -> None:
    text = "# Title\nBody line one\nBody line two\n"
    regions = extract_foldable_regions(text, "markdown")
    assert len(regions) == 1
    assert regions[0].label == "Title"
    assert regions[0].level == 1
    assert regions[0].start == 0
    assert regions[0].end == len(text)


def test_heading_region_ends_at_next_same_or_higher_level() -> None:
    text = "# One\nAAA\n## Two\nBBB\n## Three\nCCC\n# Four\nDDD\n"
    regions = extract_foldable_regions(text, "markdown")
    labels_and_spans = [(r.label, text[r.start : r.end]) for r in regions]
    assert labels_and_spans[0] == ("One", "# One\nAAA\n## Two\nBBB\n## Three\nCCC\n")
    assert labels_and_spans[1] == ("Two", "## Two\nBBB\n")
    assert labels_and_spans[2] == ("Three", "## Three\nCCC\n")
    assert labels_and_spans[3] == ("Four", "# Four\nDDD\n")


def test_nested_heading_deeper_level_does_not_close_shallower_section() -> None:
    text = "# Parent\n## Child\nStuff\n# Sibling\n"
    regions = extract_foldable_regions(text, "markdown")
    parent = next(r for r in regions if r.label == "Parent")
    assert text[parent.start : parent.end] == "# Parent\n## Child\nStuff\n"


def test_fenced_code_block_is_a_foldable_region() -> None:
    text = "Intro\n```python\nprint('hi')\n```\nOutro\n"
    regions = extract_foldable_regions(text, "markdown")
    assert len(regions) == 1
    assert regions[0].level == 0
    assert "python" in regions[0].label
    assert text[regions[0].start : regions[0].end] == "```python\nprint('hi')\n```"


def test_fence_without_info_string_gets_generic_label() -> None:
    text = "```\ncode\n```\n"
    regions = extract_foldable_regions(text, "markdown")
    assert regions[0].label == "code block"


def test_unterminated_fence_yields_no_region() -> None:
    text = "```python\nprint('never closed')\n"
    regions = extract_foldable_regions(text, "markdown")
    assert regions == []


def test_heading_and_fence_regions_both_present_and_ordered() -> None:
    text = "# Title\n```python\ncode\n```\nMore text\n"
    regions = extract_foldable_regions(text, "markdown")
    assert len(regions) == 2
    assert regions[0].start <= regions[1].start


def test_region_line_count() -> None:
    text = "# Title\nLine two\nLine three\n"
    regions = extract_foldable_regions(text, "markdown")
    assert region_line_count(text, regions[0]) == 3


def test_smallest_region_containing_picks_tightest_nested_match() -> None:
    text = "# Parent\n```python\ncode\n```\n"
    regions = extract_foldable_regions(text, "markdown")
    fence = next(r for r in regions if r.level == 0)
    # A position inside the fence should resolve to the fence, not the
    # enclosing heading section, even though both contain it.
    found = smallest_region_containing(regions, fence.start + 2)
    assert found is fence


def test_smallest_region_containing_returns_none_outside_any_region() -> None:
    text = "Plain text with no headings or fences.\n"
    regions = extract_foldable_regions(text, "markdown")
    assert smallest_region_containing(regions, 5) is None


def test_next_and_previous_region_boundary() -> None:
    text = "# One\nAAA\n# Two\nBBB\n# Three\nCCC\n"
    regions = extract_foldable_regions(text, "markdown")
    one, two, three = regions

    assert next_region_boundary(regions, one.start) is two
    assert next_region_boundary(regions, two.start) is three
    assert next_region_boundary(regions, three.start) is None

    assert previous_region_boundary(regions, three.start) is two
    assert previous_region_boundary(regions, two.start) is one
    assert previous_region_boundary(regions, one.start) is None
