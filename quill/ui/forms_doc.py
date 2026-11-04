"""A form document as the Forms commands see it: read, edit, write back (17a.4).

wx-free, and the **one place the Forms windows call the core's BFL reader and
writer** (:mod:`quill.core.forms.bfl_document`), so the commands never depend
on how the core spells a document. Everything else here works on the form
model itself -- BAF's JSON, plain dicts and lists, described by
``quill/core/forms/schema/form.schema.json`` -- which is the stable contract
between QUILL and BAF.

An edit is: read the editor's text, change the model, write it back. The
writer copies every statement nobody touched byte for byte, so the editor
replaces the text as one undo step and the person's own spelling survives.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any

from quill.core.forms import model as M

Model = dict[str, Any]
Item = dict[str, Any]


# --------------------------------------------------------------------------- #
# reading and writing (the seam)


def read(text: str) -> Any:
    """The editor's text as a form document; ``.model`` is the form to edit."""
    from quill.core.forms.bfl_document import read_bfl

    return read_bfl(text)


def write(doc: Any) -> str:
    """The (edited) document as text, keeping every untouched statement.

    Checked before it reaches the editor: the text is read back, and if it is
    not the form that was edited, the whole document is written canonically
    instead (comments and unread lines kept). A splice that dropped a question
    would otherwise be a silent loss, and a form is the last place for one.
    """
    from quill.core.forms import bfl_document as bd

    text = str(bd.write_bfl(doc))
    try:
        if M.same(bd.read_bfl(text).model, doc.model):
            return text
        return str(bd.to_bfl_with_islands(bd.model_with_islands(doc)))
    except Exception:  # noqa: BLE001 - the check is a guard; the splice stands without it
        return text


def canonical(model: Model) -> str:
    """A whole new form as canonical BFL, for New Form."""
    from quill.core.forms.bfl_write import to_bfl

    return str(to_bfl(model))


def reading_problems(doc: Any) -> list[tuple[str, int | None]]:
    """The reader's own errors and warnings, with an offset where it gave one."""
    out: list[tuple[str, int | None]] = []
    text = str(getattr(doc, "raw", ""))
    for entry in [*getattr(doc, "errors", []), *getattr(doc, "warnings", [])]:
        message = str(entry.get("message", entry)) if isinstance(entry, dict) else str(entry)
        out.append((message, _offset_of(entry, text)))
    return out


def _offset_of(entry: Any, text: str) -> int | None:
    if not isinstance(entry, dict):
        return None
    if isinstance(entry.get("offset"), int):
        return int(entry["offset"])
    line = entry.get("line")
    if isinstance(line, int) and line > 0:
        starts = [0] + [m.end() for m in re.finditer("\n", text)]
        return starts[min(line, len(starts)) - 1]
    return None


def item_offset(doc: Any, item_id: str) -> int | None:
    """Where *item_id* starts in the text: the start of the line that names it."""
    text = str(getattr(doc, "raw", ""))
    span = (0, len(text))
    for stmt in getattr(doc, "statements", []):
        key = getattr(stmt, "key", None)
        if isinstance(key, (list, tuple, set)) and item_id in key:
            span = (int(stmt.start), int(stmt.end))
            break
    pattern = re.compile(r"#" + re.escape(item_id) + r"(?![A-Za-z0-9_])")
    found = pattern.search(text, *span) or pattern.search(text)
    if found is None:
        item = M.find(doc.model, item_id)
        label = str((item or {}).get("label", ""))
        index = text.find(f'"{label}"', *span) if label else -1
        if index < 0:
            return span[0] if span != (0, len(text)) else None
        return text.rfind("\n", 0, index) + 1
    return text.rfind("\n", 0, found.start()) + 1


# --------------------------------------------------------------------------- #
# finding things in the model


def labels(model: Model) -> dict[str, str]:
    return {k: v or k.replace("_", " ") for k, v in M.labels(model).items()}


def fields(model: Model) -> list[Item]:
    return list(M.fields(model).values())


def name_of(item: Item) -> str:
    """What to call an item in a sentence: its label, else its id."""
    return str(item.get("label") or item.get("id", "")).strip() or "Untitled"


@dataclass
class Place:
    """Where an item sits: the list holding it, its index, and its page."""

    siblings: list[Item]
    index: int
    page: int
    parent: Item | None  # the section or repeater holding it; None on a page


def place_of(model: Model, item_id: str) -> Place | None:
    for page_index, page in enumerate(model.get("pages") or []):
        found = _search(page.setdefault("items", []), item_id, page_index, None)
        if found is not None:
            return found
    return None


