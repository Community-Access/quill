"""Accessible HTML form controls, whole rather than one tag at a time.

Offering `<select>` on its own is offering the easy half. A dropdown that a
screen reader can actually use is four things at once -- a ``<label>``, a
``for`` that matches the field's ``id``, the field, and its ``<option>``s -- and
the only one of the four you can *see* is the one this editor was already able
to insert. The other three are invisible in exactly the way that makes them get
forgotten: a missing ``for`` looks identical on screen to a present one, and the
page looks finished right up until somebody tabs into an unlabelled edit box.

So this module inserts the whole control. Every snippet here ships:

* a **label bound by ``for``/``id``**, with matching values generated together
  so they cannot drift apart;
* an **``id`` that is not already used in the document** -- taken ids are read
  off the buffer first, because two fields sharing one id is the commonest way
  a form that was accessible when it was written stops being so when it is
  copied;
* a ``name``, so the field actually submits;
* and the **structure the control needs to mean anything**: options inside a
  select, a legend inside a fieldset, a shared ``name`` across a radio group.

The radio group is the clearest case for doing it this way. Radios are the one
control where getting it wrong is silent in both directions: without a shared
``name`` they are not a group and every one of them can be on at once; without a
``fieldset``/``legend`` they are a group with no name, and a reader announces
each option with no idea what question it answers. That is four elements and two
attributes with no visible evidence of any of it, which is not something to ask
somebody to remember at the moment they are trying to write a form.

Pure and wx-free. The picker
(:meth:`~quill.apps.lite_window_markup.DocumentMarkupMixin.cmd_insert_html_tag`)
offers these alongside the plain tags, so "checkbox" finds both the bare
``<input>`` and the labelled one, and the labelled one is what most people mean.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from quill.core.tagging import InsertionResult

__all__ = [
    "FORM_SNIPPETS",
    "FORM_SNIPPET_ALIASES",
    "FormSnippet",
    "build_form_snippet",
    "form_snippet_names",
    "is_form_snippet",
    "next_free_id",
]

#: How a form snippet is named in the picker. The prefix is load-bearing: the
#: list holds plain tags too, and "Form field: dropdown" next to "select" tells
#: you which of the two you are about to get before you press Enter.
_PREFIX = "Form field: "

_ID_IN_TEXT = re.compile(r'\bid\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class FormSnippet:
    """One insertable control: how to build it, and what to call its id.

    ``template`` is formatted with ``label``, ``id`` and ``name``. ``stem`` is
    the base the generated id is built from, so a page of fields reads as
    ``email``, ``message``, ``country`` rather than ``field-1``, ``field-2`` --
    an id is the handle somebody later writes CSS and tests against, and a
    numbered one tells them nothing.
    """

    stem: str
    label: str
    template: str


def _field(kind: str, stem: str, label: str, *, extra: str = "") -> FormSnippet:
    """A labelled ``<input>`` of one type -- the shape most of these share."""
    return FormSnippet(
        stem,
        label,
        '<label for="{id}">{label}</label>\n'
        f'<input type="{kind}" id="{{id}}" name="{{name}}"{extra}>',
    )


#: Every control the picker offers whole, keyed by the name it shows.
FORM_SNIPPETS: dict[str, FormSnippet] = {
    f"{_PREFIX}text": _field("text", "your-name", "Your name"),
    f"{_PREFIX}email": _field("email", "email", "Email address", extra=' autocomplete="email"'),
    f"{_PREFIX}password": _field(
        "password", "password", "Password", extra=' autocomplete="current-password"'
    ),
    f"{_PREFIX}telephone": _field("tel", "phone", "Telephone", extra=' autocomplete="tel"'),
    f"{_PREFIX}web address": _field("url", "website", "Website"),
    f"{_PREFIX}number": _field("number", "quantity", "How many"),
    f"{_PREFIX}date": _field("date", "date", "Date"),
    f"{_PREFIX}search": _field("search", "search", "Search"),
    f"{_PREFIX}file upload": _field("file", "upload", "Choose a file"),
    f"{_PREFIX}long answer (textarea)": FormSnippet(
        "message",
        "Your message",
        '<label for="{id}">{label}</label>\n<textarea id="{id}" name="{name}" rows="5"></textarea>',
    ),
    f"{_PREFIX}dropdown (select)": FormSnippet(
        "country",
        "Country",
        # An empty first option, selected, so the control does not silently
        # submit whatever happened to be first. A dropdown whose default is a
        # real answer is a dropdown that collects answers nobody gave.
        '<label for="{id}">{label}</label>\n'
        '<select id="{id}" name="{name}">\n'
        '  <option value="">Choose one</option>\n'
        '  <option value="first">First choice</option>\n'
        '  <option value="second">Second choice</option>\n'
        "</select>",
    ),
    f"{_PREFIX}dropdown with groups": FormSnippet(
        "choice",
        "Choose",
        '<label for="{id}">{label}</label>\n'
        '<select id="{id}" name="{name}">\n'
        '  <option value="">Choose one</option>\n'
        '  <optgroup label="First group">\n'
        '    <option value="a">Option A</option>\n'
        '    <option value="b">Option B</option>\n'
        "  </optgroup>\n"
        '  <optgroup label="Second group">\n'
        '    <option value="c">Option C</option>\n'
        "  </optgroup>\n"
        "</select>",
    ),
    f"{_PREFIX}checkbox": FormSnippet(
        "agree",
        "I agree to the terms",
        # The label *after* the box, which is the visual convention for a
        # checkbox and the only one where "for" is doing real work: the box is
        # tiny, and the label is the rest of the click target.
        '<input type="checkbox" id="{id}" name="{name}" value="yes">\n'
        '<label for="{id}">{label}</label>',
    ),
    f"{_PREFIX}checkbox group": FormSnippet(
        "topics",
        "Which topics interest you?",
        "<fieldset>\n"
        "  <legend>{label}</legend>\n"
        '  <input type="checkbox" id="{id}-1" name="{name}" value="first">\n'
        '  <label for="{id}-1">First topic</label>\n'
        '  <input type="checkbox" id="{id}-2" name="{name}" value="second">\n'
        '  <label for="{id}-2">Second topic</label>\n'
        "</fieldset>",
    ),
    f"{_PREFIX}radio group": FormSnippet(
        "choice",
        "Pick one",
        # The one control where getting it wrong is silent in both directions:
        # no shared name and they are not a group at all; no fieldset and legend
        # and the group has no name, so a reader announces three options and
        # never the question they answer.
        "<fieldset>\n"
        "  <legend>{label}</legend>\n"
        '  <input type="radio" id="{id}-1" name="{name}" value="first" checked>\n'
        '  <label for="{id}-1">First choice</label>\n'
        '  <input type="radio" id="{id}-2" name="{name}" value="second">\n'
        '  <label for="{id}-2">Second choice</label>\n'
        '  <input type="radio" id="{id}-3" name="{name}" value="third">\n'
        '  <label for="{id}-3">Third choice</label>\n'
        "</fieldset>",
    ),
    f"{_PREFIX}autocomplete (input + datalist)": FormSnippet(
        "fruit",
        "Start typing",
        '<label for="{id}">{label}</label>\n'
        '<input type="text" id="{id}" name="{name}" list="{id}-options">\n'
        '<datalist id="{id}-options">\n'
        '  <option value="First suggestion">\n'
        '  <option value="Second suggestion">\n'
        "</datalist>",
    ),
    f"{_PREFIX}required, with hint and error": FormSnippet(
        "email",
        "Email address",
        # aria-describedby carries the hint *and* the error, in that order, and
        # the order is what a reader says. aria-invalid is what turns a
        # paragraph of red text into a state the reader reports.
        '<label for="{id}">{label}</label>\n'
        '<p id="{id}-hint">We will only use this to reply to you.</p>\n'
        '<input type="email" id="{id}" name="{name}" required\n'
        '       aria-describedby="{id}-hint {id}-error" aria-invalid="false">\n'
        '<p id="{id}-error" role="alert"></p>',
    ),
    f"{_PREFIX}submit button": FormSnippet(
        "submit",
        "Send",
        # A button element with real text, not <input type="submit" value>: the
        # text is then content a translator and a reader both handle normally.
        '<button type="submit">{label}</button>',
    ),
    f"{_PREFIX}whole form": FormSnippet(
        "contact",
        "Contact us",
        '<form action="#" method="post">\n'
        "  <fieldset>\n"
        "    <legend>{label}</legend>\n"
        '    <label for="{id}-name">Your name</label>\n'
        '    <input type="text" id="{id}-name" name="name" autocomplete="name" required>\n'
        '    <label for="{id}-email">Email address</label>\n'
        '    <input type="email" id="{id}-email" name="email" autocomplete="email" required>\n'
        '    <label for="{id}-message">Your message</label>\n'
        '    <textarea id="{id}-message" name="message" rows="5"></textarea>\n'
        "  </fieldset>\n"
        '  <button type="submit">Send</button>\n'
        "</form>",
    ),
    f"{_PREFIX}grouped fields (fieldset)": FormSnippet(
        "group",
        "Group name",
        "<fieldset>\n  <legend>{label}</legend>\n  \n</fieldset>",
    ),
}

#: The words people reach for, which are rarely the words in the name. Merged
#: into the HTML picker's own alias table, so one search box finds both a bare
#: ``<select>`` and the labelled dropdown, and the labelled one ranks alongside.
FORM_SNIPPET_ALIASES: dict[str, tuple[str, ...]] = {
    f"{_PREFIX}text": ("textbox", "input", "field", "name", "single line"),
    f"{_PREFIX}email": ("mail", "address", "input"),
    f"{_PREFIX}password": ("secret", "login", "sign in"),
    f"{_PREFIX}telephone": ("phone", "tel", "mobile", "number"),
    f"{_PREFIX}web address": ("url", "link", "website", "homepage"),
    f"{_PREFIX}number": ("numeric", "quantity", "amount", "spinner"),
    f"{_PREFIX}date": ("calendar", "day", "birthday", "when"),
    f"{_PREFIX}search": ("find", "query", "search box"),
    f"{_PREFIX}file upload": ("attach", "browse", "picture", "document"),
    f"{_PREFIX}long answer (textarea)": ("textarea", "multiline", "comments", "message", "notes"),
    f"{_PREFIX}dropdown (select)": ("select", "combo", "combobox", "list", "picker", "options"),
    f"{_PREFIX}dropdown with groups": ("optgroup", "select", "grouped", "categories"),
    f"{_PREFIX}checkbox": ("tick", "check", "toggle", "agree", "opt in"),
    f"{_PREFIX}checkbox group": ("checkboxes", "multiple", "several", "fieldset"),
    f"{_PREFIX}radio group": ("radio", "radios", "one of", "choice", "options", "fieldset"),
    f"{_PREFIX}autocomplete (input + datalist)": (
        "datalist",
        "suggestions",
        "typeahead",
        "completion",
        "combobox",
    ),
    f"{_PREFIX}required, with hint and error": (
        "validation",
        "error message",
        "aria-describedby",
        "aria-invalid",
        "hint",
        "help text",
        "required",
    ),
    f"{_PREFIX}submit button": ("submit", "send", "go", "button"),
    f"{_PREFIX}whole form": ("form", "contact form", "skeleton", "template", "everything"),
    f"{_PREFIX}grouped fields (fieldset)": ("fieldset", "legend", "group", "section"),
}


def form_snippet_names() -> list[str]:
    """Every snippet's name, in the order the picker should show them."""
    return list(FORM_SNIPPETS)


def is_form_snippet(name: str) -> bool:
    """Whether *name* is one of these rather than a plain tag name."""
    return str(name) in FORM_SNIPPETS


def _slug(text: str) -> str:
    """*text* as an id fragment: lower case, words joined by hyphens.

    Empty when there is nothing usable, so the caller falls back to the
    snippet's own stem rather than emitting ``id=""`` -- an empty id is worse
    than a generic one, because ``for=""`` matches nothing at all.
    """
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", str(text or "")).strip("-").lower()
    return cleaned[:40].strip("-")


def next_free_id(stem: str, document_text: str) -> str:
    """*stem*, or ``stem-2``, ``stem-3``... -- whichever is not taken yet.

    Ids already in the buffer are read off it first. **Two fields sharing one
    id is the commonest way a form that was accessible when it was written stops
    being so when it is copied**, and it is completely invisible: the page looks
    right, the second label points at the first field, and the only symptom is
    that clicking one label focuses the wrong box.

    The check covers the suffixed ids a snippet derives too (``{id}-1``,
    ``{id}-hint``), so a radio group inserted twice does not collide on its
    children while its parent looks free.
    """
    taken = {match.group(1).lower() for match in _ID_IN_TEXT.finditer(document_text or "")}
    base = _slug(stem) or "field"

    def free(candidate: str) -> bool:
        prefix = f"{candidate}-"
        return not any(existing == candidate or existing.startswith(prefix) for existing in taken)

    if free(base):
        return base
    for suffix in range(2, 1000):
        candidate = f"{base}-{suffix}"
        if free(candidate):
            return candidate
    return f"{base}-{len(taken) + 1}"


