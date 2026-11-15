"""Copy a Gravity Forms form's old entries into a QUILL Accessible Forms form (WP-R-029).

Copy as a QUILL Accessible Form (:mod:`quill.core.wordpress.gravity_qaf`)
makes the form and leaves its entries behind. This module carries the
entries over, one by one, after a preview:

- :func:`read_gravity_entries` reads the form's active entries through
  ``gf/v2/entries`` (:func:`quill.core.wordpress.workbench_gravity_search.read_entries`),
  page by page; spam and trashed entries stay where they are;
- :func:`plan_copy` maps each answer through the same field ids the form
  conversion gives (:func:`~quill.core.wordpress.gravity_qaf.qaf_id`):
  checkboxes become a list, a name or address becomes one line, and a
  field the target QAF form has no question for, a file, a payment or a
  field family QAF has no match for is named as left out, once for the form
  and on each entry it touches;
- :func:`send_copies` makes each entry with ``POST {namespace}/entries``
  and gives one outcome per entry.

**The route is an assumption, said plainly.** QAF's REST API today lists,
reads and deletes entries and changes their spam status; it has no route that
makes an entry. QUILL sends to :data:`ENTRY_CREATE_ROUTE` (``POST
qaf/v1/entries``, the same shape QAF's own entries come back in: ``form_id``,
``fields`` keyed by question id, ``created_at``, ``status``) and a
``source`` naming the Gravity Forms entry. A site whose QAF does not offer it
answers 404 or ``rest_no_route``, and :func:`send_copies` turns that into one
sentence instead of one failure per entry.

Wx-free; requests go through the site's own client, off the UI thread.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.forms import model as M
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.gravity_build import DISPLAY_TYPES, field_name, fields_of
from quill.core.wordpress.gravity_qaf import SHARED, qaf_id
from quill.core.wordpress.workbench_by_name import Outcome

__all__ = [
    "ENTRY_CREATE_ROUTE",
    "MAX_ENTRIES",
    "ROUTE_NOTE",
    "CopyPlan",
    "EntryCopy",
    "no_route_sentence",
    "plan_copy",
    "read_gravity_entries",
    "send_copies",
]

ENTRY_CREATE_ROUTE = "qaf/v1/entries"
"""The route QUILL makes an entry with: ``POST``. QAF must offer it; see the module doc."""
MAX_ENTRIES = 2500
"""At most this many entries are read and copied in one go (25 pages of a hundred)."""
ROUTE_NOTE = (
    "Each entry is sent to POST {namespace}/entries. QUILL Accessible Forms on the site must "
    "offer that route to make entries; if it does not, nothing is made and QUILL says so."
)

_FILE_TYPES = frozenset({"fileupload", "post_image", "signature"})
_PAYMENT_TYPES = frozenset({
    "product",
    "option",
    "shipping",
    "total",
    "quantity",
    "creditcard",
    "stripe_creditcard",
    "paypal",
    "square",
})
_ONE_LINE = {"name": " ", "address": ", "}


@dataclass
class EntryCopy:
    """One Gravity Forms entry as the QAF entry it becomes."""

    entry_id: int
    created_at: str
    starred: bool
    fields: dict[str, Any]
    lost: list[str] = field(default_factory=list)

    def body(self, form_id: int) -> dict[str, Any]:
        """What ``POST {namespace}/entries`` is sent for this entry."""
        return {
            "form_id": int(form_id),
            "fields": dict(self.fields),
            "created_at": self.created_at,
            "status": "active",
            "is_starred": 1 if self.starred else 0,
            "source": f"Imported from Gravity Forms entry {self.entry_id}",
        }

    @property
    def line(self) -> str:
        count = len(self.fields)
        said = f"Entry {self.entry_id} from {self.created_at or 'an unknown date'}: "
        said += f"{count} answer{'s' if count != 1 else ''}"
        if self.lost:
            said += "; left out: " + ", ".join(self.lost)
        return said + "."


@dataclass
class CopyPlan:
    """Every entry to copy, and what cannot carry over, before anything is sent."""

    source_title: str
    target_id: int
    target_title: str
    namespace: str
    copies: list[EntryCopy] = field(default_factory=list)
    lost: list[str] = field(default_factory=list)  # for the whole form
    beyond_cap: bool = False

    def lines(self) -> list[str]:
        """The preview: the route, what is left out, then one line per entry."""
        out = [
            f"From {self.source_title} (Gravity Forms) into {self.target_title} "
            "(QUILL Accessible Forms).",
            ROUTE_NOTE.format(namespace=self.namespace),
            "Only active entries are copied; spam and trashed entries stay in Gravity Forms.",
            *(f"Cannot carry over: {line}" for line in self.lost),
        ]
        if self.beyond_cap:
            out.append(f"Only the first {MAX_ENTRIES} entries are read; copy the rest after.")
        return out + [c.line for c in self.copies]


def read_gravity_entries(api: Any, form_id: str, *, pages: int = 25) -> list[dict[str, Any]]:
    """The form's active entries, a hundred a page, up to :data:`MAX_ENTRIES`."""
    from quill.core.wordpress.workbench_gravity_search import read_entries

    return read_entries(api, "gf/v2/entries", [str(form_id)], "active", None, pages)


