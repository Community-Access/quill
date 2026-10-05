"""One honest decoder for a text file, shared by QUILL and QUILL Lite.

The family rule this module keeps is short: **opening a file must never lose a
byte of it.** Two decoders used to answer "what is in this file?" -- QUILL's in
``quill/io/text.py`` and QUILL Lite's in ``quill/core/lite/textfile.py`` -- and
Lite's fell back to Windows-1252 with ``errors="replace"``. Windows-1252 leaves
five byte values undefined (0x81, 0x8D, 0x8F, 0x90 and 0x9D), so a file holding
any of them opened with a replacement character in its place, and the next
save wrote that replacement character over the original byte. Nothing was said
at either end. PlanCake's design (Andre, Oire Software) refuses to write a file
whose encoding it is unsure of; the 2026-10-04 design note took that caution
and found this.

So there is one decoder now, and it never replaces anything:

1. A byte-order mark is decisive: UTF-8 with BOM, UTF-16 little-endian, UTF-16
   big-endian. UTF-32's mark is excluded, because its first two bytes are the
   UTF-16 little-endian mark.
2. Strict UTF-8 next, because a UTF-8 file is also often valid Windows-1252.
3. Strict Windows-1252, the encoding of most old Windows text.
4. Latin-1 last, which maps every byte to a character and back, so it cannot
   fail and a save puts every byte back exactly where it was.

A decode that fails in step 1 (a BOM followed by bytes that are not that
encoding) falls through to the same chain rather than raising, for the same
reason: the file opens, and saves back unchanged.

Anything that is not UTF-8 is said once on open (:func:`open_notice`), because
the person cannot otherwise know, and **Reopen with Encoding** in the File
Format window re-reads the same bytes under a code page the person chooses
(:func:`decode_as`), strictly -- a choice that does not fit the bytes is
refused in a sentence rather than half-applied.

Importing this module also registers ``utf-16-be-bom`` as a real codec, so a
big-endian UTF-16 file is written back big-endian with its mark by either
editor's writer instead of being quietly flipped to little-endian.

wx-free, strict-typed.
"""

from __future__ import annotations

import codecs
from collections.abc import Buffer
from dataclasses import dataclass

__all__ = [
    "FALLBACK_ENCODINGS",
    "REOPEN_ENCODINGS",
    "UTF16_BE_BOM_CODEC",
    "DecodedBytes",
    "decode_as",
    "decode_bytes",
    "encoding_display_name",
    "is_utf8_family",
    "open_notice",
    "reopen_mismatch_sentence",
    "reopened_sentence",
]

#: Big-endian UTF-16 with a BOM. Python has no single codec for it -- ``utf-16``
#: always writes little-endian and ``utf-16-be`` writes no mark -- so this
#: module registers one under this name (see the bottom of the file).
UTF16_BE_BOM_CODEC = "utf-16-be-bom"

_UTF8_BOM = b"\xef\xbb\xbf"
_UTF16_LE_BOM = b"\xff\xfe"
_UTF16_BE_BOM = b"\xfe\xff"
_UTF32_LE_BOM = b"\xff\xfe\x00\x00"

#: Tried in this order after UTF-8 fails. Latin-1 is last because it cannot
#: fail: every byte is a character, and every one of those characters encodes
#: back to the same byte.
FALLBACK_ENCODINGS: tuple[str, ...] = ("cp1252", "latin-1")

#: How each encoding is named to a person. Plain names, not codec strings.
_DISPLAY_NAMES: dict[str, str] = {
    "utf-8": "UTF-8",
    "utf-8-sig": "UTF-8 with BOM",
    "utf-16": "UTF-16",
    UTF16_BE_BOM_CODEC: "UTF-16 big-endian",
    "utf-16-le": "UTF-16 little-endian, no BOM",
    "utf-16-be": "UTF-16 big-endian, no BOM",
    "cp1252": "Windows-1252",
    "latin-1": "Latin-1 (ISO 8859-1)",
    "cp1250": "Windows-1250 (Central European)",
    "cp1251": "Windows-1251 (Cyrillic)",
    "cp1253": "Windows-1253 (Greek)",
    "cp1254": "Windows-1254 (Turkish)",
    "cp437": "DOS code page 437",
    "cp850": "DOS code page 850 (Western European)",
    "mac_roman": "Mac OS Roman",
}

