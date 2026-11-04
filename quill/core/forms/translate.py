"""Translations: one form, several languages, side by side.

The shape is BAF's (``docs/form-model.md``, "Translations")::

    "translations": { "es": {
        "title": "...", "description": "...",
        "pages":  { "page_1": { "title": "...", "description": "..." } },
        "fields": { "type": { "label": "...", "help": "...", "placeholder": "...",
                              "choices": { "person": "..." } } },
        "confirmations": { "thanks": { "message": "..." } },
        "outcomes": { "pass": { "message": "..." } },
        "messages": { "required": "..." } } }

A missing translation falls back to the form's own text. Here are the table a
translator works through (:func:`translatable_strings`), what is still
missing in a language, and the form as it reads in one language
(:func:`localize`, which Fill It In Yourself uses).
"""

from __future__ import annotations

import copy
from typing import Any

from quill.core.forms import model as M

#: A place in a translation: (part, id, key), e.g. ("fields", "type", "label");
#: ("", "", "title") for the form; ("fields", "type", "choices/person") for a choice.
Place = tuple[str, str, str]


def translatable_strings(model: M.Model) -> list[tuple[Place, str]]:
    """Every text a translator could translate, in form order, with its source text."""
    out: list[tuple[Place, str]] = []
    for key in ("title", "description"):
        if model.get(key):
            out.append((("", "", key), model[key]))
    for page in model.get("pages") or []:
        for key in ("title", "description"):
            if page.get(key):
                out.append((("pages", page["id"], key), page[key]))
        for item in _walk(page.get("items") or []):
            for key in ("label", "help", "placeholder"):
                if item.get(key):
                    out.append((("fields", item["id"], key), item[key]))
            for c in item.get("choices") or []:
                out.append((("fields", item["id"], "choices/" + c["value"]), c["label"]))
    for c in model.get("confirmations") or []:
        if c.get("message"):
            out.append((("confirmations", c["id"], "message"), c["message"]))
    for o in (model.get("scoring") or {}).get("outcomes") or []:
        if o.get("message"):
            out.append((("outcomes", o["id"], "message"), o["message"]))
    return out


def _walk(entries: list[M.Item]) -> list[M.Item]:
    out: list[M.Item] = []
    for item in entries:
        out.append(item)
        if item.get("type") == "columns":
            for col in item.get("columns") or []:
                out.extend(_walk(col.get("items") or []))
        else:
            out.extend(_walk(item.get("items") or []))
    return out


def lookup(model: M.Model, language: str, place: Place) -> str | None:
    t = (model.get("translations") or {}).get(language) or {}
    part, ident, key = place
    if not part:
        value = t.get(key)
    else:
        entry = (t.get(part) or {}).get(ident) or {}
        if key.startswith("choices/"):
            value = (entry.get("choices") or {}).get(key[8:])
        else:
            value = entry.get(key)
    return value if isinstance(value, str) else None


def set_translation(model: M.Model, language: str, place: Place, text: str) -> None:
    t = model.setdefault("translations", {}).setdefault(language, {})
    part, ident, key = place
    if not part:
        t[key] = text
        return
    entry = t.setdefault(part, {}).setdefault(ident, {})
    if key.startswith("choices/"):
        entry.setdefault("choices", {})[key[8:]] = text
    else:
        entry[key] = text


def missing(model: M.Model, language: str) -> list[Place]:
    return [
        place
        for place, _text in translatable_strings(model)
        if lookup(model, language, place) is None
    ]


def languages(model: M.Model) -> list[str]:
    own = model.get("language", "en")
    return [own] + sorted(k for k in (model.get("translations") or {}) if k != own)


def localize(model: M.Model, language: str) -> M.Model:
    """A copy of the form in ``language``, falling back to its own text."""
    out = copy.deepcopy(model)
    if language == model.get("language", "en") or language not in (model.get("translations") or {}):
        return out
    out["language"] = language

    def tr(place: Place, current: Any) -> Any:
        found = lookup(model, language, place)
        return current if found is None else found

    for key in ("title", "description"):
        if key in out:
            out[key] = tr(("", "", key), out[key])
    for page in out.get("pages") or []:
        for key in ("title", "description"):
            if key in page:
                page[key] = tr(("pages", page["id"], key), page[key])
        for item in _walk(page.get("items") or []):
            for key in ("label", "help", "placeholder"):
                if key in item:
                    item[key] = tr(("fields", item["id"], key), item[key])
            for c in item.get("choices") or []:
                c["label"] = tr(("fields", item["id"], "choices/" + c["value"]), c["label"])
    for c in out.get("confirmations") or []:
        if "message" in c:
            c["message"] = tr(("confirmations", c["id"], "message"), c["message"])
    for o in (out.get("scoring") or {}).get("outcomes") or []:
        if "message" in o:
            o["message"] = tr(("outcomes", o["id"], "message"), o["message"])
    return out
