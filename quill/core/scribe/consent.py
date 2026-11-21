"""What the person is told before anything is sent (PRD 7.3 part 1, 10.1, 10.3).

The consent is the convert dialog's own wording: its first control, read-only
and focused, so it can be read again at any time. There is no "don't ask
again" (10.1.1). The privacy lines go in the first upload's consent only;
the copyright notice is always there.

wx-free, no I/O beyond reading file sizes.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.datalab_ocr import looks_sensitive
from quill.core.scribe import PRODUCT_NAME

COPYRIGHT_LINE = (
    "Convert only documents you own, have permission for, or that are out of copyright."
)

PRIVACY_LINES = (
    "Before your first upload:",
    "- Pneuma Solutions in the United States processes the document.",
    "- It is kept in your Scribe account under your retention setting.",
    "- Pictures can be described by Scribe's AI.",
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
    "Scribe password.\n\n"
    "Nothing is sent without your say, every time. Safe Mode turns Scribe off.\n\n"
    + "\n".join(PRIVACY_LINES[1:])
)


def size_words(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{max(1, round(size / 1024))} KB"
    return f"{size} bytes"


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
) -> str:
    """The "What will be sent" text for the convert dialog."""
    lines: list[str] = []
    if existing_title:
        lines.append(
            f"No file is sent. Scribe makes these formats from {existing_title}, "
            "already in your account."
        )
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
            lines.append(f"{len(paths)} files, sent one at a time: {listed}.")
            lead = f"They will be sent to {PRODUCT_NAME}"
            one = False
        it, stays = ("it", "It stays") if one else ("them", "They stay")
        lines.append(
            f"{lead} (Pneuma Solutions, United States) and converted there. {stays} in "
            f"your Scribe account under your retention setting until you delete {it}. "
            "Pictures may be described by Scribe's AI."
        )
        sensitive = [p.name for p in paths if looks_sensitive(p)]
        if sensitive:
            lines.append(
                "Caution: the name of "
                + ", ".join(sensitive)
                + " suggests it may hold private, medical, legal or financial information. "
                "Send it only if you are allowed to."
            )
        if first_upload:
            lines.extend(PRIVACY_LINES)
    if ai_off:
        lines.append(AI_OFF_LINE.format(app=app_name))
    lines.append(COPYRIGHT_LINE)
    return "\n".join(lines)


def pages_text(estimate: int | None, remaining: int | None) -> str:
    """The silent pages line (7.3 part 5)."""
    if remaining is None:
        return "Pages left: not known yet."
    if estimate is None:
        return f"You have {remaining} pages left."
    return f"This uses about {estimate} of your {remaining} pages."


__all__ = [
    "ABOUT_TEXT",
    "AI_OFF_LINE",
    "COPYRIGHT_LINE",
    "PRIVACY_LINES",
    "consent_text",
    "pages_text",
    "size_words",
]
