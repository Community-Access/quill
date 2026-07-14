"""Unit tests for the HTML-to-Markdown additions to the text-tools Quillin.

Covers:
- html_ops.py algorithm: headings, paragraphs, bold/italic, inline code, code
  blocks, links, lists (ordered + unordered, nested), blockquotes, hr, script/
  style stripping, and CF_HTML fragment extraction.
- text-tools manifest: updated to include the new command and clipboard.read cap.
- extension handler: inserts Markdown result, announces success, and reports
  empty clipboard gracefully.

No wx and no subprocess.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from quill.core.quillins.loader import bundled_extensions_root
from quill.core.quillins.validation import parse_manifest, validate_manifest

_TEXT_DIR = bundled_extensions_root() / "text-tools"


# -- helpers ------------------------------------------------------------------


def _load_html_ops():
    spec = importlib.util.spec_from_file_location("html_ops", _TEXT_DIR / "html_ops.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _FakeApi:
    def __init__(self) -> None:
        self.handlers: dict[str, Callable[[Any], None]] = {}

    def register_command(self, name: str, handler: Callable[[Any], None]) -> None:
        self.handlers[name] = handler


@dataclass
class _FakeCtx:
    clipboard: str = ""
    text: str = ""
    selection: str = ""
    prompts: list[str | None] = field(default_factory=list)
    inserted: list[str] = field(default_factory=list)
    set_text_calls: list[str] = field(default_factory=list)
    replaced: list[str] = field(default_factory=list)
    buffers: list[tuple[str, str]] = field(default_factory=list)
    announced: list[str] = field(default_factory=list)

    def get_text(self) -> str:
        return self.text

    def get_selection(self) -> str:
        return self.selection

    def get_clipboard(self) -> str:
        return self.clipboard

    def prompt(self, title: str, label: str, default: str = "") -> str | None:
        return self.prompts.pop(0)

    def insert_text(self, text: str) -> None:
        self.inserted.append(text)

    def set_text(self, text: str) -> None:
        self.set_text_calls.append(text)

    def replace_selection(self, text: str) -> None:
        self.replaced.append(text)

    def open_buffer(self, text: str, title: str = "") -> None:
        self.buffers.append((text, title))

    def announce(self, message: str) -> None:
        self.announced.append(message)

    def is_verbosity_speech_enabled(self) -> bool:
        return True

    def get_cursor(self):
        class _C:
            line = 1

        return _C()


def _register_extension() -> _FakeApi:
    sys.path.insert(0, str(_TEXT_DIR))
    try:
        ns: dict[str, Any] = {}
        exec((_TEXT_DIR / "extension.py").read_text(encoding="utf-8"), ns)  # noqa: S102
        api = _FakeApi()
        ns["register"](api)
        return api
    finally:
        sys.path.remove(str(_TEXT_DIR))


# -- html_ops.py algorithm ----------------------------------------------------


def test_bold_and_italic() -> None:
    ops = _load_html_ops()
    assert "**bold**" in ops.html_to_markdown("<b>bold</b>")
    assert "*em*" in ops.html_to_markdown("<em>em</em>")


def test_headings() -> None:
    ops = _load_html_ops()
    result = ops.html_to_markdown("<h1>Title</h1><h2>Sub</h2>")
    assert "# Title" in result
    assert "## Sub" in result


def test_unordered_list() -> None:
    ops = _load_html_ops()
    result = ops.html_to_markdown("<ul><li>alpha</li><li>beta</li></ul>")
    assert "- alpha" in result
    assert "- beta" in result


def test_ordered_list() -> None:
    ops = _load_html_ops()
    result = ops.html_to_markdown("<ol><li>one</li><li>two</li></ol>")
    assert "1. one" in result
    assert "2. two" in result


def test_nested_list() -> None:
    ops = _load_html_ops()
    html = "<ul><li>a<ul><li>nested</li></ul></li></ul>"
    result = ops.html_to_markdown(html)
    assert "nested" in result
    assert "  -" in result


def test_inline_code_and_code_block() -> None:
    ops = _load_html_ops()
    assert "`inline`" in ops.html_to_markdown("<code>inline</code>")
    result = ops.html_to_markdown("<pre><code>block</code></pre>")
    assert "```" in result
    assert "block" in result


def test_link() -> None:
    ops = _load_html_ops()
    result = ops.html_to_markdown('<a href="https://example.com">click</a>')
    assert "[click](https://example.com)" in result


def test_horizontal_rule() -> None:
    ops = _load_html_ops()
    assert "---" in ops.html_to_markdown("<hr>")


def test_blockquote() -> None:
    ops = _load_html_ops()
    assert "> " in ops.html_to_markdown("<blockquote>quoted</blockquote>")


def test_script_and_style_are_stripped() -> None:
    ops = _load_html_ops()
    result = ops.html_to_markdown("<p>keep</p><script>alert(1)</script><style>.x{}</style>")
    assert "keep" in result
    assert "alert" not in result
    assert ".x" not in result


def test_empty_html_returns_empty_string() -> None:
    ops = _load_html_ops()
    assert ops.html_to_markdown("") == ""
    assert ops.html_to_markdown("   ") == ""
    assert ops.html_to_markdown("<p></p>") == ""


def test_plain_text_passes_through() -> None:
    ops = _load_html_ops()
    result = ops.html_to_markdown("just text")
    assert "just text" in result


def test_cf_html_fragment_extraction() -> None:
    ops = _load_html_ops()
    payload = (
        "Version:0.9\r\nStartHTML:0000000000\r\n<!--StartFragment--><b>hi</b><!--EndFragment-->"
    )
    assert ops.extract_cf_html_fragment(payload) == "<b>hi</b>"


def test_cf_html_plain_html_passes_through() -> None:
    ops = _load_html_ops()
    html = "<p>hello</p>"
    assert ops.extract_cf_html_fragment(html) == html


# -- manifest reflects the new command ----------------------------------------


def test_manifest_includes_html_to_markdown_command() -> None:
    raw = json.loads((_TEXT_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert validate_manifest(raw) == []
    manifest = parse_manifest(raw)
    command_ids = {c.id for c in manifest.contributes.commands}
    assert "ext.text.html_to_markdown" in command_ids


def test_manifest_declares_clipboard_read_capability() -> None:
    raw = json.loads((_TEXT_DIR / "manifest.json").read_text(encoding="utf-8"))
    manifest = parse_manifest(raw)
    assert "clipboard.read" in manifest.capabilities


# -- extension handler behavior -----------------------------------------------


def test_html_to_markdown_handler_inserts_result() -> None:
    api = _register_extension()
    ctx = _FakeCtx(clipboard="<p><b>Hello</b> world</p>")
    api.handlers["html_to_markdown"](ctx)
    assert ctx.inserted
    assert "**Hello**" in ctx.inserted[0]
    assert ctx.announced and "Markdown" in ctx.announced[0]


def test_html_to_markdown_handler_empty_clipboard_announces() -> None:
    api = _register_extension()
    ctx = _FakeCtx(clipboard="")
    api.handlers["html_to_markdown"](ctx)
    assert ctx.inserted == []
    assert ctx.announced
    assert "empty" in ctx.announced[0].lower()


def test_html_to_markdown_handler_no_extractable_content_announces() -> None:
    api = _register_extension()
    ctx = _FakeCtx(clipboard="<script>bad</script>")
    api.handlers["html_to_markdown"](ctx)
    assert ctx.inserted == []
    assert ctx.announced
