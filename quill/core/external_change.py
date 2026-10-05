"""External file-change detection and safe-reload decisions (FEAT-19).

A small, UI-agnostic helper that watches the open document's file for external
modification or deletion and decides what should happen, without ever touching
``wx`` or moving the cursor itself. The UI layer owns the editor buffer and is
responsible for preserving the cursor, selection, and scroll position when it
acts on a decision; this module only answers *what* should happen.

The model is deliberately pure and testable:

* :class:`FileSnapshot` captures the on-disk identity of a file (existence,
  size, modification time, and a content hash) at a point in time.
* :class:`ExternalChangeWatcher` remembers the last snapshot it reported and,
  on each poll, classifies the file as unchanged, modified, or deleted.
* :func:`decide_reload` turns a change plus the buffer's dirty state and the
  user's settings into one of a small set of :class:`ReloadDecision` actions.

The watcher is polled (reusing the existing watch-folder polling pattern) off
the UI thread; the decision functions are synchronous and side-effect free.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Change classifications reported by the watcher.
CHANGE_NONE = "none"
CHANGE_MODIFIED = "modified"
CHANGE_DELETED = "deleted"


class ReloadAction(Enum):
    """What the UI should do in response to an external change."""

    NONE = "none"
    RELOAD = "reload"
    KEEP_MINE = "keep_mine"
    PROMPT_CLEAN = "prompt_clean"
    PROMPT_CONFLICT = "prompt_conflict"
    PROMPT_DELETED = "prompt_deleted"


@dataclass(frozen=True, slots=True)
class ReloadDecision:
    """An action plus a ready-to-speak announcement for the UI to honor."""

    action: ReloadAction
    announcement: str

    @property
    def needs_prompt(self) -> bool:
        return self.action in (
            ReloadAction.PROMPT_CLEAN,
            ReloadAction.PROMPT_CONFLICT,
            ReloadAction.PROMPT_DELETED,
        )


@dataclass(frozen=True, slots=True)
class FileSnapshot:
    """The on-disk identity of a file at one moment.

    ``exists`` is ``False`` for a missing/deleted file, in which case the other
    fields are zeroed. ``digest`` is a content hash so a save that rewrites the
    same bytes (or only touches the mtime) is correctly seen as *unchanged*.
    """

    exists: bool
    size: int = 0
    mtime_ns: int = 0
    digest: str = ""

    @classmethod
    def of(cls, path: str | Path) -> FileSnapshot:
        """Snapshot ``path`` now. A missing or unreadable file is ``exists=False``."""
        file_path = Path(path)
        try:
            stat = file_path.stat()
        except (OSError, ValueError):
            return cls(exists=False)
        digest = _hash_file(file_path)
        if digest is None:
            return cls(exists=False)
        return cls(
            exists=True,
            size=int(stat.st_size),
            mtime_ns=int(stat.st_mtime_ns),
            digest=digest,
        )

    def same_content_as(self, other: FileSnapshot) -> bool:
        """True when both exist and hold identical content (ignoring mtime)."""
        if not (self.exists and other.exists):
            return False
        return self.size == other.size and self.digest == other.digest


def _hash_file(path: Path, *, chunk_size: int = 65536) -> str | None:
    """Return a hex SHA-256 of ``path``'s bytes, or None if it can't be read."""
    hasher = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(chunk_size), b""):
                hasher.update(chunk)
    except (OSError, ValueError):
        return None
    return hasher.hexdigest()


def classify_change(previous: FileSnapshot, current: FileSnapshot) -> str:
    """Classify the transition from ``previous`` to ``current`` (pure).

    Returns :data:`CHANGE_NONE`, :data:`CHANGE_MODIFIED`, or
    :data:`CHANGE_DELETED`. A file that never existed and still does not is
    ``CHANGE_NONE``; a file that reappears with new content is ``CHANGE_MODIFIED``.
    """
    if not current.exists:
        return CHANGE_DELETED if previous.exists else CHANGE_NONE
    if not previous.exists:
        # The file (re)appeared where we had none — treat as a modification so
        # the UI can offer to load it rather than silently ignoring it.
        return CHANGE_MODIFIED
    return CHANGE_NONE if current.same_content_as(previous) else CHANGE_MODIFIED


class ExternalChangeWatcher:
    """Remembers the last reported snapshot of one file and reports changes.

    Construct with the file's path; :meth:`prime` records the baseline (call it
    right after opening or saving). :meth:`poll` re-snapshots and returns the
    classification relative to the last reported state, advancing the baseline
    so each external change is reported exactly once.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._last = FileSnapshot.of(self._path)

    @property
    def path(self) -> Path:
        return self._path

    @property
    def last(self) -> FileSnapshot:
        return self._last

    def prime(self, snapshot: FileSnapshot | None = None) -> None:
        """Reset the baseline to ``snapshot`` (or a fresh on-disk snapshot)."""
        self._last = snapshot if snapshot is not None else FileSnapshot.of(self._path)

    def poll(self) -> str:
        """Re-snapshot and return the change since the last reported state."""
        current = FileSnapshot.of(self._path)
        change = classify_change(self._last, current)
        if change != CHANGE_NONE:
            self._last = current
        return change


