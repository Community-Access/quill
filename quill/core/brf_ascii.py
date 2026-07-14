"""NABCC (North American Braille Computer Code) character set and helpers.

The Braille Mode feature treats ``.brf`` / ``.brl`` / ``pef`` / ``.ueb``
files as plain ASCII text in NABCC, with three load-time guarantees:

1. A UTF-8 BOM at the start of the file is stripped (NABCC has no BOM
   concept). The caller is told whether a BOM was present so the UI can
   surface a one-time announcement.
2. The text is scanned for any character outside the NABCC range. The
   matching offsets are returned for the warning path; the bytes are
   *not* transformed. A BRF/BRL must be saved byte-for-byte (BR-012).
3. Line endings are detected as ``CRLF`` / ``LF`` / ``CR`` / mixed so the
   save path (BR-012) can preserve them.

This module is wx-free; it lives in ``quill/core`` and is imported by
``quill/io/open_read.py`` on the BRF read path. Strict-typed: mypy
``--strict`` must stay clean.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# UTF-8 byte order mark.
_UTF8_BOM = b"\xef\xbb\xbf"

# NABCC is a strict subset of printable ASCII (0x20-0x7F) plus CR, LF,
# FF (form feed, 0x0C) and HT (horizontal tab, 0x09). Bytes >= 0x80 are
# non-BRF-ASCII and are returned as warnings, not errors.
BRF_FORM_FEED = "\x0c"
BRF_HORIZONTAL_TAB = "\t"


def is_brf_ascii_byte(byte: int) -> bool:
    """Return True when ``byte`` is allowed in a NABCC BRF stream."""
    return 0x09 <= byte <= 0x0D or 0x20 <= byte <= 0x7E


def strip_bom(raw_bytes: bytes) -> tuple[str, bool]:
    """Decode ``raw_bytes`` to text and strip a leading UTF-8 BOM.

    Returns ``(text, had_bom)``. The text is decoded as ``utf-8`` with
    ``errors="replace"`` so a malformed BRF never crashes the open path;
    the replaced characters show up in the non-BRF-ASCII warning list
    anyway.
    """
    had_bom = raw_bytes.startswith(_UTF8_BOM)
    if had_bom:
        raw_bytes = raw_bytes[len(_UTF8_BOM) :]
    text = raw_bytes.decode("utf-8", errors="replace")
    return text, had_bom


def find_non_brf_ascii_offsets(text: str) -> list[int]:
    """Return the character offsets of every non-NABCC character in ``text``.

    These are char offsets (code-point positions), not byte offsets; the
    document model is text-based and the page map (BR-006) operates on
    char offsets throughout.
    """
    return [index for index, ch in enumerate(text) if not is_brf_ascii_byte(ord(ch))]


def looks_like_braille(text: str) -> bool:
    """Heuristically decide whether ``text`` is ASCII-braille (NABCC/BRF) content.

    Used to offer "open in Braille Mode" when braille is pasted into a plain
    document. Conservative on purpose — ``is_brf_ascii_byte`` alone matches all
    printable ASCII (including ordinary prose), so this layers several braille-
    specific signals so that neither normal text nor ALL-CAPS prose trips it:

    1. Almost every character is NABCC (a stray non-ASCII rules it out).
    2. Letters are essentially all uppercase (braille ASCII has no lowercase).
    3. Lines are short (braille pages wrap at ~40 cells).
    4. At least one distinctive braille indicator is present: a form feed
       (page break), a number sign followed by a-j (braille digits), or capital/
       grouping signs that hug the next cell (``,A`` rather than ``, ``) — which
       ordinary punctuation (``, ``) never does.
    """
    sample = text[:4000]
    if len(sample) < 60:
        return False
    non_brf = sum(1 for ch in sample if not is_brf_ascii_byte(ord(ch)))
    if non_brf / len(sample) > 0.02:
        return False
    letters = [ch for ch in sample if ch.isalpha()]
    if len(letters) < 20:
        return False
    if sum(1 for ch in letters if ch.islower()) / len(letters) > 0.05:
        return False
    lines = [ln for ln in sample.splitlines() if ln.strip()]
    if not lines:
        return False
    if sum(len(ln) for ln in lines) / len(lines) > 42:
        return False
    has_formfeed = "\x0c" in sample
    has_number_sign = bool(re.search(r"#[a-jA-J]", sample))
    # Capital/grouping signs in braille immediately precede the next cell.
    indicator_hits = len(re.findall(r"[,;][^\s]", sample))
    return has_formfeed or has_number_sign or indicator_hits >= max(2, len(lines))


@dataclass(frozen=True)
class LineEndingReport:
    """Result of :func:`detect_line_endings`."""

    crlf: int
    lf: int
    cr: int
    form_feed: int

    @property
    def total(self) -> int:
        return self.crlf + self.lf + self.cr

    @property
    def is_mixed(self) -> bool:
        kinds = sum(1 for count in (self.crlf, self.lf, self.cr) if count > 0)
        return kinds > 1

    @property
    def dominant(self) -> str:
        """Return the most common line ending kind, or ``""`` for an empty file."""
        candidates: list[tuple[str, int]] = [
            ("\r\n", self.crlf),
            ("\n", self.lf),
            ("\r", self.cr),
        ]
        candidates.sort(key=lambda pair: pair[1], reverse=True)
        kind, count = candidates[0]
        if count == 0:
            return ""
        return kind


def detect_line_endings(text: str) -> LineEndingReport:
    """Count the line-ending characters in ``text``.

    A single ``\r\n`` sequence contributes 1 to ``crlf`` and 0 to the
    other two (CRLF is a single line break, not a CR followed by an LF).
    A lone ``\r`` (old-Mac style) contributes 1 to ``cr``; a lone ``\n``
    contributes 1 to ``lf``. Form feeds are counted separately because
    they are page terminators, not line terminators.
    """
    crlf = text.count("\r\n")
    lf = text.count("\n") - crlf
    cr = text.count("\r") - crlf
    form_feed = text.count(BRF_FORM_FEED)
    return LineEndingReport(crlf=crlf, lf=lf, cr=cr, form_feed=form_feed)
