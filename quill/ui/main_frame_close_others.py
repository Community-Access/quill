"""Close Other Documents in QUILL, with an answer for all the rest.

Extracted from ``main_frame.py`` under GATE-11 when the bulk prompt landed, and
the extraction is the right shape rather than only the cheap one: QuillLite's
half of the same command is ``QuillLiteApp.close_other_documents``, and the two
now read as the same feature written twice in the same order. The decisions --
what the question says, what a "to all" answer latches, what is said afterwards
-- are ``quill.core.close_prompt``, which is wx-free and shared, so the two
editors cannot drift on a question they answer identically. The window is
``quill.ui.bulk_close_dialog``, shared for the same reason.

**Why it grew two buttons.** Ctrl+Shift+F4 with sixty-eight tabs open asked
sixty-eight separate questions and gave no way to answer them together: the
command that exists to save sixty-eight keystrokes charged sixty-eight prompts
instead. Save All and Don't Save Any end the repetition, which is how Word and
Explorer have always done it.
"""

from __future__ import annotations

from quill.core.close_prompt import (
    CANCEL,
    SAVE,
    BulkSavePolicy,
    bulk_unsaved_question,
    describe_bulk_outcome,
)

__all__ = ["CloseOthersMixin"]


class CloseOthersMixin:
    """Keep this tab, close the rest, ask about unsaved work once."""

    def close_other_documents(self) -> None:
        """``Window > Close Other Documents`` (``Ctrl+Shift+F4``)."""
        self._close_other_tabs(self._active_tab_index)

    def _close_other_tabs(self, keep_index: int) -> None:
        """Close every tab but *keep_index*, asking about unsaved work in bulk.

        Closes from the end backwards so indices stay valid while tabs go. The
        question is asked about the tab that is *selected* at the time, because
        a prompt naming a document other than the one on screen is, for a
        listener, simply the wrong question.

        Cancel stops the whole thing rather than skipping one tab: somebody who
        cancels has said "not this one", and "carry on closing the other
        sixty-six" is not a reading of that anybody intends.
        """
        if keep_index < 0 or keep_index >= len(self._document_tabs):
            return
        keep_tab = self._document_tabs[keep_index]
        doomed = [tab for tab in self._document_tabs if tab is not keep_tab]
        if not doomed:
            self._announce("Only one document open")
            self._set_status("No other document to close")
            return

        policy = BulkSavePolicy()
        closed = saved = discarded = 0
        for index in range(len(self._document_tabs) - 1, -1, -1):
            tab = self._document_tabs[index]
            if tab is keep_tab:
                continue
            self._select_tab(index)
            if self.document.modified:
                remaining = sum(
                    1
                    for position in range(index - 1, -1, -1)
                    if self._document_tabs[position] is not keep_tab
                    and getattr(
                        getattr(self._document_tabs[position], "document", None),
                        "modified",
                        False,
                    )
                )
                question = bulk_unsaved_question(self.document.name, remaining, "closing")
                answer = policy.answer(lambda _q=question: self._ask_bulk_unsaved(_q))
                if answer == CANCEL:
                    self._restore_kept_tab(keep_tab)
                    self._set_status(
                        describe_bulk_outcome(closed, saved, discarded, len(doomed) - closed)
                    )
                    return
                if answer == SAVE:
                    # A save that did not happen is never consent to discard:
                    # closing on a failed save *is* the data loss (#1390). The
                    # latch breaks with it -- "save all" cannot keep meaning
                    # "save all" once saving has stopped working.
                    if not self._save_for_bulk_close():
                        policy.latched = ""
                        self._restore_kept_tab(keep_tab)
                        self._set_status(
                            f"Stopped: {self.document.name} was not saved. "
                            + describe_bulk_outcome(closed, saved, discarded, len(doomed) - closed)
                        )
                        return
                    saved += 1
                else:
                    discarded += 1
            self._close_tab(index)
            closed += 1
        self._restore_kept_tab(keep_tab)
        self._set_status(describe_bulk_outcome(closed, saved, discarded, 0))

    def _restore_kept_tab(self, keep_tab: object) -> None:
        """Put focus back on the document the command was about keeping."""
        if keep_tab in self._document_tabs:
            self._select_tab(self._document_tabs.index(keep_tab))

    def _ask_bulk_unsaved(self, question: str) -> str:
        """The window. A seam, so the loop above is testable without a display."""
        from quill.ui.bulk_close_dialog import ask_bulk_unsaved

        return ask_bulk_unsaved(self.frame, question)

    def _save_for_bulk_close(self) -> bool:
        """Save the active document. ``False`` when it did not happen.

        Mirrors what ``_prompt_to_save_active_document`` does with a Save
        answer, failure included: a writer that raises must cancel the close
        rather than be read as consent to lose the document (#1390).
        """
        try:
            self.save_file()
        except Exception:  # noqa: BLE001 - never close on a failed save (#1390)
            import logging

            logging.getLogger(__name__).warning(
                "Save during Close Other Documents failed; stopping (#1390)", exc_info=True
            )
            return False
        return not self.document.modified
