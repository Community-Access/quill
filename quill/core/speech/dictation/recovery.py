"""Dictation recovery repository (PRD §22).

Every dictation is treated as a recoverable transaction: the audio is saved to
disk *before* transcription begins, alongside a JSON sidecar of session metadata
and (once available) the transcript text. If QUILL crashes or is suspended mid
session, the next launch can discover the orphaned files and offer to transcribe,
review, or discard them (PRD §22.4) — speech is never silently lost.

Storage layout (PRD §22.1)::

    <app data>/recovery/dictation/
        <session-id>.wav    raw captured audio (16 kHz mono PCM)
        <session-id>.json   session metadata (small anchor context only)
        <session-id>.txt    transcript, written once transcription succeeds

This module is wx-free and does no audio capture itself: the caller hands it the
already-captured WAV bytes (or a path to move) and the session record.
"""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.speech.dictation.session import DictationSession
from quill.core.storage import read_json, write_json_atomic


@dataclass(frozen=True, slots=True)
class RecoveredSession:
    """An incomplete session discovered at startup (PRD §22.4)."""

    session: DictationSession
    audio_path: Path | None
    transcript_path: Path | None
    metadata_path: Path


def recovery_root() -> Path:
    """The ``recovery/dictation`` directory under the QUILL data dir."""
    return app_data_dir() / "recovery" / "dictation"


class DictationRecoveryRepository:
    """Persist, list, and clean up dictation recovery items.

    ``root`` defaults to :func:`recovery_root` but is injectable so tests can use
    a temporary directory without touching the user's real data folder.
    """

    def __init__(self, root: Path | None = None) -> None:
        self._root = root if root is not None else recovery_root()

    @property
    def root(self) -> Path:
        return self._root

    def _ensure_root(self) -> Path:
        self._root.mkdir(parents=True, exist_ok=True)
        return self._root

    # -- paths ------------------------------------------------------------- #

    def audio_path(self, session_id: str) -> Path:
        return self._root / f"{session_id}.wav"

    def metadata_path(self, session_id: str) -> Path:
        return self._root / f"{session_id}.json"

    def transcript_path(self, session_id: str) -> Path:
        return self._root / f"{session_id}.txt"

    # -- writes ------------------------------------------------------------ #

    def save_audio(self, session: DictationSession, source_wav: Path) -> Path:
        """Move a captured WAV into recovery storage and stamp the session.

        Returns the destination path. The session's ``audio_path`` /
        ``audio_state`` are updated in place and the sidecar is rewritten so the
        on-disk metadata always reflects "audio is saved" before any transcription
        is attempted (PRD §14.2 step 3, §22.1).
        """
        self._ensure_root()
        dest = self.audio_path(session.session_id)
        try:
            shutil.move(str(source_wav), str(dest))
        except (OSError, shutil.Error):
            # Fall back to a copy if the move crosses devices or the source is
            # locked; a readable source must still end up preserved.
            shutil.copyfile(str(source_wav), str(dest))
        session.audio_path = str(dest)
        session.audio_state = "saved"
        self.save_metadata(session)
        return dest

    def save_metadata(self, session: DictationSession) -> Path:
        """Write/refresh the JSON sidecar for ``session`` (atomic)."""
        self._ensure_root()
        path = self.metadata_path(session.session_id)
        write_json_atomic(path, session.to_dict())
        return path

    def save_transcript(self, session: DictationSession, text: str) -> Path:
        """Persist the transcript text and refresh the sidecar state."""
        self._ensure_root()
        path = self.transcript_path(session.session_id)
        path.write_text(text, encoding="utf-8", newline="\n")
        session.transcript = text
        session.transcript_path = str(path)
        session.transcription_state = "done"
        self.save_metadata(session)
        return path

    # -- discovery --------------------------------------------------------- #

    def list_incomplete(self) -> list[RecoveredSession]:
        """Return sessions whose insertion never completed, newest first.

        A session is "incomplete" (and therefore offered for recovery) when its
        sidecar exists and its ``insertion_state`` is not ``inserted`` — i.e. the
        audio/transcript was never successfully placed into a document.
        """
        if not self._root.is_dir():
            return []
        items: list[RecoveredSession] = []
        for meta in sorted(self._root.glob("*.json")):
            data = read_json(meta, default=None)
            if data is None:
                continue
            session = DictationSession.from_dict(data)
            if session.insertion_state == "inserted":
                continue
            audio = self.audio_path(session.session_id)
            transcript = self.transcript_path(session.session_id)
            items.append(
                RecoveredSession(
                    session=session,
                    audio_path=audio if audio.exists() else None,
                    transcript_path=transcript if transcript.exists() else None,
                    metadata_path=meta,
                )
            )
        items.sort(key=lambda item: item.session.started_at, reverse=True)
        return items

    # -- cleanup ----------------------------------------------------------- #

    def delete(self, session_id: str) -> None:
        """Remove all recovery files for one session (PRD §22.3, §23 delete)."""
        for path in (
            self.audio_path(session_id),
            self.metadata_path(session_id),
            self.transcript_path(session_id),
        ):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    def cleanup_expired(self, *, retain_seconds: float, now: float | None = None) -> int:
        """Delete *successfully inserted* sessions older than ``retain_seconds``.

        Only sessions whose insertion succeeded are eligible — incomplete
        sessions are kept until the user acts on them (PRD §22.3). ``retain_seconds``
        of 0 means "never keep a completed recording" (delete immediately).
        Returns the number of sessions deleted. Negative ``retain_seconds`` is
        treated as "keep forever" and deletes nothing.
        """
        if retain_seconds < 0 or not self._root.is_dir():
            return 0
        clock = now if now is not None else time.time()
        removed = 0
        for meta in list(self._root.glob("*.json")):
            data = read_json(meta, default=None)
            if data is None:
                continue
            session = DictationSession.from_dict(data)
            if session.insertion_state != "inserted":
                continue
            stamp = session.stopped_at or session.started_at
            if clock - stamp >= retain_seconds:
                self.delete(session.session_id)
                removed += 1
        return removed
