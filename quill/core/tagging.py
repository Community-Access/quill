from __future__ import annotations

import re
from dataclasses import dataclass

# Re-exported so every existing ``from quill.core.tagging import ...`` still
# works: the split was a GATE-11 extraction, not an interface change.
from quill.core.html_tags import HTML_SEARCH_ALIASES, HTML_TAG_CHOICES, VOID_HTML_TAGS

#: Run-level keyed attributes, in the fixed order they are materialized into a
#: Pandoc span ``[text]{...}`` so the markup round-trips deterministically. The
#: boolean flags (:data:`SPAN_FLAG_ORDER`) are emitted after these.
SPAN_ATTRIBUTE_ORDER = ("font-family", "font-size", "color", "highlight")
#: Run-level boolean flags, emitted bare and in this order (matches the model's
#: ``rtf_model._span_attr_markup`` so apply-then-reparse is stable).
SPAN_FLAG_ORDER = ("underline", "strike", "superscript", "subscript")

#: Paragraph alignments accepted by :func:`build_block_alignment`.
ALIGN_CHOICES = ("left", "right", "center", "justify")
#: Block (fenced-div) attribute keys, in materialization order (matches the
#: model's ``rtf_model._block_markup``).
BLOCK_ATTRIBUTE_ORDER = (
    "align",
    "pstyle",
    "line-spacing",
    "space-before",
    "space-after",
    "indent",
    "first-line-indent",
)
#: Named Word paragraph styles accepted by the ``pstyle`` block attribute.
NAMED_STYLE_CHOICES = ("quote", "title", "subtitle", "caption")
#: Line-spacing values accepted by the ``line-spacing`` block attribute.
LINE_SPACING_CHOICES = ("1", "1.5", "2")

#: The standalone page-break marker line.
PAGE_BREAK_MARKER = "::: pagebreak"

_SPAN_ATTR_PAIR_RE = re.compile(r'([A-Za-z][\w-]*)\s*=\s*"([^"]*)"|([A-Za-z][\w-]*)')
_EXISTING_SPAN_RE = re.compile(r"^\[(.*)\]\{([^}]*)\}$", re.DOTALL)
_EXISTING_DIV_RE = re.compile(r"^:::\s*\{([^}]*)\}\n(.*)\n:::$", re.DOTALL)
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
_U_TAG_RE = re.compile(r"<u>(.*?)</u>", re.DOTALL | re.IGNORECASE)

#: Every Markdown construction the builder below can write.
#:
#: **Underline** and **Horizontal Rule** were missing from this list while
#: :func:`build_markdown_insertion` had handled both for months -- two
#: constructions the picker could produce and could not offer, which is the
#: quietest kind of dead end. **Strikethrough** and **Definition List** are new
#: builders: the first because GFM has had it for a decade, and the second
#: because the editor *announces* definition lists as you arrow through them and
#: being able to hear one you cannot insert is backwards.
MARKDOWN_TAG_CHOICES = [
    "Bold",
    "Italic",
    "Underline",
    "Strikethrough",
    "Inline Code",
    "Code Block",
    "Heading 1",
    "Heading 2",
    "Heading 3",
    "Heading 4",
    "Heading 5",
    "Heading 6",
    "Bullet List",
    "Numbered List",
    "Task List",
    "Definition List",
    "Blockquote",
    "Horizontal Rule",
    "Link",
    "Image",
    "Table",
    "Footnote",
]

_MARKDOWN_SEARCH_ALIASES: dict[str, tuple[str, ...]] = {
    "Heading 1": ("h1", "title"),
    "Heading 2": ("h2",),
    "Heading 3": ("h3",),
    "Heading 4": ("h4",),
    "Heading 5": ("h5",),
    "Heading 6": ("h6",),
    "Bullet List": ("list", "unordered"),
    "Numbered List": ("list", "ordered"),
    "Task List": ("checklist", "todo"),
    "Inline Code": ("code", "snippet"),
    "Code Block": ("code", "fenced"),
    "Footnote": ("note", "citation"),
    "Underline": ("underline", "u"),
    "Strikethrough": ("strike", "struck out", "crossed out", "deleted"),
    "Definition List": ("glossary", "terms", "definitions", "dl"),
    "Horizontal Rule": ("rule", "divider", "separator", "thematic break", "hr"),
    "Blockquote": ("quote", "quotation"),
    "Link": ("url", "href", "hyperlink"),
    "Image": ("picture", "alt text", "photo"),
    "Table": ("grid", "rows", "columns"),
}


