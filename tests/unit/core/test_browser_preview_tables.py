from __future__ import annotations

from quill.core.browser_preview import render_preview_body


def test_markdown_pipe_table_renders_as_html_table() -> None:
    md = "| Name | Version |\n| --- | --- |\n| regex | 2026.5 |\n| requests | 2.31 |"
    out = render_preview_body(md, "markdown")
    assert "<table>" in out
    assert "<th>Name</th>" in out
    assert "<th>Version</th>" in out
    assert "<td>regex</td>" in out
    assert "<td>2026.5</td>" in out
    assert "<td>requests</td>" in out


def test_markdown_table_outer_pipes_and_alignment_colons() -> None:
    md = "| A | B |\n|:---|---:|\n| 1 | 2 |"
    out = render_preview_body(md, "markdown")
    # One header row + one data row.
    assert out.count("<tr>") == 2
    assert "<th>A</th>" in out
    assert "<td>1</td>" in out


def test_markdown_table_without_outer_pipes() -> None:
    md = "Name | Version\n--- | ---\nregex | 2026.5"
    out = render_preview_body(md, "markdown")
    assert "<table>" in out
    assert "<th>Name</th>" in out
    assert "<td>regex</td>" in out


def test_pipes_without_separator_are_not_a_table() -> None:
    out = render_preview_body("a | b is just text\n\nmore text", "markdown")
    assert "<table>" not in out


def test_table_does_not_break_headings_and_lists() -> None:
    md = "# Title\n\n- one\n- two\n\n| X | Y |\n| --- | --- |\n| 1 | 2 |"
    out = render_preview_body(md, "markdown")
    assert "<h1" in out
    assert "<li>one</li>" in out
    assert "<table>" in out


def test_thematic_break_dashes_render_as_hr() -> None:
    out = render_preview_body("above\n\n---\n\nbelow", "markdown")
    assert "<hr>" in out
    # The dashes must not survive as literal paragraph text.
    assert "<p>---</p>" not in out


def test_thematic_break_four_dashes_and_other_markers() -> None:
    for marker in ("----", "***", "___", "- - -", "* * *"):
        out = render_preview_body(f"x\n\n{marker}\n\ny", "markdown")
        assert "<hr>" in out, marker


def test_table_separator_row_is_not_a_thematic_break() -> None:
    md = "| A | B |\n| --- | --- |\n| 1 | 2 |"
    out = render_preview_body(md, "markdown")
    assert "<table>" in out
    assert "<hr>" not in out
