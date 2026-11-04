"""Writing the form model as canonical BFL: a port of BAF's ``BAF_BFL_Writer``.

:func:`to_bfl` writes exactly what BAF's writer writes, byte for byte: ``bfl 1``
first, two spaces a level, a blank line between top-level blocks, ``#id`` left
out where the reader would make up the same one, and every expression in
canonical text. BAF's ``tests/conformance/bfl/canonical`` cases are the
contract. Writing an *edited* document while keeping its untouched text is
:func:`quill.core.forms.bfl_document.write_bfl`.
"""

from __future__ import annotations

from typing import Any

from quill.core.forms import expr as E
from quill.core.forms import model as M


def value_text(v: Any) -> str:
    """A value as BFL writes it: compact JSON for lists and objects, else a literal."""
    if isinstance(v, (list, dict)):
        return M.encode(v)
    return E.literal_text(v)


def _mod(name: str, v: Any) -> str:
    return "@" + name + ("" if v is True else " " + value_text(v))


def _plain(s: str) -> bool:
    return s != "" and s.strip(" \t\n\r\0\x0b") == s and "\n" not in s and s[0] != '"'


def choice_line(c: dict[str, Any]) -> str:
    value = c["value"] if isinstance(c["value"], str) else E.literal_text(c["value"])
    label = c["label"] if isinstance(c["label"], str) else E.literal_text(c["label"])
    extras = {k: v for k, v in c.items() if k not in ("value", "label")}
    if not extras:
        if (
            _plain(label)
            and "|" not in label
            and ":" not in label
            and value == M.slug(label)
            and value != ""
        ):
            return "+ " + label
        if _plain(value) and "|" not in value and _plain(label):
            return f"+ {value}|{label}"
    line = "+ " + E.quote(value) + " | " + E.quote(label)
    for k in ("price", "image", "points", "description", "selected"):
        if k in c:
            line += " @" + k + ("" if c[k] is True else " " + value_text(c[k]))
    return line


class Writer:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.counter = 0

    def line(self, level: int, text: str) -> None:
        self.lines.append("  " * level + text)

    def blank(self) -> None:
        if self.lines and self.lines[-1] != "":
            self.lines.append("")

    def mod(self, level: int, name: str, v: Any) -> None:
        self.line(level, _mod(name, v))

    def id_part(self, item: M.Item) -> str:
        self.counter += 1
        return "" if item["id"] == f"field_{self.counter}" else " #" + item["id"]

    def items(self, entries: list[M.Item], level: int) -> None:
        for item in entries:
            self.item(item, level)

    def item(self, item: M.Item, level: int) -> None:
        kind = item["type"]
        head = kind + self.id_part(item)
        if kind == "columns":
            self.line(level, f"{head} {len(item['columns'])}")
            if "when" in item:
                self.line(level + 1, "@when " + item["when"])
            for k, v in (item.get("props") or {}).items():
                self.mod(level + 1, k, v)
            for col in item["columns"]:
                self.line(level + 1, "column")
                if "width" in col:
                    self.mod(level + 2, "width", col["width"])
                self.items(col["items"], level + 2)
            return
        if "label" in item:
            head += " " + E.quote(item["label"])
        mods = item_mods(item)
        if kind == "section" and not item.get("items"):
            if not mods:
                self.line(level, head + " {}")
                return
            self.line(level, head + " {")
            for m in mods:
                self.line(level + 1, m)
            self.line(level, "}")
            return
        self.line(level, head)
        for m in mods:
            self.line(level + 1, m)
        for c in item.get("choices") or []:
            self.line(level + 1, choice_line(c))
        if "items" in item:
            self.items(item["items"], level + 1)

    def run(self, model: M.Model) -> str:  # noqa: C901 - one block per part of the model
        self.lines = [f"bfl {M.MODEL_VERSION}"]
        self.counter = 0
        self.form_header(model)
        for name, choices in (model.get("choice_libraries") or {}).items():
            self.blank()
            self.line(0, "library #" + name)
            for c in choices:
                self.line(1, choice_line(c))
        pages = model.get("pages") or []
        bare = len(pages) == 1 and is_bare_page(pages[0], 0)
        for i, page in enumerate(pages):
            self.blank()
            if bare:
                self.items(page["items"], 0)
                continue
            self.page_header(page, i)
            self.items(page["items"], 1)
        for rule in model.get("rules") or []:
            self.blank()
            self.rule(rule)
        if "scoring" in model:
            self.blank()
            self.scoring(model["scoring"])
        for kind in ("confirmation", "notification"):
            for i, obj in enumerate(model.get(kind + "s") or []):
                self.blank()
                self.message_object(kind, obj, i)
        for lang, t in (model.get("translations") or {}).items():
            self.blank()
            self.translation(str(lang), t)
        return "\n".join(self.lines) + "\n"

    def form_header(self, model: M.Model) -> None:
        head = "form" + (" #" + model["id"] if "id" in model else "")
        self.line(0, head + " " + E.quote(model.get("title", "")))
        if "description" in model:
            self.mod(1, "description", model["description"])
        if "language" in model:
            self.mod(1, "language", model["language"])
        for k, v in (model.get("settings") or {}).items():
            self.mod(1, k, v)
        if "extensions" in model:
            self.line(1, "@extensions " + M.encode(model["extensions"]))

    def page_header(self, page: dict[str, Any], i: int) -> None:
        head = "page" + ("" if page["id"] == f"page_{i + 1}" else " #" + page["id"])
        if "title" in page:
            head += " " + E.quote(page["title"])
        self.line(0, head)
        if "description" in page:
            self.mod(1, "description", page["description"])
        if "when" in page:
            self.line(1, "@when " + page["when"])
        for k, v in (page.get("props") or {}).items():
            self.mod(1, k, v)

    def rule(self, rule: dict[str, Any]) -> None:
        self.line(0, "rule " + rule["action"] + "".join(" #" + t for t in rule["targets"]))
        if "value" in rule:
            self.line(1, "@value " + rule["value"])
        self.line(1, "@when " + rule["when"])

    def scoring(self, scoring: dict[str, Any]) -> None:
        self.line(0, "scoring")
        for k, v in scoring.items():
            if k != "outcomes":
                self.mod(1, k, v)
        for i, o in enumerate(scoring.get("outcomes") or []):
            self.line(1, "outcome" + ("" if o["id"] == f"outcome_{i + 1}" else " #" + o["id"]))
            self.line(2, "@when " + o["when"])
            self.mod(2, "message", o["message"])

    def message_object(self, kind: str, obj: dict[str, Any], i: int) -> None:
        self.line(0, kind + ("" if obj["id"] == f"{kind}_{i + 1}" else " #" + obj["id"]))
        for k in M.FIXED_NAMES[kind]:
            if k in ("id", "when", "props") or k not in obj:
                continue
            if kind == "confirmation" and k == "type" and obj["type"] == "message":
                continue
            self.mod(1, k, obj[k])
        if "when" in obj:
            self.line(1, "@when " + obj["when"])
        for k, v in (obj.get("props") or {}).items():
            self.mod(1, k, v)

    def translation(self, lang: str, t: dict[str, Any]) -> None:
        self.line(0, "translation " + E.quote(lang))
        for k in ("title", "description"):
            if k in t:
                self.mod(1, k, t[k])
        for pid, part in (t.get("pages") or {}).items():
            self.line(1, "page #" + pid)
            for k in ("title", "description"):
                if k in part:
                    self.mod(2, k, part[k])
        for fid, part in (t.get("fields") or {}).items():
            self.line(1, "field #" + fid)
            for k, spelling in (
                ("label", "label"),
                ("help", "description"),
                ("placeholder", "placeholder"),
            ):
                if k in part:
                    self.mod(2, spelling, part[k])
            for value, label in (part.get("choices") or {}).items():
                self.line(2, choice_line({"value": str(value), "label": label}))
        for key, word in (("confirmations", "confirmation"), ("outcomes", "outcome")):
            for oid, part in (t.get(key) or {}).items():
                self.line(1, f"{word} #{oid}")
                if "message" in part:
                    self.mod(2, "message", part["message"])
        for mid, text in (t.get("messages") or {}).items():
            self.line(1, f"message #{mid} {E.quote(text)}")