@dataclass(frozen=True, slots=True)
class InsertionResult:
    inserted_text: str
    caret_offset: int


def parse_attribute_pairs(raw: str) -> dict[str, str]:
    if not raw.strip():
        return {}
    attributes: dict[str, str] = {}
    parts = [part.strip() for part in raw.replace(",", ";").split(";")]
    for part in parts:
        if not part:
            continue
        if "=" in part:
            key, value = part.split("=", 1)
            attributes[key.strip()] = value.strip().strip('"').strip("'")
            continue
        attributes[part] = ""
    return attributes


def _rank_choices(
    choices: list[str],
    query: str,
    aliases: dict[str, tuple[str, ...]],
) -> list[str]:
    normalized = query.strip().lower()
    if not normalized:
        return list(choices)
    tokens = [token for token in normalized.split() if token]
    scored: list[tuple[tuple[int, int, int], str]] = []
    for choice in choices:
        choice_lower = choice.lower()
        haystack = " ".join((choice_lower, *aliases.get(choice, ())))
        exact_prefix_bonus = 0 if choice_lower.startswith(normalized) else 1
        missing = sum(1 for token in tokens if token not in haystack)
        if missing == len(tokens):
            continue
        token_miss = sum(1 for token in tokens if token not in choice_lower)
        scored.append(((missing, token_miss, exact_prefix_bonus), choice))
    scored.sort(key=lambda item: (item[0], item[1]))
    return [choice for _score, choice in scored]


def html_insert_choices() -> list[str]:
    """Everything Insert HTML Tag offers: the whole controls first, then the tags.

    Whole controls first, and that is the recommendation rather than the
    alphabet. Somebody reaching for "checkbox" almost always wants a checkbox
    *with a label bound to it*, not a bare ``<input>`` they then have to
    remember to wire up -- and the wiring is invisible, so forgetting it looks
    exactly like doing it. The bare tags are all still here, one row further
    down, for when the bare tag is what you meant.

    Imported at call time: :mod:`quill.core.html_forms` imports
    :class:`InsertionResult` from this module, and a module-level import here
    would close the circle.
    """
    from quill.core.html_forms import form_snippet_names

    return [*form_snippet_names(), *HTML_TAG_CHOICES]


def search_html_tag_choices(query: str) -> list[str]:
    """Rank everything the HTML picker offers against *query*.

    Over the snippets as well as the tags, and over both alias tables, so one
    search box answers "dropdown" with the labelled control and the bare
    ``<select>`` and lets the person choose.
    """
    from quill.core.html_forms import FORM_SNIPPET_ALIASES

    return _rank_choices(
        html_insert_choices(), query, {**HTML_SEARCH_ALIASES, **FORM_SNIPPET_ALIASES}
    )


def search_markdown_tag_choices(query: str) -> list[str]:
    return _rank_choices(MARKDOWN_TAG_CHOICES, query, _MARKDOWN_SEARCH_ALIASES)


def build_html_insertion(
    tag: str,
    selected_text: str,
    attributes: dict[str, str],
    document_text: str = "",
) -> InsertionResult:
    """Insert *tag*, which may be a bare element or a whole labelled control.

    ``document_text`` is only read by the form snippets, which scan it for ids
    already in use so a second copy of a control cannot collide with the first
    -- the failure nobody can see, where the second label points at the first
    field and only clicking it reveals the fact.
    """
    from quill.core.html_forms import build_form_snippet, is_form_snippet

    if is_form_snippet(tag):
        return build_form_snippet(tag, selected_text, document_text)
    clean_tag = tag.strip().lower()
    attrs = _render_html_attributes(attributes)
    if clean_tag in VOID_HTML_TAGS:
        text = f"<{clean_tag}{attrs} />"
        return InsertionResult(inserted_text=text, caret_offset=len(text))

    if selected_text:
        text = f"<{clean_tag}{attrs}>{selected_text}</{clean_tag}>"
        return InsertionResult(inserted_text=text, caret_offset=len(text))

    open_tag = f"<{clean_tag}{attrs}>"
    close_tag = f"</{clean_tag}>"
    return InsertionResult(
        inserted_text=f"{open_tag}{close_tag}",
        caret_offset=len(open_tag),
    )


