"""Translations: one form, several languages, side by side (17a.15, point 5).

A form's own language is ``form.language``. Every other language is a table
in ``form.translations`` from a *translation key* to its text. The keys name
what they translate, so a translator's table reads in form order:

====================================  ===================================
``title``, ``description``            the form
``settings.submit_label``             the submit button
``settings.success_message``          the thank-you message
``page.<id>.title`` / ``.description``  a page
``section.<id>.title`` / ``.description``  a section
``field.<id>.label`` / ``.help`` / ``.placeholder``  a question
``field.<id>.choice.<value>``         one choice's label
``outcome.<n>.message``               a quiz or survey outcome (from 1)
====================================  ===================================

In BFL a translation is ``@translate fr label "Courriel"`` under the field
(``@translate fr choice email "Par courriel"`` for a choice), or on the form,
page and section lines.
"""

from __future__ import annotations

import copy

from quill.core.forms.model import Columns, Field, Form, Item, Section


def translatable_strings(form: Form) -> list[tuple[str, str]]:
    """(key, text in the form's own language), in form order, skipping empty text."""
    out: list[tuple[str, str]] = [("title", form.title), ("description", form.description)]
    out += [
        ("settings.submit_label", form.settings.submit_label),
        ("settings.success_message", form.settings.success_message),
    ]
    for page in form.pages:
        out += [
            (f"page.{page.id}.title", page.title),
            (f"page.{page.id}.description", page.description),
        ]
        out += _items(page.items)
    out += [(f"outcome.{n}.message", o.message) for n, o in enumerate(form.outcomes, 1)]
    return [(k, v) for k, v in out if v]


def _items(items: list[Item]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for item in items:
        if isinstance(item, Section):
            out += [
                (f"section.{item.id}.title", item.title),
                (f"section.{item.id}.description", item.description),
            ]
            out += _items(item.items)
        elif isinstance(item, Columns):
            for column in item.columns:
                out += _items(column)
        elif isinstance(item, Field):
            base = f"field.{item.id}."
            out += [
                (base + "label", item.label),
                (base + "help", item.help),
                (base + "placeholder", item.placeholder),
            ]
            out += [(f"{base}choice.{c.value}", c.label) for c in item.choices]
            out += _items(list(item.fields))
    return out


def missing(form: Form, language: str) -> list[str]:
    """The keys with text in the form's language but none yet in ``language``."""
    have = form.translations.get(language, {})
    return [key for key, _text in translatable_strings(form) if key not in have]


def languages(form: Form) -> list[str]:
    """The form's own language first, then the others it is translated into."""
    return [form.language] + sorted(lang for lang in form.translations if lang != form.language)


def localize(form: Form, language: str) -> Form:
    """A copy of the form in ``language``: each text translated where a translation exists.

    Fill It In Yourself runs this to let a person try the form in each
    language. Text with no translation stays in the form's own language.
    """
    if language == form.language:
        return copy.deepcopy(form)
    table = form.translations.get(language, {})
    out = copy.deepcopy(form)
    out.language = language
    out.title = table.get("title", out.title)
    out.description = table.get("description", out.description)
    s = out.settings
    s.submit_label = table.get("settings.submit_label", s.submit_label)
    s.success_message = table.get("settings.success_message", s.success_message)
    for page in out.pages:
        page.title = table.get(f"page.{page.id}.title", page.title)
        page.description = table.get(f"page.{page.id}.description", page.description)
        _localize(page.items, table)
    for n, outcome in enumerate(out.outcomes, 1):
        outcome.message = table.get(f"outcome.{n}.message", outcome.message)
    return out


def _localize(items: list[Item], table: dict[str, str]) -> None:
    for item in items:
        if isinstance(item, Section):
            item.title = table.get(f"section.{item.id}.title", item.title)
            item.description = table.get(f"section.{item.id}.description", item.description)
            _localize(item.items, table)
        elif isinstance(item, Columns):
            for column in item.columns:
                _localize(column, table)
        elif isinstance(item, Field):
            base = f"field.{item.id}."
            item.label = table.get(base + "label", item.label)
            item.help = table.get(base + "help", item.help)
            item.placeholder = table.get(base + "placeholder", item.placeholder)
            for c in item.choices:
                c.label = table.get(f"{base}choice.{c.value}", c.label)
            _localize(list(item.fields), table)
