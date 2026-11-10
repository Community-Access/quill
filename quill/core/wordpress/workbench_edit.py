"""Saving from the Workbench: conflict check, verify, batch, Trash and undo (WP-R-006 to 008).

Every save follows the same four steps, whatever the object:

1. **Only what changed** goes back: the sheet's diff
   (:func:`quill.core.workbench.properties.changes`) becomes the request body
   under WordPress's own field names (:func:`body_for`).
2. **The conflict check** (WP-R-006): before sending, the object is read
   again and its ``modified_gmt`` compared with the one the sheet loaded. If
   somebody changed it meanwhile, nothing is sent and :class:`EditConflict`
   names the fields that differ, so the window can offer Keep Theirs or Use
   Mine.
3. **Verify after save:** the answer is compared with what was sent, and a
   field the site did not keep (a plugin that rewrites slugs, say) is named
   rather than claimed.
4. **Undo:** the body that puts the old values back is returned with the
   result, and the window records it in the shared Change History.

Batches go through ``batch/v1`` (WP-R-007), 25 requests a call, with a result
per item; a site or route that will not batch is sent one request at a time
instead, and the results read the same. Delete is Trash (WP-R-008): a post,
page, custom item or comment goes to WordPress's Trash and comes back with
Restore; everything else, and Delete Permanently, is a tier 3 ``force``
delete. Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.site import raw_text, rendered
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_sheets import term_ids
from quill.core.workbench.properties import FieldChange, FieldKind, SheetSpec

__all__ = [
    "TRASHABLE",
    "BatchResult",
    "EditConflict",
    "EditRefused",
    "SaveResult",
    "body_for",
    "check_conflict",
    "delete_permanently",
    "restore",
    "run_batch",
    "save",
    "set_comment_status",
    "trash",
    "undo_body",
    "verify",
]

TRASHABLE = frozenset({"item", "comment"})
"""Row types WordPress keeps a Trash for. The rest can only be deleted for good."""

_NUMBERS = frozenset({"featured_media", "parent", "menu_order", "post"})


class EditConflict(CodedError):
    """Somebody changed the object on the site after the sheet loaded it."""

    code = "QUILL-WP-WORKBENCH-CONFLICT"

    def __init__(self, message: str, changed: Sequence[FieldChange] = ()) -> None:
        super().__init__(message)
        self.changed = tuple(changed)


class EditRefused(CodedError):
    """A change the Workbench will not send, said as a sentence (a name that matches nothing)."""

    code = "QUILL-WP-WORKBENCH-REFUSED"


@dataclass(frozen=True)
class SaveResult:
    raw: Mapping[str, Any]
    sentence: str
    not_kept: tuple[str, ...] = ()
    undo: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BatchResult:
    row: WbRow
    ok: bool
    sentence: str
    raw: Mapping[str, Any] = field(default_factory=dict)


def _int_of(value: object) -> int:
    text = str(value or "").strip()
    if text.endswith(")") and "(" in text:
        text = text.rsplit("(", 1)[1].rstrip(")")
    try:
        return int(text or 0)
    except ValueError as exc:
        raise EditRefused(f"{value} is not a number.") from exc


def body_for(
    sheet: SheetSpec,
    row: WbRow,
    pending: Sequence[FieldChange],
    *,
    term_names: Mapping[str, Mapping[str, int]] | None = None,
) -> dict[str, Any]:
    """The request body for *pending*, under the names WordPress reads.

    *term_names* maps each taxonomy field (``categories``) to its terms by
    name, so "News" or "News (12)" becomes 12; a name that matches nothing
    raises :class:`EditRefused` rather than dropping it silently.
    """
    body: dict[str, Any] = {}
    names = term_names or {}
    for change in pending:
        spec = sheet.field(change.key)
        value: Any = change.after
        if change.key.startswith("meta."):
            body.setdefault("meta", {})[change.key.removeprefix("meta.")] = value
            continue
        if row.kind == "setting" and change.key == "value":
            body[str(row.raw.get("key", ""))] = value
            continue
        if row.kind == "user" and change.key == "roles":
            body["roles"] = [str(value)]
            continue
        if change.key == "author":
            body["author"] = _int_of(value)
            continue
        if spec.kind is FieldKind.LIST and isinstance(value, tuple):
            if row.kind == "item":
                ids, unknown = term_ids(value, names.get(change.key, {}))
                if unknown:
                    raise EditRefused(
                        f"{spec.label}: nothing on {row.site} is called {', '.join(unknown)}. "
                        "Make it first, or check the spelling."
                    )
                value = ids
            else:
                value = list(value)
        elif spec.kind is FieldKind.NUMBER or change.key in _NUMBERS:
            value = _int_of(value)
        body[change.key] = value
    return body


def _comparable(value: Any) -> Any:
    if isinstance(value, dict) and ("raw" in value or "rendered" in value):
        return raw_text(value) or rendered(value)
    if isinstance(value, list):
        return sorted(str(v) for v in value)
    if isinstance(value, bool):
        return value
    return "" if value is None else str(value)


def verify(body: Mapping[str, Any], answer: Mapping[str, Any]) -> tuple[str, ...]:
    """The fields of *body* the site's *answer* does not show as sent (write-only ones skipped)."""
    missed: list[str] = []
    for key, sent in body.items():
        if key == "password":
            continue
        if key == "meta" and isinstance(sent, dict):
            kept = answer.get("meta") if isinstance(answer.get("meta"), dict) else {}
            missed += [
                f"meta.{k}"
                for k, v in sent.items()
                if _comparable((kept or {}).get(k)) != _comparable(v)
            ]
            continue
        if key not in answer:
            continue  # a field the answer leaves out cannot be checked, so is not claimed
        if _comparable(answer.get(key)) != _comparable(sent):
            missed.append(key)
    return tuple(missed)