def _search(entries: list[Item], item_id: str, page: int, parent: Item | None) -> Place | None:
    for index, item in enumerate(entries):
        if item.get("id") == item_id:
            return Place(entries, index, page, parent)
        children: list[list[Item]] = []
        if item.get("type") == "columns":
            children = [col.setdefault("items", []) for col in item.get("columns") or []]
        elif isinstance(item.get("items"), list):
            children = [item["items"]]
        for child in children:
            found = _search(child, item_id, page, item)
            if found is not None:
                return found
    return None


def new_id(model: Model, wanted: str) -> str:
    """An id from *wanted* that the form does not use yet: ``email``, ``email_2``..."""
    base = re.sub(r"[^A-Za-z0-9_]+", "_", wanted.strip().lower()).strip("_") or "question"
    if base[0].isdigit():
        base = "q_" + base
    taken = {str(i.get("id")) for i in M.iter_items(model)}
    taken |= {str(p.get("id")) for p in model.get("pages") or []}
    candidate, n = base, 2
    while candidate in taken:
        candidate, n = f"{base}_{n}", n + 1
    return candidate


# --------------------------------------------------------------------------- #
# the outline's edits; each returns the sentence to say, or raises Refused


class Refused(Exception):  # noqa: N818 - a sentence, not a failure
    """An edit that cannot be made, with the sentence that says why."""


def move(model: Model, item_id: str, step: int) -> str:
    """Up (-1) or down (+1) among its neighbours; across a page edge to the next page."""
    where = _need(model, item_id)
    target = where.index + step
    if 0 <= target < len(where.siblings):
        where.siblings.insert(target, where.siblings.pop(where.index))
        return "Moved up." if step < 0 else "Moved down."
    pages = model.get("pages") or []
    next_page = where.page + step
    if where.parent is None and 0 <= next_page < len(pages):
        item = where.siblings.pop(where.index)
        items = pages[next_page].setdefault("items", [])
        if step < 0:
            items.append(item)
        else:
            items.insert(0, item)
        return f"Moved to page {next_page + 1}."
    raise Refused("It is already first." if step < 0 else "It is already last.")


def move_in(model: Model, item_id: str) -> str:
    """Into the section just above it, at the end."""
    where = _need(model, item_id)
    above = where.siblings[where.index - 1] if where.index > 0 else None
    if above is None or above.get("type") != "section":
        raise Refused("There is no section just above it to move into.")
    if where.siblings[where.index].get("type") == "section":
        raise Refused("A section cannot go inside another section here.")
    above.setdefault("items", []).append(where.siblings.pop(where.index))
    return f"Moved into {name_of(above)}."


def move_out(model: Model, item_id: str) -> str:
    """Out of its section, to just after it."""
    where = _need(model, item_id)
    if where.parent is None or where.parent.get("type") != "section":
        raise Refused("It is not inside a section.")
    outer = _need(model, str(where.parent["id"]))
    item = where.siblings.pop(where.index)
    outer.siblings.insert(outer.index + 1, item)
    return f"Moved out of {name_of(where.parent)}."


def duplicate(model: Model, item_id: str) -> str:
    where = _need(model, item_id)
    copy_of = copy.deepcopy(where.siblings[where.index])
    copy_of["id"] = new_id(model, str(copy_of.get("id", "copy")) + "_copy")
    for child in _descendants(copy_of):
        child["id"] = new_id(model, str(child.get("id", "copy")) + "_copy")
    where.siblings.insert(where.index + 1, copy_of)
    return "Duplicated. The copy is straight after it."


def remove(model: Model, item_id: str) -> str:
    where = _need(model, item_id)
    gone = where.siblings.pop(where.index)
    ids = {str(gone.get("id"))} | {str(c.get("id")) for c in _descendants(gone)}
    rules = [r for r in model.get("rules") or [] if not set(r.get("targets") or []) <= ids]
    for rule in rules:
        rule["targets"] = [t for t in rule["targets"] if t not in ids]
    if "rules" in model:
        model["rules"] = rules
    return f"{name_of(gone)} removed."


def change_type(model: Model, item_id: str, kind: str) -> str:
    where = _need(model, item_id)
    item = where.siblings[where.index]
    item["type"] = kind
    if kind in M.CHOICE_TYPES and not (
        item.get("choices") or item.get("choice_library") or item.get("cascade")
    ):
        item["choices"] = [{"value": "choice-1", "label": "Choice 1"}]
    if kind not in M.CHOICE_TYPES and kind not in M.OPTIONAL_CHOICE_TYPES:
        for key in ("choices", "choice_library", "cascade"):
            item.pop(key, None)
    return f"Changed to {M.TYPE_NAMES.get(kind, kind)}."


def rename(model: Model, item_id: str, label: str) -> str:
    item = M.find(model, item_id)
    if item is None:
        raise Refused("That question is no longer in the form.")
    item["label"] = label.strip()
    return f"Renamed to {label.strip()}."


