"""
Tests for HTML paste detection and cleaning.

Validates that the html_paste_cleaner correctly:
- Detects HTML from web pastes
- Cleans HTML to plain text while preserving structure
- Provides heuristic detection without false positives
"""

from quill.ui.html_paste_cleaner import (
    analyze_paste,
    clean_html,
    is_html,
)


class TestIsHtmlDetection:
    """Tests for HTML heuristic detection."""

    def test_simple_html_tags(self) -> None:
        """Detect common structural HTML tags."""
        assert is_html("<p>Hello</p>")
        assert is_html("<h1>Title</h1>")
        assert is_html("<div>Content</div>")
        assert is_html("<ul><li>Item</li></ul>")

    def test_html_from_web_browser(self) -> None:
        """Detect typical web browser HTML."""
        web_html = """
        <div class="article">
            <h2>Article Title</h2>
            <p>First paragraph with <strong>bold</strong> text.</p>
            <p>Second paragraph with <a href="/link">link</a>.</p>
        </div>
        """
        assert is_html(web_html)

    def test_html_with_attributes(self) -> None:
        """Detect HTML even with attributes and classes."""
        assert is_html('<div class="container" id="main">Content</div>')
        assert is_html('<a href="https://example.com">Link</a>')

    def test_no_false_positive_code(self) -> None:
        """Do NOT detect code samples with angle brackets as HTML."""
        assert not is_html("vector<int> and map<string, int>")
        assert not is_html("// Generic template<T>")
        assert not is_html("x < 5 and y > 10")

    def test_no_false_positive_email(self) -> None:
        """Do NOT detect email footers with <name@example.com> as HTML."""
        assert not is_html("Best regards,\nJohn <john@example.com>")

    def test_markdown_not_html(self) -> None:
        """Markdown should not trigger HTML detection."""
        markdown = "# Heading\n\n**Bold text** and *italic*."
        assert not is_html(markdown)

    def test_plain_text_not_html(self) -> None:
        """Plain text should not trigger HTML detection."""
        assert not is_html("This is just plain text.")
        assert not is_html("Hello world")

    def test_short_text_not_html(self) -> None:
        """Very short text should not trigger HTML detection."""
        assert not is_html("<p>")


class TestCleanHtml:
    """Tests for HTML-to-text cleaning."""

    def test_simple_paragraph_cleanup(self) -> None:
        """Clean simple paragraphs to plain text."""
        html = "<p>Hello world</p>"
        text = clean_html(html)
        assert "Hello world" in text
        assert "<p>" not in text

    def test_preserve_heading_structure(self) -> None:
        """Preserve heading hierarchy (spacing)."""
        html = "<h1>Title</h1><h2>Subtitle</h2><p>Content</p>"
        text = clean_html(html)
        assert "Title" in text
        assert "Subtitle" in text
        assert "Content" in text

    def test_strip_script_and_style(self) -> None:
        """Remove script and style blocks."""
        html = """
        <p>Visible</p>
        <script>alert('hidden')</script>
        <style>body { color: red; }</style>
        """
        text = clean_html(html)
        assert "Visible" in text
        assert "alert" not in text
        assert "color: red" not in text

    def test_strip_script_and_style_with_spaced_end_tags(self) -> None:
        """A browser ends a script at ``</script >`` too, so the cleaner must."""
        html = "<p>Visible</p><script>alert('hidden')</script ><style>b{color:red}</STYLE	>"
        text = clean_html(html)
        assert "Visible" in text
        assert "alert" not in text
        assert "color:red" not in text

    def test_preserve_strong_emphasis(self) -> None:
        """Keep <strong> and <em> text (tags stripped, text kept)."""
        html = "<p>This is <strong>important</strong> and <em>emphatic</em>.</p>"
        text = clean_html(html)
        assert "important" in text
        assert "emphatic" in text
        assert "<strong>" not in text
        assert "<em>" not in text

    def test_extract_link_text(self) -> None:
        """Extract link text (URL is visible in plain text context)."""
        html = '<p>Click <a href="https://example.com">here</a> for more.</p>'
        text = clean_html(html)
        assert "here" in text
        assert "more" in text

    def test_convert_line_breaks(self) -> None:
        """Convert <br> tags to newlines."""
        html = "Line 1<br>Line 2<br/>Line 3"
        text = clean_html(html)
        lines = text.strip().split("\n")
        assert len(lines) >= 2  # At least 2 lines from <br> conversion

    def test_handle_html_entities(self) -> None:
        """Decode HTML entities."""
        html = "<p>Copyright &copy; 2026 &mdash; All Rights Reserved</p>"
        text = clean_html(html)
        assert "©" in text or "copy" in text
        assert "Reserved" in text

    def test_collapse_whitespace(self) -> None:
        """Collapse excess whitespace."""
        html = "<p>Too    many     spaces</p>"
        text = clean_html(html)
        # Cleaned text should not have excessive spaces
        assert "Too    many" not in text or text.count(" ") < html.count(" ")


class TestAnalyzePaste:
    """Tests for paste context analysis."""

    def test_plain_text_context(self) -> None:
        """Analyze plain text paste."""
        ctx = analyze_paste("Just some plain text")
        assert not ctx.is_html
        assert ctx.cleaned_text is None
        assert ctx.get_paste_text(clean=False) == "Just some plain text"

    def test_html_context(self) -> None:
        """Analyze HTML paste."""
        html = "<p>Hello</p>"
        ctx = analyze_paste(html)
        assert ctx.is_html
        assert ctx.cleaned_text is not None
        assert "Hello" in ctx.get_paste_text(clean=True)

    def test_get_paste_text_respects_clean_flag(self) -> None:
        """get_paste_text returns cleaned or original based on flag."""
        html = "<p>Text</p>"
        ctx = analyze_paste(html)

        # With clean=True: get cleaned text
        clean_text = ctx.get_paste_text(clean=True)
        assert "<p>" not in clean_text
        assert "Text" in clean_text

        # With clean=False: get original
        raw_text = ctx.get_paste_text(clean=False)
        assert raw_text == html


class TestIntegrationWebClip:
    """Integration tests with realistic web-pasted content."""

    def test_blog_post_clip(self) -> None:
        """Clean a typical blog post HTML clip."""
        html = """
        <div class="blog-post">
            <h2>How to Write Accessible Code</h2>
            <p>Accessibility starts with <strong>awareness</strong>.</p>
            <p>Follow these steps:</p>
            <ol>
                <li>Think about users with disabilities</li>
                <li>Test with real assistive tech</li>
                <li>Iterate based on feedback</li>
            </ol>
            <p>For more, visit <a href="https://a11y.guide">a11y.guide</a>.</p>
        </div>
        """
        text = clean_html(html)

        # Check that key content is preserved
        assert "Accessible Code" in text
        assert "awareness" in text
        assert "assistive" in text or "disabilities" in text
        # HTML tags should be gone
        assert "<div" not in text
        assert "<ol>" not in text

    def test_email_html_clip(self) -> None:
        """Clean an HTML email snippet."""
        html = """
        <div>
            <p>Hi there,</p>
            <p>Thank you for reaching out. Here's what we found:</p>
            <ul>
                <li>Issue #1: Performance</li>
                <li>Issue #2: Accessibility</li>
            </ul>
            <p>Best regards,<br>The Team</p>
        </div>
        """
        text = clean_html(html)

        assert "Thank you" in text
        assert "Performance" in text
        assert "Accessibility" in text
        assert "The Team" in text
