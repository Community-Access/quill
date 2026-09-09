"""The shared audio tag and chapter model, vendored into two repositories.

This file is byte-identical in QUILL (``quill/core/speech/audio_tags_core.py``)
and podHarvest (``podharvest/audio_tags_core.py``). Editing one copy without
the other is what the drift test in each repo exists to catch. It imports
nothing from either host package, and imports mutagen lazily inside functions,
which is what makes both of those things possible -- podHarvest's command line
runs on the standard library alone, so a module it can import must not need a
third-party package just to load.

What lives here is everything the two apps must agree about: the table of tags
the editor shows, how each one maps to an ID3 frame and an MP4 atom, how tags
and chapter markers are read and written, and every operation that reshapes a
chapter list. What does not live here is anything either host is opinionated
about -- QUILL's coded errors and its ``AudioMetadata`` bridge, podHarvest's
logging voice -- because those are what the thin adapter in each repo is for.

Two decisions worth knowing before reading further:

* **Chapters are contiguous.** ``chapters[i].end_ms == chapters[i + 1].start_ms``
  always, so every millisecond of the file belongs to exactly one chapter and
  a boundary has one degree of freedom, not two. Moving a chapter's start
  moves the previous chapter's end with it; that is one edit, not two.
* **ID3 version follows the content.** Files are written as ID3v2.3, which is
  what the widest set of players reads, until the user sets a tag v2.3 has no
  frame for -- the sort fields and the full-precision dates -- at which point
  the file moves to v2.4. Mutagen's ``update_to_v23`` silently drops those
  frames, and a tag editor that quietly discards what you typed is not a tag
  editor.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- errors


class AudioTagError(Exception):
    """Anything this module refuses to do. Messages are meant to be spoken."""


class TagReadError(AudioTagError):
    """A file's tags or cover art could not be read."""


class TagWriteError(AudioTagError):
    """A file's tags could not be written; nothing was changed."""


class ChapterEditError(AudioTagError):
    """A chapter edit was not possible; the list is unchanged."""


# ----------------------------------------------------------------------- time format


def format_time_precise(ms: int) -> str:
    """Milliseconds as ``H:MM:SS.mmm`` -- the format the editor types in.

    Always shows hours and always shows milliseconds, unlike a display
    formatter that drops both when they are zero. That is the point: a marker
    nudged a tenth of a second has to visibly move, and a person typing a
    boundary needs to see the precision they are allowed to use.
    """
    total = max(0, int(ms))
    hours, rem = divmod(total, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1_000)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{millis:03d}"


_TIME_PATTERN = re.compile(r"^\d+(:\d{1,2}){0,2}(\.\d+)?$")


def parse_time(text: str) -> int | None:
    """``H:MM:SS.mmm``, ``M:SS``, or plain seconds into milliseconds.

    Returns ``None`` rather than raising when the text is not a time, because
    every caller is a text field somebody is still typing into.
    """
    token = str(text).strip()
    if not token or not _TIME_PATTERN.match(token):
        return None
    parts = token.split(":")
    try:
        seconds = 0.0
        for part in parts:
            seconds = seconds * 60 + float(part)
    except ValueError:  # pragma: no cover - the pattern already rejects these
        return None
    return int(round(seconds * 1000))


# ---------------------------------------------------------------------- the tag table


@dataclass(frozen=True, slots=True)
class TagField:
    """One editable tag: how it is shown, and where it lives in each format.

    ``label`` carries its own ``&`` mnemonic. Mnemonics are unique within a
    group rather than across the whole table, because each group is its own
    notebook page and only the visible page's controls can be reached.

    ``kind`` decides the control the dialog builds: ``text`` a one-line field,
    ``multiline`` a box, ``number`` a digits-only field, ``pair`` two number
    fields stored as one ``"n/m"`` value, and ``bool`` a checkbox stored as
    ``"1"`` or ``""``.

    ``mp4`` is empty for the fields MP4 has no home for. Those are skipped on
    an MP4 file rather than guessed at.
    """

    key: str
    label: str
    group: str
    kind: str
    id3: str
    mp4: str
    help: str


#: Notebook page order and page titles.
GROUPS: tuple[tuple[str, str], ...] = (
    ("main", "Main"),
    ("details", "Details"),
    ("publishing", "Publishing"),
    ("sort", "Sort order"),
)

