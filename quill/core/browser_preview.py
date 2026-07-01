from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import webbrowser
from dataclasses import dataclass
from pathlib import Path

from quill.core.navigation import previous_heading_start


@dataclass(frozen=True, slots=True)
class BrowserOption:
    value: str
    label: str
    executable_names: tuple[str, ...] = ()


_BROWSER_OPTIONS: tuple[BrowserOption, ...] = (
    BrowserOption("system", "System default browser"),
    BrowserOption("edge", "Microsoft Edge", ("msedge.exe", "edge.exe")),
    BrowserOption("chrome", "Google Chrome", ("chrome.exe", "chrome")),
    BrowserOption("firefox", "Mozilla Firefox", ("firefox.exe", "firefox")),
    BrowserOption("brave", "Brave", ("brave.exe", "brave-browser.exe", "brave-browser")),
    BrowserOption("opera", "Opera", ("opera.exe", "opera")),
)


def available_browser_options() -> list[BrowserOption]:
    options = [option for option in _BROWSER_OPTIONS if _is_available(option)]
    return options or [BrowserOption("system", "System default browser")]


def browser_choice_labels() -> list[str]:
    return [option.label for option in available_browser_options()]


def browser_choice_value_for_label(label: str) -> str:
    for option in available_browser_options():
        if option.label == label:
            return option.value
    return "system"


def browser_choice_label_for_value(value: str) -> str:
    for option in available_browser_options():
        if option.value == value:
            return option.label
    return "System default browser"


def normalize_browser_choice(value: str) -> str:
    for option in available_browser_options():
        if option.value == value:
            return value
    return "system"


def open_preview_url(url: str, browser_choice: str) -> None:
    choice = normalize_browser_choice(browser_choice)
    if choice == "system":
        webbrowser.open(url, new=2)
        return
    option = next((item for item in _BROWSER_OPTIONS if item.value == choice), None)
    if option is None:
        webbrowser.open(url, new=2)
        return
    executable = _resolve_browser_executable(option)
    if executable is None:
        webbrowser.open(url, new=2)
        return
    subprocess.Popen(
        [str(executable), url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=os.name != "nt",
    )


def preview_anchor_for_text(text: str, cursor: int, kind: str) -> str | None:
    if kind not in {"markdown", "html"}:
        return None
    start = previous_heading_start(text, cursor, kind)
    if start is None:
        start = 0
    heading = _extract_heading_title(text, start, kind)
    if not heading:
        return None
    return _slugify(heading)


def guess_preview_kind(path: Path | None, text: str) -> str:
    if path is not None:
        suffix = path.suffix.lower()
        if suffix in {".md", ".markdown", ".mdx"}:
            return "markdown"
        if suffix in {".html", ".htm", ".xhtml"}:
            return "html"
    stripped = text.lstrip()
    if re.search(r"^<h[1-6]\b", stripped, flags=re.IGNORECASE | re.MULTILINE):
        return "html"
    if re.search(r"^#{1,6} ", text, flags=re.MULTILINE):
        return "markdown"
    return "plain"


# Characters that have no business in a text preview and render as a phantom
# box: U+FFFC (object replacement — rides in on macOS rich-text/attachment
# paste), the BOM, and zero-width no-break space.
_PREVIEW_JUNK = {0xFFFC: None, 0xFEFF: None}


def _sanitize_preview_text(text: str) -> str:
    return text.translate(_PREVIEW_JUNK) if text else text


# Dark-theme stylesheet injected into the preview body fragment when the app is
# in dark mode (issue #83). The preview is a separate WebView that otherwise
# renders on a white background, so the split view ends up half dark, half
# bright. Targeting ``html``/``body`` from a body-level <style> recolors the
# whole pane; colors keep WCAG AA contrast (light text on a dark background).
_PREVIEW_DARK_STYLE = (
    "<style>"
    "html,body{background:#1e1e1e !important;color:#e6e6e6 !important;}"
    "a{color:#6cb6ff !important;}"
    "pre,code{background:#2d2d2d !important;color:#e6e6e6 !important;}"
    "blockquote{border-left:4px solid #555 !important;color:#c8c8c8 !important;}"
    "th,td{border:1px solid #555 !important;}"
    "th{background:#2d2d2d !important;}"
    "hr{border-color:#555 !important;}"
    "</style>"
)


def _maybe_dark(body: str, dark: bool) -> str:
    return f"{_PREVIEW_DARK_STYLE}{body}" if dark else body


def render_preview_body(text: str, kind: str, dark: bool = False) -> str:
    """Render just the body fragment (no <html> wrapper) for a preview surface."""
    text = _sanitize_preview_text(text)
    if kind == "markdown":
        return _maybe_dark(_render_markdown(text), dark)
    if kind == "html":
        return _maybe_dark(_render_html(text), dark)
    return _maybe_dark(f"<pre>{html.escape(text)}</pre>", dark)


def render_preview_html(title: str, text: str, kind: str, start_anchor: str | None = None) -> str:
    # Deliberately no ``<meta http-equiv="refresh">``: a preview page never
    # force-reloads itself on a timer. Such a poll re-rendered the whole page
    # once a second, which made the open tab flicker and, for a screen-reader
    # or braille user reading the preview, re-announced from the top constantly.
    # The in-app side preview updates by pushing fresh HTML to the WebView; the
    # external browser preview reloads only when the user re-runs the command.
    body = render_preview_body(text, kind)
    anchor_script = ""
    if start_anchor:
        anchor_script = (
            "<script>"
            f'window.addEventListener("load", function(){{'
            f"var node = document.getElementById({start_anchor!r});"
            f"if (node) node.scrollIntoView();"
            "});"
            "</script>"
        )
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{html.escape(title)}</title>"
        "<style>"
        ":root{color-scheme:light dark;}"
        "body{font-family:Segoe UI,Arial,sans-serif;line-height:1.6;margin:2rem;max-width:60rem;}"
        "pre,code{font-family:Consolas,Menlo,monospace;}"
        "pre{white-space:pre-wrap;word-break:break-word;background:#f5f5f5;padding:1rem;border-radius:8px;}"
        "blockquote{border-left:4px solid #ccc;padding-left:1rem;color:#444;}"
        "table{border-collapse:collapse;}"
        "th,td{border:1px solid #ccc;padding:0.4rem 0.6rem;}"
        "h1,h2,h3,h4,h5,h6{scroll-margin-top:1.5rem;}"
        # Dark mode (#126): the default browser link blue (#0000ee) fails contrast
        # on a dark background, so pair light text with a light-blue link colour
        # and darken the code/quote/table chrome to keep everything readable.
        "@media (prefers-color-scheme: dark){"
        "body{background:#1e1e1e;color:#e6e6e6;}"
        "a{color:#6cb6ff;}"
        "a:visited{color:#b48ce6;}"
        "pre{background:#2a2a2a;}"
        "blockquote{border-left-color:#666;color:#c8c8c8;}"
        "th,td{border-color:#555;}"
        "}"
        "</style>"
        '<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" async></script>'
        f"{anchor_script}</head><body>{body}</body></html>"
    )


