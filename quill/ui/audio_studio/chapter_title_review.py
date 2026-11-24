"""Review the AI's proposed chapter titles one by one (FUX-12).

Propose AI Titles used to replace every title in the Chapter Workbench's
list at once. The list then read only the new titles, so nobody could hear
what a title replaced, and keeping some proposals meant taking all of them
and retyping the rest. The proposals now open in the family's one review of
a proposed change (``DiffReviewDialog``), built with one check box for each
chapter whose title would change -- "Chapter 3: "Track 03" becomes "The
Storm"." -- and only the checked titles go into the list. Nothing is saved
until Save, and Restore Original still undoes them.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.ai.diff_review import build_item_review
from quill.core.i18n import _

__all__ = ["review_titles"]


def _for_titles(announce: Callable[[str], None]) -> Callable[[str], None]:
    """The review's sentences, worded for a list of titles.

    "Applied 3 changes" is left to the Workbench, which says what went into
    the list; the review's "the document is unchanged" is about titles here.
    """

    def say(message: str) -> None:
        if message.startswith("Applied "):
            return
        announce(message.replace("the document is unchanged", "the titles are unchanged"))

    return say


def review_titles(
    parent: object,
    titles: list[str],
    proposals: list[str],
    announce: Callable[[str], None],
) -> list[str] | None:
    """The titles to use after review, or None when none were taken.

    *proposals* lines up with *titles*, one per chapter; an empty proposal
    keeps the chapter's title.
    """
    from quill.ui.ai_diff_review_dialog import DiffReviewDialog

    wanted = [proposal.strip() or title for title, proposal in zip(titles, proposals, strict=True)]
    review = build_item_review(titles, wanted, unit="chapter")
    if not review.hunks:
        return None
    taken: list[list[str]] = []
    if len(review.hunks) == 1:  # one change: the review shows Accept and Reject
        intro = _(
            "The AI would change one chapter's title. Accept puts it in the chapter"
            " list; Reject keeps the current title. Nothing is saved until Save, and"
            " Restore original undoes it."
        )
    else:
        intro = _(
            "Each chapter whose title the AI would change, with its title now and the"
            " proposed one. Apply Checked puts the checked titles in the chapter list;"
            " uncheck any chapter whose current title you want to keep. Accept All"
            " takes every proposal; Reject All keeps every title. Nothing is saved"
            " until Save, and Restore original undoes them."
        )
    DiffReviewDialog(
        parent,
        title=str(_("Review Proposed Titles")),
        original_text=review.original,
        revised_text=review.revised,
        on_apply=lambda text: taken.append(text.split("\n")),
        announce=_for_titles(announce),
        intro=str(intro),
        review=review,
    ).show_modal()
    return taken[0] if taken else None