TAG_FIELDS: tuple[TagField, ...] = (
    # -- main ------------------------------------------------------------------
    TagField(
        "title",
        "&Title:",
        "main",
        "text",
        "TIT2",
        "\xa9nam",
        "The track or episode title. Most players show this as the name of what is playing.",
    ),
    TagField(
        "subtitle",
        "S&ubtitle:",
        "main",
        "text",
        "TIT3",
        "----:com.apple.iTunes:SUBTITLE",
        "A secondary title, such as a book's subtitle or an episode's strap "
        "line. Few players show it; it is stored for the ones that do.",
    ),
    TagField(
        "artist",
        "&Artist:",
        "main",
        "text",
        "TPE1",
        "\xa9ART",
        "The performing artist. For an audiobook this is conventionally the "
        "author; for a podcast, the show's host.",
    ),
    TagField(
        "album",
        "Al&bum:",
        "main",
        "text",
        "TALB",
        "\xa9alb",
        "The album. For an audiobook this is the book's title and for a "
        "podcast the show's name, and it is what groups the files together.",
    ),
    TagField(
        "album_artist",
        "Album a&rtist:",
        "main",
        "text",
        "TPE2",
        "aART",
        "The artist the album is filed under. For an audiobook this is "
        "conventionally the narrator.",
    ),
    TagField(
        "track",
        "Trac&k (number of total):",
        "main",
        "pair",
        "TRCK",
        "trkn",
        "This file's position in the album and how many there are. Leave the "
        "total blank if you do not know it.",
    ),
    TagField(
        "disc",
        "&Disc (number of total):",
        "main",
        "pair",
        "TPOS",
        "disk",
        "This file's disc number and how many discs there are. Leave both "
        "blank for a single-disc release.",
    ),
    TagField(
        "genre",
        "&Genre:",
        "main",
        "text",
        "TCON",
        "\xa9gen",
        "The genre. Audiobooks usually say Audiobook and podcasts Podcast, "
        "which is what makes some players file them apart from music.",
    ),
    TagField(
        "year",
        "&Year:",
        "main",
        "text",
        "TDRC",
        "\xa9day",
        "The release date, as a four-digit year or a fuller date such as "
        "2026-09-02. Leave blank to omit it.",
    ),
    # -- details ---------------------------------------------------------------
    TagField(
        "original_date",
        "&Original release date:",
        "details",
        "text",
        "TDOR",
        "----:com.apple.iTunes:ORIGINALDATE",
        "When the work first came out, if this file is a reissue. A "
        "four-digit year or a fuller date.",
    ),
    TagField(
        "comment",
        "Co&mment:",
        "details",
        "multiline",
        "COMM",
        "\xa9cmt",
        "A free-text comment. Players that show notes show this one.",
    ),
    TagField(
        "lyrics",
        "&Lyrics or transcript:",
        "details",
        "multiline",
        "USLT",
        "\xa9lyr",
        "Unsynchronised lyrics, or any long text you want carried inside the "
        "file, such as a transcript.",
    ),
    TagField(
        "grouping",
        "&Grouping:",
        "details",
        "text",
        "TIT1",
        "\xa9grp",
        "The work or series this belongs to. Apple players group by this field above the album.",
    ),
    TagField(
        "language",
        "L&anguage:",
        "details",
        "text",
        "TLAN",
        "----:com.apple.iTunes:LANGUAGE",
        "The spoken or sung language, conventionally a three-letter code such as eng or fra.",
    ),
    TagField(
        "bpm",
        "&Beats per minute:",
        "details",
        "number",
        "TBPM",
        "tmpo",
        "The tempo, as a whole number. Rarely meaningful for speech; leave it blank.",
    ),
    TagField(
        "compilation",
        "&Part of a compilation",
        "details",
        "bool",
        "TCMP",
        "cpil",
        "Marks the album as a collection by several artists, which stops "
        "Apple players filing every track under a different artist.",
    ),
    # -- publishing ------------------------------------------------------------
    TagField(
        "composer",
        "&Composer:",
        "publishing",
        "text",
        "TCOM",
        "\xa9wrt",
        "The composer or writer.",
    ),
    TagField(
        "conductor",
        "Con&ductor:",
        "publishing",
        "text",
        "TPE3",
        "----:com.apple.iTunes:CONDUCTOR",
        "The conductor. For spoken audio this field is often used for the director or producer.",
    ),
    TagField(
        "publisher",
        "&Publisher:",
        "publishing",
        "text",
        "TPUB",
        "----:com.apple.iTunes:PUBLISHER",
        "The publisher or label that released this.",
    ),
    TagField(
        "copyright",
        "Cop&yright:",
        "publishing",
        "text",
        "TCOP",
        "cprt",
        "The copyright line, such as 2026 Example Press.",
    ),
    TagField(
        "encoded_by",
        "&Encoded by:",
        "publishing",
        "text",
        "TENC",
        "----:com.apple.iTunes:ENCODEDBY",
        "Who or what produced this file. Whatever is already here is left "
        "alone unless you change it.",
    ),
    TagField(
        "isrc",
        "&ISRC:",
        "publishing",
        "text",
        "TSRC",
        "----:com.apple.iTunes:ISRC",
        "The International Standard Recording Code, a twelve-character "
        "identifier issued to commercial recordings.",
    ),
    # -- sort ------------------------------------------------------------------
    TagField(
        "title_sort",
        "Sort &title:",
        "sort",
        "text",
        "TSOT",
        "sonm",
        "How the title files in a sorted list, without changing what is "
        "displayed. Storing this needs ID3 version 2.4, which is switched to "
        "for you.",
    ),
    TagField(
        "artist_sort",
        "Sort &artist:",
        "sort",
        "text",
        "TSOP",
        "soar",
        "How the artist files in a sorted list -- Austen, Jane for Jane "
        "Austen. What is displayed does not change.",
    ),
    TagField(
        "album_sort",
        "Sort al&bum:",
        "sort",
        "text",
        "TSOA",
        "soal",
        "How the album files in a sorted list. What is displayed does not change.",
    ),
    TagField(
        "album_artist_sort",
        "Sort album a&rtist:",
        "sort",
        "text",
        "TSO2",
        "soaa",
        "How the album artist files in a sorted list. What is displayed does not change.",
    ),
)

