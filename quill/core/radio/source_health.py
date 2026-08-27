"""How each browse source has been doing, this session.

:mod:`quill.core.radio.browse_failure` answers a question about **one call**:
was that empty folder empty, or broken? It answers it per thread and clears on
every entry, deliberately, so one branch's failure can never describe another
branch's empty folder.

What nothing answered until now is the question about a **source over time**:
*has this directory been failing all afternoon?* A listener who opens TuneIn
three times and waits out three twelve-second timeouts is told "could not be
reached" three times, in identical words, with no hint that the first two were
the same outage. That is the difference between a hiccup and a dead source, and
it is exactly what the StreamTuner-ng review (``radio2.md``, part IV) recorded
as the piece Quill Radio was missing: it keeps consecutive-failure counts per
plugin and trips a source off after three.

This is that idea with two deliberate differences:

* **In-process, session-scoped.** Nothing is written to settings. A restart
  starts every source clean, which is right for a fault that is usually
  somebody else's outage and is usually over by tomorrow -- and it means this
  module cannot corrupt, migrate or leak anything.
* **It never switches a source off by itself.** StreamTuner-ng auto-disables
  after three strikes. Here the count is *reported* and the listener decides:
  a source that silently vanishes from the tree is a worse failure than the
  one it was trying to hide, and a directory that recovers must not stay dead
  until somebody finds the checkbox that re-arms it. Browse Sources is one
  keystroke away for anyone who does want it gone.

The unit is the **node kind** (``shoutcast``, ``live365``, ``tunein``), because
that is what :func:`quill.core.radio.browse_sources.browse` dispatches on and
what the Browse Sources list already names.

wx-free, strict-typed, thread-safe (browse runs on the task manager while the
UI thread reads these counts).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, replace

#: Consecutive failures after which a source is described as being in trouble
#: rather than merely having failed. Three, the same threshold StreamTuner-ng
#: uses to auto-disable -- but here it changes what is *said*, not what is done.
TROUBLE_THRESHOLD = 3

#: How long an error message may be before it is trimmed for display. A
#: TimeoutError's text is short; a urllib chain's is not, and this is read
#: aloud.
_MESSAGE_LIMIT = 120


@dataclass(frozen=True, slots=True)
class SourceHealth:
    """One source's record for this session."""

    source_id: str
    #: ``"unknown"`` (not tried), ``"ok"``, ``"empty"`` (reached, nothing to
    #: show) or ``"error"``. Empty is deliberately not an error: a genre with
    #: no stations in it is a true answer.
    status: str = "unknown"
    message: str = ""
    consecutive_errors: int = 0
    error_count: int = 0
    ok_count: int = 0

    @property
    def in_trouble(self) -> bool:
        """True once this source has failed :data:`TROUBLE_THRESHOLD` times in a row."""
        return self.consecutive_errors >= TROUBLE_THRESHOLD


_LOCK = threading.Lock()
_HEALTH: dict[str, SourceHealth] = {}


def _key(source_id: object) -> str:
    return str(source_id or "").strip()


def _update(source_id: str, **changes: object) -> SourceHealth:
    with _LOCK:
        current = _HEALTH.get(source_id, SourceHealth(source_id))
        updated = replace(current, **changes)  # type: ignore[arg-type]
        _HEALTH[source_id] = updated
        return updated


def record_ok(source_id: object, *, empty: bool = False) -> SourceHealth:
    """A browse succeeded. *empty* means it answered, with nothing in it.

    Either way the failure streak ends: a source that answers is not broken,
    and treating an empty genre as a fault would have every listener told a
    working directory is down.
    """
    key = _key(source_id)
    if not key:
        return SourceHealth("")
    current = health(key)
    return _update(
        key,
        status="empty" if empty else "ok",
        message="",
        consecutive_errors=0,
        ok_count=current.ok_count + 1,
    )


def record_error(source_id: object, error: object = "") -> SourceHealth:
    """A browse failed. Increments the streak and remembers the last reason."""
    key = _key(source_id)
    if not key:
        return SourceHealth("")
    current = health(key)
    text = str(error).strip() or type(error).__name__
    if len(text) > _MESSAGE_LIMIT:
        text = text[: _MESSAGE_LIMIT - 1].rstrip() + "…"
    return _update(
        key,
        status="error",
        message=text,
        consecutive_errors=current.consecutive_errors + 1,
        error_count=current.error_count + 1,
    )


def health(source_id: object) -> SourceHealth:
    """This source's record. A source never tried is ``"unknown"``, not an error."""
    key = _key(source_id)
    with _LOCK:
        return _HEALTH.get(key, SourceHealth(key))


def consecutive_failures(source_id: object) -> int:
    """How many times in a row this source has failed. ``0`` when it last worked."""
    return health(source_id).consecutive_errors


def in_trouble(source_id: object) -> bool:
    """True when this source has failed :data:`TROUBLE_THRESHOLD` times running."""
    return health(source_id).in_trouble


def status_text(source_id: object) -> str:
    """A short status for a list column, in words rather than a colour.

    StreamTuner-ng shows a coloured dot. A colour is exactly the wrong carrier
    here -- it is unreadable to the listener this application is built for, and
    unspeakable by any screen reader -- so the same six states are said out
    loud instead.
    """
    record = health(source_id)
    if record.status == "unknown":
        return "Not tried yet"
    if record.status == "ok":
        return "OK"
    if record.status == "empty":
        return "Nothing found"
    if record.consecutive_errors > 1:
        return f"Failed {record.consecutive_errors} times in a row"
    return "Failed once"


def failure_note(source_id: object) -> str:
    """The extra clause an empty branch should add, or ``""``.

    Said only once a source has failed more than once: the first failure is
    already explained by "could not be reached", and repeating a count of one
    would be noise on every transient blip.
    """
    record = health(source_id)
    if record.status != "error" or record.consecutive_errors < 2:
        return ""
    if record.in_trouble:
        return (
            f"It has failed {record.consecutive_errors} times in a row -- the directory itself "
            "may be down. You can hide it in Browse Sources."
        )
    return f"It has failed {record.consecutive_errors} times in a row."


def snapshot() -> dict[str, SourceHealth]:
    """Every source's record, for a settings list or a diagnostic bundle."""
    with _LOCK:
        return dict(_HEALTH)


def reset(source_id: object = "") -> None:
    """Forget one source's record, or (with no argument) all of them."""
    key = _key(source_id)
    with _LOCK:
        if key:
            _HEALTH.pop(key, None)
        else:
            _HEALTH.clear()
