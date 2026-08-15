"""Carrying your place between machines: the adapter that was missing.

Everything underneath this existed and nothing connected it. The engine
(:mod:`quill.core.sync.engine`) commits, pushes and pulls encrypted records.
``core/media/positions.PositionStore`` already satisfied its ``RecordStore``
protocol and ``merge_positions`` its ``MergeFn``. Quill Radio's
``core/radio/resume.ResumeStore`` now does too. What did not exist was anything
that *moved a record*, which is this module.

**Two stores, one vault, one folder.** The plan flagged this as worth settling
before an adapter was written, so: the media store keys on a file's contents and
the radio store keys on a normalised stream identity, and no single key can mean
both. They therefore stay two stores and sync as **two entity types over two
commit logs**, sharing one recovery phrase and one remote folder in separate
subdirectories. Merging them into one identity space would mean inventing a key
that is neither, and every future provider would have to be forced into it too.

**Bring your own remote.** The transport is a folder
(:class:`~quill.core.sync.transports.FolderTransport`), which in practice is a
folder inside whatever the listener already syncs -- OneDrive, Dropbox, iCloud
Drive, a network share, a USB stick carried between two machines. QUILL runs no
server and holds nobody's listening history. The contents are encrypted before
they reach it, so the folder's provider learns nothing but sizes and timings.

**Local-first, always.** Sync is additive. Nothing here is called on a playback
path, nothing waits on it to start playing, and a remote that has gone missing
produces a sentence rather than a broken app.

wx-free, strict-typed. The task manager and the words belong to the caller.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from quill.core.sync.crypto import VaultKey
from quill.core.sync.engine import SyncEngine
from quill.core.sync.protocol import Conflict, MergeFn
from quill.core.sync.transports import FolderTransport

#: The two things that follow you, and where each lives in the remote folder.
#: Named rather than numbered so a folder somebody opens is legible.
PLACES_STORES: tuple[str, ...] = ("positions", "recordings")

#: How each is described out loud.
STORE_LABELS: dict[str, str] = {
    "positions": "books and files",
    "recordings": "streamed recordings",
}


@dataclass(slots=True)
class SyncReport:
    """What one sync did, in numbers and in sentences."""

    pushed: int = 0
    pulled: int = 0
    conflicts: list[Conflict] = field(default_factory=list)
    #: Anything that failed, already phrased for a listener.
    problems: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.pushed or self.pulled)

    def summary(self) -> str:
        """One sentence. Says nothing happened when nothing did.

        "Sync finished" after a sync that moved nothing is the message that
        teaches people to ignore the message.
        """
        if self.problems and not self.changed:
            return self.problems[0]
        if not self.changed:
            return "Everything was already up to date."
        parts: list[str] = []
        if self.pulled:
            parts.append(f"brought back {self.pulled} change{'' if self.pulled == 1 else 's'}")
        if self.pushed:
            parts.append(f"sent {self.pushed} change{'' if self.pushed == 1 else 's'}")
        said = f"Sync {' and '.join(parts)}."
        if self.conflicts:
            count = len(self.conflicts)
            said += (
                f" {count} place{'' if count == 1 else 's'} disagreed between machines; "
                "the most recent was kept."
            )
        if self.problems:
            said += f" {self.problems[0]}"
        return said


class EnumerableStore(Protocol):
    """A ``RecordStore`` that can also list what it holds.

    The sync protocol deliberately does not require this -- an adapter over a
    remote system may have no way to enumerate cheaply -- but an adapter that
    *pushes* has to know what to push, and both stores here are small local
    JSON files. Declared here rather than widened in ``protocol.py`` so the
    existing implementers are unaffected.
    """

    def get_record(self, entity_id: str) -> dict | None: ...

    def put_record(self, entity_id: str, record: dict) -> None: ...

    def delete_record(self, entity_id: str) -> None: ...

    def entity_ids(self) -> list[str]: ...


def _media_store(data_dir: Path) -> EnumerableStore:
    from quill.core.media.positions import PositionStore

    return PositionStore(data_dir)


def _radio_store(data_dir: Path) -> EnumerableStore:
    from quill.core.radio.resume import ResumeStore

    return ResumeStore(data_dir)


def _merge_for(store_name: str) -> MergeFn:
    if store_name == "recordings":
        from quill.core.radio.resume import merge_resume_points

        return merge_resume_points
    from quill.core.media.positions import merge_positions

    return merge_positions


def _store_for(store_name: str, data_dir: Path) -> EnumerableStore:
    return _radio_store(data_dir) if store_name == "recordings" else _media_store(data_dir)


def engine_for(
    store_name: str, *, data_dir: Path | str, vault: VaultKey, device: str
) -> SyncEngine:
    """The engine for one of the two stores.

    Each gets its own ``data_dir`` subfolder, and therefore its own commit log:
    two stores writing one log would interleave commits over entity ids that
    mean different things, and the first pull would apply a stream position to a
    file.
    """
    root = Path(data_dir)
    return SyncEngine(
        _store_for(store_name, root),
        vault,
        device=device,
        data_dir=root / "sync-places" / store_name,
        merge_fn=_merge_for(store_name),
        entity_type=store_name,
    )


def _fingerprint(engine: SyncEngine, ids: list[str]) -> str:
    """A stable hash of everything this store currently holds."""
    import hashlib
    import json

    digest = hashlib.sha256()
    for entity_id in sorted(ids):
        record = engine.store.get_record(entity_id)  # noqa: SLF001
        digest.update(entity_id.encode("utf-8"))
        digest.update(json.dumps(record, sort_keys=True, default=str).encode("utf-8"))
    return digest.hexdigest()


def _has_changed(engine: SyncEngine, ids: list[str]) -> bool:
    """Whether anything has changed since the last commit this machine made.

    Without this, syncing twice in a row writes a second identical commit, and a
    machine left running would grow a commit log made entirely of duplicates --
    which costs disk on somebody's cloud folder and makes the log unreadable for
    anybody trying to work out what actually happened.
    """
    marker = engine.data_dir / "sync" / "last-commit.hash"
    current = _fingerprint(engine, ids)
    try:
        previous = marker.read_text(encoding="utf-8").strip()
    except OSError:
        previous = ""
    if previous == current:
        return False
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(current, encoding="utf-8")
    except OSError:
        # An unwritable marker means committing every time, which is wasteful
        # but correct. Never a reason to refuse to sync.
        pass
    return True


def sync_store(
    store_name: str,
    *,
    data_dir: Path | str,
    remote_dir: Path | str,
    vault: VaultKey,
    device: str,
) -> SyncReport:
    """Commit what changed here, send it, and bring back what did not come from here.

    Pull before push, deliberately: applying the other machine's changes first
    means what this one sends is already merged, so a third machine joining
    later sees one coherent history rather than two that have to be reconciled
    again.
    """
    report = SyncReport()
    if not Path(remote_dir).is_dir():
        # Checked before anything else: a cloud folder that has been renamed,
        # unshared or is simply not mounted yet would otherwise report
        # "everything was already up to date", which is the most misleading
        # thing this feature could possibly say.
        report.problems.append(
            "The sync folder is not there. Check that it still exists and that "
            "the drive or cloud folder holding it is available."
        )
        return report
    engine = engine_for(store_name, data_dir=data_dir, vault=vault, device=device)
    transport = FolderTransport(Path(remote_dir) / "quillsync" / store_name)

    store: EnumerableStore = engine.store  # type: ignore[assignment]
    ids = list(store.entity_ids())
    if ids and _has_changed(engine, ids):
        # One commit per sync rather than per record: these are small, they
        # change together, and a log with one entry per position saved would
        # grow without bound for no gain. And no commit at all when nothing
        # changed -- syncing twice in a row must not manufacture history.
        engine.commit(f"{device}: {len(ids)} place(s)", ids)

    try:
        pulled, conflicts = engine.pull(transport)
        report.pulled = pulled
        report.conflicts.extend(conflicts)
    except Exception as error:  # noqa: BLE001 - a remote problem is a sentence
        report.problems.append(f"Could not read the sync folder: {error}")
        return report

    try:
        report.pushed = engine.push(transport)
    except Exception as error:  # noqa: BLE001
        report.problems.append(f"Could not write to the sync folder: {error}")
    return report


def sync_places(
    *,
    data_dir: Path | str,
    remote_dir: Path | str,
    vault: VaultKey,
    device: str,
    stores: tuple[str, ...] = PLACES_STORES,
) -> SyncReport:
    """Both stores, in one pass, reported as one thing.

    One report because "your place follows you" is one promise; a listener does
    not care that a podcast and a LibriVox chapter are remembered by different
    code. A store that fails contributes its problem and costs the other
    nothing.
    """
    combined = SyncReport()
    for store_name in stores:
        try:
            one = sync_store(
                store_name,
                data_dir=data_dir,
                remote_dir=remote_dir,
                vault=vault,
                device=device,
            )
        except Exception as error:  # noqa: BLE001 - never raised at a listener
            combined.problems.append(
                f"{STORE_LABELS.get(store_name, store_name).capitalize()} could not sync: {error}"
            )
            continue
        combined.pushed += one.pushed
        combined.pulled += one.pulled
        combined.conflicts.extend(one.conflicts)
        combined.problems.extend(one.problems)
    return combined
