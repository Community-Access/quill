"""Gravity Forms beyond its forms and entries, through its REST API v2 (complete.md 10B.3).

What :mod:`quill.core.wordpress.workbench_forms` does not: a form's add-on
feeds, an entry's notes and its starred and read flags, resending an entry's
notifications, quiz, poll and survey results, the form's own field filters,
and a test submission. Every call is on the connected site's ``gf/v2``
routes, exactly as Gravity Forms documents them:

- **Feeds:** ``GET gf/v2/feeds?form_ids[]=`` (``gf/v2/forms/{id}/feeds`` when
  a site's version has no top-level route), ``PUT gf/v2/feeds/{id}`` with the
  whole feed changed only in ``is_active`` or ``meta.feedName`` (Gravity Forms
  replaces a feed, so a partial body would wipe its settings), and
  ``DELETE gf/v2/feeds/{id}``.
- **Notes and flags:** ``GET`` and ``POST gf/v2/entries/{id}/notes``; the
  entry's ``is_starred`` and ``is_read`` sent as the whole entry, re-read just
  before, by ``PUT gf/v2/entries/{id}``.
- **Notifications:** the form's ``notifications`` (``GET gf/v2/forms/{id}``)
  with their recipients worked out against the entry, then ``POST
  gf/v2/entries/{id}/notifications?_notifications=a,b``.
- **Results:** ``GET gf/v2/forms/{id}/results`` for forms with quiz, poll or
  survey fields, as one row per answer and a sentence per question.
- **Field filters:** ``GET gf/v2/forms/{id}/field-filters``, for the Filter Builder.
- **Test submission:** in :mod:`quill.core.wordpress.workbench_gravity_submit`.

Entries are personal data: nothing here logs a value. Wx-free.
"""

from __future__ import annotations

import html
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.site import friendly_date
from quill.core.wordpress.workbench_forms import GRAVITY_NAMESPACE
from quill.core.wordpress.workbench_rows import WbRow

if TYPE_CHECKING:
    from quill.core.wordpress.workbench_load import SiteContext

__all__ = [
    "CAPABILITIES",
    "NS",
    "FieldFilter",
    "Note",
    "Notification",
    "add_note",
    "addon_name",
    "entry_notifications",
    "feed_body",
    "feed_name",
    "field_filters",
    "gravity_can",
    "gravity_forms",
    "load_feeds",
    "load_results",
    "note_lines",
    "read_notes",
    "resend_notifications",
    "result_rows",
    "set_entry_flag",
    "truthy",
]

NS = GRAVITY_NAMESPACE
_MAX_FORMS = 30
_RESULT_TYPES = frozenset({"poll", "quiz", "survey"})
_ADDONS = {
    "gravityformsmailchimp": "Mailchimp",
    "gravityformsstripe": "Stripe",
    "gravityformszapier": "Zapier",
    "gravityformspaypal": "PayPal Standard",
    "gravityformsppcp": "PayPal Checkout",
    "gravityformsuserregistration": "User Registration",
    "gravityformsactivecampaign": "ActiveCampaign",
    "gravityformsaweber": "AWeber",
    "gravityformscampaignmonitor": "Campaign Monitor",
    "gravityformsconstantcontact": "Constant Contact",
    "gravityformshubspot": "HubSpot",
    "gravityformsslack": "Slack",
    "gravityformstwilio": "Twilio",
    "gravityformswebhooks": "Webhooks",
    "gravityformsadvancedpostcreation": "Advanced Post Creation",
    "gravityformssquare": "Square",
    "gravityformsauthorizenet": "Authorize.Net",
    "gravityformsdropbox": "Dropbox",
    "gravityformsgooglesheets": "Google Sheets",
}

#: The Gravity Forms permission each command needs, and its words.
CAPABILITIES = {
    "edit_forms": ("gravityforms_edit_forms", "Changing a form's feeds"),
    "edit_entries": ("gravityforms_edit_entries", "Changing an entry"),
    "view_notes": ("gravityforms_view_entry_notes", "Reading an entry's notes"),
    "edit_notes": ("gravityforms_edit_entry_notes", "Adding a note to an entry"),
    "design_forms": ("gravityforms_edit_forms", "Changing a form's fields and settings"),
    "create_form": ("gravityforms_create_form", "Making a Gravity Forms form"),
}


def truthy(value: Any) -> bool:
    """Gravity Forms says yes as ``1``, ``"1"`` or ``true``."""
    return str(value).strip().lower() in ("1", "true", "yes")


def gravity_can(account: Any, capability: str) -> bool:
    """Gravity Forms grants every one of its permissions to ``gform_full_access``."""
    if account is None:
        return True
    return bool(account.can(capability) or account.can("gform_full_access"))