def build_markdown_insertion(
    kind: str,
    selected_text: str,
    link_target: str = "",
) -> InsertionResult:
    content = selected_text or "text"
    if kind == "Bold":
        if selected_text:
            text = f"**{selected_text}**"
            return InsertionResult(text, len(text))
        return InsertionResult("****", 2)
    if kind == "Italic":
        if selected_text:
            text = f"*{selected_text}*"
            return InsertionResult(text, len(text))
        return InsertionResult("**", 1)
    # Markdown has no native underline syntax. Use inline HTML <u>...</u>,
    # which every CommonMark viewer that supports raw HTML will render as
    # underlined text. Surfaces the feature parity with the HTML branch.
    if kind == "Underline":
        if selected_text:
            text = f"<u>{selected_text}</u>"
            return InsertionResult(text, len(text))
        return InsertionResult("<u></u>", 3)
    if kind == "Strikethrough":
        # GFM's ``~~``, which every renderer that speaks GFM understands. Not
        # ``<s>``: a Markdown document should stay readable as Markdown.
        if selected_text:
            text = f"~~{selected_text}~~"
            return InsertionResult(text, len(text))
        return InsertionResult("~~~~", 2)
    if kind == "Definition List":
        # Pandoc / PHP-Markdown-Extra: the term on its own line, the definition
        # indented under a colon. Written out with a placeholder pair rather
        # than as bare syntax, because this is the one Markdown construction
        # whose shape cannot be inferred from a single line of it.
        term = selected_text.splitlines()[0] if selected_text else "Term"
        text = f"{term}\n:   Definition"
        return InsertionResult(text, len(text))
    if kind == "Inline Code":
        if selected_text:
            text = f"`{selected_text}`"
            return InsertionResult(text, len(text))
        return InsertionResult("``", 1)
    if kind == "Code Block":
        return build_markdown_code_block(selected_text)
    if kind.startswith("Heading "):
        level = int(kind.split(" ")[1])
        markers = "#" * level
        if selected_text:
            text = f"{markers} {selected_text}"
            return InsertionResult(text, len(text))
        return InsertionResult(f"{markers} ", len(markers) + 1)
    if kind == "Bullet List":
        lines = _line_list(selected_text or "Item")
        text = "\n".join(f"- {line}" for line in lines)
        return InsertionResult(text, len(text))
    if kind == "Numbered List":
        lines = _line_list(selected_text or "Item")
        text = "\n".join(f"{index}. {line}" for index, line in enumerate(lines, start=1))
        return InsertionResult(text, len(text))
    if kind == "Task List":
        lines = _line_list(selected_text or "Task")
        text = "\n".join(f"- [ ] {line}" for line in lines)
        return InsertionResult(text, len(text))
    if kind == "Blockquote":
        lines = _line_list(selected_text or "Quote")
        text = "\n".join(f"> {line}" for line in lines)
        return InsertionResult(text, len(text))
    if kind == "Horizontal Rule":
        # A thematic break. Selection is irrelevant to a rule, so it is always
        # the standalone marker; the caret lands after it ready to keep typing.
        return InsertionResult("---", 3)
    if kind == "Link":
        target = link_target or "https://example.com"
        text = f"[{content}]({target})"
        return InsertionResult(text, 1 if not selected_text else len(text))
    if kind == "Image":
        target = link_target or "https://example.com/image.png"
        text = f"![{content}]({target})"
        return InsertionResult(text, 2 if not selected_text else len(text))
    if kind == "Table":
        return build_markdown_table(2, 2, include_header=True)
    if kind == "Footnote":
        text = f"{content}[^1]\n\n[^1]: Footnote text"
        return InsertionResult(text, len(content) + 4)
    return InsertionResult(content, len(content))