#: The two answers a person can ask to have remembered for a file format.
REMEMBER_RELOAD = "reload"
REMEMBER_KEEP = "keep"


def format_key(file_name: str) -> str:
    """The remembered-answer key for a file: its lower-case suffix, or "".

    A file format, not a file. "Do not ask me again about .docx" is a statement
    about how Word behaves, and the person making it is not thinking about one
    document.
    """
    suffix = Path(file_name).suffix.lower()
    return suffix if suffix else ""


def remembered_answer(
    file_name: str,
    *,
    always_reload: Sequence[str] = (),
    always_keep: Sequence[str] = (),
) -> str:
    """The answer this person asked to have remembered for this file format.

    ``""`` when there is none, which is the normal case and means ask. Reload
    wins a format listed in both: of the two ways to be wrong, quietly showing
    text that is no longer on disk is the one nobody notices.
    """
    key = format_key(file_name)
    if not key:
        return ""
    if key in {str(item).lower() for item in always_reload}:
        return REMEMBER_RELOAD
    if key in {str(item).lower() for item in always_keep}:
        return REMEMBER_KEEP
    return ""


def decide_reload(
    change: str,
    *,
    buffer_dirty: bool,
    watch_enabled: bool = True,
    auto_reload_when_clean: bool = False,
    prompt_on_conflict: bool = True,
    file_name: str = "",
    remembered: str = "",
) -> ReloadDecision:
    """Decide what to do for ``change`` given the buffer state and settings (pure).

    **Nothing reloads silently by default** (bad.md F5, decided 2026-09-18).
    QUILL used to replace a clean tab in place whenever the file changed, which
    is right for a text file a build regenerates and wrong for everything else:
    a ``.docx`` rewritten by Word came back as its own bytes decoded into
    replacement characters, marked clean, with nothing said. A person who
    cannot see the screen change has no cue at all that the text under the
    caret is no longer the text they were reading.

    So a change asks -- every format, dirty or clean -- and the question
    carries a "do not ask me again for this format" answer, so somebody whose
    build rewrites ``.md`` files every few seconds says so once
    (:func:`remembered_answer`). ``auto_reload_when_clean`` remains as the
    blanket escape hatch for anyone who wants the old behaviour for every
    format at once, and now defaults to off.

    * Watching off, or no change → do nothing.
    * A remembered answer for this format → take it, without asking -- except
      a remembered reload while the buffer has unsaved edits, which asks.
    * Modified while the buffer is clean → ask (or reload, under the blanket
      setting).
    * Modified while the buffer is dirty → never overwrite silently; ask for
      reload / keep-mine / compare (when prompting is on), else stay quiet.
    * Deleted → ask; the buffer is kept so the user's text is never lost.
    """
    if not watch_enabled or change == CHANGE_NONE:
        return ReloadDecision(ReloadAction.NONE, "")

    label = f" ({file_name})" if file_name else ""

    if change == CHANGE_DELETED:
        if prompt_on_conflict:
            return ReloadDecision(
                ReloadAction.PROMPT_DELETED,
                f"The file{label} was deleted on disk. Keep your text or close.",
            )
        return ReloadDecision(ReloadAction.NONE, "")

    # change == CHANGE_MODIFIED
    # A remembered "always reload" was given about a clean tab. With unsaved
    # edits it would throw them away unasked, so it does not apply: the dirty
    # branch below asks the normal question (family rule 4 -- a destructive
    # habit is fixed first). "Always keep" discards nothing and still applies.
    if remembered == REMEMBER_RELOAD and not buffer_dirty:
        return ReloadDecision(ReloadAction.RELOAD, f"Reloaded{label} from disk.")
    if remembered == REMEMBER_KEEP:
        return ReloadDecision(
            ReloadAction.KEEP_MINE,
            f"The file{label} changed on disk. Keeping what is open, as you asked.",
        )

    if buffer_dirty:
        if prompt_on_conflict:
            return ReloadDecision(
                ReloadAction.PROMPT_CONFLICT,
                f"The file{label} changed on disk and you have unsaved edits. "
                "Reload, keep mine, or compare.",
            )
        return ReloadDecision(ReloadAction.NONE, "")

    if auto_reload_when_clean:
        return ReloadDecision(ReloadAction.RELOAD, "Reloaded from disk.")
    return ReloadDecision(
        ReloadAction.PROMPT_CLEAN,
        f"The file{label} changed on disk. Reload to see the new version.",
    )