#: Frames ID3 version 2.3 has no home for. Setting any of these forces v2.4.
V24_ONLY_FRAMES: frozenset[str] = frozenset({
    "TDRC",
    "TDOR",
    "TSOT",
    "TSOP",
    "TSOA",
    "TSO2",
})

_BY_KEY: dict[str, TagField] = {f.key: f for f in TAG_FIELDS}


def fields_in(group: str) -> tuple[TagField, ...]:
    """Every field in *group*, in table order. An unknown group gives ``()``."""
    return tuple(f for f in TAG_FIELDS if f.group == group)


def field_for(key: str) -> TagField:
    """The field named *key*. Raises ``KeyError`` for anything else."""
    return _BY_KEY[key]


# ------------------------------------------------------------------------ containers


@dataclass(slots=True)
class CoverArt:
    """An embedded cover image: the bytes, plus how to describe and file it."""

    data: bytes
    mime: str = "image/jpeg"
    description: str = ""
    #: ID3 APIC picture type; 3 is "cover (front)".
    picture_type: int = 3


@dataclass(slots=True)
class AudioTags:
    """Every editable tag of one file. An absent tag reads as ``""``."""

    values: dict[str, str] = field(default_factory=dict)
    cover: CoverArt | None = None

    def get(self, key: str) -> str:
        """This tag's value, or ``""`` when absent. Unknown key -> ``KeyError``."""
        if key not in _BY_KEY:
            raise KeyError(key)
        return self.values.get(key, "")

    def set(self, key: str, value: str) -> None:
        """Set this tag, or clear it with an empty value. Values are stripped."""
        if key not in _BY_KEY:
            raise KeyError(key)
        text = str(value).strip()
        if text:
            self.values[key] = text
        else:
            self.values.pop(key, None)

    def copy(self) -> AudioTags:
        """An independent copy -- editing it never reaches back to the original."""
        cover = None
        if self.cover is not None:
            cover = CoverArt(
                data=self.cover.data,
                mime=self.cover.mime,
                description=self.cover.description,
                picture_type=self.cover.picture_type,
            )
        return AudioTags(values=dict(self.values), cover=cover)


@dataclass(slots=True)
class Chapter:
    """One chapter: where it starts and ends, and what it is called."""

    index: int
    title: str
    start_ms: int
    end_ms: int
    #: Podcasting 2.0 extras: an optional link and image for this chapter.
    #: Round-tripped through the ``...chapters.json`` sidecar; empty = omitted.
    url: str = ""
    image: str = ""

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


# ------------------------------------------------------------------------ cover art

#: The largest cover image accepted, in bytes. Past this the tag block dwarfs
#: the audio and some players give up reading tags at all.
MAX_COVER_BYTES: int = 8 * 1024 * 1024

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff"


def load_cover(path: Path) -> CoverArt:
    """Read *path* as cover art, sniffing the real bytes, not the extension.

    Only JPEG and PNG are accepted: they are the two every player decodes, and
    a file renamed to ``.jpg`` is still whatever it actually is.
    """
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise TagReadError(f"Could not read the image: {exc}") from exc
    if len(data) > MAX_COVER_BYTES:
        raise TagReadError("That image is larger than the 8 MB cover art limit.")
    if data.startswith(_PNG_MAGIC):
        mime = "image/png"
    elif data.startswith(_JPEG_MAGIC):
        mime = "image/jpeg"
    else:
        raise TagReadError("Cover art must be a JPEG or PNG image.")
    return CoverArt(data=data, mime=mime, description="", picture_type=3)


