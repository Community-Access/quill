"""Insert Block: what can be inserted, the short form each needs, and its markup (8.2).

The list holds the core blocks QUILL writes itself (most-used first), then the
site's own server-rendered block types with a form generated from their
attribute schema, then the site's patterns and synced patterns, each from A
to Z. Rows read the site's own title and description where the site sent
them, so they are in the site's language.

Static blocks QUILL has no form for are left out on purpose: a static block's
saved HTML must be exactly what its JavaScript save code writes (8.5), which
QUILL can only promise for the blocks it builds here. Server-rendered
(dynamic) blocks are a comment with attributes and no HTML, so any of them can
be inserted safely with a generated form.

The forms are :class:`Field` lists, so the dialog that shows them has no
knowledge of blocks, and these functions are tested without a window.
"""

from __future__ import annotations

import html
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.blocks import Block, serialize_attributes, serialize_block
from quill.core.wordpress.fences_markup import (
    _button,
    _buttons,
    _code,
    _column,
    _columns,
    _details,
    _embed,
    _esc_attr,
    _group,
    _heading,
    _image,
    _inline_to_html,
    _list,
    _list_item,
    _new,
    _paragraph,
    _preformatted,
    _quote_block,
    _separator,
    _spacer,
    _table,
)

__all__ = [
    "CORE_CHOICES",
    "Field",
    "InsertChoice",
    "assign_access_keys",
    "build_choices",
    "build_markup",
    "fetch_choices",
    "fields_for",
    "filter_choices",
]


@dataclass
class Field:
    """One control on a generated form."""

    key: str
    label: str
    #: "text", "multiline", "check" or "choice".
    kind: str
    help: str
    value: Any = ""
    #: For "choice": the spoken rows, and the value each one stands for.
    choices: list[str] = field(default_factory=list)
    values: list[Any] = field(default_factory=list)


def assign_access_keys(labels: Sequence[str]) -> list[str]:
    """Give each label a different ``&`` letter (GATE-14), or none when all are used.

    Labels that already carry one keep it if it is free. A label with no
    free letter gets no access key at all, because a duplicate advertises a
    key that may not work while silence is merely silent.
    """
    used: set[str] = set()
    out: list[str] = []
    for raw in labels:
        plain = raw.replace("&", "")
        wanted = raw.index("&") if "&" in raw else -1
        if wanted >= 0 and wanted < len(plain) and plain[wanted].isalnum():
            letter = plain[wanted].lower()
            if letter not in used:
                used.add(letter)
                out.append(raw)
                continue
        for i, char in enumerate(plain):
            if char.isalnum() and char.lower() not in used:
                used.add(char.lower())
                out.append(plain[:i] + "&" + plain[i:])
                break
        else:
            out.append(plain)
    return out


@dataclass(frozen=True)
class InsertChoice:
    #: "core", "type" (a server-rendered block type), "pattern" or "synced".
    kind: str
    name: str
    title: str
    description: str = ""
    content: str = ""
    ref: int = 0
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def row(self) -> str:
        suffix = {"pattern": ", pattern", "synced": ", synced pattern"}.get(self.kind, "")
        text = self.title + suffix
        return f"{text}: {self.description}" if self.description else text


def _core(name: str, title: str, description: str) -> InsertChoice:
    return InsertChoice("core", name, title, description)


#: The blocks QUILL builds itself, in the order people use them most.
CORE_CHOICES: tuple[InsertChoice, ...] = (
    _core("core/paragraph", "Paragraph", "Ordinary text."),
    _core("core/heading", "Heading", "A heading that starts a section."),
    _core("core/list", "List", "A list with bullets or numbers."),
    _core("core/image", "Image", "A picture from an address, with its alt text."),
    _core("core/buttons", "Buttons", "A button that links somewhere."),
    _core("core/quote", "Quote", "Words someone said, and who said them."),
    _core("core/columns", "Columns", "Text side by side, in columns."),
    _core("core/group", "Group", "A box that keeps blocks together."),
    _core("core/details", "Details", "A summary line that opens to show more."),
    _core("core/table", "Table", "Rows and columns of text."),
    _core("core/embed", "Embed", "A video, post or map from another site, by its address."),
    _core("core/cover", "Cover", "A picture with words over it."),
    _core("core/separator", "Separator", "A line between sections."),
    _core("core/spacer", "Spacer", "Empty space between blocks."),
    _core("core/code", "Code", "Computer code, shown as typed."),
    _core("core/preformatted", "Preformatted", "Text kept exactly as typed."),
)