def changed_since(baseline: FileSnapshot | None, path: str | Path) -> FileSnapshot | None:
    """The snapshot on disk now, if it differs from *baseline*; else ``None``.

    The save-time check both editors run right before writing (2026-10-04,
    from the PlanCake design note): the watcher polls, and a change that lands
    between two polls used to be overwritten by the next Save without a word.
    No baseline, or a file that is gone, is not a conflict -- there is nothing
    on disk for the save to destroy.
    """
    if baseline is None or not baseline.exists:
        return None
    current = FileSnapshot.of(path)
    if not current.exists:
        return None
    return None if classify_change(baseline, current) == CHANGE_NONE else current


# -- Shared by both editors' watchers (2026-10-04) ------------------------------
#
# QUILL's watcher lived in its UI mixin; QUILL Lite gained one the same day, and
# QUILL Lite may never have a second implementation. Everything below is the
# part both of them decide: what the settings say, which answers are kept, and
# the sentences. The wx half (the timer and the question) is in
# ``quill/ui/external_change_timer.py`` and ``quill/ui/external_change_dialog.py``.


@dataclass(frozen=True, slots=True)
class DiskPoll:
    """One cheap look at a watched file.

    ``change`` is :data:`CHANGE_NONE` when there is nothing new to report. With
    no change, ``current`` is set only when the file was re-read and found to
    hold the same bytes (it was touched, not changed): the caller adopts it as
    the baseline so the next poll is a stat again rather than another hash.
    """

    change: str
    current: FileSnapshot | None = None


def _same_stat(snapshot: FileSnapshot, size: int, mtime_ns: int) -> bool:
    return snapshot.exists and snapshot.size == size and snapshot.mtime_ns == mtime_ns


def poll_disk(
    path: str | Path,
    baseline: FileSnapshot | None,
    reported: FileSnapshot | None = None,
) -> DiskPoll:
    """What happened to *path* since *baseline*, reading the bytes only if needed.

    A stat on every poll and a hash only when the size or modification time
    moved, so watching nine open documents costs nine stats a second. *reported*
    is the change already reported for this baseline, so one change is reported
    once however many polls see it.
    """
    if baseline is None:
        return DiskPoll(CHANGE_NONE)
    try:
        stat = Path(path).stat()
    except (OSError, ValueError):
        if baseline.exists and (reported is None or reported.exists):
            return DiskPoll(CHANGE_DELETED, FileSnapshot(exists=False))
        return DiskPoll(CHANGE_NONE)
    size, mtime_ns = int(stat.st_size), int(stat.st_mtime_ns)
    if _same_stat(baseline, size, mtime_ns):
        return DiskPoll(CHANGE_NONE)
    if reported is not None and _same_stat(reported, size, mtime_ns):
        return DiskPoll(CHANGE_NONE)
    current = FileSnapshot.of(path)
    change = classify_change(baseline, current)
    if change == CHANGE_NONE:
        return DiskPoll(CHANGE_NONE, current if current.exists else None)
    if reported is not None and current.same_content_as(reported):
        return DiskPoll(CHANGE_NONE)
    return DiskPoll(change, current)