def cover_extension(cover: CoverArt) -> str:
    """The file extension to suggest when saving *cover* out."""
    return ".png" if cover.mime == "image/png" else ".jpg"


def describe_cover(cover: CoverArt | None) -> str:
    """A speakable description of the art -- what a screen reader can use.

    A thumbnail tells a sighted person everything about a picture and a screen
    reader user nothing, so the text is the primary readout and the image is
    the supplement, not the other way round.
    """
    if cover is None:
        return "No cover art."
    fmt = "PNG" if cover.mime == "image/png" else "JPEG"
    parts = [f"{fmt} image, {len(cover.data):,} bytes"]
    if cover.description:
        parts.append(f"described as {cover.description}")
    return ". ".join(parts) + "."


# -------------------------------------------------------------------------- tag i/o


def preferred_id3_version(tags: AudioTags) -> int:
    """3, or 4 once *tags* set something ID3v2.3 has no frame for.

    Keeping files at 2.3 by default is a compatibility choice; moving them to
    2.4 the moment a sort field or a full date appears is a correctness one.
    Doing it in that order means nobody pays for a frame they never used.
    """
    for key in tags.values:
        if _BY_KEY[key].id3 in V24_ONLY_FRAMES:
            return 4
    return 3


def _is_mp4(path: Path) -> bool:
    return path.suffix.lower() in {".m4a", ".m4b", ".mp4"}


def read_tags(path: Path) -> AudioTags:
    """Every modelled tag on *path* (MP3, or M4A/M4B/MP4).

    A file with no tag block reads as empty tags rather than an error -- an
    untagged file is exactly the one somebody opens an editor to fix.
    """
    target = Path(path)
    if not target.is_file():
        raise TagReadError(f"File not found: {target}")
    return _read_mp4_tags(target) if _is_mp4(target) else _read_mp3_tags(target)


def write_tags(path: Path, tags: AudioTags) -> None:
    """Write every modelled tag onto *path*, leaving everything else alone.

    Load-modify-save: frames this module does not model -- the chapter
    CHAP/CTOC frames above all -- come through untouched.
    """
    target = Path(path)
    if not target.is_file():
        raise TagWriteError(f"File not found: {target}")
    if _is_mp4(target):
        _write_mp4_tags(target, tags)
    else:
        _write_mp3_tags(target, tags)


def _load_id3(path: Path) -> Any:
    """The file's ID3 block, or a fresh empty one when it has none."""
    try:
        from mutagen.id3 import ID3, ID3NoHeaderError
    except ImportError as exc:  # pragma: no cover - only without the extra
        raise TagReadError("Reading and writing tags requires the 'mutagen' package.") from exc
    try:
        return ID3(str(path))
    except ID3NoHeaderError:
        return ID3()
    except Exception as exc:  # noqa: BLE001 - mutagen raises many shapes
        raise TagReadError(f"Could not read tags: {exc}") from exc


def _frame_text(frame_id: str, frame: object) -> str:
    """One frame's value as the flat string the table's model stores."""
    raw = getattr(frame, "text", None)
    if raw is None:
        return ""
    # USLT stores a plain string; every other frame here stores a list, and
    # indexing the string would hand back its first character.
    if isinstance(raw, str):
        return raw
    return str(raw[0]) if raw else ""


def _read_mp3_tags(path: Path) -> AudioTags:
    id3 = _load_id3(path)
    tags = AudioTags()
    for f in TAG_FIELDS:
        frames = id3.getall(f.id3)
        if not frames:
            continue
        value = _frame_text(f.id3, frames[0])
        if f.kind == "bool":
            value = "1" if value.strip() not in {"", "0"} else ""
        if value:
            tags.set(f.key, value)
    pictures = id3.getall("APIC")
    if pictures:
        pic = pictures[0]
        tags.cover = CoverArt(
            data=bytes(pic.data),
            mime=str(pic.mime or "image/jpeg"),
            description=str(pic.desc or ""),
            picture_type=int(pic.type),
        )
    return tags


def _id3_frame(frame_id: str, value: str) -> object:
    """Build the mutagen frame for *frame_id*; COMM and USLT need more fields."""
    import mutagen.id3 as id3mod

    if frame_id == "COMM":
        return id3mod.COMM(encoding=3, lang="eng", desc="", text=[value])
    if frame_id == "USLT":
        return id3mod.USLT(encoding=3, lang="eng", desc="", text=value)
    frame_cls = getattr(id3mod, frame_id)
    return frame_cls(encoding=3, text=[value])


