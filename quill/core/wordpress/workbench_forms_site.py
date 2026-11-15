"""QUILL Accessible Forms on the site, completed in the Workbench (Package 13, wordpress.md 17a).

What 9.18's checklist had left, each through the plugin's own routes (read
from its controller, ``includes/api/class-qaf-rest-api.php``):

- **Change Form Status**: ``POST {ns}/forms/{id}`` with ``status`` -- draft,
  active (taking responses) or inactive (closed);
- **Delete Form**: ``DELETE {ns}/forms/{id}``, which the plugin carries out
  with every response, note and upload of the form, so the preview gives the
  count and the person confirms by the form's name;
- **Form Settings**: the form's ``settings`` (button text, validation,
  security, scheduling, entry limits...) read as lines, and one scalar
  changed after a preview, sent as the whole ``settings`` object;
- **Star** and **Mark Read** on a QAF response: ``POST {ns}/entries/{id}``
  with ``is_starred`` or ``is_read`` alone (unlike Gravity Forms, QAF changes
  only what it is sent);
- **Saved Views**: ``GET {ns}/views``;
- **Search Responses on the Site**: ``entries?form_id=&search=``.

Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_rows import WbRow

__all__ = [
    "FORM_STATUSES",
    "delete_preview",
    "flag_body",
    "namespace_of",
    "setting_lines",
    "setting_value",
    "settings_body",
    "status_preview",
    "view_lines",
]

FORM_STATUSES: dict[str, str] = {
    "draft": "a draft, not shown to visitors",
    "active": "open, taking responses",
    "inactive": "closed, shown but not taking responses",
}
"""QAF's form statuses (the ``forms`` route's enum on the live index), as said."""


def namespace_of(row: WbRow) -> str:
    """``qaf/v1`` or ``baf/v1``, from the row's own route."""
    return row.route.split("/forms/")[0].split("/entries/")[0]


def status_preview(title: str, old: str, new: str, site: str) -> list[str]:
    if new not in FORM_STATUSES:
        raise WordPressApiError(f"QUILL Accessible Forms has no form status called {new}.")
    lines = [
        f"{title} on {site}: {FORM_STATUSES.get(old, old or 'no status')} becomes "
        f"{FORM_STATUSES[new]}."
    ]
    if new != "active":
        lines.append("Anyone who opens a page with it can no longer send a response.")
    else:
        lines.append("Anyone who opens a page with it can send a response from now on.")
    lines.append("Its questions and past responses are not changed.")
    return lines


def delete_preview(title: str, responses: int, site: str) -> list[str]:
    return [
        f"{title} is deleted from {site}, for good: the plugin keeps no Trash for forms.",
        f"Its {responses} response{'s' if responses != 1 else ''}, their notes and uploaded "
        "files are deleted with it.",
        "Pages that show it will show nothing in its place. Export the responses first "
        "(Tools > Forms > Responses) if you need them.",
        f"To go ahead, you will type the form's name, {title}, exactly.",
    ]


def flag_body(flag: str, on: bool) -> dict[str, bool]:
    if flag not in ("is_starred", "is_read"):
        raise ValueError(f"{flag} is not a flag QUILL sets.")
    return {flag: on}


def set_entry_flag(api: Any, route: str, flag: str, on: bool) -> bool:
    """Set one flag on a QAF response and return what it was; only that flag is sent."""
    current = api.get(route)
    if not isinstance(current, Mapping) or not current.get("id"):
        raise WordPressApiError("QUILL Accessible Forms did not return this response.")
    was = bool(current.get(flag))
    api.post(route, flag_body(flag, on))
    return was


# -- settings -----------------------------------------------------------------------


def setting_lines(settings: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Each scalar setting as (key, value in words); lists and objects are left to wp-admin."""
    lines = []
    for key, value in settings.items():
        if isinstance(value, bool):
            lines.append((key, "on" if value else "off"))
        elif isinstance(value, (str, int, float)):
            lines.append((key, str(value) if str(value) != "" else "not set"))
    return lines


def setting_value(old: Any, typed: str) -> Any:
    """*typed* in *old*'s type: on/off for a switch, a whole number for a count."""
    text = typed.strip()
    if isinstance(old, bool):
        if text.lower() not in ("on", "off", "yes", "no", "true", "false"):
            raise WordPressApiError("This setting is on or off.")
        return text.lower() in ("on", "yes", "true")
    if isinstance(old, int):
        if not text.lstrip("-").isdigit():
            raise WordPressApiError("This setting is a whole number.")
        return int(text)
    return text


def settings_body(settings: Mapping[str, Any], key: str, value: Any) -> dict[str, Any]:
    """The whole ``settings`` object with one key changed, as the plugin replaces it whole."""
    if key not in settings:
        raise WordPressApiError(f"The form has no setting called {key}.")
    return {"settings": {**dict(settings), key: value}}


def settings_preview(title: str, key: str, old: Any, new: Any, site: str) -> list[str]:
    def said(value: Any) -> str:
        return ("on" if value else "off") if isinstance(value, bool) else (str(value) or "not set")

    return [
        f"{title} on {site}: {key.replace('_', ' ')} is {said(old)} and becomes {said(new)}.",
        "Every other setting is sent back as it is. Visitors see the change at once.",
    ]


# -- views -----------------------------------------------------------------------------


def view_lines(views: Any, forms: Mapping[str, str]) -> list[str]:
    """``views`` as one line each: its name, form, kind and status."""
    lines = []
    for view in views if isinstance(views, list) else []:
        if not isinstance(view, Mapping):
            continue
        form = forms.get(str(view.get("form_id", "")), f"form {view.get('form_id', '')}")
        lines.append(
            f"{view.get('title') or view.get('slug') or 'A view'}: {view.get('view_type', 'list')} "
            f"view of {form}, {view.get('status', 'draft')}"
        )
    return lines or ["This site has no saved views of its responses."]
