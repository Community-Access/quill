from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from quill.core.document import Document
from quill.core.storage import write_text_atomic
from quill.core.text_decoding import decode_as, decode_bytes, is_utf8_family

# Braille text family (#226 / BR-004). Saving any of these must round-trip
# byte-for-byte (#235 / BR-012): no line-ending normalization, no trailing
# space trimming, form feeds and encoding preserved.
BRF_SUFFIXES: frozenset[str] = frozenset({".brf", ".brl", ".pef", ".ueb"})

# Soft save-warning hook (#235 / BR-012). The UI registers a callback so a BRF
# saved with non-NABCC characters surfaces a single, non-blocking announcement;
# tests register a collector. None means warnings are silently dropped.
_save_warning_hook: Callable[[str], None] | None = None


def set_save_warning_hook(hook: Callable[[str], None] | None) -> None:
    """Register (or clear) the soft save-warning sink. Returns nothing."""
    global _save_warning_hook
    _save_warning_hook = hook


def _emit_save_warning(message: str) -> None:
    hook = _save_warning_hook
    if hook is None:
        return
    try:
        hook(message)
    except Exception:  # noqa: BLE001 - a warning sink must never break a save
        pass


#: The two UTF-16 byte-order marks, and what each means (bad.md F6, P1.8).
#: A UTF-16 file opened as UTF-8 did not raise -- most of its bytes decode as
#: cp1252 through the fallback below -- so it opened as a document with a NUL
#: between every letter, which reads as gibberish and SAVES as gibberish. The
#: BOM is the only reliable signal and Notepad has used it since Windows 95.
_UTF16_BOMS: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xfe", "utf-16"),  # little-endian, which is what Windows writes
    (b"\xfe\xff", "utf-16"),  # big-endian; the codec reads the BOM either way
)


def detect_utf16(raw: bytes) -> str | None:
    """``"utf-16"`` when *raw* begins with a UTF-16 byte-order mark, else None.

    BOM only, deliberately. Heuristics over NUL density guess wrong on binary
    files and on short ones, and a wrong guess here corrupts a document the
    person then saves. A UTF-16 file without a BOM is rare, and Windows writes
    one; the honest answer for the rest is the fallback chain.

    ``b"\xff\xfe\x00\x00"`` is UTF-32 LE, whose first two bytes are the UTF-16
    LE mark. It is excluded rather than mis-read as an empty UTF-16 document.
    """
    if raw[:4] == b"\xff\xfe\x00\x00":
        return None
    for bom, name in _UTF16_BOMS:
        if raw.startswith(bom):
            return name
    return None


# #867: a plain-text open must never crash on a non-UTF-8 file. The fallback
# chain (cp1252, then latin-1, which cannot fail) lives in the shared
# quill.core.text_decoding since 2026-10-04, so both editors read one way.


def read_text_document(path: Path, encoding: str = "utf-8") -> Document:
    # Read raw bytes so we can (a) detect the original line ending before
    # Python's universal-newline translation rewrites every CRLF to LF (#649)
    # and (b) recognise and transparently strip a UTF-8 BOM (#648). Reading via
    # ``path.read_text`` did both invisibly: CRLF files were always mis-detected
    # as LF, and a leading BOM showed up as an editable U+FEFF at the cursor.
    raw = path.read_bytes()

    # The default is the family's one lossless decoder (2026-10-04), shared
    # with QUILL Lite: a BOM, strict UTF-8, strict cp1252, then latin-1, which
    # cannot fail -- so a file always opens and always saves back byte for
    # byte. An explicit encoding is an instruction, and a reader that overrules
    # it cannot be used to open a file the way its owner says it is
    # (test_text.py has said so since #867): it is decoded strictly and raises.
    if is_utf8_family(encoding):
        decoded = decode_bytes(raw)
    else:
        decoded = decode_as(raw, encoding)
    text = decoded.text
    # The encoding a BOM or a fallback revealed is said once on open
    # (_announce_encoding_fallback); UTF-16's BOM and both fallbacks count.
    detected_encoding = None if is_utf8_family(decoded.encoding) else decoded.encoding

    # Detect the original line ending, then hand the editor LF-only text (wx
    # normalises to LF anyway); the writer converts back on save. From the
    # decoded text, because a UTF-16 CRLF is not the bytes b"\r\n".
    line_ending = "\r\n" if "\r\n" in text else "\n"
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    source_metadata: dict[str, object] = {
        "source_kind": "text",
        "engine": "plain text",
        "quality_score": 100,
    }
    if detected_encoding is not None:
        source_metadata["encoding_detected"] = detected_encoding

    return Document(
        text=text,
        path=path,
        modified=False,
        encoding=decoded.encoding,
        line_ending=line_ending,
        source_metadata=source_metadata,
    )


def write_text_document(document: Document, path: Path | None = None) -> Path:
    target_path = path or document.path
    if target_path is None:
        raise ValueError("A path is required to save this document.")

    if target_path.suffix.lower() in BRF_SUFFIXES:
        return _write_brf_document(document, target_path)

    text = _normalize_line_endings(document.text, document.line_ending)
    # Write atomically (temp + os.replace) so a crash mid-save can't corrupt the
    # user's document at its real location — the previous file stays intact
    # until the new one is fully written and fsynced.
    write_text_atomic(target_path, text, encoding=document.encoding, newline="")
    document.mark_saved(target_path)
    return target_path


def _write_brf_document(document: Document, target_path: Path) -> Path:
    """Save a braille text file byte-for-byte (#235 / BR-012).

    No line-ending normalization, no trailing-space trimming, form feeds and
    the original text preserved exactly. ``newline=""`` stops Python from
    translating ``\\n``. A soft, non-blocking warning is emitted (via the
    save-warning hook) when the text contains non-NABCC characters; those
    characters are still written unchanged, falling back to UTF-8 so the save
    never crashes on a braille-unicode codepoint.
    """
    from quill.core.brf_ascii import find_non_brf_ascii_offsets

    text = document.text
    offsets = find_non_brf_ascii_offsets(text)
    encoding = document.encoding or "utf-8"
    if offsets:
        encoding = "utf-8"
        count = len(offsets)
        plural = "s" if count != 1 else ""
        _emit_save_warning(
            f"{target_path.name} was saved with {count} non-braille-ASCII "
            f"character{plural} preserved as-is."
        )
    write_text_atomic(target_path, text, encoding=encoding, newline="")
    document.mark_saved(target_path)
    return target_path


def _normalize_line_endings(text: str, line_ending: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if line_ending == "\n":
        return normalized
    return normalized.replace("\n", line_ending)
