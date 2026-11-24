"""Which dialect to start on, and the voice list (Scribe for Documents, 7.3).

Jeff's QUILL Lite test, 2026-11-23: "I just see Scribe default and the play
button does nothing", and "shouldn't we detect the language of the operating
system and attempt to set it by default and fill the voices?". Two answers:

**A starting dialect.** When nothing is saved for a language, the Dialect
list starts on the dialect of the document's own language when the file says
it (a Word document's language, a PDF's ``/Lang``, a web page's or a book's
``lang``), else on Windows' display language and region (``en-US``). A tag
is matched to Scribe's dialect locales exactly first, then by language alone
(``en-AU`` against a Scribe that has only ``en-US`` and ``en-GB`` takes the
first English one Scribe lists); a language nothing points at stays on
Scribe's default. It is only a suggestion: a saved choice (the account's
defaults, or this app's last choice) always wins, and a suggestion is sent
for the one document, never saved as the account's defaults (F8; see
:func:`quill.core.scribe.options.quill_base`).

**A voice list that is never only "Scribe's default"** for a chosen
language. With a dialect chosen, its voices; with Dialect on Scribe's
default, every dialect's voices for the language, each with its dialect
("Jenny, English (United States)"), so choosing one also chooses the
dialect. A voice Scribe has no sample of says so in its name, once
(", no sample"), rather than in a message after Play Sample.

wx-free.
"""

from __future__ import annotations

import locale
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: Said in a voice's name when Scribe has no sample of it.
NO_SAMPLE = "no sample"

_TAG = re.compile(r"^[A-Za-z]{2,3}([-_][A-Za-z0-9]{2,8})*$")


def normalise_tag(tag: Any) -> str:
    """``"en_us.UTF-8"`` -> ``"en-US"``; ``""`` for anything that is not a tag."""
    text = str(tag or "").strip().split(".")[0].split("@")[0]
    if not text or not _TAG.match(text):
        return ""
    parts = text.replace("_", "-").split("-")
    out = [parts[0].lower()]
    for part in parts[1:]:
        if len(part) == 2:
            out.append(part.upper())
        elif len(part) == 4:
            out.append(part.title())
        else:
            out.append(part.lower())
    return "-".join(out)


def primary(tag: str) -> str:
    """The language subtag: ``"en"`` of ``"en-US"``."""
    return normalise_tag(tag).split("-")[0] if tag else ""


# ------------------------------------------------------------- the OS


def os_language_tags() -> list[str]:
    """Windows' display language, then its region's locale (``["en-US"]``).

    ``locale.getlocale()`` on Windows answers ``"English_United States"``, not a
    tag, so the LCIDs are asked for and mapped through Python's own table.
    Elsewhere, the process locale. Never raises; ``[]`` when nothing is known.
    """
    tags: list[str] = []
    if sys.platform == "win32":
        try:
            import ctypes

            kernel32 = ctypes.WinDLL("kernel32")
            for lcid in (kernel32.GetUserDefaultUILanguage(), kernel32.GetUserDefaultLCID()):
                tag = normalise_tag(locale.windows_locale.get(int(lcid), ""))
                if tag and tag not in tags:
                    tags.append(tag)
        except Exception:  # noqa: BLE001 - a suggestion, never a failure
            pass
    if not tags:
        try:
            tag = normalise_tag(locale.getlocale()[0])
        except Exception:  # noqa: BLE001
            tag = ""
        if tag:
            tags.append(tag)
    return tags


# ------------------------------------------------------- the document


def document_language(path: Path | str | None) -> str:
    """The language a file says it is in (``"en-GB"``), or ``""``.

    Word (the document's own language, else its default style's), PDF
    (``/Lang``), HTML and EPUB. Read locally; never raises.
    """
    if not path:
        return ""
    source = Path(path)
    suffix = source.suffix.lower()
    try:
        if suffix == ".docx":
            return _docx_language(source)
        if suffix == ".pdf":
            return _pdf_language(source)
        if suffix in (".html", ".htm", ".xhtml"):
            head = source.read_bytes()[:65536].decode("utf-8", "replace")
            return _html_lang(head)
        if suffix == ".epub":
            with zipfile.ZipFile(source) as archive:
                for name in archive.namelist():
                    if name.lower().endswith(".opf"):
                        text = archive.read(name)[:65536].decode("utf-8", "replace")
                        found = re.search(r"<dc:language[^>]*>\s*([^<\s]+)", text)
                        if found:
                            return normalise_tag(found.group(1))
    except Exception:  # noqa: BLE001 - a suggestion, never a failure
        return ""
    return ""


