"""Pre-commit validation for the Structured List Studio (PRD §26, §28.14).

A wx-free check run just before the generated source replaces document text:
structural invariants plus, for flat Markdown, an item-count round-trip that
reparses the generated source and confirms it yields the same number of items.
Returns a list of human-readable issues (empty means "safe to commit"); the
caller surfaces them and, per §26, leaves the document unchanged when non-empty.
"""

from __future__ import annotations

from quill.core.lists.model import DefinitionList, FlatList
from quill.core.lists.parse import list_block_to_flat


def validate_before_commit(
    model: FlatList | DefinitionList, source: str, target_format: str
) -> list[str]:
    """Return the validation issues for committing ``model`` as ``source``.

    An empty list means the source is safe to insert. ``target_format`` is
    ``"markdown"`` or ``"html"`` and only affects the round-trip check (there is
    no reparser for rendered HTML or definition syntax, so those skip it).
    """
    if not source.strip():
        return ["The list has no content to insert."]

    if isinstance(model, DefinitionList):
        return _validate_definition(model)
    return _validate_flat(model, source, target_format)


def _validate_definition(model: DefinitionList) -> list[str]:
    issues: list[str] = []
    if not model.entries or all(entry.is_blank() for entry in model.entries):
        return ["The definition list has no entries to insert."]
    for index, entry in enumerate(model.entries, start=1):
        if not any(term.strip() for term in entry.terms):
            issues.append(f"Entry {index} has no term.")
    return issues


def _validate_flat(model: FlatList, source: str, target_format: str) -> list[str]:
    if not any(item.text.strip() for item in model.items):
        return ["The list has no items to insert."]
    # Round-trip only the Markdown flat case: reparse the generated source and
    # require the same item count. A mismatch means some item's text injected
    # extra list markup (e.g. a line that itself looks like a bullet), which
    # would silently change the structure once inserted. HTML has no reparser.
    if target_format != "markdown":
        return []
    # A blank item renders as a bare "-" that does not reparse, and a non-blank
    # item reparses to exactly one item (continuation lines are skipped), so the
    # clean-round-trip count is the number of non-blank items.
    reparsed = list_block_to_flat(source)
    expected = sum(1 for item in model.items if item.text.strip())
    if len(reparsed.items) != expected:
        return [
            "The generated list did not round-trip cleanly — some item text may "
            "contain list markup (for example a line starting with '-' or a number "
            "and a dot). Edit those items before inserting."
        ]
    return []