_CORE_NAMES = {c.name for c in CORE_CHOICES} | {"core/button"}

#: Attributes a generated form never asks for: the block editor's own plumbing.
_PLUMBING = frozenset({"lock", "metadata", "className", "style", "anchor", "align"})


def _text(raw: Any) -> str:
    if isinstance(raw, dict):
        raw = raw.get("raw") or raw.get("rendered") or ""
    return raw if isinstance(raw, str) else ""


def build_choices(
    block_types: Sequence[Mapping[str, Any]] | None,
    patterns: Sequence[Mapping[str, Any]] | None,
    synced: Sequence[Mapping[str, Any]] | None,
) -> list[InsertChoice]:
    """The Insert Block list from what the site sent (any part may be missing)."""
    by_name = {t.get("name"): t for t in block_types or [] if isinstance(t, Mapping)}
    core = [
        InsertChoice(
            "core",
            c.name,
            _text(by_name.get(c.name, {}).get("title")) or c.title,
            _text(by_name.get(c.name, {}).get("description")) or c.description,
        )
        for c in CORE_CHOICES
    ]
    dynamic: list[InsertChoice] = []
    for name, raw in by_name.items():
        if not isinstance(name, str) or name in _CORE_NAMES or not raw.get("is_dynamic"):
            continue
        if raw.get("parent") or raw.get("ancestor"):
            continue
        supports = raw.get("supports")
        if isinstance(supports, Mapping) and supports.get("inserter") is False:
            continue
        attributes = raw.get("attributes")
        dynamic.append(
            InsertChoice(
                "type",
                name,
                _text(raw.get("title")) or name,
                _text(raw.get("description")),
                attributes=attributes if isinstance(attributes, Mapping) else {},
            )
        )
    found_patterns = [
        InsertChoice(
            "pattern",
            str(p.get("name") or ""),
            _text(p.get("title")) or str(p.get("name") or "Pattern"),
            _text(p.get("description")),
            content=_text(p.get("content")),
        )
        for p in patterns or []
        if isinstance(p, Mapping) and p.get("inserter", True) is not False and p.get("content")
    ]
    found_synced: list[InsertChoice] = []
    for b in synced or []:
        if not isinstance(b, Mapping) or not isinstance(b.get("id"), int):
            continue
        unsynced = b.get("wp_pattern_sync_status") == "unsynced"
        # A pattern saved as "not synced" is inserted as a copy: it is a pattern.
        (found_patterns if unsynced else found_synced).append(
            InsertChoice(
                "pattern" if unsynced else "synced",
                f"core/block/{b['id']}",
                _text(b.get("title")) or f"Pattern {b['id']}",
                content=_text(b.get("content")) if unsynced else "",
                ref=b["id"],
            )
        )

    def by_title(items: list[InsertChoice]) -> list[InsertChoice]:
        return sorted(items, key=lambda c: c.title.casefold())

    return core + by_title(dynamic) + by_title(found_patterns) + by_title(found_synced)


def fetch_choices(api: WordPressApi) -> list[InsertChoice]:
    """Ask the site for its block types and patterns; what fails is left out."""

    def attempt(work: Callable[[], Any]) -> list[Any] | None:
        try:
            value = work()
        except WordPressApiError:
            return None
        return value if isinstance(value, list) else None

    types = attempt(lambda: api.get("wp/v2/block-types", context="edit"))
    patterns = attempt(lambda: api.get("wp/v2/block-patterns/patterns"))
    synced = attempt(lambda: list(api.iter_collection("wp/v2/blocks", {"context": "edit"})))
    return build_choices(types, patterns, synced)


def filter_choices(choices: Sequence[InsertChoice], words: str) -> list[InsertChoice]:
    """Typing "but" finds Button and Buttons: every word must start a word of the row."""
    wanted = words.casefold().split()
    if not wanted:
        return list(choices)

    def matches(choice: InsertChoice) -> bool:
        title = choice.title.casefold().split()
        text = choice.row().casefold()
        return all(any(w.startswith(x) for w in title) or x in text for x in wanted)

    return [c for c in choices if matches(c)]


# --------------------------------------------------------------------------- #
# Forms

_LEVELS = [f"Heading level {n}" for n in range(1, 7)]


def _f(key: str, label: str, kind: str, help_text: str, value: Any = "") -> Field:
    return Field(key, label, kind, help_text, value)


