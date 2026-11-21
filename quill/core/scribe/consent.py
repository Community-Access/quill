"""What the person is told before anything is sent (PRD 7.3 part 1, 10.1, 10.3).

The consent is the convert dialog's own wording: its first control, read-only
and focused, so it can be read again at any time. There is no "don't ask
again" (10.1.1). The privacy lines go in the first upload's consent and in
Options (About); the copyright notice is always there.

The wording follows Pneuma's answers of 2026-11-21: processing in the United
States and by whom, no training on documents, the account's retention rule
(which the API cannot read, so it is described, not quoted), and -- for the
picture-description provider's own retention -- only that Pneuma is reviewing
it. Nothing more is promised until Pneuma says more.

wx-free, no I/O beyond reading file sizes.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.datalab_ocr import looks_sensitive
from quill.core.scribe import PRODUCT_NAME
from quill.core.scribe.inputs import size_words
from quill.core.scribe.model import HTML_SHAPING, pages_left_phrase

COPYRIGHT_LINE = (
    "Convert only documents you own, have permission for, or that are out of copyright."
)

#: PRD 10.1.2: shown before the first upload and in Options (About).
PRIVACY_LINES = (
    "Before your first upload:",
    "- Pneuma Solutions processes the document in the United States: on AWS in Ohio, "
    "with Microsoft Azure (East US) for speech and text recognition, Mathpix for "
    "mathematics, and Google Gemini through OpenRouter for picture descriptions.",
    "- Pneuma never uses documents to train AI.",
    "- It is kept in your Scribe account under your retention setting: 30 days unless "
    "you changed it, 1 to 30 days by choice, or as long as you like with a subscription; "
    "an organization sets 1 to 30 days. Change it with Open My Scribe Account in Browser.",
    "- Pictures can be described by AI. Pneuma is reviewing its picture-description "
    "provider and makes no promise yet about how long that provider keeps data.",
    "- To delete it: My Scribe Documents, Move to Trash, then Delete Forever.",
)

AI_OFF_LINE = (
    "AI is turned off in {app}, so Describe the pictures starts unchecked. You may still "
    "check it: the descriptions are Scribe's processing, not {app}'s AI."
)

ABOUT_TEXT = (
    "Powered by Scribe for Documents, from Pneuma Solutions.\n\n"
    "Scribe for Documents rebuilds inaccessible documents (scans, badly made PDFs, "
    "pictures of text, Office files) into accessible HTML, Word, tagged PDF, EPUB, "
    "Kindle, DAISY, MP3 audio and braille. You sign in with your own Scribe account "
    "and pay Scribe for your own pages; {app} never takes payment and never sees your "
    "Scribe password. What Scribe makes is yours: {app} saves it in your own folders "
    "and never shares it with anyone else who uses this computer.\n\n"
    "Nothing is sent without your say, every time. Safe Mode turns Scribe off.\n\n"
    + "\n".join(PRIVACY_LINES[1:])
)


def fixed_settings_line(title: str) -> str:
    """Reusing a document: which settings the earlier upload fixed (3.3)."""
    words = [words for _key, words in HTML_SHAPING]
    listed = ", ".join(words[:-1]) + " and " + words[-1]
    return (
        f"The {listed} settings were fixed when {title} was uploaded; they are listed "
        f"under Fixed when {title} was uploaded and cannot be changed. The other settings "
        "apply to formats not made yet; formats already made keep theirs."
    )


def _describe(path: Path, pages: int | None) -> str:
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    parts = [size_words(size)] if size else []
    if pages:
        parts.append(f"{pages} pages" if pages != 1 else "1 page")
    return f"{path.name} ({', '.join(parts)})" if parts else path.name


def consent_text(
    paths: list[Path],
    *,
    pages: dict[str, int] | None = None,
    first_upload: bool = False,
    url: str = "",
    existing_title: str = "",
    ai_off: bool = False,
    app_name: str = "QUILL",
    refused: list[str] | None = None,
) -> str:
    """The "What will be sent" text for the convert dialog. *refused* are the
    sentences for chosen files Scribe does not take: they go here, in the
    focused text, because a dialog opening cuts off speech said just before."""
    lines: list[str] = []
    if existing_title:
        lines.append(
            f"No file is sent. Scribe makes these formats from {existing_title}, "
            "already in your account."
        )
        lines.append(fixed_settings_line(existing_title))
    else:
        if url:
            lead = f"The file at {url} will be fetched by {PRODUCT_NAME}"
            one = True
        elif len(paths) == 1:
            described = _describe(paths[0], (pages or {}).get(str(paths[0])))
            lead = f"{described} will be sent to {PRODUCT_NAME}"
            one = True
        else:
            listed = "; ".join(_describe(p, (pages or {}).get(str(p))) for p in paths)
            lines.append(
                f"{len(paths)} files, sent one after another without asking again: {listed}."
            )
            lead = f"They will be sent to {PRODUCT_NAME}"
            one = False
        it, stays = ("it", "It stays") if one else ("them", "They stay")
        lines.append(
            f"{lead} (Pneuma Solutions) and converted in the United States. {stays} in "
            "your Scribe account under your retention setting (30 days unless you changed "
            f"it) until you delete {it}. Pictures may be described by AI. Pneuma does not "
            "use documents to train AI."
        )
        sensitive = [p.name for p in paths if looks_sensitive(p)]
        if sensitive:
            lines.append(
                "Caution: the name of "
                + ", ".join(sensitive)
                + " suggests it may hold private, medical, legal or financial information. "
                "Send it only if you are allowed to."
            )
        if refused:
            lines.append("Not sent: " + " ".join(refused))
        if first_upload:
            lines.extend(PRIVACY_LINES)
    if ai_off:
        lines.append(AI_OFF_LINE.format(app=app_name))
    lines.append(COPYRIGHT_LINE)
    return "\n".join(lines)


def pages_text(
    estimate: int | None, remaining: int | None, *, organization: str = "", free: bool = False
) -> str:
    """The silent pages line (7.3 part 5).

    *free*: every format still to make is of a document already charged, so no
    pages are used (3.6). *organization*: the count is that organization's
    shared pool (3.4).
    """
    if free:
        left = (
            "" if remaining is None else f" You have {pages_left_phrase(remaining, organization)}."
        )
        return f"No pages used: this document is already in your Scribe account.{left}"
    if remaining is None:
        return "Not known yet."
    if estimate is None:
        return f"You have {pages_left_phrase(remaining, organization)}."
    if organization:
        return (
            f"This uses about {estimate:,} of the {remaining:,} pages left in "
            f"{organization}'s credits."
        )
    return f"This uses about {estimate:,} of your {remaining:,} pages."


__all__ = [
    "ABOUT_TEXT",
    "AI_OFF_LINE",
    "COPYRIGHT_LINE",
    "PRIVACY_LINES",
    "consent_text",
    "fixed_settings_line",
    "pages_text",
    "size_words",
]
