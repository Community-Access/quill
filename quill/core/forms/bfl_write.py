"""Writing the form model as BFL.

Two writers:

- :func:`to_bfl` writes a whole form in QUILL's canonical style: one
  statement per paragraph, a field's choices and then its modifiers on the
  lines under it, two spaces of indent, ``if`` blocks for conditions. It is
  written so that BAF's *current* PHP parser reads as much of it as it can
  (choices before modifiers, form settings on the form line, indented ``if``
  bodies only where BAF has no better spelling; see the report).
- :func:`write_bfl` writes a :class:`~quill.core.forms.bfl_read.BflDocument`
  back. Every statement whose model objects are unchanged is copied byte for
  byte from the original text; only edited, added or moved statements are
  regenerated. Reading a document and writing it straight back gives the
  original text exactly.
"""

from __future__ import annotations

import json
from typing import Any

from quill.core.forms import expr as E
from quill.core.forms.baf_parser import _FLAGS, _ROWS, _VALUED, sanitize_title
from quill.core.forms.bfl_parts import (
    BflDocument,
    FormHeader,
    VersionLine,
    smart_default_expression,
)
from quill.core.forms.model import Columns, Field, Form, Island, Item, Outcome, Page, Section
from quill.core.forms.model_json import _item

#: The first line of a BFL document QUILL writes: the model version.
VERSION_LINE = "// bfl-version {version}"
IND = "  "

# BAF config key -> modifier spelling, in BAF's compiler order then the rest.
_MODIFIER_FOR: dict[str, str] = {}
for _name, (_key, _kinds) in _VALUED.items():
    _MODIFIER_FOR.setdefault(_key, _name)
for _name, (_key, _value) in _FLAGS.items():
    _MODIFIER_FOR.setdefault(_key, _name)
for _name, _key in _ROWS.items():
    _MODIFIER_FOR.setdefault(_key, _name)
_NUMERIC = {key for key, kinds in _VALUED.values() if kinds == ("NUMBER",)}
_ORDER = (
    "min max min_length max_length step rows cols size css_class read_only disabled "
    "admin_only visibility confirm_email input_mask format pattern autocomplete "
    "autocomplete_provider autocomplete_countries autocomplete_types unique unique_scope "
    "unique_message multiple allow_other searchable prefix suffix autofocus spellcheck "
    "accept capture inputmode enterkeyhint min_rows max_rows custom_attributes smart_default"
).split()


def quote(text: str) -> str:
    return E.quote(text)