def _core_fields(name: str) -> list[Field]:
    if name == "core/paragraph":
        return [_f("text", "&Text:", "multiline", "The paragraph's words.")]
    if name == "core/heading":
        level = Field("level", "&Level:", "choice", "Level 2 starts a section; 3 a part of it.", 2)
        level.choices, level.values = _LEVELS, list(range(1, 7))
        return [_f("text", "&Text:", "text", "The heading's words."), level]
    if name == "core/list":
        return [
            _f("items", "&Items, one per line:", "multiline", "Each line becomes one item."),
            _f("ordered", "&Numbered", "check", "Number the items instead of bullets.", False),
        ]
    if name == "core/image":
        return [
            _f("src", "&Address of the picture:", "text", "Where the picture is on the web."),
            _f(
                "alt", "&Alt text:", "text", "What the picture shows, for people who cannot see it."
            ),
        ]
    if name == "core/buttons":
        return [
            _f("text", "&Text:", "text", "The words on the button."),
            _f("url", "&Link:", "text", "The address the button goes to."),
            _f("new_tab", "Open in a &new tab", "check", "Open the link in a new tab.", False),
        ]
    if name == "core/quote":
        return [
            _f("text", "&Quotation:", "multiline", "The words being quoted."),
            _f("cite", "&Who said it:", "text", "The person or source. Leave empty for none."),
        ]
    if name == "core/columns":
        count = Field("count", "&How many columns:", "choice", "How many side by side.", 2)
        count.choices, count.values = [str(n) for n in range(2, 7)], list(range(2, 7))
        return [count]
    if name == "core/details":
        return [
            _f("summary", "&Summary line:", "text", "The line people read before opening it."),
            _f("text", "&Hidden text:", "multiline", "What shows when it is opened."),
        ]
    if name == "core/table":
        return [
            _f("header", "Column &headings:", "text", "The headings, separated by commas."),
            _f("rows", "Number of &rows:", "text", "How many empty rows under the headings.", "2"),
        ]
    if name == "core/embed":
        return [_f("url", "&Address:", "text", "The page to embed, such as a video's address.")]
    if name == "core/cover":
        return [
            _f("src", "&Address of the picture:", "text", "The background picture's address."),
            _f("text", "&Words over it:", "text", "The words shown on the picture."),
        ]
    if name == "core/spacer":
        return [_f("height", "&Height:", "text", "How tall, such as 50px.", "100px")]
    if name in ("core/code", "core/preformatted"):
        return [_f("text", "&Text:", "multiline", "Typed exactly as it should show.")]
    return []


def _schema_fields(attributes: Mapping[str, Any]) -> list[Field]:
    fields: list[Field] = []
    for key, schema in attributes.items():
        if key in _PLUMBING or not isinstance(schema, Mapping) or schema.get("source"):
            continue
        kind = schema.get("type")
        default = schema.get("default")
        words = _words(key)
        enum = schema.get("enum")
        if isinstance(enum, list) and enum:
            f = Field(key, words + ":", "choice", f"The {words.lower()} setting.", default)
            f.choices, f.values = [str(v) for v in enum], list(enum)
            fields.append(f)
        elif kind == "boolean":
            fields.append(Field(key, words, "check", f"Turn {words.lower()} on.", bool(default)))
        elif kind in ("string", "number", "integer"):
            value = "" if default is None else str(default)
            fields.append(Field(key, words + ":", "text", f"The {words.lower()} setting.", value))
    return fields


def _words(key: str) -> str:
    out = ""
    for char in key:
        out += (" " + char.lower()) if char.isupper() else char
    out = out.replace("_", " ").replace("-", " ").strip()
    return out[:1].upper() + out[1:]


def fields_for(choice: InsertChoice) -> list[Field]:
    """The form for one choice: hand-built for core blocks, generated for others."""
    if choice.kind == "core":
        fields = _core_fields(choice.name)
    elif choice.kind == "type":
        fields = _schema_fields(choice.attributes)
    else:
        fields = []
    labels = assign_access_keys([f.label for f in fields])
    for f, label in zip(fields, labels, strict=True):
        f.label = label
    return fields


# --------------------------------------------------------------------------- #
# Markup


def _s(answers: Mapping[str, Any], key: str) -> str:
    value = answers.get(key, "")
    return value.strip() if isinstance(value, str) else str(value)


def _button_new_tab(text: str, url: str) -> Block:
    href = f' href="{_esc_attr(url)}"' if url else ""
    link = (
        f'<a class="wp-block-button__link wp-element-button"{href} target="_blank" '
        f'rel="noreferrer noopener">{text}</a>'
    )
    attrs = {"linkTarget": "_blank", "rel": "noreferrer noopener"}
    return _new("core/button", attrs, f'\n<div class="wp-block-button">{link}</div>\n')


