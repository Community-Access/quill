"""A BFL document that writes back what nobody touched, byte for byte.

QAF's writer turns any model into canonical BFL, and its reader drops
comments. That is right for QAF, which stores the model. QUILL edits the
person's own text, so it keeps more:

- **Unchanged:** reading a document and writing it back gives the original
  text exactly (CRLF, a byte order mark, comments and odd spacing included).
- **Edited:** each top-level statement whose part of the model is unchanged
  is copied byte for byte; only edited statements are rewritten, in canonical
  spelling at their own indentation, and new items go in after the statement
  of the item before them. Comments and blank lines between statements stay.
- **Islands:** lines QAF's reader skips at the top level (an unknown word,
  QAF's old export dialect) are kept as written. They are not part of QAF's
  model; :func:`model_with_islands` keeps them in ``extensions.quill`` so a
  round trip through JSON keeps them too, and QAF passes extensions back
  unchanged.

When an edit moves items between containers or reorders pages, splicing
would guess; the whole document is then written canonically (islands kept)
and :attr:`BflDocument.last_write` says so.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from quill.core.forms import model as M
from quill.core.forms.bfl_read import ReadResult, Statement, read
from quill.core.forms.bfl_write import Writer, is_bare_page, item_mods, to_bfl

ISLAND_KEY = "quill"
_HEADER_KEYS = ("id", "title", "description", "language", "settings", "extensions")
_PARTS = {"library": "choice_libraries", "translation": "translations"}


@dataclass
class BflDocument:
    raw: str
    result: ReadResult
    model: M.Model
    original: M.Model
    islands: list[str] = field(default_factory=list)
    #: "unchanged", "spliced" or "canonical", after each write.
    last_write: str = ""

    @property
    def errors(self) -> list[dict[str, Any]]:
        return self.result.errors

    @property
    def warnings(self) -> list[dict[str, Any]]:
        return self.result.warnings

    @property
    def statements(self) -> list[Statement]:
        return self.result.statements


def read_bfl(text: str) -> BflDocument:
    """BFL text to a document: the model (``doc.model``, edit it) plus its sources."""
    result = read(text)
    src = result.source
    islands: list[str] = []
    last_end = -1
    for st in result.statements:
        if st.kind != "island":
            continue
        line_start = src.rfind("\n", 0, st.start) + 1
        if st.start < last_end:
            continue
        islands.append(src[line_start : st.end])
        last_end = st.end
    return BflDocument(
        text, result, copy.deepcopy(result.model), copy.deepcopy(result.model), islands
    )


def read_form(text: str) -> M.Model:
    """BFL text to the model (errors are in :func:`bfl_read.read`'s result)."""
    return read(text).model


def model_with_islands(doc: BflDocument) -> M.Model:
    """The model, with the document's islands kept under ``extensions.quill.islands``."""
    out = copy.deepcopy(doc.model)
    if doc.islands:
        out.setdefault("extensions", {}).setdefault(ISLAND_KEY, {})["islands"] = list(doc.islands)
    return out


def to_bfl_with_islands(model: M.Model) -> str:
    """Canonical BFL for a model, writing ``extensions.quill.islands`` back as lines."""
    data = copy.deepcopy(model)
    found: list[str] = []
    extensions = data.get("extensions")
    if isinstance(extensions, dict) and isinstance(extensions.get(ISLAND_KEY), dict):
        quill = extensions[ISLAND_KEY]
        found = [str(i) for i in quill.pop("islands", [])]
        if not quill:
            extensions.pop(ISLAND_KEY)
        if not extensions:
            data.pop("extensions")
    text = to_bfl(data)
    return text + "".join("\n" + i + "\n" for i in found)


# -- writing -------------------------------------------------------------------------


def _header(model: M.Model) -> dict[str, Any]:
    return {k: model[k] for k in _HEADER_KEYS if k in model}


def _page_header(page: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in page.items() if k != "items"}


def _children(item: M.Item) -> list[M.Item]:
    if item.get("type") == "columns":
        return [c for col in item.get("columns") or [] for c in col.get("items") or []]
    return list(item.get("items") or [])


def _containers(model: M.Model) -> dict[str, list[str]]:
    """Container id (``page:<id>`` or an item id) to its children's ids, in order."""
    out: dict[str, list[str]] = {}

    def walk(key: str, entries: list[M.Item]) -> None:
        out[key] = [e["id"] for e in entries]
        for e in entries:
            kids = _children(e)
            if kids or e.get("type") in ("section", "columns", "repeater"):
                walk(e["id"], kids)

    for page in model.get("pages") or []:
        walk("page:" + page["id"], page.get("items") or [])
    return out


def _by_id(model: M.Model) -> dict[str, M.Item]:
    return {i["id"]: i for i in M.iter_items(model)}


def _parent_of(containers: dict[str, list[str]]) -> dict[str, str]:
    return {child: key for key, kids in containers.items() for child in kids}


class _Splice:
    def __init__(self, doc: BflDocument) -> None:
        self.doc = doc
        self.src = doc.result.source
        self.old, self.new = doc.original, doc.model
        self.old_items, self.new_items = _by_id(self.old), _by_id(self.new)
        self.old_tree, self.new_tree = _containers(self.old), _containers(self.new)
        self.emitted: set[str] = set()
        self.claimed = {i for s in doc.statements if s.kind == "items" for i in (s.key or [])}
        # A flat section's children come from the statements after it.
        self.flat = {
            s.key[0]
            for s in doc.statements
            if s.kind == "items"
            and len(s.key or []) == 1
            and self.old_items.get(s.key[0], {}).get("type") == "section"
            and any(c in self.claimed for c in self.old_tree.get(s.key[0], []))
        }

    def possible(self) -> bool:
        old_pages = [p["id"] for p in self.old["pages"]]
        new_pages = [p["id"] for p in self.new["pages"]]
        if old_pages != new_pages:
            return False
        old_parent, new_parent = _parent_of(self.old_tree), _parent_of(self.new_tree)
        for item_id, parent in new_parent.items():
            if item_id in old_parent and old_parent[item_id] != parent:
                return False
        for key, kids in self.new_tree.items():
            kept = [k for k in kids if k in self.old_items]
            if kept != [k for k in self.old_tree.get(key, []) if k in self.new_items]:
                return False
        for name in ("rules", "scoring", "confirmations", "notifications"):
            if not M.same(self.old.get(name), self.new.get(name)) and not any(
                s.kind in (name.rstrip("s"), name) for s in self.doc.statements
            ):
                return False
        return True

    def same_item(self, item_id: str) -> bool:
        old, new = self.old_items.get(item_id), self.new_items.get(item_id)
        if old is None or new is None:
            return False
        if (
            item_id in self.flat
            or old.get("type") == "section"
            and self._is_flat_child_host(item_id)
        ):
            strip = ("items",)
            return M.same(
                {k: v for k, v in old.items() if k not in strip},
                {k: v for k, v in new.items() if k not in strip},
            )
        return M.same(old, new)

    def _is_flat_child_host(self, item_id: str) -> bool:
        return item_id in self.flat

    def item_lines(self, item_id: str, indent: str) -> list[str]:
        item = self.new_items[item_id]
        w = Writer()
        w.counter = -(10**9)  # never leave the #id out: the reader's numbering differs here
        if item_id in self.flat:
            head = (
                "section #" + item["id"] + (" " + _quote(item["label"]) if "label" in item else "")
            )
            lines = [head] + ["  " + m for m in item_mods(item)]
        else:
            w.item(item, 0)
            lines = w.lines
        return [indent + line if line else line for line in lines]

    def lead(self, item_id: str, indent: str) -> list[str]:
        """Lines for items added before ``item_id``, the first kept item of its container."""
        parent = _parent_of(self.new_tree).get(item_id)
        if parent is None:
            return []
        out: list[str] = []
        for k in self.new_tree[parent]:
            if k == item_id or k in self.old_items:
                break
            if k not in self.emitted:
                self.emitted.add(k)
                out += [*self.item_lines(k, indent), ""]
        return out

    def new_after(self, item_id: str, indent: str) -> list[str]:
        """Lines for items added straight after ``item_id`` (and after those)."""
        out: list[str] = []
        parent = _parent_of(self.new_tree).get(item_id)
        if parent is None:
            return out
        kids = self.new_tree[parent]
        i = kids.index(item_id) + 1
        while i < len(kids) and kids[i] not in self.old_items:
            if kids[i] not in self.emitted:
                self.emitted.add(kids[i])
                out += ["", *self.item_lines(kids[i], indent)]
            i += 1
        return out

    def run(self) -> str:  # noqa: C901 - one case per statement kind
        out: list[str] = []
        prev_end = 0
        header_done = False
        page_done: set[int] = set()
        statements = self.doc.statements
        for s in statements:
            if s.start < prev_end:
                continue  # already written, as part of the statement before it on this line
            gap = self.src[prev_end : s.start]
            prev_end = s.end
            text = self.src[s.start : s.end]
            if s.kind in ("bfl", "close", "island"):
                out.append(gap + text)
                if s.kind == "bfl" and not any(x.kind in ("form", "settings") for x in statements):
                    if not M.same(_header(self.old), _header(self.new)):
                        out.append("\n" + self.header_text())
                        header_done = True
                continue
            if s.kind in ("form", "settings"):
                if M.same(_header(self.old), _header(self.new)):
                    out.append(gap + text)
                elif not header_done:
                    out.append(gap + self.header_text())
                    header_done = True
                else:
                    out.append(gap.rstrip("\n") if gap.strip() == "" else gap)
                continue
            if s.kind == "page":
                pi = s.page if s.page is not None else 0
                old_page, new_page = self.old["pages"][pi], self.new["pages"][pi]
                if M.same(_page_header(old_page), _page_header(new_page)):
                    out.append(gap + text)
                elif pi not in page_done:
                    w = Writer()
                    w.page_header(new_page, pi)
                    out.append(gap + "\n".join(s.indent + x for x in w.lines))
                    page_done.add(pi)
                else:
                    out.append(gap.rstrip("\n") if gap.strip() == "" else gap)
                out.extend(self.new_at_start(pi, s.indent + "  ") if s.kind == "page" else [])
                continue
            if s.kind == "items":
                ids = [i for i in s.key or [] if i in self.new_items]
                if not ids:
                    continue  # removed, with the blank lines before it
                before = self.lead(ids[0], s.indent)
                if before:
                    out.append(gap + "\n".join(before))
                    gap = "\n"
                if all(self.same_item(i) for i in s.key or []):
                    out.append(gap + text)
                else:
                    lines: list[str] = []
                    for i in ids:
                        lines += self.item_lines(i, s.indent)
                    out.append(gap + "\n".join(lines))
                extra: list[str] = []
                for i in ids:
                    extra += self.new_after(i, s.indent)
                if extra:
                    out.append("\n" + "\n".join(extra))
                continue
            out.append(gap + self.part_text(s, text))
        out.append(self.src[prev_end:])
        out.append(self.appended_parts())
        return "".join(out)

    def new_at_start(self, pi: int, indent: str) -> list[str]:
        page = self.new["pages"][pi]
        kids = [i["id"] for i in page.get("items") or []]
        lines: list[str] = []
        for k in kids:
            if k in self.old_items:
                break
            if k not in self.emitted:
                self.emitted.add(k)
                lines += ["\n" + x for x in self.item_lines(k, indent)]
        return lines

    def header_text(self) -> str:
        w = Writer()
        w.form_header(self.new)
        return "\n".join(w.lines)

    def part_text(self, s: Statement, text: str) -> str:
        kind = s.kind
        w = Writer()
        if kind in _PARTS:
            name = _PARTS[kind]
            old = (self.old.get(name) or {}).get(s.key)
            new = (self.new.get(name) or {}).get(s.key)
            if M.same(old, new):
                return text
            if new is None:
                return ""
            if kind == "library":
                w.line(0, "library #" + str(s.key))
                for c in new:
                    from quill.core.forms.bfl_write import choice_line

                    w.line(1, choice_line(c))
            else:
                w.translation(str(s.key), new)
            return "\n".join(w.lines)
        if kind == "rule":
            old_r = (self.old.get("rules") or [None] * 1000)[s.key] if s.key is not None else None
            rules = self.new.get("rules") or []
            new_r = rules[s.key] if s.key is not None and s.key < len(rules) else None
            if M.same(old_r, new_r):
                return text
            if new_r is None:
                return ""
            w.rule(new_r)
            return "\n".join(w.lines)
        if kind == "scoring":
            if M.same(self.old.get("scoring"), self.new.get("scoring")):
                return text
            if "scoring" not in self.new:
                return ""
            w.scoring(self.new["scoring"])
            return "\n".join(w.lines)
        if kind in ("confirmation", "notification"):
            key = kind + "s"
            old_o = (
                (self.old.get(key) or [])[s.key]
                if s.key is not None and s.key < len(self.old.get(key) or [])
                else None
            )
            new_list = self.new.get(key) or []
            new_o = new_list[s.key] if s.key is not None and s.key < len(new_list) else None
            if M.same(old_o, new_o):
                return text
            if new_o is None:
                return ""
            w.message_object(kind, new_o, s.key or 0)
            return "\n".join(w.lines)
        return text

    def appended_parts(self) -> str:
        """Libraries, rules and the rest that the edit added, at the end."""
        w = Writer()
        seen = {(s.kind, s.key) for s in self.doc.statements if s.kind != "items"}
        for name, choices in (self.new.get("choice_libraries") or {}).items():
            if ("library", name) not in seen:
                from quill.core.forms.bfl_write import choice_line

                w.blank()
                w.line(0, "library #" + name)
                for c in choices:
                    w.line(1, choice_line(c))
        for i, rule in enumerate(self.new.get("rules") or []):
            if ("rule", i) not in seen:
                w.blank()
                w.rule(rule)
        if "scoring" in self.new and not any(s.kind == "scoring" for s in self.doc.statements):
            w.blank()
            w.scoring(self.new["scoring"])
        for kind in ("confirmation", "notification"):
            for i, obj in enumerate(self.new.get(kind + "s") or []):
                if (kind, i) not in seen:
                    w.blank()
                    w.message_object(kind, obj, i)
        for lang, t in (self.new.get("translations") or {}).items():
            if ("translation", lang) not in seen:
                w.blank()
                w.translation(str(lang), t)
        if not w.lines:
            return ""
        return (
            "\n".join(w.lines).lstrip("\n") + "\n" if w.lines[0] else "\n".join(w.lines[1:]) + "\n"
        )


def _quote(s: str) -> str:
    from quill.core.forms.expr import quote

    return quote(s)


def write_bfl(doc: BflDocument) -> str:
    """The document's model as BFL, keeping every byte of what was not edited."""
    if M.same(doc.model, doc.original):
        doc.last_write = "unchanged"
        return doc.raw
    splice = _Splice(doc)
    if not splice.possible():
        doc.last_write = "canonical"
        text = to_bfl_with_islands(model_with_islands(doc))
    else:
        doc.last_write = "spliced"
        text = splice.run()
        if not text.endswith("\n"):
            text += "\n"
        if not M.same(read(text).model, doc.model):
            # A splice that does not read back to the model would lose an edit
            # silently; the canonical text never does.
            doc.last_write = "canonical"
            text = to_bfl_with_islands(model_with_islands(doc))
    if "\r\n" in doc.raw:
        text = text.replace("\r\n", "\n").replace("\n", "\r\n")
    if doc.raw.startswith("﻿"):
        text = "﻿" + text
    return text


__all__ = [
    "BflDocument",
    "is_bare_page",
    "model_with_islands",
    "read_bfl",
    "read_form",
    "to_bfl_with_islands",
    "write_bfl",
]