#: What Reopen with Encoding offers, as ``(codec, name)``. Wider than the four
#: a file can be *saved* as from scratch: these are the encodings old files are
#: actually found in, and reopening is how a person tells QUILL which one.
REOPEN_ENCODINGS: tuple[tuple[str, str], ...] = (
    ("utf-8", "UTF-8"),
    ("cp1252", "Windows-1252 (Western European)"),
    ("latin-1", "Latin-1 (ISO 8859-1)"),
    ("utf-16", "UTF-16 (with a byte-order mark)"),
    ("utf-16-le", "UTF-16 little-endian, no BOM"),
    ("utf-16-be", "UTF-16 big-endian, no BOM"),
    ("cp1250", "Windows-1250 (Central European)"),
    ("cp1251", "Windows-1251 (Cyrillic)"),
    ("cp1253", "Windows-1253 (Greek)"),
    ("cp1254", "Windows-1254 (Turkish)"),
    ("cp437", "DOS code page 437"),
    ("cp850", "DOS code page 850 (Western European)"),
    ("mac_roman", "Mac OS Roman"),
)


@dataclass(frozen=True, slots=True)
class DecodedBytes:
    """A file's text, and the codec that writes it back byte for byte.

    ``text`` keeps the file's own line endings; each editor normalises them
    its own way. ``fallback`` is true when neither a BOM nor strict UTF-8
    explained the bytes.
    """

    text: str
    encoding: str
    fallback: bool = False


def is_utf8_family(encoding: str) -> bool:
    """True for UTF-8 with or without a BOM, however the codec is spelled."""
    folded = encoding.replace("-", "").replace("_", "").lower()
    return folded in {"utf8", "utf8sig"}


def _decode_bom(raw: bytes) -> DecodedBytes | None:
    """The BOM's answer, or ``None`` when there is no BOM or it lied."""
    try:
        if raw.startswith(_UTF8_BOM):
            return DecodedBytes(raw[len(_UTF8_BOM) :].decode("utf-8"), "utf-8-sig")
        if raw.startswith(_UTF32_LE_BOM):
            return None
        if raw.startswith(_UTF16_LE_BOM):
            return DecodedBytes(raw.decode("utf-16"), "utf-16")
        if raw.startswith(_UTF16_BE_BOM):
            return DecodedBytes(raw.decode("utf-16"), UTF16_BE_BOM_CODEC)
    except UnicodeDecodeError:
        return None
    return None


def decode_bytes(raw: bytes) -> DecodedBytes:
    """Decode *raw* without losing a byte. Never raises for any input."""
    by_bom = _decode_bom(raw)
    if by_bom is not None:
        return by_bom
    try:
        return DecodedBytes(raw.decode("utf-8"), "utf-8")
    except UnicodeDecodeError:
        pass
    for fallback in FALLBACK_ENCODINGS:
        try:
            return DecodedBytes(raw.decode(fallback), fallback, fallback=True)
        except UnicodeDecodeError:
            continue
    # Unreachable: latin-1 decodes every byte. Kept so the type is honest.
    return DecodedBytes(raw.decode("latin-1"), "latin-1", fallback=True)  # pragma: no cover


def decode_as(raw: bytes, codec: str) -> DecodedBytes:
    """Decode *raw* strictly as *codec*. Raises ``UnicodeDecodeError`` if it does not fit.

    The codec the result carries is the one that writes the same bytes back:
    UTF-8 with a mark becomes ``utf-8-sig``, and UTF-16 with a big-endian mark
    becomes ``utf-16-be-bom``. UTF-16 chosen for a file with no mark is read as
    little-endian, which is what Windows writes, and saved without a mark.
    ``LookupError`` for a codec Python does not know.
    """
    codecs.lookup(codec)
    if is_utf8_family(codec):
        if raw.startswith(_UTF8_BOM):
            return DecodedBytes(raw[len(_UTF8_BOM) :].decode("utf-8"), "utf-8-sig")
        return DecodedBytes(raw.decode("utf-8"), "utf-8")
    if codec == "utf-16":
        if raw.startswith(_UTF16_BE_BOM):
            return DecodedBytes(raw.decode("utf-16"), UTF16_BE_BOM_CODEC)
        if raw.startswith(_UTF16_LE_BOM):
            return DecodedBytes(raw.decode("utf-16"), "utf-16")
        return DecodedBytes(raw.decode("utf-16-le"), "utf-16-le")
    return DecodedBytes(raw.decode(codec), codec)