def _is_available(option: BrowserOption) -> bool:
    if option.value == "system":
        return True
    return _resolve_browser_executable(option) is not None


def _resolve_browser_executable(option: BrowserOption) -> Path | None:
    for executable_name in option.executable_names:
        discovered = shutil.which(executable_name)
        if discovered:
            return Path(discovered)
    candidates = _browser_paths(option)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _browser_paths(option: BrowserOption) -> list[Path]:
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local_app_data = os.environ.get("LocalAppData", "")
    candidates: dict[str, list[Path]] = {
        "edge": [
            Path(program_files) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            Path(program_files_x86) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        ],
        "chrome": [
            Path(program_files) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(program_files_x86) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(local_app_data) / "Google" / "Chrome" / "Application" / "chrome.exe",
        ],
        "firefox": [
            Path(program_files) / "Mozilla Firefox" / "firefox.exe",
            Path(program_files_x86) / "Mozilla Firefox" / "firefox.exe",
        ],
        "brave": [
            Path(program_files) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe",
            Path(program_files_x86)
            / "BraveSoftware"
            / "Brave-Browser"
            / "Application"
            / "brave.exe",
        ],
        "opera": [
            Path(program_files) / "Opera" / "launcher.exe",
            Path(program_files_x86) / "Opera" / "launcher.exe",
        ],
    }
    return candidates.get(option.value, [])


def _extract_heading_title(text: str, start: int, kind: str) -> str | None:
    if kind == "markdown":
        line_end = text.find("\n", start)
        if line_end == -1:
            line_end = len(text)
        line = text[start:line_end].strip()
        match = re.match(r"#{1,6}\s+(.*)$", line)
        if match:
            return match.group(1).strip()
    if kind == "html":
        line_end = text.find("</h", start)
        if line_end == -1:
            return None
        candidate = text[start:line_end]
        candidate = re.sub(r"<[^>]+>", " ", candidate)
        candidate = html.unescape(" ".join(candidate.split()))
        return candidate or None
    return None


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "preview"


def _render_html(text: str) -> str:
    stripped = text.lstrip()
    if stripped.startswith("<"):
        return text
    return f"<pre>{html.escape(text)}</pre>"


