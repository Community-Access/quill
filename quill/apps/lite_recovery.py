"""Last session's unsaved work in QUILL Lite: tidy it first, then ask properly.

Extracted from ``lite.py`` when the chooser landed, for the reason the session
half was extracted (``lite_session.py``): the two questions are the same shape
and belong in the same shape of module. The decisions are wx-free in
``quill/core/recovery_triage.py`` and the window is ``quill/ui/recovery_dialog.py``,
both shared, so QUILL and QUILL Lite cannot drift on an answer they agree about.

What this replaced, and why it had to go: ``_restore_pending_work`` read the
store, put every slot in a Yes/No message box, and opened all of them or none.
On 2026-09-21 that arrived as "QUILL Lite has unsaved work from 69 documents ...
Open them now?" Sixty-seven of the sixty-nine were four identical characters left
by automated runs that had been killed; two were real. Every part of that is now
answered before the question is asked -- duplicates folded, month-old copies
expired, untitled ones droppable by preference -- and what is left is a list with
a checkbox on each row rather than a number in a sentence.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quill.core.recovery_triage import Triage

__all__ = ["LiteRecoveryMixin"]


class LiteRecoveryMixin:
    """Finding, triaging, offering and discarding unsaved work."""

    def _restore_pending_work(self) -> bool:
        """Offer last session's unsaved work back. ``True`` when any was taken.

        Triage runs first and is not a preference: identical copies are one
        document however many times a crash wrote them, and a copy nobody has
        come back for in a month is litter in front of the thing that matters.
        What the triage drops is deleted here, because this is the only moment
        that knows it is safe to -- and the sentence the window opens with says
        what was dropped, so tidying is never mistaken for work going missing.
        """
        from quill.core.lite import recovery as recovery_mod
        from quill.core.recovery_triage import triage

        slots = recovery_mod.pending()
        if not slots:
            return False
        result = triage(
            slots,
            keep_days=int(getattr(self.settings, "recovery_keep_days", 30)),
            offer_untitled=bool(getattr(self.settings, "recover_untitled_documents", True)),
        )
        for slot in result.tidied:
            recovery_mod.discard(slot)
        if not result.offer:
            # Everything found was a duplicate, expired or an untitled document
            # this user does not want back. Nothing to ask, but not nothing to
            # say: silence here is indistinguishable from work having vanished.
            from quill.core.recovery_triage import describe_tidy

            said = describe_tidy(result)
            if said:
                self.voice.speak(f"Tidied up unsaved work from last time. {said}")
            return False
        return self._offer_recovery(result)

    def _offer_recovery(self, result: Triage) -> bool:
        """Put the triaged list up, act on the answer. ``True`` when any opened."""
        from quill.core.lite import recovery as recovery_mod
        from quill.core.recovery_triage import describe_restored
        from quill.ui.recovery_dialog import ask_recovery

        answer = ask_recovery(self.shell, result)
        for slot in answer.discard:
            recovery_mod.discard(slot)
        if answer.offer_untitled is not None:
            self.settings.recover_untitled_documents = bool(answer.offer_untitled)
            self.save_settings()
        restored = 0
        for slot in answer.restore:
            self.new_window(slot.mode, recovery_slot=slot)
            restored += 1
        parts = [describe_restored(restored, len(answer.restore)), answer.spoken]
        if not answer.restore and not answer.discard:
            parts = ["Unsaved work kept. It will be offered again next time.", answer.spoken]
        said = " ".join(part for part in parts if part).strip()
        if said:
            self.voice.speak(said)
        return restored > 0