def _write_mp3_tags(path: Path, tags: AudioTags) -> None:
    id3 = _load_id3(path)
    for f in TAG_FIELDS:
        value = tags.get(f.key)
        if f.kind == "bool":
            value = "1" if value else ""
        if value:
            id3.setall(f.id3, [_id3_frame(f.id3, value)])
        else:
            id3.delall(f.id3)
    id3.delall("APIC")
    if tags.cover is not None:
        import mutagen.id3 as id3mod

        id3.add(
            id3mod.APIC(
                encoding=3,
                mime=tags.cover.mime,
                type=tags.cover.picture_type,
                desc=tags.cover.description,
                data=tags.cover.data,
            )
        )
    try:
        id3.save(str(path), v2_version=preferred_id3_version(tags))
    except Exception as exc:  # noqa: BLE001 - mutagen raises many shapes
        raise TagWriteError(f"Could not write tags: {exc}") from exc


#: MP4 atoms whose value is an integer pair ``(number, total)``.
_MP4_PAIR_ATOMS: frozenset[str] = frozenset({"trkn", "disk"})
#: MP4 atoms whose value is a plain integer.
_MP4_INT_ATOMS: frozenset[str] = frozenset({"tmpo"})
#: MP4 atoms whose value is a boolean.
_MP4_BOOL_ATOMS: frozenset[str] = frozenset({"cpil"})


def _load_mp4(path: Path) -> Any:
    try:
        from mutagen.mp4 import MP4
    except ImportError as exc:  # pragma: no cover - only without the extra
        raise TagReadError("Reading and writing tags requires the 'mutagen' package.") from exc
    try:
        audio = MP4(str(path))
    except Exception as exc:  # noqa: BLE001 - mutagen raises many shapes
        raise TagReadError(f"Could not read tags: {exc}") from exc
    if audio.tags is None:
        audio.add_tags()
    return audio


def _mp4_value_to_text(atom: str, raw: object) -> str:
    """One MP4 atom's value as the flat string the table's model stores."""
    if atom in _MP4_BOOL_ATOMS:
        first = raw[0] if isinstance(raw, list) and raw else raw
        return "1" if first else ""
    if not isinstance(raw, list) or not raw:
        return ""
    first = raw[0]
    if atom in _MP4_PAIR_ATOMS and isinstance(first, tuple):
        pair = list(first) + [0, 0]
        number, total = pair[0], pair[1]
        return f"{number}/{total}" if total else str(number)
    if atom in _MP4_INT_ATOMS:
        return str(int(first))
    if isinstance(first, bytes):  # freeform ---- atoms carry raw bytes
        return first.decode("utf-8", "replace")
    return str(first)


def _mp4_text_to_value(atom: str, text: str) -> object:
    """The typed atom value for *text* -- the inverse of the reader above."""
    if atom in _MP4_BOOL_ATOMS:
        return bool(text)
    if atom in _MP4_PAIR_ATOMS:
        number, _sep, total = text.partition("/")
        return [(int(number or 0), int(total or 0))]
    if atom in _MP4_INT_ATOMS:
        return [int(text)]
    if atom.startswith("----"):
        from mutagen.mp4 import MP4FreeForm

        return [MP4FreeForm(text.encode("utf-8"))]
    return [text]


def _read_mp4_tags(path: Path) -> AudioTags:
    audio = _load_mp4(path)
    tags = AudioTags()
    for f in TAG_FIELDS:
        if not f.mp4 or f.mp4 not in audio.tags:
            continue
        value = _mp4_value_to_text(f.mp4, audio.tags[f.mp4])
        if value:
            tags.set(f.key, value)
    covers = audio.tags.get("covr") or []
    if covers:
        from mutagen.mp4 import MP4Cover

        art = covers[0]
        fmt = getattr(art, "imageformat", MP4Cover.FORMAT_JPEG)
        tags.cover = CoverArt(
            data=bytes(art),
            mime="image/png" if fmt == MP4Cover.FORMAT_PNG else "image/jpeg",
        )
    return tags


