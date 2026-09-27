"""Carry a file's cover art into its converted copy (mutagen, bundled).

FFmpeg keeps the text tags -- title, artist, album -- across nearly every
conversion, but it drops the cover picture on most of them: an audio-only
encode (``-vn`` / ``-map 0:a``) discards the attached-picture stream by
design, and Ogg, Opus and FLAC store pictures in a way FFmpeg does not write
at all. A converted audiobook or album then shows as a blank square in every
player, and a screen-reader user may never learn it had artwork until a
sighted friend asks where it went.

So after a successful encode the runner calls :func:`carry_cover_art`, which
reads the first picture from the source with mutagen and writes it into the
output in that format's own way. Best effort by contract: no mutagen, no
picture, or a format mutagen cannot write, and the converted file is simply
left as FFmpeg made it. It never raises.
"""

from __future__ import annotations

import base64
from pathlib import Path


def _read_picture(source: Path) -> tuple[bytes, str] | None:
    """The first embedded picture in *source* as ``(bytes, mime)``, or None."""
    import mutagen

    audio = mutagen.File(str(source))
    if audio is None:
        return None
    pictures = getattr(audio, "pictures", None)  # FLAC
    if pictures:
        return pictures[0].data, pictures[0].mime or "image/jpeg"
    tags = getattr(audio, "tags", None)
    if tags is None:
        return None
    if hasattr(tags, "getall"):  # ID3 (MP3, AIFF, WAV)
        frames = tags.getall("APIC")
        if frames:
            return frames[0].data, frames[0].mime or "image/jpeg"
    covr = tags.get("covr") if hasattr(tags, "get") else None  # MP4
    if covr:
        from mutagen.mp4 import MP4Cover

        first = covr[0]
        mime = (
            "image/png" if getattr(first, "imageformat", 0) == MP4Cover.FORMAT_PNG else "image/jpeg"
        )
        return bytes(first), mime
    blocks = tags.get("metadata_block_picture") if hasattr(tags, "get") else None  # Ogg
    if blocks:
        from mutagen.flac import Picture

        picture = Picture(base64.b64decode(blocks[0]))
        return picture.data, picture.mime or "image/jpeg"
    return None


def _has_picture(dest: Path) -> bool:
    try:
        return _read_picture(dest) is not None
    except Exception:  # noqa: BLE001 - unreadable means "no"
        return False


def _write_picture(dest: Path, data: bytes, mime: str) -> bool:
    """Write *data* as the front cover of *dest* in its own format's way."""
    import mutagen
    from mutagen.flac import Picture

    suffix = dest.suffix.lower()
    if suffix in (".mp3", ".mp2"):
        from mutagen.id3 import APIC, ID3, ID3NoHeaderError

        try:
            tags = ID3(str(dest))
        except ID3NoHeaderError:
            tags = ID3()
        tags.add(APIC(encoding=3, mime=mime, type=3, desc="Cover", data=data))
        tags.save(str(dest))
        return True
    if suffix in (".wav", ".aiff", ".aif"):
        # WAV and AIFF keep ID3 in a chunk inside the RIFF/FORM container. A
        # bare ID3().save() writes a header in front of the file instead, and
        # no player can open the result (found end to end, 2026-09-27).
        from mutagen.aiff import AIFF
        from mutagen.id3 import APIC
        from mutagen.wave import WAVE

        riff = WAVE(str(dest)) if suffix == ".wav" else AIFF(str(dest))
        if riff.tags is None:
            riff.add_tags()
        riff_tags = riff.tags
        assert riff_tags is not None  # add_tags() just made them
        riff_tags.add(APIC(encoding=3, mime=mime, type=3, desc="Cover", data=data))
        riff.save()
        return True
    if suffix in (".m4a", ".m4b", ".m4r", ".mp4", ".mov", ".aac"):
        if suffix == ".aac":
            return False  # a raw ADTS stream has nowhere to keep a picture
        from mutagen.mp4 import MP4, MP4Cover

        audio = MP4(str(dest))
        kind = MP4Cover.FORMAT_PNG if mime == "image/png" else MP4Cover.FORMAT_JPEG
        audio["covr"] = [MP4Cover(data, imageformat=kind)]
        audio.save()
        return True
    picture = Picture()
    picture.type = 3
    picture.mime = mime
    picture.desc = "Cover"
    picture.data = data
    if suffix == ".flac":
        from mutagen.flac import FLAC

        flac = FLAC(str(dest))
        flac.add_picture(picture)
        flac.save()
        return True
    if suffix in (".ogg", ".oga", ".opus", ".spx"):
        audio = mutagen.File(str(dest))
        if audio is None:
            return False
        if audio.tags is None:
            audio.add_tags()
        audio.tags["metadata_block_picture"] = [base64.b64encode(picture.write()).decode("ascii")]
        audio.save()
        return True
    return False


def carry_cover_art(source: Path, dest: Path) -> bool:
    """Copy *source*'s cover into *dest* when *dest* has none. Never raises."""
    try:
        found = _read_picture(source)
        if found is None or _has_picture(dest):
            return False
        return _write_picture(dest, *found)
    except Exception:  # noqa: BLE001 - artwork is a courtesy, never a failure
        return False
