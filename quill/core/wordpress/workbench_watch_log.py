"""What Watches said, kept; one refusal per Watch; one announcement per round.

Review item 27 (complete.md 2.6): Watches were fire-and-forget. Nothing they
said was kept, one refused read silenced every Watch on that site for the
round, and a busy round spoke as a burst of separate announcements. This
module holds the three cures, so :mod:`quill.core.wordpress.workbench_watches`
only has to call them:

- :func:`remember` keeps the newest :data:`KEPT` sentences, with when they were
  said, in the Watches state file; :func:`recent` reads them back for the
  Watches node in the Workbench.
- :func:`guarded` runs one Watch on one site, so a site that refuses one read
  (a plugin's route needing a role you lack, say) costs only that Watch. The
  refusal is said once, and again only after it has worked in between.
- :func:`one_announcement` turns a round's sentences into one thing to say.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from typing import Any

from quill.core.counted import plural
from quill.core.wordpress.api import WordPressApiError

__all__ = ["KEPT", "guarded", "one_announcement", "recent", "remember"]

#: How many sentences the Watches node keeps, newest first.
KEPT = 100


def _slot(state: Any, name: str) -> dict[str, Any]:
    slot = state.extra.get(name)
    if not isinstance(slot, dict):
        slot = state.extra[name] = {}
    return slot


def remember(state: Any, said: Sequence[str], moment: float | None = None) -> None:
    """Keep *said*, stamped with *moment*, newest first, at most :data:`KEPT`."""
    if not said:
        return
    stamp = time.time() if moment is None else moment
    slot = _slot(state, "said")
    log = [entry for entry in slot.get("log", []) if isinstance(entry, list) and len(entry) == 2]
    slot["log"] = ([[stamp, sentence] for sentence in reversed(said)] + log)[:KEPT]


def recent(state: Any, count: int = 20) -> list[tuple[float, str]]:
    """The newest *count* things Watches said, as (when, sentence)."""
    log = _slot(state, "said").get("log", [])
    found: list[tuple[float, str]] = []
    for entry in log[:count]:
        try:
            found.append((float(entry[0]), str(entry[1])))
        except (TypeError, ValueError, IndexError):
            continue
    return found


def guarded(
    state: Any, site: str, kind: str, label: str, run: Callable[[], list[str]]
) -> list[str]:
    """*run* one Watch for *site*; a refusal stops only it, and is said once."""
    refused = _slot(state, "refused")
    key = f"{site}:{kind}"
    try:
        said = run()
    except WordPressApiError as error:
        if key in refused:
            return []
        why = str(error.args[0]) if error.args else str(error)  # the site's words, no code
        refused[key] = why
        return [f"The Watch for {label} could not read {site}, so it skips that site: {why}"]
    if refused.pop(key, None) is not None:
        said = [f"The Watch for {label} reads {site} again.", *said]
    return said


def one_announcement(said: Sequence[str]) -> str:
    """A round's sentences as one announcement: a count first when there are several."""
    if not said:
        return ""
    if len(said) == 1:
        return said[0]
    return f"Watches found {plural(len(said), 'thing')}. " + " ".join(said)
