"""DAISY navigation parsing (PRD Section 7.8) -- audio-nav-only for v1.

Parses a DAISY NCX navigation document into an ordered heading list the player
surfaces as its chapter/heading tree (Enter jumps). This unblocks BARD audio
navigation (``bard.md`` Service 3). v1 is audio-navigation-only: it extracts the
heading structure (title, play order, content reference, depth); resolving each
heading to an exact millisecond offset from the DAISY SMIL is a follow-on.

Untrusted XML is parsed through :func:`quill.core.safe_xml.fromstring`, so a
document declaring a DTD or custom entities is refused, never expanded.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from xml.etree.ElementTree import Element

from quill.core.media.errors import MediaError
from quill.core.safe_xml import fromstring


class DaisyParseError(MediaError):
    """Raised when an NCX document cannot be parsed into a heading list."""

    code = "QUILL-MEDIA-DAISY-PARSE"


@dataclass(frozen=True, slots=True)
class DaisyHeading:
    """One navigation point in a DAISY book.

    ``time_ms`` is the audio start offset resolved from the SMIL (``None`` until
    :func:`resolve_heading_times` fills it in, or when it cannot be resolved).
    """

    title: str
    play_order: int
    src: str
    depth: int
    time_ms: int | None = None
    #: The audio file this heading plays from (filled by resolve_heading_times);
    #: distinct values across headings mean a multi-file book.
    audio_src: str = ""


def _local(tag: str) -> str:
    """The local name of a possibly-namespaced element tag."""
    return tag.rsplit("}", 1)[-1]


def parse_ncx(xml: str | bytes) -> list[DaisyHeading]:
    """Parse an NCX document into an ordered list of :class:`DaisyHeading`.

    Headings are returned in document order (which mirrors reading order). A
    malformed or non-NCX document raises :class:`DaisyParseError`.
    """
    try:
        root = fromstring(xml)
    except DaisyParseError:
        raise
    except Exception as exc:  # noqa: BLE001 - normalize any parse failure
        raise DaisyParseError(f"could not parse NCX: {exc}") from exc

    nav_map = next((el for el in root.iter() if _local(el.tag) == "navMap"), None)
    if nav_map is None:
        raise DaisyParseError("no <navMap> in NCX document")

    headings: list[DaisyHeading] = []
    _walk_nav_points(nav_map, depth=1, out=headings)
    return headings


def _walk_nav_points(parent: Element, *, depth: int, out: list[DaisyHeading]) -> None:
    for child in list(parent):
        if _local(child.tag) != "navPoint":
            continue
        out.append(_heading_from(child, depth))
        _walk_nav_points(child, depth=depth + 1, out=out)


def _heading_from(nav_point: Element, depth: int) -> DaisyHeading:
    title = ""
    src = ""
    for el in nav_point.iter():
        name = _local(el.tag)
        if name == "text" and not title and el.text:
            title = el.text.strip()
        elif name == "content" and not src:
            src = str(el.get("src", "") or "")
    return DaisyHeading(
        title=title,
        play_order=_int_attr(nav_point, "playOrder"),
        src=src,
        depth=depth,
    )


def _int_attr(element: Element, name: str) -> int:
    try:
        return int(element.get(name, "") or "")
    except (TypeError, ValueError):
        return 0


# -- SMIL clip-time resolution -----------------------------------------------

_NPT_RE = re.compile(r"^\s*(?:npt=)?\s*(.+?)\s*$", re.IGNORECASE)


def parse_clip_ms(text: str) -> int | None:
    """Parse a SMIL clip time into milliseconds, or ``None`` if unparseable.

    Handles ``npt=12.5s`` / ``12.5s`` / ``12500ms`` / plain seconds ``12.5`` and
    clock forms ``0:12.5`` (mm:ss) and ``1:02:03.5`` (h:mm:ss).
    """
    if not isinstance(text, str) or not text.strip():
        return None
    match = _NPT_RE.match(text)
    value = (match.group(1) if match else text).strip()
    try:
        if value.endswith("ms"):
            return int(float(value[:-2]))
        if value.endswith("s"):
            return int(round(float(value[:-1]) * 1000))
        if ":" in value:
            parts = [float(p) for p in value.split(":")]
            if len(parts) > 3:
                return None
            seconds = 0.0
            for part in parts:
                seconds = seconds * 60 + part
            return int(round(seconds * 1000))
        return int(round(float(value) * 1000))
    except (TypeError, ValueError):
        return None


def smil_clip_begin_ms(smil_xml: str | bytes, fragment_id: str) -> int | None:
    """Return the earliest audio ``clipBegin`` (ms) under the element ``fragment_id``.

    Looks up the SMIL element whose ``id`` matches ``fragment_id`` and returns the
    first ``<audio>`` clip-begin within it (handling ``clipBegin``/``clip-begin``
    spellings). Returns ``None`` when nothing resolves.
    """
    try:
        root = fromstring(smil_xml)
    except Exception:  # noqa: BLE001 - a bad SMIL just means "no offset"
        return None
    target = next((el for el in root.iter() if el.get("id") == fragment_id), None)
    if target is None:
        return None
    for el in target.iter():
        if _local(el.tag) != "audio":
            continue
        raw = el.get("clipBegin") or el.get("clip-begin")
        if raw is not None:
            parsed = parse_clip_ms(raw)
            if parsed is not None:
                return parsed
    return None


def smil_audio_clip(smil_xml: str | bytes, fragment_id: str) -> tuple[str, int] | None:
    """Return ``(audio_src, clipBegin_ms)`` for the SMIL element ``fragment_id``.

    The multi-file counterpart of :func:`smil_clip_begin_ms`: it returns *which*
    audio file the fragment plays from as well as the offset, so a book split
    across many audio files can be navigated. ``None`` when nothing resolves.
    """
    try:
        root = fromstring(smil_xml)
    except Exception:  # noqa: BLE001
        return None
    target = next((el for el in root.iter() if el.get("id") == fragment_id), None)
    if target is None:
        return None
    for el in target.iter():
        if _local(el.tag) != "audio":
            continue
        src = str(el.get("src", "") or "")
        raw = el.get("clipBegin") or el.get("clip-begin")
        ms = parse_clip_ms(raw) if raw else 0
        if src or ms:
            return (src, ms or 0)
    return None


def first_audio_src(smil_xml: str | bytes) -> str | None:
    """Return the ``src`` of the first ``<audio>`` in a SMIL document, or ``None``."""
    try:
        root = fromstring(smil_xml)
    except Exception:  # noqa: BLE001
        return None
    for el in root.iter():
        if _local(el.tag) == "audio":
            src = el.get("src")
            if src:
                return str(src)
    return None


def resolve_heading_times(
    headings: list[DaisyHeading], load_smil: Callable[[str], str | bytes | None]
) -> list[DaisyHeading]:
    """Fill each heading's ``time_ms`` from its SMIL, using an injected loader.

    ``load_smil(filename)`` returns the SMIL document's text (or ``None`` if
    missing); the loader is injected so this is testable without file I/O.
    Loaded SMIL files are cached across headings that share one.
    """
    cache: dict[str, str | bytes | None] = {}
    resolved: list[DaisyHeading] = []
    for heading in headings:
        filename, _, fragment = heading.src.partition("#")
        time_ms: int | None = None
        audio_src = ""
        if filename and fragment:
            if filename not in cache:
                cache[filename] = load_smil(filename)
            smil = cache[filename]
            if smil:
                clip = smil_audio_clip(smil, fragment)
                if clip is not None:
                    audio_src, time_ms = clip[0], clip[1]
        resolved.append(replace(heading, time_ms=time_ms, audio_src=audio_src))
    return resolved


__all__ = [
    "DaisyHeading",
    "DaisyParseError",
    "first_audio_src",
    "parse_clip_ms",
    "parse_ncx",
    "smil_audio_clip",
    "resolve_heading_times",
    "smil_clip_begin_ms",
]
