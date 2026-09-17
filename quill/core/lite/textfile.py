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
_UTF16_BOMS = (b"\xff\xfe", b"\xfe\xff")


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
    elif data.startswith(_UTF16_BOMS):
        text, encoding = data.decode("utf-16", errors="replace"), "utf-16"
    else:
        try:
            text, encoding = data.decode("utf-8"), "utf-8"
        except UnicodeDecodeError:
            text, encoding = data.decode("cp1252", errors="replace"), "cp1252"
    newline = "\r\n" if "\r\n" in text else ("\r" if "\r" in text else "\n")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return DecodedText(text=normalized, encoding=encoding, newline=newline)


def _encoding_name(codec: str) -> str:
    """How a codec is named to a person; the raw codec if it is not one of ours.

    From the same table the chooser and the status bar read, so the three
    cannot call one encoding three things.
    """
    return dict(ENCODING_CHOICES).get(codec, codec)


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
