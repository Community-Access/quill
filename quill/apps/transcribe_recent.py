"""Recent Phrases in QUILL Transcribe (Shift+F11, the editors' chord; D-5).

The editors' command and window, not a second one: the list is the shared
controller's ``recent`` (the last twenty phrases of this run, newest first,
in memory only), then the words kept on disk (D-5: not written last time, a
review that did not finish, and the opt-in history;
:mod:`quill.ui.dictation_kept`), and the window, Copy, Discard and the
empty-list sentence are :func:`quill.ui.windows_dictation_tools.open_recent_phrases`.
What QUILL Transcribe supplies is where **Insert Again** writes:

* into the program you go back to. From the window or the tray QUILL
  Transcribe itself is in front, and it never types into itself, so it waits
  for another program to come forward, as starting dictation from the window
  does (``_arm``), and types the phrase there;
* through the existing keystroke path only (``send_text_checked`` inside the
  shared external document), wrapped in a one-shot
  :class:`~quill.core.windows_dictation.target_lock.LockedTarget`, so the same
  checks as a dictated phrase apply: no password field, no program running as
  administrator, no QUILL window, no program on the never-type list, and the
  focus must still be in the field that was checked when the phrase is typed.

The same route types a finished recording's transcript into a field (Review
Transcript's Type into a Field, D-5), and Review Dictation's Insert falls back
to it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = ["PARTLY_TYPED", "TranscribeRecentMixin"]

#: Said when Windows did not take the whole phrase: never "done".
PARTLY_TYPED = (
    "Windows did not take all of that phrase, so part of it may be missing. Check the field."
)


class TranscribeRecentMixin:
    """On ``QuillTranscribeFrame``: Recent Phrases and its Insert Again."""

    frame: Any
    _data_dir: Path

    def show_recent_phrases(self) -> None:
        """This run's phrases, newest first, then the words kept from before."""
        from quill.ui.windows_dictation_tools import open_recent_phrases

        controller = getattr(self, "_dictation", None)
        open_recent_phrases(
            self.frame,
            list(controller.recent) if controller is not None else [],
            run_modal=self._show_modal_dialog,  # type: ignore[attr-defined]
            say=self._announce,  # type: ignore[attr-defined]
            insert_again=self.insert_recent_phrase,
            kept=self._kept_words(),
        )

    # -- words kept on disk (D-5) ----------------------------------------------- #

    def _dictation_keep(self) -> Any:
        """QUILL Transcribe's store of words not written, and the opt-in history."""
        from quill.core.windows_dictation.rescue import keep_for

        return keep_for(Path(self._data_dir), "QUILL Transcribe")

    def _kept_words(self) -> Any:
        from quill.ui.dictation_kept import KeptWords

        try:
            days = int(self._dictation_preferences().history_days)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - unreadable settings: no history
            days = 0
        rescue = getattr(self, "_review_rescue_path", None)  # TranscribeReviewMixin
        return KeptWords(self._dictation_keep(), rescue() if callable(rescue) else None, days)

    def kept_words_notice(self) -> str:
        """The sentence said at start when words from last time are waiting."""
        from quill.ui.dictation_kept import kept_at_start
        from quill.ui.windows_dictation_review import RESCUE_NOTICE

        try:
            return kept_at_start(self._kept_words(), RESCUE_NOTICE)
        except Exception:  # noqa: BLE001 - nothing to tell
            return ""

    # -- typing ------------------------------------------------------------------ #

    def insert_recent_phrase(self, text: str) -> bool | None:
        """Type *text* into the field you go back to (or the one in front).
        ``True`` when it was typed now; ``None`` when it waits for a field."""
        if getattr(self, "_safe_mode", False):
            self._announce("Safe Mode is on, so QUILL Transcribe does not type.")  # type: ignore[attr-defined]
            return False
        if self._front_is_own_window():  # type: ignore[attr-defined]
            self._arm(here=False, insert=text)  # type: ignore[attr-defined]
            return None
        return self._type_recent_phrase(text)

    def _recent_target(self) -> Any:
        """A one-shot field lock over the shared external document, with the
        never-type list (D-24) checked as for a dictated phrase."""
        from quill.ui.windows_dictation_external import locked_external_document

        return locked_external_document(
            preferences=self._dictation_preferences,  # type: ignore[attr-defined]
            never_type=self.never_type_list,  # type: ignore[attr-defined]
            app="QUILL Transcribe",
            key="start and stop key",
            hush=False,
        )

    def _type_recent_phrase(self, text: str) -> bool:
        from quill.core.sound_events import SoundEvent

        target = self._recent_target()
        refusal = target.relock() or target.unavailable_reason(writing=True)
        if not refusal:
            try:
                target.insert(text)
            except Exception as error:  # noqa: BLE001 - said, never raised
                from quill.core.windows_dictation.target_lock import MOVED

                refusal = MOVED if str(error) == MOVED else PARTLY_TYPED
                if refusal == PARTLY_TYPED:
                    self._dictation_keep().keep("unwritten", text)  # never lost (D-5)
            else:
                self._set_status(f"Typed: {text}")  # type: ignore[attr-defined]
                return True  # the screen reader echoes what was typed: nothing more to say
            target.release()
        self._announce(refusal, force=True, sound=SoundEvent.WINDOWS_DICTATION_ERROR)  # type: ignore[attr-defined]
        return False