def _as_list(answer: Any) -> list[dict[str, Any]]:
    values = answer.values() if isinstance(answer, dict) else answer
    return [item for item in values or [] if isinstance(item, dict)]


def _text(value: Any) -> str:
    """HTML from the site as one plain line."""
    plain = html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))
    return " ".join(plain.split())


def gravity_forms(api: Any) -> dict[str, str]:
    """Each form's id and title, from ``gf/v2/forms``."""
    forms = _as_list(api.get(f"{NS}/forms"))
    return {str(f.get("id", "")): str(f.get("title", "") or "Form") for f in forms if f.get("id")}


# --------------------------------------------------------------------------- #
# Feeds


def addon_name(slug: str) -> str:
    """ "Mailchimp" for ``gravityformsmailchimp``; a readable guess for any other."""
    if slug in _ADDONS:
        return _ADDONS[slug]
    bare = slug.removeprefix("gravityforms").removeprefix("gf").strip("-_")
    return bare.replace("-", " ").replace("_", " ").title() or slug or "Add-on"


def feed_name(feed: Mapping[str, Any]) -> str:
    meta = feed.get("meta") if isinstance(feed.get("meta"), dict) else {}
    for key in ("feedName", "feed_name", "name"):
        if meta and str(meta.get(key, "") or "").strip():
            return str(meta[key]).strip()
    return f"Feed {feed.get('id', '')}".strip()


def _feed_row(site: str, feed: Mapping[str, Any], titles: Mapping[str, str]) -> WbRow:
    feed_id = str(feed.get("id", ""))
    form = titles.get(str(feed.get("form_id", "")), f"Form {feed.get('form_id', '')}")
    addon = addon_name(str(feed.get("addon_slug", "") or ""))
    active = truthy(feed.get("is_active", 0))
    name = feed_name(feed)
    state = "active" if active else "inactive"
    return WbRow(
        kind="gravity_feed",
        site=site,
        key=feed_id,
        cells={
            "name": name,
            "form": form,
            "addon": addon,
            "status": "Active" if active else "Inactive",
            "site": site,
        },
        detail=(
            f"{name}, a {addon} feed on {form}, {state}. "
            + (
                "It runs when this form is submitted."
                if active
                else "It is off, so submissions do not reach it."
            )
        ),
        route=f"{NS}/feeds/{feed_id}",
        status=state,
        subkind="gravity",
        raw=dict(feed),
    )


def load_feeds(ctx: SiteContext) -> list[WbRow]:
    """Every add-on feed of every Gravity Forms form on the site."""
    titles = gravity_forms(ctx.api)
    if not titles:
        return []
    ids = sorted(titles, key=lambda value: int(value) if value.isdigit() else 0)
    params = {f"form_ids[{i}]": form_id for i, form_id in enumerate(ids)}
    try:
        feeds = _as_list(ctx.api.get(f"{NS}/feeds", **params))
    except WordPressApiError as exc:
        if exc.status != 404:
            raise
        feeds = []
        for form_id in ids[:_MAX_FORMS]:
            feeds += _as_list(ctx.api.get(f"{NS}/forms/{form_id}/feeds"))
    return [_feed_row(ctx.name, feed, titles) for feed in feeds]


def feed_body(
    feed: Mapping[str, Any], *, active: bool | None = None, name: str | None = None
) -> tuple[dict[str, Any], list[str]]:
    """The whole feed with only the safe fields changed, and the preview's lines."""
    body = {**feed}
    lines: list[str] = []
    if active is not None:
        was = truthy(feed.get("is_active", 0))
        body["is_active"] = 1 if active else 0
        lines.append(f"Active: {'yes' if was else 'no'} becomes {'yes' if active else 'no'}.")
    if name is not None:
        meta = dict(feed.get("meta") or {}) if isinstance(feed.get("meta"), dict) else {}
        key = next((k for k in ("feedName", "feed_name") if k in meta), "feedName")
        lines.append(f"Name: {feed_name(feed)} becomes {name}.")
        meta[key] = name
        body["meta"] = meta
    lines.append("Every other setting of the feed is sent back exactly as the site has it.")
    return body, lines


# --------------------------------------------------------------------------- #
# Entry notes and flags


@dataclass(frozen=True)
class Note:
    who: str
    when: str
    text: str
    kind: str


def read_notes(api: Any, entry_id: int) -> list[Note]:
    """An entry's notes, oldest first."""
    found = _as_list(api.get(f"{NS}/entries/{entry_id}/notes"))
    notes = [
        Note(
            str(n.get("user_name", "") or "Gravity Forms"),
            str(n.get("date_created", "") or ""),
            _text(n.get("value", "")),
            str(n.get("note_type", "") or "user"),
        )
        for n in found
    ]
    return sorted(notes, key=lambda note: note.when)


