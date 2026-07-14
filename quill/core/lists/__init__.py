"""Structured List Studio core (wx-free).

The pure-domain half of the Structured List Studio feature described in
``docs/planning/quill-structured-list-studio-prd.md``: a neutral list/definition
model, import interpretation (turning selected text, lines, or pasted content into
items or term/definition entries), Markdown/HTML source generation that lets the
user work with concepts instead of raw ``-``/``1.``/``<dl>`` syntax, and
conversions between list types with information-loss detection.

Everything here is wx-free and unit-tested so the wx dialog stays a thin shell
that builds a model, asks this package to render it, and previews the result.
"""

from __future__ import annotations

from quill.core.lists.announce import (
    checklist_toggle_announcement,
    definition_entry_announcement,
    flat_item_announcement,
    list_summary,
)
from quill.core.lists.convert import (
    ConversionLoss,
    definition_to_flat,
    flat_to_definition,
)
from quill.core.lists.model import (
    DefinitionEntry,
    DefinitionList,
    FlatList,
    ListItem,
    ListType,
)
from quill.core.lists.nesting import (
    add_child,
    can_indent,
    can_outdent,
    indent,
    move_subtree,
    outdent,
    subtree_end,
)
from quill.core.lists.parse import (
    DefinitionInterpretation,
    SelectionMode,
    detect_definition_separator,
    find_list_block,
    interpret_definition_entries,
    interpret_selection,
    interpret_text_into_definition,
    interpret_text_into_flat,
    list_block_to_flat,
    strip_marker,
)
from quill.core.lists.render import render_html, render_markdown
from quill.core.lists.settings import (
    DefinitionMarkdownProfile,
    StructuredListSettings,
    list_studio_presets,
)
from quill.core.lists.validate import validate_before_commit

__all__ = [
    "ConversionLoss",
    "DefinitionEntry",
    "DefinitionInterpretation",
    "DefinitionList",
    "DefinitionMarkdownProfile",
    "FlatList",
    "ListItem",
    "ListType",
    "SelectionMode",
    "StructuredListSettings",
    "add_child",
    "can_indent",
    "can_outdent",
    "checklist_toggle_announcement",
    "definition_entry_announcement",
    "definition_to_flat",
    "detect_definition_separator",
    "find_list_block",
    "flat_item_announcement",
    "flat_to_definition",
    "indent",
    "interpret_definition_entries",
    "interpret_selection",
    "interpret_text_into_definition",
    "interpret_text_into_flat",
    "list_block_to_flat",
    "list_studio_presets",
    "list_summary",
    "move_subtree",
    "outdent",
    "render_html",
    "render_markdown",
    "strip_marker",
    "subtree_end",
    "validate_before_commit",
]