def _setting_lines(settings: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    keys = [k for k in _ORDER if k in settings] + sorted(
        k for k in settings if k not in _ORDER and k != "unknown_modifiers"
    )
    for key in keys:
        value = settings[key]
        if key == "visibility":
            if value == "hidden":
                lines.append("@hidden")
            continue
        if key in ("autocomplete_countries", "autocomplete_types"):
            lines.append(f"@{key} [" + ", ".join(quote(str(v)) for v in value) + "]")
        elif key == "custom_attributes":
            lines.extend(f"@attr {quote(str(n))} {quote(str(v))}" for n, v in value.items())
        elif key == "spellcheck":
            lines.append("@spellcheck " + quote("true" if value else "false"))
        elif key == "autocomplete" and value is True:
            lines.append("@autocomplete")
        elif key in ("min_rows", "max_rows", "column_count"):
            lines.append(f"@{key} {value}")
        elif key in _MODIFIER_FOR and value is True:
            lines.append("@" + _MODIFIER_FOR[key])
        elif key in _MODIFIER_FOR:
            text = str(value)
            lines.append(f"@{_MODIFIER_FOR[key]} " + (text if key in _NUMERIC else quote(text)))
        else:
            lines.append(f"@setting {quote(key)} {quote(json.dumps(value))}")
    lines.extend(str(raw) for raw in settings.get("unknown_modifiers", []))
    return lines


def _choice_line(value: str, label: str, price: str | None) -> str:
    plain = value == sanitize_title(label) and "|" not in label and ":" not in label
    if price and value == sanitize_title(label) and "|" not in label:
        return f"+ {label}:{price}"
    return f"+ {label}" if plain else f"+ {value}|{label}"


def _translation_lines(form: Form, prefix: str) -> list[str]:
    out = []
    for lang in sorted(form.translations):
        for key, text in form.translations[lang].items():
            if prefix == "" and "." in key and not key.startswith("settings."):
                continue
            if prefix and not key.startswith(prefix):
                continue
            rest = key[len(prefix) :] if prefix else key.removeprefix("settings.")
            words = " ".join(rest.split("."))
            out.append(f"@translate {lang} {words} {quote(text)}")
    return out


def field_text(item: Field, form: Form, indent: str = "") -> str:
    head = item.type
    if item.id and not _auto_id(item.id):
        head += " #" + item.id
    if item.label:
        head += " " + quote(item.label)
    body: list[str] = [_choice_line(c.value, c.label, c.price) for c in item.choices]
    if item.required:
        body.append("@required")
    if item.placeholder:
        body.append("@placeholder " + quote(item.placeholder))
    if item.help:
        body.append("@description " + quote(item.help))
    if item.default is not None:
        body.append("@default " + quote(item.default))
    if item.default_expr:
        baf = _baf_smart(item.default_expr)
        body.append("@smart_default " + (quote(baf) if baf else item.default_expr))
    if item.choice_library:
        body.append("@library " + item.choice_library)
    if item.cascade is not None:
        c = item.cascade
        body.append("@cascade_from #" + c.source if c.source else "")
        if c.library:
            body.append("@cascade_library " + c.library)
        if c.empty_message:
            body.append("@empty_message " + quote(c.empty_message))
        if c.loading_message:
            body.append("@loading_message " + quote(c.loading_message))
    body.extend(_setting_lines(dict(item.settings)))
    if item.calculate:
        body.append("@calculate " + item.calculate)
    if item.score:
        body.append("@score " + item.score)
    body.extend(
        f"@choice_score {c.value} {E.to_text(E.Num(_dec(c.score)))}"
        for c in item.choices
        if c.score is not None
    )
    body.extend(_translation_lines(form, f"field.{item.id}."))
    lines = [indent + head + (" {" if item.fields else "")]
    lines.extend(indent + IND + b for b in body if b)
    if item.fields:
        for child in item.fields:
            lines.append(field_text(child, form, indent + IND))
        lines.append(indent + "}")
    return "\n".join(lines)


def _dec(value: float) -> Any:
    from decimal import Decimal

    return Decimal(str(value))


def _auto_id(field_id: str) -> bool:
    return field_id.startswith("field_") and field_id[6:].isdigit()


def _baf_smart(expression: str) -> str | None:
    """The BAF spelling of a smart default, when BAF has one."""
    node = E.parse(expression)
    if isinstance(node, E.Today):
        return "today"
    if (
        isinstance(node, E.Arith)
        and isinstance(node.left, E.Today)
        and isinstance(node.right, E.Num)
    ):
        candidate = f"today{node.op}{E.to_text(node.right)}"
    elif isinstance(node, E.Ctx) and len(node.path) == 2 and node.path[0] in ("user", "geo"):
        candidate = f"{node.path[0]}:{node.path[1]}" if node.path != ("geo", "country") else "geo"
    else:
        return None
    return candidate if smart_default_expression(candidate) == expression else None


def header_text(form: Form) -> str:
    line = "form " + quote(form.title)
    s = form.settings
    if form.description:
        line += " @description " + quote(form.description)
    for flag in ("ajax", "honeypot"):
        if getattr(s, flag):
            line += " @" + flag
    if s.captcha:
        line += " @captcha" + (" " + quote(s.captcha_type) if s.captcha_type else "")
    extra = [f"@{k}" for k in ("save_and_continue", "rate_limit") if getattr(s, k)]
    extra += [
        f"@{k} {quote(getattr(s, k))}"
        for k in ("submit_label", "success_message", "redirect_url")
        if getattr(s, k)
    ]
    extra += _setting_lines({k: v for k, v in s.extra.items()})
    extra += _translation_lines(form, "")
    return "\n".join([line] + [IND + x for x in extra])


def page_text(page: Page, form: Form) -> str:
    line = "page" + (" " + quote(page.title) if page.title else "")
    if page.description:
        line += " @description " + quote(page.description)
    body = ["@when " + page.visible_when] if page.visible_when else []
    body += _translation_lines(form, f"page.{page.id}.")
    return "\n".join([line] + [IND + b for b in body])


def section_text(section: Section, form: Form, indent: str = "") -> str:
    body = ["@description " + quote(section.description)] if section.description else []
    if section.visible_when:
        body.append("@when " + section.visible_when)
    body += _translation_lines(form, f"section.{section.id}.")
    head = indent + "section" + (" " + quote(section.title) if section.title else "")
    return "\n".join([head] + [indent + IND + b for b in body])


def outcome_text(outcome: Outcome, number: int, form: Form) -> str:
    body = ["@when " + outcome.when] + _translation_lines(form, f"outcome.{number}.")
    return "\n".join(["outcome " + quote(outcome.message)] + [IND + b for b in body])


def _cond(obj: Any) -> str | None:
    return obj.visible_when if isinstance(obj, (Field, Columns)) else None


def item_text(obj: Any, form: Form, indent: str = "") -> str:
    """One object as BFL, without the ``if`` its condition puts round it."""
    if isinstance(obj, Field):
        return field_text(obj, form, indent)
    if isinstance(obj, Section):
        return section_text(obj, form, indent)
    if isinstance(obj, Island):
        return obj.text
    if isinstance(obj, Columns):
        lines = [indent + "columns" + (f" {obj.count}" if obj.count is not None else "")]
        for column in obj.columns:
            lines.append(indent + IND + "column")
            text = items_text(column, form, indent + IND * 2, separator="\n")
            if text:
                lines.append(text)
        return "\n".join(lines)
    if isinstance(obj, Page):
        return page_text(obj, form)
    if isinstance(obj, Outcome):
        return outcome_text(obj, form.outcomes.index(obj) + 1, form)
    if isinstance(obj, VersionLine):
        return VERSION_LINE.format(version=form.version)
    return header_text(form)


def items_text(objs: list[Any], form: Form, indent: str = "", separator: str = "\n\n") -> str:
    """Objects as BFL, putting consecutive ones that share a condition in one ``if``."""
    objs = _flat(objs)
    parts: list[str] = []
    k = 0
    while k < len(objs):
        cond = _cond(objs[k])
        if not cond:
            parts.append(item_text(objs[k], form, indent))
            k += 1
            continue
        group = []
        while k < len(objs) and _cond(objs[k]) == cond:
            group.append(objs[k])
            k += 1
        inner = [_without_cond(o) for o in group]
        body = "\n".join(item_text(o, form, indent + IND) for o in inner)
        parts.append(f"{indent}if {cond}\n{body}")
    return separator.join(parts)


def _without_cond(obj: Any) -> Any:
    from dataclasses import replace

    return replace(obj, visible_when=None)


def sequence(form: Form, doc: BflDocument | None = None) -> list[Any]:
    """The objects of a form in writing order, as top-level statements see them.

    The form line and outcomes are not inside pages, so each goes back after
    whatever came before it in the original document.
    """
    originals = {id(o) for s in doc.statements for o in s.objs} if doc else set()
    seq: list[Any] = []
    for index, page in enumerate(form.pages):
        if (
            index > 0
            or page.title
            or page.description
            or page.visible_when
            or id(page) in originals
        ):
            seq.append(page)
        seq.extend(_flat(page.items))
    floating: list[Any] = [doc.header if doc else FormHeader(), *form.outcomes]
    if doc is None:
        return floating[:1] + seq + floating[1:]
    order = [o for s in doc.statements for o in s.objs]
    position = {id(o): n for n, o in enumerate(order)}
    for obj in floating:
        if id(obj) not in position:
            seq = [obj] + seq if isinstance(obj, FormHeader) else seq + [obj]
            continue
        mine = position[id(obj)]
        at = 0
        for n, other in enumerate(seq):
            if position.get(id(other), -1) < mine and id(other) in position:
                at = n + 1
        seq.insert(at, obj)
    if doc.version is not None:
        seq.insert(0, doc.version)
    return seq


def _flat(items: list[Item]) -> list[Any]:
    out: list[Any] = []
    for item in items:
        out.append(item)
        if isinstance(item, Section):
            out.extend(_flat(item.items))
    return out


def snapshot(obj: Any, form: Form) -> str:
    """What a statement's object looks like, to tell whether it was edited."""
    if isinstance(obj, (Field, Columns, Island)):
        data: Any = _item(obj)
        prefix = f"field.{obj.id}." if isinstance(obj, Field) else ""
    elif isinstance(obj, Section):
        data = [obj.id, obj.title, obj.description, obj.visible_when]
        prefix = f"section.{obj.id}."
    elif isinstance(obj, Page):
        data = [obj.id, obj.title, obj.description, obj.visible_when]
        prefix = f"page.{obj.id}."
    elif isinstance(obj, Outcome):
        data = [obj.when, obj.message]
        prefix = "outcome."
    else:
        data = [form.title, form.description, repr(form.settings), form.language, form.version]
        prefix = "@form"
    langs = {
        lang: {
            k: v
            for k, v in strings.items()
            if (
                k.startswith(prefix)
                if prefix != "@form"
                else "." not in k or k.startswith("settings.")
            )
        }
        for lang, strings in form.translations.items()
    }
    return json.dumps([data, langs], sort_keys=True, default=str)


def _generate(run: list[Any], form: Form) -> str:
    parts: list[str] = []
    k = 0
    while k < len(run):
        obj = run[k]
        if isinstance(obj, (Field, Columns)) and obj.visible_when:
            j = k
            while (
                j < len(run)
                and isinstance(run[j], (Field, Columns))
                and run[j].visible_when == obj.visible_when
            ):
                j += 1
            parts.append(items_text(run[k:j], form))
            k = j
            continue
        parts.append(item_text(obj, form))
        k += 1
    return "\n\n".join(parts)


def write_bfl(doc: BflDocument, form: Form | None = None) -> str:
    """The document's (possibly edited) model as BFL, keeping unchanged text."""
    form = form or doc.form
    seq = sequence(form, doc)
    starts = {id(s.objs[0]): s for s in doc.statements if s.objs}
    out: list[str] = []
    k = 0
    last_verbatim = None
    while k < len(seq):
        stmt = starts.get(id(seq[k]))
        if stmt is not None and _intact(stmt, seq, k, doc, form):
            out.append(stmt.gap + doc.text[stmt.start : stmt.end])
            last_verbatim = stmt
            k += len(stmt.objs)
            continue
        run = [seq[k]]
        k += 1
        while k < len(seq) and not (
            id(seq[k]) in starts and _intact(starts[id(seq[k])], seq, k, doc, form)
        ):
            run.append(seq[k])
            k += 1
        run = [o for o in run if not (isinstance(o, FormHeader) and not _has_header(form, doc))]
        if not run:
            continue
        gap = stmt.gap if stmt is not None else ("\n\n" if out else "")
        out.append(gap + _generate(run, form))
        last_verbatim = None
    text = "".join(out)
    if doc.statements and last_verbatim is doc.statements[-1]:
        return text + doc.tail
    return text + ("\n" if doc.text.endswith("\n") or not doc.text else "")


def _has_header(form: Form, doc: BflDocument) -> bool:
    if any(isinstance(o, FormHeader) for s in doc.statements for o in s.objs):
        return True
    return bool(
        form.title
        or form.description
        or form.settings != type(form.settings)()
        or _translation_lines(form, "")
    )


def _intact(stmt: Any, seq: list[Any], k: int, doc: BflDocument, form: Form) -> bool:
    objs = stmt.objs
    if [id(o) for o in seq[k : k + len(objs)]] != [id(o) for o in objs]:
        return False
    return all(doc.snapshots.get(id(o)) == snapshot(o, form) for o in objs)


def to_bfl(form: Form, *, version_line: bool = True) -> str:
    """A whole form in QUILL's canonical BFL style."""
    seq = sequence(form)
    if not (
        form.title
        or form.description
        or _translation_lines(form, "")
        or form.settings != type(form.settings)()
    ):
        seq = seq[1:]
    text = _generate(seq, form)
    if version_line:
        text = VERSION_LINE.format(version=form.version) + "\n" + text
    return text + "\n"
