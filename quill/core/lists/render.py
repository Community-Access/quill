"""Markdown and HTML source generation (§7, §8, §21).

The renderers turn the neutral model back into valid source so the user never
types ``-``, ``1.``, ``[ ]``, ``<ul>``, or ``<dl>`` by hand. They honor the
settings' marker/spacing/profile choices and, for definition lists, the active
Markdown definition-list profile — refusing to emit native definition syntax
when the profile is unset, because not every Markdown renderer understands it
(§7.6, §21.2).
"""

from __future__ import annotations

from dataclasses import replace
from html import escape

from quill.core.lists.model import (
    DefinitionList,
    FlatList,
    ListType,
)
from quill.core.lists.settings import (
    DefinitionMarkdownProfile,
    StructuredListSettings,
)

_MD_INDENT = "  "  # two spaces per nesting level in Markdown


class DefinitionProfileError(ValueError):
    """Raised when definition Markdown is requested without a usable profile."""


# The resolutions the §7.6/§21.3 prompt offers when no Markdown definition-list
# profile is configured (profile is ASK/DISABLED): an explicit choice token maps
# to the profile used for that one render. "html" is the recommended first
# semantic fallback (embedded <dl>); "plain" is the "Term: Definition" form; the
# rest are the native syntaxes.
DEFINITION_FALLBACK_PROFILES: dict[str, DefinitionMarkdownProfile] = {
    "html": DefinitionMarkdownProfile.HTML_FALLBACK,
    "plain": DefinitionMarkdownProfile.PLAIN_FALLBACK,
    "pandoc": DefinitionMarkdownProfile.PANDOC,
    "markdown_extra": DefinitionMarkdownProfile.MARKDOWN_EXTRA,
    "multimarkdown": DefinitionMarkdownProfile.MULTIMARKDOWN,
}


def render_definition_with_choice(
    model: DefinitionList, settings: StructuredListSettings, choice: str
) -> str:
    """Render *model* for a one-off definition-profile *choice* (§7.6/§21.3).

    Used when the configured profile is ``ASK``/``DISABLED`` and the user has
    resolved the prompt to a specific fallback (a key of
    :data:`DEFINITION_FALLBACK_PROFILES`). The choice applies to this render only;
    the stored settings are not mutated. Raises ``KeyError`` on an unknown choice.
    """
    profile = DEFINITION_FALLBACK_PROFILES[choice]
    return render_markdown(model, replace(settings, definition_markdown_profile=profile))


# -- Markdown --------------------------------------------------------------- #


def render_markdown(
    model: FlatList | DefinitionList, settings: StructuredListSettings | None = None
) -> str:
    cfg = settings if settings is not None else StructuredListSettings()
    if isinstance(model, DefinitionList):
        return _definition_markdown(model, cfg)
    return _flat_markdown(model, cfg)


def _flat_markdown(model: FlatList, cfg: StructuredListSettings) -> str:
    lines: list[str] = []
    # Per-level ordered counters so nested ordered lists restart correctly.
    counters: dict[int, int] = {}
    for item in model.items:
        level = max(0, item.level)
        for key in list(counters):
            if key > level:
                counters.pop(key, None)
        indent = _MD_INDENT * level
        marker = _md_marker(model, cfg, level, counters, item.checked)
        body_lines = item.text.split("\n")
        first = f"{indent}{marker}{body_lines[0]}".rstrip()
        lines.append(first)
        # Continuation lines of a multi-line item align under the first character
        # after the marker so Markdown keeps them within the item.
        cont_indent = indent + " " * len(marker)
        for extra in body_lines[1:]:
            lines.append(f"{cont_indent}{extra}".rstrip() if extra.strip() else "")
        if cfg.markdown_loose:
            lines.append("")
    if cfg.markdown_loose and lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _md_marker(
    model: FlatList,
    cfg: StructuredListSettings,
    level: int,
    counters: dict[int, int],
    checked: bool,
) -> str:
    if model.list_type is ListType.ORDERED:
        if cfg.ordered_strategy == "repeat_one":
            number = 1
        else:
            start = model.ordered_start if cfg.preserve_start_value else cfg.ordered_start
            counters[level] = counters.get(level, start - 1) + 1
            number = counters[level]
        return f"{number}{cfg.ordered_delimiter} "
    if model.list_type is ListType.CHECKLIST:
        mark = cfg.task_check_mark if checked else " "
        return f"{cfg.bullet_marker} [{mark}] "
    return f"{cfg.bullet_marker} "