def render_span_attributes(attributes: dict[str, str]) -> str:
    """Render run-level attributes as a Pandoc span attribute string.

    Keyed pairs are emitted in :data:`SPAN_ATTRIBUTE_ORDER` then boolean flags in
    :data:`SPAN_FLAG_ORDER`, so identical attribute sets always serialize the same
    way (stable round-trip). Empty values are skipped; truthy flags are emitted
    bare.
    """
    parts: list[str] = []
    for key in SPAN_ATTRIBUTE_ORDER:
        value = attributes.get(key, "")
        if value:
            parts.append(f'{key}="{value}"')
    for flag in SPAN_FLAG_ORDER:
        if attributes.get(flag):
            parts.append(flag)
    return " ".join(parts)


def render_block_attributes(attributes: dict[str, str]) -> str:
    """Render block (fenced-div) attributes in :data:`BLOCK_ATTRIBUTE_ORDER`."""
    parts: list[str] = []
    for key in BLOCK_ATTRIBUTE_ORDER:
        value = attributes.get(key, "")
        if value:
            parts.append(f'{key}="{value}"')
    return " ".join(parts)


def _parse_span_attributes(raw: str) -> dict[str, str]:
    """Parse space-separated ``key="value"`` pairs (and bare flags) from a span.

    Mirrors ``quill.io.rtf_model.parse_span_attributes`` but lives in ``core`` so
    ``tagging`` does not import the ``io`` layer.
    """
    attrs: dict[str, str] = {}
    for match in _SPAN_ATTR_PAIR_RE.finditer(raw):
        if match.group(1) is not None:
            attrs[match.group(1).lower()] = match.group(2)
        elif match.group(3) is not None:
            attrs.setdefault(match.group(3).lower(), "1")
    return attrs


def merge_span_attributes(base: dict[str, str], updates: dict[str, str]) -> dict[str, str]:
    """Merge ``updates`` onto ``base``, keeping one attribute set per run.

    Applying font then size to the same selection merges into a single span's
    attribute set rather than nesting spans (mirrors
    ``heading_styles._merge_style_attr``). Empty update values are ignored so a
    no-op apply never clears an existing attribute.
    """
    merged = dict(base)
    for key, value in updates.items():
        if value:
            merged[key.lower()] = value
    return merged


def build_span_insertion(selected_text: str, attrs: dict[str, str]) -> InsertionResult:
    """Materialize an inline run-formatting span ``[text]{...}`` over a selection.

    If ``selected_text`` is itself a single existing span, the new attributes merge
    into its attribute set rather than nesting a second span. With no selection, an
    empty span is produced and the caret is placed between the brackets so the user
    can type the styled text.
    """
    inner = selected_text
    base: dict[str, str] = {}
    match = _EXISTING_SPAN_RE.match(selected_text)
    if match:
        inner = match.group(1)
        base = _parse_span_attributes(match.group(2))
    merged = merge_span_attributes(base, attrs)
    rendered = render_span_attributes(merged)
    if not rendered:
        return InsertionResult(selected_text, len(selected_text))
    if inner:
        text = f"[{inner}]{{{rendered}}}"
        return InsertionResult(text, len(text))
    text = f"[]{{{rendered}}}"
    return InsertionResult(text, 1)


def build_block_attributes(selected_text: str, attrs: dict[str, str]) -> InsertionResult:
    """Materialize a paragraph block-formatting fenced div ``::: {...}``.

    The selection (or a ``text`` placeholder when empty) becomes the div body. If
    the selection is itself an existing div, the new attributes merge into its
    header rather than nesting a second div. An empty/invalid attribute set returns
    the text unchanged. The div is invisible in the editor and only realized at
    export, matching the hidden-codes design.
    """
    body = selected_text
    base: dict[str, str] = {}
    match = _EXISTING_DIV_RE.match(selected_text)
    if match:
        body = match.group(2)
        base = _parse_span_attributes(match.group(1))
    merged = merge_span_attributes(base, attrs)
    rendered = render_block_attributes(merged)
    if not rendered:
        return InsertionResult(selected_text, len(selected_text))
    inner = body or "text"
    text = f"::: {{{rendered}}}\n{inner}\n:::"
    if body:
        return InsertionResult(text, len(text))
    prefix = f"::: {{{rendered}}}\n"
    return InsertionResult(text, len(prefix) + len(inner))