def undo_body(body: Mapping[str, Any], before: Mapping[str, Any]) -> dict[str, Any]:
    """The body that puts back what *body* changed, from the object as it was (*before*)."""
    out: dict[str, Any] = {}
    for key in body:
        if key == "password":
            continue
        if key == "meta" and isinstance(body[key], dict):
            old = before.get("meta") if isinstance(before.get("meta"), dict) else {}
            out["meta"] = {k: (old or {}).get(k) for k in body[key]}
            continue
        value = before.get(key)
        if isinstance(value, dict) and ("raw" in value or "rendered" in value):
            value = raw_text(value) or rendered(value)
        out[key] = value
    return out


def check_conflict(api: WordPressApi, row: WbRow, loaded_modified: str) -> Mapping[str, Any]:
    """Read *row* again; raise :class:`EditConflict` if it changed since *loaded_modified*."""
    current = api.get(row.route, context="edit")
    current = current if isinstance(current, dict) else {}
    now = str(current.get("modified_gmt", "") or "")
    if loaded_modified and now and now != loaded_modified:
        raise EditConflict(
            f"{row.title} was changed on {row.site} after you opened it. Nothing was sent."
        )
    return current


def _route(row: WbRow) -> str:
    return "wp/v2/settings" if row.kind == "setting" else row.route


def save(
    api: WordPressApi,
    row: WbRow,
    body: Mapping[str, Any],
    *,
    loaded_modified: str = "",
    before: Mapping[str, Any] | None = None,
) -> SaveResult:
    """Send *body* for *row*: conflict check, the write, then verify."""
    if not body:
        return SaveResult({}, "Nothing changed, so nothing was sent.")
    current: Mapping[str, Any] = before or row.raw
    if loaded_modified and row.route:
        current = check_conflict(api, row, loaded_modified)
    if row.kind == "setting":
        answer = api.post(_route(row), dict(body))
        old = {str(row.raw.get("key", "")): row.raw.get("value")}
        current = old
    else:
        answer = api.post(_route(row), dict(body), context="edit")
    answer = answer if isinstance(answer, dict) else {}
    missed = verify(body, answer)
    count = len(body) if "meta" not in body else len(body) - 1 + len(body["meta"])
    noun = "change" if count == 1 else "changes"
    sentence = f"Saved {count} {noun} to {row.title} on {row.site}."
    if missed:
        sentence += f" The site did not keep: {', '.join(missed)}."
    return SaveResult(answer, sentence, missed, undo_body(body, current))


