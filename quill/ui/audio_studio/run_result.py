"""How an Audio Studio run ends: the actual result, said once and kept (FUX-04).

A narration run can take an hour. Until this module it ended on a status-bar
line nobody hears ("Batch speech export complete: 8 done (12 chapters), 1
skipped, 1 error(s)"), in QUILL Studio the run's notification was dropped, and
nothing said where the audio went. So the end of a run is now one sentence,
built from what the run left behind, spoken once and kept in Activity
(Shift+F9, and F9 repeats it) with Open Folder on the folder it went to:

* **what happened** -- how many documents became audio, out of how many, and
  how many were skipped or failed;
* **where** -- the folder, by name (:func:`quill.core.action_feedback.place_of`);
* **the book's check, apart from the build** -- a book that was built but whose
  read-back found a problem says both, in two sentences, never "done";
* **a stop** says what is kept, what was not made, and how to make the rest.

The sentence builders are pure; :func:`report_run` is the one call that speaks
and keeps. Nothing here opens a window: a result that arrives while the person
is in another window is heard and kept, and focus stays where it is.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.core.action_feedback import place_of

__all__ = [
    "book_sentence",
    "documents_sentence",
    "report_run",
    "report_translated",
    "run_sentence",
    "translated_sentence",
]

#: ``_assemble_book``'s summaries that are not a built book.
_NO_AUDIO = "audiobook skipped (no audio found)"
_REVIEW_CANCELLED = "audiobook cancelled at chapter review"
_FAILED = "audiobook failed: "
_LIBRARY = "library: "


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


def _where(folder: Path) -> str:
    """``in Reports``: a folder by its own name, the drive for a drive's root."""
    return f"in {folder.name or str(folder)}"


def documents_sentence(
    *,
    total: int,
    done: int,
    skipped: int,
    errors: int,
    cancelled: bool,
    folder: Path,
    resumes: bool,
    book: bool = False,
    dry_run: bool = False,
) -> str:
    """What became of the documents, and where it is.

    *resumes* is whether running the same job again skips the finished ones
    (Skip (resume), or Reuse unchanged audio): a stop then says so, and
    otherwise says which choice makes a re-run resume.
    """
    made = "preview text" if dry_run else "audio"
    where = _where(folder)
    if total <= 0:
        return ""  # a folder of audio only: the book is the whole result
    if cancelled:
        handled = done + skipped + errors
        left = max(total - handled, 0)
        said = f"Stopped after {handled} of {_count(total, 'document')}."
        have = done + skipped  # a skipped document already had its audio
        if have:
            said += f" The {made} for {_count(have, 'document')} is kept {where}"
        else:
            said += f" No {made} was made"
        said += f"; the other {left} {'has' if left == 1 else 'have'} no {made} yet"
        said += ", and no audiobook was built." if book else "."
        if left and not dry_run:
            said += (
                " Run it again to make the rest; finished ones are skipped."
                if resumes
                else " To make only the rest, run it again with If an audio file "
                "already exists set to Skip (resume)."
            )
        return said
    if done == total:
        said = f"Made {made} for {_count(total, 'document')} {where}."
    elif done == 0 and errors == 0:
        said = f"Made no new {made}: {_count(total, 'document')} {where} already had it."
    else:
        said = f"Made {made} for {done} of {_count(total, 'document')} {where}."
    if skipped and done + errors:
        said += f" {skipped} already had {made}."
    if errors:
        said += f" {errors} failed; the run's log {where} says why."
    return said


def book_sentence(summary: str, folder: Path) -> str:
    """The book step, with its check said apart from the build."""
    summary = summary.strip()
    if not summary:
        return ""
    if summary == _NO_AUDIO:
        return "No audiobook was built: no audio was found."
    if summary == _REVIEW_CANCELLED:
        return "No audiobook was built, because the chapter review was cancelled."
    if summary.startswith(_FAILED):
        return f"The audiobook was not built: {summary[len(_FAILED) :]}."
    if summary.startswith(_LIBRARY):
        built = summary[len(_LIBRARY) :].split(" ", 1)[0]
        count = int(built) if built.isdigit() else 0
        return f"Built {_count(count, 'audiobook')}, one for each subfolder {_where(folder)}."
    if summary.startswith("audiobook ") and summary.endswith(")") and " (" in summary:
        name, check = summary[len("audiobook ") : -1].rsplit(" (", 1)
        built = f"Built the audiobook {place_of(folder / name)}."
        if check.startswith("verified "):
            return f"{built} Its check found all {check[len('verified ') :]}."
        return f"{built} Its check found a problem: {check}."
    return summary[0].upper() + summary[1:] + "."


def run_sentence(
    *,
    total: int,
    done: int,
    skipped: int,
    errors: int,
    cancelled: bool,
    folder: Path,
    resumes: bool,
    book_summary: str = "",
    book: bool = False,
    dry_run: bool = False,
    substitutions: int = 0,
) -> str:
    """The whole end of a run: the documents, then the book, as one result."""
    said = documents_sentence(
        total=total,
        done=done,
        skipped=skipped,
        errors=errors,
        cancelled=cancelled,
        folder=folder,
        resumes=resumes,
        book=book,
        dry_run=dry_run,
    )
    if dry_run and substitutions:
        said += f" {_count(substitutions, 'substitution')} made."
    if book and not cancelled:
        said = f"{said} {book_sentence(book_summary, folder)}".strip()
    return said


def report_run(host: Any, sentence: str, *, folder: Path, problem: bool) -> None:
    """Say *sentence* once and keep it in Activity, with Open Folder on *folder*."""
    from quill.ui.outcome_report import keep_outcome

    announce = getattr(host, "_announce", None)
    if callable(announce):
        announce(sentence)
    keep_outcome("Audio Studio", sentence, object_name=folder.name, path=folder, partial=problem)


def translated_sentence(document: Path, languages: int, chapters: int) -> str:
    """``Made translated audio of report.docx: 2 languages, 9 chapters, in Reports.``"""
    if chapters <= 0:
        return f"No translated audio of {document.name} was made."
    return (
        f"Made translated audio of {document.name}: {_count(languages, 'language')}, "
        f"{_count(chapters, 'chapter')}, {_where(document.parent)}."
    )


def report_translated(host: Any, document: Path, languages: int, chapters: int) -> None:
    """The translated export's end, said once and kept with Open Folder."""
    report_run(
        host,
        translated_sentence(document, languages, chapters),
        folder=document.parent,
        problem=chapters <= 0,
    )
