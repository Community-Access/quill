"""Quill Converter's Auphonic Production History: every production sent, remembered.

The MVP kept only what it needed to resume (``auphonic_pending.json``) and
forgot a production the moment its result was saved. Production History
(``docs/planning/QUILL-Converter-Auphonic-Integration-PRD.md``, section 14)
keeps a short record of every production Quill Converter started -- its
title, how it was sent, its last known status, where its results went and
which files were saved -- so a person can find it again, open its folder,
download its results again, or take it off the list.

The list is local: reading it contacts nobody. **Refresh from Auphonic**
merges the account's recent productions into it (status brought up to date,
productions started elsewhere added); that one read is
:func:`quill.core.publish.auphonic_account.list_productions`. Removing an
entry forgets it here and nowhere else: the production stays in the
Auphonic account.

Like the pending file: never the token, never the media, written atomically
with a schema stamp, and a damaged file reads as an empty history. At most
:data:`MAX_ENTRIES` are kept, newest first. wx-free, strict-typed.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from quill.core.publish.auphonic_plan import SEPARATE, PendingProduction, result_folder

HISTORY_FILE = "auphonic_history.json"
HISTORY_SCHEMA = 1
MAX_ENTRIES = 200

#: States an entry can be in. The first four match the run's outcomes.
SAVED = "saved"
FAILED = "failed"
WAITING = "waiting"
PROCESSING = "processing"
STATE_WORDS: dict[str, str] = {
    SAVED: "results saved",
    FAILED: "failed",
    WAITING: "still at Auphonic, not fetched",
    PROCESSING: "processing at Auphonic",
}
#: Auphonic's status numbers that mean done or failed (the API's 3 and 2).
_DONE, _ERROR = 3, 2


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M")


@dataclass(slots=True)
class HistoryEntry:
    """One production in the history. ``source`` is ``here`` or ``account``."""

    uuid: str
    title: str
    mode: str = SEPARATE
    inputs: list[str] = field(default_factory=list)
    preset_label: str = ""
    out_dir: str = ""
    sent: str = field(default_factory=_now)
    state: str = PROCESSING
    status_string: str = ""
    message: str = ""
    files: list[str] = field(default_factory=list)
    source: str = "here"
    updated: str = field(default_factory=_now)

    def describe(self) -> str:
        """One list row: title, state, when."""
        state = STATE_WORDS.get(self.state, self.state)
        if self.status_string and self.state in {PROCESSING, WAITING}:
            state += f" ({self.status_string})"
        files = (
            f", {len(self.files)} file{'s' if len(self.files) != 1 else ''}" if self.files else ""
        )
        return f"{self.title}: {state}{files}, sent {self.sent}"

    def details(self) -> str:
        """Everything known about the entry, one fact a line, for the details box."""
        what = "Multitrack production" if self.mode == "multitrack" else "Production"
        lines = [
            f"{what}: {self.title}",
            f"Status: {STATE_WORDS.get(self.state, self.state)}"
            + (f"; Auphonic last said {self.status_string}" if self.status_string else "")
            + f" (checked {self.updated}).",
            f"Sent: {self.sent}"
            + (" from Quill Converter." if self.source == "here" else ", found in your account."),
        ]
        if self.inputs:
            lines.append("Files sent: " + ", ".join(self.inputs))
        if self.preset_label:
            lines.append(f"Preset: {self.preset_label}")
        if self.out_dir:
            lines.append(f"Results folder: {self.out_dir}")
        lines += [f"Saved: {name}" for name in self.files]
        if self.message:
            lines.append(f"Last outcome: {self.message}")
        lines.append(f"Auphonic production id: {self.uuid}")
        return "\n".join(lines)

    def as_pending(self) -> PendingProduction:
        """This entry as the record the run waits for and downloads (Download Again)."""
        return PendingProduction(
            uuid=self.uuid,
            mode=self.mode,
            title=self.title,
            inputs=list(self.inputs),
            preset_label=self.preset_label,
            out_dir=self.out_dir,
            started=self.sent,
        )


def history_path(data_dir: Path | None = None) -> Path:
    if data_dir is None:
        from quill.core.paths import app_data_dir

        data_dir = app_data_dir()
    return data_dir / "converter" / HISTORY_FILE


def _strings(value: object) -> list[str]:
    return [str(x) for x in value] if isinstance(value, list) else []


def load_history(path: Path) -> list[HistoryEntry]:
    """The history, newest first (read forgivingly; never the network)."""
    from quill.core.storage import read_json

    data = read_json(path, {})
    rows = data.get("entries") if isinstance(data, dict) else None
    entries: list[HistoryEntry] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or not isinstance(row.get("uuid"), str):
            continue
        text = {key: str(row.get(key, "") or "") for key in (
            "title", "mode", "preset_label", "out_dir", "sent", "state",
            "status_string", "message", "source", "updated")}  # fmt: skip
        entries.append(
            HistoryEntry(
                uuid=str(row["uuid"]),
                title=text["title"] or str(row["uuid"]),
                mode=text["mode"] or SEPARATE,
                inputs=_strings(row.get("inputs")),
                preset_label=text["preset_label"],
                out_dir=text["out_dir"],
                sent=text["sent"],
                state=text["state"] or PROCESSING,
                status_string=text["status_string"],
                message=text["message"],
                files=_strings(row.get("files")),
                source=text["source"] or "here",
                updated=text["updated"],
            )
        )
    return entries


def save_history(path: Path, entries: list[HistoryEntry]) -> None:
    """Write the history atomically, newest :data:`MAX_ENTRIES` only."""
    from quill.core.storage import write_json_atomic

    kept = entries[:MAX_ENTRIES]
    write_json_atomic(
        path, {"schema": HISTORY_SCHEMA, "entries": [asdict(entry) for entry in kept]}
    )


def record_sent(path: Path, record: PendingProduction) -> None:
    """A production Auphonic has started: put it at the top of the history."""
    entry = HistoryEntry(
        uuid=record.uuid,
        title=record.title,
        mode=record.mode,
        inputs=list(record.inputs),
        preset_label=record.preset_label,
        out_dir=record.out_dir,
        sent=record.started,
    )
    save_history(path, [entry, *(e for e in load_history(path) if e.uuid != record.uuid)])


def record_outcome(
    path: Path, uuid: str, state: str, message: str, files: list[Path] | None = None
) -> None:
    """What became of a production: its state, the words, and any files saved.

    Files saved by an earlier download are kept; a download again adds its own.
    """
    entries = load_history(path)
    for entry in entries:
        if entry.uuid == uuid:
            entry.state = state
            entry.message = message
            entry.updated = _now()
            for name in (str(p) for p in files or []):
                if name not in entry.files:
                    entry.files.append(name)
            save_history(path, entries)
            return


def remove_entry(path: Path, uuid: str) -> None:
    """Forget one production here. It stays in the Auphonic account."""
    entries = load_history(path)
    kept = [entry for entry in entries if entry.uuid != uuid]
    if len(kept) != len(entries):
        save_history(path, kept)


def merge_remote(entries: list[HistoryEntry], remote: list[object], dest: Path) -> tuple[int, int]:
    """Bring *entries* up to date from the account's list; returns ``(updated, added)``.

    *remote* holds :class:`~quill.core.publish.auphonic_account.RemoteProduction`
    rows. A known production takes Auphonic's status; one started elsewhere
    is added below the rest, with its results folder named after its title
    inside *dest*. Saved files and outcomes recorded here are never dropped.
    """
    known = {entry.uuid: entry for entry in entries}
    updated = added = 0
    for row in remote:
        uuid = str(getattr(row, "uuid", ""))
        status = int(getattr(row, "status", -1))
        words = str(getattr(row, "status_string", ""))
        entry = known.get(uuid)
        if entry is None:
            title = str(getattr(row, "title", "")) or uuid
            entry = HistoryEntry(
                uuid=uuid,
                title=title,
                out_dir=str(result_folder(dest, title)),
                sent=str(getattr(row, "created", "")) or _now(),
                source="account",
            )
            entries.append(entry)
            known[uuid] = entry
            added += 1
        else:
            updated += 1
        entry.status_string = words
        entry.updated = _now()
        if status == _ERROR:
            entry.state = FAILED
        elif status == _DONE and entry.state != SAVED:
            entry.state = WAITING  # finished at Auphonic, not fetched here
        elif status not in (_DONE, _ERROR) and entry.state != SAVED:
            entry.state = PROCESSING
    return updated, added
