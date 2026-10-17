"""Import / Convert Document: the file list and the sentences, for both editors.

QUILL has had **File > Import > Import / Convert Document (OCR)...** since
2026-07: pick a Word, Excel, PowerPoint, HTML, EPUB or PDF file, or a picture
of a page, and it opens as new, unsaved text, read by the free local tiers in
:mod:`quill.io.docconvert` (QUILL's own readers first, the PDF's own text, and
only with a yes, OCR on this computer). QUILL Lite gained the same row on
2026-10-17, and QUILL Lite may never be ahead of QUILL -- nor have a second copy
of what QUILL says. So what both editors *say* about a conversion lives here,
and each editor's window code only decides where the text goes:

* :func:`import_wildcard` -- the Open box's file-type list, built from
  docconvert's own extension sets so the list cannot offer a file the router
  refuses.
* :func:`scanned_import_question` -- the one question before OCR runs. OCR is
  never started without it.
* :func:`opened_sentence` -- what is said once the text is in a document: who
  read it, how many pages, and that nothing was uploaded. Only what the screen
  reader cannot know (GATE-13): the new document's name is the window's title
  or the tab's, and the reader says that itself.
* :func:`failed_sentence` -- why nothing opened, in the reader's own words.

The sentences name the app (``app_name``) because the person is in one of two
editors and the box should say which. They were QUILL's inline strings until
this module; QUILL's wording is unchanged.

wx-free, no I/O; in scope for strict ``mypy``.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "CANCELLED_SENTENCE",
    "IMPORT_TITLE",
    "converted_name",
    "failed_sentence",
    "import_wildcard",
    "opened_sentence",
    "scanned_import_question",
]

#: The command's name, the Open box's title and the caption of its questions.
IMPORT_TITLE = "Import / Convert Document"

#: Said (on the status bar) when a conversion is cancelled or declined.
CANCELLED_SENTENCE = "Conversion cancelled. No result was imported."


def import_wildcard() -> str:
    """The Open box's type list: everything, documents, images, all files.

    Built from :mod:`quill.io.docconvert`'s own extension sets, so a file the
    list offers is one the router accepts.
    """
    from quill.io.docconvert import BORN_DIGITAL_EXTENSIONS, IMAGE_EXTENSIONS, PDF_EXTENSION

    def _mask(extensions: frozenset[str] | set[str]) -> str:
        return ";".join(f"*{ext}" for ext in sorted(extensions))

    everything = _mask(BORN_DIGITAL_EXTENSIONS | IMAGE_EXTENSIONS | {PDF_EXTENSION})
    documents = _mask(BORN_DIGITAL_EXTENSIONS | {PDF_EXTENSION})
    images = _mask(IMAGE_EXTENSIONS)
    return (
        f"All convertible documents ({everything})|{everything}"
        f"|Documents ({documents})|{documents}"
        f"|Images ({images})|{images}"
        "|All files (*.*)|*.*"
    )


def converted_name(stem: str) -> str:
    """The new document's name: ``"report (converted)"``. Never the source's name,
    so nobody mistakes the text for the file it came from."""
    return f"{stem} (converted)"


def scanned_import_question(file_name: str, *, app_name: str = "QUILL") -> str:
    """The Tier 1 -> 2 question: no readable text, so read it with OCR?

    Asked with Yes, No and Cancel. Yes runs on-device OCR; No opens what text
    there is (perhaps none); Cancel imports nothing.
    """
    return (
        f"{app_name} could not find readable text in {file_name}. "
        "It looks scanned or image-based.\n\n"
        "Run free on-device OCR? This stays on your computer "
        "and does not upload anything.\n\n"
        "Yes: run local OCR now.  No: open the empty result anyway.  "
        "Cancel: stop."
    )


def _pages(outcome: Any) -> str:
    count = int(getattr(outcome, "page_count", 0) or 0)
    return f" {count} pages." if count > 1 else ""


def opened_sentence(file_name: str, outcome: Any) -> str:
    """One sentence for a conversion that opened: who read it, and what it found.

    *outcome* is a :class:`quill.io.docconvert.ConversionOutcome`. The words
    are the ones QUILL has said since the tiers shipped; the Windows OCR and
    own-reader sentences since 2026-10-15 and 2026-10-16.
    """
    from quill.io.docconvert import (
        TIER_CLOUD_OCR,
        TIER_LOCAL_OCR,
        TIER_OWN_READER,
        TIER_PDF_TEXT,
        TIER_WINDOWS_OCR,
    )

    tier = getattr(outcome, "tier", "")
    pages = _pages(outcome)
    if tier == TIER_CLOUD_OCR:
        return (
            f"Opened {file_name} from Datalab cloud OCR.{pages} "
            "The result was retrieved and is only stored in this document."
        )
    if tier == TIER_LOCAL_OCR:
        mean = float(getattr(outcome, "mean_confidence", -1.0))
        confidence = f" Confidence {mean:.0f} out of 100." if mean >= 0.0 else ""
        return f"Opened {file_name} from free on-device OCR.{pages}{confidence}"
    if tier == TIER_WINDOWS_OCR:
        return (
            f"Opened {file_name} from Windows OCR on this computer.{pages} "
            "Nothing was uploaded. Check the text; OCR makes mistakes."
        )
    if tier == TIER_PDF_TEXT:
        return (
            f"Opened {file_name} as editable text from the PDF's own text.{pages} "
            "Nothing was uploaded."
        )
    if tier == TIER_OWN_READER:
        # MarkItDown could not run or read it (always, in a shipped build): say
        # who did, and how many sheets or slides -- neither is something the
        # screen reader can know.
        units = str(getattr(outcome, "units", "") or "")
        reader = str(getattr(outcome, "reader", "") or "") or "QUILL"
        return (
            f"Opened {file_name} as editable text, read by {reader}."
            f"{f' {units}.' if units else ''} Nothing was uploaded."
        )
    return (
        f"Opened {file_name} as editable text using the free local converter. Nothing was uploaded."
    )


def failed_sentence(file_name: str, error: object, *, app_name: str = "QUILL") -> str:
    """Why nothing opened: the app, the file, then the reader's own sentence."""
    return f"{app_name} could not convert {file_name}.\n\n{error}"