def _write_mp4_tags(path: Path, tags: AudioTags) -> None:
    audio = _load_mp4(path)
    for f in TAG_FIELDS:
        if not f.mp4:
            continue  # MP4 has no home for this field: skip it, never guess
        value = tags.get(f.key)
        if f.kind == "bool":
            value = "1" if value else ""
        if value:
            try:
                audio.tags[f.mp4] = _mp4_text_to_value(f.mp4, value)
            except ValueError:
                # Non-numeric text typed into a numeric atom. Drop that one
                # field rather than refusing the whole save.
                audio.tags.pop(f.mp4, None)
        else:
            audio.tags.pop(f.mp4, None)
    audio.tags.pop("covr", None)
    if tags.cover is not None:
        from mutagen.mp4 import MP4Cover

        fmt = MP4Cover.FORMAT_PNG if tags.cover.mime == "image/png" else MP4Cover.FORMAT_JPEG
        audio.tags["covr"] = [MP4Cover(tags.cover.data, imageformat=fmt)]
    try:
        audio.save()
    except Exception as exc:  # noqa: BLE001 - mutagen raises many shapes
        raise TagWriteError(f"Could not write tags: {exc}") from exc


# --------------------------------------------------------------- chapter frames (mp3)

#: The element id given to the Nth chapter frame. ``ch0``, ``ch1``, ... is what
#: ffmpeg writes, and matching it is what lets a file pass between the two apps
#: without either noticing. Element ids are opaque handles; no player reads
#: meaning into them.
CHAPTER_ELEMENT_ID = "ch{index}"
#: The element id of the table of contents frame that lists the chapters.
CHAPTER_TOC_ID = "toc"


def write_mp3_chapters(
    path: Path,
    chapters: list[Chapter],
    *,
    toc_title: str = "Chapters",
    v2_version: int | None = None,
) -> None:
    """Write ID3 CHAP + CTOC frames onto *path*, keeping every other tag.

    Idempotent: existing chapter frames are removed first, so running this
    twice does not give you the chapters twice.

    ``v2_version`` selects the ID3 minor version the whole tag block is saved
    as. **Left unset it follows the file**, which is the only safe default:
    saving the block is all-or-nothing, so writing chapters at 2.3 onto a file
    whose tags need 2.4 quietly strands the sort fields and full dates that
    were already there. Reading what is on disk and asking
    :func:`preferred_id3_version` costs one parse and removes a whole class of
    ordering bug -- callers no longer have to write tags and chapters in a
    particular sequence to keep what they wrote. Both versions define CHAP and
    CTOC identically, so the choice costs the chapters nothing either way.
    """
    try:
        from mutagen.id3 import CHAP, CTOC, TIT2, CTOCFlags
    except ImportError as exc:  # pragma: no cover - only without the extra
        raise TagWriteError("Writing chapter markers requires the 'mutagen' package.") from exc

    target = Path(path)
    if v2_version is None:
        v2_version = preferred_id3_version(_read_mp3_tags(target))
    tags = _load_id3(target)
    tags.delall("CHAP")
    tags.delall("CTOC")

    element_ids: list[str] = []
    for chapter in chapters:
        element_id = CHAPTER_ELEMENT_ID.format(index=chapter.index)
        element_ids.append(element_id)
        tags.add(
            CHAP(
                element_id=element_id,
                start_time=int(chapter.start_ms),
                end_time=int(chapter.end_ms),
                start_offset=0xFFFFFFFF,  # 0xFFFFFFFF = "use time, ignore bytes"
                end_offset=0xFFFFFFFF,
                sub_frames=[TIT2(encoding=3, text=[chapter.title])],
            )
        )
    if element_ids:
        tags.add(
            CTOC(
                element_id=CHAPTER_TOC_ID,
                flags=CTOCFlags.TOP_LEVEL | CTOCFlags.ORDERED,
                child_element_ids=element_ids,
                sub_frames=[TIT2(encoding=3, text=[toc_title])],
            )
        )
    try:
        tags.save(str(target), v2_version=v2_version)
    except Exception as exc:  # noqa: BLE001 - mutagen raises many shapes
        raise TagWriteError(f"Could not write chapter markers: {exc}") from exc


def read_mp3_chapters(path: Path) -> list[Chapter]:
    """Read chapter frames back from *path*, ordered by start time.

    Ordered by time and renumbered from zero rather than trusting the element
    ids, because the ids are opaque and a file may have been written by any
    tool.
    """
    from mutagen.id3 import ID3

    tags = ID3(str(path))
    frames = sorted(tags.getall("CHAP"), key=lambda f: f.start_time)
    chapters: list[Chapter] = []
    for index, frame in enumerate(frames):
        title = ""
        title_frame = frame.sub_frames.get("TIT2")
        if title_frame is not None and title_frame.text:
            title = str(title_frame.text[0])
        chapters.append(
            Chapter(
                index=index,
                title=title,
                start_ms=int(frame.start_time),
                end_ms=int(frame.end_time),
            )
        )
    return chapters


# ------------------------------------------------------------- chapter list editing