def build_block_alignment(selected_text: str, align: str) -> InsertionResult:
    """Materialize a paragraph-alignment fenced div (thin :func:`build_block_attributes`)."""
    normalized = align.strip().lower()
    if normalized not in ALIGN_CHOICES:
        return InsertionResult(selected_text, len(selected_text))
    return build_block_attributes(selected_text, {"align": normalized})


def strip_run_formatting(text: str) -> str:
    """Remove run-level formatting markup, keeping the visible text (Clear Formatting).

    Unwraps hidden-codes spans ``[inner]{...}`` to ``inner`` (repeatedly, for
    nested spans), then strips bold/italic markers and inline ``<u>`` tags. Links
    ``[label](url)`` are intentionally preserved — clearing *formatting* should not
    destroy a hyperlink.
    """
    previous = None
    while previous != text:
        previous = text
        text = re.sub(r"\[([^\]]*)\]\{[^}]*\}", r"\1", text)
    text = _BOLD_RE.sub(r"\1", text)
    text = _ITALIC_RE.sub(r"\1", text)
    text = _U_TAG_RE.sub(r"\1", text)
    return text


def build_clear_formatting(selected_text: str) -> InsertionResult:
    """Return the selection with run formatting stripped (Clear Formatting)."""
    stripped = strip_run_formatting(selected_text)
    return InsertionResult(stripped, len(stripped))


def build_page_break() -> InsertionResult:
    """Return the standalone page-break marker line."""
    return InsertionResult(PAGE_BREAK_MARKER, len(PAGE_BREAK_MARKER))


def _render_html_attributes(attributes: dict[str, str]) -> str:
    if not attributes:
        return ""
    items = []
    for key, value in attributes.items():
        if value:
            safe = value.replace('"', "&quot;")
            items.append(f'{key}="{safe}"')
        else:
            items.append(key)
    return " " + " ".join(items)


def _line_list(selected_text: str) -> list[str]:
    lines = [line.strip() for line in selected_text.splitlines() if line.strip()]
    return lines or [selected_text.strip() or "Item"]


def build_markdown_table(
    rows: int,
    columns: int,
    include_header: bool = True,
) -> InsertionResult:
    row_count = max(1, rows)
    column_count = max(1, columns)

    parts: list[str] = []
    if include_header:
        header = "| " + " | ".join(f"Column {index}" for index in range(1, column_count + 1)) + " |"
        separator = "| " + " | ".join("---" for _ in range(column_count)) + " |"
        parts.extend([header, separator])

    blank_row = "| " + " | ".join("" for _ in range(column_count)) + " |"
    parts.extend(blank_row for _ in range(row_count))
    snippet = "\n".join(parts)
    return InsertionResult(snippet, len(snippet))


def build_html_table(
    rows: int,
    columns: int,
    include_header: bool = True,
) -> InsertionResult:
    row_count = max(1, rows)
    column_count = max(1, columns)

    lines = ["<table>"]
    if include_header:
        lines.append("  <thead>")
        lines.append("    <tr>")
        for index in range(1, column_count + 1):
            lines.append(f"      <th>Column {index}</th>")
        lines.append("    </tr>")
        lines.append("  </thead>")
    lines.append("  <tbody>")
    for _ in range(row_count):
        lines.append("    <tr>")
        for _ in range(column_count):
            lines.append("      <td></td>")
        lines.append("    </tr>")
    lines.append("  </tbody>")
    lines.append("</table>")
    snippet = "\n".join(lines)
    return InsertionResult(snippet, len(snippet))


def build_markdown_code_block(
    selected_text: str,
    language_hint: str = "",
) -> InsertionResult:
    language = language_hint.strip()
    opening = f"```{language}\n" if language else "```\n"
    inner = selected_text or "\n"
    snippet = f"{opening}{inner}\n```"
    return InsertionResult(snippet, len(opening))


def build_html_code_block(
    selected_text: str,
    language_hint: str = "",
) -> InsertionResult:
    language = language_hint.strip()
    class_attr = f' class="language-{language}"' if language else ""
    open_tag = f"<pre><code{class_attr}>"
    close_tag = "</code></pre>"
    snippet = f"{open_tag}{selected_text or 'code'}{close_tag}"
    return InsertionResult(snippet, len(open_tag))