def remembered_for(settings: object, file_name: str) -> str:
    """The kept answer for *file_name*'s format under *settings*, or ``""``.

    Both editors store the two lists under the same field names, so this reads
    either settings object.
    """
    return remembered_answer(
        file_name,
        always_reload=list(getattr(settings, "external_change_always_reload", []) or []),
        always_keep=list(getattr(settings, "external_change_always_keep", []) or []),
    )


def decide_for(
    change: str,
    settings: object,
    *,
    buffer_dirty: bool,
    file_name: str,
) -> ReloadDecision:
    """:func:`decide_reload` with the four settings read from *settings*."""
    return decide_reload(
        change,
        buffer_dirty=buffer_dirty,
        watch_enabled=bool(getattr(settings, "external_change_watch_enabled", True)),
        auto_reload_when_clean=bool(
            getattr(settings, "external_change_auto_reload_when_clean", False)
        ),
        prompt_on_conflict=bool(getattr(settings, "external_change_prompt_on_conflict", True)),
        file_name=file_name,
        remembered=remembered_for(settings, file_name),
    )


def remember_answer(settings: object, file_name: str, value: str) -> bool:
    """Keep "always reload" or "always keep" for *file_name*'s format.

    One answer per format: the other list gives the key up, so changing your
    mind later is one check box rather than a contradiction on disk. ``True`` when
    something was recorded, so the caller knows to save.
    """
    key = format_key(file_name) if value else ""
    if not key:
        return False
    reload_list = list(getattr(settings, "external_change_always_reload", []) or [])
    keep_list = list(getattr(settings, "external_change_always_keep", []) or [])
    target, other = (
        (reload_list, keep_list) if value == REMEMBER_RELOAD else (keep_list, reload_list)
    )
    if key not in target:
        target.append(key)
    if key in other:
        other.remove(key)
    settings.external_change_always_reload = reload_list  # type: ignore[attr-defined]
    settings.external_change_always_keep = keep_list  # type: ignore[attr-defined]
    return True


def forget_answers(settings: object) -> int:
    """Clear every kept answer; how many there were."""
    count = len(getattr(settings, "external_change_always_reload", []) or []) + len(
        getattr(settings, "external_change_always_keep", []) or []
    )
    if count:
        settings.external_change_always_reload = []  # type: ignore[attr-defined]
        settings.external_change_always_keep = []  # type: ignore[attr-defined]
    return count


def forget_answers_sentence(count: int, app_name: str) -> str:
    """What to say after :func:`forget_answers`."""
    if not count:
        return "No file formats are being answered for you."
    return (
        f"Forgot {count} remembered file-format answer{'s' if count != 1 else ''}. "
        f"{app_name} will ask again when a file changes on disk."
    )


def poll_interval_ms(settings: object) -> int:
    """How often to look, from ``external_change_debounce_ms``; never below 100.

    Zero is a legal value of the setting and would make a repeating timer spin.
    """
    try:
        value = int(getattr(settings, "external_change_debounce_ms", 750))
    except (TypeError, ValueError):
        value = 750
    return max(100, value)


def reloaded_sentence(file_name: str) -> str:
    """Said once after a quiet reload."""
    return f"Reloaded {file_name}: changed by another program."


def deleted_sentence(file_name: str) -> str:
    """Said once when the file is deleted or moved away."""
    return (
        f"{file_name} was deleted or moved by another program. Your text is still "
        "here and is not saved; use Save As to keep it."
    )
