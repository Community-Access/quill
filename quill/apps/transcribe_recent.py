"""Recent Phrases in QUILL Transcribe (Shift+F11, the editors' chord; D-5 slice).

The editors' command and window, not a second one: the list is the shared
controller's ``recent`` (the last twenty phrases of this run, newest first,
in memory only), and the window, Copy and the empty-list sentence are
:func:`quill.ui.windows_dictation_tools.open_recent_phrases`. What QUILL
Transcribe supplies is where **Insert Again** writes:

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

Nothing is kept on disk: that is the rest of D-5, not this slice.
"""

from __future__ import annotations

from typing import Any

__all__ = ["PARTLY_TYPED", "TranscribeRecentMixin"]

#: Said when Windows did not take the whole phrase: never "done".
PARTLY_TYPED = (
    "Windows did not take all of that phrase, so part of it may be missing. Check the field."
)


class TranscribeRecentMixin:
    """On ``QuillTranscribeFrame``: Recent Phrases and its Insert Again."""

    frame: Any

    def show_recent_phrases(self) -> None:
        """The last twenty phrases, newest first: type one again, or copy it."""
        from quill.ui.windows_dictation_tools import open_recent_phrases

        controller = getattr(self, "_dictation", None)
        open_recent_phrases(
            self.frame,
            list(controller.recent) if controller is not None else [],
            run_modal=self._show_modal_dialog,  # type: ignore[attr-defined]
            say=self._announce,  # type: ignore[attr-defined]
            insert_again=self.insert_recent_phrase,
        )

    def insert_recent_phrase(self, text: str) -> None:
        """Type *text* into the field you go back to (or the one in front)."""
        if getattr(self, "_safe_mode", False):
            self._announce("Safe Mode is on, so QUILL Transcribe does not type.")  # type: ignore[attr-defined]
            return
        if self._front_is_own_window():  # type: ignore[attr-defined]
            self._arm(here=False, insert=text)  # type: ignore[attr-defined]
            return
        self._type_recent_phrase(text)

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

    def _type_recent_phrase(self, text: str) -> None:
        from quill.core.sound_events import SoundEvent

        target = self._recent_target()
        refusal = target.relock() or target.unavailable_reason(writing=True)
        if not refusal:
            try:
                target.insert(text)
            except Exception as error:  # noqa: BLE001 - said, never raised
                from quill.core.windows_dictation.target_lock import MOVED

                refusal = MOVED if str(error) == MOVED else PARTLY_TYPED
            else:
                self._set_status(f"Typed: {text}")  # type: ignore[attr-defined]
                return  # the screen reader echoes what was typed: nothing more to say
            target.release()
        self._announce(refusal, force=True, sound=SoundEvent.WINDOWS_DICTATION_ERROR)  # type: ignore[attr-defined]