def _html_lang(text: str) -> str:
    found = re.search(r"<html[^>]*\blang\s*=\s*[\"']?([A-Za-z0-9_-]+)", text, re.IGNORECASE)
    return normalise_tag(found.group(1)) if found else ""


def _docx_language(source: Path) -> str:
    with zipfile.ZipFile(source) as archive:
        names = set(archive.namelist())
        if "docProps/core.xml" in names:
            core = archive.read("docProps/core.xml").decode("utf-8", "replace")
            found = re.search(r"<dc:language[^>]*>\s*([^<\s]+)", core)
            if found and normalise_tag(found.group(1)):
                return normalise_tag(found.group(1))
        if "word/styles.xml" in names:
            styles = archive.read("word/styles.xml").decode("utf-8", "replace")
            found = re.search(r"<w:lang\b[^>]*\bw:val=\"([^\"]+)\"", styles)
            if found:
                return normalise_tag(found.group(1))
    return ""


def _pdf_language(source: Path) -> str:
    try:
        import pypdf  # type: ignore[import-not-found,unused-ignore]  # an optional extra
    except ImportError:
        return ""
    reader = pypdf.PdfReader(str(source))
    root: Any = reader.trailer["/Root"]
    return normalise_tag(str(root.get("/Lang", "") or ""))


# ------------------------------------------------------ the suggestion


def suggest_dialect(dialects: list[tuple[str, str]], hints: list[str], language: str) -> str:
    """The dialect locale to start on for *language*, or ``""`` (Scribe's default).

    *dialects* is Scribe's ``[(name, locale), ...]`` for *language*; *hints*
    are tags in order of trust (the document's, then the OS's). Exact match
    first, over every hint; then the first of Scribe's dialects when any hint
    is in *language* at all; else nothing.
    """
    if not dialects or not language:
        return ""
    lang = primary(language)
    by_tag = {normalise_tag(locale_id).lower(): locale_id for _name, locale_id in dialects}
    relevant = [tag for tag in (normalise_tag(h) for h in hints) if tag and primary(tag) == lang]
    for tag in relevant:
        exact = by_tag.get(tag.lower())
        if exact:
            return exact
    if relevant:
        return dialects[0][1]
    return ""


def guess_language(dialects: dict[str, list[tuple[str, str]]], hints: list[str]) -> str:
    """For Language on "Detect automatically": the language code of Scribe's
    whose dialects the first hint with any belongs to, or ``""``."""
    codes = {primary(code): code for code in dialects if dialects.get(code)}
    for hint in hints:
        code = codes.get(primary(hint))
        if code:
            return code
    return ""


# ------------------------------------------------------ the voice list


@dataclass(frozen=True, slots=True)
class VoiceItem:
    """One row of the Voice list."""

    label: str
    short_name: str
    locale: str
    has_sample: bool
    #: The voice's own name, without its dialect or sample note.
    name: str


def voice_items(
    locale_id: str,
    dialects: list[tuple[str, str]],
    voices: dict[str, list[tuple[str, str, bool]]],
) -> list[VoiceItem]:
    """The Voice list (not counting Scribe's default).

    With a dialect (*locale_id*), its voices by name; without one, every
    dialect's in *dialects* order, each with its dialect's name.
    """
    items: list[VoiceItem] = []
    if locale_id:
        for name, short, has in voices.get(locale_id, []):
            label = name if has else f"{name}, {NO_SAMPLE}"
            items.append(VoiceItem(label, short, locale_id, has, name))
        return items
    for dialect_name, dialect_locale in dialects:
        for name, short, has in voices.get(dialect_locale, []):
            label = f"{name}, {dialect_name}" + ("" if has else f", {NO_SAMPLE}")
            items.append(VoiceItem(label, short, dialect_locale, has, name))
    return items


__all__ = [
    "NO_SAMPLE",
    "VoiceItem",
    "document_language",
    "guess_language",
    "normalise_tag",
    "os_language_tags",
    "primary",
    "suggest_dialect",
    "voice_items",
]