def note_lines(notes: Sequence[Note]) -> list[str]:
    if not notes:
        return ["This entry has no notes yet."]
    return [
        f"{note.who}, {friendly_date(note.when) if note.when else 'undated'}"
        + (f" ({note.kind})" if note.kind not in ("user", "") else "")
        + f": {note.text}"
        for note in notes
    ]


def add_note(api: Any, entry_id: int, text: str, account: Any = None) -> Any:
    """A user note on the entry, signed as the connected account."""
    body: dict[str, Any] = {"value": text, "note_type": "user", "entry_id": entry_id}
    if account is not None:
        body["user_id"] = account.id
        body["user_name"] = account.name
    return api.post(f"{NS}/entries/{entry_id}/notes", body)


def set_entry_flag(api: Any, route: str, flag: str, on: bool) -> bool:
    """Set ``is_starred`` or ``is_read`` on the entry; returns what it was.

    The entry is read again first and sent whole, because Gravity Forms'
    ``PUT`` replaces an entry: a body of the one flag would empty its answers.
    """
    if flag not in ("is_starred", "is_read"):
        raise ValueError(f"{flag} is not a flag QUILL sets.")
    current = api.get(route)
    if not isinstance(current, dict) or not current.get("id"):
        raise WordPressApiError("Gravity Forms did not return this entry, so nothing was changed.")
    was = truthy(current.get(flag, 0))
    api.request("PUT", route, json_body={**current, flag: 1 if on else 0})
    return was


# --------------------------------------------------------------------------- #
# Notifications


@dataclass(frozen=True)
class Notification:
    id: str
    name: str
    event: str
    active: bool
    recipients: str

    @property
    def line(self) -> str:
        state = "" if self.active else ", turned off"
        event = "" if self.event in ("", "form_submission") else f", sent on {self.event}"
        return f"{self.name}: to {self.recipients}{event}{state}"


def _field_labels(form: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(f.get("id", "")): str(f.get("label", "") or f"Field {f.get('id', '')}")
        for f in form.get("fields") or []
        if isinstance(f, dict)
    }


def _recipients(
    note: Mapping[str, Any], entry: Mapping[str, Any], labels: Mapping[str, str]
) -> str:
    kind = str(note.get("toType", "") or "email")
    to = str(note.get("to", "") or "")
    if kind == "field":
        value = str(entry.get(to, "") or "")
        said = f"the address in {labels.get(to, 'field ' + to)}"
        found = f"{said}, {value}" if value else f"{said}, which this entry left empty"
    elif kind == "routing":
        rules = [r for r in note.get("routing") or [] if isinstance(r, dict)]
        found = (
            "; ".join(
                f"{r.get('email', '')} when {labels.get(str(r.get('fieldId', '')), 'a field')} "
                f"{str(r.get('operator', 'is')).replace('isnot', 'is not')} {r.get('value', '')}"
                for r in rules
            )
            or "nobody, as no routing rules are set"
        )
    else:
        found = to.replace("{admin_email}", "the site's admin email") or "nobody"
    bcc = str(note.get("bcc", "") or "").strip()
    return found + (f", with a blind copy to {bcc}" if bcc else "")


def entry_notifications(form: Mapping[str, Any], entry: Mapping[str, Any]) -> list[Notification]:
    """The form's notifications, with who each would go to for *entry*."""
    labels = _field_labels(form)
    found: list[Notification] = []
    for note in _as_list(form.get("notifications")):
        found.append(
            Notification(
                str(note.get("id", "")),
                str(note.get("name", "") or "Notification"),
                str(note.get("event", "") or "form_submission"),
                truthy(note.get("isActive", True)),
                _recipients(note, entry, labels),
            )
        )
    return [n for n in found if n.id]


def resend_notifications(api: Any, entry_id: int, ids: Sequence[str]) -> list[str]:
    """Send *ids* again for the entry; the ids Gravity Forms says it sent."""
    answer = api.post(f"{NS}/entries/{entry_id}/notifications", None, _notifications=",".join(ids))
    if isinstance(answer, dict):
        answer = list(answer.values())
    return [str(value) for value in answer or [] if value not in (None, "", False)]


# --------------------------------------------------------------------------- #
# Results


def _choice_texts(field_spec: Mapping[str, Any]) -> dict[str, str]:
    texts: dict[str, str] = {}
    for key in ("choices", "gsurveyLikertRows"):
        for choice in field_spec.get(key) or []:
            if isinstance(choice, dict):
                value = str(choice.get("value", "") or choice.get("text", ""))
                texts[value] = str(choice.get("text", "") or value)
    return texts


def _label_for(labels: Any, field_id: str, fields: Mapping[str, Mapping[str, Any]]) -> str:
    found = labels.get(field_id) if isinstance(labels, dict) else None
    if isinstance(found, dict) and found.get("label"):
        return str(found["label"])
    if isinstance(found, str) and found:
        return found
    return str(fields.get(field_id, {}).get("label", "") or f"Field {field_id}")


