"""Timestamped notes on a moment in a podcast episode.

The most QUILL-native idea in the Podcasts feature set -- no mainstream
podcast app does this, and it follows directly from QUILL already being a
notes-and-writing tool, not just a player. Deliberately its own small
atomic-JSON store rather than a literal reuse of Sticky Notes (freeform,
no anchor at all) or Inline Notes (anchored to a text quote): a moment in
an audio timeline is a different kind of anchor than either of those, so
forcing it into one would mean bolting an audio-position concept onto a
system that was never shaped for it. Same storage shape as both, though --
one atomic-JSON file, one dataclass, no surprises.

wx-free, strict-typed.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

_FILENAME = "podcast_episode_notes.json"


@dataclass(frozen=True, slots=True)
class EpisodeNote:
    note_id: str
    show_id: str
    episode_guid: str
    position_ms: int
    text: str
    created_at: str

    def to_dict(self) -> dict[str, object]:
        return {
            "note_id": self.note_id,
            "show_id": self.show_id,
            "episode_guid": self.episode_guid,
            "position_ms": self.position_ms,
            "text": self.text,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> EpisodeNote | None:
        note_id = str(data.get("note_id", "")).strip()
        show_id = str(data.get("show_id", "")).strip()
        episode_guid = str(data.get("episode_guid", "")).strip()
        text = str(data.get("text", "")).strip()
        if not note_id or not show_id or not episode_guid or not text:
            return None
        position_ms = data.get("position_ms")
        return cls(
            note_id=note_id,
            show_id=show_id,
            episode_guid=episode_guid,
            position_ms=int(position_ms) if isinstance(position_ms, (int, float)) else 0,
            text=text,
            created_at=str(data.get("created_at", "")),
        )


def episode_notes_path() -> Path:
    return app_data_dir() / _FILENAME


def load_episode_notes() -> list[EpisodeNote]:
    raw = read_json(episode_notes_path(), default=[])
    if not isinstance(raw, list):
        return []
    notes: list[EpisodeNote] = []
    for entry in raw:
        if isinstance(entry, dict):
            note = EpisodeNote.from_dict(entry)
            if note is not None:
                notes.append(note)
    return notes


def save_episode_notes(notes: list[EpisodeNote]) -> None:
    write_json_atomic(episode_notes_path(), [note.to_dict() for note in notes])


def notes_for_episode(
    notes: list[EpisodeNote], show_id: str, episode_guid: str
) -> list[EpisodeNote]:
    """This episode's notes, earliest timestamp first."""
    matching = [n for n in notes if n.show_id == show_id and n.episode_guid == episode_guid]
    return sorted(matching, key=lambda n: n.position_ms)


def add_episode_note(
    show_id: str, episode_guid: str, position_ms: int, text: str
) -> list[EpisodeNote]:
    """Load, append a new note, save, and return the full updated list."""
    notes = load_episode_notes()
    notes.append(
        EpisodeNote(
            note_id=uuid.uuid4().hex,
            show_id=show_id,
            episode_guid=episode_guid,
            position_ms=max(0, position_ms),
            text=text.strip(),
            created_at=datetime.now(UTC).isoformat(),
        )
    )
    save_episode_notes(notes)
    return notes


def delete_episode_note(note_id: str) -> list[EpisodeNote]:
    """Load, remove *note_id* if present, save, and return the updated list."""
    notes = [n for n in load_episode_notes() if n.note_id != note_id]
    save_episode_notes(notes)
    return notes