def is_bare_page(page: dict[str, Any], index: int) -> bool:
    return page["id"] == f"page_{index + 1}" and len(page) == 2 and "items" in page


def item_mods(item: M.Item) -> list[str]:  # noqa: C901
    out: list[str] = []
    if "required" in item:
        out.append(_mod("required", item["required"]))
    for k, spelling in (("placeholder", "placeholder"), ("help", "description")):
        if k in item:
            out.append(_mod(spelling, item[k]))
    if "default" in item:
        out.append("@default " + value_text(item["default"]))
    if "smart_default" in item:
        out.append("@smart_default " + item["smart_default"])
    if "mask" in item:
        out.append(_mod("mask", item["mask"]))
    if "when" in item:
        out.append("@when " + item["when"])
    if "calculation" in item:
        out.append("@calculate " + item["calculation"])
    if "choice_library" in item:
        out.append(_mod("library", item["choice_library"]))
    if "cascade" in item:
        c = item["cascade"]
        if "from" in c:
            out.append("@cascade_from #" + c["from"])
        for k, spelling in (
            ("library", "cascade_library"),
            ("empty_message", "empty_message"),
            ("loading_message", "loading_message"),
        ):
            if k in c:
                out.append(_mod(spelling, c[k]))
    v = item.get("validation") or {}
    spellings = (
        ("min", "min"), ("max", "max"), ("min_length", "minlength"), ("max_length", "maxlength"),
        ("pattern", "pattern"), ("message", "error_message"), ("unique", "unique"),
        ("unique_scope", "unique_scope"), ("unique_message", "unique_message"),
    )  # fmt: skip
    for k, spelling in spellings:
        if k in v:
            out.append(_mod(spelling, v[k]))
    s = item.get("scoring") or {}
    if "correct" in s:
        out.append("@correct " + M.encode(list(s["correct"])))
    for k in (
        "points",
        "partial",
        "case_sensitive",
        "feedback_correct",
        "feedback_incorrect",
        "feedback_partial",
        "explanation",
    ):
        if k in s:
            out.append(_mod(k, s[k]))
    for name, value in (item.get("attributes") or {}).items():
        out.append("@attr " + E.quote(name) + " " + value_text(value))
    for k, value in (item.get("props") or {}).items():
        out.append(_mod(k, value))
    return out


def to_bfl(model: M.Model) -> str:
    """The model as canonical BFL, ending in a newline."""
    return Writer().run(model)


def items_bfl(entries: list[M.Item], level: int = 0, counter_start: int = 0) -> list[str]:
    """Lines for some items, as the writer would put them (for splicing)."""
    w = Writer()
    w.counter = counter_start
    w.items(entries, level)
    return w.lines