def _definition_markdown(model: DefinitionList, cfg: StructuredListSettings) -> str:
    profile = cfg.definition_markdown_profile
    if profile in {DefinitionMarkdownProfile.ASK, DefinitionMarkdownProfile.DISABLED}:
        raise DefinitionProfileError(
            "Definition-list support is not configured for this Markdown document."
        )
    if profile is DefinitionMarkdownProfile.HTML_FALLBACK:
        return _definition_html(model, cfg)
    if profile is DefinitionMarkdownProfile.PLAIN_FALLBACK:
        return _definition_plain_markdown(model, cfg)
    # Pandoc / Markdown Extra / MultiMarkdown all share the "term \n : def" shape.
    blocks: list[str] = []
    for entry in model.entries:
        lines: list[str] = []
        for term in entry.terms:
            if term.strip():
                lines.append(term.strip())
        for definition in entry.definitions:
            if definition.strip():
                # Multi-line definitions keep the colon on the first line only.
                def_lines = definition.strip().split("\n")
                lines.append(f": {def_lines[0]}")
                lines.extend(f"  {extra}" for extra in def_lines[1:])
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _definition_plain_markdown(model: DefinitionList, cfg: StructuredListSettings) -> str:
    lines: list[str] = []
    for entry in model.entries:
        term = " / ".join(t.strip() for t in entry.terms if t.strip())
        definition = " ".join(d.strip() for d in entry.definitions if d.strip())
        lines.append(f"{cfg.bullet_marker} {term}: {definition}".rstrip())
    return "\n".join(lines)


# -- HTML ------------------------------------------------------------------- #


def render_html(
    model: FlatList | DefinitionList, settings: StructuredListSettings | None = None
) -> str:
    cfg = settings if settings is not None else StructuredListSettings()
    if isinstance(model, DefinitionList):
        return _definition_html(model, cfg)
    return _flat_html(model, cfg)


def _flat_html(model: FlatList, cfg: StructuredListSettings) -> str:
    container = "ol" if model.list_type is ListType.ORDERED else "ul"
    start_attr = ""
    if (
        model.list_type is ListType.ORDERED
        and cfg.preserve_start_value
        and model.ordered_start != 1
    ):
        start_attr = f' start="{model.ordered_start}"'

    lines: list[str] = [f"<{container}{start_attr}>"]
    # Build nesting from item levels using a stack of open container depths.
    open_levels = [0]
    for index, item in enumerate(model.items):
        level = max(0, item.level)
        while level > open_levels[-1]:
            # Open a nested list inside the previous <li> (no closing </li> yet).
            inner = "ol" if model.list_type is ListType.ORDERED else "ul"
            lines.append(f"{cfg.html_indent * len(open_levels)}<{inner}>")
            open_levels.append(open_levels[-1] + 1)
        while level < open_levels[-1]:
            depth = len(open_levels) - 1
            inner = "ol" if model.list_type is ListType.ORDERED else "ul"
            lines.append(f"{cfg.html_indent * depth}</{inner}>")
            lines.append(f"{cfg.html_indent * depth}</li>")
            open_levels.pop()
        indent = cfg.html_indent * len(open_levels)
        lines.append(f"{indent}{_html_li(model, cfg, item, index)}")
    while len(open_levels) > 1:
        depth = len(open_levels) - 1
        inner = "ol" if model.list_type is ListType.ORDERED else "ul"
        lines.append(f"{cfg.html_indent * depth}</{inner}>")
        lines.append(f"{cfg.html_indent * depth}</li>")
        open_levels.pop()
    lines.append(f"</{container}>")
    return "\n".join(lines)


def _html_li(model: FlatList, cfg: StructuredListSettings, item, index: int) -> str:  # type: ignore[no-untyped-def]
    text = escape(item.text.replace("\n", " ").strip())
    if model.list_type is ListType.CHECKLIST:
        checked = " checked" if item.checked else ""
        disabled = " disabled" if cfg.html_checkbox_disabled else ""
        # Readable text immediately adjacent to the input (§8.3 default).
        return f'<li><input type="checkbox"{checked}{disabled}> {text}</li>'
    return f"<li>{text}</li>"


def _definition_html(model: DefinitionList, cfg: StructuredListSettings) -> str:
    ind = cfg.html_indent
    lines: list[str] = ["<dl>"]
    for position, entry in enumerate(model.entries):
        if position > 0:
            lines.append("")  # blank line between entries for readability
        for term in entry.terms:
            if term.strip():
                lines.append(f"{ind}<dt>{escape(term.strip())}</dt>")
        for definition in entry.definitions:
            if definition.strip():
                lines.append(f"{ind}<dd>{escape(definition.strip())}</dd>")
    lines.append("</dl>")
    return "\n".join(lines)