def _why_lost(spec: Mapping[str, Any], questions: Mapping[str, Any]) -> str:
    kind = str(spec.get("type", ""))
    name = field_name(spec)
    if kind in _FILE_TYPES:
        return f"{name}: uploaded files stay on the Gravity Forms entry"
    if kind in _PAYMENT_TYPES:
        return f"{name}: payment details stay with Gravity Forms"
    if kind not in SHARED:
        return f"{name}: a {kind} field, which QUILL Accessible Forms has no match for"
    if qaf_id(spec.get("id")) not in questions:
        return f"{name}: the QUILL Accessible Forms form has no question for it"
    return ""


def _answer(spec: Mapping[str, Any], entry: Mapping[str, Any]) -> Any:
    """One field's answer from *entry*: a value, a list for checkboxes, or None."""
    ident = str(spec.get("id"))
    kind = str(spec.get("type", ""))
    parts = [
        str(entry[key])
        for key in sorted(
            (k for k in entry if str(k).startswith(f"{ident}.")),
            key=lambda k: [int(p) if p.isdigit() else 0 for p in str(k).split(".")],
        )
        if entry.get(key) not in ("", None)
    ]
    if kind in ("checkbox", "multiselect"):
        if parts:
            return parts
        whole = entry.get(ident)
        if kind == "multiselect" and isinstance(whole, str) and whole.startswith("["):
            import json

            try:
                found = json.loads(whole)
            except ValueError:
                found = None
            if isinstance(found, list):
                return [str(v) for v in found if v not in ("", None)] or None
        return [str(whole)] if whole not in ("", None) else None
    if parts:
        return _ONE_LINE.get(kind, " ").join(parts)
    whole = entry.get(ident)
    return None if whole in ("", None) else str(whole)


def plan_copy(
    gravity_form: Mapping[str, Any],
    entries: Sequence[Mapping[str, Any]],
    target_id: int,
    target_title: str,
    target_model: Mapping[str, Any] | None,
    *,
    namespace: str = "qaf/v1",
) -> CopyPlan:
    """Each entry mapped onto the target form's questions, and what is left out."""
    questions = M.fields(dict(target_model)) if isinstance(target_model, Mapping) else {}
    plan = CopyPlan(
        str(gravity_form.get("title") or "the form"),
        int(target_id),
        target_title,
        namespace,
        beyond_cap=len(entries) >= MAX_ENTRIES,
    )
    if not questions:
        plan.lost.append(
            f"{target_title} has no questions QUILL can read, so no answer has a place there."
        )
    carried: list[Mapping[str, Any]] = []
    dropped: dict[str, str] = {}
    for spec in fields_of(gravity_form):
        if str(spec.get("type", "")) in DISPLAY_TYPES:
            continue
        why = _why_lost(spec, questions)
        if why:
            dropped[str(spec.get("id"))] = field_name(spec)
            plan.lost.append(why + ".")
        else:
            carried.append(spec)
    for entry in list(entries)[:MAX_ENTRIES]:
        copy = EntryCopy(
            int(entry.get("id", 0) or 0),
            str(entry.get("date_created", "") or ""),
            str(entry.get("is_starred", "0")) in ("1", "true", "True"),
            {},
        )
        for kept in carried:
            value = _answer(kept, entry)
            if value is not None:
                copy.fields[qaf_id(kept.get("id"))] = value
        for ident, name in dropped.items():
            if any(
                str(k) == ident or str(k).startswith(f"{ident}.")
                for k, v in entry.items()
                if v not in ("", None)
            ):
                copy.lost.append(name)
        if str(entry.get("payment_status") or "").strip():
            copy.lost.append("its payment status")
        plan.copies.append(copy)
    return plan


def no_route_sentence(site: str, namespace: str) -> str:
    """The one sentence for a site whose QAF has no route that makes an entry."""
    return (
        f"{site}'s QUILL Accessible Forms cannot take entries yet: it offers no "
        f"POST {namespace}/entries route, so no entry was copied. Update the plugin and try again."
    )


def _no_route(exc: WordPressApiError) -> bool:
    return exc.status in (404, 405) or exc.wp_code == "rest_no_route"


def send_copies(api: Any, site: str, plan: CopyPlan) -> tuple[list[Outcome], list[int]]:
    """Make each entry on the site: one outcome per entry, and the new entries' ids.

    A site with no create route stops at the first entry, with one outcome
    saying so (:func:`no_route_sentence`), rather than failing every entry.
    """
    outcomes: list[Outcome] = []
    made: list[int] = []
    route = f"{plan.namespace}/entries"
    for copy in plan.copies:
        title = f"Gravity Forms entry {copy.entry_id}"
        try:
            answer = api.post(route, copy.body(plan.target_id))
        except WordPressApiError as exc:
            if _no_route(exc) and not made:
                return [
                    Outcome(site, plan.target_title, False, no_route_sentence(site, plan.namespace))
                ], []
            outcomes.append(Outcome(site, title, False, exc.plain or str(exc)))
            continue
        new_id = int(answer.get("id", 0) or 0) if isinstance(answer, dict) else 0
        if new_id:
            made.append(new_id)
        words = f"copied as entry {new_id}" if new_id else "copied"
        if copy.lost:
            words += "; left out: " + ", ".join(copy.lost)
        outcomes.append(Outcome(site, title, True, words))
    return outcomes, made