def encoding_display_name(codec: str) -> str:
    """The name a person hears for *codec*; the codec itself if it is unknown."""
    return _DISPLAY_NAMES.get(codec, codec)


def open_notice(codec: str) -> str:
    """What to say on open, once, when the file is not UTF-8. ``""`` when it is.

    An outcome only the app knows (GATE-13): the screen reader can read the
    text but cannot know what encoding it came in, and the encoding decides
    what a save will be able to hold.
    """
    if not codec or is_utf8_family(codec):
        return ""
    return f"Opened as {encoding_display_name(codec)}, not UTF-8."


def reopened_sentence(codec: str) -> str:
    """The outcome of a successful Reopen with Encoding."""
    name = encoding_display_name(codec)
    return f"Reopened as {name}. It saves as {name} unless you choose another encoding."


def reopen_mismatch_sentence(codec: str) -> str:
    """The outcome of a Reopen whose code page does not fit the bytes."""
    return (
        f"This file is not valid {encoding_display_name(codec)}, so nothing was "
        "changed. Try another encoding."
    )


# -- the utf-16-be-bom codec ------------------------------------------------ #


def _be_bom_encode(text: str, errors: str = "strict") -> tuple[bytes, int]:
    payload, consumed = codecs.utf_16_be_encode(text, errors)
    return _UTF16_BE_BOM + payload, consumed


def _be_bom_decode(data: Buffer, errors: str = "strict") -> tuple[str, int]:
    body = bytes(data)
    skipped = 0
    if body.startswith(_UTF16_BE_BOM):
        body, skipped = body[2:], 2
    text, consumed = codecs.utf_16_be_decode(body, errors, True)
    return text, consumed + skipped


class _BeBomIncrementalEncoder(codecs.IncrementalEncoder):
    """Writes the big-endian mark once, before the first character."""

    def __init__(self, errors: str = "strict") -> None:
        super().__init__(errors)
        self._started = False

    def encode(self, input: str, final: bool = False) -> bytes:  # noqa: A002 - codec API
        payload = codecs.utf_16_be_encode(input, self.errors)[0]
        if self._started:
            return payload
        self._started = True
        return _UTF16_BE_BOM + payload

    def reset(self) -> None:
        self._started = False

    def getstate(self) -> int:
        return 1 if self._started else 0

    def setstate(self, state: int | str) -> None:
        self._started = bool(state)


class _BeBomIncrementalDecoder(codecs.BufferedIncrementalDecoder):
    """Skips the big-endian mark once, then reads UTF-16 big-endian."""

    def __init__(self, errors: str = "strict") -> None:
        super().__init__(errors)
        self._started = False

    def _buffer_decode(self, input: Buffer, errors: str, final: bool) -> tuple[str, int]:  # noqa: A002
        skipped = 0
        data = bytes(input)
        if not self._started:
            if len(data) < 2 and not final:
                return "", 0
            self._started = True
            if data.startswith(_UTF16_BE_BOM):
                data, skipped = data[2:], 2
        text, consumed = codecs.utf_16_be_decode(data, errors, final)
        return text, consumed + skipped

    def reset(self) -> None:
        super().reset()
        self._started = False


class _BeBomStreamWriter(codecs.StreamWriter):
    def encode(self, input: str, errors: str = "strict") -> tuple[bytes, int]:  # noqa: A002
        return _be_bom_encode(input, errors)


class _BeBomStreamReader(codecs.StreamReader):
    def decode(self, input: bytes, errors: str = "strict") -> tuple[str, int]:  # noqa: A002
        return _be_bom_decode(input, errors)


_BE_BOM_INFO = codecs.CodecInfo(
    name=UTF16_BE_BOM_CODEC,
    encode=_be_bom_encode,
    decode=_be_bom_decode,
    incrementalencoder=_BeBomIncrementalEncoder,
    incrementaldecoder=_BeBomIncrementalDecoder,
    streamwriter=_BeBomStreamWriter,
    streamreader=_BeBomStreamReader,
)


def _search(name: str) -> codecs.CodecInfo | None:
    if name.replace("-", "_") == "utf_16_be_bom":
        return _BE_BOM_INFO
    return None


codecs.register(_search)