def build_form_snippet(
    name: str, selected_text: str = "", document_text: str = ""
) -> InsertionResult:
    """Build *name*'s control, labelled, wired and with an id nobody else has.

    ``selected_text`` becomes the label when there is one -- selecting "Postcode"
    and inserting a text field gives you a Postcode field, which is the fastest
    way to write a form -- and the id is derived from it so the two agree. That
    derivation is the point of doing it here rather than at the call site: a
    label and a ``for`` written in two places are a label and a ``for`` that
    drift the first time somebody edits one of them.

    The caret lands at the end. These are multi-line insertions with several
    places worth editing, and a caret parked in one of them would be a guess
    about which; the end is the one position that is never wrong.
    """
    snippet = FORM_SNIPPETS.get(str(name))
    if snippet is None:
        return InsertionResult("", 0)
    label = str(selected_text or "").strip().splitlines()[0:1]
    label_text = label[0] if label else snippet.label
    identifier = next_free_id(_slug(label_text) or snippet.stem, document_text)
    text = snippet.template.format(
        label=label_text,
        id=identifier,
        # The name is the id's base: a submitted field whose key matches its
        # anchor is one fewer thing to hold in your head, and the suffixed ids
        # inside a group deliberately share one name because that is what makes
        # them a group.
        name=identifier,
    )
    return InsertionResult(inserted_text=text, caret_offset=len(text))