def _renumber(chapters: list[Chapter]) -> list[Chapter]:
    return [replace(c, index=i) for i, c in enumerate(chapters)]


def merge_chapter(chapters: list[Chapter], index: int) -> list[Chapter]:
    """Remove the marker at *index*, merging that chapter into its neighbour.

    The first chapter merges into the second and keeps the first's title; any
    other merges into the previous one. Audio is never removed -- only the
    marker goes away.
    """
    n = len(chapters)
    if n < 2:
        raise ChapterEditError("There must be at least two chapters to merge.")
    if not 0 <= index < n:
        raise ChapterEditError("No chapter is selected.")
    if index == 0:
        merged = replace(chapters[0], end_ms=chapters[1].end_ms)
        result = [merged, *chapters[2:]]
    else:
        prev = replace(chapters[index - 1], end_ms=chapters[index].end_ms)
        result = [*chapters[: index - 1], prev, *chapters[index + 1 :]]
    return _renumber(result)


def split_chapter(
    chapters: list[Chapter],
    at_ms: int,
    *,
    title: str = "New chapter",
    min_part_ms: int = 1000,
) -> list[Chapter]:
    """Insert a boundary at *at_ms* -- the split-at-the-playhead operation.

    The chapter containing *at_ms* is cut in two; the left half keeps the
    original title and the right half gets *title*. Refuses a point outside
    every chapter, or one that would leave a sliver on either side.
    """
    for i, c in enumerate(chapters):
        if c.start_ms < at_ms < c.end_ms:
            if at_ms - c.start_ms < min_part_ms or c.end_ms - at_ms < min_part_ms:
                raise ChapterEditError("That split point is too close to a chapter boundary.")
            left = replace(c, end_ms=at_ms)
            right = Chapter(
                index=i + 1,
                title=title or "New chapter",
                start_ms=at_ms,
                end_ms=c.end_ms,
            )
            return _renumber([*chapters[:i], left, right, *chapters[i + 1 :]])
    raise ChapterEditError("The split point is not inside a chapter.")


def set_chapter_start(
    chapters: list[Chapter],
    index: int,
    new_start_ms: int,
    *,
    min_part_ms: int = 500,
) -> list[Chapter]:
    """Retime chapter *index*'s start, and the previous chapter's end with it.

    Chapters stay contiguous and ordered; the new start must leave at least
    *min_part_ms* of both the previous chapter and this one.
    """
    if not 0 <= index < len(chapters):
        raise ChapterEditError("No chapter is selected.")
    if index == 0:
        raise ChapterEditError("The first chapter must start at the beginning.")
    lo = chapters[index - 1].start_ms + min_part_ms
    hi = chapters[index].end_ms - min_part_ms
    if not lo <= new_start_ms <= hi:
        raise ChapterEditError(
            f"Start must be between {format_time_precise(lo)} and {format_time_precise(hi)}."
        )
    prev = replace(chapters[index - 1], end_ms=new_start_ms)
    cur = replace(chapters[index], start_ms=new_start_ms)
    return _renumber([*chapters[: index - 1], prev, cur, *chapters[index + 1 :]])


def add_chapter(
    chapters: list[Chapter],
    at_ms: int,
    *,
    title: str = "New chapter",
    min_part_ms: int = 1000,
) -> list[Chapter]:
    """Insert a chapter boundary at *at_ms* -- the explicit "add" operation.

    Inside an existing chapter this is :func:`split_chapter`. At or past the
    last chapter's end there is nothing to split, so the marker is appended as
    a zero-length chapter that a later retime fills out -- the case
    :func:`split_chapter` refuses outright, and the reason "add" is its own
    verb rather than an alias for "split".
    """
    if not chapters:
        raise ChapterEditError("There are no chapters to add to.")
    if at_ms < 0:
        raise ChapterEditError("A chapter cannot start before the beginning.")
    last_end = chapters[-1].end_ms
    if at_ms >= last_end:
        appended = Chapter(
            index=len(chapters),
            title=title or "New chapter",
            start_ms=last_end,
            end_ms=last_end,
        )
        return _renumber([*chapters, appended])
    return split_chapter(chapters, at_ms, title=title, min_part_ms=min_part_ms)


