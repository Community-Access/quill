from __future__ import annotations

from quill.ui.word_view import render_word_accessible_preview


def test_render_word_accessible_preview_uses_html_headings_and_tables() -> None:
    html = """
    <html><body>
      <h1>Quarterly Report</h1>
      <p>Highlights are below.</p>
      <table>
        <tr><th>Item</th><th>Amount</th></tr>
        <tr><td>Revenue</td><td>1200</td></tr>
        <tr><td>Cost</td><td>400</td></tr>
      </table>
    </body></html>
    """

    preview = render_word_accessible_preview("fallback", html)

    assert "# Quarterly Report" in preview
    assert "Highlights are below." in preview
    assert "Table 1" in preview
    assert "Headers: Item | Amount" in preview
    assert "Row 2: Item: Revenue; Amount: 1200" in preview


def test_render_word_accessible_preview_falls_back_to_markdown_text() -> None:
    preview = render_word_accessible_preview("# Heading\n\nBody", None)
    assert preview == "# Heading\n\nBody\n"


def test_render_word_accessible_preview_linearizes_markdown_tables() -> None:
    markdown = "# Budget\n\n| Item | Amount |\n| --- | --- |\n| Revenue | 1200 |\n| Cost | 400 |\n"

    preview = render_word_accessible_preview(markdown, None)

    assert "Table 1" in preview
    assert "Headers: Item | Amount" in preview
    assert "Row 1: Item: Revenue; Amount: 1200" in preview
    assert "Row 2: Item: Cost; Amount: 400" in preview


def _method_calls_ensure_text_mode(method_name: str) -> bool:
    """True if WordDocumentSurface.<method_name> calls _ensure_text_mode()."""
    import ast
    from pathlib import Path

    src = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "word_view.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "WordDocumentSurface":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == method_name:
                    return any(
                        isinstance(call, ast.Call)
                        and isinstance(call.func, ast.Attribute)
                        and call.func.attr == "_ensure_text_mode"
                        for call in ast.walk(item)
                    )
    return False


def test_find_selection_surfaces_the_text_editor() -> None:
    """Regression for #1182: the structured Word view defaults to the preview
    (structure) page, but Find operated on the hidden text control -- selecting
    and moving the caret where the user could not see it, so Find looked like it
    never located anything. SetSelection and SetInsertionPoint must switch to
    the text page first (like Replace) so a match is shown."""
    assert _method_calls_ensure_text_mode("SetSelection")
    assert _method_calls_ensure_text_mode("SetInsertionPoint")
