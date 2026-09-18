"""Reading and writing plain text files byte-honestly.

A Notepad replacement is judged on one thing above all: open a file, change
nothing, save it, and the bytes must be the bytes you started with. That is
harder than it sounds, because three separate things are easy to lose:

* **The encoding.** A UTF-8 file with a BOM must keep its BOM; a UTF-16 file
  must stay UTF-16; and the enormous installed base of Windows text files that
  are neither is cp1252, which never fails to decode and so must be tried last
  rather than first.
* **The line endings.** Windows text is CRLF, but a file that arrived from a
  shell script is LF and must not silently gain carriage returns because it was
  opened in an editor once.
* **The last line.** A file that does not end in a newline must not grow one,
  and a file that does must not lose it. Both are round-trip failures that show
  up in somebody's version control diff rather than in the editor.

The control itself works in ``\\n`` throughout -- Rich Edit normalises anyway --
so the newline the file was read with is remembered and re-applied on the way
out. All of that is here, wx-free, so it can be tested against real bytes
rather than against a screenshot.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "ENCODING_CHOICES",
    "UTF16_BE_BOM_CODEC",
    "encoding_rows",
    "newline_rows",
    "unencodable_characters",
    "unencodable_warning",
    "NEWLINE_CHOICES",
    "DecodedText",
    "decode_text",
    "encode_text",
    "write_bytes_atomic",
]

#: The encodings a person can deliberately choose, as ``(codec, name)``.
#: Four, not forty: these are the ones Windows text files are actually in, and a
#: dropdown of every codec Python knows is a dropdown nobody can choose from.
#: The names are Notepad's, so somebody who has seen its Save As dialog
#: recognises them.
ENCODING_CHOICES: tuple[tuple[str, str], ...] = (
    ("utf-8", "UTF-8"),
    ("utf-8-sig", "UTF-8 with BOM"),
    ("utf-16", "UTF-16"),
    ("cp1252", "Windows-1252 (ANSI)"),
)

#: Line endings, as ``(value, name)``. The name says which world each belongs
#: to, because "CRLF" alone answers nothing for the person who needs to know
#: whether their build server will accept the file.
NEWLINE_CHOICES: tuple[tuple[str, str], ...] = (
    ("\r\n", "CRLF (Windows)"),
    ("\n", "LF (Unix, macOS, most build tools)"),
)

_UTF8_BOM = b"\xef\xbb\xbf"
_UTF16_LE_BOM = b"\xff\xfe"
_UTF16_BE_BOM = b"\xfe\xff"

#: Big-endian UTF-16 with a BOM, which Python has no single codec for: the
#: ``utf-16`` codec always writes little-endian, and ``utf-16-be`` writes no BOM
#: at all. Named here so the encoding a document carries can say "big-endian",
#: which is the whole of bad.md F8: both byte orders decoded to "utf-16" and
#: every big-endian file was quietly rewritten little-endian on a save that
#: changed nothing else. A byte-order swap is invisible in the editor and
#: visible to everything downstream that reads the file.
UTF16_BE_BOM_CODEC = "utf-16-be-bom"


@dataclass(frozen=True, slots=True)
class DecodedText:
    """One file, decoded, plus everything needed to write it back unchanged."""

    #: The text with every line ending normalised to ``\\n``.
    text: str
    #: The codec to encode with. Round-trips the BOM: ``utf-8-sig`` writes one.
    encoding: str
    #: The line ending the file actually used, re-applied on save.
    newline: str


def decode_text(data: bytes) -> DecodedText:
    """Decode *data*, remembering its encoding and its line endings.

    The order is deliberate. A BOM is decisive, so it is checked first. Strict
    UTF-8 is tried next, because a UTF-8 file that also happens to be valid
    cp1252 must be read as UTF-8. cp1252 is the fallback precisely because it
    *cannot* fail -- every byte maps to something -- so trying it earlier would
    mean never detecting anything else.
    """
    if data.startswith(_UTF8_BOM):
        text, encoding = data[len(_UTF8_BOM) :].decode("utf-8", errors="replace"), "utf-8-sig"
    elif data.startswith(_UTF16_LE_BOM):
        text, encoding = data.decode("utf-16", errors="replace"), "utf-16"
    elif data.startswith(_UTF16_BE_BOM):
        text, encoding = data.decode("utf-16", errors="replace"), UTF16_BE_BOM_CODEC
    else:
        try:
            text, encoding = data.decode("utf-8"), "utf-8"
        except UnicodeDecodeError:
            text, encoding = data.decode("cp1252", errors="replace"), "cp1252"
    newline = "\r\n" if "\r\n" in text else ("\r" if "\r" in text else "\n")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return DecodedText(text=normalized, encoding=encoding, newline=newline)


#: Encodings and line endings a file can arrive in that the chooser does not
#: offer: read faithfully, written back faithfully, never offered as a new
#: choice. ``utf-16-be-bom`` because little-endian is what Windows means by
#: UTF-16, and classic-Mac CR because no tool has written one this century.
_READ_ONLY_ENCODING_NAMES: dict[str, str] = {
    UTF16_BE_BOM_CODEC: "UTF-16 big-endian",
    "utf-16-be": "UTF-16 big-endian, no BOM",
    "utf-16-le": "UTF-16 little-endian, no BOM",
}
_READ_ONLY_NEWLINE_NAMES: dict[str, str] = {"\r": "CR (classic Mac)"}


def _encoding_name(codec: str) -> str:
    """How a codec is named to a person; the raw codec if it is not one of ours.

    From the same table the chooser and the status bar read, so the three
    cannot call one encoding three things.
    """
    if codec in _READ_ONLY_ENCODING_NAMES:
        return _READ_ONLY_ENCODING_NAMES[codec]
    return dict(ENCODING_CHOICES).get(codec, codec)


def encoding_rows(current: str) -> tuple[tuple[str, str], ...]:
    """The chooser's encoding rows, with the document's own added if it is missing.

    The bug this closes is one line of arithmetic (bad.md F8). The chooser
    selected the index of the current value and fell back to **0** for anything
    it did not offer -- and index 0 is UTF-8. So a UTF-16 big-endian file opened
    the dialog reading "UTF-8", and OK, the safe-looking answer, re-encoded the
    document. A dialog that cannot show the state it is editing must not be
    allowed to answer for it, so the state becomes a row.
    """
    if any(codec == current for codec, _name in ENCODING_CHOICES):
        return ENCODING_CHOICES
    return ((current, f"{_encoding_name(current)} (keep as is)"), *ENCODING_CHOICES)


def newline_rows(current: str) -> tuple[tuple[str, str], ...]:
    """The chooser's line-ending rows, on the same rule as :func:`encoding_rows`.

    The case that bit: a classic-Mac CR file preselected CRLF, so OK converted
    every line ending in the document and said nothing.
    """
    if any(value == current for value, _name in NEWLINE_CHOICES):
        return NEWLINE_CHOICES
    name = _READ_ONLY_NEWLINE_NAMES.get(current, "Mixed")
    return ((current, f"{name} (keep as is)"), *NEWLINE_CHOICES)


def unencodable_characters(text: str, encoding: str) -> list[str]:
    """The distinct characters *encoding* cannot hold, in the order they appear.

    Asked *before* the write, so the app can say what it is about to lose rather
    than losing it. ``errors="replace"`` turned an em dash typed into a cp1252
    file into a question mark with nothing said, which is the quietest possible
    way to damage somebody's document -- and the damage is only visible if they
    happen to read that line again (bad.md F3).
    """
    missing: list[str] = []
    seen: set[str] = set()
    for character in text:
        if character in seen:
            continue
        seen.add(character)
        try:
            character.encode(encoding)
        except UnicodeEncodeError:
            missing.append(character)
    return missing


def unencodable_warning(count: int, encoding: str) -> str:
    """The one sentence both editors ask with, when characters will not fit.

    One string, because two products asking the same question in two different
    ways is two things to learn -- and this one is asked at the worst possible
    moment, which is while somebody is trying to save.
    """
    plural = "" if count == 1 else "s"
    return (
        f"{count} character{plural} cannot be saved as {_encoding_name(encoding)}. "
        "Save as UTF-8 instead?"
    )


def encode_text(text: str, *, encoding: str, newline: str) -> bytes:
    """The bytes to write for *text*, restoring *newline* and *encoding*.

    ``errors="replace"`` is the last resort rather than the policy: the caller
    asks :func:`unencodable_characters` first and offers UTF-8, so by the time
    this runs the user has either chosen an encoding that fits or chosen to lose
    the characters knowingly. It stays ``replace`` because a save that *raises*
    is a save that loses the document, which is the worse of the two.
    """
    restored = text.replace("\n", newline) if newline != "\n" else text
    if encoding == UTF16_BE_BOM_CODEC:
        # Python has no codec for "big-endian with a BOM": utf-16 always writes
        # little-endian and utf-16-be writes no BOM, so the two halves are put
        # together here (bad.md F8).
        return _UTF16_BE_BOM + restored.encode("utf-16-be", errors="replace")
    return restored.encode(encoding, errors="replace")


def write_bytes_atomic(target: Path, payload: bytes) -> None:
    """Write *payload* to *target* via a temp file in the same directory.

    The same guarantee :func:`quill.core.storage.write_json_atomic` gives QUILL's
    settings, for the user's own documents: a power cut during a save leaves
    either the old file or the new one, never a truncated file. The temp file is
    a sibling because ``os.replace`` is only atomic within one filesystem.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, raw_temp = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".quilllite-tmp", dir=target.parent
    )
    temp_path = Path(raw_temp)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, target)
    except BaseException:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise
