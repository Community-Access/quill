"""Which QuillLite window is in front, and which ones close.

Extracted from ``lite.py`` under GATE-11 when Close Other Documents grew its
bulk prompt. QUILL's half of the same command is
``quill.ui.main_frame_close_others``, extracted from ``main_frame.py`` in the
same change and for the same reason, so the two read as one feature written
twice in the same order rather than as two apps' window code.

The decisions are ``quill.core.close_prompt`` -- what the question says, what a
"to all" answer latches, what is said afterwards -- and the window is
``quill.ui.bulk_close_dialog``. Both are shared, so the two editors cannot drift
on a question they answer identically.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quill.apps.lite_window import DocumentFrame

__all__ = ["LiteWindowsMixin"]


class LiteWindowsMixin:
    """Closing every document but one, and asking about the work in them."""

    def close_other_documents(self, keep: DocumentFrame) -> int:
        """Close every document window but *keep*. Returns how many closed.

        Reported by a QuillLite user with sixty-nine windows open at once: the
        only way back to one document was Ctrl+W sixty-eight times, answering a
        save prompt on each. QUILL has had Close Other Documents on
        Ctrl+Shift+F4 since 2026-06-15 and QuillLite never got it, which is the
        wrong direction for a key somebody learns in one editor and presses in
        the other (family rule 2: the command both products have keeps the
        chord).

        **The prompt that can repeat carries an answer that ends the
        repetition.** Save All and Don't Save Any, exactly as Word and Explorer
        do it -- a command that exists to save sixty-eight keystrokes must not
        charge sixty-eight prompts instead. The latching rule lives in
        ``BulkSavePolicy`` so both editors cannot disagree about what "any"
        means, and the count travels in the question, because a listener has no
        stack of windows to work it out from.

        Each window is focused before it is asked about, because an MDI child
        cannot be raised: without it the prompt names a document that is not the
        one on screen, which for a listener is simply the wrong question.

        Cancel stops the lot, exactly as Exit does. Somebody who cancels has
        said "not this one", and the sensible reading of that is "stop", not
        "skip it and carry on closing the other sixty-six".
        """
        from quill.core.close_prompt import (
            CANCEL,
            SAVE,
            BulkSavePolicy,
            bulk_unsaved_question,
            describe_bulk_outcome,
        )
        from quill.ui.bulk_close_dialog import ask_bulk_unsaved

        others = [frame for frame in self.frames if frame is not keep]
        if not others:
            self.voice.speak("This is the only document open")
            return 0
        policy = BulkSavePolicy()
        closed = saved = discarded = 0
        for index, frame in enumerate(others):
            if frame.modified:
                self.focus_frame(frame)
                remaining = sum(1 for later in others[index + 1 :] if later.modified)
                question = bulk_unsaved_question(frame.document_name(), remaining, "closing")
                answer = policy.answer(lambda _q=question: ask_bulk_unsaved(self.shell, _q))
                if answer == CANCEL:
                    self.focus_frame(keep)
                    self.voice.speak(
                        describe_bulk_outcome(closed, saved, discarded, len(others) - closed)
                    )
                    return closed
                if answer == SAVE:
                    # A failed save must never read as consent to discard:
                    # closing on a failed save *is* the data loss. It also
                    # breaks the latch, because "save all" cannot keep meaning
                    # "save all" once saving has stopped working.
                    if not frame.save():
                        policy.latched = ""
                        self.focus_frame(keep)
                        self.voice.speak(
                            f"Stopped: {frame.document_name()} was not saved. "
                            + describe_bulk_outcome(closed, saved, discarded, len(others) - closed)
                        )
                        return closed
                    saved += 1
                else:
                    discarded += 1
            frame.modified = False  # already answered for, just above
            frame.Close()
            closed += 1
        self.focus_frame(keep)
        self.voice.speak(describe_bulk_outcome(closed, saved, discarded, 0))
        return closed
