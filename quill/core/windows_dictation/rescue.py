"""Never lose what was said: words not written, kept on disk until delivered.

D-5 of the 2026-10-13 dictation gap plan. A crash, a sleep or a forced exit used
to lose every phrase held while dictation was paused for its field, and a
phrase Windows stopped typing part-way through. This module keeps exactly those
**uncommitted** words on disk, and nothing that was written:

* **held** -- the phrases held while paused (``target_hold.py``), one entry for
  each pause, rewritten as the held list changes;
* **unwritten** -- a phrase whose writing failed or stopped part-way.

An open review (D-2) already keeps itself in ``dictation-review.json``
(:mod:`~quill.core.windows_dictation.review_session`); Recent Phrases offers it
from there rather than copying it here.

Each entry is deleted when it is delivered (Insert Again, Resume) or discarded
(Discard, Discard Held Words); stopping, failing and the app ending keep it, so
the next start can say so. Entries live in ``recovery/live-dictation/`` under
the host's data folder, one file each, written atomically, and the words are
sealed with Windows DPAPI (:mod:`quill.platform.windows.dpapi`) so another
Windows account cannot read them. When the words cannot be sealed, nothing is
written: they stay in memory, as they always did. Nothing here logs the words.

**History** (``windows_dictation_history_days``: 0 off, 1, 7 or 30) is the
opt-in other half: every phrase written, text only, never audio, sealed the same
way, pruned to its days on every write and read, and deleted whole when it is
turned off or cleared. Off by default.

wx-free.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "HISTORY_CHOICES",
    "KIND_LABELS",
    "DictationKeep",
    "Kept",
    "coerce_history_days",
    "keep_for",
    "kept_notice",
]

#: (days, label) for More Dictation Settings. 0 is off, the default.
HISTORY_CHOICES: tuple[tuple[int, str], ...] = (
    (0, "Off"),
    (1, "One day"),
    (7, "Seven days"),
    (30, "Thirty days"),
)
_SCHEMA = 1
_ENTROPY = b"quill-dictation-rescue"
#: How many phrases the history keeps at most, whatever its days.
_HISTORY_CAP = 2000

#: What the Recent Phrases list says before a kept entry's words.
KIND_LABELS = {
    "held": "Not written, held while paused",
    "unwritten": "Not written, typing stopped",
    "review": "Review not finished",
}


def coerce_history_days(value: object) -> int:
    """A saved history length; anything else is off."""
    try:
        days = int(str(value))
    except (TypeError, ValueError):
        return 0
    return days if days in {choice for choice, _label in HISTORY_CHOICES} else 0


def _seal(text: str) -> str:
    from quill.platform.windows.dpapi import protect_secret

    return protect_secret(text, _ENTROPY)


def _unseal(blob: str) -> str:
    from quill.platform.windows.dpapi import unprotect_secret

    return unprotect_secret(blob, _ENTROPY)


@dataclass(frozen=True, slots=True)
class Kept:
    """One kept entry: words not written, or a phrase from the history."""

    entry_id: str
    kind: str
    text: str
    saved_at: float

    @property
    def label(self) -> str:
        """The row Recent Phrases shows: what it is, then the words."""
        when = time.strftime("%d %B, %H:%M", time.localtime(self.saved_at)).lstrip("0")
        if self.kind == "history":
            return f"Earlier, {when}: {self.text}"
        return f"{KIND_LABELS.get(self.kind, 'Not written')}, {when}: {self.text}"


class DictationKeep:
    """One app's kept words in one data folder. Every method answers; none raises."""

    def __init__(
        self,
        data_dir: Path,
        app: str,
        *,
        seal: Callable[[str], str] = _seal,
        unseal: Callable[[str], str] = _unseal,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.app = "".join(ch for ch in app.lower() if ch.isalnum()) or "quill"
        self.root = Path(data_dir) / "recovery" / "live-dictation"
        self.history_path = Path(data_dir) / f"dictation-history-{self.app}.json"
        self._seal = seal
        self._unseal = unseal
        self._clock = clock
        #: The history phrases added this run, which Recent Phrases already lists.
        self._added: set[float] = set()

    # -- words not written --------------------------------------------------- #

    def _path(self, entry_id: str) -> Path:
        return self.root / f"{self.app}-{entry_id}.json"

    def keep(self, kind: str, text: str, entry_id: str = "") -> str:
        """Keep *text* (or replace entry *entry_id*); returns the id, ``""`` when
        it could not be kept. Empty *text* drops the entry instead."""
        entry_id = entry_id or uuid.uuid4().hex[:12]
        if not text.strip():
            self.drop(entry_id)
            return entry_id
        try:
            sealed = self._seal(text)
            from quill.core.storage import write_json_atomic

            self.root.mkdir(parents=True, exist_ok=True)
            write_json_atomic(
                self._path(entry_id),
                {"schema": _SCHEMA, "kind": kind, "saved_at": self._clock(), "text": sealed},
            )
        except Exception:  # noqa: BLE001 - kept in memory instead, as before D-5
            return ""
        return entry_id

    def drop(self, entry_id: str) -> None:
        """Delivered or discarded: nothing to bring back."""
        if not entry_id:
            return
        try:
            self._path(entry_id).unlink(missing_ok=True)
        except OSError:
            pass

    def kept(self) -> list[Kept]:
        """Every entry this app kept, oldest first."""
        out: list[Kept] = []
        try:
            files = sorted(self.root.glob(f"{self.app}-*.json"))
        except OSError:
            return out
        for path in files:
            entry = self._read(path, path.stem[len(self.app) + 1 :])
            if entry is not None:
                out.append(entry)
        return sorted(out, key=lambda entry: entry.saved_at)

    def _read(self, path: Path, entry_id: str) -> Kept | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            text = self._unseal(str(data["text"]))
        except Exception:  # noqa: BLE001 - unreadable (another account, damaged): skipped
            return None
        if not text.strip():
            return None
        return Kept(entry_id, str(data.get("kind", "held")), text, float(data.get("saved_at", 0)))

    # -- history (opt-in) ------------------------------------------------------ #

    def _history(self) -> list[dict[str, object]]:
        try:
            data = json.loads(self.history_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        rows = data.get("phrases", []) if isinstance(data, dict) else []
        return [row for row in rows if isinstance(row, dict)]

    def _write_history(self, rows: list[dict[str, object]]) -> None:
        if not rows:
            self.clear_history()
            return
        from quill.core.storage import write_json_atomic

        try:
            write_json_atomic(self.history_path, {"schema": _SCHEMA, "phrases": rows})
        except Exception:  # noqa: BLE001 - history is a convenience, never a failure
            pass

    def _fresh(self, rows: list[dict[str, object]], days: int) -> list[dict[str, object]]:
        oldest = self._clock() - days * 86400
        return [row for row in rows if float(str(row.get("at", 0))) >= oldest][-_HISTORY_CAP:]

    def remember(self, text: str, days: int) -> None:
        """Add a written phrase to the history; with *days* 0, there is none."""
        days = coerce_history_days(days)
        if not days:
            self.clear_history()
            return
        if not text.strip():
            return
        try:
            sealed = self._seal(text)
        except Exception:  # noqa: BLE001 - not sealed, not kept
            return
        rows = self._fresh(self._history(), days)
        at = self._clock()
        self._added.add(at)
        rows.append({"at": at, "text": sealed})
        self._write_history(rows)

    def history(self, days: int, *, earlier_only: bool = True) -> list[Kept]:
        """The history, newest first; *earlier_only* leaves out this run's
        phrases, which Recent Phrases already lists."""
        days = coerce_history_days(days)
        if not days:
            return []
        rows = self._history()
        fresh = self._fresh(rows, days)
        if len(fresh) != len(rows):
            self._write_history(fresh)
        out: list[Kept] = []
        for index, row in enumerate(fresh):
            at = float(str(row.get("at", 0)))
            if earlier_only and at in self._added:
                continue
            try:
                text = self._unseal(str(row.get("text", "")))
            except Exception:  # noqa: BLE001 - unreadable: skipped
                continue
            out.append(Kept(f"h{index}:{at!r}", "history", text, at))
        return out[::-1]

    def forget(self, entry: Kept) -> None:
        """Take one phrase out of the history."""
        rows = self._history()
        _index, _sep, at = entry.entry_id[1:].partition(":")
        kept = [row for row in rows if repr(float(str(row.get("at", 0)))) != at]
        if len(kept) != len(rows):
            self._write_history(kept)

    def clear_history(self) -> bool:
        """Delete the whole history. ``True`` when there was one."""
        try:
            existed = self.history_path.exists()
            self.history_path.unlink(missing_ok=True)
        except OSError:
            return False
        return existed


_keeps: dict[tuple[str, str], DictationKeep] = {}


def keep_for(data_dir: Path, app: str) -> DictationKeep:
    """The one :class:`DictationKeep` for *app* in *data_dir* this run."""
    key = (str(Path(data_dir)), app)
    keep = _keeps.get(key)
    if keep is None:
        keep = _keeps[key] = DictationKeep(Path(data_dir), app)
    return keep


def kept_notice(count: int, where: str) -> str:
    """Said once at start when words from last time are waiting; ``""`` for none."""
    if count <= 0:
        return ""
    things = "1 dictated phrase was" if count == 1 else f"{count} dictated phrases were"
    return f"{things} not written last time and {'is' if count == 1 else 'are'} kept. {where}"