def _batchable(api: WordPressApi) -> bool:
    return not getattr(api, "_quill_no_batch", False)


def run_batch(
    api: WordPressApi, rows: Sequence[WbRow], bodies: Sequence[Mapping[str, Any]]
) -> list[BatchResult]:
    """One body per row through ``batch/v1``, else one request at a time; a result each."""
    requests = [
        {"method": "POST", "path": f"/{row.route}", "body": dict(body)}
        for row, body in zip(rows, bodies, strict=True)
    ]
    answers: list[dict[str, Any]] = []
    if _batchable(api) and all(row.kind in ("item", "term", "media") for row in rows):
        try:
            answers = api.batch(requests)
        except WordPressApiError as exc:
            if exc.status not in (400, 404, 405, 501) and exc.wp_code != "rest_batch_not_allowed":
                raise
            answers = []
    results: list[BatchResult] = []
    if len(answers) == len(rows):
        for row, answer in zip(rows, answers, strict=True):
            status = int(answer.get("status", 200) or 200)
            payload = answer.get("body") if isinstance(answer.get("body"), dict) else {}
            payload = payload or {}
            ok = 200 <= status < 300
            said = "saved" if ok else str(payload.get("message", "") or f"refused ({status})")
            results.append(BatchResult(row, ok, f"{row.title}: {said}", payload if ok else {}))
        return results
    for row, body in zip(rows, bodies, strict=True):
        try:
            raw = api.post(row.route, dict(body), context="edit")
            results.append(BatchResult(row, True, f"{row.title}: saved", raw or {}))
        except WordPressApiError as exc:
            results.append(BatchResult(row, False, f"{row.title}: {exc.plain}"))
    return results


def trash(api: WordPressApi, row: WbRow) -> Mapping[str, Any]:
    """Into WordPress's Trash (no ``force``). Only for :data:`TRASHABLE` rows."""
    if row.kind not in TRASHABLE:
        raise EditRefused(
            "WordPress keeps no Trash for this, so it can only be deleted permanently, "
            "with Shift+Delete."
        )
    raw = api.delete(row.route)
    return raw if isinstance(raw, dict) else {}


def restore(api: WordPressApi, row: WbRow, status: str = "") -> Mapping[str, Any]:
    """Out of the Trash: an item to *status* (draft by default), a comment to waiting."""
    if row.kind == "comment":
        wanted = status if status and status != "trash" else "hold"
    else:
        wanted = status if status and status != "trash" else "draft"
    raw = api.post(row.route, {"status": wanted}, context="edit")
    return raw if isinstance(raw, dict) else {}


def delete_permanently(api: WordPressApi, row: WbRow, *, reassign: int = 0) -> None:
    """Gone for good (tier 3). A user's content goes to *reassign*, which must be given."""
    if row.kind == "user":
        if not reassign:
            raise EditRefused("Choose who gets this person's posts before removing them.")
        api.delete(row.route, force=True, reassign=reassign)
        return
    api.delete(row.route, force=True)


def set_comment_status(api: WordPressApi, row: WbRow, status: str) -> Mapping[str, Any]:
    """``approved``, ``hold`` or ``spam``; the site's spam plugin hears of Spam and Not Spam."""
    raw = api.post(row.route, {"status": status}, context="edit")
    return raw if isinstance(raw, dict) else {}