def _split_table_row(line: str) -> list[str]:
    """Split a GFM table row into trimmed cells, ignoring outer pipes."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [cell.strip() for cell in s.split("|")]


def _is_table_separator(line: str) -> bool:
    """True for a GFM header-separator row, e.g. ``| --- | :--: |``."""
    s = line.strip()
    if "-" not in s or "|" not in s:
        return False
    cells = _split_table_row(line)
    if not cells:
        return False
    return all(re.fullmatch(r":?-+:?", cell) is not None for cell in cells if cell != "")


def _render_table(header: str, rows: list[str]) -> str:
    headers = _split_table_row(header)
    parts = ["<table>", "<thead>", "<tr>"]
    parts += [f"<th>{_render_inline(cell)}</th>" for cell in headers]
    parts += ["</tr>", "</thead>", "<tbody>"]
    for row in rows:
        cells = _split_table_row(row)
        parts.append("<tr>" + "".join(f"<td>{_render_inline(c)}</td>" for c in cells) + "</tr>")
    parts += ["</tbody>", "</table>"]
    return "".join(parts)


# Hidden-codes vocabulary (docs/rich-text-formatting-hidden-codes-design.md):
# inline run spans ``[text]{font-family="Arial" ...}`` and paragraph alignment
# fenced divs ``::: {align="center"}`` ... ``:::``. These render to styled HTML in
# both the live preview and HTML export (which both flow through this renderer).
_SPAN_CODE_RE = re.compile(r"\[([^\]]+)\]\{([^}]*)\}")
_FENCE_OPEN_CODE_RE = re.compile(r"^:::+\s*\{([^}]*)\}\s*$")
_FENCE_CLOSE_CODE_RE = re.compile(r"^:::+\s*$")
_PAGEBREAK_CODE_RE = re.compile(r"^:::+\s*pagebreak\s*$", re.IGNORECASE)
# Markdown thematic break: a line of 3+ of the same -, *, or _ (spaces allowed,
# up to 3 leading spaces, CommonMark style). Renders to <hr>. A separator row
# inside a GFM table contains "|" and is handled by the table path instead.
_THEMATIC_BREAK_RE = re.compile(r"^ {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$")
_ATTR_PAIR_CODE_RE = re.compile(r'([A-Za-z][\w-]*)\s*=\s*"([^"]*)"|([A-Za-z][\w-]*)')
_ALIGN_VALUES = {"left", "right", "center", "justify"}
_LINE_HEIGHTS = {"1": "1", "1.5": "1.5", "2": "2"}
# Named Word paragraph styles -> a few CSS declarations apiece, so the preview and
# HTML export approximate Word's built-in styles.
_NAMED_STYLE_CSS = {
    "quote": ("font-style: italic", "border-left: 4px solid #ccc", "padding-left: 1rem"),
    "title": ("font-size: 2em", "font-weight: bold"),
    "subtitle": ("font-size: 1.3em", "color: #555"),
    "caption": ("font-size: 0.85em", "font-style: italic", "color: #666"),
}


def _parse_code_attrs(raw: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for match in _ATTR_PAIR_CODE_RE.finditer(raw):
        if match.group(1) is not None:
            attrs[match.group(1).lower()] = match.group(2)
        elif match.group(3) is not None:
            attrs.setdefault(match.group(3).lower(), "")
    return attrs


def _span_style_from_attrs(raw: str) -> str:
    attrs = _parse_code_attrs(raw)
    decl: list[str] = []
    if attrs.get("font-family"):
        decl.append(f"font-family: {html.escape(attrs['font-family'], quote=True)}")
    size = attrs.get("font-size", "")
    if size.isdigit():
        decl.append(f"font-size: {size}pt")
    if attrs.get("color"):
        decl.append(f"color: {html.escape(attrs['color'], quote=True)}")
    if attrs.get("highlight"):
        decl.append(f"background-color: {html.escape(attrs['highlight'], quote=True)}")
    decorations = []
    if "underline" in attrs:
        decorations.append("underline")
    if "strike" in attrs:
        decorations.append("line-through")
    if decorations:
        decl.append(f"text-decoration: {' '.join(decorations)}")
    if "superscript" in attrs:
        decl.append("vertical-align: super")
        decl.append("font-size: smaller")
    elif "subscript" in attrs:
        decl.append("vertical-align: sub")
        decl.append("font-size: smaller")
    return "; ".join(decl)


def _div_style_from_attrs(raw: str) -> str:
    attrs = _parse_code_attrs(raw)
    decl: list[str] = []
    align = attrs.get("align", "").lower()
    if align in _ALIGN_VALUES:
        decl.append(f"text-align: {align}")
    spacing = attrs.get("line-spacing", "")
    if spacing in _LINE_HEIGHTS:
        decl.append(f"line-height: {_LINE_HEIGHTS[spacing]}")
    if attrs.get("space-before", "").isdigit():
        decl.append(f"margin-top: {attrs['space-before']}pt")
    if attrs.get("space-after", "").isdigit():
        decl.append(f"margin-bottom: {attrs['space-after']}pt")
    if attrs.get("indent", "").isdigit():
        decl.append(f"margin-left: {attrs['indent']}pt")
    if attrs.get("first-line-indent", "").isdigit():
        decl.append(f"text-indent: {attrs['first-line-indent']}pt")
    decl.extend(_NAMED_STYLE_CSS.get(attrs.get("pstyle", "").lower(), ()))
    return "; ".join(decl)


def _render_markdown(text: str) -> str:
    lines = text.splitlines()
    blocks: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    list_tag = ""
    code_lines: list[str] = []
    in_code = False

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            blocks.append(f"<p>{_render_inline(' '.join(paragraph))}</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items, list_tag
        if list_items:
            blocks.append(f"<{list_tag}>" + "".join(list_items) + f"</{list_tag}>")
            list_items = []
            list_tag = ""

    index = 0
    total = len(lines)
    while index < total:
        line = lines[index]
        stripped = line.rstrip()
        if in_code:
            if stripped.startswith("```"):
                blocks.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                in_code = False
                code_lines = []
            else:
                code_lines.append(line)
            index += 1
            continue
        if stripped.startswith("```"):
            flush_paragraph()
            flush_list()
            in_code = True
            index += 1
            continue
        # GFM pipe table: a row containing "|" immediately followed by a
        # separator row (| --- | --- |). Consume the header, separator, and the
        # contiguous data rows that follow.
        if "|" in stripped and index + 1 < total and _is_table_separator(lines[index + 1]):
            flush_paragraph()
            flush_list()
            header = stripped
            index += 2
            rows: list[str] = []
            while index < total and lines[index].strip() and "|" in lines[index]:
                rows.append(lines[index])
                index += 1
            blocks.append(_render_table(header, rows))
            continue
        if _PAGEBREAK_CODE_RE.match(stripped):
            flush_paragraph()
            flush_list()
            blocks.append('<div style="page-break-after: always"></div>')
            index += 1
            continue
        fence_open = _FENCE_OPEN_CODE_RE.match(stripped)
        if fence_open:
            flush_paragraph()
            flush_list()
            style = _div_style_from_attrs(fence_open.group(1))
            blocks.append(f'<div style="{style}">' if style else "<div>")
            index += 1
            continue
        if _FENCE_CLOSE_CODE_RE.match(stripped):
            flush_paragraph()
            flush_list()
            blocks.append("</div>")
            index += 1
            continue
        if _THEMATIC_BREAK_RE.match(stripped):
            flush_paragraph()
            flush_list()
            blocks.append("<hr>")
            index += 1
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            flush_paragraph()
            flush_list()
            level = len(heading.group(1))
            title = heading.group(2).strip()
            slug = _slugify(title)
            blocks.append(f'<h{level} id="{slug}">{_render_inline(title)}</h{level}>')
            index += 1
            continue
        bullet = re.match(r"^(\s*)([-*+])\s+(.*)$", line)
        numbered = re.match(r"^(\s*)(\d+)\.\s+(.*)$", line)
        if bullet or numbered:
            flush_paragraph()
            if not list_tag:
                list_tag = "ul" if bullet else "ol"
            item_match = bullet or numbered
            assert item_match is not None  # one of the two matched
            list_items.append(f"<li>{_render_inline(item_match.group(3))}</li>")
            index += 1
            continue
        if not stripped:
            flush_paragraph()
            flush_list()
            index += 1
            continue
        if list_tag:
            flush_list()
        paragraph.append(stripped)
        index += 1

    if in_code:
        blocks.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
    flush_paragraph()
    flush_list()
    return "\n".join(blocks) if blocks else f"<p>{html.escape(text) or '&nbsp;'}</p>"


def _render_inline(text: str) -> str:
    # Hidden-codes run spans are resolved first, on the raw text, so their
    # attribute values are read before html.escape mangles the quotes. The styled
    # HTML is stashed behind a NUL sentinel (which escaping leaves untouched) and
    # restored verbatim at the end, exactly as the export plain-text path stashes
    # links.
    placeholders: list[str] = []

    def _stash_span(match: re.Match[str]) -> str:
        style = _span_style_from_attrs(match.group(2))
        inner = _render_inline(match.group(1))
        if not style:
            placeholders.append(inner)
        else:
            placeholders.append(f'<span style="{style}">{inner}</span>')
        return f"\x00{len(placeholders) - 1}\x00"

    text = _SPAN_CODE_RE.sub(_stash_span, text)
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", lambda m: f"<code>{m.group(1)}</code>", escaped)
    escaped = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{html.escape(m.group(2), quote=True)}">{m.group(1)}</a>',
        escaped,
    )
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)
    return re.sub(r"\x00(\d+)\x00", lambda m: placeholders[int(m.group(1))], escaped)


def file_url(path: Path) -> str:
    return path.as_uri()
