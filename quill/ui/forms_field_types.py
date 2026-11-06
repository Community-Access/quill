"""Insert Field's list: every field type the core knows, with a line about each (17a.4.2).

wx-free, and generated from :data:`quill.core.forms.model.FIELD_TYPES` and
``TYPE_NAMES``, so a type the core learns is in the list the day it lands.
The descriptions are written for the common types; any other type gets a
plain sentence from its spoken name rather than nothing. Section and Page
Break come first, beside the questions, as 17a.4.2 asks.
"""

from __future__ import annotations

from quill.core.forms import model as M

SECTION = "section"
PAGE_BREAK = "page_break"

#: One line per type: what a visitor meets.
DESCRIPTIONS: dict[str, str] = {
    SECTION: "A heading for the questions under it.",
    PAGE_BREAK: "Start a new page here.",
    "text": "One line of text, such as a name.",
    "textarea": "Several lines of text, such as a message.",
    "number": "A number, with an optional smallest and largest.",
    "email": "An email address, checked as it is typed.",
    "phone": "A phone number.",
    "website": "A web address.",
    "hidden": "A value sent with the form that visitors never see.",
    "password": "Text that is not shown as it is typed.",
    "currency": "An amount of money.",
    "toggle": "One switch: on or off.",
    "select": "Choose one from a drop-down list.",
    "multiselect": "Choose several from a list.",
    "radio": "Choose one from a group of buttons.",
    "checkbox": "Check as many as apply.",
    "consent": "One check box to agree to something.",
    "likert": "How much they agree, on a scale, for each statement.",
    "matrix": "A grid: the same choices for several questions.",
    "ranking": "Put the choices in order.",
    "rating": "A score out of five.",
    "nps": "How likely they are to recommend, from 0 to 10.",
    "quiz": "A question with a right answer, for scoring.",
    "date": "A date.",
    "time": "A time of day.",
    "datetime": "A date and a time.",
    "daterange": "A first and last date.",
    "name": "A person's name, in parts.",
    "address": "A postal address, in parts.",
    "fileupload": "A file they send with the form.",
    "signature": "A signature.",
    "calculation": "A number worked out from other answers.",
    "repeater": "A group of questions they can fill in more than once.",
    "payment": "Stripe or PayPal checkout on a compatible WordPress site; starts in test mode.",
    "html": "Text or information shown on the form, not a question.",
}

#: Advanced commerce components can be authored in source; buttons and post
#: fields remain the site's to place. Payment uses its dedicated guided dialog.
LEFT_OUT: frozenset[str] = frozenset({
    "product", "quantity", "price", "total", "coupon", "submit", "save",
    "post_title", "post_content", "post_excerpt", "post_category", "post_tags", "post_image",
    "post_custom", "user_login", "user_email", "user_password", "captcha", "social",
})  # fmt: skip


def kinds() -> list[str]:
    """Section, Page Break, then every insertable field type in the core's order."""
    return [SECTION, PAGE_BREAK] + [t for t in M.FIELD_TYPES if t not in LEFT_OUT]


def spoken(kind: str) -> str:
    if kind == PAGE_BREAK:
        return "Page break"
    name = M.TYPE_NAMES.get(kind, kind.replace("_", " "))
    return name[:1].upper() + name[1:]


def describe(kind: str) -> str:
    return DESCRIPTIONS.get(kind, f"A {spoken(kind).lower()} question.")


def row(kind: str) -> str:
    """ "Email: An email address, checked as it is typed." """
    return f"{spoken(kind)}: {describe(kind)}"


def matches(query: str, kind: str) -> bool:
    """Every word of *query* is in the type's row or its name."""
    text = f"{row(kind)} {kind}".lower()
    return all(word in text for word in query.lower().split())


def takes_choices(kind: str) -> bool:
    return kind in M.CHOICE_TYPES or kind in M.OPTIONAL_CHOICE_TYPES
