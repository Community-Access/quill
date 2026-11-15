"""One checked write for a plugin's object: conflict check, the write, verify, and undo.

The WooCommerce, Events Calendar and Yoast SEO objects the Workbench changes
(a review, a shipping zone, a tax rate, a customer, a variation, an event's
terms) have no ``modified_gmt`` to compare, so the conflict check compares
the very fields being changed: the object is read again, and if any of them
differs from what the row loaded, nothing is sent and :class:`EditConflict`
names them. After the write, the answer is compared with what was sent and a
field the site did not keep is named rather than claimed. The undo body puts
back the values the object had just before the write (read in the conflict
check), so it restores what was there, not what QUILL last listed.

Nested objects (a customer's billing address) are compared, verified and
undone key by key, so only the keys sent count. Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress.site import rendered
from quill.core.wordpress.workbench_edit import EditConflict

__all__ = [
    "WRITE_ONLY",
    "Outcome",
    "Written",
    "changed_since",
    "checked_write",
    "not_kept",
    "outcomes_report",
    "reread",
    "restore_body",
]

#: Fields that are sent but never read back (a webhook's secret, a password).
WRITE_ONLY = frozenset({"secret", "password"})


@dataclass(frozen=True)
class Written:
    """What a checked write did: the site's answer, what it did not keep, and the undo body."""

    answer: Mapping[str, Any]
    not_kept: tuple[str, ...] = ()
    undo: Mapping[str, Any] = field(default_factory=dict)

    def tail(self) -> str:
        """`` The site did not keep: x.`` when it did not, else ""."""
        return f" The site did not keep: {', '.join(self.not_kept)}." if self.not_kept else ""


@dataclass(frozen=True)
class Outcome:
    """One item of a batch: its name, whether it worked, and the sentence for it."""

    name: str
    ok: bool
    said: str


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping) and ("raw" in value or "rendered" in value):
        return str(value.get("raw") or rendered(value) or "")
    if isinstance(value, Mapping) and "value" in value:  # a WooCommerce setting
        return _plain(value.get("value"))
    if isinstance(value, bool):
        return value
    if isinstance(value, (list, tuple)):
        return sorted(str(_plain(v)) for v in value)
    return "" if value is None else str(value)


def _pairs(body: Mapping[str, Any], obj: Mapping[str, Any]) -> list[tuple[str, Any, Any]]:
    """(name, sent, found) for each sent field, a nested object's keys one by one."""
    out: list[tuple[str, Any, Any]] = []
    for key, sent in body.items():
        if key in WRITE_ONLY:
            continue
        found = obj.get(key)
        if isinstance(sent, Mapping) and not ("raw" in sent or "rendered" in sent):
            inner = found if isinstance(found, Mapping) else {}
            out += [(f"{key}.{k}", v, inner.get(k)) for k, v in sent.items()]
            continue
        out.append((key, sent, found))
    return out


def reread(api: Any, route: str) -> dict[str, Any]:
    """The object as the site has it now (``context=edit``), or ``{}``."""
    found = api.get(route, context="edit")
    return found if isinstance(found, dict) else {}


def changed_since(
    loaded: Mapping[str, Any], current: Mapping[str, Any], body: Mapping[str, Any]
) -> list[str]:
    """The sent fields whose value on the site is no longer what the row loaded.

    A field the row did not load, or the site does not return, is not a conflict:
    there is nothing to compare it with.
    """
    changed = []
    for name, _sent, was in _pairs(body, loaded):
        top, _, sub = name.partition(".")
        if top not in loaded or top not in current:
            continue
        if sub:
            inner = current.get(top) if isinstance(current.get(top), Mapping) else {}
            now = (inner or {}).get(sub)
        else:
            now = current.get(top)
        if _plain(now) != _plain(was):
            changed.append(name)
    return changed


def not_kept(body: Mapping[str, Any], answer: Mapping[str, Any]) -> tuple[str, ...]:
    """The sent fields the answer shows otherwise (left-out fields cannot be checked)."""
    missed = []
    for name, sent, found in _pairs(body, answer):
        top = name.partition(".")[0]
        if top not in answer:
            continue
        if _plain(found) != _plain(sent):
            missed.append(name)
    return tuple(missed)


def restore_body(body: Mapping[str, Any], before: Mapping[str, Any]) -> dict[str, Any]:
    """The body that puts back what *body* changed, from *before* (write-only fields skipped)."""
    out: dict[str, Any] = {}
    for key, sent in body.items():
        if key in WRITE_ONLY:
            continue
        old = before.get(key)
        if isinstance(sent, Mapping) and not ("raw" in sent or "rendered" in sent):
            inner = old if isinstance(old, Mapping) else {}
            out[key] = {k: inner.get(k, "") for k in sent}
            continue
        out[key] = _plain(old) if isinstance(old, Mapping) else old
    return out


def checked_write(
    api: Any,
    route: str,
    body: Mapping[str, Any],
    loaded: Mapping[str, Any],
    *,
    name: str,
    site: str,
    read_route: str = "",
) -> Written:
    """Re-read, refuse on a conflict, write, verify. Runs off the UI thread.

    *read_route* is where the object is read when it differs from where it is
    written (a shipping zone's locations are written to their own route).
    """
    current = reread(api, read_route or route)
    changed = changed_since(loaded, current, body)
    if changed:
        raise EditConflict(
            f"{name} was changed on {site} after QUILL read it ({', '.join(changed)}). "
            "Nothing was sent. F5 reads it again."
        )
    answer = api.post(route, dict(body))
    answer = answer if isinstance(answer, dict) else {}
    return Written(answer, not_kept(body, answer), restore_body(body, current or loaded))


def outcomes_report(outcomes: Sequence[Outcome], what: str) -> tuple[str, str]:
    """A spoken sentence and a line-a-item report for a batch."""
    done = sum(1 for o in outcomes if o.ok)
    failed = len(outcomes) - done
    said = f"{what}: {done} done" + (f", {failed} not done." if failed else ".")
    return said, "\n".join(o.said for o in outcomes)