def _cover(src: str, words: str) -> Block:
    inner = _new(
        "core/paragraph",
        {"align": "center", "fontSize": "large"},
        f'\n<p class="has-text-align-center has-large-font-size">{words}</p>\n',
    )
    head = (
        '\n<div class="wp-block-cover"><span aria-hidden="true" '
        'class="wp-block-cover__background has-background-dim"></span>'
    )
    if src:
        head += (
            f'<img class="wp-block-cover__image-background" alt="" src="{_esc_attr(src)}" '
            'data-object-fit="cover"/>'
        )
    head += '<div class="wp-block-cover__inner-container">'
    attrs: dict[str, Any] = {"url": src} if src else {}
    attrs |= {"dimRatio": 50, "layout": {"type": "constrained"}}
    return _new("core/cover", attrs, head, inner, "</div></div>\n")


def _core_block(name: str, a: Mapping[str, Any]) -> Block | None:
    if name == "core/paragraph":
        return _paragraph(_inline_to_html(_s(a, "text")))
    if name == "core/heading":
        level = a.get("level", 2)
        return _heading(level if isinstance(level, int) else 2, _inline_to_html(_s(a, "text")))
    if name == "core/list":
        lines = [line.strip() for line in _s(a, "items").splitlines() if line.strip()] or [""]
        return _list(bool(a.get("ordered")), [_list_item(_inline_to_html(x), []) for x in lines])
    if name == "core/image":
        return _image(_s(a, "src"), _s(a, "alt"), None, None, None, None)
    if name == "core/buttons":
        text, url = _inline_to_html(_s(a, "text")), _s(a, "url")
        button = _button_new_tab(text, url) if a.get("new_tab") else _button(text, url or None)
        return _buttons([button])
    if name == "core/quote":
        cite = _s(a, "cite")
        body = _paragraph(_inline_to_html(_s(a, "text")))
        return _quote_block([body], _inline_to_html(cite) if cite else None)
    if name == "core/columns":
        count = a.get("count", 2)
        return _columns([_column(None, []) for _ in range(count if isinstance(count, int) else 2)])
    if name == "core/group":
        return _group([])
    if name == "core/details":
        hidden = _s(a, "text")
        children = [_paragraph(_inline_to_html(hidden))] if hidden else []
        return _details(_inline_to_html(_s(a, "summary")), children)
    if name == "core/table":
        header = [_inline_to_html(h.strip()) for h in _s(a, "header").split(",")] or [""]
        rows_text = _s(a, "rows")
        count = int(rows_text) if rows_text.isdigit() else 2
        return _table(header, [[""] * len(header) for _ in range(min(count, 100))])
    if name == "core/embed":
        return _embed(_s(a, "url"), None, None, None)
    if name == "core/cover":
        return _cover(_s(a, "src"), _inline_to_html(_s(a, "text")))
    if name == "core/separator":
        return _separator()
    if name == "core/spacer":
        return _spacer(_s(a, "height") or None)
    if name == "core/code":
        return _code(str(a.get("text", "")))
    if name == "core/preformatted":
        return _preformatted(html.escape(str(a.get("text", "")), quote=False))
    return None


def _schema_attrs(attributes: Mapping[str, Any], answers: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in answers.items():
        schema = attributes.get(key)
        if not isinstance(schema, Mapping):
            continue
        default = schema.get("default")
        kind = schema.get("type")
        if isinstance(value, str) and kind in ("number", "integer"):
            text = value.strip()
            if not text:
                continue
            try:
                value = int(text) if kind == "integer" else float(text)
            except ValueError:
                continue
        if value == default or value == "" or value is None:
            continue
        out[key] = value
    return out


def build_markup(choice: InsertChoice, answers: Mapping[str, Any] | None = None) -> str:
    """The block markup to insert, exactly as WordPress's own save code writes it."""
    answers = answers or {}
    if choice.kind == "core":
        block = _core_block(choice.name, answers)
        return serialize_block(block) if block is not None else ""
    if choice.kind == "synced":
        return f"<!-- wp:block {serialize_attributes({'ref': choice.ref})} /-->"
    if choice.kind == "pattern":
        return choice.content
    attrs = _schema_attrs(choice.attributes, answers)
    short = choice.name[5:] if choice.name.startswith("core/") else choice.name
    return f"<!-- wp:{short} {serialize_attributes(attrs) + ' ' if attrs else ''}/-->"