def delete_chapter(chapters: list[Chapter], index: int) -> list[Chapter]:
    """Remove chapter *index*'s marker. The audio is never touched.

    Deleting the first chapter pulls the second one's start back to the
    beginning; deleting any other extends the previous chapter over it. Unlike
    :func:`merge_chapter` this is defined for the last chapter too, and it
    keeps the *surviving* chapter's title rather than the deleted one's --
    which is what "delete" means and "merge" does not.
    """
    n = len(chapters)
    if not 0 <= index < n:
        raise ChapterEditError("No chapter is selected.")
    if n < 2:
        raise ChapterEditError("The only chapter cannot be deleted.")
    if index == 0:
        head = replace(chapters[1], start_ms=chapters[0].start_ms)
        return _renumber([head, *chapters[2:]])
    prev = replace(chapters[index - 1], end_ms=chapters[index].end_ms)
    return _renumber([*chapters[: index - 1], prev, *chapters[index + 1 :]])


def set_chapter_bounds(
    chapters: list[Chapter],
    index: int,
    start_ms: int,
    end_ms: int,
    *,
    min_part_ms: int = 500,
) -> list[Chapter]:
    """Retime both edges of chapter *index*, keeping the list contiguous.

    The neighbours stretch or shrink to meet the new edges. The first
    chapter's start and the last chapter's end are pinned to the file, so a
    different value for either is ignored rather than refused -- there is
    nothing on the far side of them to give or take the time.
    """
    n = len(chapters)
    if not 0 <= index < n:
        raise ChapterEditError("No chapter is selected.")
    if index == 0:
        start_ms = chapters[0].start_ms
    if index == n - 1:
        end_ms = chapters[-1].end_ms
    if end_ms - start_ms < min_part_ms:
        raise ChapterEditError("A chapter's start must come before its end.")
    lo = chapters[index - 1].start_ms + min_part_ms if index > 0 else chapters[0].start_ms
    hi = chapters[index + 1].end_ms - min_part_ms if index < n - 1 else chapters[-1].end_ms
    if not lo <= start_ms <= hi or not lo <= end_ms <= hi:
        raise ChapterEditError(
            f"Start and end must be between {format_time_precise(lo)} "
            f"and {format_time_precise(hi)}."
        )
    result = list(chapters)
    result[index] = replace(chapters[index], start_ms=start_ms, end_ms=end_ms)
    if index > 0:
        result[index - 1] = replace(chapters[index - 1], end_ms=start_ms)
    if index < n - 1:
        result[index + 1] = replace(chapters[index + 1], start_ms=end_ms)
    return _renumber(result)


#: The nudge step sizes the editors offer, in milliseconds.
NUDGE_STEPS_MS: tuple[int, ...] = (100, 250, 500, 1000, 2000, 5000, 10_000)


def nudge_chapter_start(
    chapters: list[Chapter],
    index: int,
    delta_ms: int,
    *,
    min_part_ms: int = 500,
) -> tuple[list[Chapter], int]:
    """Move chapter *index*'s start by *delta_ms*, clamped at its neighbours.

    Returns the new list and the delta **actually** applied. This is the one
    chapter edit that clamps rather than raising: a nudge is a held key, and
    running a marker up against its neighbour should stop there, not throw. An
    applied delta of 0 means the marker is already at the wall, which lets the
    caller say so once per run instead of once per keypress.

    Because chapters are contiguous, a chapter's start *is* the previous
    chapter's end, so this moves both sides of one boundary.
    """
    n = len(chapters)
    if not 0 <= index < n:
        raise ChapterEditError("No chapter is selected.")
    if index == 0:
        raise ChapterEditError("The first chapter must start at the beginning.")
    lo = chapters[index - 1].start_ms + min_part_ms
    hi = chapters[index].end_ms - min_part_ms
    current = chapters[index].start_ms
    if lo > hi:
        return list(chapters), 0
    target = max(lo, min(current + delta_ms, hi))
    applied = target - current
    if applied == 0:
        return list(chapters), 0
    prev = replace(chapters[index - 1], end_ms=target)
    cur = replace(chapters[index], start_ms=target)
    result = _renumber([*chapters[: index - 1], prev, cur, *chapters[index + 1 :]])
    return result, applied


def clamp_chapters(chapters: list[Chapter], total_ms: int) -> list[Chapter]:
    """Clamp chapters to ``[0, total_ms]``, dropping any that fall outside.

    Guards a plan against a re-encode that shortened the audio, or an imported
    list from a different edit of the file: starts and ends are clamped, empty
    chapters are dropped, and the final chapter is extended to *total_ms* so
    the whole timeline stays covered.
    """
    if total_ms <= 0:
        return []
    kept: list[Chapter] = []
    for c in chapters:
        start = max(0, min(c.start_ms, total_ms))
        end = max(0, min(c.end_ms, total_ms))
        if end > start:
            kept.append(replace(c, start_ms=start, end_ms=end))
    if kept:
        kept[-1] = replace(kept[-1], end_ms=total_ms)
    return _renumber(kept)