def result_rows(
    site: str, form_title: str, form: Mapping[str, Any], answer: Mapping[str, Any]
) -> list[WbRow]:
    """One row per answer, each carrying its question's sentence."""
    fields = {str(f.get("id", "")): f for f in form.get("fields") or [] if isinstance(f, dict)}
    labels = answer.get("labels") or {}
    total = int(str(answer.get("entry_count", 0) or 0) or 0)
    rows: list[WbRow] = []

    def add(question: str, answer_text: str, count: int, sentence: str) -> None:
        share = f"{round(100 * count / total)} percent" if total else ""
        rows.append(
            WbRow(
                kind="gravity_result",
                site=site,
                key=f"{form.get('id', '')}:{len(rows)}",
                cells={
                    "form": form_title,
                    "question": question,
                    "answer": answer_text,
                    "count": str(count),
                    "share": share,
                    "site": site,
                },
                detail=sentence,
                subkind="gravity",
                raw={"form_id": form.get("id", ""), "question": question, "answer": answer_text},
            )
        )

    if str(answer.get("status", "complete")) != "complete":
        add(
            "Still being counted",
            "",
            0,
            f"Gravity Forms is still counting the results of {form_title}. Press F5 in a moment.",
        )
    for field_id, data in (answer.get("field_data") or {}).items():
        field_id = str(field_id)
        spec = fields.get(field_id, {})
        if spec and str(spec.get("type", "")) not in _RESULT_TYPES:
            continue
        question = _label_for(labels, field_id, fields)
        label_info = labels.get(field_id) if isinstance(labels, dict) else None
        texts = _choice_texts(spec)
        if isinstance(label_info, dict) and isinstance(label_info.get("choices"), dict):
            texts.update({str(k): str(v) for k, v in label_info["choices"].items()})
        pairs: list[tuple[str, int]] = []
        if isinstance(data, dict):
            for value, count in data.items():
                if isinstance(count, dict):  # a Likert row: its columns
                    row_text = texts.get(str(value), str(value))
                    for col, n in count.items():
                        pairs.append((f"{row_text}, {texts.get(str(col), str(col))}", _int(n)))
                else:
                    pairs.append((texts.get(str(value), str(value)), _int(count)))
        else:
            pairs.append(("Answered", _int(data)))
        said = "; ".join(
            f"{text} {n}" + (f", {round(100 * n / total)} percent" if total else "")
            for text, n in pairs
        )
        sentence = f"{question}, {total} response{'s' if total != 1 else ''}: {said or 'none'}."
        for text, n in pairs:
            add(question, text, n, sentence)
    return rows


def _int(value: Any) -> int:
    try:
        return int(str(value or 0))
    except ValueError:
        return 0


def load_results(ctx: SiteContext) -> list[WbRow]:
    """Results for every form with quiz, poll or survey fields."""
    rows: list[WbRow] = []
    for form_id, title in list(gravity_forms(ctx.api).items())[:_MAX_FORMS]:
        form = ctx.api.get(f"{NS}/forms/{form_id}")
        if not isinstance(form, dict):
            continue
        kinds = {str(f.get("type", "")) for f in form.get("fields") or [] if isinstance(f, dict)}
        if not kinds & _RESULT_TYPES:
            continue
        answer = ctx.api.get(f"{NS}/forms/{form_id}/results")
        if isinstance(answer, dict):
            rows += result_rows(ctx.name, title, form, answer)
    return rows


# --------------------------------------------------------------------------- #
# Field filters


@dataclass(frozen=True)
class FieldFilter:
    key: str
    text: str
    operators: tuple[str, ...]
    values: tuple[tuple[str, str], ...] = ()


def field_filters(api: Any, form_id: str) -> list[FieldFilter]:
    """What the form's entries can be filtered on, as Gravity Forms says."""

    def flatten(items: Iterable[Any]) -> Iterable[Mapping[str, Any]]:
        for item in items:
            if isinstance(item, dict) and isinstance(item.get("filters"), list):
                yield from flatten(item["filters"])
            elif isinstance(item, dict):
                yield item

    raw = api.get(f"{NS}/forms/{form_id}/field-filters")
    found: list[FieldFilter] = []
    for item in flatten(raw.values() if isinstance(raw, dict) else raw or []):
        key = str(item.get("key", ""))
        if not key or key == "0":  # "Any form field" is the filter box's words
            continue
        values = tuple(
            (str(v.get("text", "") or v.get("value", "")), str(v.get("value", "")))
            for v in item.get("values") or []
            if isinstance(v, dict)
        )
        operators = tuple(str(o) for o in item.get("operators") or ("is",))
        found.append(FieldFilter(key, str(item.get("text", "") or key), operators, values))
    return found