def change_id(model: Model, item_id: str, wanted: str) -> str:
    """A new id, with every rule, calculation and translation that names it updated."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", wanted):
        raise Refused("An id is letters, digits and underscores, and does not start with a digit.")
    if wanted != item_id and M.find(model, wanted) is not None:
        raise Refused(f"The id {wanted} is already used in this form.")
    item = M.find(model, item_id)
    if item is None:
        raise Refused("That question is no longer in the form.")
    item["id"] = wanted
    ref = re.compile(r"#" + re.escape(item_id) + r"(?![A-Za-z0-9_])")
    for other in [*M.iter_items(model), *(model.get("pages") or [])]:
        for key in ("when", "calculation", "smart_default"):
            if isinstance(other.get(key), str):
                other[key] = ref.sub("#" + wanted, other[key])
        cascade = other.get("cascade")
        if isinstance(cascade, dict) and cascade.get("from") == item_id:
            cascade["from"] = wanted
    for rule in model.get("rules") or []:
        for key in ("when", "value"):
            if isinstance(rule.get(key), str):
                rule[key] = ref.sub("#" + wanted, rule[key])
        rule["targets"] = [wanted if t == item_id else t for t in rule.get("targets") or []]
    for table in (model.get("translations") or {}).values():
        named = table.get("fields") or {}
        if item_id in named:
            named[wanted] = named.pop(item_id)
    return f"The id is now {wanted}."


def _need(model: Model, item_id: str) -> Place:
    where = place_of(model, item_id)
    if where is None:
        raise Refused("That question is no longer in the form.")
    return where


def _descendants(item: Item) -> list[Item]:
    out: list[Item] = []
    entries: list[Item] = list(item.get("items") or [])
    for col in item.get("columns") or []:
        entries.extend(col.get("items") or [])
    for child in entries:
        out.append(child)
        out.extend(_descendants(child))
    return out


# --------------------------------------------------------------------------- #
# the outline itself


def outline_rows(model: Model) -> list[tuple[str, str | None]]:
    """``(spoken row, item id)`` per page, section and field, in form order.

    "Email address, email field, required, page 1": the core's own summary
    (:mod:`quill.core.forms.summary`) where it answers, else a plain one.
    """
    rows: list[tuple[str, str | None]] = []
    for number, page in enumerate(model.get("pages") or [], 1):
        count = sum(1 for e in _all(page.get("items") or []) if M.is_field_type(e.get("type")))
        title = f", {page['title']}" if page.get("title") else ""
        plural = "question" if count == 1 else "questions"
        rows.append((f"Page {number}{title}, {count} {plural}", None))
        for depth, item in _walk(page.get("items") or [], 1):
            rows.append(("  " * depth + summary_of(model, item, number), str(item.get("id"))))
    return rows


def _walk(entries: list[Item], depth: int) -> list[tuple[int, Item]]:
    out: list[tuple[int, Item]] = []
    for item in entries:
        out.append((depth, item))
        children: list[Item] = list(item.get("items") or [])
        for col in item.get("columns") or []:
            children.extend(col.get("items") or [])
        out.extend(_walk(children, depth + 1))
    return out


def _all(entries: list[Item]) -> list[Item]:
    return [item for _depth, item in _walk(entries, 0)]


def summary_of(model: Model, item: Item, page_number: int) -> str:
    kind = str(item.get("type", ""))
    if kind == "section":
        count = sum(1 for e in _all(item.get("items") or []) if M.is_field_type(e.get("type")))
        return f"Section, {name_of(item)}, {count} question" + ("" if count == 1 else "s")
    if kind == "columns":
        return f"{len(item.get('columns') or [])} columns side by side"
    parts = [str(item.get("label") or f"Untitled question ({item.get('id')})")]
    spoken = M.TYPE_NAMES.get(kind, kind)
    parts.append(spoken + (" field" if kind in M.INPUT_FAMILY else ""))
    if item.get("required"):
        parts.append("required")
    if item.get("choice_library"):
        parts.append(f"choices from the {item['choice_library'].replace('_', ' ')} list")
    elif item.get("choices"):
        n = len(item["choices"])
        parts.append(f"{n} choice" + ("" if n == 1 else "s"))
    if item.get("when"):
        parts.append("shown when " + sentence(model, str(item["when"])))
    if item.get("calculation"):
        parts.append("worked out")
    parts.append(f"page {page_number}")
    return ", ".join(parts)


def sentence(model: Model, expression: str) -> str:
    """An expression as words, with this form's labels; the text itself if it cannot be read."""
    try:
        return str(M.sentence(model, expression))
    except Exception:  # noqa: BLE001 - a rule QUILL cannot read is still shown
        return expression
