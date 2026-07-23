"""#1200: the live preview must not renumber ordered lists or split loose lists,
so the preview matches the numbers the author typed in the editor."""

from __future__ import annotations

from quill.core.browser_preview import _render_markdown


def test_ordered_list_honors_author_start_number() -> None:
    html = _render_markdown("3. Third\n4. Fourth\n5. Fifth")
    assert '<ol start="3">' in html
    assert html.count("<li>") == 3
    assert "<li>Third</li>" in html


def test_ordered_list_starting_at_one_has_no_start_attribute() -> None:
    html = _render_markdown("1. a\n2. b")
    assert "<ol>" in html
    assert "start=" not in html


def test_loose_ordered_list_stays_one_list() -> None:
    # Blank lines between items must not split into three <ol> that each restart.
    html = _render_markdown("1. First\n\n2. Second\n\n3. Third")
    assert html.count("<ol") == 1
    assert html.count("<li>") == 3


def test_loose_bullet_list_stays_one_list() -> None:
    html = _render_markdown("- a\n\n- b")
    assert html.count("<ul>") == 1
    assert html.count("<li>") == 2


def test_paragraph_after_list_still_separates() -> None:
    html = _render_markdown("1. a\n2. b\n\nA new paragraph.")
    assert "<ol>" in html
    assert "<p>A new paragraph.</p>" in html
